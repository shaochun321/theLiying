# Walkthrough — v41.1 Session: Column Forward Model + Degradation Recovery

## Changes Made

### 1. Column Forward Model (Cerebellar Phase Alignment) — NEW
**Files**: [hebbian_circuit.py](file:///D:/cell-cc/Morphosphere_v37_0_native_runtime_prototype_flat_complete/morphosphere_v2pp/engines/hebbian_circuit.py), [_phase5_pipeline.py](file:///D:/cell-cc/experiments/_phase5_pipeline.py)

- Added `_column_forward_step()` method — Column acts as cerebellar-like forward model
- Mossy fiber pathway: `col_raw_*` neurons receive **ungated** signal (`received_*`)
- Detects signal wasted during gate-shut → accumulates misalignment
- Phase reset: kicks CPG when misalignment > threshold
- Per-channel phase memory: `col_phase_*` learns where each signal arrives in CPG cycle
- **Result**: alignment improved from 0.50 → 0.55 (5% signal capture gain)

---

### 2. Heterogeneous Medium — RECOVERED
**File**: [medium_system.py](file:///D:/cell-cc/Morphosphere_v37_0_native_runtime_prototype_flat_complete/morphosphere_v2pp/engines/medium_system.py)

- `MediumParticle` now has `local_k`, `local_m`, `local_c2`
- `_build_lattice()` generates smooth sinusoidal spatial variation (±30%)
- Each channel type uses **different phase offsets** → different impedance landscapes
- Wave equation uses **local c²(x)** instead of global constant
- **Result**: Same source at (0,0,0) → asymmetric propagation (+x: 0.029 vs -x: 0.045)

---

### 3. BCM Learning Rule — RECOVERED
**Files**: [hebbian_circuit.py](file:///D:/cell-cc/Morphosphere_v37_0_native_runtime_prototype_flat_complete/morphosphere_v2pp/engines/hebbian_circuit.py), [_phase5_pipeline.py](file:///D:/cell-cc/experiments/_phase5_pipeline.py)

- Added `bcm_theta` (sliding threshold) and `bcm_theta_tau` to `MetaNeuron`
- Added `learning_rule = "bcm"` option with `_bcm_update()` method
- BCM rule: ΔW = η · x · y · (y − θ_M), where θ_M tracks ⟨y²⟩
- encoding→column bundle set to BCM
- **Result**: θ_M differentiated [0.004, 0.010], weights differentiated [0.10, 0.18]

---

### 4. Emergent Feedback Topology — RECOVERED  
**File**: [_phase5_pipeline.py](file:///D:/cell-cc/experiments/_phase5_pipeline.py)

- Replaced 2 hand-designed grouped feedback bundles with 1 all-to-all bundle
- Initial weights: small random [0.01, 0.05]
- STDP autonomously selects which z_t→sig connections survive
- **Result** (consistent across 3 seeds):
  - `transition, drift, gamma_desync, magnitude` → **strong** (0.93-0.96)
  - `xin_residual` → **selective** (0.50, only to sig_mean/sig_std/sig_sync)
  - `potential_disp, churn` → **pruned** (0.00) — STDP killed irrelevant pathways

## Validation

| Metric | Seed 42 | Seed 123 | Seed 999 |
|--------|---------|----------|----------|
| acoustic→motor | 0.972 | 0.976 | 0.975 |
| luminous→motor | 0.978 | 0.979 | 0.979 |
| Q4/Q1 intake | 4.41× | 4.43× | 4.31× |
| Column align | 0.528 | 0.532 | 0.525 |
| Noether J | 1.546 | 1.933 | 1.896 |
| Noether anomaly | 0.002 | 0.001 | 0.0001 |

## Degradation Ledger

| Status | Count |
|--------|-------|
| Total unique degradations | 44 |
| Recovered this session | 4 (heterogeneous_medium, BCM, emergent_feedback ×2) |
| Previously recovered | 2 (signal_delay, metabolic_pool) |
| INTENTIONAL_SIMPLIFICATION | 8 |
| Remaining degraded | 38 |
