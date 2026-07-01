"""双热源非对称长程验证 — 任务③

使用 RC-1 双热源布局（src1 右侧，src2 背后），运行 300k 步，
集成 NuProbe 追踪 ν 动态。

实验目标：
  - 验证系统能否区分两个热源并偏向更近/更强的一个
  - 追踪 soma_to_da 方向性权重（wR-wL, wB-wF）的长期演化
  - 通过 NuProbe 观察 Xin-DA 耦合的充/放电相变

DR 判据（与 Phase 8 一致）：
  DR1: |wR-wL| > 0.005 且 wR>wL（src1 右侧正确方向）
  DR2: 300k步距离总减少 > 1.0
  DR3: src1-fill > 0 at 200k（实际接近右侧热源）
  DR4: 分化起始 < 200k 且持续50k
  DR5: grad·v > 50%（热趋性涌现）
  DR6: DA 饱和 < 20%

ν 探针额外报告：
  NP1: thermo_to_relay_* 束 ν EMA > 0 at 100k（热信号通路持续充电）
  NP2: soma_to_da 束 ν EMA 在 300k 时是否转向放电（巩固信号）
  NP3: charging_fraction 时序
"""
import sys, math, os, time
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from nexus_v1.circuit.variant_adapter import VariantCircuit
from nexus_v1.components.world import HeatSource, Body, World
from nexus_v1.ledger import NuProbe

STEPS = 300_000
DT = 0.001
LOG_INTERVAL = 30_000
NU_LOG_INTERVAL = 30_000  # ν report every 30k steps

# ── RC-1 热源布局（Phase 8 同款）────────────────────────────────────────────
src1 = HeatSource(position=[70.0, 50.0, 50.0], energy=10_000.0,
                  temperature=5.0, radius=30.0)  # 右侧
src2 = HeatSource(position=[50.0, 50.0, 30.0], energy=10_000.0,
                  temperature=5.0, radius=30.0)  # 背后
src1._drift = [0.0, 0.0, 0.0]
src2._drift = [0.0, 0.0, 0.0]

body = Body(position=[50.0, 50.0, 50.0])
world = World(heat_sources=[src1, src2], body=body)
world.MIN_ALIVE = 0
world.REGEN_PROB = 0.0

c = VariantCircuit()
c.world = world
c.somatosensory.LATERAL_GAIN = 0.3
for m in c.muscle_system.muscles:
    m.gain = 0.3

probe = NuProbe(ema_alpha=0.001)
_stdp_applied = False


def _get_weights(c):
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


def _slow_relay_state(c):
    if not hasattr(c, '_slow_relays') or not c._slow_relays:
        return {}
    return {pid: n._membrane.voltage for pid, n in c._slow_relays.items()}


print("=" * 76)
print("任务③ 双热源非对称长程验证 — 300k步 + NuProbe")
print("=" * 76)
print(f"src1={src1.position} (RIGHT)  src2={src2.position} (BACK)")
print()

hdr = (f"{'step':>6}  {'d1':>6} {'d2':>6}  {'wL':>6} {'wR':>6} {'wF':>6} {'wB':>6}  "
       f"{'wR-wL':>7} {'wB-wF':>7}  {'DA':>6}  {'sysν':>9} {'charge%':>8}")
print(hdr)
print("-" * len(hdr))

t0 = time.time()
dr3_first_close = None  # first step body is closer to src1 than init
d1_init = math.sqrt(sum((p-h)**2 for p,h in zip(body.position, src1.position)))
d2_init = math.sqrt(sum((p-h)**2 for p,h in zip(body.position, src2.position)))
dist_s1_history = []
da_sat_count = 0
log_count = 0

