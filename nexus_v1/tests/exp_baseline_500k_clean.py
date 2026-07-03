"""单热源 500k 步干净基线实验

**目的**：在 HC-009/013/014/017/021/022/024 全部修复后，建立第一条干净基线。
重点测量：
  (1) thermo_to_relay patch-specific 权重分化（HC-009 后首次可测，STDP 路径）
  (2) relay_to_da 方向学习（wFront vs wBack）
  (3) DR5（patch 温差版，电路可感知，非全知梯度）
  (4) DA 活跃度与能量生存

**热源布局**：单热源在 +x 方向 d=20，即 src=[70,50,25]，body=[50,50,25]。
方向预期：right patch > left patch；若 STDP 正常，relay_to_da wR > wL 在数万步内出现。

**2026-07-03 commit 1f7733d 之后运行**。
"""
import sys, os, time, math

sys.stdout.reconfigure(line_buffering=True)
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from nexus_v1.circuit.variant_adapter import VariantCircuit
from nexus_v1.components.world import HeatSource, Body, World
from nexus_v1.ledger import NuProbe

STEPS        = 200_000
DT           = 0.001
LOG_INTERVAL = 20_000

# ── World setup ───────────────────────────────────────────────────────────────
src = HeatSource(position=[70.0, 50.0, 25.0], energy=50_000.0,
                 temperature=5.0, radius=30.0)
src._drift = [0.0, 0.0, 0.0]

body = Body(position=[50.0, 50.0, 25.0])
world = World(heat_sources=[src], body=body)
world.MIN_ALIVE = 0
world.REGEN_PROB = 0.0

# ── Circuit ───────────────────────────────────────────────────────────────────
c = VariantCircuit()
c.world = world
c.somatosensory.LATERAL_GAIN = 0.3
for m in c.muscle_system.muscles:
    m.gain = 0.3

probe = NuProbe(ema_alpha=0.001)


# ── Weight helpers ────────────────────────────────────────────────────────────
def _relay_to_da_weights():
    """Per-patch relay→DA weights (alias: bundles_soma_to_da)."""
    bundles = c.bundles_relay_to_da
    patch_ids = list(c.somatosensory.patch_ids)
    result = {}
    for i, pid in enumerate(patch_ids):
        if i < len(bundles):
            wm = bundles[i].weight_matrix()
            result[pid] = round(sum(wm[0]) / max(len(wm[0]), 1), 5) if wm else 0.0
    return result

def _thermo_to_relay_weights():
    """Per-patch thermo→relay weights (STDP, should differentiate)."""
    result = {}
    for pid, b in c.somatosensory.bundles_thermo_to_relay.items():
        wm = b.weight_matrix()
        result[pid] = round(sum(wm[0]) / max(len(wm[0]), 1), 5) if wm else 0.0
    return result

def _patch_thermo():
    """Current thermo_activation per patch."""
    if not c._patch_temps:
        return {}
    so = c.somatosensory.get_output()
    return {pid: round(so[pid]["thermo_activation"], 4) for pid in so}

def _dr5_patch():
    """DR5 from patch temperature gradient × body velocity (circuit-sensible)."""
    pt = c._patch_temps   # dict: pid → (T, dT, damage)
    if not pt:
        return 0.0
    T_r = pt.get('right', (0,))[0]
    T_l = pt.get('left',  (0,))[0]
    T_f = pt.get('front', (0,))[0]
    T_b = pt.get('back',  (0,))[0]
    bv = world.body.velocity
    vx = bv[0] if len(bv) > 0 else 0.0
    vy = bv[1] if len(bv) > 1 else 0.0
    return (T_r - T_l) * vx + (T_f - T_b) * vy


# ── Header ────────────────────────────────────────────────────────────────────
t0 = time.time()
print("=" * 72)
print("BASELINE 500k  |  single +x source [70,50,25]  |  dt=0.001")
print("HC-009/013/014/017/021/022/024 全修复后首次干净基线")
print("=" * 72)

ws_t2r_init = _thermo_to_relay_weights()
ws_r2d_init = _relay_to_da_weights()
print(f"\n初始权重:")
print(f"  thermo_to_relay: {ws_t2r_init}")
print(f"  relay_to_da:     {ws_r2d_init}")

