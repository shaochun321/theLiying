"""Vestibular calibration scan — Phase P0: STDP-FROZEN measurement.

Identical protocol to exp_vest_calibration_scan.py, with one critical change:
  STDP is FROZEN during the MEASURE window (steps 3000-5000).
  This eliminates the "observer effect" where weight evolution during
  measurement contaminated the Phase 1 scan (54-79% axis non-isomorphism).

Only bundles_met_to_hc have active STDP; bundles_hc_to_aff use learning_rule="frozen"
(ribbon synapse, BIO: Bao et al. 2003), so only met_to_hc needs intervention.

Outputs:
  1. Slope comparison: Phase 1 (unfrozen) vs P0 (frozen)
  2. Isotropy decision: <5% → unified template; >30% → independent per axis
  3. S1 baseline: weight snapshot + membrane potentials at amp=6.0
  4. baseline_v2_结构快照.csv

EXP reference: EXP-vest-scan-P0-2026-06-30
"""
import sys, os, math, time, csv
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from nexus_v1.vestibular.chain_v2 import VestibularChainV2

DT        = 0.001
FREQ      = 2.0         # Hz — Lasker 2008
STEPS     = 5000
WARMUP    = 3000        # STDP active (weight convergence)
MEASURE   = 2000        # STDP FROZEN (clean measurement)
AMPS      = [round(0.5 * i, 1) for i in range(1, 21)]
CANAL_AXES   = ["yaw", "pitch", "roll"]
OTOLITH_AXES = ["oto_x", "oto_y", "oto_z"]
ALL_AXES     = CANAL_AXES + OTOLITH_AXES

# Phase 1 slopes (unfrozen, EXP-vest-scan-2026-06-30) — for comparison
PHASE1_SLOPES = {
    "yaw": 8.479, "pitch": 4.913, "roll": 3.084,
    "oto_x": 5.780, "oto_y": 0.846, "oto_z": 3.059,
}


def scan_one_frozen(axis: str, amplitude: float) -> tuple:
    """Measure steady-state Aff firing rate with STDP frozen during measurement.

    Returns:
        (f_reg_Hz, f_irr_Hz, w_met_hc_mean_after_warmup, hc_vmem_mean, aff_vmem_mean)
    """
    chain = VestibularChainV2(p_avail_ref=[1.0])
    spikes_reg = 0
    spikes_irr = 0

    # ── WARMUP: STDP active (weights allowed to evolve/converge) ──
    for step in range(WARMUP):
        t = step * DT
        sig = amplitude * math.sin(2.0 * math.pi * FREQ * t)
        mechanical = {ax: (sig if ax == axis else 0.0) for ax in ALL_AXES}
        chain.step(mechanical, dt=DT)

    # ── FREEZE: disable STDP in met_to_hc bundles for all axes ──
    saved_lr = {}
    for ax in ALL_AXES:
        b = chain.bundles_met_to_hc[ax]
        saved_lr[ax] = b.config.stdp_lr
        b.config.stdp_lr = 0.0

    # Capture weight state after warmup (S1 baseline)
    w_after_warmup = {ax: chain.bundles_met_to_hc[ax].mean_weight()
                      for ax in ALL_AXES}

    # ── MEASURE: STDP frozen, clean observation ──
    hc_vmem_sum = 0.0
    aff_vmem_sum = 0.0
    for step in range(MEASURE):
        t = (WARMUP + step) * DT
        sig = amplitude * math.sin(2.0 * math.pi * FREQ * t)
        mechanical = {ax: (sig if ax == axis else 0.0) for ax in ALL_AXES}
        chain.step(mechanical, dt=DT)

        if chain.afferent_regular[axis]._spiked_this_step:
            spikes_reg += 1
        if chain.afferent_irregular[axis]._spiked_this_step:
            spikes_irr += 1

        hc_vmem_sum  += chain.haircell_neurons[axis].activation
        aff_vmem_sum += chain.afferent_regular[axis].activation

    # Restore STDP (not strictly needed — chain is discarded, but clean)
    for ax in ALL_AXES:
        chain.bundles_met_to_hc[ax].config.stdp_lr = saved_lr[ax]

    window_s = MEASURE * DT
    f_reg = spikes_reg / window_s
    f_irr = spikes_irr / window_s
    hc_vmem  = hc_vmem_sum / MEASURE
    aff_vmem = aff_vmem_sum / MEASURE
    w_target = w_after_warmup[axis]
    return f_reg, f_irr, w_target, hc_vmem, aff_vmem


