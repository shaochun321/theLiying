# Walkthrough: v41.1 — Structural Spacetime Coupling (Final)

## Summary

v41.1 implements the complete transition from artificial signal-circuit coupling to **structural coupling via spacetime circulation alignment**. Six interconnected changes form a closed feedback loop:

```
CPG pulsation → phase gating → signal intermittency →
STDP with temporal structure → circulation → coherence →
learning modulation → weight changes → circulation (loop)
                                         ↓
                              Noether anomaly (measurement)
```

## All Changes

### 1. Luminous Medium Lattice
**Files**: `medium_system.py`, `practice_engine.py`
- Wave mode, stiffness=2.0, damping=0.03, v=2.0 unit/tick

### 2. CPG Half-Center Fix
**File**: `hebbian_circuit.py` `_cpg_step()`
- Symmetry breaking: A=0.08, B=0.02 initial conditions
- Additive tonic drive (not `activate()` overwrite)
- Full suppression: winner zeros loser
- **Result**: period=10 ticks, duty=50%

### 3. CPG Phase Gating
**Files**: `_phase5_pipeline.py`, `run_v40_integrated.py`
- External signals × gate, gate = clamp((A-B)×5 + 0.5, 0, 1)
- IMU partially gated, internal signals ungated

### 4. CPG Layer in Pipeline
**File**: `_phase5_pipeline.py`
- Added missing CPG layer with 4 neurons to `build_full_circuit()`

### 5. Spacetime Circulation Tracking
**File**: `hebbian_circuit.py` `detect_circulations()`
- Phase order, coherence (Kendall-τ), period (autocorrelation)

### 6. Coherence → Learning Modulation
**File**: `hebbian_circuit.py` `learn()`
- Rich P path (≥3 neurons): coherence=0→factor=0.5, coherence=1→factor=1.5
- Trivial P path (<3 neurons): factor=1.0 (neutral)

### 7. Noether Conservation Tracker
**File**: `hebbian_circuit.py` `learn()`
- Tracks μ(G) history, computes dμ/dt, J (EMA), anomaly = |dμ/dt|/J

### 8. Paper Update
**File**: `paper3_medium_physics.tex`
- §5.4 Phase Gating, §5.5 Spacetime Circulation, §5.6 Noether Anomaly
- Table 1 updated with luminous parameters, Table 5 with Noether data

---

## Final Validation (3 seeds, 2000 ticks)

| Metric | Seed 42 | Seed 123 | Seed 999 |
|--------|---------|----------|----------|
| grad_acoustic | 0.968 | 0.973 | 0.973 |
| grad_luminous | 0.974 | 0.978 | 0.979 |
| grad_thermal | 0.421 | 0.143 | 0.293 |
| Intake Q4/Q1 | 4.73× | 4.74× | 4.64× |
| J_conserved | 1.050 | 1.117 | 1.125 |
| Q4 anomaly | 0.0006 | 0.0007 | 0.0006 |
| Symmetry | CONSERVED | CONSERVED | CONSERVED |

### Noether Anomaly Evolution

| Quartile | Anomaly | Phase |
|----------|---------|-------|
| Q1 (learning) | 0.037 | **Symmetry breaking** |
| Q2 (convergence) | 0.0008 | Rapid restoration |
| Q3 (steady state) | 0.0008 | Approximate conservation |
| Q4 (deep) | 0.0006 | **Deep conservation** |

Anomaly drops **50×** from Q1→Q4: learning IS symmetry breaking,
and the steady state IS an approximate conservation law granted
by the physical substrate (CPG oscillation + STDP saturation).
