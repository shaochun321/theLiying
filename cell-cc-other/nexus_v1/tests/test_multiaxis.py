"""Task A: Multi-axis joint input — verify spatial integration + lateral inhibition."""
import sys
sys.path.insert(0, '.')
from nexus_v1.circuit.variant_adapter import VariantCircuit

print("=" * 70)
print("Task A: Multi-Axis Joint Input Verification")
print("=" * 70)

# ── Test 1: Single axis (baseline) ──
print("\n── Test 1: Single axis (yaw=0.8) ──")
c1 = VariantCircuit()
for _ in range(5000):
    c1.step({'yaw': 0.8}, 0.001)
print(f"  Col activations:")
for ax in c1.vestibular.axes:
    col = c1.column_neurons[ax]
    print(f"    {ax:>8s}: act={col.activation:>7.4f}  energy={col.energy:.3f}")
mot1 = {k: len(m.spike_times) for k, m in c1.motor_neurons.items()}
print(f"  Motor spikes: {mot1}")

# ── Test 2: Two axes (yaw + pitch) ──
print("\n── Test 2: Two axes (yaw=0.8, pitch=0.6) ──")
c2 = VariantCircuit()
for _ in range(5000):
    c2.step({'yaw': 0.8, 'pitch': 0.6}, 0.001)
print(f"  Col activations:")
for ax in c2.vestibular.axes:
    col = c2.column_neurons[ax]
    print(f"    {ax:>8s}: act={col.activation:>7.4f}  energy={col.energy:.3f}")
mot2 = {k: len(m.spike_times) for k, m in c2.motor_neurons.items()}
print(f"  Motor spikes: {mot2}")

# ── Test 3: Three axes (yaw + pitch + oto_x) ──
print("\n── Test 3: Three axes (yaw=0.8, pitch=0.6, oto_x=0.4) ──")
c3 = VariantCircuit()
for _ in range(5000):
    c3.step({'yaw': 0.8, 'pitch': 0.6, 'oto_x': 0.4}, 0.001)
print(f"  Col activations:")
for ax in c3.vestibular.axes:
    col = c3.column_neurons[ax]
    print(f"    {ax:>8s}: act={col.activation:>7.4f}  energy={col.energy:.3f}")
mot3 = {k: len(m.spike_times) for k, m in c3.motor_neurons.items()}
print(f"  Motor spikes: {mot3}")

# ── Test 4: All axes ──
print("\n── Test 4: All 6 axes ──")
c4 = VariantCircuit()
inputs = {'yaw': 0.8, 'pitch': 0.6, 'roll': 0.3, 'oto_x': 0.4, 'oto_y': 0.2, 'oto_z': 0.5}
for _ in range(5000):
    c4.step(inputs, 0.001)
print(f"  Col activations:")
for ax in c4.vestibular.axes:
    col = c4.column_neurons[ax]
    print(f"    {ax:>8s}: act={col.activation:>7.4f}  energy={col.energy:.3f}  (input={inputs.get(ax,0):.1f})")
mot4 = {k: len(m.spike_times) for k, m in c4.motor_neurons.items()}
print(f"  Motor spikes: {mot4}")

# ── Test 5: Lateral inhibition check ──
print("\n── Test 5: Lateral Inhibition Verification ──")
# Compare single-axis col activation vs multi-axis
# In multi-axis, lateral inhibition should suppress weaker axes
col_single = c1.column_neurons['yaw'].activation
col_multi = c4.column_neurons['yaw'].activation
print(f"  Yaw col (single-axis): {col_single:.4f}")
print(f"  Yaw col (all-axes):    {col_multi:.4f}")
suppression = (1.0 - col_multi / max(col_single, 0.001)) * 100
print(f"  Suppression from lateral inhibition: {suppression:.1f}%")

# ── Test 6: Weight evolution with multi-axis ──
print("\n── Test 6: STDP Weight Evolution (multi-axis, 5s) ──")
for b in c4.get_all_bundles():
    bid = b.config.bundle_id
    if 'enc_to_col' in bid or 'col_to_motor' in bid:
        print(f"  {bid:<25s}: w={b.mean_weight():.4f} (init={b.config.initial_weight})")

# ── Verdict ──
print("\n── VERDICT ──")
checks = []
# V1: Active axes have non-zero col activation
for ax in ['yaw', 'pitch', 'oto_x']:
    act = c3.column_neurons[ax].activation
    ok = abs(act) > 0.001
    checks.append(ok)
    status = "✓" if ok else "✗"
    print(f"  {status} Active axis {ax}: col_act={act:.4f} > 0")

# V2: Inactive axes have zero/near-zero activation
for ax in ['roll', 'oto_y', 'oto_z']:
    act = c3.column_neurons[ax].activation
    ok = abs(act) < 0.1
    checks.append(ok)
    status = "✓" if ok else "✗"
    print(f"  {status} Inactive axis {ax}: col_act={act:.4f} ≈ 0")

# V3: More active axes → more motor output
ok3 = sum(mot3.values()) >= sum(mot1.values())
checks.append(ok3)
status = "✓" if ok3 else "✗"
print(f"  {status} More axes → more motor: {sum(mot3.values())} >= {sum(mot1.values())}")

# V4: All-axis no energy depletion
min_e = min(n.energy for n in c4.get_all_neurons())
ok4 = min_e > 0.001
checks.append(ok4)
status = "✓" if ok4 else "✗"
print(f"  {status} All-axis energy safe: min={min_e:.4f}")

# V5: Lateral inhibition exists
ok5 = suppression > 0
checks.append(ok5)
status = "✓" if ok5 else "✗"
print(f"  {status} Lateral inhibition active: {suppression:.1f}%")

passed = sum(checks)
total = len(checks)
print(f"\n  RESULT: {passed}/{total} checks passed")
if passed == total:
    print(f"  ★ MULTI-AXIS INTEGRATION VERIFIED")
