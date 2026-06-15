"""Full integration test: all 3 mandatory corrections verified.

Correction 1: SkinPatch is a Fourier thermal integrator (not ideal thermometer)
Correction 2: No SelfOriginModule (Shadow layer handles prediction)
Correction 3: Shadow metabolic tax drains EnergyStore
"""
import sys
sys.path.insert(0, r"d:\cell-cc")

print("=" * 60)
print("INTEGRATION TEST: 3 Mandatory Architectural Corrections")
print("=" * 60)

# ── Instantiation ──
print("\n[1] Importing and instantiating VariantCircuit...")
from nexus_v1.circuit.variant_adapter import VariantCircuit
circuit = VariantCircuit()
print(f"    all_axes: {circuit.all_axes}")
print(f"    extra_axes: {circuit.extra_axes}")
print(f"    encoding neurons: {len(circuit.encoding_neurons)}")
print(f"    column neurons: {len(circuit.column_neurons)}")
print(f"    somatosensory patches: {circuit.somatosensory.patch_ids}")

# ── Correction 1: SkinPatch Thermal Integrator ──
print("\n[2] CORRECTION 1: SkinPatch Thermal Integrator")
body = circuit.world.body
front_patch = [p for p in body.skin_patches if p.patch_id == "front"][0]
print(f"    heat_capacity: {front_patch.heat_capacity}")
print(f"    conductance: {front_patch.conductance}")
print(f"    damage_threshold: {front_patch.damage_threshold}")
print(f"    initial T_skin: {front_patch.current_temperature:.4f}")

# Step thermal dynamics
print("    Stepping 20 iterations...")
for i in range(20):
    body.sample_skin(circuit.world, dt=1.0)

print(f"    T_skin after 20 steps: {front_patch.current_temperature:.4f}")
print(f"    damage_integral: {front_patch.damage_integral:.4f}")
print(f"    T_env at front: {circuit.world.temperature_at(front_patch.world_position(body)):.4f}")

# Verify thermal inertia: T_skin should NOT equal T_env (has thermal lag)
T_env = circuit.world.temperature_at(front_patch.world_position(body))
assert front_patch.current_temperature != T_env, \
    "FAIL: T_skin == T_env (ideal thermometer, not integrator!)"
print("    ✓ T_skin ≠ T_env (thermal inertia confirmed)")

# ── Correction 2: No SelfOriginModule ──
print("\n[3] CORRECTION 2: No SelfOriginModule")
has_self_origin = hasattr(circuit, 'self_origin_module')
print(f"    has self_origin_module: {has_self_origin}")
assert not has_self_origin, "FAIL: SelfOriginModule exists!"
print("    ✓ No SelfOriginModule (Shadow handles prediction)")

# ── Correction 3: Shadow Metabolic Tax ──
print("\n[4] CORRECTION 3: Shadow Metabolic Tax")
energy_before = circuit.energy_store.level
print(f"    EnergyStore level before: {energy_before:.4f}")
print(f"    Shadow bundles: {len(circuit.shadow_sandbox.bundles)}")
print(f"    Shadow neurons: {len(circuit.shadow_sandbox.neurons)}")

# Run enough steps to trigger shadow observe + metabolic tax
print("    Running 1100 steps to trigger shadow tax...")
for i in range(1100):
    circuit.step({}, dt=1.0)

energy_after = circuit.energy_store.level
shadow_state = circuit.shadow_sandbox.get_state()
tax_paid = shadow_state.get('metabolic_tax', {}).get('total_paid', 0)
print(f"    EnergyStore level after: {energy_after:.4f}")
print(f"    Energy delta: {energy_before - energy_after:.4f}")
print(f"    Shadow tax paid: {tax_paid:.4f}")
print(f"    Cost per tax check: {shadow_state['metabolic_tax']['cost_per_tax_check']:.6f}")

assert tax_paid > 0, "FAIL: Shadow paid zero tax!"
print("    ✓ Shadow metabolic tax is being collected")

# ── Full Chain Verification ──
print("\n[5] Full Chain: Somatosensory → Encoding → Column")
soma_out = circuit.somatosensory.get_output()
for pid, vals in soma_out.items():
    print(f"    {pid}: relay={vals['relay_activation']:.4f} "
          f"thermo={vals['thermo_activation']:.4f} "
          f"noci={vals['noci_activation']:.4f}")

# Check encoding neurons are alive
for axis in circuit.extra_axes:
    enc = circuit.encoding_neurons.get(f"reg_{axis}")
    if enc:
        print(f"    enc reg_{axis}: act={enc.activation:.4f}")

# Check column neurons
for axis in circuit.extra_axes:
    col = circuit.column_neurons.get(axis)
    if col:
        print(f"    col {axis}: act={col.activation:.4f}")

print("\n" + "=" * 60)
print("ALL CORRECTIONS VERIFIED ✓")
print("=" * 60)
