"""World 2.0 Phase 3 — 三热源正三角形导航验证

**背景**：Phase 3（2026-06-28）使用旧架构（tonic DA）时 W13/W14/W15 全败（STDP 对称
死锁）。本实验在 RC-4 phasic DA 激活后重新测试相同场景，检验 phasic DA 是否解决
对称死锁问题。

**热源布局（正三角形，半径=30，中心=[50,50,25]）**：
  S1=[80,50,25]  +x 方向（右）
  S2=[35,76,25]  -x+y 方向（左-前，120°）
  S3=[35,24,25]  -x-y 方向（左-后，240°）

**验收标准**：
  DR1: |wR-wL| > 0.005 OR |wB-wF| > 0.005（至少一方向学习）
  DR2: dist_to_nearest reduction > 1.0 at 300k 步
  DR3: fill > 0.05 at 200k 步（能量存活）
  DR5: grad·v > 50%（热趋性涌现）
  NP1: thermo 束 ν EMA > 0（热信号充电态）
"""
import sys, math, os, time

# Force line-buffering so output appears in redirected files immediately
sys.stdout.reconfigure(line_buffering=True)

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from nexus_v1.circuit.variant_adapter import VariantCircuit
from nexus_v1.components.world import HeatSource, Body, World
from nexus_v1.ledger import NuProbe

STEPS = 500_000
DT = 0.001
LOG_INTERVAL = 50_000
NU_LOG_INTERVAL = 100_000
DR2_CHECK_STEP = 300_000

src1 = HeatSource(position=[80.0, 50.0, 25.0], energy=10_000.0,
                  temperature=5.0, radius=30.0)
src2 = HeatSource(position=[35.0, 76.0, 25.0], energy=10_000.0,
                  temperature=5.0, radius=30.0)
src3 = HeatSource(position=[35.0, 24.0, 25.0], energy=10_000.0,
                  temperature=5.0, radius=30.0)
src1._drift = [0.0, 0.0, 0.0]
src2._drift = [0.0, 0.0, 0.0]
src3._drift = [0.0, 0.0, 0.0]

# Body starts at d=20 from S1 (within sustain zone).
# At d=30 (centroid), proximity=0 → zero energy absorption.
# Matching Phase 7 calibration: d=20, r=30 → deposit≈drain equilibrium.
body = Body(position=[60.0, 50.0, 25.0])
world = World(heat_sources=[src1, src2, src3], body=body)
world.MIN_ALIVE = 0
world.REGEN_PROB = 0.0

c = VariantCircuit()
c.world = world
c.somatosensory.LATERAL_GAIN = 0.3
for m in c.muscle_system.muscles:
    m.gain = 0.3

probe = NuProbe(ema_alpha=0.001)
_stdp_applied = False


def _dist(pos, src):
    return math.sqrt(sum((p - h) ** 2 for p, h in zip(pos, src.position)))


def _dist_to_nearest(pos):
    return min(_dist(pos, src1), _dist(pos, src2), _dist(pos, src3))


def _get_weights(circ):
    # HC-002 fix: bundles_soma_to_da now has one bundle per patch (not one all-to-all).
    # Each bundle has 1 source (proj_pid); weight_matrix()[0] = that source's DA weights.
    if not circ.bundles_soma_to_da:
        return {}
    patch_ids = list(circ.somatosensory.patch_ids)
    result = {}
    bundles = circ.bundles_soma_to_da
    for i, pid in enumerate(patch_ids):
        if i < len(bundles):
            wm = bundles[i].weight_matrix()
            result[pid] = sum(wm[0]) / max(len(wm[0]), 1)  # wm[0] = only source
        else:
            result[pid] = 0.0
    return result


def _da_vmem(circ):
    if hasattr(circ, 'da_neurons') and circ.da_neurons:
        vals = [n._membrane.voltage for n in circ.da_neurons.values()]
        return sum(vals) / len(vals)
    return 0.0


init_pos = list(body.position)
init_dist = _dist_to_nearest(init_pos)
d1_init = _dist(init_pos, src1)
d2_init = _dist(init_pos, src2)
d3_init = _dist(init_pos, src3)

