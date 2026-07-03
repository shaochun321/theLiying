"""50k步验证实验：ThermalDeltaNeuron + CPG削减后 relay_to_da STDP 方向翻转

目标：验证 EXP-BASE-200K 中的 LTD 模式是否翻转为 LTP。
预期（commit 37e664e）：
  - relay_to_da front 从 LTD（-82%）翻转为 LTP（> +0.005 增长）
  - ThermalDelta 在 body 接近热源时激活（warm-onset drive）
  - DA 在接近期间爆发，而非固定 2Hz（CPG 已减 10×）

实验设置与 200k 基线相同，但只跑 50k 步。
热源在 +y 方向（body=[50,50,25], src=[50,70,25]），使 front/back
成为主轴而 left/right 为侧轴，可清楚看到方向分化。
"""
import sys, os, time, math

sys.stdout.reconfigure(line_buffering=True)
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from nexus_v1.circuit.variant_adapter import VariantCircuit
from nexus_v1.components.world import HeatSource, Body, World

STEPS        = 50_000
DT           = 0.001
LOG_INTERVAL = 5_000

# ── World: 热源在 +y 方向，front patch (y+) 面向热源 ──────────────────────
src = HeatSource(position=[50.0, 70.0, 25.0], energy=50_000.0,
                 temperature=5.0, radius=30.0)
src._drift = [0.0, 0.0, 0.0]

body = Body(position=[50.0, 50.0, 25.0])
world = World(heat_sources=[src], body=body)
world.MIN_ALIVE = 0
world.REGEN_PROB = 0.0

# ── Circuit ────────────────────────────────────────────────────────────────
c = VariantCircuit()
c.world = world
c.somatosensory.LATERAL_GAIN = 0.3
for m in c.muscle_system.muscles:
    m.gain = 0.3


# ── Weight helpers ─────────────────────────────────────────────────────────
def _relay_to_da_weights():
    bundles = c.bundles_relay_to_da
    patch_ids = list(c.somatosensory.patch_ids)
    result = {}
    for i, pid in enumerate(patch_ids):
        if i < len(bundles):
            wm = bundles[i].weight_matrix()
            result[pid] = round(sum(wm[0]) / max(len(wm[0]), 1), 5) if wm else 0.0
    return result

def _thermo_delta_activations():
    """Current ThermalDeltaNeuron activations per patch."""
    return {pid: round(dn.activation, 5)
            for pid, dn in c.thermo_delta_neurons.items()}

def _da_mean():
    return sum(n.activation for n in c.da_neurons.values()) / max(len(c.da_neurons), 1)

def _patch_temps_brief():
    pt = c._patch_temps
    if not pt:
        return {k: 0.0 for k in ['front','back','left','right']}
    return {pid: round(pt.get(pid, (0,))[0], 3) for pid in ['front','back','left','right']}

def _dist():
    pos = list(world.body.position)
    return math.sqrt(sum((pos[i] - src.position[i])**2 for i in range(3)))

def _dr5():
    pt = c._patch_temps
    if not pt:
        return 0.0
    T_r = pt.get('right', (0,))[0]; T_l = pt.get('left',  (0,))[0]
    T_f = pt.get('front', (0,))[0]; T_b = pt.get('back',  (0,))[0]
    bv = world.body.velocity
    vx = bv[0] if len(bv) > 0 else 0.0
    vy = bv[1] if len(bv) > 1 else 0.0
    return (T_r - T_l) * vx + (T_f - T_b) * vy


# ── Init ───────────────────────────────────────────────────────────────────
t0 = time.time()
print("=" * 80)
print("VALIDATE ThermalDeltaNeuron (50k steps) | src=[50,70,25] front=+y | CPG×0.1")
print("Expect: relay_to_da front LTP (flip from -82% LTD in 200k baseline)")
print("=" * 80)

# Force DA circuit init by running 1 step
_sig0 = {'yaw':0,'pitch':0,'roll':0,'oto_x':0,'oto_y':0,'oto_z':0}
c.step(_sig0, dt=DT)
ws_r2d_init = _relay_to_da_weights()
print(f"\n初始权重 (after 1st step, DA circuit lazy-init):")
print(f"  relay_to_da : {ws_r2d_init}")
print(f"  thermo_delta_neurons registered: {list(c.thermo_delta_neurons.keys())}")
print(f"  bundles_thermo_delta_to_da: {len(c.bundles_thermo_delta_to_da)}")
print(f"  CPG synapse_gain: {c.bundles_cpg_to_da[0].config.synapse_gain if c.bundles_cpg_to_da else 'N/A'}")

hdr = (f"{'step':>6}  {'d':>5} {'fill':>5} {'DA':>6}  "
       f"{'T_f':>5} {'T_b':>5}  "
       f"{'td_f':>6} {'td_b':>6}  "
       f"{'r2d_F':>7} {'r2d_B':>7} {'r2d_R':>7} {'r2d_L':>7}  "
       f"{'DR5':>7}")
print(f"\n{hdr}")
print("-" * len(hdr))

dr5_pos = dr5_tot = 0

for step in range(2, STEPS + 1):
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

    dv = _dr5()
    bv = world.body.velocity
    if dv != 0.0 or any(abs(v) > 1e-8 for v in bv):
        dr5_tot += 1
        if dv > 0:
            dr5_pos += 1

    if step % LOG_INTERVAL == 0:
        d = _dist()
        fill = c.energy_store.fill_fraction
        da = _da_mean()
        pt = _patch_temps_brief()
        td = _thermo_delta_activations()
        ws = _relay_to_da_weights()
        dr5_pct = 100.0 * dr5_pos / max(dr5_tot, 1)

        row = (f"{step:>6d}  {d:>5.1f} {fill:>5.3f} {da:>6.4f}  "
               f"{pt.get('front',0):>5.3f} {pt.get('back',0):>5.3f}  "
               f"{td.get('front',0):>6.4f} {td.get('back',0):>6.4f}  "
               f"{ws.get('front',0):>7.5f} {ws.get('back',0):>7.5f} "
               f"{ws.get('right',0):>7.5f} {ws.get('left',0):>7.5f}  "
               f"{dr5_pct:>6.1f}%")
        print(row)
        dr5_pos = dr5_tot = 0

# ── Final ──────────────────────────────────────────────────────────────────
elapsed = time.time() - t0
ws_r2d_fin = _relay_to_da_weights()
print(f"\n{'=' * 80}")
print(f"DONE {STEPS}步 | {elapsed:.0f}s ({elapsed/STEPS*1000:.2f}ms/step)")
print(f"\nrelay_to_da 权重 (初始 → 终态 → Δ):")
for pid in ['front', 'back', 'left', 'right']:
    w0 = ws_r2d_init.get(pid, 0)
    w1 = ws_r2d_fin.get(pid, 0)
    print(f"  {pid:6s}: {w0:.5f} → {w1:.5f}  Δ={w1-w0:+.5f}")

wF0 = ws_r2d_init.get('front', 0); wF1 = ws_r2d_fin.get('front', 0)
print(f"\n方向翻转检验 (期望 ΔwFront > 0):")
print(f"  ΔwFront = {wF1-wF0:+.5f}  {'✓ LTP' if wF1-wF0 > 0 else '✗ still LTD'}")

wB1 = ws_r2d_fin.get('back', 0)
print(f"  wFront - wBack = {wF1-wB1:+.5f}  {'✓ direction!' if wF1>wB1 else '— not yet'}")
print(f"  Fill: {c.energy_store.fill_fraction:.4f}")
print(f"  DA mean: {_da_mean():.4f}")
