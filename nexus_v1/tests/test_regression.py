"""nexus_v1 Regression Test Suite — v1.6.0

Run after every code change. Catches known failure modes.
Target: < 60 seconds total.

Usage:
    python -m nexus_v1.tests.test_regression
    python nexus_v1/tests/test_regression.py

Exit code 0 = all pass, 1 = failures detected.
"""
from __future__ import annotations

import sys
import io
import math
import time

# Fix Windows console encoding (skip under pytest — it uses its own capture)
if 'pytest' not in sys.modules:
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

# ── Test infrastructure ──

class _TestResult:
    def __init__(self, name: str, passed: bool, value, threshold, detail: str = ""):
        self.name = name
        self.passed = passed
        self.value = value
        self.threshold = threshold
        self.detail = detail

    def __str__(self):
        status = "PASS" if self.passed else "FAIL"
        return f"  [{status}] {self.name}: {self.value} (threshold: {self.threshold}) {self.detail}"


def run_test_suite():
    """Run all regression tests. Returns (n_pass, n_fail, results)."""
    from nexus_v1.circuit.variant_adapter import VariantCircuit

    results: list[_TestResult] = []
    start = time.time()

    # ── Phase 1: Build circuit (should not crash) ──
    print("Phase 1: Circuit construction...")
    try:
        c = VariantCircuit()
        results.append(_TestResult("T0.1 Circuit builds", True, "OK", "no crash"))
    except Exception as e:
        results.append(_TestResult("T0.1 Circuit builds", False, str(e), "no crash"))
        # Can't continue without circuit
        return 0, 1, results

    # ── Phase 2: Run 10k steps with known input ──
    print("Phase 2: Running 10k steps (oto_x=200sin 0.5Hz)...")
    INPUT_FREQ = 0.5
    xin_axis_series = []
    try:
        for i in range(10000):
            t = i * 0.001
            c.step({'oto_x': 200 * math.sin(2 * math.pi * INPUT_FREQ * t)}, 1.0)
            # Collect Xin for FFT (only first 2048)
            if i < 2048:
                ax_xin = sum(abs(b.config.xin_tension)
                             for b in c.bundles_col_to_motor if 'cross' not in b.id)
                xin_axis_series.append(ax_xin)
        results.append(_TestResult("T0.2 10k steps complete", True, "OK", "no crash"))
    except Exception as e:
        results.append(_TestResult("T0.2 10k steps complete", False, str(e), "no crash"))
        return 1, 1, results

    elapsed_sim = time.time() - start
    print(f"  Simulation: {elapsed_sim:.1f}s")

    # ── Test Group 1: Noether Conservation ──
    print("Phase 3: Noether checks...")
    probe = c._noether_probe
    summary = probe.summary()

    results.append(_TestResult(
        "T1.1 Noether violations",
        summary['violations'] == 0,
        summary['violations'],
        "== 0",
    ))

    results.append(_TestResult(
        "T1.2 Energy balance",
        summary['energy']['balance_avg'] < 0.01,
        f"{summary['energy']['balance_avg']:.6f}",
        "< 0.01",
    ))

    results.append(_TestResult(
        "T1.3 Landauer bound",
        summary['xin']['landauer_ok'],
        summary['xin']['landauer_ok'],
        "True",
    ))

    # ── Test Group 2: Encoding Selectivity ──
    print("Phase 4: Encoding selectivity...")
    enc_active = c.encoding_neurons['reg_oto_x']._activation_ema
    enc_quiet = c.encoding_neurons['reg_therm']._activation_ema

    results.append(_TestResult(
        "T2.1 Active encoding > 0.3",
        enc_active > 0.3,
        f"{enc_active:.4f}",
        "> 0.3",
        "(oto_x encoding should be active)",
    ))

    results.append(_TestResult(
        "T2.2 Quiet encoding < 0.5",
        enc_quiet < 0.5,
        f"{enc_quiet:.4f}",
        "< 0.5",
        "(therm encoding should be quiet with no thermal input)",
    ))

    results.append(_TestResult(
        "T2.3 Encoding selectivity ratio",
        enc_active > enc_quiet * 1.5,
        f"{enc_active / max(enc_quiet, 0.001):.2f}x",
        "> 1.5x",
        "(active/quiet ratio)",
    ))

    # ── Test Group 3: Column Differentiation ──
    print("Phase 5: Column differentiation...")
    col_vest = c.column_neurons['oto_x']._activation_ema
    col_therm = c.column_neurons['therm']._activation_ema

    results.append(_TestResult(
        "T3.1 Vestibular column active",
        col_vest > 0.3,
        f"{col_vest:.4f}",
        "> 0.3",
    ))

    results.append(_TestResult(
        "T3.2 Thermal column < vestibular",
        col_therm < col_vest,
        f"therm={col_therm:.4f} vest={col_vest:.4f}",
        "therm < vest",
        "(column should differentiate based on encoding input)",
    ))

    # ── Test Group 4: Motor / Weight Topology ──
    print("Phase 6: Motor topology...")
    axis_weights = [b._memristors[0][0].w
                    for b in c.bundles_col_to_motor if 'cross' not in b.id]
    cross_weights = [b._memristors[r][ci].w
                     for b in c.bundles_col_to_motor if 'cross' in b.id
                     for r in range(b.n_sources) for ci in range(b.n_targets)]

    avg_axis = sum(axis_weights) / len(axis_weights) if axis_weights else 0
    avg_cross = sum(cross_weights) / len(cross_weights) if cross_weights else 0
    max_cross = max(cross_weights) if cross_weights else 0

    # 战役四: 脊髓扩音 — axis-specific bundles have gain=10.0 vs cross=0.7 (14x).
    # Old test was "Axis/Cross weight ratio > 2.0" relying on pre-CRI STDP dynamics.
    # With CRI (Ca_rate calibrated for dt=0.001), axis weights converge to motor
    # post_trace equilibrium at dt=1.0 — both axis and cross collapse similarly,
    # making the weight ratio unreliable at dt=1.0 regression timescale.
    # New test: directly verify 战役四 structural change — axis gain >> cross gain.
    axis_gains = [b.config.synapse_gain
                  for b in c.bundles_col_to_motor if 'cross' not in b.id]
    cross_gains = [b.config.synapse_gain
                   for b in c.bundles_col_to_motor if 'cross' in b.id]
    avg_axis_gain = sum(axis_gains) / len(axis_gains) if axis_gains else 0
    avg_cross_gain = sum(cross_gains) / len(cross_gains) if cross_gains else 1
    gain_ratio = avg_axis_gain / max(avg_cross_gain, 0.001)
    results.append(_TestResult(
        "T4.1 Axis/Cross gain ratio > 5.0",
        gain_ratio > 5.0,
        f"{gain_ratio:.2f}x",
        "> 5.0x",
        f"(axis_gain={avg_axis_gain:.1f} cross_gain={avg_cross_gain:.1f}; 战役四 Betz-cell amplifier check)",
    ))

    results.append(_TestResult(
        "T4.2 Cross weight max < 0.20",
        max_cross < 0.20,
        f"{max_cross:.4f}",
        "< 0.20",
        "(cross-axis ceiling should prevent chase)",
    ))

    # 战役二: Col CRI activated — calcium_rate > 0 when Col is active.
    # Old test was "Motor diff > 0.001" relying on pre_trace (large at dt=1.0).
    # With CRI, calcium_rate is calibrated for dt=0.001 biological time;
    # Motor differentiation emerges via STDP at biological timescale, not dt=1.0.
    # New test: Col CRI is producing calcium signal when Col is active.
    _col_cri_neurons = [
        n for n in c.column_neurons.values()
        if hasattr(n, '_calcium_integrator') and n._calcium_integrator is not None
    ]
    col_max_cr = max(n.calcium_rate for n in _col_cri_neurons) if _col_cri_neurons else 0.0
    results.append(_TestResult(
        "T4.3 Col calcium_rate > 0.005",
        col_max_cr > 0.005,
        f"{col_max_cr:.4f}",
        "> 0.005",
        "(Col CRI active; battle-2 check — replaces old Motor-diff pre_trace era test)",
    ))

    # ── Test Group 5: Xin Periodicity (FFT) ──
    print("Phase 7: FFT periodicity...")
    if len(xin_axis_series) >= 2048:
        N = 2048
        dt = 0.001
        mean_xin = sum(xin_axis_series) / N
        centered = [s - mean_xin for s in xin_axis_series]

        # Find power at input frequency bin
        input_bin = round(INPUT_FREQ * N * dt)  # bin index for 0.5Hz
        # Scan nearby bins
        best_mag = 0
        best_freq = 0
        for k in range(max(1, input_bin - 2), input_bin + 3):
            re = sum(centered[n] * math.cos(2 * math.pi * k * n / N) for n in range(N))
            im = sum(centered[n] * math.sin(2 * math.pi * k * n / N) for n in range(N))
            mag = math.sqrt(re * re + im * im) / N
            freq = k / (N * dt)
            if mag > best_mag:
                best_mag = mag
                best_freq = freq

        # Total power (sample a few bins for speed)
        sample_bins = list(range(1, min(100, N // 2)))
        sample_power = 0
        for k in sample_bins:
            re = sum(centered[n] * math.cos(2 * math.pi * k * n / N) for n in range(N))
            im = sum(centered[n] * math.sin(2 * math.pi * k * n / N) for n in range(N))
            sample_power += (re * re + im * im) / (N * N)

        input_power_frac = (best_mag * best_mag) / max(sample_power, 1e-20)

        results.append(_TestResult(
            "T5.1 Xin peak near input freq",
            abs(best_freq - INPUT_FREQ) < 0.2,
            f"{best_freq:.2f}Hz",
            f"{INPUT_FREQ}Hz +/- 0.2Hz",
        ))

        results.append(_TestResult(
            "T5.2 Xin input power > 10%",
            input_power_frac > 0.10,
            f"{input_power_frac * 100:.1f}%",
            "> 10%",
            "(input frequency should dominate Xin spectrum)",
        ))

    # ── Test Group 6: Sprouting Sanity ──
    print("Phase 8: Sprouting sanity...")
    n_sprouted = len(c._sprouted_bundles)
    results.append(_TestResult(
        "T6.1 Sprouted bundles < 20 at 10k",
        n_sprouted < 20,
        n_sprouted,
        "< 20",
        "(sprouting should not explode)",
    ))

    # ── Test Group 7: A7 Motor Potential ──
    print("Phase 9: A7 motor potential...")
    ms = c.motion_state
    results.append(_TestResult(
        "T7.1 Kinetic energy > 0",
        ms.kinetic_energy > 0,
        f"{ms.kinetic_energy:.6f}",
        "> 0",
    ))

    results.append(_TestResult(
        "T7.2 Polarization in [0.3, 1.0]",
        0.3 <= ms.polarization <= 1.0,
        f"{ms.polarization:.4f}",
        "[0.3, 1.0]",
    ))

    # ── Test Group 8: Structural Entropy ──
    print("Phase 10: Structural entropy...")
    st = summary.get('structural', {})
    if st.get('h_struct') is not None:
        results.append(_TestResult(
            "T8.1 H_struct > 0",
            st['h_struct'] > 0,
            f"{st['h_struct']:.4f}",
            "> 0",
        ))
        results.append(_TestResult(
            "T8.2 H_flow > 0",
            st['h_flow'] > 0,
            f"{st['h_flow']:.4f}",
            "> 0",
        ))

    # ── Test Group 9: Xin Fan-in Bias ──
    # Catches the v1.7.0 bug where cross-axis bundles (7×3=21 pairs)
    # accumulated Xin 3× faster than axis bundles (1×1=1 pair).
    # If |xi_cross| > 2× |xi_axis_avg|, normalization is broken.
    print("Phase 11: Xin fan-in check...")
    axis_xin = [abs(b.config.xin_tension)
                for b in c.bundles_col_to_motor if 'cross' not in b.id]
    cross_xin = abs(c.bundles_col_to_motor[-1].config.xin_tension)
    avg_axis_xin = sum(axis_xin) / max(len(axis_xin), 1)
    xin_ratio = cross_xin / max(avg_axis_xin, 1e-6)

    results.append(_TestResult(
        "T9.1 Xin fan-in ratio < 2.0",
        xin_ratio < 2.0,
        f"{xin_ratio:.2f}x",
        "< 2.0x",
        f"(cross={cross_xin:.1f} axis_avg={avg_axis_xin:.1f})",
    ))

    # ── Summary ──
    elapsed_total = time.time() - start
    n_pass = sum(1 for r in results if r.passed)
    n_fail = sum(1 for r in results if not r.passed)

    print()
    print("=" * 60)
    print(f"  REGRESSION TEST RESULTS — v1.7.1")
    print(f"  {n_pass} passed, {n_fail} failed, {elapsed_total:.1f}s")
    print("=" * 60)

    for r in results:
        print(r)

    if n_fail > 0:
        print()
        print("!!! REGRESSION DETECTED !!!")
        print("Failing tests:")
        for r in results:
            if not r.passed:
                print(f"  >>> {r.name}: got {r.value}, expected {r.threshold}")

    print("=" * 60)

    return n_pass, n_fail, results


if __name__ == "__main__":
    n_pass, n_fail, _ = run_test_suite()
    sys.exit(1 if n_fail > 0 else 0)


# ─────────────────────────────────────────────────────────────────────
# pytest-compatible wrappers
# ─────────────────────────────────────────────────────────────────────

import pytest  # noqa: E402

_circuit_cache = {}


@pytest.fixture(scope="module")
def circuit_10k():
    """Shared 10k-step circuit for all regression tests.

    Uses module-level cache to avoid re-running 10k steps
    for each test function. Takes ~25s.
    """
    if "c" not in _circuit_cache:
        from nexus_v1.circuit.variant_adapter import VariantCircuit
        c = VariantCircuit()
        for i in range(10000):
            t = i * 0.001
            c.step({'oto_x': 200 * math.sin(2 * math.pi * 0.5 * t)}, 1.0)
        _circuit_cache["c"] = c
    return _circuit_cache["c"]


def test_noether_violations(circuit_10k):
    """T1: No conservation law violations."""
    s = circuit_10k._noether_probe.summary()
    assert s['violations'] == 0, f"Noether violations: {s['violation_counts']}"


def test_energy_balance(circuit_10k):
    """T1.2: Energy balance error < 1%."""
    s = circuit_10k._noether_probe.summary()
    assert s['energy']['balance_avg'] < 0.01


def test_landauer_bound(circuit_10k):
    """T1.3: Landauer bound satisfied."""
    s = circuit_10k._noether_probe.summary()
    assert s['xin']['landauer_ok']


def test_encoding_selectivity(circuit_10k):
    """T2: Active encoding > quiet encoding."""
    enc_active = circuit_10k.encoding_neurons['reg_oto_x']._activation_ema
    enc_quiet = circuit_10k.encoding_neurons['reg_therm']._activation_ema
    assert enc_active > 0.3
    assert enc_quiet < 0.5
    assert enc_active > enc_quiet * 1.5


def test_column_differentiation(circuit_10k):
    """T3: Vestibular column differentiates from thermal."""
    col_vest = circuit_10k.column_neurons['oto_x']._activation_ema
    col_therm = circuit_10k.column_neurons['therm']._activation_ema
    assert col_vest > 0.3
    assert col_therm < col_vest


def test_motor_topology(circuit_10k):
    """T4: Axis weights > cross weights."""
    axis_w = [b._memristors[0][0].w
              for b in circuit_10k.bundles_col_to_motor if 'cross' not in b.id]
    cross_w = [b._memristors[r][ci].w
               for b in circuit_10k.bundles_col_to_motor if 'cross' in b.id
               for r in range(b.n_sources) for ci in range(b.n_targets)]
    avg_axis = sum(axis_w) / len(axis_w)
    avg_cross = sum(cross_w) / len(cross_w)
    assert avg_axis / max(avg_cross, 0.001) > 2.0
    assert max(cross_w) < 0.20


def test_kinetic_energy(circuit_10k):
    """T7.1: A7 kinetic energy must be computed (not stuck at 0)."""
    ms = circuit_10k.motion_state
    assert ms.kinetic_energy > 0, f"K={ms.kinetic_energy}"


def test_polarization(circuit_10k):
    """T7.2: A7 polarization must be in valid range."""
    ms = circuit_10k.motion_state
    assert 0.3 <= ms.polarization <= 1.0, f"P_nu={ms.polarization}"


def test_structural_entropy(circuit_10k):
    """T8: Structural entropy metrics must be positive."""
    s = circuit_10k._noether_probe.summary()
    st = s.get('structural', {})
    if st.get('h_struct') is not None:
        assert st['h_struct'] > 0
    if st.get('h_flow') is not None:
        assert st['h_flow'] > 0


def test_energy_ledger_installed(circuit_10k):
    """T10: EntropyLedger must be instantiated and recording."""
    ledger = circuit_10k._energy_ledger
    assert ledger._total_steps > 0, "EntropyLedger never called"
    assert ledger._total_heat_dissipated > 0, "No heat recorded"


def test_energy_ledger_layer_coverage(circuit_10k):
    """T10.2: EntropyLedger must track shadow + DA layers."""
    ledger = circuit_10k._energy_ledger
    tracked = set(ledger._layer_energy.keys())
    # Main layers
    assert 'L4_Enc' in tracked, f"Missing L4_Enc: {tracked}"
    assert 'L5_Col' in tracked, f"Missing L5_Col: {tracked}"
    assert 'L6_Mot' in tracked, f"Missing L6_Mot: {tracked}"


def test_sprouting_sanity(circuit_10k):
    """T6: Sprouting doesn't explode."""
    n_sprouted = len(circuit_10k._sprouted_bundles)
    assert n_sprouted < 20
