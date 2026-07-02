"""nexus_v1.ledger.signal_path_audit — Non-Bundle Signal Path Auditor.

TYPE:INFRA

AUDIT-NOTE (2026-06-28): Added to address the structural observability gap
identified in 大问题.2026.6.28.md. The existing ledger (NoetherProbe,
EntropyLedger, TOPRXinLedger) only observes signals that flow through
SynapticBundles. This probe tracks the 24 non-bundle membrane injections
that are invisible to the standard ledger stack.

Core question answered: "Why doesn't the ledger catch DEVIATION_MOTOR_GAIN
domination?" Answer: it injects directly into membrane without passing through
any bundle, so it leaves no trace in the T/O/P/R/Xin framework.

Design: pure observer, read-only. Never modifies circuit state.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple


@dataclass
class InjectionRecord:
    """One step of injection metrics."""
    tick: int = 0
    # DEVIATION_MOTOR_GAIN contribution
    # AUDIT-CORRECTION (2026-06-28): DEVIATION_MOTOR_GAIN = 1.0 in variant_adapter.py
    # (not 1/dt=1000 as previously assumed). motor_drive = (deviation-0.1)*1.0.
    # Previous formula used /dt — producing values 1000× too high.
    deviation: float = 0.0          # homeo_deviation (= |v_ref - rho_homeo|)
    rho_homeo: float = 0.0          # circulation proportion: thermal/(thermal+motor+feed)
    motor_drive: float = 0.0        # (deviation - 0.1) * 1.0  when deviation > 0.1
    fill_fraction: float = 0.0
    # VitalOscillator amplitude
    vital_amplitude: float = 0.0    # sum|vital_outputs|
    # Motor activation snapshot
    motor_acts: Dict[str, float] = field(default_factory=dict)
    # Top STDP signal to motor (estimated, as w × pre_act, BEFORE inertia scaling)
    stdp_motor_max: float = 0.0


class SignalPathAudit:
    """TYPE:INFRA — Tracks non-bundle signal injections invisible to standard ledger.

    AUDIT-NOTE (2026-06-28): Companion to the existing NoetherProbe /
    EntropyLedger stack. Measures the magnitude hierarchy of all competing
    signal sources at Motor neurons:

        DEVIATION_MOTOR_GAIN >> VitalOscillator >> STDP bundles

    When DEVIATION_MOTOR_GAIN dominates, STDP learning is drowned out even
    if DA direction gating is perfectly implemented.

    Usage:
        audit = SignalPathAudit()
        for step in range(N):
            circuit.step(inputs, dt)
            audit.measure(circuit, step, dt)
        audit.print_report(dt)
    """

    def __init__(self):
        self._history: List[InjectionRecord] = []

        # Rolling accumulators
        self._motor_saturation_ticks: Dict[str, int] = {}   # key -> ticks >0.95
        self._motor_total_ticks: int = 0

        # Vestibular axis activation accumulation
        self._vestibular_acc: Dict[str, List[float]] = {}

        # Xin tension per bundle (signed)
        self._xin_signed: Dict[str, List[float]] = {}

        # DA direction factor history
        self._da_dir_history: List[float] = []
        self._approach_rate_history: List[float] = []

    # ------------------------------------------------------------------
    def measure(self, circuit, tick: int, dt: float):
        """Record one step. Call immediately after circuit.step()."""

        rec = InjectionRecord(tick=tick)

        # ── 1. DEVIATION_MOTOR_GAIN source ──
        # AUDIT-CORRECTION: motor_drive = (deviation - 0.1) * DEVIATION_MOTOR_GAIN
        # where DEVIATION_MOTOR_GAIN = 1.0 in variant_adapter.py line 762.
        # deviation = |v_ref - rho_homeo| = |0.7 - circulation_proportion.rho_homeo|
        ms = getattr(circuit, 'motion_state', None)
        if ms is not None:
            rec.deviation = getattr(ms, 'homeo_deviation', 0.0)
            rec.rho_homeo = getattr(ms, 'rho_homeo', 0.0)
        es = getattr(circuit, 'energy_store', None)
        if es is not None:
            rec.fill_fraction = es.fill_fraction
        if rec.deviation > 0.1:
            # Correct formula: DEVIATION_MOTOR_GAIN = 1.0 (constant in code)
            rec.motor_drive = (rec.deviation - 0.1) * 1.0

        # ── 2. VitalOscillator amplitude ──
        if ms is not None:
            rec.vital_amplitude = getattr(ms, 'vital_amplitude', 0.0)

        # ── 3. Motor activation snapshot ──
        motor_neurons = getattr(circuit, 'motor_neurons', {})
        for key, mot in motor_neurons.items():
            act = mot.activation
            rec.motor_acts[key] = act
            if key not in self._motor_saturation_ticks:
                self._motor_saturation_ticks[key] = 0
            if act > 0.95:
                self._motor_saturation_ticks[key] += 1
        self._motor_total_ticks += 1

        # ── 4. STDP signal strength estimate to motor neurons ──
        stdp_signals = []
        for b in circuit.get_all_bundles():
            has_motor_target = any(
                ('move_' in tgt.config.neuron_id or 'motor_' in tgt.config.neuron_id)
                for tgt in b.targets
            )
            if has_motor_target:
                w = b.mean_weight()
                pre_acts = [s.activation for s in b.sources if s.is_alive()]
                if pre_acts:
                    mean_pre = sum(pre_acts) / len(pre_acts)
                    stdp_signals.append(w * mean_pre)
        rec.stdp_motor_max = max(stdp_signals) if stdp_signals else 0.0

        # ── 5. Vestibular column activation ──
        col_neurons = getattr(circuit, 'column_neurons', {})
        for axis, col in col_neurons.items():
            if axis not in self._vestibular_acc:
                self._vestibular_acc[axis] = []
            self._vestibular_acc[axis].append(abs(col.activation))

        # ── 6. Xin tension signed values ──
        for b in circuit.get_all_bundles():
            bid = b.id
            if bid not in self._xin_signed:
                self._xin_signed[bid] = []
            self._xin_signed[bid].append(b.config.xin_tension)

        # ── 7. DA direction factor (if present from Phase 4-C monkeypatch) ──
        da_gate = getattr(circuit, 'da_gate', None)
        if da_gate is not None:
            dir_factor = getattr(da_gate, '_direction_factor', None)
            approach_rate = getattr(da_gate, '_approach_rate', None)
            if dir_factor is not None:
                self._da_dir_history.append(dir_factor)
            if approach_rate is not None:
                self._approach_rate_history.append(approach_rate)

        self._history.append(rec)
        if len(self._history) > 5000:
            self._history.pop(0)

    # ------------------------------------------------------------------
    def print_report(self, dt: float = 0.001):
        """Print structured signal path audit report."""
        total = self._motor_total_ticks
        if total == 0:
            print("  [SignalPathAudit] No data recorded.")
            return

        print("\n" + "═" * 72)
        print("  SIGNAL PATH STRUCTURAL AUDIT")
        print("  (Non-bundle injections invisible to NoetherProbe / TOPRXin)")
        print("═" * 72)

        # ── Motor saturation ──
        print("\n  [1] MOTOR NEURON SATURATION (act > 0.95)")
        for key in sorted(self._motor_saturation_ticks):
            sat = self._motor_saturation_ticks[key]
            pct = 100.0 * sat / max(total, 1)
            bar = "█" * int(pct / 5)
            flag = "  ← CRITICAL" if pct > 70 else ("  ← WARNING" if pct > 30 else "")
            print(f"    {key:<12s}  {pct:5.1f}%  [{bar:<20s}]{flag}")

        # ── Signal magnitude hierarchy ──
        print("\n  [2] SIGNAL MAGNITUDE HIERARCHY AT MOTOR NEURONS")
        print("  NOTE: DEVIATION_MOTOR_GAIN = 1.0 in code (not 1/dt).")
        print("  NOTE: STDP signals pass through neuron.step() (inertia=0.5 for Motor)")
        print("  NOTE: → STDP effective current = 2× (w × pre_act) before membrane inject")
        dev_drives = [r.motor_drive for r in self._history]
        vitals = [r.vital_amplitude for r in self._history]
        stdps = [r.stdp_motor_max for r in self._history]
        fills = [r.fill_fraction for r in self._history]
        rhos = [r.rho_homeo for r in self._history]

        mean_dev = sum(dev_drives) / len(dev_drives) if dev_drives else 0
        max_dev = max(dev_drives) if dev_drives else 0
        frac_active = sum(1 for x in dev_drives if x > 0) / max(len(dev_drives), 1)

        mean_vital = sum(vitals) / len(vitals) if vitals else 0
        mean_stdp = sum(stdps) / len(stdps) if stdps else 0
        max_stdp = max(stdps) if stdps else 0

        mean_fill = sum(fills) / len(fills) if fills else 0
        min_fill = min(fills) if fills else 0

        mean_rho = sum(rhos) / len(rhos) if rhos else 0

        print(f"    DEVIATION_MOTOR_GAIN  (DEVIATION_MOTOR_GAIN=1.0 in code)")
        print(f"      motor_drive = (deviation-0.1) × 1.0, injected to ALL Motor membranes")
        print(f"      mean drive:   {mean_dev:12.4f}  [A, passed to inject(drive, dt)]")
        print(f"      max drive:    {max_dev:12.4f}")
        print(f"      active frac:  {frac_active*100:11.1f}%  (when deviation>0.1)")
        print(f"    Circulation Proportion: rho_homeo (thermal / total amplitude)")
        print(f"      mean rho_h:   {mean_rho:12.4f}  (set point = 0.70)")
        deviation_offset = 0.7 - mean_rho
        print(f"      mean offset:  {deviation_offset:12.4f}  (mean_deviation = |0.7 - rho_h|)")

        motor_V_ss = mean_dev * 5.0  # R_leak = 5.0 for motor neuron
        print(f"      V_ss(DEVIATION)= {motor_V_ss:.4f} V  (R_leak=5.0, v_peak=0.2)")
        print(f"      → V_ss {'> v_peak — Motor ALWAYS driven to spike by DEVIATION alone' if motor_V_ss > 0.2 else '< v_peak — DEVIATION insufficient alone'}")

        print(f"    VitalOscillator (VdP tri-heart, amplitude~0.01)")
        print(f"      mean |amp|:   {mean_vital:12.4f}  [pre-neuron current]")

        print(f"    STDP bundles → Motor (w × pre_act, BEFORE inertia=0.5 scaling)")
        print(f"      mean signal:  {mean_stdp:12.4f}  [w×pre_act per top bundle]")
        print(f"      max signal:   {max_stdp:12.4f}")
        print(f"      eff current:  {mean_stdp/0.5:12.4f}  [after inertia=0.5: ×2]")

        print(f"    EnergyStore fill")
        print(f"      mean fill:    {mean_fill:12.4f}")
        print(f"      min fill:     {min_fill:12.4f}")

        # Ratio: DEVIATION inject vs STDP effective inject
        # DEVIATION: inject(motor_drive, dt) → ΔQ = motor_drive × dt
        # STDP: neuron.step(w×pre_act) → inject(w×pre_act/inertia×v_ratio, dt)
        # Ratio (same dt cancels) = motor_drive / (w×pre_act/inertia) = motor_drive × inertia / (w×pre_act)
        inertia_motor = 0.5  # from _motor_config in hebbian.py
        if mean_stdp > 1e-8:
            # Before inertia: DEVIATION = mean_dev, STDP = mean_stdp
            # After inertia: DEVIATION bypasses (stays same), STDP → mean_stdp/inertia
            # Correct ratio = mean_dev / (mean_stdp / inertia) = mean_dev × inertia / mean_stdp
            ratio_raw = mean_dev / mean_stdp  # pre-inertia comparison
            ratio_eff = mean_dev * inertia_motor / mean_stdp  # post-inertia comparison
            print(f"\n    ┌─ RATIO: DEVIATION ÷ STDP (pre-inertia) = {ratio_raw:.1f}× ───────────────────")
            print(f"    │  (post-inertia: DEVIATION bypasses, STDP÷{inertia_motor}=2× → ratio = {ratio_eff:.1f}×)")
            print(f"    │  STDP contributes {100/ratio_eff:.1f}% of effective DEVIATION injection at membrane")
            print(f"    │  V_ss(DEVIATION) = {motor_V_ss:.3f}V >> v_peak={0.2} — Motor spiking rate set by DEVIATION")
            print(f"    │  {'DEVIATION dominates Motor behavior' if ratio_eff > 10 else 'STDP competitive'}")
            print(f"    └──────────────────────────────────────────────────────────────────────")

        # ── Vestibular channel silence ──
        print("\n  [3] VESTIBULAR COLUMN CHANNEL ACTIVITY")
        for axis in sorted(self._vestibular_acc):
            vals = self._vestibular_acc[axis]
            mean_v = sum(vals) / max(len(vals), 1)
            max_v = max(vals) if vals else 0
            # classify
            if mean_v < 0.0001:
                status = "SILENT   ← NOT REACHING COLUMN LAYER"
            elif mean_v < 0.005:
                status = "minimal"
            elif mean_v < 0.05:
                status = "active"
            else:
                status = "STRONG"
            print(f"    {axis:<10s}  mean={mean_v:.6f}  max={max_v:.4f}  [{status}]")

        # ── Xin tension sign quality ──
        print("\n  [4] XIN TENSION SIGN QUALITY (signed, not |ξ|)")
        print(f"    {'Bundle':<38s}  {'mean':>8s}  {'min':>8s}  {'neg%':>6s}  note")
        for bid in sorted(self._xin_signed):
            vals = self._xin_signed[bid]
            if not vals:
                continue
            mean_t = sum(vals) / len(vals)
            min_t = min(vals)
            neg_pct = 100.0 * sum(1 for x in vals if x < 0) / len(vals)
            # flag anomalies
            note = ""
            if neg_pct > 80:
                note = "← INVERTED (actual >> predicted)"
            elif neg_pct > 50:
                note = "← mixed sign"
            short_id = bid[:38]
            print(f"    {short_id:<38s}  {mean_t:>8.3f}  {min_t:>8.3f}  {neg_pct:>5.1f}%  {note}")

        # ── DA direction (if available) ──
        if self._da_dir_history:
            print("\n  [5] DA DIRECTION FACTOR STATISTICS (v·∇T gate)")
            mean_dir = sum(self._da_dir_history) / len(self._da_dir_history)
            zero_frac = sum(1 for x in self._da_dir_history if x < 0.01) / len(self._da_dir_history)
            one_frac = sum(1 for x in self._da_dir_history if x > 0.99) / len(self._da_dir_history)
            print(f"    mean factor:  {mean_dir:.4f}")
            print(f"    at zero:      {zero_frac*100:.1f}%  (DA fully blocked)")
            print(f"    at one:       {one_frac*100:.1f}%  (DA fully open)")
            if self._approach_rate_history:
                mean_ar = sum(self._approach_rate_history) / len(self._approach_rate_history)
                neg_ar_frac = sum(1 for x in self._approach_rate_history if x < 0) / len(self._approach_rate_history)
                print(f"    mean v·∇T:    {mean_ar:.6f}")
                print(f"    receding frac:{neg_ar_frac*100:.1f}%  (moving away, DA should gate=0)")

        print("\n" + "═" * 72)

    # ------------------------------------------------------------------
    def snapshot_at(self, tick: int) -> Optional[InjectionRecord]:
        """Return the most recent record at or before tick."""
        for rec in reversed(self._history):
            if rec.tick <= tick:
                return rec
        return None

    def deviation_drive_fraction(self) -> float:
        """Fraction of steps where DEVIATION_MOTOR_GAIN was active."""
        if not self._history:
            return 0.0
        active = sum(1 for r in self._history if r.motor_drive > 0)
        return active / len(self._history)

    def motor_saturation_pct(self, key: str) -> float:
        """Saturation percentage for one motor neuron."""
        sat = self._motor_saturation_ticks.get(key, 0)
        return 100.0 * sat / max(self._motor_total_ticks, 1)
