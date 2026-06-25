# Walkthrough: G-001 v2.0 Complete Engineering Implementation

## Summary

Three rounds of implementation covering **A-level** (architecture), **M-level** (metric math), and critical fixes.

---

## Round 1: A-Level (Architecture)

| ID | Problem | File(s) | Fix | Result |
|----|---------|---------|-----|--------|
| A-VF | Vestibular chain gain=0 | [chain.py](file:///d:/cell-cc/nexus_v1/vestibular/chain.py), [neuron.py](file:///d:/cell-cc/nexus_v1/components/neuron.py), [hebbian.py](file:///d:/cell-cc/nexus_v1/circuit/hebbian.py) | Ca leak 6->20, Ca cap=1.0, release cap=0.5, gain 10->1 / 5->1 | 126 Aff spikes, enc=0.31 |
| A1 | Xin->DA->LR disconnected | [variant_adapter.py](file:///d:/cell-cc/nexus_v1/circuit/variant_adapter.py) L397-459 | Xin tension -> DA release; DA modulates all plasticity_gates | DA=1.0, gain_factor=1.27 |
| A5 | Binding sync gate missing | [variant_adapter.py](file:///d:/cell-cc/nexus_v1/circuit/variant_adapter.py) L461-468 | g_sync = min(1, total_bind / theta_sync) gates Col->Motor learning | Active when binding fires |
| A3 | No inter-layer heat diffusion | [variant_adapter.py](file:///d:/cell-cc/nexus_v1/circuit/variant_adapter.py) L523-539 | kappa*Sum(Tj-Ti) - lambda*Ti, T>=0 clamp | vest=0.27, enc/col diffusing |
| A4 | Body has no impedance | [world.py](file:///d:/cell-cc/nexus_v1/components/world.py), [variant_adapter.py](file:///d:/cell-cc/nexus_v1/circuit/variant_adapter.py) L276-286 | Z=sqrt(k*m), T=2Z/(Z+Z_m) attenuates mechanical inputs | T=1.0 (matched) |

---

## Round 2: Gain Chain Fix

| File | Fix | Result |
|------|-----|--------|
| [ledger.py](file:///d:/cell-cc/governance/ledger.py) L147-186 | Use pre_trace for spiking neurons, release_rate for HairCells | **5/5 gain links non-zero** |

### Before vs After

```diff
- L1->L2: 0.000   L2->L3: 0.000   L3->L4: 0.000   L4->L5: 0.000   L5->L6: 0.000
+ L1->L2: 0.071   L2->L3: 1.646   L3->L4: 1.157   L4->L5: 0.089   L5->L6: 0.018
```

---

## Round 3: M-Level (Metric Math)

| ID | Problem | File(s) | Fix | Result |
|----|---------|---------|-----|--------|
| M1 | |a| used instead of delta_a | [shadow_sandbox.py](file:///d:/cell-cc/nexus_v1/components/shadow_sandbox.py) L556-575 | EMA baseline tracking, delta_a = a - a_bar for all shadow neurons | delta_a=0.021 (yaw), 0.013 (pitch) |
| M2 | No curl/divergence | [circulation.py](file:///d:/cell-cc/nexus_v1/circuit/circulation.py) L244-298 | omega_ij = (dnu_i/da_j - dnu_j/da_i)/2, div = sum(dnu_i/da_i) | div=-0.006, curl awaiting multi-axis |
| M3 | kappa formula wrong | [shadow_sandbox.py](file:///d:/cell-cc/nexus_v1/components/shadow_sandbox.py) L578-618 | kappa = Sum(g_ij*da_i*da_j) / Sum(da_i^2), g_ij=cross-weight | kappa=8.5e-5 (collapsed, correct for early sim) |
| M1-fix | Shadow neurons all zero | [shadow_sandbox.py](file:///d:/cell-cc/nexus_v1/components/shadow_sandbox.py) L22, L64 | ChannelConfig(v_threshold=0.01), bc_current=0.005 | Shadow alive, delta_a non-zero |
| ds2 | Outdated ds2 formula | [shadow_sandbox.py](file:///d:/cell-cc/nexus_v1/components/shadow_sandbox.py) L538-553 | ds2 = g_ij * da_a * da_b (uses delta_a + cross-weights) | Geometric meaning restored |

---

## Files Modified (8 total)

| File | Changes |
|------|---------|
| [chain.py](file:///d:/cell-cc/nexus_v1/vestibular/chain.py) | Ca clearance + release gain |
| [neuron.py](file:///d:/cell-cc/nexus_v1/components/neuron.py) | Ca voltage cap + release saturation |
| [semiconductor.py](file:///d:/cell-cc/nexus_v1/components/semiconductor.py) | MOSFET subthreshold fix (prior session) |
| [hebbian.py](file:///d:/cell-cc/nexus_v1/circuit/hebbian.py) | Synapse gain reduction |
| [variant_adapter.py](file:///d:/cell-cc/nexus_v1/circuit/variant_adapter.py) | A1 Xin->DA, A5 g_sync, A3 heat, A4 impedance |
| [world.py](file:///d:/cell-cc/nexus_v1/components/world.py) | Body stiffness + impedance |
| [shadow_sandbox.py](file:///d:/cell-cc/nexus_v1/components/shadow_sandbox.py) | M1 delta_a, M3 kappa, ds2 upgrade, threshold fix |
| [circulation.py](file:///d:/cell-cc/nexus_v1/circuit/circulation.py) | M2 curl + divergence |
| [ledger.py](file:///d:/cell-cc/governance/ledger.py) | Gain chain spiking/HC measurement fix |

---

## Verification

- **Governance tests**: ALL PASSED (5/5)
- **Gain chain**: 5/5 links non-zero (was 0/5)
- **Motor output**: 3-54 spikes per 10k steps
- **Shadow delta_a**: Non-zero, tracking baseline correctly
- **Circulation divergence**: -0.006 (contracting, physically meaningful)
- **Kappa**: 8.5e-5 (collapsed state, correct for early simulation)

---

## Remaining (S-level, T-level)

| Level | Items | Status |
|-------|-------|--------|
| S1 | Vestibular L1->L2 gain (0.07 = 93% loss) | Observation, may need MET channel tuning |
| S2 | Motor sync (low firing rate ~0.6 Hz) | Needs col->motor gain increase or threshold adjustment |
| S3 | Thermal signal penetration | Thermal path working but weak |
| T1-T5 | Theory-level (Noether, recursion, variational) | Framework present, needs longer simulations |
