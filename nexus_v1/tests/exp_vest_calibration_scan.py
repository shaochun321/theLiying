"""Vestibular calibration scan — Phase 1 of vestibular dimension anchoring.

Protocol (matching Lasker et al. 2008, J Neurophysiol 99:1222):
  - Signal:     pure sinusoid per axis, all others = 0
  - Frequency:  2 Hz  →  500 steps/cycle at dt=0.001
  - Amplitudes: 0.5, 1.0, ..., 10.0  (20 points per axis)
  - Duration:   5000 steps / point  (10 cycles; last 2000 steps measured)
  - Chain:      VestibularChainV2 isolated, p_avail=1.0 (no World/VariantCircuit)
  - Fresh chain per (axis, amplitude) — avoids STDP history contamination

Outputs:
  1. Console table: amplitude → f_reg, f_irr per axis
  2. Isotropy check: yaw/pitch/roll slope comparison (< 5% diff = isomorphic)
  3. Working-point: oto_x=6.0 physical mapping target

DT convention: dt=0.001 s = 1 ms (project standard)
"""
import sys, os, math, time
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from nexus_v1.vestibular.chain_v2 import VestibularChainV2

DT        = 0.001       # 1 ms / step
FREQ      = 2.0         # Hz — matches Lasker 2008
STEPS     = 5000        # steps per amplitude point
WARMUP    = 3000        # first 3000 steps: warm-up (6 cycles)
MEASURE   = 2000        # last 2000 steps: measurement window (4 cycles)
AMPS      = [round(0.5 * i, 1) for i in range(1, 21)]   # 0.5 … 10.0
CANAL_AXES   = ["yaw", "pitch", "roll"]
OTOLITH_AXES = ["oto_x", "oto_y", "oto_z"]
ALL_AXES     = CANAL_AXES + OTOLITH_AXES


def scan_one(axis: str, amplitude: float) -> tuple[float, float]:
    """Measure steady-state Aff firing rate for one (axis, amplitude) pair.

    Returns:
        (f_reg_Hz, f_irr_Hz)  — measured over last MEASURE steps
    """
    chain = VestibularChainV2(p_avail_ref=[1.0])

    spikes_reg = 0
    spikes_irr = 0

    for step in range(STEPS):
        t = step * DT
        sig = amplitude * math.sin(2.0 * math.pi * FREQ * t)
        mechanical = {ax: (sig if ax == axis else 0.0) for ax in ALL_AXES}
        chain.step(mechanical, dt=DT)

        if step >= WARMUP:
            if chain.afferent_regular[axis]._spiked_this_step:
                spikes_reg += 1
            if chain.afferent_irregular[axis]._spiked_this_step:
                spikes_irr += 1

    window_s = MEASURE * DT          # 2.0 s
    f_reg = spikes_reg / window_s
    f_irr = spikes_irr / window_s
    return f_reg, f_irr


def linear_slope(amps, rates) -> float:
    """Slope of linear regression through (amp, rate) pairs (Hz / unit)."""
    n = len(amps)
    if n < 2:
        return 0.0
    sx = sum(amps)
    sy = sum(rates)
    sxx = sum(a * a for a in amps)
    sxy = sum(a * r for a, r in zip(amps, rates))
    denom = n * sxx - sx * sx
    if abs(denom) < 1e-12:
        return 0.0
    return (n * sxy - sx * sy) / denom


def saturation_point(amps, rates) -> float | None:
    """Return amplitude where rate no longer grows (> 95% of max)."""
    if not rates:
        return None
    max_r = max(rates)
    if max_r <= 0:
        return None
    for a, r in zip(amps, rates):
        if r >= 0.95 * max_r:
            return a
    return amps[-1]


# ─────────────────────────────────────────────────────────────────────────────
print("=" * 72)
print("Vestibular Calibration Scan  |  Phase 1  |  dt=1ms, f=2Hz, N=20pts")
print("=" * 72)
print(f"Protocol: {STEPS} steps/pt ({WARMUP} warmup + {MEASURE} measure), "
      f"amplitudes 0.5–10.0")
print()

results: dict[str, dict[float, tuple[float, float]]] = {}
t0 = time.time()

for axis in ALL_AXES:
    results[axis] = {}
    print(f"── Axis: {axis:<8s} {'amp':>6s}  {'f_reg':>7s}  {'f_irr':>7s}")
    for amp in AMPS:
        f_reg, f_irr = scan_one(axis, amp)
        results[axis][amp] = (f_reg, f_irr)
        marker = ""
        if amp == 6.0:
            marker = "  ← Phase-5/6 working point"
        print(f"             {amp:>6.1f}  {f_reg:>7.2f}  {f_irr:>7.2f}{marker}")
    print()