def linear_slope(amps, rates) -> float:
    n = len(amps)
    if n < 2:
        return 0.0
    sx = sum(amps); sy = sum(rates)
    sxx = sum(a * a for a in amps); sxy = sum(a * r for a, r in zip(amps, rates))
    denom = n * sxx - sx * sx
    return 0.0 if abs(denom) < 1e-12 else (n * sxy - sx * sy) / denom


# ─────────────────────────────────────────────────────────────────────────────
print("=" * 72)
print("Vestibular Calibration Scan P0 — STDP FROZEN during measurement")
print("=" * 72)
print(f"Protocol: {STEPS} steps/pt ({WARMUP} warmup[STDP-on] + {MEASURE} measure[STDP-frozen])")
print()

results: dict = {}
s1_baseline: list = []   # S1 data rows
t0 = time.time()

for axis in ALL_AXES:
    results[axis] = {}
    print(f"── Axis: {axis:<8s}  {'amp':>6s}  {'f_reg':>7s}  {'f_irr':>7s}  {'w_met':>7s}  {'hc_v':>7s}")
    for amp in AMPS:
        f_reg, f_irr, w_met, hc_v, aff_v = scan_one_frozen(axis, amp)
        results[axis][amp] = (f_reg, f_irr, w_met, hc_v, aff_v)
        marker = ""
        if amp == 6.0:
            marker = "  ← WP"
            s1_baseline.append({
                "axis": axis, "amp": 6.0,
                "f_reg": f_reg, "f_irr": f_irr,
                "w_met_hc_after_warmup": w_met,
                "hc_vmem_mean": hc_v,
                "aff_reg_vmem_mean": aff_v,
            })
        print(f"             {amp:>6.1f}  {f_reg:>7.2f}  {f_irr:>7.2f}  {w_met:>7.4f}  {hc_v:>7.4f}{marker}")
    print()

elapsed = time.time() - t0
print(f"Scan complete in {elapsed:.0f}s\n")

# ─────────────────────────────────────────────────────────────────────────────
# Slope analysis & isotropy decision
# ─────────────────────────────────────────────────────────────────────────────
print("=" * 72)
print("Slope Analysis: Phase 1 (unfrozen) vs P0 (frozen)")
print("=" * 72)

def axis_slope(axis_key, amp_max=6.0):
    amps  = [a for a in AMPS if a <= amp_max]
    rates = [results[axis_key][a][0] for a in amps]
    return linear_slope(amps, rates)

frozen_slopes = {ax: axis_slope(ax) for ax in ALL_AXES}

print(f"\n{'axis':<10s} {'P1 slope':>10s} {'P0 slope':>10s} {'Δslope%':>9s}  verdict")
for ax in ALL_AXES:
    p1 = PHASE1_SLOPES[ax]
    p0 = frozen_slopes[ax]
    delta = (p0 - p1) / p1 * 100 if p1 > 0 else float('inf')
    print(f"{ax:<10s} {p1:>10.4f} {p0:>10.4f} {delta:>+9.1f}%")

# Isotropy within canal / otolith groups (frozen slopes only)
print()
for group_name, group_axes in [("Canal (angular velocity)", CANAL_AXES),
                                 ("Otolith (linear accel.)", OTOLITH_AXES)]:
    vals = [frozen_slopes[ax] for ax in group_axes]
    mean_v = sum(vals) / len(vals)
    max_dev = max(abs(v - mean_v) / mean_v * 100 for v in vals) if mean_v > 0 else 999.0
    iso = "ISOMORPHIC (<5%)" if max_dev < 5 else ("BORDERLINE (5-30%)" if max_dev < 30 else "NON-ISOMORPHIC (>30%)")
    print(f"{group_name}:")
    for ax in group_axes:
        print(f"  {ax:<8s}  frozen slope = {frozen_slopes[ax]:.4f} Hz/unit")
    print(f"  max deviation: {max_dev:.1f}%  → {iso}")
    print()

# ─────────────────────────────────────────────────────────────────────────────
# Isotropy decision
# ─────────────────────────────────────────────────────────────────────────────
canal_vals    = [frozen_slopes[ax] for ax in CANAL_AXES]
otolith_vals  = [frozen_slopes[ax] for ax in OTOLITH_AXES]
canal_mean    = sum(canal_vals) / 3
otolith_mean  = sum(otolith_vals) / 3
canal_max_dev = max(abs(v - canal_mean) / canal_mean * 100 for v in canal_vals)
oto_max_dev   = max(abs(v - otolith_mean) / otolith_mean * 100 for v in otolith_vals)

