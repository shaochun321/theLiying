"""P0 真实基线实验 — 100k 步，三热源，无 HC-005/006/012 污染"""
import sys, time, math, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__)))

from nexus_v1.circuit.variant_adapter import VariantCircuit
from nexus_v1.components.world import HeatSource, Body, World
from nexus_v1.ledger import NuProbe

STEPS = 100_000
DT = 0.001
LOG = 20_000

src1 = HeatSource(position=[80.0, 50.0, 25.0], energy=10_000.0, temperature=5.0, radius=30.0)
src2 = HeatSource(position=[35.0, 76.0, 25.0], energy=10_000.0, temperature=5.0, radius=30.0)
src3 = HeatSource(position=[35.0, 24.0, 25.0], energy=10_000.0, temperature=5.0, radius=30.0)
src1._drift = src2._drift = src3._drift = [0.0, 0.0, 0.0]

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

def _dist(pos, src): return math.sqrt(sum((p-h)**2 for p,h in zip(pos, src.position)))
def _near(pos): return min(_dist(pos,src1), _dist(pos,src2), _dist(pos,src3))
def _weights(c):
    if not c.bundles_soma_to_da: return {}
    b = c.bundles_soma_to_da[0]; wm = b.weight_matrix()
    return {pid: sum(wm[i])/max(len(wm[i]),1) for i,pid in enumerate(c.somatosensory.patch_ids)}

init_pos = list(body.position)
init_dist = _near(init_pos)
gdv_total = gdv_pos = 0
_stdp_applied = False

print(f"P0 Baseline | init_dist={init_dist:.2f} | {STEPS//1000}k steps", flush=True)
print(f"{'step':>7}  {'d_near':>7}  {'fill':>6}  {'DR5%':>6}  {'wR-wL':>9}  {'t(s)':>5}", flush=True)
t0 = time.time()

for step in range(STEPS):
    c.step({}, dt=DT)
    probe.update(c, step, dt=DT)

    if not _stdp_applied and step >= 1 and c.bundles_soma_to_da:
        for b in c.bundles_soma_to_da: b.config.stdp_lr = 0.005
        _stdp_applied = True

    pos = list(c.world.body.position)
    bv = c.world.body.velocity
    pt = c._patch_temps
    if pt:
        pg = [pt.get('right',(0,))[0]-pt.get('left',(0,))[0], 0.0,
              pt.get('front',(0,))[0]-pt.get('back',(0,))[0]]
        dot_p = sum(pg[i]*bv[i] for i in range(3))
        if dot_p != 0 or any(abs(v)>1e-8 for v in bv):
            gdv_total += 1
            if dot_p > 0: gdv_pos += 1

    if step % LOG == 0 or step == STEPS-1:
        dr5 = gdv_pos/max(gdv_total,1)*100
        ws = _weights(c); wdiff = ws.get('right',0)-ws.get('left',0)
        fill = c.energy_store.fill_fraction
        d_near = _near(pos)
        print(f"{step:>7}  {d_near:>7.3f}  {fill:>6.4f}  {dr5:>6.1f}%  {wdiff:>+9.5f}  ({time.time()-t0:.0f}s)", flush=True)

pos_f = list(c.world.body.position)
d_f = _near(pos_f)
dr5_f = gdv_pos/max(gdv_total,1)*100
fill_f = c.energy_store.fill_fraction
ws_f = _weights(c)
dist_red = init_dist - d_f

print("\n" + "="*60, flush=True)
print("P0 Baseline DR (无 HC-005/006/012 污染)", flush=True)
print("="*60, flush=True)
results = [
    ("DR1 |wR-wL|>0.005",     abs(ws_f.get('right',0)-ws_f.get('left',0))>0.005, f"wR-wL={ws_f.get('right',0)-ws_f.get('left',0):+.5f}"),
    ("DR2 dist_red>1.0",      dist_red>1.0,  f"red={dist_red:.3f} (init={init_dist:.2f}→{d_f:.2f})"),
    ("DR3 fill>0.05",         fill_f>0.05,   f"fill={fill_f:.4f}"),
    ("DR5 patch-grad.v>50%",  dr5_f>50.0,    f"{dr5_f:.1f}% ({gdv_pos}/{gdv_total})"),
]
n = 0
for desc, ok, val in results:
    print(f"  [{'PASS' if ok else 'FAIL'}] {desc}  ({val})", flush=True)
    if ok: n += 1
print(f"  system_nu_ema={probe.system_nu_ema:+.4f}  charge={probe.charging_fraction:.1%}", flush=True)
print(f"\n{n}/{len(results)} DR PASS", flush=True)
