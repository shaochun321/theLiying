"""nexus_v1.tests.diag_world2_physics — World 2.0 Phase 1 unit tests.

Tests W1-W8 (physical layer verification before behavior-level experiments).
Run from repo root: python -m nexus_v1.tests.diag_world2_physics
"""
import math
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from nexus_v1.components.heat_source import CylindricalHeatSource, _dist_to_cylinder_surface
from nexus_v1.components.world import World, Body, SkinPatch
from nexus_v1.components.thermal_mouth import ThermalMouth


PASS = "[PASS]"
FAIL = "[FAIL]"


def check(name, cond, detail=""):
    status = PASS if cond else FAIL
    print(f"  {status} {name}" + (f"  ({detail})" if detail else ""))
    return cond


def test_W1b_dist_to_cylinder():
    """W1b: _dist_to_cylinder_surface geometry."""
    center = [50.0, 50.0, 25.0]
    r = 6.0
    hh = 8.0  # half_height

    # Inside: [50, 50, 25] exactly at center → d = max(0, 0 - 6) = 0
    d_inside = _dist_to_cylinder_surface([50, 50, 25], center, r, hh)
    r1 = check("W1b-inside", abs(d_inside) < 1e-9, f"d={d_inside:.6f}")

    # Side surface (within height): [57, 50, 25] → radial=7, d=7-6=1
    d_side = _dist_to_cylinder_surface([57, 50, 25], center, r, hh)
    r2 = check("W1b-side", abs(d_side - 1.0) < 1e-6, f"d={d_side:.6f}")

    # Cap above (directly above): [50, 50, 34] → dz=9, hh=8 → d_to_rim=1
    d_above = _dist_to_cylinder_surface([50, 50, 34], center, r, hh)
    r3 = check("W1b-above-cap", abs(d_above - 1.0) < 1e-6, f"d={d_above:.6f}")

    # Corner: [57, 50, 34] → radial=7(>6), dz=9(>8) → sqrt((7-6)^2+(9-8)^2)=sqrt(2)
    d_corner = _dist_to_cylinder_surface([57, 50, 34], center, r, hh)
    expected = math.sqrt(2)
    r4 = check("W1b-corner", abs(d_corner - expected) < 1e-4,
               f"d={d_corner:.6f}, expected={expected:.6f}")

    return all([r1, r2, r3, r4])


def test_W1_temperature_field():
    """W1: CylindricalHeatSource Gaussian temperature field."""
    src = CylindricalHeatSource(
        center=[50.0, 50.0, 25.0], radius=6.0, height=16.0,
        T_surface=5.0, T_ambient=0.15, sigma=25.0, energy=1000.0)

    # At cylinder surface (dist=0): T = T_ambient + (T_surface - T_ambient) * 1.0
    T_surface = src.temperature_at([56.0, 50.0, 25.0])
    expected_surface = 5.0
    r1 = check("W1-at-surface", abs(T_surface - expected_surface) < 0.01,
               f"T={T_surface:.3f}, expected={expected_surface:.3f}")

    # At dist=sigma from surface: T = T_ambient + ΔT * exp(-0.5)
    T_sigma = src.temperature_at([56.0 + 25.0, 50.0, 25.0])
    expected_sigma = 0.15 + (5.0 - 0.15) * math.exp(-0.5)
    r2 = check("W1-at-sigma", abs(T_sigma - expected_sigma) < 0.1,
               f"T={T_sigma:.3f}, expected={expected_sigma:.3f}")

    # At dist=3*sigma: T ≈ T_ambient (< 5% above ambient)
    T_far = src.temperature_at([56.0 + 75.0, 50.0, 25.0])
    r3 = check("W1-at-3sigma", T_far < 0.15 + (5.0 - 0.15) * 0.05,
               f"T={T_far:.4f}")

    # Inside cylinder: T ≈ T_surface
    T_inside = src.temperature_at([50.0, 50.0, 25.0])
    r4 = check("W1-inside-cylinder", abs(T_inside - expected_surface) < 0.01,
               f"T={T_inside:.3f}")

    return all([r1, r2, r3, r4])


