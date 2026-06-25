"""Experiment 3: consumable heat source + shadow layer cross-modal coupling.

Observe:
1. Shadow layer cross-axis weights: intra-vestibular vs cross-modal
2. Heat source depletion → "memory" in weights (object permanence)
3. Deep coupling: does shadow w(oto_x, therm) encode spatial relationship?
"""
import sys, math
sys.path.insert(0, "d:\\cell-cc")

from nexus_v1.circuit.variant_adapter import VariantCircuit
from nexus_v1.components.world import HeatSource, Body, World

# ── Setup ──
heat_src = HeatSource(position=[60.0, 50.0, 50.0], energy=100.0,
                      temperature=5.0, radius=25.0)
body = Body(position=[55.0, 50.0, 50.0])
body.velocity = [0.05, 0.0, 0.0]
world = World(heat_sources=[heat_src], body=body)

c = VariantCircuit()
c.world = world

STEPS = 30000
DT = 0.001

print("=" * 70)
print("Experiment 3: Consumable Heat + Shadow Cross-Modal Coupling")
print("=" * 70)

# ── Track shadow cross-axis weights ──
def get_shadow_cross_weights():
    w = {}
    for bid, bundle in c.shadow_sandbox.bundles.items():
        if bid.startswith("s_cross_"):
            w[bid] = bundle.mean_weight()
    return w

def classify_weights(w):
    intra = {k: v for k, v in w.items() if 'therm' not in k}
    cross = {k: v for k, v in w.items() if 'therm' in k}
    return intra, cross

# ── Run ──
shadow_history = []
for step in range(STEPS):
    t = step * DT
    signal = {
        'yaw': 5.0 * math.sin(3.0 * t),
        'pitch': 3.0 * math.sin(2.0 * t + 0.5),
        'roll': 2.0 * math.sin(1.5 * t + 1.0),
        'oto_x': 4.0 * math.sin(4.0 * t),
        'oto_y': 3.0 * math.sin(2.5 * t + 0.3),
        'oto_z': 5.0 * math.sin(3.0 * t + 0.7),
    }
    c.step(signal, dt=DT)

    # Record every 5000 steps
    if step % 5000 == 0:
        w = get_shadow_cross_weights()
        intra, cross = classify_weights(w)
        shadow_history.append({
            'step': step,
            'heat_energy': heat_src.energy,
            'col_therm': next((n.activation for k, n in c.column_neurons.items() if 'therm' in k), 0.0),
            'intra_avg': sum(intra.values()) / max(1, len(intra)),
            'cross_avg': sum(cross.values()) / max(1, len(cross)),
            'intra_max': max(intra.values()) if intra else 0,
            'cross_max': max(cross.values()) if cross else 0,
            'cross_detail': dict(cross),
            'K_ema': c.shadow_sandbox._k_ema,
            'nu': c.shadow_sandbox._nu,
        })

        pos = c.world.body.position
        T = c.world.temperature_at(pos)
        dist = math.sqrt(sum((pos[i]-heat_src.position[i])**2 for i in range(3)))

        print(f"\n--- Step {step:>6d} ---")
        print(f"  Body: [{pos[0]:.2f}, {pos[1]:.2f}, {pos[2]:.2f}]  "
              f"dist={dist:.1f}  T={T:.4f}")
        print(f"  Heat source: E={heat_src.energy:.1f}  T_eff={heat_src.effective_temperature():.3f}")
        print(f"  Col therm: {next((n.activation for k, n in c.column_neurons.items() if 'therm' in k), 0.0):.6f}")

        # Shadow state
        print(f"  Shadow neurons: {len(c.shadow_sandbox.neurons)}")
        print(f"  Shadow bundles: {len(c.shadow_sandbox.bundles)}")
        print(f"  Shadow K_ema: {c.shadow_sandbox._k_ema:.8f}")
        print(f"  Shadow nu: {c.shadow_sandbox._nu:.10f}")

        # Shadow cross-axis weights
        i_avg = sum(intra.values()) / max(1, len(intra))
        c_avg = sum(cross.values()) / max(1, len(cross))
        print(f"  Cross-axis weights: intra_avg={i_avg:.6f} ({len(intra)})  "
              f"cross_avg={c_avg:.6f} ({len(cross)})")

        # Show cross-modal weights individually
        for k, v in sorted(cross.items()):
            print(f"    {k}: {v:.6f}")

# ── Final Analysis ──
print("\n" + "=" * 70)
print("SHADOW LAYER CROSS-MODAL COUPLING ANALYSIS")
print("=" * 70)

print("\nWeight evolution over time:")
header = f"{'Step':>6}  {'Heat_E':>7}  {'Col_T':>8}  {'Intra':>10}  {'Cross':>10}  {'Ratio':>8}  {'K_ema':>12}"
print(header)
print("-" * len(header))
for h in shadow_history:
    i_avg = h['intra_avg']
    c_avg = h['cross_avg']
    ratio = c_avg / i_avg if i_avg > 1e-8 else 0
    print(f"{h['step']:>6}  {h['heat_energy']:>7.1f}  {h['col_therm']:>8.6f}  "
          f"{i_avg:>10.6f}  {c_avg:>10.6f}  {ratio:>8.4f}  {h['K_ema']:>12.8f}")

# Did the weights differentiate?
if len(shadow_history) >= 2:
    first = shadow_history[0]
    last = shadow_history[-1]
    i_growth = (last['intra_avg'] / max(first['intra_avg'], 1e-8)) - 1
    c_growth = (last['cross_avg'] / max(first['cross_avg'], 1e-8)) - 1
    print(f"\nWeight growth: intra={i_growth:+.1%}  cross={c_growth:+.1%}")

# Shadow cross-modal detail at end
print(f"\nFinal shadow cross-modal weights:")
w = get_shadow_cross_weights()
_, cross = classify_weights(w)
for k, v in sorted(cross.items()):
    # Mark as self-geometry (intra) or world-knowledge (cross)
    kind = "WORLD" if "therm" in k else "SELF"
    print(f"  {k}: {v:.6f}  [{kind}]")

# Enc-to-col weight comparison (main circuit)
print(f"\nMain circuit enc-to-col weights:")
for b in c.bundles_enc_to_col:
    print(f"  {b.id}: {b.mean_weight():.6f}")
