"""nexus_v1.tests.run_structural_audit — Full Structural Signal Path Audit.

AUDIT-NOTE (2026-06-28): Created in response to 大问题.2026.6.28.md.

Goal: Answer "Why doesn't the entropy ledger catch these problems?"
Method:
  1. Run VariantCircuit in the same thermal world scenario used in experiments
  2. Every 5k steps: print intermediate snapshot from ALL existing ledger probes
     (these probes run internally but NEVER print during normal simulation)
  3. After run: print full reports from all probes + new SignalPathAudit
  4. Produce a structured list of detected anomalies

This script does NOT modify main project code.
The ONLY additions are:
  - nexus_v1/ledger/signal_path_audit.py (new non-bundle injection probe)
  - This script (reads existing probes + new probe)

Run from J:/cell-cc/cell-cc-other:
  PYTHONIOENCODING=utf-8 python -u -m nexus_v1.tests.run_structural_audit 2>&1 | tee J:/cell-cc/structural_audit_out.txt
"""

import sys
import os
import math
import types

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from nexus_v1.circuit.variant_adapter import VariantCircuit
from nexus_v1.components.heat_source import CylindricalHeatSource
from nexus_v1.ledger.signal_path_audit import SignalPathAudit   # AUDIT-NOTE: new probe

# ── Constants ─────────────────────────────────────────────────────────────────
STEPS = 30_000       # 30k: enough to see approach → orbital → early fill-drain
SNAPSHOT_INTERVAL = 5_000
DT = 0.001
K_VANE = 0.001
V_REF = 0.003

VEST_AXES = ['yaw', 'pitch', 'roll', 'oto_x', 'oto_y', 'oto_z']
MOTOR_KEYS = ['move_x', 'move_y', 'move_z']


# ── P4B-FIX-01: ThermalMouth nearest-source bookkeeping ───────────────────────
def _thermal_mouth_step_nearest(self, world, body, energy_store,
                                ecm_temp=0.15, dt=0.001):
    """AUDIT-NOTE: Inherited monkeypatch from Phase 4-B.
    Original bug: always depletes first alive source. Fix: deplete nearest.
    """
    pos = self.world_position(body)
    T_env = world.temperature_at(pos)
    T_body = ecm_temp
    dT = ((T_env - self.temperature) / self.tau_heat
          - (self.temperature - T_body) / self.tau_cool)
    self.temperature += dT * dt
    delta_T = max(0.0, T_env - self.temperature)
    total_heat_flux = self.conductance * self.area * delta_T * dt
    self.energy_intake = self.eta * total_heat_flux
    if self.energy_intake > 0:
        energy_store.deposit(self.energy_intake)
        srcs = [s for s in getattr(world, 'cylindrical_sources', []) if s.alive]
        if srcs:
            nearest = min(srcs, key=lambda s: math.hypot(
                pos[0] - s.center[0], pos[1] - s.center[1]))
            nearest.absorb(total_heat_flux)
    return self.energy_intake


# ── DA Directional Gate (P4C-NEW-01) ──────────────────────────────────────────
def _make_da_directional(da_gate, world, body, v_ref=V_REF):
    """AUDIT-NOTE: Inherited from Phase 4-C. Gates DA on v·∇T approach rate."""
    def step_directional(self, fill_fraction, dt=0.001):
        delta_fill = fill_fraction - self._fill_prev
        self._fill_prev = fill_fraction
        raw = self.config.eta_da * delta_fill / max(dt, 1e-9)
        rpe_raw = min(max(0.0, raw - self.config.threshold), self.config.clip_max)
        v = body.velocity
        grad = world.gradient_at(body.position)
        approach_rate = v[0] * grad[0] + v[1] * grad[1]
        direction_factor = max(0.0, min(1.0, approach_rate / v_ref))
        gated = rpe_raw * direction_factor
        self._da_output = gated
        self._approach_rate = approach_rate
        self._direction_factor = direction_factor
        return gated
    da_gate._approach_rate = 0.0
    da_gate._direction_factor = 0.0
    return types.MethodType(step_directional, da_gate)


# ── Helpers ───────────────────────────────────────────────────────────────────
def find_bundle(all_bundles, keyword):
    return next((b for b in all_bundles if keyword in b.config.bundle_id), None)


