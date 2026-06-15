# Feeding Chain Integration — Walkthrough

## Goal
Wire the complete feeding/energy chain so that:
1. Energy store state (`fill_fraction`) is observable in `MotionState`
2. Hunger drives motor output via thermoreceptor spatial contrast
3. The organism physically navigates toward heat sources when hungry
4. No god-view (privileged coordinate) lookups remain

## Changes Made

### Component 1: `fill_fraction` in MotionState
**File**: [motor_decision.py](file:///d:/cell-cc/nexus_v1/circuit/motor_decision.py)
- Added `fill_fraction: float = 0.5` field to `MotionState` dataclass

### Component 2: Write `fill_fraction` in variant_adapter
**File**: [variant_adapter.py](file:///d:/cell-cc/nexus_v1/circuit/variant_adapter.py)
- Added `ms.fill_fraction = self.energy_store.fill_fraction` after energy absorption

### Component 3: Hunger approach reflex
**File**: [spinal_reflex.py](file:///d:/cell-cc/nexus_v1/components/spinal_reflex.py)
- Added `_hunger_gate` MOSFET (v_threshold=0.3, gm=1.5) — gates on when `1-fill_fraction > 0.3`
- Added `process_hunger(thermo_activations, fill_fraction, dt)` method
- Same spatial-contrast architecture as noci withdrawal, but **inverted** (approach, not flee) and gated by hunger

### Component 4: Integrate hunger reflex in step()
**File**: [variant_adapter.py](file:///d:/cell-cc/nexus_v1/circuit/variant_adapter.py)
- After noci withdrawal reflex injection, added hunger approach reflex injection
- Uses `thermo_activation` (DC channel) for spatial contrast
- Drives motor neurons toward warmer side when hungry

### Component 5: Replace god-view `feed_alignment`
**File**: [variant_adapter.py](file:///d:/cell-cc/nexus_v1/circuit/variant_adapter.py)
- **Removed**: `get_nearest_heat_source()` coordinate lookup (privileged/god-view)
- **Replaced with**: `max(thermo_vals) - min(thermo_vals)` — skin thermoreceptor spatial contrast
- This is a **local physical measurement** the organism can actually perform

### Component 6 (Bug Fix): Thermoreceptor time constant
**File**: [chain.py](file:///d:/cell-cc/nexus_v1/somatosensory/chain.py)
- **Root cause**: τ = R×C = 20×5 = 100 time-units. With dt=0.001, reaching steady state took 500,000 steps — thermoreceptors never activated in typical simulations
- **Fix**: Reduced to C=1.0, R=5.0 → τ=5.0 (5000 steps to 63%, reasonable for dt=0.001)
- **Also fixed**: Default MOSFET v_threshold=0.3 was too high for skin temperatures (0.1-0.3). Added explicit `ChannelConfig(name="default", v_threshold=0.01)` for TRPV/TRPM channel sensitivity
- Comment in original code claimed "v_threshold=0.01" but no channels were set → fell through to default 0.3

## Verification Results

### Unit test: SpinalReflexArc
- `fill=0.3` (hungry) → `move_x=0.072` (approaches warm front) ✓
- `fill=0.95` (satiated) → `move_x=0.0` (no approach drive) ✓

### Integration test: Full circuit (5000 steps)
| Step | thermo_F | thermo_B | contrast | hunger_x | feed_align |
|------|----------|----------|----------|----------|------------|
| 0 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 |
| 1000 | 0.056 | 0.034 | 0.022 | 0.002 | 0.017 |
| 2000 | 0.392 | 0.255 | 0.137 | 0.013 | 0.123 |
| 3000 | 0.825 | 0.569 | 0.256 | **0.024** | 0.303 |
| 5000 | 1.184 | 1.007 | 0.177 | **0.017** | 0.516 |

- Thermoreceptors now produce differential activation (front > back)
- Spatial contrast peaks and then narrows (back catches up) — physically correct
- Hunger drive follows contrast × hunger gate
- feed_alignment integrates physical contrast without any coordinate lookups

### God-view audit
- `get_nearest_heat_source()` no longer called in the main step loop
- All sensor readings derive from skin patch thermal physics (Newton's cooling law)

## Test file
- [_feeding_verify.py](file:///d:/cell-cc/nexus_v1/_feeding_verify.py) — integration test script (kept for regression)
