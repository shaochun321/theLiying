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

## Physical Unit Anchoring

**Two scans performed** — use P0 (frozen) data as authoritative source:

| Scan | Date | STDP during measure | Status |
|------|------|---------------------|--------|
| Phase 1 (EXP-vest-scan-2026-06-30) | 2026-06-30 | ACTIVE | ⚠️ Inflated by LTP — SUPERSEDED |
| **P0 (exp_vest_calibration_scan_frozen.py)** | **2026-06-30** | **FROZEN** | **✅ Authoritative** |

### Canal axes — P0 frozen (authoritative)

Reference: Lasker et al. 2008, J Neurophysiol 99:1222 (C57BL/6 mouse, 2 Hz)  
Literature sensitivity: 1.0 spikes/s per deg/s

| Axis | P0 slope (Hz/unit) | 1 unit (deg/s) | w_met_hc after warmup |
|------|-------------------|---------------|----------------------|
| yaw | 1.213 | 1.21 | 0.5195 |
| pitch | 2.252 | 2.25 | 0.5579 |
| roll | 1.930 | 1.93 | 0.4415 |
| **mean** | **1.798** | **1.80** | — |

Canal max deviation: **32.5%** → **NON-ISOMORPHIC** (structural, not measurement artifact)

### Otolith axes — P0 frozen (authoritative)

Reference: Goldberg 2000, Physiol Rev 80:1–18 (3.57 Hz/(m/s²))

| Axis | P0 slope (Hz/unit) | 1 unit (m/s²) | 1 unit (g) | w_met_hc after warmup |
|------|-------------------|-------------|-----------|----------------------|
| oto_x | 1.633 | 0.457 | 0.047 | 0.5559 |
| oto_y | 3.227 | 0.904 | 0.092 | 0.4155 |
| oto_z | 2.549 | 0.714 | 0.073 | 0.3852 |
| **mean** | **2.470** | **0.692** | **0.071** | — |

Otolith max deviation: **33.9%** → **NON-ISOMORPHIC** (structural, weight-driven)

> **Key finding from P0**: oto_y had apparent 0.85 Hz/unit in Phase 1 (looked "dead").
> After freezing STDP, oto_y is actually the STRONGEST otolith axis at 3.23 Hz/unit.
> The Phase 1 oto_y weakness was 100% STDP measurement contamination (LTD during measure).

### Working point physical values (amp=6.0, P0 frozen data)

| Axis | f_reg P0 (Hz) | Physical amplitude |
|------|-------------|-------------------|
| yaw | 9.0 | 6 × 1.21 = 7.3 deg/s |
| pitch | 15.0 | 6 × 2.25 = 13.5 deg/s |
| roll | 14.5 | 6 × 1.93 = 11.6 deg/s |
| oto_x | 11.5 | 6 × 0.46 = 2.7 m/s² (0.28g) |
| oto_y | 23.5 | 6 × 0.90 = 5.4 m/s² (0.55g) |
| oto_z | 19.5 | 6 × 0.71 = 4.3 m/s² (0.44g) |

Phase 1 WP rates (47.5 Hz for yaw) were inflated by STDP LTP during measurement.
True rates (P0): 9–23.5 Hz. More biologically reasonable.

---

## Dead Zone Architecture Note

**Observed**: all axes f_reg = 1.0 Hz (spontaneous) for amp < ~4.0, regardless of input.  
**P0 finding**: dead zone boundary is similar between axes (3.5–4.5 amplitude).  
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
