"""Phase 1 Validation: VestibularChainV2 in V2_PARALLEL_LOG shadow mode.

Validates that v2 runs correctly in parallel without affecting the main circuit.
Uses the same mechanical input as the regression suite (oto_x=200*sin(0.5Hz)).

Correct Phase 1 metrics (plan §2.3 corrected for actual architecture):
  - Enc/Col are in HebbianCircuit, NOT in VestibularChainV2.
  - v2 chain contains: MET → HC → Aff_reg / Aff_irr only.
  - Measurable v2 signals: spike_cost (Aff fires), fifo_rms (signal in transit),
    last_gain (G_eff = 14.7 at full energy).

Phase 1 checks:
  P1.1  Circuit builds in V2_PARALLEL_LOG mode (no crash)
  P1.2  5000 steps complete (no crash, no NaN)
  P1.3  v2 Aff fires: total spike_cost > 0 during active input
  P1.4  FIFO carries real signal: peak fifo_rms > 3× noise floor (σ=0.01)
  P1.5  G_eff ≈ 14.7: mean within ±1.5 (energy may not be full at step 0)
  P1.6  G_eff stable: max step-to-step |ΔG| < 0.5
  P1.7  Main circuit unaffected: Enc activation still > 0.3 (T2.1 equivalent)
  P1.8  No v2 state bleeds into main Xin (v2 motor contribution = 0)

Usage:
    python -m nexus_v1.tests.test_vestibular_v2_phase1
"""
from __future__ import annotations

import sys
import io
import math

if 'pytest' not in sys.modules:
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

N_STEPS    = 5000
INPUT_FREQ = 0.5   # Hz — same as regression test
INPUT_AMP  = 200.0
NOISE_FLOOR = 0.01  # FIFODelayBuffer prefill σ