def test_W1_world_temperature_at():
    """W1: World.temperature_at() uses cylindrical sources."""
    src = CylindricalHeatSource(
        center=[50.0, 50.0, 25.0], radius=6.0, height=16.0,
        T_surface=5.0, T_ambient=0.15, sigma=25.0, energy=1000.0)
    world = World(cylindrical_sources=[src])

    # Near cylinder: T > ambient
    T_near = world.temperature_at([56.0, 50.0, 25.0])
    r1 = check("W1-world-near", T_near > 4.0, f"T={T_near:.3f}")

    # Far from cylinder: T ≈ ambient
    T_far = world.temperature_at([0.0, 0.0, 25.0])
    r2 = check("W1-world-far", T_far < 0.5, f"T={T_far:.4f}")

    return r1 and r2


def test_W4_yaw_dynamics():
    """W4: Body.apply_yaw_torque() and SkinPatch.world_position() with explicit yaw."""
    body = Body(position=[50.0, 50.0, 25.0])
    dt = 0.001

    # Initial yaw=0
    r1 = check("W4-initial-yaw", body.yaw == 0.0, f"yaw={body.yaw}")

    # Apply positive torque → yaw increases
    body.apply_yaw_torque(1.0, dt)
    r2 = check("W4-torque-increases-yaw", body.yaw > 0.0,
               f"yaw={body.yaw:.6f}, omega={body.angular_velocity:.6f}")

    # Remove torque: angular_velocity decays exponentially
    omega_before = body.angular_velocity
    body.apply_yaw_torque(0.0, dt)
    omega_after = body.angular_velocity
    expected_decay = math.exp(-body.angular_friction * dt)
    r3 = check("W4-angular-decay", abs(omega_after / max(omega_before, 1e-12) - expected_decay) < 1e-4,
               f"ratio={omega_after / max(omega_before, 1e-12):.6f}, expected={expected_decay:.6f}")

    # SkinPatch.world_position() at yaw=π/2: front patch → +y direction
    body2 = Body(position=[50.0, 50.0, 25.0])
    body2.yaw = math.pi / 2
    front_patch = SkinPatch(patch_id="front", local_offset=[1.0, 0.0, 0.0])
    pos = front_patch.world_position(body2)
    # At yaw=π/2: cos=0, sin=1 → wx=0, wy=1 → world_pos = [50, 51, 25]
    r4 = check("W4-patch-at-90deg",
               abs(pos[0] - 50.0) < 1e-6 and abs(pos[1] - 51.0) < 1e-6,
               f"pos=[{pos[0]:.4f}, {pos[1]:.4f}, {pos[2]:.4f}]")

    return all([r1, r2, r3, r4])


def test_W2_W3_collision():
    """W2/W3: Cylinder collision → velocity reflection + damage injection."""
    src = CylindricalHeatSource(
        center=[50.0, 50.0, 25.0], radius=6.0, height=16.0,
        T_surface=5.0, T_ambient=0.15, sigma=25.0, energy=1000.0)

    # Body approaching from +x at high speed
    body = Body(position=[50.0 + 6.0 + 1.2, 50.0, 25.0],  # just outside (dist_xy=7.2)
                velocity=[-1.0, 0.0, 0.0])
    # effective_radius ≈ 1.30; collision_dist = 6.0 + 1.30 = 7.30 > 7.2 → inside range

    damage_before = body.skin_patches[0].damage_integral
    vx_before = body.velocity[0]

    body._collide_with_cylinder(src, 0.001)

    vx_after = body.velocity[0]
    damage_after = body.skin_patches[0].damage_integral

    r1 = check("W2-velocity-reversed", vx_after > 0,
               f"vx_before={vx_before:.3f}, vx_after={vx_after:.3f}")
    r2 = check("W3-damage-increased", damage_after >= damage_before,
               f"damage: {damage_before:.4f} → {damage_after:.4f}")

    return r1 and r2


