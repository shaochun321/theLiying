# v40.10 Implementation Plan — Practice Layer (实践层)

## Goal

Close the sensorimotor loop: circuit output → motor force → physics state change → new sensory input.
Introduce trainable new origin (概率原点) as crystallized P in Hebbian hypergraph.

---

## Proposed Changes

### Phase A: Motor Layer in Hebbian Circuit

#### [MODIFY] [run_v40_integrated.py](file:///D:/cell-cc/Morphosphere_v37_0_native_runtime_prototype_flat_complete/morphosphere_v2pp/runners/run_v40_integrated.py)

Add `motor` layer to `build_signal_entropy_circuit()`:

```python
motor_layer = CircuitLayer(layer_id="motor")
# 3 motor neurons: force direction in x, y, z
# Activation range [-1, +1] → direction and magnitude of movement
for mid in ["move_x", "move_y", "move_z"]:
    mn = motor_layer.add_neuron(mid)
    mn.target_rate = 0.0  # default: no movement
    mn.threshold = 0.01
    mn.energy = 1000.0
circuit.layers["motor"] = motor_layer
```

Inter-layer bundles:
- `encoding → motor` (z_t activations drive motor output)
- `cpg → motor` (CPG rhythm modulates motor baseline)
- `motor → encoding` (efference copy: motor output feeds back to sensory)

---

### Phase B: Closed-Loop Physics Engine

#### [NEW] [practice_engine.py](file:///D:/cell-cc/Morphosphere_v37_0_native_runtime_prototype_flat_complete/morphosphere_v2pp/engines/practice_engine.py)

Core class: `PracticeEngine`

```
PracticeEngine:
  __init__(n_particles=30, box_size=10.0)
    → creates ParticleSystem3D
    → initializes origin tracker
    → initializes energy ledger

  step(motor_output: dict) → sensory_input: dict
    1. Compose perturbation from:
       - CPG baseline rhythm (always active)
       - Motor cortex output (move_x, move_y, move_z)
       perturbation = cpg_oscillation + motor_force
    
    2. Run physics (STEPS_PER_TICK = 20 steps, ~2ms)
    
    3. Compute sensory feedback:
       - V_mean distribution → signal entropy channels
       - Per-particle stress → spatial stress field
       - Energy accounting (work done by motor force)
    
    4. Update origin tracker:
       - Compute divergence of motor-induced displacement field
       - Update exponential moving average of divergence maxima
    
    Return: {entropy channels, stress stats, energy balance, origin estimate}
```

Key design: **N=30 particles** for speed. Thermodynamic convergence guarantees
bulk properties match N=214 (fluctuation ~18%, acceptable for learning).

Each tick:
- 20 physics steps × 30 particles = 600 force calculations
- Estimated time: ~5ms per tick → 300 ticks = 1.5 seconds total

---

### Phase C: Dual-Drive Initialization

#### Reflexes (hardwired, in `practice_engine.py`)

```python
def compute_reflex(sensory_input: dict) -> dict:
    """Preset reflexes — always active, overridden by learned motor."""
    motor = {"move_x": 0.0, "move_y": 0.0, "move_z": 0.0}
    
    # Avoidance reflex: if energy_H spikes → push away
    if sensory_input.get("energy_H", 0) > 0.8:
        motor["move_x"] = -0.5  # retreat
    
    # Orienting reflex: if spectral_H changes sharply → move toward
    delta_spectral = sensory_input.get("delta_spectral_H", 0)
    if abs(delta_spectral) > 0.3:
        motor["move_x"] = 0.3 * math.copysign(1, delta_spectral)
    
    return motor
```

#### Babbling (random exploration, in circuit loop)

```python
# Every tick with probability ε (decays over time):
if rng.random() < babbling_epsilon:
    motor_noise = {
        "move_x": rng.gauss(0, 0.2),
        "move_y": rng.gauss(0, 0.2),
        "move_z": rng.gauss(0, 0.2),
    }
    # Add noise to motor output (on top of circuit + reflex)
```

Dual-drive alignment: final motor = `circuit_output + reflex + babbling_noise`

Bernstein freeze-then-release:
- Ticks 0-100: only reflexes + babbling (motor layer weights frozen)
- Ticks 100-200: unfreeze motor weights, enable STDP learning
- Ticks 200+: reduce babbling ε exponentially

---

### Phase D: Motor-Sensory STDP Crystallization

In the circuit main loop, add motor-sensory STDP:

```python
# After motor action and sensory feedback:
for bundle in circuit.inter_layer_bundles:
    if bundle.bundle_id.startswith("motor_to_") or \
       bundle.bundle_id.startswith("encoding_to_motor"):
        # Motor-sensory STDP: strengthen connections where
        # motor output was followed by entropy change
        pre_neurons = [motor_layer.neurons[sid] for sid in bundle.source_neuron_ids]
        post_neurons = [enc.neurons[tid] for tid in bundle.target_neuron_ids]
        bundle.stdp_update(pre_neurons, post_neurons, dt=1.0)
```

