"""Feeding mechanism diagnostic — trace the full energy pipeline."""
import math
from nexus_v1.circuit.variant_adapter import VariantCircuit

c = VariantCircuit()

# === Initial State ===
print("=== ENERGY STORE CONFIG ===")
print(f"  capacity          = {c.energy_store.config.capacity}")
print(f"  initial_fill      = {c.energy_store.config.initial_fill}")
print(f"  initial_level     = {c.energy_store.level:.2f}")
print(f"  basal_drain/step  = {c.energy_store.config.basal_drain}")
print(f"  max_deposit/step  = {c.energy_store.config.max_deposit_per_step}")
print(f"  deposit_efficiency= {c.energy_store.config.deposit_efficiency}")
print(f"  CONSUME_RATE      = 0.15 (hardcoded in variant_adapter.step)")

# === Heat Source ===
hs = c.world.heat_sources[0]
print(f"\n=== HEAT SOURCE [0] ===")
print(f"  position     = {hs.position}")
print(f"  radius       = {hs.radius}")
print(f"  energy       = {hs.energy}")
print(f"  temperature  = {hs.temperature}")
print(f"  effective_T  = {hs.effective_temperature():.2f}")
print(f"  num_sources  = {len(c.world.heat_sources)}")

# === Organism position ===
body = c.world.body
dist = math.sqrt(sum((a-b)**2 for a,b in zip(body.position, hs.position)))
print(f"\n=== ORGANISM vs HEAT SOURCE ===")
print(f"  body.position       = {body.position}")
print(f"  distance_to_source  = {dist:.1f}")
print(f"  in_feeding_radius?  = {dist < hs.radius} (radius={hs.radius})")

# === consume_nearby at various distances ===
print(f"\n=== CONSUME_NEARBY(rate=0.15, dt=0.001) vs DISTANCE ===")
dt = 0.001
for d in [0, 2, 5, 8, 10, 15, 19, 20, 25]:
    test_pos = [hs.position[0] + d, hs.position[1], hs.position[2]]
    # Use fresh world to avoid depleting source
    c_test = VariantCircuit()
    absorbed = c_test.world.consume_nearby(test_pos, 0.15, dt)
    print(f"  d={d:3d}: absorbed={absorbed:.8f}")

# === Basal drain math ===
basal_per_step = c.energy_store.config.basal_drain * dt
print(f"\n=== BASAL DRAIN MATH ===")
print(f"  basal_drain * dt = {c.energy_store.config.basal_drain} * {dt} = {basal_per_step:.8f}")
print(f"  drain over 50k steps = {basal_per_step * 50_000:.4f}")
print(f"  drain over 100k steps = {basal_per_step * 100_000:.4f}")

# === Run near source (d=5) via step() ===
print(f"\n=== 10k STEPS NEAR SOURCE (d=5) via step() ===")
c_near = VariantCircuit()
c_near.world.body.position = [hs.position[0]+5, hs.position[1], hs.position[2]]
s0 = c_near.energy_store.summary()
for step in range(10_000):
    c_near.step({"yaw": 0.3}, dt)
s1 = c_near.energy_store.summary()
dep = s1["total_deposited"] - s0["total_deposited"]
wdr = s1["total_withdrawn"] - s0["total_withdrawn"]
bsl = s1["total_basal_drain"] - s0["total_basal_drain"]
print(f"  deposited:    {s0['total_deposited']:.6f} -> {s1['total_deposited']:.6f}  (delta={dep:.6f})")
print(f"  withdrawn:    {s0['total_withdrawn']:.6f} -> {s1['total_withdrawn']:.6f}  (delta={wdr:.6f})")
print(f"  basal_drain:  {s0['total_basal_drain']:.8f} -> {s1['total_basal_drain']:.8f}  (delta={bsl:.8f})")
print(f"  level:        {s0['level']:.4f} -> {s1['level']:.4f}")
print(f"  fill:         {s0['fill_fraction']:.4f} -> {s1['fill_fraction']:.4f}")

# === Run far from source (d=50) via step() ===
print(f"\n=== 10k STEPS FAR FROM SOURCE (d=50) via step() ===")
c_far = VariantCircuit()
c_far.world.body.position = [10.0, 10.0, 10.0]
s0f = c_far.energy_store.summary()
for step in range(10_000):
    c_far.step({"yaw": 0.3}, dt)
s1f = c_far.energy_store.summary()
dep_f = s1f["total_deposited"] - s0f["total_deposited"]
wdr_f = s1f["total_withdrawn"] - s0f["total_withdrawn"]
bsl_f = s1f["total_basal_drain"] - s0f["total_basal_drain"]
print(f"  deposited:    {s0f['total_deposited']:.6f} -> {s1f['total_deposited']:.6f}  (delta={dep_f:.6f})")
print(f"  withdrawn:    {s0f['total_withdrawn']:.6f} -> {s1f['total_withdrawn']:.6f}  (delta={wdr_f:.6f})")
print(f"  basal_drain:  {s0f['total_basal_drain']:.8f} -> {s1f['total_basal_drain']:.8f}  (delta={bsl_f:.8f})")
print(f"  level:        {s0f['level']:.4f} -> {s1f['level']:.4f}")
print(f"  fill:         {s0f['fill_fraction']:.4f} -> {s1f['fill_fraction']:.4f}")

# === Net energy balance ===
print(f"\n=== NET ENERGY BALANCE (10k steps) ===")
print(f"  Near source:  income={dep:.6f}  expense={wdr+bsl:.6f}  net={dep-wdr-bsl:.6f}")
print(f"  Far from src: income={dep_f:.6f}  expense={wdr_f+bsl_f:.6f}  net={dep_f-wdr_f-bsl_f:.6f}")
print(f"  → Feeding contribution: {dep - dep_f:.6f} more energy from proximity")
