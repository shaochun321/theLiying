# Vestibular Chain Dimensional Contract

**Version**: 1.0  
**Date**: 2026-06-30  
**Authority**: 运动势时空测度语言 v1.1 §3.2 — gain classification law  
**Scan data**: EXP-vest-scan-2026-06-30 (exp_vest_calibration_scan.py, 6 axes × 20 amps)

---

## Gain Classification Law

Cross-modal gains carry physical units (transduction across physical domains).  
Same-modal gains are dimensionless (amplification within one domain).

```
Domain chain:
  ω [rad/s] → I [A] → V [V] → f [Hz] → V [V] → F [N]
              ↑            ↑         ↑         ↑
          g_MET        G_HC_Aff  G_Aff_Enc  η_motor
        CROSS-MODAL   CROSS-MODAL CROSS-MODAL CROSS-MODAL
```

---

## Cross-Modal Gains

| Symbol | Code location | Value | Unit | Calibration status | Physical source |
|--------|--------------|-------|------|--------------------|----------------|
| g_MET | `vestibular/chain.py` ChannelConfig gm | 2.0 | A·s/rad | **ANCHORED** | EXP-vest-scan: slope 3.1–8.5 Hz/unit; anchor = 1 unit ≈ 5.5 deg/s canal (Lasker 2008, C57BL/6, 2 Hz) |
| G_HC_Aff | `vestibular/chain.py` bundles_hc_to_aff synapse_gain | 20.0 | 1/(V·s) | **NOT CALIBRATED** | DEG-017: engineering backfit |
| G_Aff_Enc | `circuit/hebbian.py` bundles_vest_to_enc synapse_gain | 16.0 | V·s | **ANCHORED (formula)** | V_ss = f×W×g×dt×R; at f=7 Hz V_ss=1.40V >> V_th=0.30V; 33× bio target due to N=1 (DEG-016) |
| η_motor | `circuit/variant_adapter.py` MuscleSystem gain | 0.1 | N/V | **NOT CALIBRATED** | DEG-017; EXP-RouteA: 0.1→0.3 gives 10× body speed |

---

## Same-Modal Gains (dimensionless)

| Symbol | Code location | Value | Domain |
|--------|--------------|-------|--------|
| G_MET | `vestibular/chain.py` bundles_met_to_hc synapse_gain | 5.0 | I → I |
| G_HC | `vestibular/chain.py` bundles_hc_to_aff synapse_gain first stage | — | V → V |
| G_Enc_Col | `circuit/hebbian.py` enc_to_col bundles | varies | V → V |
| G_Col_Motor | `circuit/hebbian.py` col_to_motor synapse_gain | 0.1 (FIX-016) | V → V |

---

## Physical Unit Anchoring (EXP-vest-scan-2026-06-30)

### Canal axes (semicircular canals — angular velocity)

Reference: Lasker et al. 2008, J Neurophysiol 99:1222 (C57BL/6 mouse, 2 Hz sinusoidal)  
Literature sensitivity: 1.0 spikes/s per deg/s (regular afferents)

| Axis | Slope (Hz/unit) | 1 model unit (deg/s) | Chain sens. (Hz/(deg/s)) |
|------|----------------|---------------------|--------------------------|
| yaw | 8.479 | 8.5 | 1.00 |
| pitch | 4.913 | 4.9 | 1.00 |
| roll | 3.084 | 3.1 | 1.00 |
| **mean** | **5.492** | **5.5** | **1.00** |

> NOTE: slope variation (54%) likely due to STDP weight evolution during measurement.
> P0 (freeze-STDP re-scan) will confirm. If slopes converge to <5%, unified anchor 5.5 deg/s applies.

### Otolith axes (utricular/saccular maculae — linear acceleration)

Reference: Goldberg 2000, Physiol Rev 80:1–18 (sensitivity 35 spikes/s per g = 3.57 Hz/(m/s²))

| Axis | Slope (Hz/unit) | 1 model unit (m/s²) | 1 model unit (g) |
|------|----------------|---------------------|-----------------|
| oto_x | 5.780 | 1.62 | 0.165 |
| oto_y | 0.846 | 0.24 | 0.024 |
| oto_z | 3.059 | 0.86 | 0.088 |
| **mean** | **3.228** | **0.90** | **0.092** |

> NOTE: oto_y slope is 6× lower than oto_x. P0 + entropy audit (P3) will determine if this is
> measurement contamination or true signal attenuation in the oto_y pathway.

### Working point physical values (amp = 6.0, Phase 5/6 default)

| Axis | f_reg (Hz) | Physical amplitude |
|------|-----------|-------------------|
| yaw | ~47.5 | 6 × 5.5 = 33 deg/s |
| pitch | ~32.5 | 6 × 4.9 = 29 deg/s |
| roll | ~23.0 | 6 × 3.1 = 19 deg/s |
| oto_x | ~36.5 | 6 × 1.62 = 9.7 m/s² ≈ 1g |
| oto_y | ~7.0 | 6 × 0.24 = 1.4 m/s² |
| oto_z | ~19.5 | 6 × 0.86 = 5.2 m/s² |

---

## Dead Zone Architecture Note

**Observed**: all axes f_reg = 1.0 Hz (spontaneous) for amp < 3.5, regardless of input.  
**Interpretation**: NOT a defect to fix. With N=1 afferent and synapse_gain=33× bio target,
dead zone acts as hardware noise gate preventing Langevin noise from being amplified 33× 
into Enc spurious firing. Required consequence of N=1 high-gain architecture (DEG-016).

---

## Dimensional Chain Closure Verification

```
ω [rad/s] × g_MET [A·s/rad]   = I [A]         ✓
V [V]     × G_HC_Aff [1/(V·s)] = f [1/s]       ✓ (not yet calibrated)
f [1/s]   × G_Aff_Enc [V·s]    = V [V]         ✓ (formula-anchored)
V [V]     × η_motor [N/V]       = F [N]         ✓ (not yet calibrated)
```

Two of four cross-modal gains remain uncalibrated (DEG-017). See P2/P3 in execution plan.

---

## ν Power Formula (corrected 2026-06-30)

From Xin KCL: C_ξ · dξ/dt = −ξ/R_ξ + |O − P|  
Multiply by ξ:  **ν(t) = ξ|O−P| − ξ²/R_ξ**  [W]

- Term 1 (ξ|O−P|): error-injection power  → positive = charging / exploration  
- Term 2 (ξ²/R_ξ): Joule dissipation      → always negative = consolidation pressure  

Path optimization functional: ∫P_spike dt has dimension [J], not [W].  
Follows **minimum-action principle** (not minimum-power principle).

ν probe implementation: deferred to P5 (not yet implemented).
