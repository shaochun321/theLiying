"""B0诊断 + 200k基线实验

目标：
  1. B0 - 诊断 B-layer V_slow 实际幅度和 ema_up vs ema_down 不平衡度
  2. 200k基线 - 采集 ν 分布（mean/std/90th），作为 C1 阈值设定数据基础
  3. 记录 DR5、距离、relay权重演化

热源：[70,50,25]，T=5，radius=30（静止）。Body 初始 [50,50,25]。
dt=0.001，步数 200k。
"""
import sys, os, time, math
sys.stdout.reconfigure(line_buffering=True)
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from nexus_v1.circuit.variant_adapter import VariantCircuit
from nexus_v1.components.world import HeatSource, Body, World

STEPS        = 200_000
DT           = 0.001
LOG_INTERVAL = 20_000

src  = HeatSource(position=[70.0, 50.0, 25.0], energy=50_000.0,
                  temperature=5.0, radius=30.0)
src._drift = [0.0, 0.0, 0.0]
body = Body(position=[50.0, 50.0, 25.0])
world = World(heat_sources=[src], body=body)
world.MIN_ALIVE = 0
world.REGEN_PROB = 0.0

c = VariantCircuit()
c.world = world
c.somatosensory.LATERAL_GAIN = 0.3
for m in c.muscle_system.muscles:
    m.gain = 0.3


# ── B-layer 诊断：追踪 enc_to_col[0] 的 coupler V_slow ──
def _blayer_vslows():
    """从 enc_to_col 和 aff_to_enc 各取一条 bundle 的 V_slow。"""
    vs_enc_col = 0.0
    vs_aff_enc = 0.0
    if c.bundles_enc_to_col:
        b = c.bundles_enc_to_col[0]
        if b._couplers:
            vs_enc_col = b._couplers[0]._v_slow
    if c.bundles_vest_to_enc:
        b = c.bundles_vest_to_enc[0]
        if b._couplers:
            vs_aff_enc = b._couplers[0]._v_slow
    return vs_enc_col, vs_aff_enc


def _ema_balance():
    """追踪 enc_to_col[0] 的 ema_up vs ema_down (B-layer 输入)。"""
    if not c.bundles_enc_to_col:
        return 0.0, 0.0
    b = c.bundles_enc_to_col[0]
    ema_up = sum(s._activation_ema for s in b.sources) / max(len(b.sources), 1)
    ema_dn = b.targets[0]._activation_ema if b.targets else 0.0
    return ema_up, ema_dn


def _r2d_weights():
    bundles = c.bundles_relay_to_da
    patch_ids = list(c.somatosensory.patch_ids)
    result = {}
    for i, pid in enumerate(patch_ids):
        if i < len(bundles):
            wm = bundles[i].weight_matrix()
            result[pid] = round(sum(wm[0]) / max(len(wm[0]), 1), 5) if wm else 0.0
    return result


def _patch_T():
    pt = c._patch_temps
    if not pt:
        return {k: 0.0 for k in ('right', 'left', 'front', 'back')}
    return {pid: round(pt[pid][0], 3) for pid in pt}


def _current_dist():
    pos = list(world.body.position)
    return math.sqrt(sum((pos[i] - src.position[i])**2 for i in range(3)))


_prev_dist_ring = [None] * 1000
_dist_ring_idx  = 0


def _dr5_approaching(current_d):
    global _dist_ring_idx
    past_d = _prev_dist_ring[_dist_ring_idx]
    _prev_dist_ring[_dist_ring_idx] = current_d
    _dist_ring_idx = (_dist_ring_idx + 1) % 1000
    if past_d is None:
        return False
    return current_d < past_d


# ── ν 分布采集 ──
nu_samples = []

t0 = time.time()
print("=" * 100)
print("B0诊断 + 200k基线  |  +x 热源 [70,50,25]  |  200k 步")
print("追踪：ν分布(C1阈值) + B-layer V_slow(B0诊断) + relay_to_da权重 + DR5")
print("=" * 100)

hdr = (f"{'step':>7}  {'d':>5} {'yaw°':>7}  "
       f"{'nu_ema':>8}  "
       f"{'vs_enc':>8} {'vs_aff':>8}  "
       f"{'ema_up':>7} {'ema_dn':>7}  "
       f"{'T_r':>6} {'T_f':>6}  "
       f"{'r2d_R':>7} {'r2d_F':>7}  "
       f"{'DR5%':>5}")
print(f"\n{hdr}")
print("-" * len(hdr))