elapsed = time.time() - t0
print(f"Scan complete in {elapsed:.0f}s\n")

# ─────────────────────────────────────────────────────────────────────────────
# Isotropy analysis
# ─────────────────────────────────────────────────────────────────────────────
print("=" * 72)
print("Isotropy Analysis")
print("=" * 72)

def axis_slope(axis_key, amp_max=6.0):
    """Linear slope of f_reg in the sub-saturation range."""
    amps = [a for a in AMPS if a <= amp_max]
    rates = [results[axis_key][a][0] for a in amps]
    return linear_slope(amps, rates)

canal_slopes  = {ax: axis_slope(ax) for ax in CANAL_AXES}
otolith_slopes = {ax: axis_slope(ax) for ax in OTOLITH_AXES}

print("\nCanal (angular velocity) axes:")
for ax, sl in canal_slopes.items():
    print(f"  {ax:<8s}  slope = {sl:.4f} Hz/unit")
if canal_slopes:
    vals = list(canal_slopes.values())
    mean_s = sum(vals) / len(vals)
    max_dev = max(abs(v - mean_s) / mean_s * 100 for v in vals) if mean_s > 0 else float('inf')
    print(f"  max deviation from mean: {max_dev:.1f}%  → "
          f"{'ISOMORPHIC (<5%)' if max_dev < 5 else 'NON-ISOMORPHIC (≥5%)'}")

print("\nOtolith (linear acceleration) axes:")
for ax, sl in otolith_slopes.items():
    print(f"  {ax:<8s}  slope = {sl:.4f} Hz/unit")
if otolith_slopes:
    vals = list(otolith_slopes.values())
    mean_s = sum(vals) / len(vals)
    max_dev = max(abs(v - mean_s) / mean_s * 100 for v in vals) if mean_s > 0 else float('inf')
    print(f"  max deviation from mean: {max_dev:.1f}%  → "
          f"{'ISOMORPHIC (<5%)' if max_dev < 5 else 'NON-ISOMORPHIC (≥5%)'}")

# ─────────────────────────────────────────────────────────────────────────────
# Working-point summary (for Phase 2 anchor)
# ─────────────────────────────────────────────────────────────────────────────
print("\n" + "=" * 72)
print("Working-Point Summary (for Phase 2 anchor computation)")
print("=" * 72)
print()
print(f"{'axis':<10s} {'f_reg@amp=1.0':>14s}  {'f_reg@amp=6.0':>14s}  "
      f"{'sat_point':>10s}  {'slope(0.5-6)':>12s}")
for axis in ALL_AXES:
    f1  = results[axis].get(1.0, (0.0, 0.0))[0]
    f6  = results[axis].get(6.0, (0.0, 0.0))[0]
    sat = saturation_point(AMPS, [results[axis][a][0] for a in AMPS])
    sl  = axis_slope(axis)
    print(f"{axis:<10s} {f1:>14.3f}  {f6:>14.3f}  {sat:>10.1f}  {sl:>12.4f}")

print()
print("NOTE: f_reg@amp=1.0 is the key value for anchor calibration.")
print("      Literature target (Lasker 2008): 1.0 deg/s → ~1.0 Hz (Goldberg)")
print("      Ratio f_reg@1.0 / 1.0 = calibration K-factor per axis")
print()

# ─────────────────────────────────────────────────────────────────────────────
# Spontaneous rate (amplitude=0 baseline)
# ─────────────────────────────────────────────────────────────────────────────
print("=" * 72)
print("Spontaneous firing rate (amplitude=0 baseline, single run)")
print("=" * 72)
chain0 = VestibularChainV2(p_avail_ref=[1.0])
sp_reg = {ax: 0 for ax in ALL_AXES}
sp_irr = {ax: 0 for ax in ALL_AXES}
for step in range(STEPS):
    chain0.step({ax: 0.0 for ax in ALL_AXES}, dt=DT)
    if step >= WARMUP:
        for ax in ALL_AXES:
            if chain0.afferent_regular[ax]._spiked_this_step:
                sp_reg[ax] += 1
            if chain0.afferent_irregular[ax]._spiked_this_step:
                sp_irr[ax] += 1
window_s = MEASURE * DT
print(f"\n{'axis':<10s} {'f_reg_0':>10s}  {'f_irr_0':>10s}")
for ax in ALL_AXES:
    print(f"{ax:<10s} {sp_reg[ax]/window_s:>10.3f}  {sp_irr[ax]/window_s:>10.3f}")

print("\nDone.")