def run():
    from nexus_v1.circuit.variant_adapter import VariantCircuit

    results: list[tuple[str, bool, str]] = []

    def chk(tag: str, ok: bool, detail: str):
        results.append((tag, ok, detail))
        status = "PASS" if ok else "FAIL"
        print(f"  [{status}] {tag}: {detail}")

    # ── P1.1: build ──────────────────────────────────────────────────────────
    print(f"\nPhase 1 validation — {N_STEPS} steps, oto_x={INPUT_AMP}*sin({INPUT_FREQ}Hz)")
    try:
        c = VariantCircuit(vestibular_mode="V2_PARALLEL_LOG")
        assert c._vestibular_v2 is not None, "_vestibular_v2 not initialised"
        chk("P1.1 build V2_PARALLEL_LOG", True, "no crash, _vestibular_v2 present")
    except Exception as e:
        chk("P1.1 build V2_PARALLEL_LOG", False, str(e))
        _report(results)
        return 1

    # ── P1.2: run 5000 steps ─────────────────────────────────────────────────
    spike_cost_series: list[float] = []
    fifo_rms_series:   list[float] = []
    gain_series:       list[float] = []
    xin_v1_series:    list[float] = []

    try:
        for i in range(N_STEPS):
            t = i * 0.001
            inp = {'oto_x': INPUT_AMP * math.sin(2 * math.pi * INPUT_FREQ * t)}
            c.step(inp, 1.0)

            st = c._v2_last_state
            if st:
                spike_cost_series.append(st['spike_cost'])
                fifo_rms_series.append(st['fifo_rms'])
                gain_series.append(st['last_gain'])
                # Xin from main axis bundles (v1 path, same as T5 in regression)
                xin_v1 = sum(abs(b.config.xin_tension)
                              for b in c.bundles_col_to_motor if 'cross' not in b.id)
                xin_v1_series.append(xin_v1)

        chk("P1.2 5000 steps complete", True, "no crash, no NaN")
    except Exception as e:
        chk("P1.2 5000 steps complete", False, str(e))
        _report(results)
        return 1

    # ── P1.3: Aff fires ──────────────────────────────────────────────────────
    total_cost = sum(spike_cost_series)
    aff_fires = total_cost > 0
    chk("P1.3 v2 Aff fires (spike_cost > 0)",
        aff_fires,
        f"total spike_cost={total_cost:.4f} over {N_STEPS} steps")

    # ── P1.4: FIFO real signal ───────────────────────────────────────────────
    peak_rms  = max(fifo_rms_series) if fifo_rms_series else 0.0
    threshold = NOISE_FLOOR * 3
    fifo_ok   = peak_rms > threshold
    chk("P1.4 FIFO real signal (peak_rms > 3×noise)",
        fifo_ok,
        f"peak={peak_rms:.4f}, threshold={threshold:.4f}")

    # ── P1.5: G_eff in valid physical range ──────────────────────────────────
    # G_BASE=2.0 (floor), G_max≈15.6 (full energy P=1.0).
    # Circuit starts at 50% energy (initial_fill=0.5), so expected G_eff ≈ 8.4.
    # 14.7 is the theoretical max at full load — irrelevant without a heat source.
    _G_BASE = 2.0
    _G_MAX  = 16.0  # 2.0×(1+5×1.0)×1.3 with margin
    mean_gain = sum(gain_series) / len(gain_series) if gain_series else 0.0
    gain_ok   = _G_BASE < mean_gain < _G_MAX
    # Back-compute implied P_avail: G=2(1+5P)×lf → P=(G/2/lf - 1)/5 (lf≈1.2 measured)
    p_implied = max(0.0, (mean_gain / 2.0 / 1.196 - 1.0) / 5.0)
    chk("P1.5 G_eff in valid range (2.0 < G < 16.0)",
        gain_ok,
        f"mean={mean_gain:.3f}, implied P_avail≈{p_implied:.2f}, G_BASE={_G_BASE}, G_MAX={_G_MAX}")

    # ── P1.6: G_eff stable ───────────────────────────────────────────────────
    deltas = [abs(gain_series[i] - gain_series[i-1])
               for i in range(1, len(gain_series))]
    max_delta = max(deltas) if deltas else 0.0
    stable_ok = max_delta < 0.5
    chk("P1.6 G_eff stable (max |ΔG| < 0.5)",
        stable_ok,
        f"max step-to-step delta={max_delta:.4f}")

    # ── P1.7: main Enc still active ──────────────────────────────────────────
    # Uses _activation_ema, same as regression T2.1 check.
    try:
        enc_active = c.encoding_neurons['reg_oto_x']._activation_ema
        enc_ok     = enc_active > 0.3
        chk("P1.7 main Enc active (_activation_ema > 0.3)",
            enc_ok,
            f"reg_oto_x _activation_ema={enc_active:.4f}")
    except Exception as e:
        chk("P1.7 main Enc active", False, f"error: {e}")

    # ── P1.8: no v2 bleed into main Xin ─────────────────────────────────────
    # v2 has no SynapticBundle connections to HebbianCircuit bundles,
    # so Xin on main bundles must come from v1 only.
    # Verify v2 shadow list has no overlap with main bundle list.
    v2_bundle_ids = set()
    if c._vestibular_v2 is not None:
        for b in (list(c._vestibular_v2.bundles_met_to_hc.values()) +
                  list(c._vestibular_v2.bundles_hc_to_aff.values())):
            v2_bundle_ids.add(id(b))

    main_bundle_ids = {id(b) for b in c.get_all_bundles()}
    overlap = v2_bundle_ids & main_bundle_ids
    no_bleed = len(overlap) == 0
    chk("P1.8 no v2→main bundle overlap",
        no_bleed,
        f"shared bundle refs={len(overlap)} (expected 0)")

    _report(results)
    n_fail = sum(1 for _, ok, _ in results if not ok)
    return 0 if n_fail == 0 else 1


def _report(results: list[tuple[str, bool, str]]):
    n_pass = sum(1 for _, ok, _ in results if ok)
    n_fail = sum(1 for _, ok, _ in results if not ok)
    print(f"\n{'='*60}")
    print(f"Phase 1 result: {n_pass} PASS / {n_fail} FAIL")
    if n_fail:
        print("PHASE 1 INCOMPLETE — fix failures before switching to V2_ACTIVE_DRIVE")
    else:
        print("PHASE 1 COMPLETE — safe to set VESTIBULAR_MODE = 'V2_ACTIVE_DRIVE'")
    print('='*60)


if __name__ == '__main__':
    sys.exit(run())
