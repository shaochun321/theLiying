# VitalOscillator Implementation Walkthrough

## Summary

Implemented a **tri-frequency detuned Van der Pol oscillator** (`VitalOscillator`) as the physical origin of basal motility — the organism's "heartbeat". This breaks the cold-start deadlock where the organism has zero motor output → zero sensory change → zero learning.

## Design Decisions

### Tri-Heart Architecture (from Doc 7 ruling)
Three independent `ResonantOscillator` instances with mutually irrational frequencies:
- **X-axis**: 2.00 Hz
- **Y-axis**: 2.11 Hz (ratio to X: 211/200, coprime)
- **Z-axis**: 1.93 Hz (ratio to X: 193/200, coprime)

Since frequency ratios are irrational, phase relationships drift continuously → Lissajous figures in 3D that **never repeat** → ergodic space-filling wandering with **zero `math.random()` calls**.

### Energy Death Switch (from Doc 8 ruling)
Hard cutoff at `fill_fraction < 0.05`:
- Output forced to `[0, 0, 0]`
- No energy withdrawn
- Models biological cardiac arrest

### Additive Motor Injection (combined ruling)
Vital output is injected via `Motor._membrane.inject(vital_out, dt)`. The injected charge is accounted for in `Neuron.step()` dissipation (I²R + basal_cost → heat_output) — no Noether black hole.

## Files Changed

### [NEW] [vital_oscillator.py](file:///d:/cell-cc/nexus_v1/components/vital_oscillator.py)
Core component: `VitalOscillatorConfig` + `VitalOscillator` class.
- Wraps 3 `ResonantOscillator` (VdP cores, μ=2.0)
- Amplitude modulated by `EnergyStore.fill_fraction` (linear ramp 0.05→0.3)
- Energy cost: `0.02 × Σ|output_i| × dt` per step

### [MODIFY] [motor_decision.py](file:///d:/cell-cc/nexus_v1/circuit/motor_decision.py)
Added `MotionState` diagnostic fields:
- `vital_pulse: List[float]` — per-axis drive signal
- `vital_amplitude: float` — total magnitude

### [MODIFY] [variant_adapter.py](file:///d:/cell-cc/nexus_v1/circuit/variant_adapter.py)
Integration in `VariantCircuit`:
- **`__init__`**: `self.vital_oscillator = VitalOscillator()` (after `energy_store`)
- **`step()`**: After `energy_store.tick(dt)`:
  1. `vital_outputs = self.vital_oscillator.step(self.energy_store, dt)`
  2. Inject `vital_outputs[i]` into `motor_neurons['move_x/y/z']._membrane`
  3. Record in `ms.vital_pulse` and `ms.vital_amplitude`

### [NEW] [test_vital_oscillator.py](file:///d:/cell-cc/tests/test_vital_oscillator.py)
Independent unit tests (7/7 passed):

| Test | What it Verifies |
|---|---|
| basic_oscillation | Non-zero output at healthy energy |
| noether_conservation_10k | Energy balance = 0.0 over 10k steps |
| death_switch | Output = 0 when fill < 5% |
| death_switch_transition | Alive → dead transition at fill = 0.05 |
| lissajous_non_collinear | All pair correlations |r| < 0.07 |
| energy_budget_sustainable | Cost < 0.01% of capacity over 100k steps |
| amplitude_modulation | High fill → larger amplitude than low fill |

## Validation Results

### Independent Test
```
7 passed, 0 failed
```

### Integration Regression (1000 steps)
```
vital alive: True
vital outputs: [0.0084, -0.008, -0.007]  (non-collinear ✓)
noether balance: -0.0                      (closed ✓)
body speed: 0.000073                       (from-dead-to-alive ✓)
energy fill: 0.4968                        (sustainable ✓)
```

> [!IMPORTANT]
> The body speed going from 0 to 0.000073 after 1000 steps means the vital oscillator is successfully **breaking the cold-start deadlock**. The organism now has basal motility from pure ODE dynamics — no random noise needed.

## Next Steps for EXP-016
Run full experiment to verify:
1. Lissajous wandering generates spatial `dT/dt` at skin patches
2. Nociceptor fires → DA maintains → learning begins
3. Trajectory shows coherent heat-seeking behavior emerging from initial random wandering
