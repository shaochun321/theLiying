"""Experiment 5: Cross-modal directional learning.

THE definitive test: can the system learn "heat is in +x direction"
from temporal correlations between movement and temperature change?

Setup:
  - Heat source at [60, 50, 50] (in +x direction from body)
  - Body oscillates in x (toward/away from heat) → dT/dt correlates with v_x
  - Body does NOT oscillate in y or z → no dT/dt correlation with v_y, v_z

Prediction:
  If cross-modal Hebbian works: w(oto_x, therm) > w(oto_y, therm)
  = the system has learned "heat is in the x direction"
  WITHOUT any directional thermal sensor
"""
import sys, math
import os; sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from nexus_v1.circuit.variant_adapter import VariantCircuit
from nexus_v1.components.world import HeatSource, Body, World

# Heat source at +x from body
heat_src = HeatSource(position=[58.0, 50.0, 50.0], energy=500.0,
                      temperature=8.0, radius=20.0)
body = Body(position=[50.0, 50.0, 50.0])  # 8 units from heat
world = World(heat_sources=[heat_src], body=body)

c = VariantCircuit()
c.world = world

STEPS = 60000
DT = 0.001

print("=" * 70)
print("Experiment 5: Cross-Modal Directional Learning")
print("=" * 70)
print(f"Heat at [58, 50, 50] → +x direction from body")
print(f"Body oscillates in x-axis only → dT/dt correlates with oto_x")
print()

# Track
shadow_history = []
therm_history = []

for step in range(STEPS):
    t = step * DT

    # KEY: Vestibular input with STRONG x-axis component,
    # weaker y/z to create directional asymmetry
    signal = {
        'yaw': 2.0 * math.sin(2.0 * t),
        'pitch': 1.0 * math.sin(1.5 * t),
        'roll': 0.5 * math.sin(1.0 * t),
        'oto_x': 5.0 * math.sin(3.0 * t),    # STRONG x-axis
        'oto_y': 1.0 * math.sin(2.0 * t),     # weak y
        'oto_z': 1.0 * math.sin(2.0 * t),     # weak z
    }
    c.step(signal, dt=DT)

    # Record thermal signal every 100 steps
    if step % 100 == 0:
        state = c.thermal_membrane.get_state()
        therm_history.append({
            'step': step,
            'adapted': state['adapted'],
            'col_therm': c.column_neurons['therm'].activation,
            'pos_x': c.world.body.position[0],
            'vel_x': c.world.body.velocity[0],
        })

    # Shadow weights every 10k steps
    if step % 10000 == 0:
        sw = {}
        for bid, bundle in c.shadow_sandbox.bundles.items():
            if 's_cross_' in bid and 'therm' in bid:
                sw[bid.replace('s_cross_', '').replace('_therm', '')] = bundle.mean_weight()
        shadow_history.append({'step': step, 'weights': sw})

        pos = c.world.body.position
        T_raw = c.world.temperature_at(pos)
        state = c.thermal_membrane.get_state()
        dist = math.sqrt(sum((pos[i]-heat_src.position[i])**2 for i in range(3)))

        print(f"--- Step {step:>6d} ---")
        print(f"  pos=[{pos[0]:.4f}, {pos[1]:.4f}, {pos[2]:.4f}]  dist={dist:.3f}")
        print(f"  T_raw={T_raw:.4f}  adapted={state['adapted']:.6f}")
        print(f"  col_therm={c.column_neurons['therm'].activation:.6f}")

        if sw:
            # Sort by weight
            sorted_sw = sorted(sw.items(), key=lambda x: x[1], reverse=True)
            print(f"  Shadow cross-modal weights:")
            for k, v in sorted_sw:
                marker = " ←" if k == "oto_x" else ""
                print(f"    {k}-therm: {v:.6f}{marker}")
        print()

# ── Final Analysis ──
print("=" * 70)
print("DIRECTIONAL LEARNING ANALYSIS")
print("=" * 70)

# 1. Did thermal signal grow?
print("\nThermal signal evolution:")
# Show therm at key points
for i in range(0, len(therm_history), len(therm_history)//10):
    h = therm_history[i]
    print(f"  step {h['step']:>6d}: adapted={h['adapted']:.6f}"
          f"  col_therm={h['col_therm']:.6f}  pos_x={h['pos_x']:.4f}")

# 2. Shadow weight asymmetry: THE KEY TEST
print("\nShadow cross-modal weight evolution:")
print(f"  {'Step':>6s}  {'oto_x':>10s}  {'oto_y':>10s}  {'oto_z':>10s}  {'yaw':>10s}  {'ratio x/y':>10s}")
print(f"  {'-'*6}  {'-'*10}  {'-'*10}  {'-'*10}  {'-'*10}  {'-'*10}")
for sh in shadow_history:
    w = sh['weights']
    if w:
        ox = w.get('oto_x', 0)
        oy = w.get('oto_y', 0)
        oz = w.get('oto_z', 0)
        yaw = w.get('yaw', 0)
        ratio = ox / oy if oy > 1e-8 else 0
        print(f"  {sh['step']:>6d}  {ox:>10.6f}  {oy:>10.6f}  {oz:>10.6f}  {yaw:>10.6f}  {ratio:>10.3f}")

# 3. Verdict
if len(shadow_history) >= 2:
    final = shadow_history[-1]['weights']
    if final:
        ox = final.get('oto_x', 0)
        oy = final.get('oto_y', 0)
        oz = final.get('oto_z', 0)

        if ox > oy * 1.2 and ox > oz * 1.2:
            print(f"\n>>> DIRECTIONAL LEARNING DETECTED! <<<")
            print(f"    w(oto_x, therm) = {ox:.6f}")
            print(f"    w(oto_y, therm) = {oy:.6f}")
            print(f"    Ratio: {ox/oy:.2f}x")
            print(f"    System learned: 'heat is in the x direction'")
        elif ox > oy:
            print(f"\n>>> WEAK directional signal: oto_x({ox:.6f}) > oto_y({oy:.6f})")
            print(f"    Ratio: {ox/oy:.2f}x (need >1.2x for strong)")
        else:
            print(f"\n>>> NO directional learning: oto_x({ox:.6f}) ≤ oto_y({oy:.6f})")
            print(f"    Cross-modal weights are not direction-selective")

# 4. Enc-to-col weights
print(f"\nMain circuit enc→col weights:")
for b in c.bundles_enc_to_col:
    print(f"  {b.id}: {b.mean_weight():.6f}")
