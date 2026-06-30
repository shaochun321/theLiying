"""Phase 5 Route A: Single-Parameter Scan — 50k steps each.

Goal: isolate which parameter (oto amplitude vs muscle gain) drives DR2 success.
Three conditions tested sequentially:
  Cond 1: oto=6.0, gain=0.1 (only oto raised, baseline gain)
  Cond 2: oto=3.0, gain=0.3 (only gain raised, baseline oto)
  Cond 3: oto=6.0, gain=0.3 (both raised — v2 reference)

Key metric: body displacement at 50k steps and body speed.
"""
import sys, math, os, time
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from nexus_v1.circuit.variant_adapter import VariantCircuit
from nexus_v1.components.world import HeatSource, Body, World

STEPS = 50_000
DT = 0.001

CONDITIONS = [
    {'label': 'Cond1: oto=6.0 gain=0.1 (only oto↑)', 'oto': 6.0, 'gain': 0.1},
    {'label': 'Cond2: oto=3.0 gain=0.3 (only gain↑)', 'oto': 3.0, 'gain': 0.3},
    {'label': 'Cond3: oto=6.0 gain=0.3 (both↑, v2)', 'oto': 6.0, 'gain': 0.3},
]

results = []

print("=" * 70)
print("Phase 5 Route A: Single-Parameter Scan (50k steps × 3 conditions)")
print("=" * 70)

for cond in CONDITIONS:
    print(f"\n── {cond['label']} ──")
    heat = HeatSource(position=[70.0, 50.0, 50.0], energy=500.0,
                      temperature=5.0, radius=30.0)
    heat._drift = [0.0, 0.0, 0.0]
    body = Body(position=[50.0, 50.0, 50.0])
    world = World(heat_sources=[heat], body=body)
    world.MIN_ALIVE = 0
    world.REGEN_PROB = 0.0

    init_pos = list(body.position)
    init_dist = math.sqrt(sum((p - h)**2 for p, h in zip(body.position, heat.position)))

    c = VariantCircuit()
    c.world = world
    c.somatosensory.LATERAL_GAIN = 0.3
    for m in c.muscle_system.muscles:
        m.gain = cond['gain']

    _stdp_applied = False
    motor_ema_max = 0.0
    fill_start = None
    t0 = time.time()

    for step in range(STEPS):
        t_sim = step * DT
        signal = {
            'yaw':   2.0 * math.sin(1.5 * t_sim),
            'pitch': 1.5 * math.sin(1.0 * t_sim),
            'roll':  1.0 * math.sin(0.7 * t_sim),
            'oto_x': cond['oto'] * math.sin(2.0 * t_sim),
            'oto_y': cond['oto'] * math.sin(2.5 * t_sim + 0.3),
            'oto_z': cond['oto'] * math.sin(3.0 * t_sim + 0.7),
        }
        c.step(signal, dt=DT)

        if not _stdp_applied and step >= 1 and c.bundles_soma_to_da:
            for b in c.bundles_soma_to_da:
                b.config.stdp_lr = 0.005
            _stdp_applied = True

        if fill_start is None:
            fill_start = c.energy_store.fill_fraction

        motor_ema = max(mot._activation_ema for mot in c.motor_neurons.values())
        if motor_ema > motor_ema_max:
            motor_ema_max = motor_ema

    elapsed = time.time() - t0
    pos = list(c.world.body.position)
    dist = math.sqrt(sum((p - h)**2 for p, h in zip(pos, heat.position)))
    dx = pos[0] - init_pos[0]
    total_disp = math.sqrt(sum((p - i)**2 for p, i in zip(pos, init_pos)))
    bv = c.world.body.velocity
    speed = math.sqrt(sum(v*v for v in bv))
    fill_end = c.energy_store.fill_fraction
    fill_drain = (fill_start - fill_end) / (STEPS / 10000)

    # Weight diff
    bda = c.bundles_soma_to_da[0] if c.bundles_soma_to_da else None
    wdiff = 0.0
    if bda:
        wm = bda.weight_matrix()
        w_lr = {}
        for i, pid in enumerate(c.somatosensory.patch_ids):
            if pid in ('left', 'right'):
                w_lr[pid] = sum(wm[i]) / max(len(wm[i]), 1)
        if 'left' in w_lr and 'right' in w_lr:
            wdiff = abs(w_lr['right'] - w_lr['left'])

    r = {
        'label': cond['label'], 'oto': cond['oto'], 'gain': cond['gain'],
        'dx': dx, 'total_disp': total_disp, 'speed': speed,
        'motor_ema_max': motor_ema_max, 'fill_end': fill_end,
        'fill_drain_per10k': fill_drain, 'wdiff': wdiff,
        'elapsed': elapsed,
    }
    results.append(r)

    print(f"  Δx={dx:+.4f}  disp={total_disp:.4f}  speed={speed:.5f}")
    print(f"  motor_ema_peak={motor_ema_max:.4f}  fill={fill_end:.3f}  drain/10k={fill_drain:.4f}")
    print(f"  |Δw|={wdiff:.4f}  ({elapsed:.0f}s, {STEPS/elapsed:.0f}/s)")

# ─── Summary ─────────────────────────────────────────────────────────────────
print("\n" + "=" * 70)
print("Summary: Single-Parameter Scan")
print("=" * 70)
print(f"\n{'Condition':<35} {'Δx@50k':>8} {'speed':>8} {'fill':>6} {'drain/10k':>10} {'|Δw|':>7}")
print("-" * 75)
for r in results:
    label_short = r['label'].split(':')[0]
    print(f"{r['label']:<35} {r['dx']:>+8.4f} {r['speed']:>8.5f} "
          f"{r['fill_end']:>6.3f} {r['fill_drain_per10k']:>10.4f} {r['wdiff']:>7.4f}")

print("\nConclusion:")
c1, c2, c3 = results
oto_contribution = c1['dx'] / max(abs(c3['dx']), 1e-6)
gain_contribution = c2['dx'] / max(abs(c3['dx']), 1e-6)
print(f"  oto=6.0 alone → {c1['dx']:+.4f} Δx ({oto_contribution:.0%} of v2 combined)")
print(f"  gain=0.3 alone → {c2['dx']:+.4f} Δx ({gain_contribution:.0%} of v2 combined)")
print(f"  Both combined  → {c3['dx']:+.4f} Δx (v2 reference)")
if abs(c1['dx']) > abs(c2['dx']):
    print("  → oto amplitude is the DOMINANT factor for body displacement")
else:
    print("  → muscle gain is the DOMINANT factor for body displacement")

print("=" * 70)
sys.exit(0)
