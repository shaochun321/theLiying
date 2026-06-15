"""EXP-016 诊断: Nociceptor 灵敏度推演

量化推演: vital脉搏 -> dT/dt -> Nociceptor 是否发火?
"""
import sys, math
sys.path.insert(0, "d:\\cell-cc")

from nexus_v1.components.world import SkinPatch, Body, World, HeatSource

# =====================================================================
# 1. 推演 vital 微位移产生的 dT
# =====================================================================
print("=" * 70)
print("EXP-016 NOCICEPTOR SENSITIVITY DIAGNOSIS")
print("=" * 70)

# Setup: body at [50,50,50], heat source at [70,50,50], r=30
body = Body(position=[50.0, 50.0, 50.0])
heat_src = HeatSource(position=[70.0, 50.0, 50.0], energy=500.0,
                      temperature=5.0, radius=30.0)
heat_src._drift = [0.0, 0.0, 0.0]
world = World(heat_sources=[heat_src], body=body)
world.MIN_ALIVE = 0
world.REGEN_PROB = 0.0

# Distance = 20, T_env at body center
d = 20.0
T_at_body = world.temperature_at([50.0, 50.0, 50.0])
print(f"\n[1] THERMAL FIELD:")
print(f"  Distance to source: {d}")
print(f"  T_env at body: {T_at_body:.4f}")

# Temperature gradient at body position
grad = world.gradient_at([50.0, 50.0, 50.0])
print(f"  Gradient: dT/dx={grad[0]:.6f}")

# Vital speed: 0.000252 (from EXP-016)
vital_speed = 0.000252
dx_per_step = vital_speed * 0.001  # speed * dt
dT_from_motion = abs(grad[0]) * dx_per_step
print(f"\n[2] VITAL PULSE -> dT:")
print(f"  Vital speed: {vital_speed}")
print(f"  dx per step: {dx_per_step:.9f}")
print(f"  dT from dx (env): {dT_from_motion:.12f}")

# =====================================================================
# 2. Fourier conduction: how fast does skin track env changes?
# =====================================================================
# SkinPatch: C=10, k=2, tau = C/k = 5 steps
C_th = 10.0
k = 2.0
tau_skin = C_th / k
print(f"\n[3] SKIN THERMAL DYNAMICS:")
print(f"  C_thermal: {C_th}")
print(f"  Conductance k: {k}")
print(f"  tau_skin: {tau_skin} steps")

# At equilibrium, T_skin tracks T_env. A step dT_env produces:
# dT_skin/step = (k/C) * (T_env - T_skin) * dt
# Near equilibrium: dT_skin ~ (k/C) * dT_env * dt
# But dT_env from vital motion is ALREADY multiplied by dt in dx
# So: dT_skin_per_step = (k/C) * grad * dx_per_step * dt

# Actually, the skin temperature changes because the PATCH POSITION moves
# relative to the temperature field. The patch sees a new T_env each step.
# T_env changes by grad * v * dt per step.
# Then skin temperature changes by q_dot/C * dt where q_dot = k*(T_env - T_skin)

# But since T_skin is ALREADY near equilibrium with T_env,
# the change in q_dot comes from the change in T_env:
# d(q_dot) = k * dT_env = k * grad * v * dt
# dT_skin_per_step = k * grad * v * dt^2 / C

dT_skin_per_step = (k * abs(grad[0]) * vital_speed * 0.001**2) / C_th
print(f"  dT_skin per step from vital: {dT_skin_per_step:.15f}")

# Actually let's be more careful. The Fourier integration is:
# dT_skin = (k/C) * (T_env_new - T_skin) * dt
# If body moves dx, T_env_new = T_env_old + grad*dx = T_env_old + grad*v*dt
# The key: (T_env - T_skin) is already ~0.43 (front-back diff / total)
# So the CHANGE in (T_env - T_skin) per step from vital motion is tiny

# Let me compute the raw dT_skin that the patch actually sees
# Run one step with the actual body
front_patch = body.skin_patches[0]  # front

# Warm up: 10000 steps to equilibrium
for _ in range(10000):
    front_patch.step_thermal(world, body, dt=0.001)

T_before = front_patch.current_temperature
print(f"\n[4] ACTUAL PATCH MEASUREMENT:")
print(f"  T_skin (front) at equilibrium: {T_before:.6f}")

# Move body by one vital step
body.position[0] += dx_per_step
front_patch.step_thermal(world, body, dt=0.001)
T_after = front_patch.current_temperature
dT_actual = T_after - T_before
print(f"  After 1 vital step (dx={dx_per_step:.9f}):")
print(f"  T_skin: {T_after:.12f}")
print(f"  dT_skin: {dT_actual:.15f}")

# =====================================================================
# 3. Nociceptor: can this dT fire it?
# =====================================================================
print(f"\n[5] NOCICEPTOR FIRING ANALYSIS:")
print(f"  Nociceptor config:")
print(f"    C = 0.5,  R_leak = 8.0,  tau = {0.5*8.0}ms")
print(f"    v_peak = 0.5 (firing threshold)")
print(f"    v_reset = 0.1")

