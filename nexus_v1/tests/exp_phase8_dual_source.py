"""Phase 8: Dual non-symmetric heat source navigation.

RC fixes applied (code changes, not experiment parameters):
  RC-1: Non-symmetric source layout — two sources on orthogonal axes
         src1=[70,50,50] (+x right) and src2=[50,50,30] (-z back)
         ΔT_LR = +0.333 (right warmer), ΔT_FB = -0.333 (back warmer)
         No geometric cancellation (unlike symmetric [70]+[30] in x-axis).
  RC-2: chain.py thermo_to_relay synapse_gain 3.0→0.3 (relay activation
         3.7→0.37, pre_trace unsaturated, STDP gradient preserved).
  RC-3: variant_adapter.py d2_conductance 0.5→0.1 + d2_da_r_leak 100→20
         (D2R g×τ product 50→2; DA stays ~0.07 vs previous decay to 0.03).

Expected Phase 8 improvements over Phase 7 (single source):
  - DR1 (|wR - wL|) should improve: relay pre_traces now carry gradient ratio
  - DR1b (|wB - wF|) is new: tests FB gradient learning (src2)
  - DA_v should stabilize ~0.05-0.10 (not decay to 0.03)
  - Both source directions should accumulate weight asymmetry over 300k steps

Heat source geometry at body=[50,50,50]:
  src1=[70,50,50]: right_patch (x+1=51) dist=19, left_patch (x-1=49) dist=21
    → T_right=1.833, T_left=1.500, ΔT_LR=+0.333
  src2=[50,50,30]: back_patch (z-1=49) dist=19, front_patch (z+1=51) dist=21
    → T_back=1.833, T_front=1.500, ΔT_FB=-0.333 (back warmer)
  Combined: right≈3.500, back≈3.500, left≈3.167, front≈3.167
    → two "hot" directions, two "cool" directions
"""
import sys, math, os, time
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from nexus_v1.circuit.variant_adapter import VariantCircuit
from nexus_v1.components.world import HeatSource, Body, World

STEPS = 300_000
DT = 0.001
LOG_INTERVAL = 50_000
DR2_STEP = 300_000

# ── Heat sources (non-symmetric, orthogonal axes) ─────────────────────────────
src1 = HeatSource(position=[70.0, 50.0, 50.0], energy=10_000.0,
                  temperature=5.0, radius=30.0)
src2 = HeatSource(position=[50.0, 50.0, 30.0], energy=10_000.0,
                  temperature=5.0, radius=30.0)
src1._drift = [0.0, 0.0, 0.0]
src2._drift = [0.0, 0.0, 0.0]

body = Body(position=[50.0, 50.0, 50.0])
world = World(heat_sources=[src1, src2], body=body)
world.MIN_ALIVE = 0
world.REGEN_PROB = 0.0

init_pos = list(body.position)
init_dist_s1 = math.sqrt(sum((p - h)**2 for p, h in zip(body.position, src1.position)))
init_dist_s2 = math.sqrt(sum((p - h)**2 for p, h in zip(body.position, src2.position)))

c = VariantCircuit()
c.world = world
# BIO: lateral inhibition gain 0.3 (Melzack & Wall 1965)
c.somatosensory.LATERAL_GAIN = 0.3
# BIO: muscle gain 0.3 (Zajac 1989 Crit. Rev. Biomed. Eng. 17:359)
for m in c.muscle_system.muscles:
    m.gain = 0.3

_stdp_applied = False

print("=" * 72)
print("Phase 8: Dual non-symmetric source — RC-1/2/3 integration test")
print("=" * 72)
print(f"src1={src1.position}  src2={src2.position}")
print(f"RC-2: thermo_to_relay synapse_gain=0.3 (was 3.0)")
print(f"RC-3: d2_conductance=0.1, d2_da_r_leak=20.0 (was 0.5, 100)")
print(f"ΔT_LR=+0.333 (src1)  ΔT_FB=-0.333 (src2, back warmer)")
print(f"Body: {init_pos}  dist_s1={init_dist_s1:.2f}  dist_s2={init_dist_s2:.2f}")
print()
print(f"{'step':>6}  {'dst1':>6} {'dst2':>6}  {'wL':>6} {'wR':>6} {'wF':>6} {'wB':>6}  {'ΔwLR':>7} {'ΔwFB':>7}  {'fill':>5}  note")
print("-" * 90)

trajectory = []
dr2_snapshot = None
fill_zero_step = None
grad_dot_v_pos = 0
grad_dot_v_total = 0
da_sat_count = 0
dr4_first_step = None
dr4_sustained_start = None
t0 = time.time()

# Weight tracking helpers
def _get_weights(c):
    """Return {patch_id: mean_weight} for soma_to_da bundle."""
    if not c.bundles_soma_to_da:
        return {}
    b = c.bundles_soma_to_da[0]
    wm = b.weight_matrix()
    return {pid: sum(wm[i]) / max(len(wm[i]), 1)
            for i, pid in enumerate(c.somatosensory.patch_ids)}