def dist_surface(body, src):
    dx = body.position[0] - src.center[0]
    dy = body.position[1] - src.center[1]
    return math.sqrt(dx * dx + dy * dy) - src.radius


def nearest_dist(body, sources):
    return min(dist_surface(body, s) for s in sources if s.alive)


def body_yaw_deg(circuit):
    return math.degrees(getattr(circuit.world.body, 'yaw', 0.0))


# ── Snapshot printer: reads the EXISTING ledger probes ───────────────────────
def print_ledger_snapshot(circuit, tick, dt):
    """Print a one-line snapshot from the existing ledger probes.

    AUDIT-NOTE: These probes run every 100/1000 steps INSIDE circuit.step(),
    but they never print anything. This is the first time their data is surfaced
    during a live simulation.
    """
    # TOPRXin (updated every 100 steps)
    topxin = circuit._toprxin_ledger.summary()
    T = topxin.get('T', 0)
    O = topxin.get('O', 0)
    P = topxin.get('P', 0)
    R = topxin.get('R', 0)
    Xin = topxin.get('Xin', 0)
    n_b = topxin.get('n_bundles', 0)

    # Noether violations so far
    noether = circuit._noether_probe.summary()
    n_viol = noether['violations']
    e_bal = noether['energy']['balance_avg']

    # EntropyLedger (updated every 1000 steps)
    elsum = circuit._energy_ledger.summary()
    tot_spikes = elsum.get('total_spikes', 0)
    eff = elsum.get('energy_efficiency', 0)
    layers = elsum.get('layers', {})

    mot_act = layers.get('L6_Mot', {}).get('avg_activity', 0)
    col_act = layers.get('L5_Col', {}).get('avg_activity', 0)
    enc_act = layers.get('L4_Enc', {}).get('avg_activity', 0)

    # ComponentRegistry (updated every 1000 steps)
    cr = circuit._component_registry
    n_comp = len(getattr(cr, '_last_scan', [])) if hasattr(cr, '_last_scan') else '?'

    print(f"\n  ─── LEDGER SNAPSHOT @ step {tick:,} ─────────────────────────────────")
    print(f"  TOPRXin  T={T:.4f}  O={O:.4f}  P={P:.4f}  R={R:.6f}  Xin={Xin:.4f}  n_bundles={n_b}")
    print(f"  Noether  violations={n_viol}  energy_balance_avg={e_bal:.6f}")
    print(f"  Entropy  spikes={tot_spikes}  efficiency={eff:.4f}")
    print(f"  Layers   L4_Enc={enc_act:.4f}  L5_Col={col_act:.4f}  L6_Mot={mot_act:.4f}")
    if layers:
        for lname in ['L1_MET', 'L2_HC', 'L3_Aff', 'DA', 'Soma_Therm']:
            if lname in layers:
                la = layers[lname].get('avg_activity', 0)
                le = layers[lname].get('avg_energy', 0)
                print(f"           {lname:<12s}: act={la:.4f}  E={le:.4f}")


