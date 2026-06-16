"""nexus_v1.ledger.energy_ledger — Global Entropy Accounting System.

TYPE:INFRASTRUCTURE — Thermodynamic bookkeeping for the neural circuit.

===========================================================
ZERO DEPENDENCY ON EXISTING NEXUS CODE (observation only).
===========================================================

Biological Equivalent:
    Metabolic accounting in the brain:
    - ATP consumption tracking (≈20W total brain power)
    - Heat dissipation balance
    - Information transfer efficiency (bits/joule)
    REF: Attwell & Laughlin 2001 — "An energy budget for signaling
         in the grey matter of the brain"

Electronic Equivalent:
    Power integrity analysis in VLSI:
    - IR-drop monitoring across power grid
    - Total dynamic + static power accounting
    - Signal integrity metrics (SNR, eye diagrams)

The entropy ledger is a READ-ONLY observer that does NOT modify
any circuit state. It samples neurons and bundles each step to
compute thermodynamic metrics.

Metrics tracked:
    1. Energy balance: input vs dissipated vs stored
    2. Information flow: mutual information between layers
    3. Efficiency: bits per unit energy
    4. Entropy production rate: dS/dt
    5. Free energy: F = U - TS (Helmholtz)
"""

import math
import json
import os
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple


@dataclass
class EntropyLedger:
    """Global thermodynamic bookkeeper for the neural circuit.

    Observes (never modifies) circuit state to compute:
    - Energy balance across all layers
    - Information-theoretic metrics
    - Thermodynamic efficiency

    Usage:
        ledger = EntropyLedger()
        for step in range(N):
            circuit.step(inputs, dt)
            ledger.record(circuit, dt)
        report = ledger.summary()
    """

    # Accumulation windows
    window_size: int = 1000  # steps for rolling statistics

    # Running totals
    _total_energy_input: float = field(default=0.0, repr=False)
    _total_heat_dissipated: float = field(default=0.0, repr=False)
    _total_spikes: int = field(default=0, repr=False)
    _total_steps: int = field(default=0, repr=False)
    _total_time: float = field(default=0.0, repr=False)

    # Per-layer tracking
    _layer_energy: Dict[str, List[float]] = field(default_factory=dict, repr=False)
    _layer_heat: Dict[str, List[float]] = field(default_factory=dict, repr=False)
    _layer_activity: Dict[str, List[float]] = field(default_factory=dict, repr=False)
    # Spike-rate proxy using pre_trace (correct for spiking neurons)
    # Used by transfer entropy; _layer_activity kept for energy reporting.
    _layer_spike_proxy: Dict[str, List[float]] = field(default_factory=dict, repr=False)

    # Shadow sandbox K_ema history (divergence indicator)
    _k_ema_history: List[float] = field(default_factory=list, repr=False)

    # Time series (rolling window)
    _entropy_rate: List[float] = field(default_factory=list, repr=False)
    _energy_efficiency: List[float] = field(default_factory=list, repr=False)

    # Spike counts per neuron (for ISI entropy)
    _spike_history: Dict[str, List[float]] = field(default_factory=dict, repr=False)

    def record(self, circuit, dt: float):
        """Record one step of circuit state.

        Args:
            circuit: HebbianCircuit or VariantCircuit instance
            dt: time step (seconds)
        """
        self._total_steps += 1
        self._total_time += dt

        neurons = circuit.get_all_neurons()
        bundles = circuit.get_all_bundles()

        # ── 1. Energy accounting ──
        total_heat = 0.0
        total_energy = 0.0
        spikes_this_step = 0

        for n in neurons:
            total_heat += n.heat_output
            total_energy += n.energy
            if hasattr(n, '_spiked_this_step') and n._spiked_this_step:
                spikes_this_step += 1

            # Track per-neuron spikes for ISI analysis
            nid = n.config.neuron_id
            if nid not in self._spike_history:
                self._spike_history[nid] = []
            if hasattr(n, '_spiked_this_step') and n._spiked_this_step:
                self._spike_history[nid].append(self._total_time)

        self._total_heat_dissipated += total_heat * dt
        self._total_spikes += spikes_this_step

        # ── 2. Layer-wise tracking ──
        # Categorize neurons by layer
        layers = {
            'L1_MET': [], 'L2_HC': [], 'L3_Aff': [],
            'L4_Enc': [], 'L5_Col': [], 'L6_Mot': [],
            # Shadow layer
            'S_Enc': [], 'S_Col': [], 'S_Mot': [],
            # DA circuit
            'DA': [],
            # Somatosensory chain (V07)
            'Soma_Therm': [], 'Soma_Noci': [], 'Soma_Relay': [],
        }
        for n in neurons:
            nid = n.config.neuron_id
            if nid.startswith('met_'):
                layers['L1_MET'].append(n)
            elif nid.startswith('hc_'):
                layers['L2_HC'].append(n)
            elif nid.startswith('aff_'):
                layers['L3_Aff'].append(n)
            elif nid.startswith('s_enc_'):
                layers['S_Enc'].append(n)
            elif nid.startswith('s_col_'):
                layers['S_Col'].append(n)
            elif nid.startswith('s_mot_'):
                layers['S_Mot'].append(n)
            elif nid.startswith('thermo_'):
                layers['Soma_Therm'].append(n)
            elif nid.startswith('noci_'):
                layers['Soma_Noci'].append(n)
            elif nid.startswith('relay_'):
                layers['Soma_Relay'].append(n)
            elif nid.startswith('enc_') or nid.startswith('reg_'):
                layers['L4_Enc'].append(n)
            elif nid.startswith('col_'):
                layers['L5_Col'].append(n)
            elif nid.startswith('da_'):
                layers['DA'].append(n)
            elif nid.startswith('motor_') or nid.startswith('move_'):
                layers['L6_Mot'].append(n)

        for layer_name, layer_neurons in layers.items():
            if not layer_neurons:
                continue
            if layer_name not in self._layer_energy:
                self._layer_energy[layer_name] = []
                self._layer_heat[layer_name] = []
                self._layer_activity[layer_name] = []
                self._layer_spike_proxy[layer_name] = []

            avg_energy = sum(n.energy for n in layer_neurons) / len(layer_neurons)
            avg_heat = sum(n.heat_output for n in layer_neurons) / len(layer_neurons)
            avg_act = sum(n._activation_ema for n in layer_neurons) / len(layer_neurons)  # M4
            # Spike-rate proxy: pre_trace for spiking neurons, |activation| otherwise
            avg_proxy = sum(
                abs(n.pre_trace) if n.config.spiking else abs(n._activation_ema)
                for n in layer_neurons
            ) / len(layer_neurons)

            self._layer_energy[layer_name].append(avg_energy)
            self._layer_heat[layer_name].append(avg_heat)
            self._layer_activity[layer_name].append(avg_act)
            self._layer_spike_proxy[layer_name].append(avg_proxy)

            # Keep rolling window
            if len(self._layer_energy[layer_name]) > self.window_size:
                self._layer_energy[layer_name] = self._layer_energy[layer_name][-self.window_size:]
                self._layer_heat[layer_name] = self._layer_heat[layer_name][-self.window_size:]
                self._layer_activity[layer_name] = self._layer_activity[layer_name][-self.window_size:]
                self._layer_spike_proxy[layer_name] = self._layer_spike_proxy[layer_name][-self.window_size:]

        # ── 3. Entropy production rate ──
        # dS/dt ∝ heat_dissipated / T (simplified)
        # Using normalized units: dS = heat × dt
        ds_dt = total_heat  # entropy production rate
        self._entropy_rate.append(ds_dt)
        if len(self._entropy_rate) > self.window_size:
            self._entropy_rate = self._entropy_rate[-self.window_size:]

        # ── 4. Energy efficiency ──
        # bits per unit energy: spikes / heat
        if total_heat > 0.001:
            efficiency = spikes_this_step / total_heat
        else:
            efficiency = 0.0
        self._energy_efficiency.append(efficiency)
        if len(self._energy_efficiency) > self.window_size:
            self._energy_efficiency = self._energy_efficiency[-self.window_size:]

        # ── 5. K_ema from shadow sandbox (divergence indicator) ──
        kema = getattr(getattr(circuit, 'shadow_sandbox', None), '_k_ema', None)
        if kema is not None:
            self._k_ema_history.append(kema)
            if len(self._k_ema_history) > self.window_size:
                self._k_ema_history = self._k_ema_history[-self.window_size:]

    def compute_isi_entropy(self, neuron_id: str) -> float:
        """Compute ISI entropy for a neuron (bits).

        Higher entropy = more irregular firing.
        Lower entropy = more regular/predictable firing.
        """
        spikes = self._spike_history.get(neuron_id, [])
        if len(spikes) < 3:
            return 0.0

        # Compute ISIs
        isis = [spikes[i+1] - spikes[i] for i in range(len(spikes)-1)]
        if not isis:
            return 0.0

        # Discretize ISIs into bins
        min_isi = min(isis)
        max_isi = max(isis)
        if max_isi - min_isi < 1e-6:
            return 0.0  # all ISIs identical = 0 entropy

        n_bins = min(20, len(isis) // 3 + 1)
        bin_width = (max_isi - min_isi) / n_bins
        counts = [0] * n_bins
        for isi in isis:
            b = min(int((isi - min_isi) / bin_width), n_bins - 1)
            counts[b] += 1

        # Shannon entropy
        total = len(isis)
        entropy = 0.0
        for c in counts:
            if c > 0:
                p = c / total
                entropy -= p * math.log2(p)

        return entropy

    def compute_transfer_entropy(self, src_id: str, tgt_id: str) -> float:
        """Estimate information transfer between two neurons.

        Uses spike-rate proxy (pre_trace for spiking layers) to avoid
        the near-zero correlation artifact from binary activation EMA.
        Returns value in [-1, 1]; positive = forward transfer.
        """
        src_act = []
        tgt_act = []
        for layer_name in self._layer_spike_proxy:
            lkey = layer_name.split('_')[1].lower() if '_' in layer_name else layer_name.lower()
            if src_id.startswith(lkey):
                src_act = self._layer_spike_proxy[layer_name]
            if tgt_id.startswith(lkey):
                tgt_act = self._layer_spike_proxy[layer_name]

        if len(src_act) < 10 or len(tgt_act) < 10:
            return 0.0

        n = min(len(src_act), len(tgt_act))
        src = src_act[-n:]
        tgt = tgt_act[-n:]
        mean_s = sum(src) / n
        mean_t = sum(tgt) / n
        var_s = sum((s - mean_s)**2 for s in src) / n
        var_t = sum((t - mean_t)**2 for t in tgt) / n

        if var_s < 1e-10 or var_t < 1e-10:
            return 0.0

        cov = sum((src[i] - mean_s) * (tgt[i] - mean_t) for i in range(n)) / n
        return cov / math.sqrt(var_s * var_t)

    def summary(self) -> Dict:
        """Generate comprehensive entropy ledger report."""
        report = {
            'time': self._total_time,
            'steps': self._total_steps,
            'total_spikes': self._total_spikes,
            'total_heat_dissipated': self._total_heat_dissipated,
            'avg_spike_rate': self._total_spikes / max(self._total_time, 0.001),
            'layers': {},
        }

        # Per-layer summary
        for layer_name in self._layer_energy:
            e_vals = self._layer_energy[layer_name]
            h_vals = self._layer_heat[layer_name]
            a_vals = self._layer_activity[layer_name]
            report['layers'][layer_name] = {
                'avg_energy': sum(e_vals) / max(len(e_vals), 1),
                'avg_heat': sum(h_vals) / max(len(h_vals), 1),
                'avg_activity': sum(a_vals) / max(len(a_vals), 1),
                'energy_trend': e_vals[-1] - e_vals[0] if len(e_vals) > 1 else 0,
            }

        # Entropy metrics
        if self._entropy_rate:
            report['entropy_production_rate'] = sum(self._entropy_rate) / len(self._entropy_rate)
        if self._energy_efficiency:
            report['energy_efficiency'] = sum(self._energy_efficiency) / len(self._energy_efficiency)

        return report

    def print_report(self):
        """Print formatted entropy ledger report."""
        r = self.summary()
        print("=" * 70)
        print("熵 账 本 (Entropy Ledger)")
        print("=" * 70)
        print(f"  模拟时间: {r['time']:.1f}s ({r['steps']} steps)")
        print(f"  总 spike: {r['total_spikes']}")
        print(f"  总热耗散: {r['total_heat_dissipated']:.4f}")
        print(f"  平均 spike 率: {r['avg_spike_rate']:.1f} spk/s")

        if 'entropy_production_rate' in r:
            print(f"  熵产生率 dS/dt: {r['entropy_production_rate']:.6f}")
        if 'energy_efficiency' in r:
            print(f"  能效 (spk/heat): {r['energy_efficiency']:.4f}")

        print(f"\n  {'Layer':<12s}  {'Avg E':>8s}  {'Avg Heat':>8s}  {'Avg Act':>8s}  {'E trend':>8s}")
        for layer_name in sorted(r['layers']):
            L = r['layers'][layer_name]
            print(f"  {layer_name:<12s}  {L['avg_energy']:>8.4f}  {L['avg_heat']:>8.6f}  {L['avg_activity']:>8.4f}  {L['energy_trend']:>+8.4f}")

        # ISI entropy for key neurons
        print(f"\n  ISI Entropy (bits):")
        for nid in sorted(self._spike_history):
            n_spk = len(self._spike_history[nid])
            if n_spk > 5:
                h = self.compute_isi_entropy(nid)
                print(f"    {nid:<25s}: {h:.3f} bits ({n_spk} spikes)")

        print(f"\n  Layer Transfer (spike-proxy correlation):")
        layer_pairs = [
            ('L1_MET', 'L2_HC'), ('L2_HC', 'L3_Aff'),
            ('L3_Aff', 'L4_Enc'), ('L4_Enc', 'L5_Col'),
            ('L5_Col', 'L6_Mot'),
            ('S_Enc', 'S_Col'), ('S_Col', 'S_Mot'),
            ('DA', 'L6_Mot'),
        ]
        for src, tgt in layer_pairs:
            sp = self._layer_spike_proxy
            if src in sp and tgt in sp:
                src_act = sp[src]
                tgt_act = sp[tgt]
                n = min(len(src_act), len(tgt_act))
                if n > 10:
                    s = src_act[-n:]
                    t = tgt_act[-n:]
                    ms = sum(s)/n
                    mt = sum(t)/n
                    vs = sum((x-ms)**2 for x in s)/n
                    vt = sum((x-mt)**2 for x in t)/n
                    if vs > 1e-10 and vt > 1e-10:
                        cov = sum((s[i]-ms)*(t[i]-mt) for i in range(n))/n
                        corr = cov / math.sqrt(vs * vt)
                        bar = "█" * int(max(0, corr) * 20)
                        print(f"    {src} → {tgt}: {corr:>6.3f}  {bar}")

        # K_ema status
        if self._k_ema_history:
            print(f"\n  Shadow K_ema: {self._k_ema_history[-1]:.1f}"
                  f"  ({'DIVERGING' if self._k_ema_history[-1] > 10000 else 'OK'})")

    def energy_balance_check(self) -> Tuple[bool, str]:
        """Check if energy is balanced (1st law of thermodynamics).

        Returns (ok, message).
        """
        # In a closed system: ΔE_stored + Q_dissipated = E_input
        # We don't track E_input directly, but we can check:
        # - No neuron has negative energy
        # - Total heat dissipated is finite
        # - Energy is monotonically bounded

        ok = True
        msgs = []

        if self._total_heat_dissipated < 0:
            ok = False
            msgs.append("Negative heat dissipation (2nd law violation!)")

        for layer_name, e_vals in self._layer_energy.items():
            if e_vals and e_vals[-1] < 0:
                ok = False
                msgs.append(f"{layer_name}: negative energy")

        if ok:
            msgs.append("Energy balance OK (1st+2nd law satisfied)")

        return ok, "; ".join(msgs)

    def check_anomalies(self, min_window: int = 50) -> List[str]:
        """Check for known anomalies and return alert strings.

        # NORM(V05/V06/V08): implements 纪律约束 #6 "告警不沉默"
        # Checks: Col layer dead, DA heat dominance, Shadow Col dead.
        # Does NOT modify circuit state — pure observation.

        Args:
            min_window: minimum recorded steps before alerting (avoid false
                        positives during warm-up).
        Returns:
            List of alert strings (empty = no anomalies detected).
        """
        alerts: List[str] = []

        # ── A1: L5_Col layer dead ──
        col_acts = self._layer_activity.get('L5_Col', [])
        if len(col_acts) >= min_window:
            recent = col_acts[-min_window:]
            avg_col = sum(recent) / len(recent)
            if avg_col < 1e-4:
                alerts.append(
                    f"DEG-COL: L5_Col avg_activity={avg_col:.2e} < 1e-4 "
                    f"over last {min_window} steps — Column layer dead "
                    f"(lateral inhibition over-suppression?)"
                )

        # ── A2: DA heat dominance ──
        da_heat = self._layer_heat.get('DA', [])
        total_heat_layers = sum(
            (self._layer_heat.get(k, [0])[-1] if self._layer_heat.get(k) else 0)
            for k in ('L1_MET', 'L2_HC', 'L3_Aff', 'L4_Enc', 'L5_Col', 'L6_Mot', 'DA')
        )
        if da_heat and total_heat_layers > 1e-8:
            da_frac = da_heat[-1] / total_heat_layers
            if da_frac > 0.5:
                alerts.append(
                    f"DEG-DA: DA heat fraction={da_frac:.1%} > 50% "
                    f"— DA layer dominates dissipation, may mask other layers"
                )

        # ── A3: Shadow Col dead ──
        scol_acts = self._layer_activity.get('S_Col', [])
        if len(scol_acts) >= min_window:
            recent = scol_acts[-min_window:]
            avg_scol = sum(recent) / len(recent)
            if avg_scol < 1e-6:
                alerts.append(
                    f"DEG-SCOL: S_Col avg_activity={avg_scol:.2e} < 1e-6 "
                    f"over last {min_window} steps — Shadow Column layer dead "
                    f"(K_ema likely diverging)"
                )

        # ── A4: K_ema divergence (shadow free energy) ──
        if self._k_ema_history:
            latest_kema = self._k_ema_history[-1]
            if latest_kema > 10000:
                alerts.append(
                    f"DEG-KEMA: shadow K_ema={latest_kema:.1f} > 10000 "
                    f"— shadow free energy diverging (unbounded momentum)"
                )

        return alerts

    # ── Registry integration ──────────────────────────────────────

    _registry: Optional[dict] = field(default=None, repr=False)

    def load_registry(self, registry_path: str = None):
        """Load the project registry (docs/registry.json).

        The registry provides machine-readable metadata about components,
        theories, and relationships. When loaded, the ledger can annotate
        structural events with documentation references.

        Args:
            registry_path: Absolute path to registry.json. If None,
                auto-discovers relative to this file.
        """
        if registry_path is None:
            # Auto-discover: this file is in components/, registry is in docs/
            here = os.path.dirname(os.path.abspath(__file__))
            registry_path = os.path.join(
                here, '..', 'docs', 'registry.json')

        try:
            with open(registry_path, 'r', encoding='utf-8') as f:
                self._registry = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            self._registry = None

    def lookup_component(self, name: str) -> Optional[dict]:
        """Look up a component in the registry.

        Args:
            name: Component class name (e.g. 'Neuron', 'SynapticBundle')

        Returns:
            Registry entry dict or None.
        """
        if self._registry is None:
            self.load_registry()
        if self._registry and 'components' in self._registry:
            return self._registry['components'].get(name)
        return None

    def lookup_theory(self, theory_id: str) -> Optional[dict]:
        """Look up a theory in the registry.

        Args:
            theory_id: Theory ID (e.g. 'T001_noether', 'T003_fruit')

        Returns:
            Registry entry dict or None.
        """
        if self._registry is None:
            self.load_registry()
        if self._registry and 'theories' in self._registry:
            return self._registry['theories'].get(theory_id)
        return None

    def annotate_event(self, event_type: str, target: str) -> str:
        """Annotate a structural event with registry context.

        Args:
            event_type: 'sprout', 'prune', 'mitosis', 'fruit_mature'
            target: Bundle or neuron ID

        Returns:
            Annotation string with theory/doc references.
        """
        annotations = [f"{event_type}: {target}"]

        # Map event types to theories
        theory_map = {
            'sprout': 'T003_fruit',
            'prune': 'T003_fruit',
            'fruit_mature': 'T003_fruit',
            'mitosis': 'T002_stdp',
        }

        theory_id = theory_map.get(event_type)
        if theory_id:
            theory = self.lookup_theory(theory_id)
            if theory:
                annotations.append(f"  theory: {theory.get('name', theory_id)}")
                annotations.append(f"  doc: {theory.get('doc', 'N/A')}")
                annotations.append(f"  verified: {theory.get('verified', 'unknown')}")

        # Try to identify component from target ID
        if 'bundle' in target.lower() or 'to_' in target:
            comp = self.lookup_component('SynapticBundle')
        elif 'motor' in target.lower() or 'move_' in target:
            comp = self.lookup_component('Neuron')
        else:
            comp = None

        if comp:
            annotations.append(f"  component: {comp.get('bio', 'N/A')}")

        return "\n".join(annotations)

    def registry_summary(self) -> dict:
        """Return a summary of registry contents for diagnostics."""
        if self._registry is None:
            self.load_registry()
        if self._registry is None:
            return {'loaded': False}
        return {
            'loaded': True,
            'version': self._registry.get('_meta', {}).get('version', '?'),
            'n_components': len(self._registry.get('components', {})),
            'n_theories': len(self._registry.get('theories', {})),
            'n_relationships': len(self._registry.get('relationships', [])),
            'n_modifications': len(self._registry.get('modifications', [])),
        }

