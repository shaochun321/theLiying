"""World 2.0 Phase 5 — HC-008 兼容性验证（radius=30 + HC-008 保留）

**目的**：Phase 4b（radius=50）出现单调接近、无撤退，2/7 FAIL。
根因分析（2026-07-03）确认：
  - HC-008 fix 对 STDP 无直接影响（Ca²⁺ pre_trace=0，但 hc_to_aff 是 frozen 束）
  - Phase 4b 异常来自 radius=50 正能量效应 + fill_zero 提前（203k vs 445k）

本实验验证假说：**若将 radius 回退至 30（与 Phase 4 相同），HC-008 保留，
行为应当复现 Phase 4 的 5/7 PASS。**

**对照关系**：
  Phase 4 ：radius=30，无 HC-008（REF: 5/7 PASS）
  Phase 4b：radius=50，有 HC-008（REF: 2/7 FAIL）
  Phase 5 ：radius=30，有 HC-008（本次验证）

**热源布局（正三角形，同 Phase 3/4）**：
  S1=[80,50,25]  +x 方向（右）
  S2=[35,76,25]  -x+y 方向（左-前，120°）
  S3=[35,24,25]  -x-y 方向（左-后，240°）

**body 起点**：d=20 from S1（同 Phase 4，在能量赤字区内）

**验收标准**（同 Phase 4，5/7 PASS = success）：
  DR1: |wR-wL| > 0.005 OR |wB-wF| > 0.005 @600k（方向学习）
  DR2: dist_to_nearest reduction > 3.0 @600k（长程接近）
  DR3: fill > 0.05 @800k（能量维持）
  DR5: patch_grad·v > 60%（热趋性，patch 温差代理）
  DR4: 访问至少 2 个热源（d < 15）
  DR_cycles: approach_count >= 3（至少 3 次接近-撤退循环）
  DR_fill: fill > 0 throughout（不断粮）

**决策**：
  成功（>=5/7）→ HC-008 兼容多源学习；Phase 4b 回退纯为能量动力学；V2.0 路线正确
  失败（<4/7）→ HC-008 有间接效应（需深查）或存在其他未知变量
"""
import sys, math, os, time

sys.stdout.reconfigure(line_buffering=True)
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from nexus_v1.circuit.variant_adapter import VariantCircuit
from nexus_v1.components.world import HeatSource, Body, World
from nexus_v1.ledger import NuProbe

STEPS = 1_000_000
DT = 0.001
LOG_INTERVAL = 100_000
NU_LOG_INTERVAL = 200_000
DR1_CHECK_STEP = 600_000
DR2_CHECK_STEP = 600_000
DR3_CHECK_STEP = 800_000
VISIT_THRESHOLD = 15.0

# radius=30（与 Phase 4 相同；Phase 4b 用了 50 导致行为相变）
src1 = HeatSource(position=[80.0, 50.0, 25.0], energy=10_000.0,
                  temperature=5.0, radius=30.0)
src2 = HeatSource(position=[35.0, 76.0, 25.0], energy=10_000.0,
                  temperature=5.0, radius=30.0)
src3 = HeatSource(position=[35.0, 24.0, 25.0], energy=10_000.0,
                  temperature=5.0, radius=30.0)
for src in [src1, src2, src3]:
    src._drift = [0.0, 0.0, 0.0]

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
    if not circ.bundles_soma_to_da:
        return {}
    patch_ids = list(circ.somatosensory.patch_ids)
    result = {}
    for i, pid in enumerate(patch_ids):
        if i < len(circ.bundles_soma_to_da):
            wm = circ.bundles_soma_to_da[i].weight_matrix()
            result[pid] = sum(wm[0]) / max(len(wm[0]), 1)
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

print("=" * 80)
print("World 2.0 Phase 5 -- HC-008 compatibility validation (radius=30, HC-008 retained)")
print("Hypothesis: Phase 4b regression was energy dynamics (radius=50), NOT HC-008")
print("=" * 80)
print(f"S1={src1.position}  S2={src2.position}  S3={src3.position}")
print(f"body={init_pos}  dist_nearest={init_dist:.2f}  radius=30.0")
print(f"HC-008 fix: RETAINED in VariantCircuit (Ca-based pre_trace, hc_to_aff frozen)")
print()

hdr = (f"{'step':>7}  {'d_near':>6} {'nr':>2}  {'wL':>6} {'wR':>6} "
       f"{'wF':>6} {'wB':>6}  {'wR-wL':>7} {'wB-wF':>7}  "
       f"{'fill':>5}  {'DA':>6}  {'sysv':>9} {'chg%':>5}  {'DR5%':>5}  "
       f"{'vis':>5}  {'cyc':>4}  {'agc':>4}")
print(hdr)
print("-" * len(hdr))

grad_dot_v_pos = 0
grad_dot_v_total = 0
fill_zero_step = None
approach_count = 0
min_dist_ever = init_dist
in_approach = False
approach_threshold = 2.0

visited_s1 = False
visited_s2 = False
visited_s3 = False
sources_visited = 0

