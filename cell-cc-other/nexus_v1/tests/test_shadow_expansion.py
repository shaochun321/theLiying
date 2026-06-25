"""Test: Shadow dynamic axis expansion.

Verifies that ShadowSandbox correctly expands its topology
when new axes are added to the main circuit's all_axes list.
"""
import sys
sys.path.insert(0, r"d:\cell-cc")

from nexus_v1.components.shadow_sandbox import ShadowSandbox


class MockVestibular:
    """Minimal vestibular mock for shadow init."""
    def __init__(self):
        self.axes = ["yaw", "pitch", "roll", "oto_x", "oto_y", "oto_z"]

    def get_all_neurons(self):
        return []

    def get_all_bundles(self):
        return []


class MockBundle:
    def __init__(self, bid, xin=0.0):
        self.id = bid
        self.config = type('C', (), {'xin_tension': xin})()


class MockCircuit:
    """Minimal circuit mock."""
    def __init__(self, extra_axes=None):
        self.vestibular = MockVestibular()
        self.all_axes = list(self.vestibular.axes) + (extra_axes or ["therm"])
        self._bundles = [MockBundle(f"enc_to_col_{ax}") for ax in self.all_axes]

    def get_all_bundles(self):
        return self._bundles


def test_initial_axes():
    """Test initial shadow has correct neuron/bundle counts."""
    sandbox = ShadowSandbox()
    circuit = MockCircuit(extra_axes=["therm"])
    sandbox.initialize(circuit)

    # 7 axes: 6 vest + 1 therm
    assert len(sandbox._axes) == 7, f"Expected 7 axes, got {len(sandbox._axes)}"

    # Neurons: 7×2 enc + 7 col + 3 mot = 24
    expected_neurons = 7 * 2 + 7 + 3
    assert len(sandbox.neurons) == expected_neurons, \
        f"Expected {expected_neurons} neurons, got {len(sandbox.neurons)}"

    # Bundles: 7 enc→col + 7 col→mot + C(7,2)=21 cross = 35
    expected_bundles = 7 + 7 + 21
    assert len(sandbox.bundles) == expected_bundles, \
        f"Expected {expected_bundles} bundles, got {len(sandbox.bundles)}"

    print(f"✓ Initial: {len(sandbox._axes)} axes, "
          f"{len(sandbox.neurons)} neurons, {len(sandbox.bundles)} bundles")


def test_dynamic_expansion():
    """Test that adding new axes to circuit expands shadow."""
    sandbox = ShadowSandbox()
    circuit = MockCircuit(extra_axes=["therm"])
    sandbox.initialize(circuit)

    initial_n = len(sandbox.neurons)
    initial_b = len(sandbox.bundles)
    initial_axes = len(sandbox._axes)

    # Now add 4 new patch axes to the circuit
    new_patch_axes = ["therm_front", "therm_back", "therm_left", "therm_right"]
    circuit.all_axes.extend(new_patch_axes)
    # Add corresponding bundles
    for ax in new_patch_axes:
        circuit._bundles.append(MockBundle(f"enc_to_col_{ax}"))

    # Trigger expansion
    sandbox._expand_for_new_axes(circuit)

    # Check axes expanded
    assert len(sandbox._axes) == initial_axes + 4, \
        f"Expected {initial_axes + 4} axes, got {len(sandbox._axes)}"

    # Check new neurons: 4 × (2 enc + 1 col) = 12
    new_neurons = len(sandbox.neurons) - initial_n
    assert new_neurons == 12, f"Expected 12 new neurons, got {new_neurons}"

    # Check new bundles:
    # 4 × enc→col = 4
    # 4 × col→mot = 4
    # 4 × 7 existing × 2 directions = 56 cross bundles (new↔existing)
    # C(4,2) = 6 cross bundles between new axes
    # Total new = 4 + 4 + 56 + 6 = 70
    new_bundles = len(sandbox.bundles) - initial_b
    expected_new_bundles = 4 + 4 + (4 * 7 * 2) + 6
    assert new_bundles == expected_new_bundles, \
        f"Expected {expected_new_bundles} new bundles, got {new_bundles}"

    # Check specific neurons exist
    for ax in new_patch_axes:
        assert f"s_enc_reg_{ax}" in sandbox.neurons, f"Missing s_enc_reg_{ax}"
        assert f"s_enc_irr_{ax}" in sandbox.neurons, f"Missing s_enc_irr_{ax}"
        assert f"s_col_{ax}" in sandbox.neurons, f"Missing s_col_{ax}"

    # Check Xin routing updated
    for ax in new_patch_axes:
        main_bid = f"enc_to_col_{ax}"
        assert main_bid in sandbox._xin_routing, f"Missing Xin routing for {ax}"

    # Check baselines initialized
    for ax in new_patch_axes:
        assert f"s_col_{ax}" in sandbox._baseline_ema

    print(f"✓ Expansion: +{len(new_patch_axes)} axes → "
          f"+{new_neurons} neurons, +{new_bundles} bundles")
    print(f"  Total: {len(sandbox._axes)} axes, "
          f"{len(sandbox.neurons)} neurons, {len(sandbox.bundles)} bundles")


def test_idempotent():
    """Test that re-expansion with same axes does nothing."""
    sandbox = ShadowSandbox()
    circuit = MockCircuit(extra_axes=["therm"])
    sandbox.initialize(circuit)

    n_before = len(sandbox.neurons)
    b_before = len(sandbox.bundles)

    # Call expand with no new axes
    sandbox._expand_for_new_axes(circuit)

    assert len(sandbox.neurons) == n_before
    assert len(sandbox.bundles) == b_before
    print("✓ Idempotent: no change when no new axes")


def test_no_existing_modification():
    """Test that expansion doesn't modify existing neurons."""
    sandbox = ShadowSandbox()
    circuit = MockCircuit(extra_axes=["therm"])
    sandbox.initialize(circuit)

    # Record existing neuron IDs and their energy
    existing_state = {nid: n.energy for nid, n in sandbox.neurons.items()}

    # Expand
    circuit.all_axes.extend(["therm_front"])
    circuit._bundles.append(MockBundle("enc_to_col_therm_front"))
    sandbox._expand_for_new_axes(circuit)

    # Check existing neurons unchanged
    for nid, orig_energy in existing_state.items():
        assert sandbox.neurons[nid].energy == orig_energy, \
            f"Existing neuron {nid} was modified!"

    print("✓ Existing neurons unchanged after expansion")


if __name__ == "__main__":
    test_initial_axes()
    test_dynamic_expansion()
    test_idempotent()
    test_no_existing_modification()
    print("\n✅ All shadow expansion tests passed!")
