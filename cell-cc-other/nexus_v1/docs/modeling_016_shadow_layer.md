# Shadow Layer (Introspective Layer) -- Modeling Doc 016

## Summary

The shadow layer is a **21-neuron structural copy** of the sensorimotor Enc->Col->Mot subgraph,
built from identical component types (Neuron, SynapticBundle, ECM, VascularCooling) with
parameters tuned for slow-timescale introspection.

**Status: Read-only observer** -- does not feed back to main system.

## Component Table

| Component | Count | Key Config |
|-----------|-------|------------|
| Neuron | 21 | C=3 (3x main), E=5.0, VR=0.01 |
| SynapticBundle (intra-axis) | 12 | enc->col x6, col->mot x6, gain=10 |
| SynapticBundle (cross-axis) | 15 | col<->col, w_init=0.001, gain=10 |
| ECM | 3 | one per layer, slow PNN |
| VascularCooling | 1 | base_flow=0.2 |

## Signal Path

```
Main Xin tension (abs) --[gain=3]--> Shadow Encoding (12 neurons)
    |
    +--[bundle, gain=10]--> Shadow Column (6 neurons)
    |                           |
    |                    [cross-axis bundles, dormant]
    |                           |
    +--[bundle, gain=10]--> Shadow Motor (3 neurons)
```

## Key Design Decisions (from silence diagnosis)

| Parameter | Original | Fixed | Reason |
|-----------|----------|-------|--------|
| C (capacitance) | 10 | **3** | tau=50 too slow; tau=15 allows activation in 15000 steps |
| Xin sign | raw | **abs()** | Negative Xin pushes V below MOSFET threshold (0.3) |
| synapse_gain | 1.0 | **10.0** | Multi-stage MOSFET threshold cascading requires amplification |
| Energy | 0.5 | **5.0** | I^2R heat = 0.045/step with gain=10 drains 0.5 in 11 steps |
| VR base_rate | 0.0005 | **0.01** | Balance I^2R drain rate |
| kappa | 0.01 | **0.001** | Reduce E_remodel cost |

## Verified Results (50000 steps)

### Activations
- enc yaw/pitch: act = 2.1-2.5 (strong)
- col yaw/pitch: act = 1.6 (above MOSFET threshold)
- mot x/y: act = 0.04 (starting)

### Cross-axis Contraction
- yaw<->pitch: w = 0.001116 (+11.6% from 0.001)
- Other cross-axes: +3% (weaker)
- ds^2 yaw<->pitch: 80.3 (down from 100.0, -19.7%)

### Column Correlation Matrix
Two clear clusters emerged:
1. {yaw, pitch} -- r=0.986 (semicircular canal axes)
2. {roll, oto_x, oto_y, oto_z} -- r>0.94 (otolith + roll)
Cross-cluster correlation: ~0.17 (distinguishable)

### Regression
- 5/5 gates PASS (shadow is read-only)
- Energy balance: PASS (1st + 2nd law satisfied)
