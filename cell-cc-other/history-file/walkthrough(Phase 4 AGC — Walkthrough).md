# Phase 4 AGC — Walkthrough

## Goal

Implement Automatic Gain Control (AGC) to couple behavior intensity with physiological deficit state. When energy and/or DA are chronically low, AGC amplifies the hunger-driven thermotaxis reflex to break the static energy deadlock identified in EXP-020 C4.

## Changes Made

### New Files

#### [agc.py](file:///D:/cell-cc/nexus_v1/components/agc.py)
`AutomaticGainControl` class — RC leaky integrator with Zener clamp.
- **Drive**: `S_drive = α × max(0, 0.5 - fill) + β × max(0, 0.2 - DA)`
- **Integration**: `Capacitor` with τ=40k steps (C=1.0, R=40k)
- **Clamp**: `Capacitor.discharge_to(g_max=4.0)` — instantaneous Zener
- **Output**: `gain = 1.0 + G_clamped` ∈ [1.0, 5.0]

#### [diag_agc_validation.py](file:///D:/cell-cc/nexus_v1/tests/diag_agc_validation.py)
5-criterion validation: gain amplification (C1), deficit response (C2), saturation (C3), stability (C4), unit step (C5).

---

### Modified Files

#### [variant_adapter.py](file:///D:/cell-cc/nexus_v1/circuit/variant_adapter.py)
- **Import**: `AutomaticGainControl` (L47)
- **Init**: `self.agc = AutomaticGainControl()` (L309-315)
- **Step**: `self.agc.step(fill, da, dt)` after fill_fraction computed (L810-817)
- **Hunger reflex**: `gain_multiplier=self.agc.gain` passed to `process_hunger()` (L768-771)
- **Diagnostics**: `"agc": self.agc.summary()` in `get_variant_state()` (L1528-1529)

#### [spinal_reflex.py](file:///D:/cell-cc/nexus_v1/components/spinal_reflex.py)
- `process_hunger()` gains `gain_multiplier: float = 1.0` parameter
- Return values scaled by `gain_multiplier` (L289-290)
- Nociceptive withdrawal (`process()`) unchanged — L2 hardwired

#### [motor_decision.py](file:///D:/cell-cc/nexus_v1/circuit/motor_decision.py)
- `MotionState.agc_gain: float = 1.0` field added for diagnostics (L107-112)

---

## Bugs Found & Fixed

### Bug 1: MOSFET Bang-Bang Oscillation
**Symptom**: C4 stability FAIL — 67.7% sign reversals in gain signal.
**Root cause**: MOSFET feedback clamp with gm=10.0 over-corrects. At V=4.1: `inject(-10×0.1×1.0)` drops voltage to 3.1, then S_drive pushes back above 4.0 → bang-bang cycle.
**Fix**: Replaced `MOSFET.conduct() → inject(-i_clamp)` with `Capacitor.discharge_to(g_max)` — instantaneous Zener clamp, still S0-compliant.

### Bug 2: Col→Motor AGC Breaks Selectivity
**Symptom**: T2.2/T2.3 regression — thermal encoding selectivity ratio dropped from 655× to 1.35×.
**Root cause**: AGC amplifying ALL col→motor bundles uniformly (5× gain) → body moves aggressively → hits heat sources → thermal encoding rises to 0.35 (was 0.00).
**Fix**: Removed AGC from `_propagate_bundles()`. AGC acts only on hunger reflex — the targeted mechanism for energy deadlock.

---

## Design Decision: AGC Scope

The original plan had AGC on both hunger reflex AND col→motor bundles. Testing showed col→motor is too broad:
- Col→Motor bundles carry ALL motor signals (vestibular, thermal, sprouted)
- 5× uniform amplification disrupts the carefully-tuned selectivity ratios
- Hunger reflex is the **targeted** mechanism for the energy deadlock problem

Final architecture: AGC → hunger reflex only. Col→Motor remains DA-gain-only.

---

## Test Results

| Suite | Result |
|-------|--------|
| Regression (21 tests) | **21/21 PASS** |
| AGC Validation (5 criteria) | **5/5 PASS** |

### AGC Validation Details
| Criterion | Result | Value |
|-----------|--------|-------|
| C1 Hunger gain amplification | PASS | avg 5.0× when fill < 0.4 |
| C2 Deficit response | PASS | gain reaches 5.0 at low fill |
| C3 Saturation protection | PASS | max gain = 5.000 (≤ 5.0) |
| C4 Stability | PASS | 0.000 sign reversals |
| C5 Unit step response | PASS | monotonic, final = 5.0 |