def _da_vmem(c):
    if hasattr(c, 'da_neurons') and c.da_neurons:
        vals = [n._membrane.voltage for n in c.da_neurons.values()]
        return sum(vals) / len(vals)
    return 0.0

for step in range(STEPS):
    t = step * DT
    signal = {
        'yaw':   2.0 * math.sin(1.5 * t),
        'pitch': 1.5 * math.sin(1.0 * t),
        'roll':  1.0 * math.sin(0.7 * t),
        'oto_x': 6.0 * math.sin(2.0 * t),
        'oto_y': 6.0 * math.sin(2.5 * t + 0.3),
        'oto_z': 6.0 * math.sin(3.0 * t + 0.7),
    }
    c.step(signal, dt=DT)

    if not _stdp_applied and step >= 1 and c.bundles_soma_to_da:
        for b in c.bundles_soma_to_da:
            # BIO: STDP lr=0.005 — Bi & Poo 1998 J.Neurosci.; 2001 ARN
            b.config.stdp_lr = 0.005
        _stdp_applied = True

    pos = list(c.world.body.position)
    bv = c.world.body.velocity
    dist_s1 = math.sqrt(sum((p - h)**2 for p, h in zip(pos, src1.position)))
    dist_s2 = math.sqrt(sum((p - h)**2 for p, h in zip(pos, src2.position)))
    dist_nearest = min(dist_s1, dist_s2)
    nearest_src = src1 if dist_s1 <= dist_s2 else src2

    # DR5: gradient·velocity alignment to nearest source
    grad = [h - p for p, h in zip(pos, nearest_src.position)]
    dot = sum(g * v for g, v in zip(grad, bv))
    grad_dot_v_total += 1
    if dot > 0:
        grad_dot_v_pos += 1

    # DR6: DA saturation
    da_v = _da_vmem(c)
    if abs(da_v) > 0.9:
        da_sat_count += 1

    # fill zero
    if fill_zero_step is None and c.energy_store.fill_fraction <= 0.0:
        fill_zero_step = step

    # Weight divergence (LR and FB)
    ws = _get_weights(c)
    wdiff_lr = abs(ws.get('right', 0) - ws.get('left', 0))
    wdiff_fb = abs(ws.get('back', 0) - ws.get('front', 0))
    wdiff_max = max(wdiff_lr, wdiff_fb)

    # DR4: any divergence appears < 200k, sustained > 50k
    if wdiff_max > 0.003 and dr4_first_step is None:
        dr4_first_step = step
    if wdiff_max > 0.003:
        if dr4_sustained_start is None:
            dr4_sustained_start = step
    else:
        dr4_sustained_start = None

    # DR2 snapshot at 300k
    if step == DR2_STEP - 1:
        dist_red_s1 = init_dist_s1 - dist_s1
        dist_red_s2 = init_dist_s2 - dist_s2
        dr2_snapshot = {
            'pos': pos, 'dist_s1': dist_s1, 'dist_s2': dist_s2,
            'reduction_s1': dist_red_s1, 'reduction_s2': dist_red_s2,
            'reduction_nearest': init_dist_s1 - dist_nearest,
            'fill': c.energy_store.fill_fraction,
            'wdiff_lr': wdiff_lr, 'wdiff_fb': wdiff_fb,
        }

    if step % LOG_INTERVAL == 0:
        note = ""
        if step == 0:
            note = "init"
        trajectory.append({
            'step': step, 'pos': pos,
            'dist_s1': dist_s1, 'dist_s2': dist_s2,
            'fill': c.energy_store.fill_fraction,
            'wdiff_lr': wdiff_lr, 'wdiff_fb': wdiff_fb,
            'da_v': da_v,
            'ws': dict(ws),
        })
        elapsed = time.time() - t0
        print(f"{step:>6}  {dist_s1:>6.3f} {dist_s2:>6.3f}  "
              f"{ws.get('left',0):>6.4f} {ws.get('right',0):>6.4f} "
              f"{ws.get('front',0):>6.4f} {ws.get('back',0):>6.4f}  "
              f"{wdiff_lr:>+7.4f} {wdiff_fb:>+7.4f}  "
              f"{c.energy_store.fill_fraction:>5.3f}  "
              f"DA={da_v:.4f} ({elapsed:.0f}s)")

elapsed = time.time() - t0
print(f"\nDone: {STEPS:,} steps in {elapsed:.1f}s ({STEPS/elapsed:.0f} steps/s)\n")

# ── Final weights ──────────────────────────────────────────────────────────────
ws_f = _get_weights(c)
wdiff_lr_f = ws_f.get('right', 0) - ws_f.get('left', 0)
wdiff_fb_f = ws_f.get('back', 0) - ws_f.get('front', 0)

