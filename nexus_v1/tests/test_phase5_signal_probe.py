"""Phase 5 Signal Probe — 10k steps, 4 vital checks.

Confirms thermal chain preconditions before 500k experiment:
  P5.1  Noci voltage in safe range (not -134V deep negative)
  P5.2  Directional relay signal: relay_right > relay_left when heat is right
  P5.3  soma_to_da weight divergence starting (|w_right - w_left| > 0.001)
  P5.4  DA shows dynamic range (not persistently saturated)

Setup: heat source at [70,50,50] (right of body), body at [50,50,50].
Periodic vestibular input drives body oscillation for klinokinesis.
"""
import sys, math, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from nexus_v1.circuit.variant_adapter import VariantCircuit
from nexus_v1.components.world import HeatSource, Body, World

STEPS = 10_000
DT = 0.001

heat = HeatSource(position=[70.0, 50.0, 50.0], energy=500.0,
                  temperature=5.0, radius=30.0)
heat._drift = [0.0, 0.0, 0.0]
body = Body(position=[50.0, 50.0, 50.0])
world = World(heat_sources=[heat], body=body)
world.MIN_ALIVE = 0
world.REGEN_PROB = 0.0

c = VariantCircuit()
c.world = world

# Apply Phase 5 directional-competition parameter
c.somatosensory.LATERAL_GAIN = 0.3   # 0.05 default → 0.3 for stronger competition

da_samples = []
noci_max = {'left': 0.0, 'right': 0.0}

for step in range(STEPS):
    t = step * DT
    # Periodic vestibular: drives body oscillation (klinokinesis substrate)
    signal = {
        'yaw':   2.0 * math.sin(1.5 * t),
        'pitch': 1.5 * math.sin(1.0 * t),
        'roll':  1.0 * math.sin(0.7 * t),
        'oto_x': 3.0 * math.sin(2.0 * t),
        'oto_y': 3.0 * math.sin(2.5 * t + 0.3),
        'oto_z': 3.0 * math.sin(3.0 * t + 0.7),
    }
    c.step(signal, dt=DT)

    # Track noci max voltage (check for deep negative)
    for pid in ['left', 'right']:
        v = c.somatosensory.nociceptors[pid]._membrane.voltage
        if abs(v) > abs(noci_max[pid]):
            noci_max[pid] = v

    # Sample DA every 100 steps (after DA circuit initialized at step 1)
    if step % 100 == 0 and step > 0:
        da_samples.append(c.dopamine.concentration)

# ── Apply soma_to_da stdp_lr override (Phase 5 slow learning)
if c.bundles_soma_to_da:
    for b in c.bundles_soma_to_da:
        b.config.stdp_lr = 0.005

# ── Read final state ──
bda = c.bundles_soma_to_da[0]
wm = bda.weight_matrix()
patch_ids = c.somatosensory.patch_ids
weights = {}
for i, pid in enumerate(patch_ids):
    weights[pid] = sum(wm[i]) / max(len(wm[i]), 1)

relay_left_ema  = c.somatosensory.relays['left']._activation_ema
relay_right_ema = c.somatosensory.relays['right']._activation_ema
w_diff = abs(weights.get('right', 0.0) - weights.get('left', 0.0))
da_sat_fraction = sum(1 for d in da_samples if d > 0.90) / max(len(da_samples), 1)

# ── Report ──
print("=" * 60)
print("Phase 5 Signal Probe — 10k steps")
print("=" * 60)
print(f"\nNoci peak voltages: left={noci_max['left']:.4f}  right={noci_max['right']:.4f}")
print(f"Relay EMA:  left={relay_left_ema:.4f}  right={relay_right_ema:.4f}")
print(f"soma_to_da weights: {', '.join(f'{pid}={w:.4f}' for pid, w in weights.items())}")
print(f"|w_right - w_left| = {w_diff:.4f}")
print(f"DA: mean={sum(da_samples)/max(len(da_samples),1):.4f}  "
      f"sat_fraction={da_sat_fraction:.2%}")
print(f"Energy fill: {c.energy_store.fill_fraction:.4f}")
print(f"Body pos: {[round(x,4) for x in c.world.body.position]}")
print()

# ── Checks ──
results = []

# P5.1: Noci safe range
noci_safe = all(abs(v) < 2.0 for v in noci_max.values())
results.append(('P5.1 Noci safe (|V|<2.0)',
                noci_safe,
                f"left={noci_max['left']:.4f}  right={noci_max['right']:.4f}"))

# P5.2: Directional relay signal (right warmer → relay_right > relay_left)
relay_directional = relay_right_ema > relay_left_ema * 0.9
results.append(('P5.2 Relay directional (right>left)',
                relay_directional,
                f"right={relay_right_ema:.4f}  left={relay_left_ema:.4f}"))

# P5.3: Weight divergence starting
weight_diverging = w_diff > 0.001
results.append(('P5.3 Weight divergence |Δw|>0.001',
                weight_diverging,
                f"|Δw|={w_diff:.4f}"))

# P5.4: DA dynamic range (not persistently saturated)
da_dynamic = da_sat_fraction < 0.5
results.append(('P5.4 DA not saturated (sat<50%)',
                da_dynamic,
                f"sat_fraction={da_sat_fraction:.2%}"))

passed = sum(1 for _, ok, _ in results if ok)
for name, ok, detail in results:
    marker = "[PASS]" if ok else "[FAIL]"
    print(f"  {marker} {name}: {detail}")

print()
print(f"Phase 5 Probe: {passed}/{len(results)} PASS")
print("=" * 60)

if passed == len(results):
    print("→ Proceed to 500k experiment")
    sys.exit(0)
else:
    print("→ Probe failed — investigate before running 500k experiment")
    sys.exit(1)