print("=" * 72)
print("DECISION: Template Strategy")
print("=" * 72)
if canal_max_dev < 5 and oto_max_dev < 5:
    decision = "UNIFIED TEMPLATE — axes isomorphic after STDP freeze. Single anchor per modality."
    oto_y_action = "oto_y normal"
elif canal_max_dev < 30 and oto_max_dev < 30:
    decision = "UNIFIED TEMPLATE with per-axis calibration coefficients."
    oto_y_action = "check oto_y slope vs mean"
else:
    decision = "INDEPENDENT PER-AXIS — true structural non-isomorphism confirmed."
    oto_y_action = "P1 needed for oto_y"

print(f"\nCanal max deviation:   {canal_max_dev:.1f}%")
print(f"Otolith max deviation: {oto_max_dev:.1f}%")
print(f"\nDecision: {decision}")
print(f"oto_y action: {oto_y_action}")

# P1 trigger check
oto_y_ratio = frozen_slopes["oto_y"] / otolith_mean if otolith_mean > 0 else 0.0
print(f"\nP1 trigger check: oto_y slope = {frozen_slopes['oto_y']:.4f}, "
      f"otolith mean = {otolith_mean:.4f}, ratio = {oto_y_ratio:.2f}")
if oto_y_ratio < 0.5:
    print("→ P1 TRIGGERED: oto_y slope < 50% of otolith mean — needs diagnosis")
else:
    print("→ P1 NOT triggered: oto_y within acceptable range")

# ─────────────────────────────────────────────────────────────────────────────
# S1 baseline table
# ─────────────────────────────────────────────────────────────────────────────
print("\n" + "=" * 72)
print("S1 Baseline Snapshot (amp=6.0, STDP-frozen measurement)")
print("=" * 72)
print(f"\n{'axis':<10s} {'f_reg':>8s}  {'f_irr':>8s}  {'w_met_hc':>10s}  {'hc_vmem':>9s}  {'aff_vmem':>9s}")
for row in s1_baseline:
    print(f"{row['axis']:<10s} {row['f_reg']:>8.3f}  {row['f_irr']:>8.3f}  "
          f"{row['w_met_hc_after_warmup']:>10.4f}  {row['hc_vmem_mean']:>9.4f}  "
          f"{row['aff_reg_vmem_mean']:>9.4f}")

# Write CSV
csv_path = os.path.join(os.path.dirname(__file__), "baseline_v2_结构快照.csv")
with open(csv_path, "w", newline="", encoding="utf-8") as f:
    writer = csv.DictWriter(f, fieldnames=[
        "axis", "amp", "f_reg", "f_irr",
        "w_met_hc_after_warmup", "hc_vmem_mean", "aff_reg_vmem_mean"
    ])
    writer.writeheader()
    writer.writerows(s1_baseline)
print(f"\nS1 baseline saved to: {csv_path}")

# ─────────────────────────────────────────────────────────────────────────────
# Working-point summary with physical anchors
# ─────────────────────────────────────────────────────────────────────────────
print("\n" + "=" * 72)
print("Working-Point Physical Values (amp=6.0, frozen slopes)")
print("=" * 72)
canal_anchor_deg_s = canal_mean if canal_mean > 0 else 5.5   # Hz/unit = deg/s/unit at lit 1.0 Hz/(deg/s)
oto_anchor_ms2     = otolith_mean / 3.57 if otolith_mean > 0 else 0.9  # m/s² per unit
print(f"\nCanal anchor:   {canal_anchor_deg_s:.2f} deg/s per model unit (Lasker 2008)")
print(f"Otolith anchor: {oto_anchor_ms2:.3f} m/s² per model unit (Goldberg 2000)")
print()
print(f"{'axis':<10s} {'f_reg@6.0':>10s}  {'physical amplitude':>22s}")
for row in s1_baseline:
    ax = row["axis"]
    f = row["f_reg"]
    if ax in CANAL_AXES:
        phys = f"6.0 × {canal_anchor_deg_s:.1f} = {6*canal_anchor_deg_s:.1f} deg/s"
    else:
        phys = f"6.0 × {oto_anchor_ms2:.2f} = {6*oto_anchor_ms2:.2f} m/s² ({6*oto_anchor_ms2/9.81:.3f}g)"
    print(f"{ax:<10s} {f:>10.3f}  {phys}")

print("\nDone.")
