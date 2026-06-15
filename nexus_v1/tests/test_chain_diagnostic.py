"""Signal chain diagnostic: trace amplitude at every stage."""
import sys, math
import os; sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from nexus_v1.circuit.variant_adapter import VariantCircuit
from nexus_v1.components.world import HeatSource, Body, World

heat_src = HeatSource(position=[60.0, 50.0, 50.0], energy=200.0,
                      temperature=5.0, radius=25.0)
body = Body(position=[55.0, 50.0, 50.0])
body.velocity = [0.05, 0.0, 0.0]
world = World(heat_sources=[heat_src], body=body)
c = VariantCircuit()
c.world = world

# Run 20k steps to reach steady state
for step in range(20000):
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

print("=" * 70)
print("SIGNAL CHAIN DIAGNOSTIC (after 20k steps)")
print("=" * 70)

# Stage 1: MET
print("\n--- Stage 1: MET (mechanotransduction) ---")
for ax in ['yaw', 'oto_x']:
    met = c.vestibular.met_neurons[ax]
    print(f"  {ax}: V={met._membrane.voltage:.4f}  "
          f"act={met.activation:.4f}  E={met.energy:.4f}")

# Stage 2: HairCell
print("\n--- Stage 2: HairCell ---")
for ax in ['yaw', 'oto_x']:
    hc = c.vestibular.haircell_neurons[ax]
    print(f"  {ax}: V={hc._membrane.voltage:.4f}  "
          f"act={hc.activation:.4f}  E={hc.energy:.4f}")

# Stage 3: Afferent
print("\n--- Stage 3: Afferent ---")
for ax in ['yaw', 'oto_x']:
    r = c.vestibular.afferent_regular[ax]
    i = c.vestibular.afferent_irregular[ax]
    print(f"  {ax} reg: V={r._membrane.voltage:.4f}  "
          f"act={r.activation:.6f}  E={r.energy:.4f}")
    print(f"  {ax} irr: V={i._membrane.voltage:.4f}  "
          f"act={i.activation:.6f}  E={i.energy:.4f}")

# Stage 4: Encoding
print("\n--- Stage 4: Encoding ---")
for ax in ['yaw', 'oto_x', 'therm']:
    for kind in ['reg', 'irr']:
        n = c.encoding_neurons[f"{kind}_{ax}"]
        print(f"  {kind}_{ax}: V={n._membrane.voltage:.4f}  "
              f"act={n.activation:.6f}  E={n.energy:.4f}")

# Stage 5: Column
print("\n--- Stage 5: Column ---")
for ax in c.all_axes:
    n = c.column_neurons[ax]
    print(f"  {ax}: V={n._membrane.voltage:.4f}  "
          f"act={n.activation:.6f}  E={n.energy:.4f}")

# Stage 6: Col->Motor bundle analysis
print("\n--- Stage 6: Col->Motor Bundle ---")
for b in c.bundles_col_to_motor:
    print(f"  bundle: {b.id}")
    print(f"  synapse_gain: {b.config.synapse_gain}")
    print(f"  mean_weight: {b.mean_weight():.6f}")
    print(f"  weight_max: {b.config.weight_max}")
    print(f"  n_sources: {len(b.sources)}, n_targets: {len(b.targets)}")

    # Propagate and measure currents
    currents = b.propagate()
    print(f"  propagated currents: {[round(val, 4) for val in currents]}")

    # Per-source contribution
    for i, src in enumerate(b.sources):
        total_G = 0
        for j in range(len(b.targets)):
            total_G += b._memristors[i][j].conductance
        I_contrib = abs(src.activation) * total_G * b.config.synapse_gain / len(b.targets)
        if abs(src.activation) > 0.01:
            print(f"    src {src.id}: act={src.activation:.4f} G_avg={total_G/len(b.targets):.4f} I_contrib={I_contrib:.4f}")

# Stage 7: Motor
print("\n--- Stage 7: Motor ---")
for k, mot in c.motor_neurons.items():
    ch = mot._channels.get("default")
    v_th = ch.v_threshold if ch else "?"
    r_s = mot.config.r_supply
    vdd = mot.config.vdd
    print(f"  {k}:")
    print(f"    V={mot._membrane.voltage:.6f}  act={mot.activation:.6f}  E={mot.energy:.4f}")
    print(f"    threshold={v_th}  R_supply={r_s}  VDD={vdd}")
    print(f"    bc_current={mot.config.bc_current}")

# PowerRail analysis
print("\n" + "=" * 70)
print("POWERRAIL MATHEMATICAL ANALYSIS")
print("=" * 70)
mot = c.motor_neurons["move_x"]
r_s = mot.config.r_supply
vdd = mot.config.vdd
E = mot.energy

b = c.bundles_col_to_motor[0]
currents = b.propagate()
I_per_motor = currents[0] if currents else 0

print(f"\n  V_supply = VDD * E / (1 + I * R_supply)")
print(f"  VDD = {vdd}, E = {E:.4f}, R_supply = {r_s}")
print(f"  I_input (from propagate) = {I_per_motor:.2f}")
V_supply = vdd * E / (1 + abs(I_per_motor) * r_s) if r_s > 0 else vdd
print(f"  V_supply = {vdd}*{E:.4f}/(1+{abs(I_per_motor):.2f}*{r_s}) = {V_supply:.6f}")
print(f"  Motor threshold = 0.3")
print(f"  V_supply < threshold? {V_supply < 0.3}")

# Calculate max allowed current
I_max = (1/0.3 - 1) / r_s if r_s > 0 else float('inf')
print(f"\n  For V_supply >= 0.3: I_max = (1/0.3 - 1) / {r_s} = {I_max:.1f}")
print(f"  Actual I = {abs(I_per_motor):.1f}")
print(f"  Overload factor: {abs(I_per_motor)/I_max:.1f}x")

# What gain would work?
if len(b.sources) > 0:
    # Without gain, what's the raw current?
    raw_I = sum(abs(s.activation) * b._memristors[b.sources.index(s)][0].conductance()
                for s in b.sources)
    print(f"\n  Raw current (gain=1): {raw_I:.4f}")
    ideal_gain = I_max / raw_I if raw_I > 0 else 0
    print(f"  Ideal gain for I <= I_max: {ideal_gain:.4f}")

# Enc->Col bundle analysis
print("\n--- Enc->Col Bundle Gains ---")
for b in c.bundles_enc_to_col:
    currents = b.propagate()
    I = currents[0] if currents else 0
    print(f"  {b.id}: gain={b.config.synapse_gain}  "
          f"w={b.mean_weight():.4f}  I_out={I:.4f}")

# Vestibular chain bundle analysis
print("\n--- Vestibular Chain Bundles ---")
for name in ['met_to_hc_yaw', 'hc_to_aff_yaw']:
    for b in c.vestibular.get_all_bundles():
        if b.id == name:
            print(f"  {name}: gain={b.config.synapse_gain}  w={b.mean_weight():.4f}")
            break
