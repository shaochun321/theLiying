"""Test: Body skin patch temperature sampling.

Phase 1 Gate:
  1. Body near heat source → front patch temp > back patch temp
  2. Body turning → patch temp distribution follows heading

NOTE: SkinPatch is a Fourier thermal integrator, not an ideal
thermometer. T_skin lags behind T_env due to thermal inertia.
Sample returns 3-tuple: (T_skin, dT_skin, damage_integral).
"""
import sys
sys.path.insert(0, r"d:\cell-cc")

from nexus_v1.components.world import World, Body, HeatSource, SkinPatch


def test_patch_creation():
    """Body creates 4 default patches."""
    body = Body()
    assert len(body.skin_patches) == 4
    ids = {p.patch_id for p in body.skin_patches}
    assert ids == {"front", "back", "left", "right"}
    print(f"OK patch_creation: r={body.effective_radius:.3f}, "
          f"patches={[p.patch_id for p in body.skin_patches]}")


def test_directional_gradient():
    """Front patch closer to source should be warmer than back."""
    # Place heat source at [70, 50, 50], body at [50, 50, 50] heading +x
    src = HeatSource(position=[70.0, 50.0, 50.0], energy=50.0,
                     temperature=5.0, radius=25.0)
    body = Body(position=[50.0, 50.0, 50.0],
                velocity=[1.0, 0.0, 0.0])  # heading +x
    world = World(heat_sources=[src], body=body)

    # Multiple steps to let Fourier integrator converge
    for _ in range(20):
        skin = body.sample_skin(world, dt=1.0)

    T_front = skin["front"][0]
    T_back = skin["back"][0]
    T_left = skin["left"][0]
    T_right = skin["right"][0]

    print(f"OK directional: front={T_front:.4f} back={T_back:.4f} "
          f"left={T_left:.4f} right={T_right:.4f}")

    # Front should be warmer (closer to source)
    assert T_front > T_back, \
        f"Front ({T_front:.4f}) should be warmer than back ({T_back:.4f})"
    # Left and right should be roughly equal (source is straight ahead)
    assert abs(T_left - T_right) < 0.2, \
        f"Left and right should be similar: {T_left:.4f} vs {T_right:.4f}"

    print("OK directional gradient verified")


def test_heading_rotation():
    """When heading changes, patch world positions rotate."""
    src = HeatSource(position=[50.0, 70.0, 50.0], energy=50.0,
                     temperature=5.0, radius=25.0)
    body = Body(position=[50.0, 50.0, 50.0])

    # Heading +x (default): source is to the left
    body.velocity = [1.0, 0.0, 0.0]
    world = World(heat_sources=[src], body=body)
    # Let integrator converge
    for _ in range(20):
        skin1 = body.sample_skin(world, dt=1.0)
    T_left_1 = skin1["left"][0]
    T_front_1 = skin1["front"][0]

    # Now heading +y: source is straight ahead
    # Reset patches for clean comparison
    for p in body.skin_patches:
        p.current_temperature = 0.1  # SkinPatch default
        p._prev_temperature = 0.1
    body.velocity = [0.0, 1.0, 0.0]
    for _ in range(20):
        skin2 = body.sample_skin(world, dt=1.0)
    T_left_2 = skin2["left"][0]
    T_front_2 = skin2["front"][0]

    print(f"OK heading +x: front={T_front_1:.4f} left={T_left_1:.4f}")
    print(f"OK heading +y: front={T_front_2:.4f} left={T_left_2:.4f}")

    # When heading +x, source at +y should be on left side
    assert T_left_1 > T_front_1, \
        "With heading +x, source at +y should heat left patch more"
    # When heading +y, source at +y should be in front
    assert T_front_2 > T_left_2, \
        "With heading +y, source at +y should heat front patch more"

    print("OK heading rotation verified")


def test_ambient_only():
    """Far from sources → all patches converge toward ambient."""
    body = Body(position=[50.0, 50.0, 50.0],
                velocity=[1.0, 0.0, 0.0])
    world = World(heat_sources=[], body=body)
    # Manually set ambient
    world.ambient_temp = 0.1

    # Let Fourier integrator converge toward ambient
    for _ in range(50):
        skin = body.sample_skin(world, dt=1.0)
    for pid, vals in skin.items():
        T = vals[0]
        assert abs(T - 0.1) < 0.05, f"{pid}: expected near ambient 0.1, got {T}"

    print("OK ambient: all patches converge toward ambient temp")


def test_dT_tracking():
    """Moving toward source should produce positive dT."""
    src = HeatSource(position=[70.0, 50.0, 50.0], energy=50.0,
                     temperature=5.0, radius=25.0)
    body = Body(position=[55.0, 50.0, 50.0],
                velocity=[1.0, 0.0, 0.0])
    world = World(heat_sources=[src], body=body)

    # Warm up for a few steps at initial position
    for _ in range(5):
        body.sample_skin(world, dt=1.0)

    # Move closer → T_env increases → dT should be positive
    body.position[0] += 2.0
    skin2 = body.sample_skin(world, dt=1.0)

    dT_front = skin2["front"][1]
    print(f"OK dT: front dT={dT_front:.4f} (should be positive)")
    assert dT_front > 0, f"Moving toward source should increase front temp"

    # Also verify damage_integral is in the tuple
    damage = skin2["front"][2]
    print(f"OK damage_integral: {damage:.6f}")

    print("OK dT tracking verified")


if __name__ == "__main__":
    test_patch_creation()
    test_directional_gradient()
    test_heading_rotation()
    test_ambient_only()
    test_dT_tracking()
    print("\nAll Phase 1 patch tests passed!")