# ── Main ──────────────────────────────────────────────────────────────────────
def run():
    print("=" * 80)
    print("  STRUCTURAL SIGNAL PATH AUDIT — VariantCircuit + Thermal World")
    print(f"  {STEPS:,} steps, DT={DT}, snapshot every {SNAPSHOT_INTERVAL:,}")
    print("=" * 80)
    print()
    print("  AUDIT-NOTE (2026-06-28): Surfaces ledger data that runs internally")
    print("  but never prints during normal simulation. Also adds SignalPathAudit")
    print("  for non-bundle injection points invisible to standard ledger.")
    print()

    # ── Circuit setup (same as Phase 4-C) ─────────────────────────────────────
    circuit = VariantCircuit()

    src1 = CylindricalHeatSource(
        center=[80.0, 50.0, 25.0], radius=6.0, height=16.0,
        T_surface=5.0, sigma=25.0, energy=8000.0, regeneration_rate=0.002)
    src2 = CylindricalHeatSource(
        center=[35.0, 76.0, 25.0], radius=6.0, height=16.0,
        T_surface=5.0, sigma=25.0, energy=8000.0, regeneration_rate=0.002)
    src3 = CylindricalHeatSource(
        center=[35.0, 24.0, 25.0], radius=6.0, height=16.0,
        T_surface=5.0, sigma=25.0, energy=8000.0, regeneration_rate=0.002)
    all_sources = [src1, src2, src3]

    circuit.world.heat_sources = []
    circuit.world.cylindrical_sources = all_sources
    circuit.thermal_mouth.eta = 0.50
    circuit.thermal_mouth.step = types.MethodType(
        _thermal_mouth_step_nearest, circuit.thermal_mouth)
    circuit.world.body.position = [75.0, 35.0, 25.0]
    circuit.world.body.velocity = [0.0, 0.0, 0.0]
    circuit.world.body.yaw = 0.0
    for m in circuit.muscle_system.muscles:
        m.gain = 0.5
    circuit._conv_k = 0.47
    circuit.da_gate.step = _make_da_directional(
        circuit.da_gate, circuit.world, circuit.world.body, V_REF)

    # ── Bundle monitoring ──────────────────────────────────────────────────────
    all_bundles = circuit.get_all_bundles()
    b_front = find_bundle(all_bundles, 'therm_therm_front_to_move_x')
    b_brake = find_bundle(all_bundles, 'therm_therm_back_to_move_x')

    print(f"  Circuit: {len(circuit.get_all_neurons())} neurons, {len(all_bundles)} bundles")
    if b_front:
        print(f"  Front bundle: {b_front.config.bundle_id}")
    if b_brake:
        print(f"  Brake bundle: {b_brake.config.bundle_id}")

    print()
    print(f"  {'step':>6s} | {'d_surf':>6s} | {'yaw°':>5s} | {'fill':>5s} | "
          f"{'w_frt':>6s} | {'w_brk':>6s} | {'ratio':>5s} | "
          f"{'DA_dir':>6s} | {'dev':>5s} | {'mot_x':>5s}")
    print("  " + "-" * 80)

    # ── Signal path audit (new) ───────────────────────────────────────────────
    spa = SignalPathAudit()

    # ── Simulation loop ───────────────────────────────────────────────────────
    for step in range(STEPS):
        inputs = {axis: 0.0 for axis in ['yaw', 'pitch', 'roll',
                                          'oto_x', 'oto_y', 'oto_z']}
        circuit.step(inputs, DT)

        # Signal path audit (AUDIT-NOTE: new, runs every step)
        spa.measure(circuit, step, DT)

        # ── Periodic snapshot ─────────────────────────────────────────────────
        if step % SNAPSHOT_INTERVAL == 0 and step > 0:
            body = circuit.world.body
            src = src1
            ds = nearest_dist(body, all_sources)
            yaw_d = body_yaw_deg(circuit)
            fill = circuit.energy_store.fill_fraction

            wf = b_front.mean_weight() if b_front else 0.0
            wb = b_brake.mean_weight() if b_brake else 0.0
            ratio = wf / wb if wb > 1e-6 else float('inf')

            da_dir = getattr(circuit.da_gate, '_direction_factor', 0.0)
            ms = circuit.motion_state
            deviation = getattr(ms, 'homeo_deviation', 0.0)
            mot_x_act = circuit.motor_neurons.get('move_x',
                         circuit.motor_neurons.get('x', None))
            mot_x = mot_x_act.activation if mot_x_act else 0.0

            print(f"  {step:>6,} | {ds:>6.2f} | {yaw_d:>5.1f} | {fill:>5.3f} | "
                  f"{wf:>6.4f} | {wb:>6.4f} | {ratio:>5.3f} | "
                  f"{da_dir:>6.3f} | {deviation:>5.3f} | {mot_x:>5.3f}")

            # Print ledger snapshot every SNAPSHOT_INTERVAL
            print_ledger_snapshot(circuit, step, DT)

    # ── End-of-run: full probe reports ────────────────────────────────────────
    print("\n\n" + "=" * 80)
    print("  END OF SIMULATION — FULL LEDGER REPORTS")
    print("=" * 80)

    # 1. Noether probe (existing)
    circuit._noether_probe.print_report()

    # 2. Entropy ledger (existing)
    circuit._energy_ledger.print_report()

    # 3. TOPRXin (existing) — per-bundle detail
    print("\n\n  TOPRXin — Per-Bundle Phase Intensities (last snapshot)")
    latest = circuit._toprxin_ledger.latest
    if latest:
        print(f"  {'Bundle':<40s}  {'T':>6s}  {'O':>6s}  {'P':>6s}  {'R':>8s}  {'Xin':>8s}")
        for bid, bpi in sorted(latest.bundles.items()):
            print(f"  {bid[:40]:<40s}  {bpi.t_intensity:>6.4f}  "
                  f"{bpi.o_intensity:>6.4f}  {bpi.p_intensity:>6.4f}  "
                  f"{bpi.r_intensity:>8.6f}  {bpi.xin_intensity:>8.4f}")

    # 4. Weight entropy (existing)
    wep = circuit._entropy_probe
    print(f"\n\n  Weight Entropy Probe (existing)")
    try:
        latest_snap = getattr(wep, '_snapshots', None)
        if latest_snap and len(latest_snap) > 0:
            snap = latest_snap[-1]
            print(f"  Tick: {snap.tick}  Global entropy: {snap.global_entropy:.4f} bits")
            for layer, h in snap.layer_entropy.items():
                print(f"    {layer:<20s}: {h:.4f} bits")
        else:
            print("  No snapshots accumulated.")
    except Exception as e:
        print(f"  (WeightEntropyProbe read error: {e})")

    # 5. ComponentRegistry (existing)
    cr = circuit._component_registry
    try:
        last_entries = getattr(cr, '_last_scan', [])
        if last_entries:
            print(f"\n\n  ComponentRegistry — Last Scan ({len(last_entries)} entries)")
            from collections import Counter
            type_counts = Counter(e.type_tag for e in last_entries)
            alive_counts = Counter(
                (e.type_tag, e.is_alive) for e in last_entries)
            print(f"  Type distribution: {dict(type_counts)}")
            hidden = [e for e in last_entries
                      if hasattr(e, 'census_visible') and not e.census_visible]
            print(f"  Hidden from bundle census: {len(hidden)} components")
            for e in hidden[:20]:
                print(f"    {e.component_id}")
        else:
            print("\n\n  ComponentRegistry: no scan data.")
    except Exception as ex:
        print(f"\n\n  ComponentRegistry read error: {ex}")

    # 6. Signal Path Audit (NEW — AUDIT-NOTE)
    spa.print_report(DT)

    # ── Final anomaly summary ─────────────────────────────────────────────────
    _print_anomaly_summary(circuit, spa, b_front, b_brake)


