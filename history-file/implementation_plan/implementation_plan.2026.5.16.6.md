# 3D Spring-Repulsion Particle System + LIF Dynamics

## Goal

Replace the synthetic sin-wave data in `AllenBrainAdapter` with a physically-grounded 3D simulation: particles connected by springs, subject to repulsion forces, with each particle hosting a Leaky Integrate-and-Fire (LIF) neuron driven by mechanical stress.

The new `PhysicsSourceAdapter` implements the **exact same interface** as `AllenBrainAdapter`:
- `generate_cells(window_k) → List[CellRecord]`
- `make_envelope(window_k) → EnvelopeRecord`

## Background

The current pipeline reads data from Allen Brain calcium imaging (real but 2D, single-plane). The 3D physics system provides:
- **True 3D geometry** with spring-repulsion forces
- **Emergent spatiotemporal dynamics** (not hardcoded waveforms)
- **LIF neural dynamics** coupled to mechanical state
- **Energy conservation auditing** via the existing entropy ledger

## Proposed Changes

### Engine: 3D Particle Physics

#### [NEW] [physics_particle_system.py](file:///D:/cell-cc/Morphosphere_v37_0_native_runtime_prototype_flat_complete/morphosphere_v2pp/engines/physics_particle_system.py)

Core simulation engine with zero external dependencies (pure Python + math).

**`Particle3D` dataclass**:
```python
@dataclass
class Particle3D:
    pid: int
    x: float; y: float; z: float       # position
    vx: float; vy: float; vz: float     # velocity
    V_m: float = -65.0                  # membrane potential (mV)
    V_thresh: float = -55.0             # LIF spike threshold
    V_reset: float = -70.0              # post-spike reset
    tau_m: float = 20.0                 # membrane time constant (ms)
    refrac_remaining: float = 0.0       # refractory timer
    spike: bool = False                 # current spike state
    I_ext: float = 0.0                  # external current (from stress)
    neighbors: List[int] = field(...)   # connected particle IDs
    rest_lengths: Dict[int, float] = field(...)  # equilibrium distances
```

**`ParticleSystem3D` class**:
- `__init__(n_particles, box_size, seed)`: Random initial placement with minimum distance enforcement
- `step(dt)`: One physics + LIF timestep:
  1. **Spring forces**: $F_{spring} = -k_s (r - r_0) \hat{r}$ for each connected pair
  2. **Repulsion forces**: $F_{rep} = k_r / r^2$ for overlapping pairs (Lennard-Jones short-range)
  3. **Damping**: $F_{damp} = -\gamma \vec{v}$
  4. **Velocity Verlet integration**: update positions + velocities
  5. **Boundary reflection**: particles bounce off box walls
  6. **LIF update**: $\tau_m \frac{dV}{dt} = -(V - V_{rest}) + R_m \cdot I_{ext}$
     - $I_{ext} = \alpha \cdot |\text{stress}| + \beta \cdot |\text{displacement}|$
     - If $V > V_{thresh}$: spike, reset to $V_{reset}$, enter refractory
  7. **Spike propagation**: spiking particle sends current pulse to neighbors
- `get_state()`: Returns snapshot of all particle positions, velocities, V_m, spikes

**Parameters** (physically motivated defaults):
| Parameter | Value | Meaning |
|-----------|-------|---------|
| n_particles | 50 | Small enough for CPU, large enough for statistics |
| box_size | 10.0 | Bounding box [-5, 5]³ |
| k_spring | 2.0 | Spring stiffness |
| k_repulsion | 0.5 | Short-range repulsion |
| damping | 0.3 | Velocity damping coefficient |
| dt | 0.1 | Physics timestep (ms) |
| tau_m | 20.0 | LIF membrane time constant |
| connect_radius | 3.0 | Particles within this distance are spring-connected |

---

### Adapter: Pipeline Interface

#### [NEW] [physics_source_adapter.py](file:///D:/cell-cc/Morphosphere_v37_0_native_runtime_prototype_flat_complete/morphosphere_v2pp/engines/physics_source_adapter.py)

Wraps `ParticleSystem3D` into the `CellRecord`/`EnvelopeRecord` interface.

**Signal mapping** (particle state → CellRecord):

| CellRecord field | Source | Notes |
|-----------------|--------|-------|
| `x, y, z` | particle position | Real 3D coordinates |
| `V_mean` | time-averaged membrane potential | Normalized to [0, 1] |
| `V_slope` | ΔV_m over window | Membrane potential change rate |
| `spike_rate` | spike count / window duration | LIF firing rate |
| `release_proxy` | signal variance | V_m variance over window |
| `adaptation_state` | mean stress | Mechanical stress proxy |
| `normal_x/y/z` | velocity direction | Movement vector |
| `boundary_distance` | distance to box wall | Boundary proximity |
| `support_radius` | connect_radius / 2 | Interaction radius |
| `neighbor_ids` | spring-connected neighbors | From physics topology |

**Window strategy**: Each logical window = N physics timesteps (default: 100 steps = 10ms of simulation).

---

### Runner Modification

#### [MODIFY] [run_v40_integrated.py](file:///D:/cell-cc/Morphosphere_v37_0_native_runtime_prototype_flat_complete/morphosphere_v2pp/runners/run_v40_integrated.py)

Add `--source` CLI argument:
```python
# At top of main():
source = os.environ.get("DATA_SOURCE", "allen")  # "allen" or "physics"
if source == "physics":
    from physics_source_adapter import PhysicsSourceAdapter
    adapter = PhysicsSourceAdapter(n_particles=50, seed=42)
else:
    adapter = AllenBrainAdapter(split_role="all")
```

No other changes needed — the adapter interface is identical.

---

## Open Questions

> [!IMPORTANT]
> **Particle count**: 50 particles is a balance between computational cost and statistical significance. The Allen Brain adapter has 214 cells. Should the physics system match this (214 particles) or use fewer for faster iteration?

> [!IMPORTANT]  
> **Stimulus injection**: Allen Brain data has natural stimulus epochs (movies, scenes, gratings). The physics system needs equivalent perturbation modes to test discrimination. Proposed: 3 distinct perturbation regimes:
> 1. **"movie"**: Continuous sinusoidal external force (smooth, correlated)
> 2. **"scenes"**: Random force impulses (episodic, variable)
> 3. **"gratings"**: Periodic boundary compression (structured, repetitive)

## Verification Plan

### Automated Tests
1. Run `python engines/physics_particle_system.py` — self-test validates:
   - Energy conservation (total E stable within 10%)
   - LIF spike rate reasonable (1-20 Hz)
   - No particle escapes bounding box
   - Spring topology connected (no isolated particles)

2. Run `python runners/run_v40_integrated.py` with `DATA_SOURCE=physics`:
   - Signal entropy ledger populated with 7 channels
   - Circuit builds and discriminates ✅
   - CPG + ghost resurrection still works
   - Temperature doesn't freeze

### Manual Verification
- Compare discrimination metrics (avg cosine) between Allen Brain and Physics sources
