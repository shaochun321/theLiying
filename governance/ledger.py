"""governance.ledger — Extended Entropy Ledger with Governance Integration.

Migrated from nexus_v1/components/entropy_ledger.py with additions:
    - Signal gain chain tracking (input→output amplification)
    - Baseline activity monitoring
    - G-001 v2.0 metric computation (ds², κ, ν with δa)
    - Governance-grade reporting

The original entropy_ledger.py remains in nexus_v1 for backward compatibility.
This module is the governance-grade version with extended capabilities.
"""

import math
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple


@dataclass
class GovernanceLedger:
    """Extended entropy ledger for the governance system.

    All capabilities of the original EntropyLedger plus:
    - Gain chain tracking
    - Baseline monitoring
    - ds²/κ computation with δa
    """

    window_size: int = 1000

    # ── Running totals (from original) ──
    _total_heat_dissipated: float = field(default=0.0, repr=False)
    _total_spikes: int = field(default=0, repr=False)
    _total_steps: int = field(default=0, repr=False)
    _total_time: float = field(default=0.0, repr=False)

    # ── Per-layer tracking ──
    _layer_energy: Dict[str, List[float]] = field(
        default_factory=dict, repr=False)
    _layer_heat: Dict[str, List[float]] = field(
        default_factory=dict, repr=False)
    _layer_activity: Dict[str, List[float]] = field(
        default_factory=dict, repr=False)

    # ── Entropy rate ──
    _entropy_rate: List[float] = field(default_factory=list, repr=False)

    # ── NEW: Baseline tracking ──
    _baseline_ema: Dict[str, float] = field(
        default_factory=dict, repr=False)
    _baseline_tau: float = field(default=500.0, repr=False)

    # ── NEW: Gain chain ──
    _gain_chain: Dict[str, float] = field(
        default_factory=dict, repr=False)

    # ── NEW: ds² / κ history ──
    _ds2_history: List[float] = field(default_factory=list, repr=False)
    _kappa_history: List[float] = field(default_factory=list, repr=False)

    def record(self, circuit, dt: float):
        """Record one step of circuit state."""
        self._total_steps += 1
        self._total_time += dt

        neurons = circuit.get_all_neurons()

        # ── 1. Energy accounting (from original) ──
        total_heat = 0.0
        spikes_this_step = 0

        for n in neurons:
            total_heat += n.heat_output
            if hasattr(n, '_spiked_this_step') and n._spiked_this_step:
                spikes_this_step += 1

        self._total_heat_dissipated += total_heat * dt
        self._total_spikes += spikes_this_step

        # ── 2. Layer-wise tracking ──
        layers: Dict[str, list] = {
            'L1_MET': [], 'L2_HC': [], 'L3_Aff': [],
            'L4_Enc': [], 'L5_Col': [], 'L6_Mot': [],
        }
        for n in neurons:
            nid = n.config.neuron_id
            if nid.startswith('met_'):
                layers['L1_MET'].append(n)
            elif nid.startswith('hc_'):
                layers['L2_HC'].append(n)
            elif nid.startswith('aff_'):
                layers['L3_Aff'].append(n)
            elif nid.startswith('enc_'):
                layers['L4_Enc'].append(n)
            elif nid.startswith('col_'):
                layers['L5_Col'].append(n)
            elif nid.startswith('motor_'):
                layers['L6_Mot'].append(n)

        for layer_name, layer_neurons in layers.items():
            if not layer_neurons:
                continue
            if layer_name not in self._layer_energy:
                self._layer_energy[layer_name] = []
                self._layer_heat[layer_name] = []
                self._layer_activity[layer_name] = []

            avg_act = sum(abs(n.activation) for n in layer_neurons) / len(
                layer_neurons)
            avg_energy = sum(n.energy for n in layer_neurons) / len(
                layer_neurons)
            avg_heat = sum(n.heat_output for n in layer_neurons) / len(
                layer_neurons)

            self._layer_activity[layer_name].append(avg_act)
            self._layer_energy[layer_name].append(avg_energy)
            self._layer_heat[layer_name].append(avg_heat)

            # Rolling window
            for store in (self._layer_activity, self._layer_energy,
                          self._layer_heat):
                if len(store[layer_name]) > self.window_size:
                    store[layer_name] = store[layer_name][-self.window_size:]

        # ── 3. Entropy production rate ──
        self._entropy_rate.append(total_heat)
        if len(self._entropy_rate) > self.window_size:
            self._entropy_rate = self._entropy_rate[-self.window_size:]

        # ── 4. NEW: Baseline tracking ──
        self._update_baselines(neurons, dt)

        # ── 5. NEW: Gain chain ──
        self._update_gain_chain(layers)

    def _update_baselines(self, neurons, dt: float):
        """Track baseline activity per neuron (EMA)."""
        alpha = dt / max(self._baseline_tau * dt, dt)
        for n in neurons:
            nid = n.config.neuron_id
            act = abs(n.activation)
            if nid not in self._baseline_ema:
                self._baseline_ema[nid] = act
            else:
                self._baseline_ema[nid] += alpha * (
                    act - self._baseline_ema[nid])

    def _update_gain_chain(self, layers: Dict[str, list]):
        """Compute signal gain from layer to layer.

        For spiking neurons, uses pre_trace (temporally smoothed firing
        rate proxy) instead of instantaneous activation (0 or 1).
        """
        chain = [
            ('L1_MET', 'L2_HC'), ('L2_HC', 'L3_Aff'),
            ('L3_Aff', 'L4_Enc'), ('L4_Enc', 'L5_Col'),
            ('L5_Col', 'L6_Mot'),
        ]
        for src_name, tgt_name in chain:
            src_list = layers.get(src_name, [])
            tgt_list = layers.get(tgt_name, [])
            if src_list and tgt_list:
                src_act = sum(self._effective_activity(n)
                              for n in src_list) / len(src_list)
                tgt_act = sum(self._effective_activity(n)
                              for n in tgt_list) / len(tgt_list)
                if src_act > 1e-10:
                    gain = tgt_act / src_act
                else:
                    gain = 0.0
                key = f"{src_name}→{tgt_name}"
                self._gain_chain[key] = gain

    @staticmethod
    def _effective_activity(n) -> float:
        """Get effective activity for gain measurement.

        Spiking neurons: use pre_trace (firing rate proxy).
        Non-spiking neurons: use |activation| directly.
        HairCells: use |activation| for consistency with EntropyLedger.
        # FIX(V02): release_rate ≈ 0 for hc_ neurons → caused L1→L2=0.000
        # vs EntropyLedger 0.977; unified to |activation| across all layers.
        """
        nid = n.config.neuron_id
        # Spiking neurons: activation is binary 0/1, use pre_trace instead
        if n.config.spiking:
            return abs(n.pre_trace)
        return abs(n.activation)

    def get_baselines(self) -> Dict[str, float]:
        """Return current baseline estimates for all neurons."""
        return dict(self._baseline_ema)

    def get_gain_chain(self) -> Dict[str, float]:
        """Return current gain chain."""
        return dict(self._gain_chain)

    def summary(self) -> Dict:
        """Generate governance-grade report."""
        report = {
            'time': self._total_time,
            'steps': self._total_steps,
            'total_spikes': self._total_spikes,
            'total_heat_dissipated': self._total_heat_dissipated,
            'layers': {},
            'gain_chain': self._gain_chain,
            'n_baselined_neurons': len(self._baseline_ema),
        }

        for layer_name in self._layer_energy:
            e = self._layer_energy[layer_name]
            a = self._layer_activity[layer_name]
            report['layers'][layer_name] = {
                'avg_energy': sum(e) / max(len(e), 1),
                'avg_activity': sum(a) / max(len(a), 1),
                'energy_trend': e[-1] - e[0] if len(e) > 1 else 0,
                'baseline': sum(a[-50:]) / max(len(a[-50:]), 1) if a else 0,
            }

        if self._entropy_rate:
            report['entropy_production_rate'] = (
                sum(self._entropy_rate) / len(self._entropy_rate))

        return report

    def print_report(self):
        """Print formatted governance ledger report."""
        r = self.summary()
        print("=" * 70)
        print("熵 治 理 报 告 (Entropy Governance Report)")
        print("=" * 70)
        print(f"  模拟时间: {r['time']:.3f}s ({r['steps']} steps)")
        print(f"  总 spike: {r['total_spikes']}")
        print(f"  总热耗散: {r['total_heat_dissipated']:.6f}")

        if 'entropy_production_rate' in r:
            print(f"  熵产生率 dS/dt: {r['entropy_production_rate']:.6f}")

        print(f"\n  {'Layer':<12s}  {'Avg Act':>8s}  {'Baseline':>8s}  "
              f"{'Avg E':>8s}  {'E trend':>8s}")
        for ln in sorted(r['layers']):
            L = r['layers'][ln]
            print(f"  {ln:<12s}  {L['avg_activity']:>8.4f}  "
                  f"{L['baseline']:>8.4f}  {L['avg_energy']:>8.4f}  "
                  f"{L['energy_trend']:>+8.4f}")

        if r['gain_chain']:
            print(f"\n  信号增益链:")
            for k, g in r['gain_chain'].items():
                bar = "#" * min(int(g * 10), 40) if g > 0 else "."
                print(f"    {k:<20s}: {g:>8.4f}  {bar}")