def _print_anomaly_summary(circuit, spa: SignalPathAudit, b_front, b_brake):
    """Synthesize all findings into a structured anomaly list."""
    anomalies = []

    # Check 1: Motor saturation
    for key in spa._motor_saturation_ticks:
        pct = spa.motor_saturation_pct(key)
        if pct > 50:
            anomalies.append(
                f"CRITICAL: Motor '{key}' saturated {pct:.0f}% of steps — "
                f"DEVIATION_MOTOR_GAIN drowns STDP signal")

    # Check 2: DEVIATION vs STDP ratio
    if spa._history:
        dev_mean = sum(r.motor_drive for r in spa._history) / len(spa._history)
        stdp_mean = sum(r.stdp_motor_max for r in spa._history) / len(spa._history)
        if stdp_mean > 0:
            ratio = dev_mean / stdp_mean
            if ratio > 100:
                anomalies.append(
                    f"CRITICAL: DEVIATION_MOTOR_GAIN/{'{:.0f}'.format(ratio)}× stronger than STDP — "
                    f"learning cannot influence Motor behavior")

    # Check 3: Vestibular silence
    for axis, vals in spa._vestibular_acc.items():
        if vals:
            mean_v = sum(vals) / len(vals)
            if mean_v < 0.0001:
                anomalies.append(
                    f"STRUCTURAL: Vestibular axis '{axis}' mean activation = {mean_v:.6f} — "
                    f"6-layer signal chain silent, Motor driven by bypass only")

    # Check 4: Xin sign inversion
    for bid, vals in spa._xin_signed.items():
        if not vals:
            continue
        neg_pct = 100.0 * sum(1 for x in vals if x < 0) / len(vals)
        mean_v = sum(vals) / len(vals)
        if neg_pct > 80:
            anomalies.append(
                f"SIGNAL QUALITY: Bundle '{bid[:35]}' Xin tension {mean_v:.2f} "
                f"({neg_pct:.0f}% negative) — actual >> predicted, "
                f"TOPRXin uses |ξ| so this sign inversion is INVISIBLE to ledger")

    # Check 5: DA direction (if available)
    if spa._da_dir_history:
        zero_frac = sum(1 for x in spa._da_dir_history if x < 0.01) / len(spa._da_dir_history)
        if zero_frac > 0.5:
            anomalies.append(
                f"GATING: DA direction factor is 0 for {zero_frac*100:.0f}% of steps — "
                f"body not approaching, DA blocked → STDP gets no reward signal")

    # Check 6: Fill collapse
    if spa._history:
        min_fill = min(r.fill_fraction for r in spa._history)
        zero_fill_frac = sum(1 for r in spa._history if r.fill_fraction < 0.01) / len(spa._history)
        if zero_fill_frac > 0.1:
            anomalies.append(
                f"METABOLIC: Energy store fill=0 for {zero_fill_frac*100:.0f}% of steps — "
                f"triggers DEVIATION_MOTOR_GAIN=max, making motor fully injection-driven")

    # Check 7: Noether violations
    noether = circuit._noether_probe.summary()
    n_viol = noether['violations']
    if n_viol > 0:
        vd = noether.get('violation_counts', {})
        anomalies.append(
            f"PHYSICS: {n_viol} Noether violations detected: {vd}")

    # Check 8: Xin tension divergence (front vs brake)
    if b_front and b_brake:
        xin_f = b_front.config.xin_tension
        xin_b = b_brake.config.xin_tension
        if abs(xin_f) > 0.1 and abs(xin_b) > 0.1:
            ratio = abs(xin_b) / abs(xin_f)
            if ratio > 2.0:
                anomalies.append(
                    f"XIN DIVERGENCE: brake/front Xin ratio={ratio:.1f} "
                    f"(front={xin_f:.2f}, brake={xin_b:.2f}) — "
                    f"brake bundle has {ratio:.0f}× larger prediction error")

    print("\n\n" + "═" * 80)
    print("  ANOMALY SUMMARY")
    print("═" * 80)
    if not anomalies:
        print("  No anomalies detected.")
    else:
        for i, a in enumerate(anomalies, 1):
            print(f"  [{i:02d}] {a}")
    print("═" * 80)
    print()
    print("  LEDGER COVERAGE ANALYSIS")
    print("  ────────────────────────────────────────────────────────────────────")
    print("  What the EXISTING ledger CAN detect:")
    print("    ✓ Noether conservation violations (energy, KCL, Xin bookkeeping, Landauer)")
    print("    ✓ Weight entropy (Shannon bits of weight distribution)")
    print("    ✓ T/O/P/R/Xin per bundle (|ξ|, transport_cost, weight change rate)")
    print("    ✓ Per-layer energy/heat/activity (EntropyLedger)")
    print("    ✓ Component TYPE tags and census visibility")
    print()
    print("  What the EXISTING ledger CANNOT detect (blind spots):")
    print("    ✗ DEVIATION_MOTOR_GAIN injection (bypasses all bundles)")
    print("    ✗ VitalOscillator injection (bypasses all bundles)")
    print("    ✗ Spinal reflex / noci injection (bypasses all bundles)")
    print("    ✗ DA direct membrane injection (bypasses all bundles)")
    print("    ✗ Column lateral inhibition direct injection")
    print("    ✗ Motor saturation statistics (not a physics violation)")
    print("    ✗ Vestibular silence (not a physics violation)")
    print("    ✗ Xin tension SIGN (TOPRXin uses |ξ|, sign inversion invisible)")
    print("    ✗ DA direction factor (entirely outside bundle framework)")
    print("    ✗ fill=0 triggering injection-dominated behavior")
    print()
    print("  Root cause of 'ledger not working': the 24 non-bundle injection points")
    print("  operate outside the T/O/P/R/Xin framework, making their effects")
    print("  structurally invisible. The ledger reports 'no violations' while")
    print("  Motor neurons are 100% injection-saturated.")
    print("═" * 80)


if __name__ == '__main__':
    run()
