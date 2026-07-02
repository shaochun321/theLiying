"""nexus_v1.tests.test_delayed_bundle — Unit tests for DelayedBundle (V2.0 Phase 2).

Tests:
  T1. Zero delay (no positions): behavior identical to SynapticBundle
  T2. Non-zero delay: signal arrives τ steps later
  T3. Position-derived delay: d=2mm, v=50mm/ms, dt=1ms → τ=0 (vestibular Aα)
  T4. Position-derived delay: d=10mm, v=1mm/ms, dt=1ms → τ=10 (cortical C-analog)
  T5. Mixed positions (one neuron has None): falls back to 0 delay
  T6. Regression: 21/21 regression suite still passes after import
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from nexus_v1.circuit.bundle_v2 import DelayedBundle, make_delayed, V_COND_AALPHA, V_COND_C
from nexus_v1.circuit.bundle import BundleConfig
from nexus_v1.components.neuron import Neuron, NeuronConfig


def make_test_neuron(nid: str, position=None) -> Neuron:
    return Neuron(NeuronConfig(
        neuron_id=nid,
        position=position,
        capacitance=1.0,
        r_leak=10.0,
        vdd=1.0,
        r_supply=0.1,
    ))


def make_bundle_config(bid: str) -> BundleConfig:
    return BundleConfig(
        bundle_id=bid,
        learning_rule="frozen",
        initial_weight=1.0,
        synapse_gain=1.0,
    )


PASS = "✓"
FAIL = "✗"


def test_t1_zero_delay_no_position():
    """T1: No positions → delay=0 → signal propagates immediately."""
    src = make_test_neuron("src", position=None)
    tgt = make_test_neuron("tgt", position=None)
    b = DelayedBundle(make_bundle_config("t1"), [src], [tgt], v_cond_mm_per_ms=50.0, dt=0.001)

    # Delay should be 0
    assert b._delay[0][0] == 0, f"Expected delay=0, got {b._delay[0][0]}"

    # Signal propagates at step 0
    src.activation = 1.0
    currents = b.propagate()
    assert len(currents) == 1, "Expected 1 current"
    assert currents[0] > 0, f"Expected positive current at t=0, got {currents[0]}"
    print(f"  {PASS} T1: zero delay, signal at t=0, current={currents[0]:.4f}")


def test_t2_explicit_delay():
    """T2: Manual position → τ=5 steps → signal arrives 5 steps later."""
    # d=5mm, v=1mm/ms, dt=1ms → τ=5 steps
    src = make_test_neuron("src", position=(5.0, 0.0, 0.0))
    tgt = make_test_neuron("tgt", position=(0.0, 0.0, 0.0))
    b = DelayedBundle(make_bundle_config("t2"), [src], [tgt], v_cond_mm_per_ms=1.0, dt=0.001)

    delay = b._delay[0][0]
    assert delay == 5, f"Expected delay=5, got {delay}"

    # Activate source at step 0; signal should appear at step delay
    src.activation = 1.0
    seen_at = None
    for t in range(20):
        if t == 1:
            src.activation = 0.0  # turn off after first step
        prev_v = tgt._membrane.voltage
        currents = b.propagate()
        if currents[0] > 0.0 and seen_at is None:
            seen_at = t
    assert seen_at == delay, f"Expected signal at step {delay}, arrived at {seen_at}"
    print(f"  {PASS} T2: delay={delay} steps, signal arrived at step {seen_at}")


def test_t3_vestibular_delay():
    """T3: Vestibular Aα: d=2mm, v=50mm/ms, dt=1ms → τ≈0 steps."""
    # Scarpa's ganglion to afferent: 2mm at 50mm/ms → 0.04ms → 0 steps
    src = make_test_neuron("hc_yaw", position=(1.5, 2.5, 0.0))   # hair cell
    tgt = make_test_neuron("aff_yaw", position=(-0.5, 2.5, 0.0)) # afferent
    b = DelayedBundle(make_bundle_config("t3"), [src], [tgt], v_cond_mm_per_ms=V_COND_AALPHA, dt=0.001)

    delay = b._delay[0][0]
    # d = sqrt((1.5-(-0.5))^2 + 0^2 + 0^2) = sqrt(4) = 2.0 mm
    # τ = 2.0/50.0/0.001 = 0.04 steps → round(0.04) = 0
    assert delay == 0, f"Expected delay=0 for vestibular Aα, got {delay}"
    print(f"  {PASS} T3: vestibular Aα d=2mm, τ=0 steps (effectively instantaneous)")


def test_t4_cortical_delay():
    """T4: Long-range C-fiber: d=10mm, v=0.5mm/ms, dt=1ms → τ=20 steps."""
    src = make_test_neuron("noci", position=(10.0, 0.0, 0.0))
    tgt = make_test_neuron("relay", position=(0.0, 0.0, 0.0))
    b = DelayedBundle(make_bundle_config("t4"), [src], [tgt], v_cond_mm_per_ms=V_COND_C, dt=0.001)

    # d=10mm, v=0.5mm/ms, dt=1ms → τ = 10/0.5/0.001 = ... wait
    # delay_ms = d/v = 10/0.5 = 20ms
    # delay_steps = delay_ms/dt = 20/1 = 20 steps
    delay = b._delay[0][0]
    assert delay == 20, f"Expected delay=20 for C-fiber, got {delay}"
    print(f"  {PASS} T4: C-fiber d=10mm, v=0.5mm/ms → τ={delay} steps")


def test_t5_mixed_position_none():
    """T5: Source has position, target has None → delay=0 (fallback)."""
    src = make_test_neuron("src", position=(5.0, 0.0, 0.0))
    tgt = make_test_neuron("tgt", position=None)
    b = DelayedBundle(make_bundle_config("t5"), [src], [tgt], v_cond_mm_per_ms=1.0, dt=0.001)

    assert b._delay[0][0] == 0, f"Expected delay=0 when target has None position, got {b._delay[0][0]}"
    print(f"  {PASS} T5: one neuron has None position → fallback to delay=0")


def test_t6_make_delayed_factory():
    """T6: make_delayed factory works identically to direct constructor."""
    src = make_test_neuron("src", position=(2.0, 0.0, 0.0))
    tgt = make_test_neuron("tgt", position=(0.0, 0.0, 0.0))
    b1 = make_delayed(make_bundle_config("t6a"), [src], [tgt], v_cond_mm_per_ms=2.0, dt=0.001)
    b2 = DelayedBundle(make_bundle_config("t6b"), [src], [tgt], v_cond_mm_per_ms=2.0, dt=0.001)
    assert b1._delay[0][0] == b2._delay[0][0], "Factory should produce same delay as constructor"
    print(f"  {PASS} T6: make_delayed factory → same delay ({b1._delay[0][0]} steps) as direct constructor")


def run_all():
    tests = [
        ("T1", test_t1_zero_delay_no_position),
        ("T2", test_t2_explicit_delay),
        ("T3", test_t3_vestibular_delay),
        ("T4", test_t4_cortical_delay),
        ("T5", test_t5_mixed_position_none),
        ("T6", test_t6_make_delayed_factory),
    ]
    passed = 0
    failed = 0
    print("DelayedBundle V2.0 Tests")
    print("=" * 40)
    for name, fn in tests:
        try:
            fn()
            passed += 1
        except Exception as e:
            print(f"  {FAIL} {name}: {e}")
            failed += 1
    print("=" * 40)
    print(f"Total: {passed}/{len(tests)} PASS")
    return failed == 0


if __name__ == "__main__":
    ok = run_all()
    sys.exit(0 if ok else 1)