When motor-sensory pairs repeatedly co-activate → convergence nodes form →
crystallize into motor P (运动 P 固化).

---

### Phase E: New Origin as Trainable Probability P

#### Origin tracking (in `practice_engine.py`)

```python
class OriginTracker:
    """Track the probabilistic origin from motor-induced divergence."""
    
    def __init__(self):
        self.origin_estimate = [0.0, 0.0, 0.0]  # starts at geometric center
        self.divergence_history = []
        self.alpha = 0.02  # EMA decay rate
        self.confidence = 0.0  # how stable is the estimate
    
    def update(self, particles_before, particles_after, motor_force):
        """Compute divergence of motor-induced displacement field."""
        # Displacement field: Δr_i = r_after_i - r_before_i
        # Divergence: ∇·Δr ≈ Σ (Δr_i · r̂_i) / |r_i - origin|²
        
        div_field = compute_divergence_field(
            particles_before, particles_after, self.origin_estimate)
        
        # Find point of maximum divergence
        max_div_point = argmax(div_field)
        
        # EMA update of origin estimate
        for d in range(3):
            self.origin_estimate[d] += self.alpha * (
                max_div_point[d] - self.origin_estimate[d])
        
        # Confidence: how close is div to 1.0?
        self.confidence = 1.0 - abs(1.0 - max(div_field.values()))
        self.divergence_history.append(self.confidence)
```

#### Origin crystallization (in circuit)

When `origin_tracker.confidence > threshold` for sustained period:

```python
# Create a special neuron in Hebbian hypergraph
if origin_tracker.confidence > 0.7 and sustained_ticks > 50:
    origin_neuron = enc.add_neuron("origin_self")
    origin_neuron.activation = origin_tracker.confidence
    origin_neuron.threshold = 0.5
    # This neuron receives from motor layer AND encoding layer
    # → it crystallizes as the intersection of motor and sensory spaces
    # → entering recursion: origin_self → motor → physics → sensory → origin_self
```

This creates a **self-referential loop** in the Hebbian hypergraph —
a special region where motor causality and sensory evidence converge.

> [!IMPORTANT]
> The origin P, once crystallized, becomes **recursive**: it participates
> in its own re-estimation. Each motor action updates the divergence field,
> which updates the origin estimate, which feeds back into the motor cortex.
> This is the computational structure that the symbol system names "self".

---

### Phase F: Energy Accounting

#### [MODIFY] [pipeline_engine.py](file:///D:/cell-cc/Morphosphere_v37_0_native_runtime_prototype_flat_complete/morphosphere_v2pp/pipeline_engine.py)

Add `write_motor_energy_ledger()`:

```python
def write_motor_energy_ledger(conn, run_id, tick, motor_output, 
                               work_done, delta_entropy, origin_state):
    conn.execute("""
        INSERT INTO v40_motor_energy_ledger
        (run_id, tick, motor_x, motor_y, motor_z,
         work_done, delta_entropy_total, 
         origin_x, origin_y, origin_z, origin_confidence)
        VALUES (?,?,?,?,?,?,?,?,?,?,?)
    """, (run_id, tick,
          motor_output["move_x"], motor_output["move_y"], motor_output["move_z"],
          work_done, delta_entropy,
          origin_state[0], origin_state[1], origin_state[2],
          origin_state[3]))
```

Motor efficiency metric:
```
η = |Δ(signal_entropy)| / work_done
```
High η = small force, big information change (efficient exploration).
Low η = big force, small information change (inefficient).

---

## Verification Plan

### Automated Tests

1. **Unit test**: `practice_engine.py` self-test
   - Motor force → particle displacement → verify V_mean change
   - Reflex response → correct direction
   - Origin tracker convergence after 100 cycles

2. **Integration test**: `DATA_SOURCE=practice` full pipeline
   - Circuit produces motor output
   - Motor output changes physics state
   - Changed physics state feeds back
   - Origin confidence > 0.5 after 200 ticks

3. **Energy conservation**: work_done = ΔKE + ΔPE + dissipation ± 5%

### Manual Verification

- Inspect `v40_motor_energy_ledger` for η trend (should increase)
- Verify origin_estimate converges (not random walk)
- Check motor P crystallization in convergence nodes

---

## File Summary

| File | Action | Description |
|---|:-:|---|
| `practice_engine.py` | NEW | Closed-loop physics + origin tracker + reflexes |
| `run_v40_integrated.py` | MODIFY | Motor layer, closed-loop circuit, `DATA_SOURCE=practice` |
| `pipeline_engine.py` | MODIFY | `v40_motor_energy_ledger` table + write function |
| `physics_particle_system.py` | MINOR | Add `snapshot()` method for before/after comparison |

## Open Questions

> [!IMPORTANT]
> **New origin 的递归入口**：当 origin P 固化后进入递归，是否应该
> 创建一个专门的 `origin` 层（像 cpg 层那样独立），还是作为
> encoding 层中的一个特殊 neuron？前者更干净但增加复杂度，
> 后者更简单但可能被其他 z_t 维度的 STDP 干扰。
