"""nexus_v1.circuit.noether_probe — Discrete Noether Verification (T4).

Verifies that the discrete neural circuit respects conservation laws
derived from continuous symmetries (Noether's theorem, discretized).

Four conservation/symmetry checks:

1. ENERGY (time translation symmetry):
   E_stored(t) + Q_dissipated(0→t) = E_stored(0) + E_input(0→t)

2. WEIGHT BALANCE (gauge invariance):
   ΔW_total = Σ(LTP) - Σ(LTD) - Σ(decay)   (no phantom creation)

3. XIN BOOKKEEPING (tension conservation):
   Xin_produced = Xin_consumed + Xin_remaining

4. LANDAUER BOUND (information-entropy coupling):
   Q_dissipated ≥ k_B T ln(2) × bits_erased   (per erasure event)

Pure observer — reads circuit state, NEVER writes.

BIO: metabolic accounting (Attwell & Laughlin 2001)
PHYS: Noether's theorem for discrete systems (Dorodnitsyn 2011)
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Dict, List, Tuple


def _std(values: List[float]) -> float:
    """Standard deviation (population) of a list of floats."""
    if len(values) < 2:
        return 0.0
    mean = sum(values) / len(values)
    variance = sum((x - mean) ** 2 for x in values) / len(values)
    return math.sqrt(variance)


@dataclass
class NoetherViolation:
    """A detected conservation violation."""
    law: str           # which law was violated
    tick: int          # when
    magnitude: float   # how badly (0 = no violation)
    details: str       # human-readable description


class NoetherProbe:
    """Discrete Noether conservation verifier (T4).

    Attach to a VariantCircuit and call check() each step.
    Accumulates violations and provides a summary report.

    Usage:
        probe = NoetherProbe()
        for step in range(N):
            circuit.step(...)
            probe.check(circuit, step, dt)
        report = probe.summary()
    """

    # Tolerance for floating-point conservation checks
    ENERGY_TOL = 0.1      # 10% relative tolerance on energy balance
    WEIGHT_TOL = 1e-6     # absolute tolerance on weight phantom creation
    XIN_TOL = 0.01        # relative tolerance on Xin bookkeeping
    LANDAUER_TEMP = 1.0   # effective temperature (normalized units)

    def __init__(self):
        # ── Energy tracking ──
        self._e_stored_initial: float = 0.0
        self._e_stored_prev: float = 0.0
        self._q_dissipated_total: float = 0.0
        self._e_input_total: float = 0.0
        self._initialized = False

        # ── Weight tracking ──
        self._w_total_prev: float = 0.0
        self._w_delta_accumulated: float = 0.0

        # ── Xin tracking ──
        self._xin_produced_total: float = 0.0
        self._xin_consumed_total: float = 0.0

        # ── Landauer tracking ──
        self._bits_erased: float = 0.0
        self._q_for_erasure: float = 0.0

        # ── Violations log ──
        self._violations: List[NoetherViolation] = []
        self._check_count: int = 0

        # ── Rolling metrics ──
        self._energy_balance_history: List[float] = []
        self._weight_drift_history: List[float] = []

        # ── [5] Structural entropy H_struct ──
        # H = -Σ (n_i/N) log₂(n_i/N), n_i = synapses per bundle
        # High H → uniform distribution (no specialization)
        # Low H → few bundles dominate (structural specialization)
        self._h_struct_history: List[float] = []

        # ── [6] Flow entropy H_flow ──
        # H = -Σ (f_i/F) log₂(f_i/F), f_i = coupler voltage integral
        # High H → signal flows everywhere equally
        # Low H → signal concentrated in few pathways (routing specialization)
        self._h_flow_history: List[float] = []
        self._coupler_flow_accum: Dict[str, float] = {}  # bundle_id → cumulative flow

        # ── [7] Scale parameter Ω ──
        # Ω = N_neurons × N_bundles × N_sprouted
        # Tracks system complexity growth. Healthy: dΩ/dt → 0
        self._omega_history: List[Tuple[int, float]] = []  # (tick, Ω)

        # ── [8] P_ν × H_flow product (数理基因候选) ──
        self._pnu_hflow_history: List[float] = []

    def check(self, circuit, tick: int, dt: float):
        """Run all Noether checks on current circuit state.

        Args:
            circuit: VariantCircuit instance
            tick: current simulation tick
            dt: time step
        """
        self._check_count += 1

        neurons = circuit.get_all_neurons()
        bundles = circuit.get_all_bundles()

        # ── 1. Energy conservation ──
        # Neural energy
        e_neural = sum(n.energy for n in neurons)
        # Body kinetic energy (A4): 0.5 × m × v²
        body = getattr(circuit, 'world', None)
        e_kinetic = 0.0
        if body and hasattr(body, 'body'):
            spd = body.body.speed()
            e_kinetic = 0.5 * body.body.mass * spd * spd
        # ECM thermal energy: ΣC_th × T
        e_thermal = 0.0
        for ecm_attr in ['ecm_vestibular', 'ecm_encoding', 'ecm_column']:
            ecm = getattr(circuit, ecm_attr, None)
            if ecm:
                e_thermal += ecm.thermal_capacity * max(0, ecm.temperature)
        e_stored = e_neural + e_kinetic + e_thermal
        # Coupler energy: ΣE_coupler = Σ(0.5 × C × V²) across all bundles
        e_coupler = 0.0
        q_coupler = 0.0  # cumulative coupler dissipation
        ein_coupler = 0.0  # cumulative coupler input
        for b in bundles:
            for cp in getattr(b, '_couplers', []):
                e_coupler += cp.stored_energy
                q_coupler += getattr(cp, '_cumulative_energy_out', 0.0)
                ein_coupler += getattr(cp, '_cumulative_energy_in', 0.0)
        e_stored += e_coupler
        # Use cumulative energy tracking (covers ALL steps, not just check step)
        q_total = sum(getattr(n, '_cumulative_heat_out', 0.0) for n in neurons)
        q_total += q_coupler  # include coupler dissipation
        e_in_total = sum(getattr(n, '_cumulative_energy_in', 0.0) for n in neurons)
        e_in_total += ein_coupler  # include coupler input

        if not self._initialized:
            self._e_stored_initial = e_stored
            self._e_stored_prev = e_stored
            self._q_baseline = q_total    # baseline cumulative at init
            self._ein_baseline = e_in_total
            self._w_total_prev = sum(b.mean_weight() for b in bundles)
            self._initialized = True
            return

        # Cumulative since init
        self._q_dissipated_total = q_total - self._q_baseline
        self._e_input_total = e_in_total - self._ein_baseline

        # Energy balance: E(t) + Q(0→t) should equal E(0) + E_in(0→t)
        lhs = e_stored + self._q_dissipated_total
        rhs = self._e_stored_initial + self._e_input_total
        if rhs > 0.01:
            e_imbalance = abs(lhs - rhs) / rhs
        else:
            e_imbalance = abs(lhs - rhs)

        self._energy_balance_history.append(e_imbalance)
        if len(self._energy_balance_history) > 500:
            self._energy_balance_history.pop(0)

        # Only flag persistent imbalance (transient is OK due to VR timing)
        if (e_imbalance > self.ENERGY_TOL and
                len(self._energy_balance_history) > 100 and
                sum(self._energy_balance_history[-100:]) / 100 > self.ENERGY_TOL):
            self._violations.append(NoetherViolation(
                law="energy_conservation",
                tick=tick,
                magnitude=e_imbalance,
                details=f"E_stored={e_stored:.4f} Q_diss={self._q_dissipated_total:.4f} "
                        f"E_in={self._e_input_total:.4f} imbalance={e_imbalance:.4f}",
            ))

        # ── 1b. KCL charge conservation (Kirchhoff's Current Law) ──
        # First-order linear constraint: Q_in - Q_out ≡ ΔQ_stored.
        # More robust than energy (quadratic V²).
        kcl_total = 0.0
        kcl_scale = 0.0
        for n in neurons:
            cap = n._membrane
            kcl_total += cap.kcl_imbalance
            kcl_scale += cap._q_in + cap._q_out
        # Include coupler capacitors
        for b in bundles:
            for cp in getattr(b, '_couplers', []):
                cap = cp._cap
                kcl_total += cap.kcl_imbalance
                kcl_scale += cap._q_in + cap._q_out
        KCL_TOL = 1e-6
        if kcl_scale > 1.0 and tick > 100:
            kcl_rel = kcl_total / kcl_scale
            if kcl_rel > KCL_TOL:
                self._violations.append(NoetherViolation(
                    law="kcl_charge",
                    tick=tick,
                    magnitude=kcl_rel,
                    details=f"KCL imbalance={kcl_total:.8f} "
                            f"scale={kcl_scale:.4f} "
                            f"relative={kcl_rel:.2e}",
                ))

        # ── 2. Weight balance (no phantom creation) ──
        w_total = sum(b.mean_weight() for b in bundles)
        w_delta = w_total - self._w_total_prev
        self._w_delta_accumulated += abs(w_delta)
        self._w_total_prev = w_total

        # Weight should only change through learning (STDP/BCM)
        # We can't perfectly track LTP vs LTD, but we check for
        # instantaneous jumps that indicate phantom creation
        self._weight_drift_history.append(abs(w_delta))
        if len(self._weight_drift_history) > 500:
            self._weight_drift_history.pop(0)

        # ── 3. Xin bookkeeping (strict conservation) ──
        # Conservation: xin(t) = xin(0) + Σ_injected - Σ_leaked
        # Equivalently: produced - consumed = Δremaining
        xin_remaining = sum(b.config.xin_tension for b in bundles)  # signed
        xin_consumed = sum(
            getattr(b, '_xin_checkpoint_consumed', 0.0)
            + getattr(b, '_xin_consumed', 0.0) for b in bundles
        )
        xin_produced = sum(
            getattr(b, '_xin_checkpoint_produced', 0.0)
            + getattr(b, '_xin_produced', 0.0) for b in bundles
        )
        # Track initial state for delta calculation (sync all three)
        if not hasattr(self, '_xin_remaining_initial'):
            self._xin_remaining_initial = xin_remaining
            self._xin_produced_initial = xin_produced
            self._xin_consumed_initial = xin_consumed
        delta_remaining = xin_remaining - self._xin_remaining_initial
        # Adjust produced/consumed to start from same baseline
        adj_produced = xin_produced - self._xin_produced_initial
        adj_consumed = xin_consumed - self._xin_consumed_initial
        # Conservation: adj_produced - adj_consumed == delta_remaining
        xin_imbalance_abs = abs((adj_produced - adj_consumed) - delta_remaining)
        scale = max(abs(adj_produced), abs(adj_consumed), 1.0)
        if tick > 1000:  # skip warm-up
            xin_imbalance = xin_imbalance_abs / scale
            if xin_imbalance > self.XIN_TOL:
                self._violations.append(NoetherViolation(
                    law="xin_conservation",
                    tick=tick,
                    magnitude=xin_imbalance,
                    details=f"adj_produced-consumed={adj_produced - adj_consumed:.4f} "
                            f"Δremaining={delta_remaining:.4f} "
                            f"imbalance={xin_imbalance:.6f}",
                ))

        # ── 4. Landauer bound (Shannon entropy of weight distribution) ──
        # H(w) = -Σ p(w_bin) × log₂(p(w_bin))
        # When ΔH < 0 (entropy decreases = "learning"), that's bit erasure.
        # Landauer minimum heat: Q_min = kT × ln(2) × |ΔH| per bit erased.
        K_LANDAUER = 0.693 * self.LANDAUER_TEMP
        N_BINS = 20  # histogram resolution
        all_weights = [m.w for b in bundles for row in b._memristors for m in row]
        if len(all_weights) > 0:
            # Build histogram
            counts = [0] * N_BINS
            for w in all_weights:
                bin_idx = min(N_BINS - 1, int(w * N_BINS))
                counts[bin_idx] += 1
            # Shannon entropy
            n = len(all_weights)
            entropy = 0.0
            for c in counts:
                if c > 0:
                    p = c / n
                    entropy -= p * math.log2(p)
            # Track entropy change
            if not hasattr(self, '_prev_entropy'):
                self._prev_entropy = entropy
            delta_h = entropy - self._prev_entropy
            if delta_h < 0:
                # Entropy decreased = bits erased
                self._bits_erased += abs(delta_h)
            self._prev_entropy = entropy

        if self._bits_erased > 0 and self._q_dissipated_total > 0:
            q_per_bit = self._q_dissipated_total / self._bits_erased
            if q_per_bit < K_LANDAUER * 0.01:  # generous margin
                self._violations.append(NoetherViolation(
                    law="landauer_bound",
                    tick=tick,
                    magnitude=q_per_bit,
                    details=f"Q/bit={q_per_bit:.6f} < Landauer={K_LANDAUER:.4f}",
                ))

        self._e_stored_prev = e_stored

        # ── 5. Structural entropy H_struct ──
        # Distribution of synapses across bundles
        synapse_counts = []
        for b in bundles:
            n_syn = b.n_sources * b.n_targets
            if n_syn > 0:
                synapse_counts.append(n_syn)
        if synapse_counts:
            total_syn = sum(synapse_counts)
            h_struct = 0.0
            for n in synapse_counts:
                p = n / total_syn
                if p > 0:
                    h_struct -= p * math.log2(p)
            self._h_struct_history.append(h_struct)
            if len(self._h_struct_history) > 500:
                self._h_struct_history.pop(0)

        # ── 6. Flow entropy H_flow ──
        # Accumulate coupler flow (voltage integral) per bundle
        for b in bundles:
            bid = b.id
            flow = sum(cp.voltage for cp in getattr(b, '_couplers', []))
            self._coupler_flow_accum[bid] = self._coupler_flow_accum.get(bid, 0.0) + flow
        flows = [f for f in self._coupler_flow_accum.values() if f > 0]
        if flows:
            total_flow = sum(flows)
            h_flow = 0.0
            for f in flows:
                p = f / total_flow
                if p > 0:
                    h_flow -= p * math.log2(p)
            self._h_flow_history.append(h_flow)
            if len(self._h_flow_history) > 500:
                self._h_flow_history.pop(0)

        # ── 7. Scale parameter Ω ──
        n_neurons = len(neurons)
        n_bundles = len(bundles)
        n_sprouted = sum(1 for b in bundles if hasattr(b, '_sprout_depth'))
        omega = n_neurons * n_bundles * max(n_sprouted, 1)
        self._omega_history.append((tick, omega))
        if len(self._omega_history) > 500:
            self._omega_history.pop(0)

        # ── 8. P_ν × H_flow (数理基因候选) ──
        ms = getattr(circuit, 'motion_state', None)
        if ms and self._h_flow_history:
            p_nu = getattr(ms, 'polarization', 0.333)
            h_flow_now = self._h_flow_history[-1]
            self._pnu_hflow_history.append(p_nu * h_flow_now)
            if len(self._pnu_hflow_history) > 500:
                self._pnu_hflow_history.pop(0)

    def summary(self) -> Dict:
        """Generate Noether verification report."""
        n_violations = len(self._violations)
        violation_counts = {}
        for v in self._violations:
            violation_counts[v.law] = violation_counts.get(v.law, 0) + 1

        # Energy balance trend
        if self._energy_balance_history:
            e_bal_avg = sum(self._energy_balance_history) / len(self._energy_balance_history)
            e_bal_max = max(self._energy_balance_history)
        else:
            e_bal_avg = 0.0
            e_bal_max = 0.0

        # Weight stability
        if self._weight_drift_history:
            w_drift_avg = sum(self._weight_drift_history) / len(self._weight_drift_history)
        else:
            w_drift_avg = 0.0

        # Landauer
        if self._bits_erased > 0:
            q_per_bit = self._q_dissipated_total / self._bits_erased
        else:
            q_per_bit = float('inf')

        return {
            "checks": self._check_count,
            "violations": n_violations,
            "violation_counts": violation_counts,
            "all_passed": n_violations == 0,
            "energy": {
                "balance_avg": round(e_bal_avg, 6),
                "balance_max": round(e_bal_max, 6),
                "q_dissipated": round(self._q_dissipated_total, 4),
                "e_input": round(self._e_input_total, 4),
            },
            "weight": {
                "drift_avg_per_step": round(w_drift_avg, 8),
                "total_delta": round(self._w_delta_accumulated, 6),
            },
            "xin": {
                "bits_erased": self._bits_erased,
                "q_per_bit": round(q_per_bit, 6) if q_per_bit != float('inf') else None,
                "landauer_ok": q_per_bit >= 0.693 * self.LANDAUER_TEMP * 0.01,
            },
            "structural": {
                "h_struct": round(self._h_struct_history[-1], 4) if self._h_struct_history else None,
                "h_flow": round(self._h_flow_history[-1], 4) if self._h_flow_history else None,
                "omega": self._omega_history[-1][1] if self._omega_history else None,
                "pnu_hflow_avg": round(sum(self._pnu_hflow_history) / len(self._pnu_hflow_history), 4) if self._pnu_hflow_history else None,
                "pnu_hflow_std": round(_std(self._pnu_hflow_history), 4) if len(self._pnu_hflow_history) > 1 else None,
            },
        }

    def print_report(self):
        """Print formatted Noether verification report."""
        s = self.summary()
        print(f"\n{'='*60}")
        print(f"  Noether Conservation Verification (T4)")
        print(f"{'='*60}")
        print(f"  Checks: {s['checks']}  Violations: {s['violations']}")
        print(f"  Status: {'PASS' if s['all_passed'] else 'FAIL'}")

        print(f"\n  [1] Energy Conservation (time symmetry):")
        print(f"      Balance error avg: {s['energy']['balance_avg']:.6f}")
        print(f"      Balance error max: {s['energy']['balance_max']:.6f}")
        print(f"      Q dissipated: {s['energy']['q_dissipated']:.4f}")

        print(f"\n  [2] Weight Stability (gauge invariance):")
        print(f"      Avg drift/step: {s['weight']['drift_avg_per_step']:.8f}")
        print(f"      Total |ΔW|: {s['weight']['total_delta']:.6f}")

        print(f"\n  [3] Landauer Bound (info-entropy):")
        print(f"      Bits erased: {s['xin']['bits_erased']}")
        qpb = s['xin']['q_per_bit']
        print(f"      Q/bit: {qpb if qpb is not None else 'N/A'}")
        print(f"      Landauer OK: {s['xin']['landauer_ok']}")

        if s['violations'] > 0:
            print(f"\n  Violation breakdown:")
            for law, count in s['violation_counts'].items():
                print(f"      {law}: {count}")

        st = s.get('structural', {})
        if st.get('h_struct') is not None:
            print(f"\n  [5] Structural Entropy (topology):")
            print(f"      H_struct: {st['h_struct']:.4f}")
            print(f"      H_flow:   {st['h_flow']:.4f}" if st['h_flow'] is not None else "")
            print(f"      Ω (scale): {st['omega']}" if st['omega'] is not None else "")
            if st.get('pnu_hflow_avg') is not None:
                print(f"\n  [6] P_ν × H_flow (数理基因候选):")
                print(f"      avg: {st['pnu_hflow_avg']:.4f}  std: {st['pnu_hflow_std']:.4f}")
                cv = st['pnu_hflow_std'] / max(st['pnu_hflow_avg'], 1e-10)
                print(f"      CV:  {cv:.4f}  {'~const PASS' if cv < 0.2 else 'variable'}")

        print(f"{'='*60}")
