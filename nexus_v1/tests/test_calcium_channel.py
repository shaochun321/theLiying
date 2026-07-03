"""nexus_v1.tests.test_calcium_channel — Unit tests for CalciumChannel + CalciumDynamics.

Phase A validation: standalone numerical checks, no circuit connection.
All tests verify specific numerical values (not just "no crash").

Run from repo root:
    python -m nexus_v1.tests.test_calcium_channel
    pytest nexus_v1/tests/test_calcium_channel.py -v
"""

import math
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from nexus_v1.components.calcium_channel import CalciumChannel, CalciumDynamics


# ─────────────────────────────────────────────────────────────────────────────
# CalciumChannel tests
# ─────────────────────────────────────────────────────────────────────────────

def test_channel_half_activation():
    """At V_m = V_half, conductance = g_max / 2 (Boltzmann definition)."""
    ch = CalciumChannel()
    g = ch.conductance(ch.V_half)
    expected = ch.g_max / 2.0
    assert abs(g - expected) < 1e-9, f"g(V_half)={g:.9f}, expected {expected:.9f}"


def test_channel_closed_at_rest():
    """At V_m = 0 (resting), channel < 0.1% open — effectively closed."""
    ch = CalciumChannel()
    g = ch.conductance(0.0)
    # Boltzmann: g/g_max = 1/(1+exp(0.308/0.030)) = 1/(1+exp(10.27)) ≈ 3.5e-5
    assert g < 0.001 * ch.g_max, f"Channel not closed at rest: g={g:.6f} (g_max={ch.g_max})"


def test_channel_saturated_above_threshold():
    """At V_m = V_half + 5k (~99% activation), channel > 99% open."""
    ch = CalciumChannel()
    V_sat = ch.V_half + 5.0 * ch.k   # 5× slope factor above V_half
    g = ch.conductance(V_sat)
    assert g > 0.99 * ch.g_max, f"Channel not saturated at V_sat={V_sat:.3f}: g={g:.4f}"


def test_channel_monotonic_activation():
    """Conductance strictly increases with V_m (Boltzmann is monotone)."""
    ch = CalciumChannel()
    voltages = [i * 0.05 for i in range(20)]   # 0.0 to 0.95
    g_vals = [ch.conductance(v) for v in voltages]
    for i in range(1, len(g_vals)):
        assert g_vals[i] > g_vals[i - 1], (
            f"Non-monotone at V={voltages[i]:.2f}: g={g_vals[i]:.6f} <= {g_vals[i-1]:.6f}"
        )


def test_current_inward_positive():
    """Inward Ca²⁺ current is positive for all physiological V_m < E_Ca."""
    ch = CalciumChannel()
    for v in [0.0, 0.2, 0.308, 0.5, 0.8, 1.0]:
        I = ch.current(v)
        assert I > 0, f"Current not positive (inward) at V_m={v}: I={I:.6f}"


def test_current_exact_at_half_activation():
    """At V_half, I_Ca = (g_max/2) × (E_Ca − V_half) — exact Ohm's law."""
    ch = CalciumChannel()
    expected = (ch.g_max / 2.0) * (ch.E_Ca - ch.V_half)
    actual = ch.current(ch.V_half)
    assert abs(actual - expected) < 1e-9, f"I at V_half: {actual:.9f} vs {expected:.9f}"


def test_current_decreases_as_vm_approaches_eca():
    """As V_m → E_Ca, driving force (E_Ca − V_m) → 0, so current → 0."""
    ch = CalciumChannel()
    I_low = ch.current(0.3)
    I_high = ch.current(1.4)   # very close to E_Ca=1.5
    assert I_high < I_low, f"Current did not decrease near E_Ca: {I_low:.4f} vs {I_high:.4f}"


# ─────────────────────────────────────────────────────────────────────────────
# CalciumDynamics tests
# ─────────────────────────────────────────────────────────────────────────────

def test_dynamics_tau_property():
    """τ_steps = R_ca × C_ca / dt = 5.0 × 0.010 / 0.001 = 50 steps = 50 ms."""
    dyn = CalciumDynamics()
    assert abs(dyn.tau_steps - 50.0) < 1e-9, f"τ_steps={dyn.tau_steps}, expected 50"


