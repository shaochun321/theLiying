# v40.10 Walkthrough — Practice Layer

## Changes Made

### 1. Physics Audit Corrections

- **Removed LIF parameter injection** from `physics_source_adapter.py`
  - Previously: per-epoch V_thresh/tau_m/V_rest modulation injected false discriminability
  - Now: LIF params set once at init, driven purely by mechanical stress
  - Result: cos improved from 0.333 (injected) to **0.498** (pure physics)

- **Renamed perturbation functions** to physical regime labels:
  - `natural_movie_one` → `uniform_oscillation` (global coherent forcing)
  - `natural_scenes` → `stochastic_impulse` (localized random bursts)
  - `static_gratings` → `structured_compression` (multi-frequency spatial structure)

- **Fixed self-tests**: Both `physics_particle_system.py` and `physics_source_adapter.py` ✅ PASS

---

### 2. New File: `practice_engine.py`

Closed-loop sensorimotor physics engine:

```
PracticeEngine.step(motor_output) → sensory_feedback

  1. Compose perturbation = CPG rhythm + circuit motor + reflexes + babbling
  2. Run 20 physics steps (N=30 particles)
  3. Compute sensory: V_m distribution → 7 entropy channels
  4. Update origin tracker: divergence field → EMA → confidence
  5. Energy accounting: work done, ΔKE
```

Key components:
- **OriginTracker**: Tracks probabilistic origin via motor-induced divergence field
- **Reflex module**: Avoidance (high energy → retreat) + Orienting (spectral change → approach)
- **Babbling**: ε=0.8 → 0.05 exponential decay (Bernstein freeze-then-release)

---

### 3. Circuit Architecture (v40.10)

```
┌─────────────────────────────────────────────────────────────┐
│                    Hebbian Hypergraph Circuit                │
│                                                             │
│  ┌──────────────┐  ┌──────────┐  ┌────────────────────┐    │
│  │ Signal       │  │ Encoding │  │ Column             │    │
│  │ Entropy (7)  │→→│ (7 z_t + │→→│ (7 col neurons)    │    │
│  └──────────────┘  │  2 visc) │  └────────────────────┘    │
│                    └────┬─────┘                             │
│                         ↕                                   │
│  ┌──────────────┐  ┌────┴─────┐  ┌────────────────────┐    │
│  │ CPG          │→→│ Motor    │→→│ Origin             │    │
│  │ (4 neurons)  │  │ (3 DOF)  │  │ (5 neurons)        │    │
│  │ fast_a/b     │  │ x, y, z  │  │ x, y, z, conf, bw  │    │
│  │ slow_a/b     │  └──────────┘  └─────────┬──────────┘    │
│  └──────────────┘                          │               │
│                    ┌───────────────────────-┘               │
│                    ↓ recursive                              │
│              encoding (xin_residual, gamma_desync)          │
└─────────────────────────────────────────────────────────────┘
         ↕                              ↕
    sensory input                  motor output
         ↑                              ↓
┌─────────────────────────────────────────────────────────────┐
│              3D Physics Engine (closed-loop)                 │
│   particle state → V_m → signal entropy                     │
│                    ↑                                        │
│   perturbation = CPG + motor + reflex + babbling            │
└─────────────────────────────────────────────────────────────┘
```

Inter-layer bundles added:
- `encoding_to_motor` (STDP, initially frozen)
- `cpg_to_motor` (STDP)
- `motor_to_encoding` (efference copy)
- `motor_to_origin` (STDP)
- `origin_to_encoding` (recursive feedback)

---

### 4. Integration Results

**Practice mode** (`DATA_SOURCE=practice`):
```
motor      T_layer=0.007  occ=0.289
origin     T_layer=0.007  occ=0.940
convergence: gamma_desync × xin_residual (age=4)
crystallized: cx_gam_xin
```

**Physics mode** (backward compatible):
```
cos=0.474  discrimination: ✅
PRP=2.347  convergence: 15  crystallized: 11
```

---

## Environment Variables

```
DATA_SOURCE="practice"  # closed-loop sensorimotor
DATA_SOURCE="physics"   # open-loop 3D spring simulation
DATA_SOURCE="ctc"       # real cell tracking
DATA_SOURCE="allen"     # Allen Brain Observatory
STRESS_TEST_TICKS=200   # number of circuit ticks
```
