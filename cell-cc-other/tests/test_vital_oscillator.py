"""Independent unit test for VitalOscillator + EnergyStore.

Tests run BEFORE system integration to verify:
  1. Noether energy conservation (deposited = withdrawn + basal + level - initial)
  2. Energy death switch (fill < 0.05 → output = 0, withdraw = 0)
  3. Three-axis outputs are NOT in-phase (Lissajous test)
  4. Long-term energy budget is sustainable
  5. Graceful shutdown when energy depletes

Run: python -m pytest tests/test_vital_oscillator.py -v
  or: python tests/test_vital_oscillator.py
"""

import sys
import os
import math

# Add project root to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from nexus_v1.components.vital_oscillator import VitalOscillator, VitalOscillatorConfig
from nexus_v1.components.energy_store import EnergyStore, EnergyStoreConfig


def test_basic_oscillation():
    """VitalOscillator produces non-zero output when energy is available."""
    store = EnergyStore()  # default: 50% fill = 500
    vital = VitalOscillator()

    outputs = vital.step(store, dt=0.001)

    # Should produce three outputs
    assert len(outputs) == 3, f"Expected 3 outputs, got {len(outputs)}"
    # After first step, at least one axis should be non-zero
    # (VdP starts from non-zero initial conditions)
    assert any(abs(o) > 1e-10 for o in outputs), \
        f"All outputs are zero on first step: {outputs}"
    print(f"  OK basic_oscillation: outputs = {[f'{o:.6f}' for o in outputs]}")


def test_noether_conservation_10k():
    """Energy is conserved over 10k steps: Noether balance ≈ 0."""
    store = EnergyStore(EnergyStoreConfig(
        capacity=1000.0,
        initial_fill=0.5,
        basal_drain=0.0001,
        max_deposit_per_step=0.05,
    ))
    vital = VitalOscillator()

    # Run 10k steps with periodic deposits (simulating feeding)
    for step in range(10000):
        # Deposit every 10 steps (simulates periodic feeding)
        if step % 10 == 0:
            store.deposit(0.1)
        store.tick(dt=0.001)
        vital.step(store, dt=0.001)

    summary = store.summary()
    noether = abs(summary['noether_balance'])
    print(f"  OK noether_10k: balance = {noether:.8f} "
          f"(level={summary['level']:.2f}, "
          f"deposited={summary['total_deposited']:.4f}, "
          f"withdrawn={summary['total_withdrawn']:.4f}, "
          f"basal={summary['total_basal_drain']:.4f})")

    assert noether < 0.01, \
        f"Noether violation: |balance| = {noether} > 0.01"


def test_death_switch():
    """Output = 0 and withdraw = 0 when energy < 5% capacity."""
    store = EnergyStore(EnergyStoreConfig(
        capacity=100.0,
        initial_fill=0.03,  # start at 3% → below death threshold
        basal_drain=0.0,    # disable basal drain for clean test
    ))
    vital = VitalOscillator()

    level_before = store.level
    outputs = vital.step(store, dt=0.001)

    # All outputs must be exactly zero
    assert all(o == 0.0 for o in outputs), \
        f"Death switch failed: outputs = {outputs} at fill = {store.fill_fraction:.3f}"
    # No energy withdrawn
    assert store.level == level_before, \
        f"Energy withdrawn during death: {level_before} → {store.level}"
    print(f"  OK death_switch: outputs = {outputs}, "
          f"fill = {store.fill_fraction:.3f}, level unchanged")


def test_death_switch_transition():
    """Oscillator stops when energy drains below threshold.

    Use small capacity (10.0) and aggressive basal_drain (0.01/step)
    so the store empties within ~5000 steps → death switch triggers.
    """
    store = EnergyStore(EnergyStoreConfig(
        capacity=10.0,
        initial_fill=0.5,   # start at 50% = 5.0 units
        basal_drain=10.0,   # effective drain: 10.0 * dt(0.001) = 0.01/step
        max_deposit_per_step=0.0,  # no feeding -> eventual depletion
    ))
    vital = VitalOscillator()

    alive_count = 0
    dead_count = 0
    transitioned = False

    for step in range(10000):
        store.tick(dt=0.001)
        outputs = vital.step(store, dt=0.001)
        if any(abs(o) > 1e-10 for o in outputs):
            alive_count += 1
            if dead_count > 0:
                # Should not resurrect
                assert False, f"Oscillator resurrected at step {step}"
        else:
            if alive_count > 0 and not transitioned:
                transitioned = True
                print(f"  OK death_transition: alive for {alive_count} steps, "
                      f"died at fill = {store.fill_fraction:.4f}")
            dead_count += 1

    assert transitioned, (
        f"Oscillator never died despite no energy input. "
        f"fill={store.fill_fraction:.4f}, level={store.level:.4f}")
    assert alive_count > 10, f"Died too early: only {alive_count} alive steps"
    print(f"  OK death_switch_transition: {alive_count} alive, "
          f"{dead_count} dead steps")


