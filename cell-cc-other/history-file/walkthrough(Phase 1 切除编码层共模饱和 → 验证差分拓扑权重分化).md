# Phase 1 Walkthrough: 切除编码层共模饱和 → 验证差分拓扑权重分化

## Problem Statement

Thermal encoding neurons (`reg_therm_front`, `reg_therm_back`, etc.) were permanently saturated at `activation_ema = 1.0`, regardless of actual thermal gradient direction. This destroyed the differential topology's ability to learn directional associations via STDP — both `w_front` and `w_back` received identical pre-synaptic traces, converging to the same weight.

## Root Cause Chain (3 layers deep)

### Layer 1: Bias-driven common mode (minor)
- `bc_current = 0.02` → `V_ss = 0.02 × 5.0 = 0.10`, close to `v_peak = 0.35`
- Combined with VoltageRegulator, pushed encoding above spike threshold even without input

### Layer 2: Impedance mismatch (major)
- Somatosensory relay `_activation_ema` is **unbounded** — reaches 2.35+ (not clamped to [0,1])
- Original `EXTRA_AXIS_GAIN = 1.0` injected relay output as raw current:
  - `V_ss = 2.35 × 1.0 × 5.0 = 11.75` — **33× above v_peak!**
- Even at `gain = 0.06`: `V_ss = 0.73` — 2× above threshold → permanent saturation

### Layer 3: ISI quantization (fundamental)
- Spiking neurons at `dt=1.0` have only ~3 discrete ISI levels (1, 2, 3+ steps)
- Front/back relay differential is only **12%** (2.35 vs 2.10)
- With any gain that places BOTH neurons above `v_peak`, both fire at ISI=1 → `ema ≈ 1.0`
- The 12% differential is destroyed by the spiking hard limiter

## Changes Made

### 1. Bias current reduction
**File**: [hebbian.py:L82](file:///D:/cell-cc/nexus_v1/circuit/hebbian.py#L82)
```diff
-bc_current=0.02,
+bc_current=0.005,
```
`V_ss(bias) = 0.005 × 5.0 = 0.025 << v_peak = 0.35`

---

### 2. Encoder→Column coupler leak increase
**File**: [hebbian.py:L435](file:///D:/cell-cc/nexus_v1/circuit/hebbian.py#L435)
```diff
-coupler_r_leak=2.0,
+coupler_r_leak=0.5,
```
Faster leakage prevents residual charge from maintaining column activation after encoding goes quiet.

---

### 3. Relay→Encoding injection gain calibration
**File**: [hebbian.py:L623-L640](file:///D:/cell-cc/nexus_v1/circuit/hebbian.py#L623-L640)
```diff
-enc_reg.step(tonic_val * 1.0, dt)
+EXTRA_AXIS_GAIN = 0.04
+enc_reg.step(tonic_val * EXTRA_AXIS_GAIN, dt)
```
At `gain=0.04`, relay≈1.0 (regression test) → `V_ss=0.225` (quiet). Relay≈2.35 (thermal proximity) → `V_ss=0.50` (active but not saturated in graded mode).

---

### 4. Graded thermal encoding config (key fix)
**File**: [hebbian.py:L86-L139](file:///D:/cell-cc/nexus_v1/circuit/hebbian.py#L86-L139) — NEW function `_thermal_encoding_config()`

```python
spiking=False,          # NON-SPIKING: graded analog output
v_threshold=0.10,       # higher threshold: quiet when relay < 1.0
gm=0.5,                 # low gm: keeps activation < 0.5
use_bias_current=False,  # silent without input
```

**Why**: Spiking encoding at `dt=1.0` has only ~3 ISI levels, destroying the 12% relay differential. Non-spiking mode gives continuous `activation = gm × max(0, V_m - v_th)`, preserving the differential through the entire signal chain.

**BIO**: Thermosensory cortex (S1 area 3a) uses graded rate coding for temperature perception, not sparse binary spiking.

---

### 5. Split encoding config: vestibular (spiking) vs thermal (graded)
**File**: [hebbian.py:L328-L339](file:///D:/cell-cc/nexus_v1/circuit/hebbian.py#L328-L339)
```python
extra_set = set(self.extra_axes)
for axis in self.all_axes:
    cfg_fn = _thermal_encoding_config if axis in extra_set else _encoding_config
```

---

### 6. Regression test determinism
**File**: [test_regression.py:L40-L41](file:///D:/cell-cc/nexus_v1/tests/test_regression.py#L40-L41)
```python
import random
random.seed(42)
```
Heat source drift/spawn is random → body trajectory varies per run → relay values at 10k steps non-deterministic. Fixed with seed.

## Validation Results

### Regression Test: 21/21 PASS

| Test | Value | Threshold |
|------|-------|-----------|
| T2.2 enc_quiet | 0.0000 | < 0.5 ✅ |
| T2.3 selectivity | 656.22x | > 1.5x ✅ |
| T3.2 therm < vest | 0.000 < 0.656 | ✅ |

### Stage 3a (20k steps): PASS

| Metric | Value | Threshold |
|--------|-------|-----------|
| w_front | 0.1390 | > 0.10 ✅ |
| w_back | 0.0740 | < 0.10 ✅ |
| Δw | +0.0650 | > 0.01 ✅ |

### Stage 3b (50k steps): PASS

| Metric | Value | Threshold |
|--------|-------|-----------|
| w_front | 0.3606 | grew +261% ✅ |
| w_back | 0.3222 | grew +222% |
| **Δw** | **+0.0384** | **> 0.03 ✅** |
| Δx (body) | +32.25 | organism approached heat ✅ |

### Signal Chain Gradient Amplification (at 50k)

```
Relay:    front=0.778  back=0.698  → 11% differential
Encoding: front=0.106  back=0.081  → 31% differential (2.8× amplification)
Column:   front=0.375  back=0.250  → 50% differential (4.5× amplification)
```

The graded encoding MOSFET transfer curve acts as a **contrast enhancer** — small input differences produce proportionally larger output differences due to the threshold nonlinearity.

## Diagnostic Scripts Created

| Script | Purpose |
|--------|---------|
| [diag_soma_drive.py](file:///D:/cell-cc/nexus_v1/tests/diag_soma_drive.py) | Traces relay→encoding current injection magnitude |
| [diag_thermal_gradient.py](file:///D:/cell-cc/nexus_v1/tests/diag_thermal_gradient.py) | Staged thermal gradient weight divergence validation |