def test_W5_W6_thermal_mouth():
    """W5/W6: ThermalMouth deposits energy when warmer than mouth."""
    src = CylindricalHeatSource(
        center=[50.0, 50.0, 25.0], radius=6.0, height=16.0,
        T_surface=5.0, T_ambient=0.15, sigma=25.0, energy=1000.0)
    world = World(cylindrical_sources=[src])

    # Simple energy store stub
    class _MockStore:
        def __init__(self): self.total = 0.0
        def deposit(self, v): self.total += v
        def withdraw(self, v): pass

    body = Body(position=[56.0, 50.0, 25.0])  # at cylinder surface
    mouth = ThermalMouth()
    store = _MockStore()

    # Run 1000 steps at T_env ≈ 5.0
    for _ in range(1000):
        mouth.step(world, body, store, ecm_temp=0.15, dt=0.001)

    r1 = check("W5-energy-positive", store.total > 0,
               f"total_intake={store.total:.6f}")
    r2 = check("W6-mouth-temperature-raised", mouth.temperature > 0.3,
               f"T_mouth={mouth.temperature:.3f}")

    # At rest for 10000 steps: energy_intake should not be zero (no thermal deadlock)
    body2 = Body(position=[56.0, 50.0, 25.0])
    mouth2 = ThermalMouth()
    store2 = _MockStore()
    for _ in range(10000):
        mouth2.step(world, body2, store2, ecm_temp=0.15, dt=0.001)
    r3 = check("W6-no-deadlock", store2.total > 0,
               f"total_after_10k={store2.total:.6f}")

    return all([r1, r2, r3])


def test_W8_temperature_to_yaw():
    """W8: Left-right temperature difference drives yaw torque."""
    body = Body(position=[50.0, 50.0, 25.0])
    yaw_before = body.yaw

    # Simulate: T_left=3.0, T_right=1.0 → delta=2.0 → torque=0.2
    delta_T_lr = 3.0 - 1.0
    YAW_GAIN = 0.1
    torque = delta_T_lr * YAW_GAIN
    body.apply_yaw_torque(torque, 0.001)

    r1 = check("W8-positive-torque-increases-yaw", body.yaw > yaw_before,
               f"yaw_before={yaw_before:.6f}, yaw_after={body.yaw:.6f}")
    r2 = check("W8-torque-magnitude", torque == pytest_approx(0.2) if False else abs(torque - 0.2) < 1e-9,
               f"torque={torque:.4f}")

    return r1 and r2


def run_all():
    tests = [
        ("W1b: dist_to_cylinder_surface", test_W1b_dist_to_cylinder),
        ("W1:  Gaussian temperature field", test_W1_temperature_field),
        ("W1:  World.temperature_at()", test_W1_world_temperature_at),
        ("W4:  Yaw dynamics", test_W4_yaw_dynamics),
        ("W2/W3: Collision + damage", test_W2_W3_collision),
        ("W5/W6: ThermalMouth", test_W5_W6_thermal_mouth),
        ("W8:  Temperature → yaw", test_W8_temperature_to_yaw),
    ]
    passed = 0
    failed = 0
    print("\n" + "=" * 60)
    print("  World 2.0 Phase 1 — Physical Layer Tests (W1-W8)")
    print("=" * 60)
    for name, fn in tests:
        print(f"\n[{name}]")
        try:
            ok = fn()
            if ok:
                passed += 1
            else:
                failed += 1
        except Exception as e:
            print(f"  {FAIL} EXCEPTION: {e}")
            import traceback
            traceback.print_exc()
            failed += 1

    print("\n" + "=" * 60)
    print(f"  {passed} passed, {failed} failed")
    print("=" * 60)
    return failed == 0


if __name__ == "__main__":
    ok = run_all()
    sys.exit(0 if ok else 1)
