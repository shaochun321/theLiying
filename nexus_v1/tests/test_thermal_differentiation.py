"""Experiment: thermal-vestibular coupling and binding layer differentiation.

Place the body NEAR the heat source and give it initial velocity.
Apply random vestibular perturbations to simulate natural movement.
Observe: do cross-modal binding nodes differentiate from intra-vestibular?
"""
import sys, math, random
import os; sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from nexus_v1.circuit.variant_adapter import VariantCircuit
from nexus_v1.components.world import HeatSource, Body, World

random.seed(42)

# ── Setup: body near heat source with initial velocity ──
heat_src = HeatSource(position=[65.0, 50.0, 50.0], energy=200.0,
                      temperature=5.0, radius=25.0)
body = Body(position=[55.0, 50.0, 50.0])  # 10 units from heat source
body.velocity = [0.05, 0.0, 0.0]  # initial push toward heat source
world = World(heat_sources=[heat_src], body=body)

c = VariantCircuit()
c.world = world  # replace default world

STEPS = 20000
DT = 0.001

# ── Tracking ──
bind_ids = list(c.binding_layer.cells.keys())
cross_modal = sorted([b for b in bind_ids if 'therm' in b])
intra_vest = sorted([b for b in bind_ids if 'therm' not in b])

# Track histories
history = {
    'body_x': [], 'body_y': [], 'body_z': [],
    'T_at_body': [],
    'enc_therm_reg': [], 'enc_therm_irr': [],
    'col_therm': [],
    'active_intra': [], 'active_cross': [],
    'motor_x': [], 'motor_y': [], 'motor_z': [],
    'bind_intra_mean': [], 'bind_cross_mean': [],
}

print("=" * 70)
print("Experiment: Thermal-Vestibular Coupling Differentiation")
print("=" * 70)
print(f"Body start: {body.position}, v={body.velocity}")
print(f"Heat source: pos={heat_src.position}, T={heat_src.temperature}, "
      f"E={heat_src.energy}, r={heat_src.radius}")
print(f"Steps: {STEPS}, dt={DT}")
print(f"Bindings: {len(intra_vest)} intra-vestibular, {len(cross_modal)} cross-modal")
print()

for step in range(STEPS):
    t = step * DT

    # Vestibular: sinusoidal + random noise (simulate natural movement)
    signal = {
        'yaw':   0.8 * math.sin(3.0 * t) + random.gauss(0, 0.1),
        'pitch': 0.5 * math.sin(2.0 * t + 0.5) + random.gauss(0, 0.1),
        'roll':  0.3 * math.sin(1.5 * t + 1.0) + random.gauss(0, 0.05),
        'oto_x': 0.6 * math.sin(4.0 * t) + random.gauss(0, 0.1),
        'oto_y': 0.4 * math.sin(2.5 * t + 0.3) + random.gauss(0, 0.1),
        'oto_z': 0.7 * math.sin(3.0 * t + 0.7) + random.gauss(0, 0.1),
    }

    c.step(signal, dt=DT)

    # Record every 100 steps
    if step % 100 == 0:
        pos = c.world.body.position
        T_body = c.world.temperature_at(pos)
        history['body_x'].append(pos[0])
        history['body_y'].append(pos[1])
        history['body_z'].append(pos[2])
        history['T_at_body'].append(T_body)
        history['enc_therm_reg'].append(c.encoding_neurons['reg_therm'].activation)
        history['enc_therm_irr'].append(c.encoding_neurons['irr_therm'].activation)
        history['col_therm'].append(c.column_neurons['therm'].activation)
        history['motor_x'].append(c.motor_neurons['move_x'].activation)
        history['motor_y'].append(c.motor_neurons['move_y'].activation)
        history['motor_z'].append(c.motor_neurons['move_z'].activation)

        # Binding layer
        col_act = {ax: c.column_neurons[ax].activation for ax in c.all_axes}
        b_act = c.binding_layer.compute_all(col_act)
        n_intra = sum(1 for b in intra_vest if b_act.get(b, 0) > 0.001)
        n_cross = sum(1 for b in cross_modal if b_act.get(b, 0) > 0.001)
        history['active_intra'].append(n_intra)
        history['active_cross'].append(n_cross)

        intra_acts = [b_act.get(b, 0) for b in intra_vest]
        cross_acts = [b_act.get(b, 0) for b in cross_modal]
        history['bind_intra_mean'].append(sum(intra_acts) / max(len(intra_acts), 1))
        history['bind_cross_mean'].append(sum(cross_acts) / max(len(cross_acts), 1))

    # Print progress
    if step % 5000 == 0 and step > 0:
        pos = c.world.body.position
        T_body = c.world.temperature_at(pos)
        dist = math.sqrt(sum((pos[i]-heat_src.position[i])**2 for i in range(3)))
        enc_r = c.encoding_neurons['reg_therm'].activation
        enc_i = c.encoding_neurons['irr_therm'].activation
        col_t = c.column_neurons['therm'].activation

        print(f"--- Step {step:>6d} ---")
        print(f"  Body: [{pos[0]:.2f}, {pos[1]:.2f}, {pos[2]:.2f}]  "
              f"dist_to_heat={dist:.1f}  T={T_body:.4f}")
        print(f"  Enc therm: reg={enc_r:.6f}  irr={enc_i:.6f}  Col={col_t:.6f}")
        print(f"  Motor: x={c.motor_neurons['move_x'].activation:.4f} "
              f"y={c.motor_neurons['move_y'].activation:.4f} "
              f"z={c.motor_neurons['move_z'].activation:.4f}")

        # Vestibular enc/col samples
        for ax in ['yaw', 'oto_x']:
            enc_act = c.encoding_neurons[f'reg_{ax}'].activation
            col_act_v = c.column_neurons[ax].activation
            print(f"  {ax}: enc={enc_act:.6f} col={col_act_v:.6f}")

        # Binding summary
        col_act_all = {ax: c.column_neurons[ax].activation for ax in c.all_axes}
        b_act = c.binding_layer.compute_all(col_act_all)
        n_intra = sum(1 for b in intra_vest if b_act.get(b, 0) > 0.001)
        n_cross = sum(1 for b in cross_modal if b_act.get(b, 0) > 0.001)
        print(f"  Bindings active: intra={n_intra}/{len(intra_vest)} "
              f"cross={n_cross}/{len(cross_modal)}")

        # Show all cross-modal binding activations
        for b in cross_modal:
            act = b_act.get(b, 0)
            if act > 0:
                print(f"    {b}: {act:.6f}")
        
        print(f"  Heat source energy: {heat_src.energy:.1f}")
        print()