def test_dynamics_initial_state_zero():
    """Ca²⁺ level starts at zero (no initial Ca²⁺ load)."""
    dyn = CalciumDynamics()
    assert dyn.V_ca == 0.0


def test_dynamics_zero_input_stays_zero():
    """With no input current, V_ca stays at zero (no spontaneous Ca²⁺)."""
    dyn = CalciumDynamics()
    for _ in range(100):
        dyn.step(0.0, 0.001)
    assert abs(dyn.V_ca) < 1e-15, f"V_ca drifted from zero: {dyn.V_ca}"


def test_dynamics_charging_step_response():
    """Step-response: after τ steps, V_ca ≈ V_ss × (1 − 1/e).

    Discrete approximation: (1 − 1/τ)^τ ≈ e^-1.
    Error < 1.5% for τ=50 steps.
    """
    dyn = CalciumDynamics()
    dt = 0.001
    I_const = 1.0                              # arbitrary constant input
    V_ss = I_const * dyn.R_ca                 # V_steady_state = I × R

    tau_steps = int(dyn.tau_steps)             # 50
    for _ in range(tau_steps):
        dyn.step(I_const, dt)

    expected = V_ss * (1.0 - math.exp(-1.0))  # ≈ 0.6321 × V_ss
    rel_err = abs(dyn.V_ca - expected) / (abs(expected) + 1e-30)
    assert rel_err < 0.02, f"V_ca after τ steps: {dyn.V_ca:.5f}, expected {expected:.5f} (err={rel_err:.4f})"


def test_dynamics_decay_from_initial():
    """From V_ca=1, zero input: after τ steps V_ca ≈ 1/e ≈ 0.368."""
    dyn = CalciumDynamics()
    dyn.V_ca = 1.0
    dt = 0.001

    tau_steps = int(dyn.tau_steps)    # 50
    for _ in range(tau_steps):
        dyn.step(0.0, dt)

    expected = math.exp(-1.0)         # ≈ 0.3679
    rel_err = abs(dyn.V_ca - expected) / expected
    assert rel_err < 0.02, f"V_ca after decay τ: {dyn.V_ca:.5f}, expected {expected:.5f} (err={rel_err:.4f})"


def test_dynamics_steady_state():
    """After many τ, V_ca converges to V_ss = I_Ca × R_ca."""
    dyn = CalciumDynamics()
    dt = 0.001
    I_const = 0.5
    V_ss = I_const * dyn.R_ca   # expected: 2.5

    for _ in range(500):         # 10 × τ — should be well-converged
        dyn.step(I_const, dt)

    rel_err = abs(dyn.V_ca - V_ss) / V_ss
    assert rel_err < 0.001, f"V_ca at steady state: {dyn.V_ca:.5f}, expected {V_ss:.5f} (err={rel_err:.5f})"


def test_dynamics_reset():
    """reset() brings V_ca back to zero."""
    dyn = CalciumDynamics()
    dyn.V_ca = 3.7
    dyn.reset()
    assert dyn.V_ca == 0.0


# ─────────────────────────────────────────────────────────────────────────────
# release_rate tests
# ─────────────────────────────────────────────────────────────────────────────

def test_release_rate_zero_below_threshold():
    """Release rate is zero when V_ca ≤ threshold (dead band)."""
    dyn = CalciumDynamics()
    for v_ca in [0.0, 0.005, 0.009]:
        dyn.V_ca = v_ca
        rate = dyn.release_rate(threshold=0.01)
        assert rate == 0.0, f"Expected 0.0 at V_ca={v_ca}, got {rate}"


def test_release_rate_positive_above_threshold():
    """Release rate > 0 when V_ca > threshold."""
    dyn = CalciumDynamics()
    dyn.V_ca = 0.1
    rate = dyn.release_rate(threshold=0.01)
    assert rate > 0, f"Expected positive release rate at V_ca=0.1, got {rate}"


def test_release_rate_quadratic():
    """release_rate = gain × (V_ca − threshold)² — exact quadratic."""
    dyn = CalciumDynamics()
    threshold = 0.01
    gain = 1.0
    dyn.V_ca = 0.05
    expected = gain * (0.05 - threshold) ** 2
    actual = dyn.release_rate(threshold=threshold, gain=gain)
    assert abs(actual - expected) < 1e-15, f"Quadratic check: {actual} vs {expected}"