# Nociceptor is driven by damage_integral * 10.0
# damage_integral = 0 when T_skin < 3.0 (damage_threshold)
# At distance 20, T_skin ~ 1.98 << 3.0
# So damage_integral = 0 ALWAYS for this setup!
print(f"\n  CRITICAL: Nociceptor driven by damage_integral, NOT dT/dt!")
print(f"  damage_threshold = 3.0")
print(f"  T_skin at d=20: {T_before:.4f}")
print(f"  T_skin < damage_threshold: {T_before < 3.0}")
print(f"  => damage_integral = 0 ALWAYS at this distance!")
print(f"  => Nociceptor input = 0 * 10 = 0")
print(f"  => Nociceptor NEVER fires at d=20!")
print(f"")
print(f"  This means the Nociceptor channel is COMPLETELY DEAD")
print(f"  unless the organism is already ON TOP of the heat source")
print(f"  (T_skin > 3.0 requires d < {30*(1-3.0/5.0):.1f} from source center)")

# =====================================================================
# 4. What about dT/dt as nociceptor input instead?
# =====================================================================
print(f"\n[6] IF NOCICEPTOR USED dT/dt INSTEAD OF damage_integral:")
# dT from vital motion:
dT_per_step = abs(dT_actual)
# Nociceptor membrane: dV = (I - V/R) * dt / C
# Steady state: V_ss = I * R = (dT * 10) * R_leak
# With R=8, scale=10: V_ss = dT * 10 * 8 = dT * 80
V_ss_noci = dT_per_step * 10.0 * 8.0
print(f"  dT per step: {dT_per_step:.15f}")
print(f"  Noci input (dT*10): {dT_per_step*10:.15f}")
print(f"  Noci V_ss (I*R): {V_ss_noci:.15f}")
print(f"  v_peak: 0.5")
print(f"  V_ss / v_peak: {V_ss_noci/0.5:.12f}")
print(f"  => Even with dT/dt input, {V_ss_noci/0.5*100:.6f}% of threshold")

# =====================================================================
# 5. What parameters would make it work?
# =====================================================================
print(f"\n[7] PARAMETER SENSITIVITY:")
# To reach v_peak=0.5 from dT/dt:
# Need I * R / C to integrate to 0.5
# Currently: I = dT * scale, V_ss = I * R
# Need: I * R >= v_peak
# I = dT * scale, R = R_leak
# dT * scale * R >= 0.5

# Option A: reduce C (faster integration, same V_ss)
print(f"  Option A: reduce C (doesn't help V_ss, only speeds up)")

# Option B: increase R_leak (higher V_ss for same I)
R_needed = 0.5 / (dT_per_step * 10.0 + 1e-30)
print(f"  Option B: R_leak needed: {R_needed:.2f} (vs current 8.0)")

# Option C: reduce v_peak
v_peak_needed = V_ss_noci
print(f"  Option C: v_peak needed: {v_peak_needed:.15f} (vs current 0.5)")

# Option D: increase temperature gradient (steeper field)
# Need T_src such that dT per vital step is large enough
# dT_skin ~ (k/C) * (T_env_new - T_env_old) * dt
# T_env_new - T_env_old = grad_T * v * dt = (T_src/r) * v * dt
# Need: (T_src/r) * v * dt * (k/C) * dt * scale * R >= v_peak
# T_src >= v_peak * r / (v * dt^2 * k/C * scale * R)
T_src_needed = 0.5 * 30.0 / (vital_speed * 0.001**2 * (2.0/10.0) * 10.0 * 8.0 + 1e-30)
print(f"  Option D: T_src needed: {T_src_needed:.2f} (vs current 5.0)")

# =====================================================================
# 6. The REAL fix: change noci input from damage to dT/dt
# =====================================================================
print(f"\n[8] ROOT CAUSE AND FIX:")
print(f"  Problem 1: Nociceptor is driven by damage_integral, not dT/dt")
print(f"    damage_integral = 0 unless T_skin > 3.0 (close to source)")
print(f"    => Nociceptor is blind to thermal GRADIENTS at safe distances")
print(f"    => Only fires when organism is already being cooked")
print(f"")
print(f"  Problem 2: Even if driven by dT/dt, the signal is ~1e-12")
print(f"    Vital speed 0.000252 produces dT/step ~ {dT_per_step:.2e}")
print(f"    This is ~10 orders of magnitude below noci threshold")
print(f"")
print(f"  Problem 3: Thermoreceptor IS providing signal (T_skin=1.98)")
print(f"    But Shadow layer saturates on static signal -> DA collapses")
print(f"    Need TEMPORAL variation in thermo signal -> need body MOTION")
print(f"    Need enough motion to change T_skin measurably")
print(f"")
print(f"  MINIMUM VIABLE MOTION for detectable dT/dt:")
# Need dT_skin per step > leak floor of Nociceptor
# Leak floor: V / R / C per step at v_peak threshold
leak_floor = 0.001 / (8.0 * 0.5)  # arbitrary small V / R*C
print(f"    Nociceptor leak floor: ~{leak_floor:.6f} V/step")
# Need dT * scale > leak_floor
dT_needed = leak_floor / 10.0
print(f"    dT_skin needed per step: {dT_needed:.6f}")
# dT_skin ~ (k/C) * grad * v * dt^2
# v = dT_needed * C / (k * grad * dt^2)
v_needed = dT_needed * C_th / (k * abs(grad[0]) * 0.001**2 + 1e-30)
print(f"    Speed needed: {v_needed:.2f} (vs vital 0.000252)")
print(f"    Ratio: {v_needed/vital_speed:.0f}x faster needed")
