# EXP-023 Drain Root Cause: Loop B Repair Cost Runaway

## 🔑 Definitive Diagnosis

**The metabolic wall is caused by Loop B (tissue repair cost), NOT by max_deposit_per_step.**

### Evidence

| Metric | Value | Implication |
|--------|-------|-------------|
| deposit utilization | **45%** | max_deposit=0.12 is NOT the bottleneck |
| avg deposit/step | 0.054 | Source proximity, not cap, limits intake |
| avg withdraw/step (normal) | **0.010** | All subsystems combined: 0.010/step |
| **repair_cost (crisis)** | **0.095/step** | 💀 **Single drain = 9.5x all others combined** |

### Drain Breakdown (instrumented)

| Source | Code Location | Normal | Crisis | Notes |
|--------|--------------|--------|--------|-------|
| **Repair cost** | `variant_adapter.py:739` | 0.001 | **0.095** | `total_damage × 0.005` |
| Vascular delivery | `variant_adapter.py:1311` | 0.004 | 0.004 | Stable |
| Vital oscillator | `vital_oscillator.py:195` | 0.003 | 0.003 | Stable |
| DA neuron refill | `variant_adapter.py:1088` | 0.003 | 0.003 | Stable |
| STDP energy | `hebbian.py:767` | 0.000 | 0.000 | Stable |

> [!CAUTION]
> Repair cost alone during burn events (**0.095/step**) exceeds total deposit capacity (**0.054 avg, 0.12 max**). This makes recovery impossible during sustained burns.

### Physics Contradiction

```
Safe feeding zone:  d ∈ (12.6, 30.0)  →  no burn, P_in ≈ 0.05-0.12
Burn zone:          d < 12.6          →  P_repair ≈ 0.095 > P_in
Dead zone:          d > 30.0          →  P_in ≈ 0 (outside thermal radius)
```

The organism **must** stay in the narrow safe feeding band (12.6-30.0 units) but has no behavioral mechanism to precisely maintain this distance during early learning. Any excursion into the burn zone triggers a repair cost that exceeds its feeding capacity.

### Run3 Timeline Confirming Pattern

| Step | fill | dist | P_out | Event |
|------|------|------|-------|-------|
| 50k | 0.655 | 16.5 | 0.007 | Safe zone ✅ |
| **60k** | **0.000** | 13.8 | **0.105** | Burn zone → repair spike 💀 |
| 120k | 0.996 | 28.0 | 0.015 | Safe zone ✅ |
| **130k** | 0.244 | 43.3 | **0.103** | Post-burn overshoot |
| **170k** | **0.000** | 40.4 | **0.072** | Dead zone starvation |
| **270k** | 0.079 | 20.3 | **0.112** | Burn zone → repair spike 💀 |

## Proposed Fix Options

### Option 1: Cap repair_cost per step ⭐ (Minimal, targeted)
```python
# variant_adapter.py L737-739
repair_cost = _total_damage * self.repair_energy_rate * dt
repair_cost = min(repair_cost, 0.02)  # NEW: cap at max_deposit/6
self.energy_store.withdraw(repair_cost)
```
- **Pro**: Directly addresses the runaway, preserves physics
- **Con**: Artificial cap, less physical

### Option 2: Reduce repair_energy_rate (0.005 → 0.001)
- **Pro**: Simple, proportional
- **Con**: May weaken the damage-avoidance learning signal

### Option 3: Raise damage_threshold (3.0 → 4.0)
- Widens safe feeding zone from d>12.6 to d>6.0
- **Pro**: More physical, organisms can feed closer without burning
- **Con**: Changes nociceptor behavior

### Option 4: Logarithmic repair cost
```python
repair_cost = math.log1p(_total_damage) * self.repair_energy_rate * dt
```
- **Pro**: Sublinear growth prevents runaway while keeping signal
- **Con**: Less physical than linear

> [!IMPORTANT]
> **Recommendation**: Option 1 (cap) + Option 2 (reduce rate) combined.
> Cap prevents catastrophic drain spikes while reduced rate keeps the signal meaningful.
> `repair_energy_rate = 0.002`, `cap = 0.03/step`.