print("=" * 76)
print("World 2.0 Phase 3 -- San-source equilateral triangle (500k, RC-4 phasic DA)")
print("=" * 76)
print(f"S1={src1.position}(+x right)  S2={src2.position}(-x+y)  S3={src3.position}(-x-y)")
print(f"body={init_pos}  dist_nearest={init_dist:.2f}")
print(f"d_S1={d1_init:.2f}  d_S2={d2_init:.2f}  d_S3={d3_init:.2f}")
print()

hdr = (f"{'step':>6}  {'d_near':>6} {'nr':>2}  {'wL':>6} {'wR':>6} "
       f"{'wF':>6} {'wB':>6}  {'wR-wL':>7} {'wB-wF':>7}  "
       f"{'fill':>5}  {'DA':>6}  {'sysv':>9} {'chg%':>5}  {'DR5%':>5}  {'agc':>4}")
print(hdr)
print("-" * len(hdr))

grad_dot_v_pos = 0
grad_dot_v_total = 0
fill_zero_step = None
approach_count = 0
min_dist_ever = init_dist
in_approach = False
approach_threshold = 2.0

dist_at_300k = None
fill_at_200k = None

t0 = time.time()

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
    probe.update(c, step, dt=DT)

    if not _stdp_applied and step >= 1 and c.bundles_soma_to_da:
        for b in c.bundles_soma_to_da:
            b.config.stdp_lr = 0.005
        _stdp_applied = True

    pos = list(c.world.body.position)
    bv = c.world.body.velocity
    d_near = _dist_to_nearest(pos)
    fill = c.energy_store.fill_fraction

    # DR5 patch-gradient proxy: what the circuit can actually sense via skin patches.
    # (world.gradient_at is kept as diagnostic only, not used for PASS/FAIL)
    pt = c._patch_temps
    patch_grad = [
        pt.get('right', (0,))[0] - pt.get('left', (0,))[0],
        0.0,
        pt.get('front', (0,))[0] - pt.get('back', (0,))[0],
    ] if pt else [0.0, 0.0, 0.0]
    dot_patch = sum(patch_grad[i] * bv[i] for i in range(min(3, len(bv))))
    dot_gt = sum(g * v for g, v in zip(c.world.gradient_at(pos, eps=0.5), bv))  # diagnostic
    if dot_patch != 0 or any(abs(v) > 1e-8 for v in bv):
        grad_dot_v_total += 1
        if dot_patch > 0:
            grad_dot_v_pos += 1

    if fill_zero_step is None and fill <= 0.0:
        fill_zero_step = step

    if d_near < min_dist_ever:
        min_dist_ever = d_near
        if not in_approach:
            approach_count += 1
            in_approach = True
    elif d_near > min_dist_ever + approach_threshold:
        in_approach = False

    if step == 200_000:
        fill_at_200k = fill
    if step == DR2_CHECK_STEP - 1:
        dist_at_300k = d_near

    if step % LOG_INTERVAL == 0:
        ws = _get_weights(c)
        da_v = _da_vmem(c)
        wdiff_lr = ws.get('right', 0) - ws.get('left', 0)
        wdiff_fb = ws.get('back', 0) - ws.get('front', 0)
        sys_nu = probe.system_nu_ema
        cf = probe.charging_fraction
        dr5_now = grad_dot_v_pos / max(grad_dot_v_total, 1) * 100

        dists = [_dist(pos, s) for s in [src1, src2, src3]]
        near_idx = dists.index(min(dists)) + 1

        elapsed = time.time() - t0
        agc_g = c.agc.gain  # circuit-level AGC (BG/HPA axis; modulates exploration noise)
        row = (f"{step:>6}  {d_near:>6.3f} S{near_idx}  "
               f"{ws.get('left', 0):>6.4f} {ws.get('right', 0):>6.4f} "
               f"{ws.get('front', 0):>6.4f} {ws.get('back', 0):>6.4f}  "
               f"{wdiff_lr:>+7.4f} {wdiff_fb:>+7.4f}  "
               f"{fill:>5.3f}  {da_v:>6.4f}  "
               f"{sys_nu:>+9.3f} {cf:>4.0%}  {dr5_now:>5.1f}%  {agc_g:>4.2f}  ({elapsed:.0f}s)")
        print(row)

    if step > 0 and step % NU_LOG_INTERVAL == 0:
        print(f"\n  nu top-3 at step {step}:")
        for snap in probe.top_bundles(3):
            nu_ema = probe._nu_ema.get(snap.bundle_id, 0.0)
            print(f"    {snap.bundle_id:40s} v={nu_ema:+.5f}  xi={snap.xi:.4f}")
        print()

