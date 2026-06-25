"""nexus_v1.observer — Entropy Ledger (adapted from RLIS observer).

External observer for the nexus_v1 unified circuit.
Reads HebbianCircuit state WITHOUT modification.

Computes per-tick:
  1. TickSnapshot: frozen copy of all neuron/bundle states
  2. EntropyBalance: per-neuron and per-bundle energy accounting
  3. SignalTrace: tracks signal propagation from MET → Motor

This is the entropy audit tool that externally examines
whether the circuit is actually working.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

from ..components.neuron import Neuron
from ..circuit.bundle import SynapticBundle


# ─────────────────────────────────────────────────────────────
# Data Structures
# ─────────────────────────────────────────────────────────────

@dataclass
class TickSnapshot:
    """Frozen copy of circuit state at one tick."""
    tick: int = 0

    # Per-neuron state (neuron_id → value)
    neuron_voltages: Dict[str, float] = field(default_factory=dict)
    neuron_activations: Dict[str, float] = field(default_factory=dict)
    neuron_energies: Dict[str, float] = field(default_factory=dict)
    neuron_release_rates: Dict[str, float] = field(default_factory=dict)
    neuron_spike_counts: Dict[str, int] = field(default_factory=dict)

    # Per-bundle state (bundle_id → value)
    bundle_mean_weights: Dict[str, float] = field(default_factory=dict)
    bundle_transport_costs: Dict[str, float] = field(default_factory=dict)

    # Aggregate
    total_energy: float = 0.0
    total_heat: float = 0.0
    total_spikes: int = 0
    active_neuron_count: int = 0


@dataclass
class EntropyBalance:
    """Per-tick entropy accounting.

    For each tick, tracks:
      - input_entropy: energy injected into the system
      - dissipation: energy lost to heat (PowerRail IR drop, RC leak)
      - stored: energy retained in capacitors
      - transport: energy used by bundle propagation
      - balance_error: |input - dissipation - stored - transport|
    """
    tick: int = 0
    input_entropy: float = 0.0
    dissipation: float = 0.0
    stored: float = 0.0
    transport: float = 0.0
    balance_error: float = 0.0

    # Per-layer aggregates
    layer_energies: Dict[str, float] = field(default_factory=dict)
    layer_activations: Dict[str, float] = field(default_factory=dict)

    # Signal propagation depth
    # How far the signal got from input (MET) to output (Motor)
    signal_depth: int = 0  # 0 = nothing, 5 = full path
    signal_trace: Dict[str, float] = field(default_factory=dict)


@dataclass
class LedgerEntry:
    """One row in the entropy ledger."""
    tick: int
    snapshot: TickSnapshot
    entropy: EntropyBalance


# ─────────────────────────────────────────────────────────────
# CircuitObserver
# ─────────────────────────────────────────────────────────────

class CircuitObserver:
    """External observer — reads nexus_v1 HebbianCircuit, never writes.

    Usage:
        observer = CircuitObserver()
        for t in range(N):
            circuit.step(inputs, dt)
            observer.observe(circuit, t)
        observer.print_summary()
    """

    def __init__(self, max_ledger_size: int = 10000):
        self._ledger: List[LedgerEntry] = []
        self._max_ledger_size = max_ledger_size

    @property
    def ledger(self) -> List[LedgerEntry]:
        return self._ledger

    @property
    def latest(self) -> Optional[LedgerEntry]:
        return self._ledger[-1] if self._ledger else None

    def observe(self, circuit, tick: int) -> LedgerEntry:
        """Take snapshot and compute entropy balance.

        Args:
            circuit: nexus_v1 HebbianCircuit instance (read-only).
            tick: current tick number.
        """
        snapshot = self._take_snapshot(circuit, tick)
        entropy = self._compute_entropy_balance(circuit, tick)

        entry = LedgerEntry(
            tick=tick,
            snapshot=snapshot,
            entropy=entropy,
        )

        self._ledger.append(entry)
        if len(self._ledger) > self._max_ledger_size:
            self._ledger.pop(0)

        return entry

    # ── Snapshot ──────────────────────────────────────────────

    def _take_snapshot(self, circuit, tick: int) -> TickSnapshot:
        """Deep-read all neuron/bundle states. NEVER mutates circuit."""
        snap = TickSnapshot(tick=tick)

        all_neurons = circuit.get_all_neurons()
        all_bundles = circuit.get_all_bundles()

        for n in all_neurons:
            snap.neuron_voltages[n.id] = n._membrane.voltage
            snap.neuron_activations[n.id] = n.activation
            snap.neuron_energies[n.id] = n.energy
            snap.neuron_release_rates[n.id] = n.release_rate
            snap.neuron_spike_counts[n.id] = len(n.spike_times)

        for b in all_bundles:
            snap.bundle_mean_weights[b.id] = b.mean_weight()
            snap.bundle_transport_costs[b.id] = b.transport_cost

        snap.total_energy = sum(snap.neuron_energies.values())
        snap.total_heat = sum(n.heat_output for n in all_neurons)
        snap.total_spikes = sum(snap.neuron_spike_counts.values())
        snap.active_neuron_count = sum(
            1 for a in snap.neuron_activations.values() if abs(a) > 1e-6
        )

        return snap

    # ── Entropy Balance ───────────────────────────────────────

    def _compute_entropy_balance(self, circuit, tick: int) -> EntropyBalance:
        """Compute per-layer entropy and signal propagation depth."""
        eb = EntropyBalance(tick=tick)

        # Per-layer energy and activation
        # Vestibular layers
        vest = circuit.vestibular
        layers = {
            "met": list(vest.met_neurons.values()),
            "haircell": list(vest.haircell_neurons.values()),
            "afferent_reg": list(vest.afferent_regular.values()),
            "afferent_irr": list(vest.afferent_irregular.values()),
            "encoding": list(circuit.encoding_neurons.values()),
            "column": list(circuit.column_neurons.values()),
            "motor": list(circuit.motor_neurons.values()),
        }

        total_input = 0.0
        total_dissip = 0.0
        total_stored = 0.0

        for layer_name, neurons in layers.items():
            layer_energy = sum(n.energy for n in neurons)
            layer_act = sum(n._activation_ema for n in neurons)  # M4
            layer_heat = sum(n.heat_output for n in neurons)
            layer_stored = sum(abs(n._membrane.voltage * n.config.capacitance)
                             for n in neurons)

            eb.layer_energies[layer_name] = layer_energy
            eb.layer_activations[layer_name] = layer_act
            total_dissip += layer_heat
            total_stored += layer_stored

        eb.dissipation = total_dissip
        eb.stored = total_stored
        eb.transport = sum(b.transport_cost for b in circuit.get_all_bundles())

        # Signal propagation depth
        # For spiking neurons, use cumulative spike counts instead of
        # instantaneous activation (which only lasts 1 dt and gets missed)
        depth = 0
        trace = {}
        for layer_name in ["met", "haircell", "afferent_reg", "encoding",
                           "column", "motor"]:
            act = eb.layer_activations.get(layer_name, 0.0)
            # For spiking layers, check if ANY neuron has fired at all
            layer_neurons = layers.get(layer_name, [])
            spike_count = sum(len(n.spike_times) for n in layer_neurons)
            # Use whichever signal indicator is present
            signal = max(act, float(spike_count))
            trace[layer_name] = signal
            if signal > 1e-6:
                depth += 1
            else:
                break  # signal didn't reach this layer

        eb.signal_depth = depth
        eb.signal_trace = trace

        return eb

    # ── Summary ───────────────────────────────────────────────

    def print_summary(self):
        """Print human-readable entropy ledger summary."""
        if not self._ledger:
            print("Ledger is empty.")
            return

        print("=" * 70)
        print("ENTROPY LEDGER SUMMARY")
        print("=" * 70)

        latest = self._ledger[-1]
        snap = latest.snapshot
        eb = latest.entropy

        print(f"\nTick: {latest.tick}")
        print(f"Active neurons: {snap.active_neuron_count}")
        print(f"Total spikes:   {snap.total_spikes}")
        print(f"Total energy:   {snap.total_energy:.4f}")
        print(f"Total heat:     {snap.total_heat:.6f}")

        print(f"\n--- Layer Activations (signal propagation) ---")
        for layer, act in eb.signal_trace.items():
            if math.isnan(act) or math.isinf(act):
                print(f"  {layer:15s}: {'NaN/Inf':>8s}  << UNSTABLE")
                continue
            bar_len = int(min(act, 10) * 5)
            bar = "#" * bar_len
            marker = " << DEAD" if act < 1e-6 else ""
            print(f"  {layer:15s}: {act:8.4f} {bar}{marker}")
        print(f"  Signal depth: {eb.signal_depth}/6")

        print(f"\n--- Layer Energies ---")
        for layer, energy in eb.layer_energies.items():
            print(f"  {layer:15s}: {energy:.4f}")

        print(f"\n--- Bundle Weights ---")
        for bid, w in snap.bundle_mean_weights.items():
            print(f"  {bid:35s}: {w:.4f}")

        print(f"\n--- Entropy Accounting ---")
        print(f"  Dissipation (heat): {eb.dissipation:.6f}")
        print(f"  Stored (capacitors):{eb.stored:.6f}")
        print(f"  Transport (bundles):{eb.transport:.6f}")

    def signal_depth_history(self) -> List[Tuple[int, int]]:
        """Return (tick, signal_depth) over time."""
        return [(e.tick, e.entropy.signal_depth) for e in self._ledger]

    def layer_activation_history(self, layer: str) -> List[Tuple[int, float]]:
        """Return (tick, activation) for a specific layer over time."""
        return [(e.tick, e.entropy.layer_activations.get(layer, 0.0))
                for e in self._ledger]

    def weight_history(self, bundle_id: str) -> List[Tuple[int, float]]:
        """Return (tick, weight) for a specific bundle over time."""
        return [(e.tick, e.snapshot.bundle_mean_weights.get(bundle_id, 0.0))
                for e in self._ledger]

    def to_table(self) -> List[Dict]:
        """Export ledger as list of dicts (for SQLite/CSV)."""
        rows = []
        for e in self._ledger:
            row = {
                "tick": e.tick,
                "active_neurons": e.snapshot.active_neuron_count,
                "total_spikes": e.snapshot.total_spikes,
                "total_energy": e.snapshot.total_energy,
                "total_heat": e.snapshot.total_heat,
                "signal_depth": e.entropy.signal_depth,
                "dissipation": e.entropy.dissipation,
                "stored": e.entropy.stored,
                "transport": e.entropy.transport,
            }
            # Add per-layer activations
            for layer, act in e.entropy.layer_activations.items():
                row[f"act_{layer}"] = act
            # Add per-bundle weights
            for bid, w in e.snapshot.bundle_mean_weights.items():
                row[f"w_{bid}"] = w
            rows.append(row)
        return rows