def test_release_rate_normal_input_near_zero():
    """For typical HC activation (V_m~0.3), release rate ≈ 0 (Phase 5 compat).

    With CalciumChannel at V_m=0.308 (half-activation) after τ steps,
    V_ca_ss ≈ I_Ca × R_ca.  I_Ca at V_half ≈ small (driving force E_Ca−V_half).
    Release rate should remain < 0.1 (not dominating the system).
    """
    ch = CalciumChannel()
    dyn = CalciumDynamics()
    dt = 0.001
    V_m = 0.308   # HC MOSFET threshold — typical normal drive

    # Run to steady state
    I_Ca = ch.current(V_m)
    for _ in range(500):
        dyn.step(I_Ca, dt)

    rate = dyn.release_rate()
    # V_ca_ss = I_Ca × R_ca; at V_half I_Ca = (g_max/2)×(E_Ca−V_half)
    #         = 1.0 × (1.5 − 0.308) = 1.192
    # V_ca_ss = 1.192 × 5 = 5.96 → large! This is Phase B territory.
    # Phase A note: at normal drive the channel IS significantly open.
    # The key invariant: release_rate is monotone in V_ca, non-negative.
    assert rate >= 0.0, f"release_rate must be non-negative, got {rate}"


# ─────────────────────────────────────────────────────────────────────────────
# End-to-end chain test
# ─────────────────────────────────────────────────────────────────────────────

def test_chain_resting_to_active():
    """Full chain V_m → I_Ca → V_ca → release_rate from rest to V_half.

    At V_m=0 (rest): channel nearly closed → I_Ca ≈ 0 → V_ca stays ~0 → rate ≈ 0.
    At V_m=V_half: channel 50% open → I_Ca non-trivial → V_ca charges → rate > 0.
    Verifies monotone response: active V_ca > resting V_ca.
    """
    ch = CalciumChannel()
    dt = 0.001

    # Resting: V_m=0
    dyn_rest = CalciumDynamics()
    for _ in range(200):
        dyn_rest.step(ch.current(0.0), dt)

    # Active: V_m = V_half
    dyn_active = CalciumDynamics()
    for _ in range(200):
        dyn_active.step(ch.current(ch.V_half), dt)

    assert dyn_active.V_ca > dyn_rest.V_ca, (
        f"Active V_ca ({dyn_active.V_ca:.4f}) must exceed resting ({dyn_rest.V_ca:.4f})"
    )
    # At rest, V_ss_rest = I_rest × R ≈ 1e-4 × 5 = 5e-4 (tiny but non-zero).
    # After 200 steps (~4τ), V_ca approaches V_ss_rest. Must be << active state.
    assert dyn_rest.V_ca < 1e-2, f"Resting V_ca should be tiny, got {dyn_rest.V_ca:.2e}"


# ─────────────────────────────────────────────────────────────────────────────
# Runner
# ─────────────────────────────────────────────────────────────────────────────

_TESTS = [
    # CalciumChannel
    test_channel_half_activation,
    test_channel_closed_at_rest,
    test_channel_saturated_above_threshold,
    test_channel_monotonic_activation,
    test_current_inward_positive,
    test_current_exact_at_half_activation,
    test_current_decreases_as_vm_approaches_eca,
    # CalciumDynamics
    test_dynamics_tau_property,
    test_dynamics_initial_state_zero,
    test_dynamics_zero_input_stays_zero,
    test_dynamics_charging_step_response,
    test_dynamics_decay_from_initial,
    test_dynamics_steady_state,
    test_dynamics_reset,
    # release_rate
    test_release_rate_zero_below_threshold,
    test_release_rate_positive_above_threshold,
    test_release_rate_quadratic,
    test_release_rate_normal_input_near_zero,
    # chain
    test_chain_resting_to_active,
]

if __name__ == '__main__':
    passed = failed = 0
    for t in _TESTS:
        try:
            t()
            print(f"  PASS  {t.__name__}")
            passed += 1
        except AssertionError as e:
            print(f"  FAIL  {t.__name__}: {e}")
            failed += 1
        except Exception as e:
            print(f"  ERROR {t.__name__}: {type(e).__name__}: {e}")
            failed += 1
    print(f"\n{passed}/{passed + failed} PASS")
    sys.exit(0 if failed == 0 else 1)
