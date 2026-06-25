# Walkthrough: v41.1 — Structural Spacetime Coupling

## Overview

v41.1 implements the transition from **artificial signal-circuit coupling** to **structural coupling via spacetime circulation alignment**. The key metaphor is biological thalamic gating: external signals must align with the circuit's intrinsic pulsation (CPG oscillation) to enter.

## Changes Made

### 1. Luminous Medium Lattice

**Files**: [medium_system.py](file:///D:/cell-cc/Morphosphere_v37_0_native_runtime_prototype_flat_complete/morphosphere_v2pp/engines/medium_system.py), [practice_engine.py](file:///D:/cell-cc/Morphosphere_v37_0_native_runtime_prototype_flat_complete/morphosphere_v2pp/engines/practice_engine.py)

- Added `luminous` material preset: wave mode, stiffness=2.0, damping=0.03
- Propagation speed v=2.0 unit/tick (3× acoustic), penetration ~67 units
- All three signal channels now propagate through physical medium

**Result**: luminous weight jumped from 0.001 → 0.98, confirming the prior suppression was infrastructure bias, not emergent preference.

---

### 2. CPG Half-Center Fix

**File**: [hebbian_circuit.py](file:///D:/cell-cc/Morphosphere_v37_0_native_runtime_prototype_flat_complete/morphosphere_v2pp/engines/hebbian_circuit.py) `_cpg_step()`

Three bugs were fixed:
1. **Symmetry breaking**: A and B neurons started identical, locking in synchrony. Added asymmetric initial activation (A=0.08, B=0.02)
2. **Tonic drive**: Changed from `activate(0.1)` (which overwrites) to additive `activation += 0.1`
3. **Full suppression**: Winner now completely zeros the loser (`nb.activation = 0.0`)

**Result**: Clean 10-tick period oscillation with 50% duty cycle.

---

### 3. CPG Phase Gating (Thalamic Gating)

**Files**: [_phase5_pipeline.py](file:///D:/cell-cc/experiments/_phase5_pipeline.py) `inject_sensory()`, [run_v40_integrated.py](file:///D:/cell-cc/Morphosphere_v37_0_native_runtime_prototype_flat_complete/morphosphere_v2pp/runners/run_v40_integrated.py)

- External signals (gradient, lever, dlever) are multiplied by `phase_gate`
- `phase_gate = clamp((cpg_fast_a - cpg_fast_b) × 5 + 0.5, 0, 1)`
- IMU signals are partially gated: `imu_gate = 0.5 + 0.5 × phase_gate`
- Internal signals (entropy, origin) bypass the gate

**Biological basis**: Thalamic reticular nucleus (TRN) rhythmically inhibits sensory relay. Only signals arriving during the "open window" reach cortex.

---

### 4. Spacetime Circulation Tracking

**File**: [hebbian_circuit.py](file:///D:/cell-cc/Morphosphere_v37_0_native_runtime_prototype_flat_complete/morphosphere_v2pp/engines/hebbian_circuit.py) `detect_circulations()`

Added three new metrics to the P circulation path:
- `_st_circ_phase_order`: neuron activation ordering within one period
- `_st_circ_coherence`: consistency of phase ordering (Kendall-tau)
- `_st_circ_period`: autocorrelation-estimated period

---

### 5. CPG Layer in Pipeline

**File**: [_phase5_pipeline.py](file:///D:/cell-cc/experiments/_phase5_pipeline.py) `build_full_circuit()`

- CPG layer was missing from pipeline (only existed in runner)
- Added 4 CPG neurons with asymmetric initial activations

## Validation Results

### Three-stage comparison (seeds 42, 123, 999)

| Metric | v41.0 (no medium) | v41.1a (+medium) | v41.1b (+gating) |
|--------|-------------------|-------------------|-------------------|
| grad_acoustic | 0.97 / 0.97 / 0.97 | 0.97 / 0.97 / 0.97 | 0.95 / 0.96 / 0.96 |
| grad_thermal | 0.91 / 0.91 / 0.89 | 0.46 / 0.00 / 0.72 | 0.78 / 0.17 / 0.27 |
| grad_luminous | **0.00 / 0.00 / 0.00** | **0.98 / 0.98 / 0.98** | 0.96 / 0.97 / 0.97 |
| Gate duty | 100% | 100% | **50%** |
| Intake Q4/Q1 | 4.7× | 4.7× | 4.7× |
| ST period | — | — | **10.0 ticks** |

### Key findings

1. **Learning preserved under gating**: STDP learns equally well with 50% signal intermittency
2. **Thermal becomes the weakest**: diffusion mode + gating = highest learning variance
3. **Period detection works**: ST period = 10 ticks matches CPG oscillation
4. **Symmetry breaking confirmed**: channel differentiation is driven by medium physics, not design
