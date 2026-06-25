"""Experiment 2: Timing differentiation + weight evolution analysis."""
import sys, math
sys.path.insert(0, "d:\\cell-cc")

from nexus_v1.circuit.variant_adapter import VariantCircuit
from nexus_v1.components.world import HeatSource, Body, World

heat_src = HeatSource(position=[60.0, 50.0, 50.0], energy=200.0,
                      temperature=5.0, radius=25.0)
body = Body(position=[55.0, 50.0, 50.0])
body.velocity = [0.05, 0.0, 0.0]
world = World(heat_sources=[heat_src], body=body)

c = VariantCircuit()
c.world = world

# Track WHEN each binding first activates
first_active = {}
bind_ids = list(c.binding_layer.cells.keys())
cross_modal = sorted([b for b in bind_ids if 'therm' in b])
intra_vest = sorted([b for b in bind_ids if 'therm' not in b])

# Track weight evolution
weight_history = []

STEPS = 20000
for step in range(STEPS):
    t = step * 0.001
    signal = {
        'yaw': 5.0 * math.sin(3.0 * t),
        'pitch': 3.0 * math.sin(2.0 * t + 0.5),
        'roll': 2.0 * math.sin(1.5 * t + 1.0),
        'oto_x': 4.0 * math.sin(4.0 * t),
        'oto_y': 3.0 * math.sin(2.5 * t + 0.3),
        'oto_z': 5.0 * math.sin(3.0 * t + 0.7),
    }
    c.step(signal, dt=0.001)

    # Check binding activation timing
    col_act = {ax: c.column_neurons[ax].activation for ax in c.all_axes}
    b_act = c.binding_layer.compute_all(col_act)
    for bid, act in b_act.items():
        if act > 0.001 and bid not in first_active:
            first_active[bid] = step

    # Track weights every 2000 steps
    if step % 2000 == 0:
        ws = {}
        for b in c.bundles_enc_to_col:
            ws[b.id] = b.mean_weight()
        weight_history.append((step, ws))

# ── RESULTS ──
print("=" * 60)
print("TIMING DIFFERENTIATION")
print("=" * 60)

print("\nIntra-vestibular (first activation step):")
for bid in intra_vest:
    t = first_active.get(bid, -1)
    print(f"  {bid}: step {t}")

print("\nCross-modal (first activation step):")
for bid in cross_modal:
    t = first_active.get(bid, -1)
    print(f"  {bid}: step {t}")

# Averages
intra_t = [first_active.get(b, -1) for b in intra_vest if first_active.get(b, -1) > 0]
cross_t = [first_active.get(b, -1) for b in cross_modal if first_active.get(b, -1) > 0]
avg_intra = sum(intra_t) / len(intra_t) if intra_t else -1
avg_cross = sum(cross_t) / len(cross_t) if cross_t else -1
print(f"\nAvg first activation: intra={avg_intra:.0f}  cross={avg_cross:.0f}")
if avg_intra > 0 and avg_cross > 0:
    print(f"Delay (cross - intra): {avg_cross - avg_intra:.0f} steps")
    print(f"Cross-modal bindings activate {(avg_cross/avg_intra):.1f}x later")

print("\n" + "=" * 60)
print("WEIGHT DIFFERENTIATION (enc_to_col)")
print("=" * 60)

header = f"{'Step':>6}  {'vest_avg':>10}  {'therm':>10}  {'ratio':>8}  {'divergence':>12}"
print(header)
print("-" * len(header))
initial_ratio = None
for step, ws in weight_history:
    vest_keys = [k for k in ws if 'therm' not in k]
    vest_avg = sum(ws[k] for k in vest_keys) / len(vest_keys) if vest_keys else 0
    therm_w = ws.get('enc_to_col_therm', 0)
    ratio = therm_w / vest_avg if vest_avg > 0 else 0
    if initial_ratio is None:
        initial_ratio = ratio
    divergence = ratio - initial_ratio
    print(f"{step:>6}  {vest_avg:>10.6f}  {therm_w:>10.6f}  {ratio:>8.4f}  {divergence:>+12.6f}")

print("\n" + "=" * 60)
print("MOTOR DIAGNOSIS")
print("=" * 60)

for k, mot in c.motor_neurons.items():
    ch = mot._channels.get("default")
    th = ch.v_threshold if ch else "?"
    print(f"  {k}: V={mot._membrane.voltage:.6f}  act={mot.activation:.6f}"
          f"  E={mot.energy:.4f}  threshold={th}")

b = c.bundles_col_to_motor[0]
print(f"\n  Col->Motor synapse_gain: {b.config.synapse_gain}")
print(f"  Col->Motor mean_weight: {b.mean_weight():.6f}")
print(f"  Col->Motor base_gain: {c._base_col_mot_gain}")

# Check if homeostasis is throttling
print(f"\n  Motor homeostasis check:")
avg_e = sum(m.energy for m in c.motor_neurons.values()) / len(c.motor_neurons)
print(f"  Avg motor energy: {avg_e:.4f}")
print(f"  E_CRIT=0.3, E_SCALE=0.5")
if avg_e < 0.5:
    print(f"  WARNING: Energy < E_SCALE → synaptic scaling may be active")

# Shadow layer
print("\n" + "=" * 60)
print("SHADOW LAYER STATUS")
print("=" * 60)
sb = c.shadow_sandbox
print(f"  Contraction: {sb._contraction:.6f}")
print(f"  K_ema: {sb._K_ema:.6f}")
print(f"  Nu: {sb._nu:.6f}")