elapsed_total = time.time() - t0
print(f"\nDone: {STEPS:,} steps in {elapsed_total:.1f}s ({STEPS/elapsed_total:.0f}/s)\n")

print("=" * 76)
print("Phase 3 DR Judgment")
print("=" * 76)

ws_f = _get_weights(c)
wdiff_lr_f = ws_f.get('right', 0) - ws_f.get('left', 0)
wdiff_fb_f = ws_f.get('back', 0) - ws_f.get('front', 0)
fill_f = c.energy_store.fill_fraction
d_near_f = _dist_to_nearest(list(c.world.body.position))
dr5_final = grad_dot_v_pos / max(grad_dot_v_total, 1) * 100

print(f"\nFinal state (step {STEPS:,}):")
print(f"  body pos: {[round(x, 2) for x in c.world.body.position]}")
print(f"  dist_nearest: {d_near_f:.3f}  (init: {init_dist:.3f})")
print(f"  fill: {fill_f:.4f}")
print(f"  wR-wL: {wdiff_lr_f:+.4f}  wB-wF: {wdiff_fb_f:+.4f}")
print(f"  approach cycles: {approach_count}")
print(f"  fill_zero_step: {fill_zero_step}")

print(f"\nHeat source status:")
for i, src in enumerate([src1, src2, src3], 1):
    print(f"  S{i}: energy={src.energy:.1f}  alive={src.alive}")
print()

dist_reduction_300k = (init_dist - dist_at_300k) if dist_at_300k is not None else (init_dist - d_near_f)
fill_200k = fill_at_200k if fill_at_200k is not None else fill_f

dr_results = {
    "DR1 direction learning |wR-wL|>0.005 or |wB-wF|>0.005":
        (abs(wdiff_lr_f) > 0.005 or abs(wdiff_fb_f) > 0.005,
         f"wR-wL={wdiff_lr_f:+.4f}  wB-wF={wdiff_fb_f:+.4f}"),
    "DR2 dist_nearest reduction>1.0 @300k":
        (dist_reduction_300k > 1.0,
         f"reduction={dist_reduction_300k:.3f} (init={init_dist:.2f} -> @300k={dist_at_300k})"),
    "DR3 fill>0.05 @200k":
        (fill_200k > 0.05,
         f"fill@200k={fill_200k:.4f}"),
    "DR5 thermotaxis grad.v>50%":
        (dr5_final > 50.0,
         f"DR5={dr5_final:.1f}%  ({grad_dot_v_pos}/{grad_dot_v_total})"),
    "DR_fill fill>0 throughout":
        (fill_zero_step is None,
         f"fill_zero={'never' if fill_zero_step is None else f'@{fill_zero_step}'}"),
}
n_pass = 0
for desc, (ok, val) in dr_results.items():
    mark = "PASS" if ok else "FAIL"
    print(f"  [{mark}] {desc}  ({val})")
    if ok:
        n_pass += 1

print("\n" + "-" * 60)
print("NuProbe final state")
thermo_nus = {bid: v for bid, v in probe._nu_ema.items() if 'thermo' in bid}
np1_ok = all(v > 0 for v in thermo_nus.values()) if thermo_nus else False
print(f"  [{'PASS' if np1_ok else 'FAIL'}] NP1: thermo bundles charging  "
      f"({', '.join(f'{k}={v:.4f}' for k, v in list(thermo_nus.items())[:3])})")
print(f"  approach_count = {approach_count}")
print(f"  charging_fraction = {probe.charging_fraction:.1%}")
print(f"  system_nu_ema = {probe.system_nu_ema:+.4f}")

passed = n_pass >= 4
print(f"\n{'='*76}")
print(f"Total DR: {n_pass}/{len(dr_results)} {'PASS' if passed else 'FAIL'}")
print(f"{'='*76}")
sys.exit(0 if passed else 1)