print("=" * 72)
print(f"DR Criteria (Phase 8 — dual source, RC-1/2/3 fixes)")
print("=" * 72)

# DR1: |wR - wL| > 0.005
dr1_ok = abs(wdiff_lr_f) > 0.005
print(f"\nDR1  |wR-wL| > 0.005:   {wdiff_lr_f:+.4f}  {'PASS' if dr1_ok else 'FAIL'}")

# DR1b: |wB - wF| > 0.005 (new: FB gradient from src2)
dr1b_ok = abs(wdiff_fb_f) > 0.005
print(f"DR1b |wB-wF| > 0.005:   {wdiff_fb_f:+.4f}  {'PASS' if dr1b_ok else 'FAIL'}  (src2 direction)")

# DR2: nearest source 3D dist reduction at 300k > 1.0
if dr2_snapshot:
    dr2_red = dr2_snapshot['reduction_nearest']
    dr2_red_s1 = dr2_snapshot['reduction_s1']
    dr2_red_s2 = dr2_snapshot['reduction_s2']
    dr2_ok = dr2_red > 1.0
    print(f"DR2  dist-reduction(300k)>1.0:  nearest={dr2_red:.4f}  "
          f"(s1={dr2_red_s1:+.4f} s2={dr2_red_s2:+.4f})  "
          f"{'PASS' if dr2_ok else 'FAIL'}")
else:
    dr2_ok = False

# DR3: fill@200k > 0
dr3_rec = next((r for r in trajectory if r['step'] == 200_000), None)
dr3_fill = dr3_rec['fill'] if dr3_rec else (dr2_snapshot['fill'] if dr2_snapshot else 0.0)
dr3_ok = dr3_fill > 0.0
if fill_zero_step:
    print(f"DR3  fill>0@200k:  {dr3_fill:.4f}  (zeroed@{fill_zero_step})  {'PASS' if dr3_ok else 'FAIL'}")
else:
    print(f"DR3  fill>0@200k:  {dr3_fill:.4f}  (never zeroed)  {'PASS' if dr3_ok else 'FAIL'}")

# DR4: divergence first<200k + sustained>50k
dr4_ok = (dr4_first_step is not None and dr4_first_step < 200_000 and
          dr4_sustained_start is not None and
          (STEPS - dr4_sustained_start) >= 50_000)
print(f"DR4  diverge<200k+sustain50k:  first@{dr4_first_step}  "
      f"sustained@{dr4_sustained_start}  {'PASS' if dr4_ok else 'FAIL'}")

# DR5: grad·v > 50%
dr5_pct = grad_dot_v_pos / max(grad_dot_v_total, 1) * 100
dr5_ok = dr5_pct > 50.0
print(f"DR5  grad·v>50%:  {dr5_pct:.2f}%  {'PASS' if dr5_ok else 'FAIL'}")

# DR6: DA saturation < 20%
dr6_pct = da_sat_count / max(STEPS, 1) * 100
dr6_ok = dr6_pct < 20.0
print(f"DR6  DA sat<20%:  {dr6_pct:.2f}%  {'PASS' if dr6_ok else 'FAIL'}")

core = [dr1_ok, dr2_ok, dr3_ok, dr4_ok, dr5_ok, dr6_ok]
bonus = [dr1b_ok]
passed = sum(core)
labels = ['DR1', 'DR2', 'DR3', 'DR4', 'DR5', 'DR6']
status_str = ' '.join(l + '=' + ('OK' if ok else 'NG') for l, ok in zip(labels, core))
bonus_str = 'DR1b=' + ('OK' if dr1b_ok else 'NG')

print(f"\n{'='*72}")
print(f"Core: {passed}/6 DR PASS  {status_str}")
print(f"Bonus: {bonus_str} (FB gradient — expected positive with src2)")
print('='*72)

print("\nFinal weights:")
print(f"  left={ws_f.get('left',0):.4f}  right={ws_f.get('right',0):.4f}  "
      f"front={ws_f.get('front',0):.4f}  back={ws_f.get('back',0):.4f}")
print(f"  wR-wL={wdiff_lr_f:+.4f} (expect >0: src1 at right)")
print(f"  wB-wF={wdiff_fb_f:+.4f} (expect >0: src2 at back, z=30)")

print("\nDistance trajectory:")
for r in trajectory:
    print(f"  step {r['step']:>6d}: dist_s1={r['dist_s1']:.3f}  dist_s2={r['dist_s2']:.3f}  "
          f"fill={r['fill']:.4f}  DA={r['da_v']:.4f}  "
          f"|ΔwLR|={r['wdiff_lr']:.4f}  |ΔwFB|={r['wdiff_fb']:.4f}")

sys.exit(0 if passed >= 6 else 1)
