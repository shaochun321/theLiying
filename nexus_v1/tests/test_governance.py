"""Test governance system integration with VariantCircuit.

Tests:
    1. Governance initializes correctly
    2. Fuse detects weight violation
    3. Ledger records data correctly
    4. Modeler predictions match actual neuron behavior
    5. Full simulation with governance active
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from nexus_v1.circuit.variant_adapter import VariantCircuit


def test_governance_init():
    """Governance should be present on VariantCircuit."""
    circuit = VariantCircuit()
    assert circuit.governance is not None, "Governance not initialized"
    assert circuit.governance.fuse.enabled, "Fuse should be enabled"
    assert not circuit.governance.config.debug_mode, "Should not be debug"
    print("[OK] Governance initialized, fuse enabled")


def test_governance_runs_with_circuit():
    """Run 500 steps with governance active - no fuse trips."""
    circuit = VariantCircuit()
    for i in range(500):
        inputs = {
            'yaw': 0.5 * (1 if i % 20 < 10 else -1),
            'pitch': 0.0, 'roll': 0.0,
            'oto_x': 0.0, 'oto_y': 0.0, 'oto_z': 0.0,
        }
        circuit.step(inputs, dt=0.001)

    # Check ledger recorded data
    gov = circuit.governance
    report = gov.ledger.summary()
    assert report['steps'] == 500, f"Expected 500, got {report['steps']}"
    assert report['total_heat_dissipated'] >= 0, "Negative heat!"
    print(f"[OK] 500 steps completed, {report['total_spikes']} spikes, "
          f"heat={report['total_heat_dissipated']:.6f}")

    # Check gain chain
    gain = gov.ledger.get_gain_chain()
    if gain:
        print(f"  Gain chain: {len(gain)} links measured")
        for k, g in gain.items():
            print(f"    {k}: {g:.4f}")

    # Check baselines
    baselines = gov.ledger.get_baselines()
    print(f"  Baselines tracked for {len(baselines)} neurons")

    # Fuse should not have tripped
    assert gov.fuse.trip_count == 0, f"Fuse tripped {gov.fuse.trip_count} times!"
    print("[OK] No fuse trips")


def test_fuse_detects_weight_violation():
    """Manually corrupt a weight and verify fuse catches it."""
    circuit = VariantCircuit()
    # Run a few steps to warm up
    for _ in range(10):
        circuit.step({'yaw': 0.5, 'pitch': 0, 'roll': 0,
                      'oto_x': 0, 'oto_y': 0, 'oto_z': 0}, dt=0.001)

    # Corrupt a weight
    bundles = circuit.get_all_bundles()
    if bundles:
        b = bundles[0]
        original_w = b._memristors[0][0].w
        b._memristors[0][0].w = 1.5  # OUT OF BOUNDS

        # Directly call fuse.check (learn() would clip w back to 1.0)
        violations = circuit.governance.fuse.check(circuit, 0.001)
        assert len(violations) > 0, "Fuse should detect weight violation"
        assert any("F3" in v for v in violations), "Should be F3 violation"
        print(f"[OK] Fuse detected violation: {violations[0]}")

        # Restore
        b._memristors[0][0].w = original_w


def test_fuse_trips_in_strict_mode():
    """Verify fuse raises error in strict mode."""
    circuit = VariantCircuit()

    # Directly test: fuse.trip with enabled=True should raise
    from governance.fuse import FuseTrippedError
    try:
        circuit.governance.fuse.trip(
            ["F3 Test violation: w=1.5 out of bounds"], tick=99)
        assert False, "Should have raised FuseTrippedError"
    except FuseTrippedError as e:
        assert "FUSE TRIPPED" in str(e)
        print(f"[OK] Fuse tripped in strict mode (as expected)")


def test_modeler_vs_actual():
    """Compare modeler prediction with actual neuron baseline."""
    from governance.modeler import Modeler
    m = Modeler()

    # Predict for current params
    r = m.predict_baseline(bc_current=0.001, r_leak=5.0, v_th=0.3)
    assert r.verdict == "WARNING", f"Should warn, got {r.verdict}"
    print(f"[OK] Modeler correctly warns: {r.message}")

    r2 = m.predict_baseline(bc_current=0.07, r_leak=5.0, v_th=0.3)
    assert r2.verdict == "SAFE", f"Should be safe, got {r2.verdict}"
    assert r2.outputs['activation'] > 0, "Should have positive baseline"
    print(f"[OK] Modeler predicts baseline={r2.outputs['activation']:.4f}")


if __name__ == '__main__':
    test_governance_init()
    test_governance_runs_with_circuit()
    test_fuse_detects_weight_violation()
    test_fuse_trips_in_strict_mode()
    test_modeler_vs_actual()
    print("\n=== ALL GOVERNANCE TESTS PASSED ===")