def test_lissajous_non_collinear():
    """Three-axis outputs are NOT in-phase (produce 2D+ wandering).

    If outputs were in-phase, the cross-correlation between any two
    axes at zero lag would be > 0.95 (nearly identical time series).
    With detuned frequencies, cross-correlation should be LOW (< 0.5).

    Beat periods: X-Z = 1/(2.00-1.93) = 14.3s = 14300 steps
                  X-Y = 1/(2.11-2.00) = 9.1s  = 9100 steps
    Need at least 2 full beat periods → 30000 steps.
    """
    store = EnergyStore(EnergyStoreConfig(
        capacity=1000.0,
        initial_fill=0.5,
        basal_drain=0.0,  # no drain for clean signal test
    ))
    vital = VitalOscillator()

    # Collect 30000 steps of output (30s → >2 beat periods for all pairs)
    N_STEPS = 30000
    xs, ys, zs = [], [], []
    for _ in range(N_STEPS):
        outputs = vital.step(store, dt=0.001)
        xs.append(outputs[0])
        ys.append(outputs[1])
        zs.append(outputs[2])

    # Compute Pearson correlation between pairs
    def pearson(a, b):
        n = len(a)
        mean_a = sum(a) / n
        mean_b = sum(b) / n
        cov = sum((a[i] - mean_a) * (b[i] - mean_b) for i in range(n)) / n
        std_a = math.sqrt(sum((x - mean_a)**2 for x in a) / n)
        std_b = math.sqrt(sum((x - mean_b)**2 for x in b) / n)
        if std_a < 1e-12 or std_b < 1e-12:
            return 0.0
        return cov / (std_a * std_b)

    corr_xy = abs(pearson(xs, ys))
    corr_xz = abs(pearson(xs, zs))
    corr_yz = abs(pearson(ys, zs))

    print(f"  OK lissajous ({N_STEPS} steps): |r_xy|={corr_xy:.3f}, "
          f"|r_xz|={corr_xz:.3f}, |r_yz|={corr_yz:.3f}")

    # All correlations should be well below 0.5 for non-collinear wandering
    assert corr_xy < 0.5, f"X-Y too correlated: |r|={corr_xy:.3f}"
    assert corr_xz < 0.5, f"X-Z too correlated: |r|={corr_xz:.3f}"
    assert corr_yz < 0.5, f"Y-Z too correlated: |r|={corr_yz:.3f}"


def test_energy_budget_sustainable():
    """Long-term energy drain from vital oscillator is small.

    In isolation, vital is the ONLY withdrawer, so fraction-of-total is
    meaningless. Instead, verify that absolute vital cost over 100k steps
    is small relative to store capacity (< 10% of capacity).
    This ensures the heartbeat is a minor metabolic expense.
    """
    store = EnergyStore(EnergyStoreConfig(
        capacity=1000.0,
        initial_fill=0.5,
        basal_drain=0.0001,
        max_deposit_per_step=0.05,
    ))
    vital = VitalOscillator()

    initial_level = store.level

    # Run 100k steps (100s) with periodic deposits
    for step in range(100000):
        if step % 10 == 0:
            store.deposit(0.1)
        store.tick(dt=0.001)
        vital.step(store, dt=0.001)

    final_level = store.level
    vital_cost = vital.total_energy_withdrawn
    capacity = store.config.capacity

    # Vital cost as fraction of total capacity
    cost_fraction_of_capacity = vital_cost / capacity

    print(f"  OK energy_budget: vital cost = {vital_cost:.4f}, "
          f"capacity = {capacity:.0f}, "
          f"cost/capacity = {cost_fraction_of_capacity:.4f}")
    print(f"    level: {initial_level:.1f} -> {final_level:.1f}")

    # Vital cost over 100s should be < 10% of total capacity
    assert cost_fraction_of_capacity < 0.10, \
        f"Vital oscillator cost ({vital_cost:.4f}) is {cost_fraction_of_capacity*100:.1f}% of capacity"
    # System should not be energy-bankrupt
    assert final_level > 0, "System went bankrupt -- energy budget unsustainable"


def test_amplitude_modulation():
    """Output amplitude tracks energy fill level."""
    vital = VitalOscillator()

    # High energy: full amplitude
    store_high = EnergyStore(EnergyStoreConfig(
        capacity=100.0, initial_fill=0.8, basal_drain=0.0))

    # Low energy (but above death): reduced amplitude
    store_low = EnergyStore(EnergyStoreConfig(
        capacity=100.0, initial_fill=0.15, basal_drain=0.0))

    # Warm up both for 1000 steps to reach limit cycle
    vital_high = VitalOscillator()
    vital_low = VitalOscillator()
    for _ in range(1000):
        vital_high.step(store_high, dt=0.001)
        vital_low.step(store_low, dt=0.001)

    # Collect peak amplitudes over 1000 more steps
    max_high = 0.0
    max_low = 0.0
    for _ in range(1000):
        out_h = vital_high.step(store_high, dt=0.001)
        out_l = vital_low.step(store_low, dt=0.001)
        max_high = max(max_high, max(abs(o) for o in out_h))
        max_low = max(max_low, max(abs(o) for o in out_l))

    print(f"  OK amplitude_modulation: high_fill peak={max_high:.6f}, "
          f"low_fill peak={max_low:.6f}")

    # High energy should produce larger amplitude than low energy
    assert max_high > max_low, \
        f"High energy ({max_high}) should have larger amplitude than low ({max_low})"


if __name__ == '__main__':
    tests = [
        ("basic_oscillation", test_basic_oscillation),
        ("noether_conservation_10k", test_noether_conservation_10k),
        ("death_switch", test_death_switch),
        ("death_switch_transition", test_death_switch_transition),
        ("lissajous_non_collinear", test_lissajous_non_collinear),
        ("energy_budget_sustainable", test_energy_budget_sustainable),
        ("amplitude_modulation", test_amplitude_modulation),
    ]

    passed = 0
    failed = 0
    for name, test_fn in tests:
        try:
            print(f"\n[TEST] {name}")
            test_fn()
            passed += 1
        except AssertionError as e:
            print(f"  FAILED: {e}")
            failed += 1
        except Exception as e:
            print(f"  ERROR: {type(e).__name__}: {e}")
            failed += 1

    print(f"\n{'='*50}")
    print(f"Results: {passed} passed, {failed} failed, {passed+failed} total")
    if failed == 0:
        print("ALL TESTS PASSED")
    else:
        print("SOME TESTS FAILED")
        sys.exit(1)