dr5_pos = dr5_tot = 0

for step in range(1, STEPS + 1):
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

    # ν 采样（每步，用于分布统计）
    try:
        nu_val = c.shadow_sandbox.get_state().get("nu", 0.0)
    except Exception:
        nu_val = 0.0
    nu_samples.append(nu_val)

    _d_now = _current_dist()
    if _dr5_approaching(_d_now):
        dr5_pos += 1
    dr5_tot += 1

    if step % LOG_INTERVAL == 0:
        d       = _d_now
        yaw_deg = math.degrees(world.body.yaw)
        pt      = _patch_T()
        r2d     = _r2d_weights()
        vs_ec, vs_ae = _blayer_vslows()
        eu, ed  = _ema_balance()
        dr5_pct = 100.0 * dr5_pos / max(dr5_tot, 1)

        # 当前窗口 ν 统计
        window = nu_samples[-LOG_INTERVAL:]
        nu_mean_w = sum(window) / len(window)

        print(f"{step:>7d}  {d:>5.1f} {yaw_deg:>7.2f}  "
              f"{nu_mean_w:>8.5f}  "
              f"{vs_ec:>8.5f} {vs_ae:>8.5f}  "
              f"{eu:>7.4f} {ed:>7.4f}  "
              f"{pt.get('right', 0):>6.3f} {pt.get('front', 0):>6.3f}  "
              f"{r2d.get('right', 0):>7.5f} {r2d.get('front', 0):>7.5f}  "
              f"{dr5_pct:>5.1f}")
        dr5_pos = dr5_tot = 0

elapsed = time.time() - t0

# ── ν 分布统计 ──
nu_arr = sorted(nu_samples)
n      = len(nu_arr)
nu_mean = sum(nu_arr) / n
nu_var  = sum((x - nu_mean) ** 2 for x in nu_arr) / n
nu_std  = nu_var ** 0.5
nu_10th = nu_arr[int(n * 0.10)]
nu_50th = nu_arr[int(n * 0.50)]
nu_90th = nu_arr[int(n * 0.90)]
nu_min  = nu_arr[0]
nu_max  = nu_arr[-1]

# B-layer 总结（最终快照）
vs_ec_fin, vs_ae_fin = _blayer_vslows()
eu_fin, ed_fin = _ema_balance()

# 最终状态
d_fin   = _current_dist()
yaw_fin = math.degrees(world.body.yaw)
pos_fin = [round(x, 1) for x in world.body.position]
r2d_fin = _r2d_weights()

print(f"\n{'=' * 100}")
print(f"DONE  {STEPS}步  |  {elapsed:.0f}s  ({elapsed/STEPS*1000:.2f} ms/step)")
print()
print("── ν 分布统计（C1 阈值依据）──")
print(f"  nu_min   = {nu_min:.6f}")
print(f"  nu_10th  = {nu_10th:.6f}")
print(f"  nu_mean  = {nu_mean:.6f}")
print(f"  nu_50th  = {nu_50th:.6f}  (中位数)")
print(f"  nu_std   = {nu_std:.6f}")
print(f"  nu_90th  = {nu_90th:.6f}  ← C1 主方案阈值候选")
print(f"  nu_max   = {nu_max:.6f}")
print(f"  nu_mean+1σ = {nu_mean + nu_std:.6f}  ← C1 备选阈值")
print()
print("── B0 诊断：B-layer ema平衡度（最终快照）──")
print(f"  enc_to_col[0]: ema_up={eu_fin:.4f}  ema_dn={ed_fin:.4f}  "
      f"diff={eu_fin - ed_fin:+.4f}  V_slow={vs_ec_fin:.5f}")
print(f"  aff_to_enc[0]: V_slow={vs_ae_fin:.5f}")
print(f"  B-layer 理论 V_slow* = gm × diff × R_slow = "
      f"0.01 × {eu_fin-ed_fin:+.4f} × 10 = {0.01*(eu_fin-ed_fin)*10:.5f}")
print()
print("── 行为摘要 ──")
print(f"  最终 d   = {d_fin:.1f}  (期望 < 20)")
print(f"  最终 yaw = {yaw_fin:.2f}°")
print(f"  最终 pos = {pos_fin}")
print(f"  relay_to_da: R={r2d_fin.get('right',0):.5f}  F={r2d_fin.get('front',0):.5f}  "
      f"L={r2d_fin.get('left',0):.5f}  B={r2d_fin.get('back',0):.5f}")