dist_at_600k = None
fill_at_800k = None
weights_at_600k = None

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

    # DR5: patch-gradient proxy（只用电路可感知的 patch 温差，非全局梯度）
    pt = c._patch_temps
    patch_grad = [
        pt.get('right', (0,))[0] - pt.get('left', (0,))[0],
        0.0,
        pt.get('front', (0,))[0] - pt.get('back', (0,))[0],
    ] if pt else [0.0, 0.0, 0.0]
    dot_patch = sum(patch_grad[i] * bv[i] for i in range(min(3, len(bv))))
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

    if not visited_s1 and _dist(pos, src1) < VISIT_THRESHOLD:
        visited_s1 = True
        sources_visited += 1
    if not visited_s2 and _dist(pos, src2) < VISIT_THRESHOLD:
        visited_s2 = True
        sources_visited += 1
    if not visited_s3 and _dist(pos, src3) < VISIT_THRESHOLD:
        visited_s3 = True
        sources_visited += 1

    if step == DR2_CHECK_STEP - 1:
        dist_at_600k = d_near
    if step == DR3_CHECK_STEP - 1:
        fill_at_800k = fill
    if step == DR1_CHECK_STEP - 1:
        weights_at_600k = _get_weights(c)

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
        agc_g = c.agc.gain
        row = (f"{step:>7}  {d_near:>6.3f} S{near_idx}  "
               f"{ws.get('left', 0):>6.4f} {ws.get('right', 0):>6.4f} "
               f"{ws.get('front', 0):>6.4f} {ws.get('back', 0):>6.4f}  "
               f"{wdiff_lr:>+7.4f} {wdiff_fb:>+7.4f}  "
               f"{fill:>5.3f}  {da_v:>6.4f}  "
               f"{sys_nu:>+9.3f} {cf:>4.0%}  {dr5_now:>5.1f}%  "
               f"{sources_visited:>5}  {approach_count:>4}  {agc_g:>4.2f}  ({elapsed:.0f}s)")
        print(row)

    if step > 0 and step % NU_LOG_INTERVAL == 0:
        print(f"\n  nu top-3 at step {step}:")
        for snap in probe.top_bundles(3):
            nu_ema = probe._nu_ema.get(snap.bundle_id, 0.0)
            print(f"    {snap.bundle_id:40s} v={nu_ema:+.5f}  xi={snap.xi:.4f}")
        print()

elapsed_total = time.time() - t0
print(f"\nDone: {STEPS:,} steps in {elapsed_total:.1f}s ({STEPS/elapsed_total:.0f}/s)\n")

print("=" * 80)
print("Phase 5 DR Judgment  [Phase 4 REF: 5/7 PASS  |  Phase 4b REF: 2/7 FAIL]")
print("=" * 80)

ws_f = _get_weights(c)
wdiff_lr_f = ws_f.get('right', 0) - ws_f.get('left', 0)
wdiff_fb_f = ws_f.get('back', 0) - ws_f.get('front', 0)
fill_f = c.energy_store.fill_fraction
d_near_f = _dist_to_nearest(list(c.world.body.position))
dr5_final = grad_dot_v_pos / max(grad_dot_v_total, 1) * 100

ws_dr1 = weights_at_600k if weights_at_600k else ws_f
wdiff_lr_dr1 = ws_dr1.get('right', 0) - ws_dr1.get('left', 0)
wdiff_fb_dr1 = ws_dr1.get('back', 0) - ws_dr1.get('front', 0)

dist_reduction_600k = (init_dist - dist_at_600k) if dist_at_600k is not None else (init_dist - d_near_f)
fill_800k = fill_at_800k if fill_at_800k is not None else fill_f

print(f"\nFinal state (step {STEPS:,}):")
print(f"  body pos: {[round(x, 2) for x in c.world.body.position]}")
print(f"  dist_nearest: {d_near_f:.3f}  (init: {init_dist:.3f})")
print(f"  fill: {fill_f:.4f}")
print(f"  wR-wL@600k: {wdiff_lr_dr1:+.4f}  wB-wF@600k: {wdiff_fb_dr1:+.4f}")
print(f"  wR-wL@final: {wdiff_lr_f:+.4f}  wB-wF@final: {wdiff_fb_f:+.4f}")
print(f"  approach cycles: {approach_count}")
print(f"  sources visited: {sources_visited} (S1:{visited_s1}, S2:{visited_s2}, S3:{visited_s3})")
print(f"  fill_zero_step: {fill_zero_step}")

dr_results = {
    "DR1 |wR-wL|>0.005 or |wB-wF|>0.005 @600k":
        (abs(wdiff_lr_dr1) > 0.005 or abs(wdiff_fb_dr1) > 0.005,
         f"wR-wL={wdiff_lr_dr1:+.4f}  wB-wF={wdiff_fb_dr1:+.4f}"),
    "DR2 dist reduction>3.0 @600k":
        (dist_reduction_600k > 3.0,
         f"reduction={dist_reduction_600k:.3f} (init={init_dist:.2f} -> @600k={dist_at_600k})"),
    "DR3 fill>0.05 @800k":
        (fill_800k > 0.05,
         f"fill@800k={fill_800k:.4f}"),
    "DR4 visit >=2 sources (d<15)":
        (sources_visited >= 2,
         f"visited={sources_visited} (S1:{visited_s1}, S2:{visited_s2}, S3:{visited_s3})"),
    "DR5 thermotaxis patch_grad.v>60%":
        (dr5_final > 60.0,
         f"DR5={dr5_final:.1f}%"),
    "DR_cycles approach_count>=3":
        (approach_count >= 3,
         f"cycles={approach_count}"),
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

print(f"\n{'='*80}")
print("Interpretation:")
if n_pass >= 5:
    print("  SUCCESS: HC-008 compatible with multi-source navigation.")
    print("  -> Phase 4b regression confirmed as energy dynamics (radius=50), NOT HC-008.")
    print("  -> V2.0 architecture path is valid.")
else:
    print("  FAILURE: Multi-source navigation did not recover.")
    print("  -> Possible HC-008 indirect effect OR unknown variable.")
    print("  -> Need deeper investigation before proceeding to V2.0.")

passed = n_pass >= 5
print(f"\nTotal DR: {n_pass}/{len(dr_results)} {'PASS' if passed else 'FAIL'}")
print(f"{'='*80}")
sys.exit(0 if passed else 1)