hdr = (f"{'step':>7}  {'d':>5} {'fill':>5} {'DA':>6}  "
       f"{'T_r':>5} {'T_l':>5} {'T_f':>5} {'T_b':>5}  "
       f"{'t2r_R':>7} {'t2r_L':>7} {'t2r_F':>7} {'t2r_B':>7}  "
       f"{'r2d_R':>7} {'r2d_L':>7} {'r2d_F':>7} {'r2d_B':>7}  "
       f"{'DR5%':>5}")
print(f"\n{hdr}")
print("-" * len(hdr))

dr5_pos = 0
dr5_tot = 0

# ── Main loop ─────────────────────────────────────────────────────────────────
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
    probe.update(c, step, dt=DT)

    # DR5 tracking
    dv = _dr5_patch()
    bv = world.body.velocity
    if dv != 0.0 or any(abs(v) > 1e-8 for v in bv):
        dr5_tot += 1
        if dv > 0:
            dr5_pos += 1

    if step % LOG_INTERVAL == 0:
        pos = list(world.body.position)
        d = math.sqrt(sum((pos[i] - src.position[i])**2 for i in range(3)))
        fill = c.energy_store.fill_fraction
        da_mean = sum(n.activation for n in c.da_neurons.values()) / max(len(c.da_neurons), 1)

        pt = _patch_thermo()
        ws_t2r = _thermo_to_relay_weights()
        ws_r2d = _relay_to_da_weights()
        dr5_pct = 100.0 * dr5_pos / max(dr5_tot, 1)

        row = (f"{step:>7d}  {d:>5.1f} {fill:>5.3f} {da_mean:>6.4f}  "
               f"{pt.get('right',0):>5.3f} {pt.get('left',0):>5.3f} "
               f"{pt.get('front',0):>5.3f} {pt.get('back',0):>5.3f}  "
               f"{ws_t2r.get('right',0):>7.5f} {ws_t2r.get('left',0):>7.5f} "
               f"{ws_t2r.get('front',0):>7.5f} {ws_t2r.get('back',0):>7.5f}  "
               f"{ws_r2d.get('right',0):>7.5f} {ws_r2d.get('left',0):>7.5f} "
               f"{ws_r2d.get('front',0):>7.5f} {ws_r2d.get('back',0):>7.5f}  "
               f"{dr5_pct:>5.1f}")
        print(row)
        dr5_pos = 0
        dr5_tot = 0

# ── Final ─────────────────────────────────────────────────────────────────────
elapsed = time.time() - t0
ws_t2r_fin = _thermo_to_relay_weights()
ws_r2d_fin = _relay_to_da_weights()
print(f"\n{'=' * 72}")
print(f"DONE  {STEPS}步  |  {elapsed:.0f}s  ({elapsed/STEPS*1000:.2f}ms/step)")
print(f"\n最终权重:")
print(f"  thermo_to_relay: {ws_t2r_fin}")
print(f"  relay_to_da:     {ws_r2d_fin}")
t2r_diff = {pid: round(ws_t2r_fin.get(pid, 0) - ws_t2r_init.get(pid, 0), 5) for pid in ws_t2r_fin}
r2d_diff = {pid: round(ws_r2d_fin.get(pid, 0) - ws_r2d_init.get(pid, 0), 5) for pid in ws_r2d_fin}
print(f"\n权重变化量 Δ:")
print(f"  Δthermo_to_relay: {t2r_diff}")
print(f"  Δrelay_to_da:     {r2d_diff}")

wR = ws_r2d_fin.get('right', 0)
wL = ws_r2d_fin.get('left', 0)
wF = ws_r2d_fin.get('front', 0)
wB = ws_r2d_fin.get('back', 0)
print(f"\n方向学习检验:")
print(f"  wR - wL = {wR - wL:+.5f}  (期望 > 0，热源在 +x/right)")
print(f"  wB - wF = {wB - wF:+.5f}")

print(f"\nFill fraction: {c.energy_store.fill_fraction:.4f}")
print(f"DA mean:       {sum(n.activation for n in c.da_neurons.values())/max(len(c.da_neurons),1):.4f}")