# ── Final Analysis ──
print("=" * 70)
print("FINAL ANALYSIS")
print("=" * 70)

# 1. Body trajectory
print(f"\nBody trajectory range:")
print(f"  x: [{min(history['body_x']):.2f}, {max(history['body_x']):.2f}]")
print(f"  y: [{min(history['body_y']):.2f}, {max(history['body_y']):.2f}]")
print(f"  z: [{min(history['body_z']):.2f}, {max(history['body_z']):.2f}]")

# 2. Temperature range experienced
print(f"\nTemperature at body:")
print(f"  range: [{min(history['T_at_body']):.4f}, {max(history['T_at_body']):.4f}]")
print(f"  final: {history['T_at_body'][-1]:.4f}")

# 3. Thermal encoding
max_enc_r = max(abs(x) for x in history['enc_therm_reg'])
max_enc_i = max(abs(x) for x in history['enc_therm_irr'])
max_col_t = max(abs(x) for x in history['col_therm'])
print(f"\nThermal axis peak activations:")
print(f"  Enc reg (tonic):  {max_enc_r:.6f}")
print(f"  Enc irr (phasic): {max_enc_i:.6f}")
print(f"  Col therm:        {max_col_t:.6f}")

# 4. Binding differentiation
print(f"\nBinding layer differentiation:")
print(f"  Intra-vestibular mean activation: {sum(history['bind_intra_mean'])/len(history['bind_intra_mean']):.8f}")
print(f"  Cross-modal mean activation:      {sum(history['bind_cross_mean'])/len(history['bind_cross_mean']):.8f}")
max_intra_active = max(history['active_intra'])
max_cross_active = max(history['active_cross'])
print(f"  Max simultaneous active: intra={max_intra_active}/{len(intra_vest)}, "
      f"cross={max_cross_active}/{len(cross_modal)}")

# 5. PNN maturity comparison (if available)
print(f"\nColumn neuron states:")
for ax in c.all_axes:
    n = c.column_neurons[ax]
    print(f"  col_{ax}: V={n._membrane.voltage:.6f} act={n.activation:.6f} E={n.energy:.4f}")

# 6. Enc→Col bundle weights
print(f"\nEnc→Col bundle weights:")
for b in c.bundles_enc_to_col:
    w = b.mean_weight()
    print(f"  {b.id}: w={w:.6f}")

# 7. Col→Motor bundle weights
print(f"\nCol→Motor bundle (mean): {c.bundles_col_to_motor[0].mean_weight():.6f}")
