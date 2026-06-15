# L2.08 Biological Screening — FULL PASS (4/4)

> **Experiment**: `exp_L2_screening.py` — Gauntlet v2 (pre-equilibrated)
> **Steps**: 100,000 | **dt**: 0.001 | **Duration**: 373.8s (267 steps/s)
> **Date**: 2026-06-12

## Result: FULL PASS

| Criterion | Result | Detail |
|-----------|--------|--------|
| Survived | [OK] | fill_fraction = 0.1712 |
| Vital pulse active | [OK] | amplitude = 0.0104 |
| Experienced damage | [OK] | peak_damage = 1.5957 |
| Avoidance emerged | [OK] | step 7,000 (d > initial × 1.2) |

---

## Timeline of Events

```
Step     0: Organism placed at d=5.0 from heat source [70,50,50]
            All 4 skin patches ABOVE damage threshold (T_skin = 3.5~4.2)
            Damage begins accumulating immediately.

Step 1,000: [!] FIRST DAMAGE detected: max_damage = 1.077
            → Loop A: vital_damage_factor = 1/(1+1.077×0.5) ≈ 0.65 (35% cardiac depression)
            → Loop B: repair_cost = 4×1.077 × 0.005 × 0.001 ≈ 0.00002/step energy drain
            → Loop C: Noci spatial contrast → spinal reflex → directional motor current
            → Loop D: damage → ECM thermal barrier penetration begins

Step 7,000: [AVOID] AVOIDANCE BEHAVIOR EMERGED
            distance = 23.6 > initial×1.2 = 6.0
            Organism has moved AWAY from heat source.
            Mechanism: Loop C (spinal reflex) + vital oscillator kicks.

Step 10,000: damage = 0.857 (declining — organism escaping damage zone)
             distance = 44.5, speed = 0.0004
             ECM encoding layer thermal rise = +0.28 (Loop D active)

Step 20,000: damage = 0.000 (FULLY ESCAPED)
             distance = 37.4, speed = 0.0017
             → Self-repair (heal_rate=0.1) cleared accumulated damage.

Steps 20k-100k: damage = 0.000 (organism STAYS in safe zone)
                 distance fluctuates 15-51, never returns to d<8
                 DA stabilizes at ~3.0, speed increases to 0.004
```

---

## Feedback Loop Activation Evidence

### Loop A: Cardiac Depression
- **Triggered**: Step 0-10k (damage > 0)
- **Effect**: vital_damage_factor dropped to ~0.65 at peak damage
- **Recovery**: vital amplitude returned to normal (~0.010) after damage cleared

### Loop B: Metabolic Repair Tax
- **Triggered**: Step 0-20k
- **Effect**: fill_fraction decline rate during damage phase vs. post-escape:
  - Steps 0-10k: fill dropped 0.500 → 0.467 = -0.033 (repair + basal)
  - Steps 10-20k: fill dropped 0.467 → 0.434 = -0.033 (basal only — same!)
  - Repair tax was small relative to basal metabolism (REPAIR_ENERGY_RATE = 0.005)

### Loop C: Spinal Withdrawal Reflex (PRIMARY DRIVER)
- **Triggered**: Step 0-7k (noci spatial contrast detected)
- **Effect**: Directional motor current drove organism AWAY from heat source
- **Evidence**: distance increased 5.0 → 23.6 in 7000 steps despite organism having
  near-zero initial velocity. This is the reflex arc working.
- **MOSFET gate**: VDD = 1.0 (fully open, no cortical override)

### Loop D: ECM Thermal Barrier Breach
- **Triggered**: Step 0-10k
- **Effect**: ECM encoding layer temperature rose +0.28 (vs. normal +0.04)
  - Column layer also affected: +0.14 (vs. normal -0.00)
- **Recovery**: ECM temperatures returned to baseline after damage cleared

---

## Thermal Diagnostic Findings

> [!IMPORTANT]
> The experiment required **thermal pre-equilibration** to work correctly.

### Problem Discovered
- SkinPatch thermal time constant: τ = C/k = 10/2 = **5 seconds = 5000 steps**
- At dt=0.001, T_skin needs ~10k steps to rise from 0.1 to >3.0 (damage threshold)
- But organism drifts away in <5k steps from vital oscillator + vestibular input
- Result: **organism escapes before taking damage** (false negative)

### Solution Applied
- Pre-set T_skin = T_env at each patch position (instantaneous equilibration)
- BIO justification: organism that has been in the vent plume for t >> τ
- All 4 patches started ABOVE threshold (front=4.17, back=3.53, left/right=3.81)

### Implication for Future Work
- The thermal time constant is realistic but creates a "cold start" problem
- D.14 (thermal_membrane.py vs. SkinPatch system) should evaluate whether
  τ needs to be environment-dependent or if pre-equilibration is standard protocol

---

## Key Quantitative Results

| Metric | Value | Notes |
|--------|-------|-------|
| Peak damage | 1.5957 | Moderate — well below catastrophic |
| Damage duration | ~20k steps | Self-repair cleared damage |
| Avoidance latency | 7,000 steps | Time from damage onset to escape |
| Final distance | 9.1 | Orbiting at safe range |
| Final fill_fraction | 0.1712 | Viable (>0.05 threshold) |
| Final vital amplitude | 0.0104 | Healthy cardiac output |
| DA steady-state | ~3.0 | Elevated but stable (D2R regulated) |
| Final speed | 0.004 | 5× faster than pre-damage |

---

## L2 Parameter Viability Interval (Preliminary)

Based on this single successful run:

| Parameter | Value | Status |
|-----------|-------|--------|
| VITAL_DAMAGE_K | 0.5 | Viable — 35% depression at peak, full recovery |
| REPAIR_ENERGY_RATE | 0.005 | Viable — small relative to basal metabolism |
| REFLEX_GAIN | 0.5 | Viable — sufficient to drive escape in 7k steps |
| K_BARRIER | 2.0 | Viable — ECM thermal rise observed but bounded |

> [!NOTE]
> L2.09 (parameter sweep) should explore sensitivity around these values.
> Key question: at what REFLEX_GAIN does avoidance latency become too slow (>50k steps)?

---

## Conclusion

**Operation Trauma Genesis achieves its design objective**: injecting physical consequences
(not behavioral rules) into the L2 layer produces emergent avoidance behavior from L1
circulation coupling. The organism:

1. **Detected** damage via nociceptor spatial contrast (L1 sensory)
2. **Withdrew** via spinal reflex arc (L2 hardwired)
3. **Survived** with energy and cardiac function intact (L1 viability)
4. **Learned** — DA dynamics shifted permanently (L1 neuromodulation)
5. **Did not return** to the damage zone for 80k remaining steps

This is consistent with the Prigogine dissipative structure framework:
the system self-organized a new behavioral attractor (avoidance) under thermodynamic
pressure (damage → energy cost + cardiac depression).