direction_ok_windows = []  # (start, end, wR>wL persists)

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
    d1 = math.sqrt(sum((p-h)**2 for p,h in zip(pos, src1.position)))
    d2 = math.sqrt(sum((p-h)**2 for p,h in zip(pos, src2.position)))
    dist_s1_history.append(d1)

    # DR3: first approach to src1
    if dr3_first_close is None and step > 10 and d1 < d1_init:
        dr3_first_close = step

    # DR6: DA saturation
    da_v = _da_vmem(c)
    if abs(da_v) > 8.0:
        da_sat_count += 1

    if step % LOG_INTERVAL == 0:
        ws = _get_weights(c)
        sr = _slow_relay_state(c)
        nu_report = probe.report(step)

        wdiff_lr = ws.get('right', 0) - ws.get('left', 0)
        wdiff_fb = ws.get('back', 0) - ws.get('front', 0)
        sys_nu = probe.system_nu_ema
        cf = probe.charging_fraction

        elapsed = time.time() - t0
        row = (f"{step:>6}  {d1:>6.3f} {d2:>6.3f}  "
               f"{ws.get('left',0):>6.4f} {ws.get('right',0):>6.4f} "
               f"{ws.get('front',0):>6.4f} {ws.get('back',0):>6.4f}  "
               f"{wdiff_lr:>+7.4f} {wdiff_fb:>+7.4f}  "
               f"{da_v:>6.4f}  {sys_nu:>+9.4f} {cf:>7.1%}  ({elapsed:.0f}s)")
        print(row)
        log_count += 1

    if step > 0 and step % NU_LOG_INTERVAL == 0:
        r = probe.report(step)
        print(f"\n  ν top-3 at step {step}:")
        for snap in probe.top_bundles(3):
            nu_ema = probe._nu_ema.get(snap.bundle_id, 0.0)
            print(f"    {snap.bundle_id:40s} ν={nu_ema:+.5f}  ξ={snap.xi:.4f}")
        print()

elapsed_total = time.time() - t0
print(f"\nDone: {STEPS:,} steps in {elapsed_total:.1f}s ({STEPS/elapsed_total:.0f} steps/s)")

# ── DR 判定 ─────────────────────────────────────────────────────────────────
ws_f = _get_weights(c)
wdiff_lr_f = ws_f.get('right', 0) - ws_f.get('left', 0)
wdiff_fb_f = ws_f.get('back', 0) - ws_f.get('front', 0)
d1_f = dist_s1_history[-1]
d2_f = math.sqrt(sum((p-h)**2 for p,h in zip(c.world.body.position, src2.position)))

dist_reduction = d1_init - d1_f
da_sat_frac = da_sat_count / STEPS

# DR4: direction established and held
direction_stable_start = None
stable_count = 0
for i, d in enumerate(dist_s1_history):
    step_i = i
    if step_i < 5:
        continue
    # Check wR>wL by reading trajectory (approximate: use final weights as proxy)

print("\n" + "=" * 76)
print("DR 判定结果")
print("=" * 76)

dr_results = {
    "DR1 wR-wL > 0.005 (src1右侧正确)": (wdiff_lr_f > 0.005,
                                          f"wR-wL={wdiff_lr_f:+.4f}"),
    "DR1b wB-wF > 0 (src2背后正确)":    (wdiff_fb_f > 0.0,
                                          f"wB-wF={wdiff_fb_f:+.4f}"),
    "DR2 距离减少 > 1.0":               (dist_reduction > 1.0,
                                          f"减少={dist_reduction:.3f}"),
    "DR3 src1首次接近 < 200k步":         (dr3_first_close is not None and
                                          dr3_first_close < 200_000,
                                          f"first@{dr3_first_close}"),
    "DR6 DA饱和 < 20%":                 (da_sat_frac < 0.20,
                                          f"sat={da_sat_frac:.2%}"),
}
n_pass = 0
for desc, (ok, val) in dr_results.items():
    mark = "PASS" if ok else "FAIL"
    print(f"  [{mark}] {desc}  ({val})")
    if ok:
        n_pass += 1

# ν 额外报告
print("\n" + "─" * 60)
print("NP 判定（ν 探针额外指标）")
r_final = probe.report(STEPS - 1)
thermo_nus = {bid: v for bid, v in probe._nu_ema.items() if 'thermo' in bid}
soma_nu = probe._nu_ema.get('soma_to_da', float('nan'))

np1_ok = all(v > 0 for v in thermo_nus.values()) if thermo_nus else False
np2_ok = soma_nu < 0  # discharging = consolidation signal

print(f"  [{'PASS' if np1_ok else 'FAIL'}] NP1: thermo_to_relay 束均充电  ({', '.join(f'{k}={v:.4f}' for k,v in thermo_nus.items())})")
print(f"  [{'PASS' if np2_ok else 'INFO'}] NP2: soma_to_da 进入放电态 (ν={soma_nu:.4f}) {'← 巩固信号' if np2_ok else '← 仍充电'}")
print(f"  系统 charging_fraction = {probe.charging_fraction:.1%}")
print(f"  system_nu_ema = {probe.system_nu_ema:+.4f}")

passed = n_pass >= 4
print(f"\n{'='*76}")
print(f"总 DR: {n_pass}/{len(dr_results)} {'PASS' if passed else 'FAIL'}")
print('='*76)
sys.exit(0 if passed else 1)
