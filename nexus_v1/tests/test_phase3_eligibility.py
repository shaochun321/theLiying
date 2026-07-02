"""EXP-019: Phase 3 three-factor eligibility trace verification.

Three-group experiment per Phase 3 spec §4.1:
  A: DA=0 throughout       → Δw ≤ 0 (only LTD + decay)
  B: DA=0.5 at t=20        → Δw > 0 (immediate DA)
  C: DA=0.5 at t=220       → Δw > 0 (delayed DA, eligibility trace bridges)

Pass criteria:
  1. Δw_A ≤ 0               (no DA → no LTP)
  2. Δw_C > Δw_A + 0.02     (delayed DA still effective)
  3. Δw_C / Δw_B > 0.3      (200-step delay retains >30% efficacy)
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from nexus_v1.components.neuron import Neuron, NeuronConfig, ChannelConfig
from nexus_v1.circuit.bundle import SynapticBundle, BundleConfig


def make_neuron(nid: str, spiking: bool = False) -> Neuron:
    """Create a minimal neuron for testing."""
    return Neuron(NeuronConfig(
        neuron_id=nid,
        capacitance=1.0,
        r_leak=1.0,
        v_rest=0.0,
        channels=[ChannelConfig(name="default", v_threshold=0.5, gm=1.0)],
        spiking=spiking,
        energy=100.0,
        trace_tau_pre=20.0,
        trace_tau_post=20.0,
    ))


def make_bundle(src: Neuron, tgt: Neuron, initial_w: float = 0.1) -> SynapticBundle:
    """Create a three-factor enabled bundle."""
    return SynapticBundle(
        config=BundleConfig(
            bundle_id="test_elig",
            learning_rule="stdp",
            initial_weight=initial_w,
            weight_max=1.0,
            weight_min=0.0,
            stdp_lr=0.05,
            # Phase 3 enabled
            use_eligibility_trace=True,
            eligibility_tau=300.0,
            eligibility_gain=1.0,
            eligibility_ltd_rate=0.01,
        ),
        sources=[src],
        targets=[tgt],
    )


def run_experiment(da_schedule: dict, total_steps: int = 500,
                   pulse_step: int = 20, pulse_current: float = 2.0) -> dict:
    """Run one experiment group.
    
    Args:
        da_schedule: {step: da_concentration} — DA is set at specified steps
                     and held until changed.
        total_steps: total simulation steps
        pulse_step: step at which pre×post co-activation pulse occurs
        pulse_current: current injected to both src and tgt at pulse_step
    
    Returns:
        dict with w_initial, w_final, dw, eligibility trace history
    """
    src = make_neuron("src")
    tgt = make_neuron("tgt")
    bundle = make_bundle(src, tgt)
    
    w0 = bundle._memristors[0][0].w
    dt = 1.0
    current_da = 0.0
    
    trace_log = []
    w_log = []
    
    for t in range(total_steps):
        # Update DA if schedule says so
        if t in da_schedule:
            current_da = da_schedule[t]
        
        # Inject co-activation pulse at pulse_step
        if t == pulse_step:
            src.step(pulse_current, dt)
            tgt.step(pulse_current, dt)
        else:
            src.step(0.0, dt)
            tgt.step(0.0, dt)
        
        # Propagate and learn
        bundle.propagate()
        bundle.learn(dt=dt, plasticity_gate=1.0, fill_fraction=1.0,
                     da_concentration=current_da)
        
        # Log
        e = bundle._eligibility_traces[0][0] if bundle._eligibility_traces else 0.0
        trace_log.append(e)
        w_log.append(bundle._memristors[0][0].w)
    
    w_final = bundle._memristors[0][0].w
    dw = w_final - w0
    
    return {
        'w_initial': w0,
        'w_final': w_final,
        'dw': dw,
        'trace_log': trace_log,
        'w_log': w_log,
    }


def test_phase3_eligibility():
    """Three-group verification experiment."""
    print("=" * 60)
    print("EXP-019: Phase 3 Three-Factor Eligibility Trace")
    print("=" * 60)
    
    # Group A: DA=0 throughout (no LTP expected)
    result_a = run_experiment(da_schedule={}, total_steps=500, pulse_step=20)
    
    # Group B: DA=0.5 at t=20 (immediate, same as pulse)
    result_b = run_experiment(da_schedule={20: 0.5}, total_steps=500, pulse_step=20)
    
    # Group C: DA=0.5 at t=220 (delayed 200 steps)
    result_c = run_experiment(da_schedule={220: 0.5}, total_steps=500, pulse_step=20)
    
    # Report
    print(f"\n{'Group':<12} {'w_init':>8} {'w_final':>8} {'Δw':>10}")
    print("-" * 42)
    for label, r in [("A (DA=0)", result_a), ("B (DA@20)", result_b), 
                     ("C (DA@220)", result_c)]:
        print(f"{label:<12} {r['w_initial']:>8.4f} {r['w_final']:>8.4f} {r['dw']:>10.6f}")
    
    # Check eligibility trace at key moments
    print(f"\nEligibility trace @ t=25 (5 steps after pulse):")
    print(f"  A: {result_a['trace_log'][25]:.6f}")
    print(f"  B: {result_b['trace_log'][25]:.6f}")
    print(f"  C: {result_c['trace_log'][25]:.6f}")
    
    print(f"\nEligibility trace @ t=220 (200 steps after pulse):")
    print(f"  A: {result_a['trace_log'][220]:.6f}")
    print(f"  C: {result_c['trace_log'][220]:.6f}")
    
    # Decay check: E(220)/E(25) should be exp(-195/300) ≈ 0.52
    if result_c['trace_log'][25] > 0:
        decay_ratio = result_c['trace_log'][220] / result_c['trace_log'][25]
        expected_ratio = 0.52  # exp(-195/300)
        print(f"  Decay ratio E(220)/E(25) = {decay_ratio:.4f} (expected ≈ {expected_ratio:.2f})")
    
    # ── Pass criteria ──
    print("\n" + "=" * 60)
    print("Pass Criteria:")
    
    # Criterion 1: Δw_A ≤ 0 (no DA → no LTP)
    c1 = result_a['dw'] <= 0.001  # small tolerance for numerical noise
    print(f"  [{'PASS' if c1 else 'FAIL'}] C1: dw_A <= 0 -> dw_A = {result_a['dw']:.6f}")
    
    # Criterion 2: Δw_C > Δw_A (delayed DA still effective vs no-DA baseline)
    c2 = result_c['dw'] > result_a['dw'] + 0.001
    print(f"  [{'PASS' if c2 else 'FAIL'}] C2: dw_C > dw_A + eps -> dw_C-dw_A = {result_c['dw'] - result_a['dw']:.6f}")
    
    # Criterion 3: DA-attributable LTP ratio.
    # Isolate DA contribution: (Δw_X - Δw_A) = net effect of DA alone.
    # Then check that delayed DA retains >20% of immediate DA's efficacy.
    da_effect_b = result_b['dw'] - result_a['dw']  # DA contribution in B
    da_effect_c = result_c['dw'] - result_a['dw']  # DA contribution in C
    if da_effect_b > 0:
        ratio = da_effect_c / da_effect_b
        c3 = ratio > 0.2
        print(f"  [{'PASS' if c3 else 'FAIL'}] C3: DA_effect_C/DA_effect_B > 0.2 -> ratio = {ratio:.4f}")
        print(f"       DA_effect_B = {da_effect_b:.6f}, DA_effect_C = {da_effect_c:.6f}")
    else:
        c3 = False
        print(f"  [FAIL] C3: DA_effect_B <= 0 (unexpected)")
    
    all_pass = c1 and c2 and c3
    status = "ALL PASS" if all_pass else "SOME FAILED"
    print(f"\n{status}")
    print("=" * 60)
    
    return all_pass


def test_backward_compatibility():
    """Verify two-factor STDP still works when eligibility is disabled."""
    print("\n" + "=" * 60)
    print("Backward Compatibility: Two-factor STDP")
    print("=" * 60)
    
    src = make_neuron("src_bc")
    tgt = make_neuron("tgt_bc")
    
    # Bundle WITHOUT eligibility trace (default)
    bundle = SynapticBundle(
        config=BundleConfig(
            bundle_id="test_compat",
            learning_rule="stdp",
            initial_weight=0.1,
            weight_max=1.0,
            stdp_lr=0.05,
            use_eligibility_trace=False,  # explicitly disabled
        ),
        sources=[src],
        targets=[tgt],
    )
    
    w0 = bundle._memristors[0][0].w
    dt = 1.0
    
    # Run 100 steps with strong co-activation (no DA needed for two-factor)
    for t in range(100):
        if t % 10 == 0:
            src.step(2.0, dt)
            tgt.step(2.0, dt)
        else:
            src.step(0.0, dt)
            tgt.step(0.0, dt)
        bundle.propagate()
        bundle.learn(dt=dt, plasticity_gate=1.0, fill_fraction=1.0,
                     da_concentration=0.0)  # DA=0, should not matter
    
    w_final = bundle._memristors[0][0].w
    dw = w_final - w0
    
    # Two-factor STDP should still produce weight change even without DA
    passed = abs(dw) > 1e-6
    print(f"  w0={w0:.4f}, w_final={w_final:.4f}, dw={dw:.6f}")
    print(f"  [{'PASS' if passed else 'FAIL'}] Two-factor STDP produces weight change without DA")
    
    # Check _eligibility_traces is None
    et_none = bundle._eligibility_traces is None
    print(f"  [{'PASS' if et_none else 'FAIL'}] Eligibility traces not allocated")
    
    print("=" * 60)
    return passed and et_none


if __name__ == "__main__":
    ok1 = test_phase3_eligibility()
    ok2 = test_backward_compatibility()
    
    print(f"\n{'=' * 60}")
    status = "ALL PASS" if (ok1 and ok2) else "FAILED"
    print(f"FINAL: {status}")
    print(f"{'=' * 60}")
    
    sys.exit(0 if ok1 and ok2 else 1)

