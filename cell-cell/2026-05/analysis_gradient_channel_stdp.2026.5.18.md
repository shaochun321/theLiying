# Root Cause Analysis: Why Does STDP Differentiate Gradient Channels?

## The Observation

Three independent agents (seed=42/123/999) all learned:
```
grad_acoustic → motor: 0.97  (strengthened)
grad_thermal  → motor: 0.91  (strengthened)
grad_luminous → motor: 0.001 (suppressed)
```

## Physical Root Cause

### Signal Chain Differences

| Property | acoustic | thermal | luminous |
|----------|----------|---------|----------|
| Medium | MediumLattice3D (wave) | MediumLattice3D (diffusion) | **NONE** (analytic) |
| Source amplitude | 5.0 | 3.0 | 4.0 |
| Source frequency | 2.0 Hz | 0.1 Hz | 5.0 Hz |
| Source position | (7.5, 0, 0) | (0, 7.5, 0) | (0, 0, 7.5) |
| Raw gradient avg | 0.01 | 0.0003 | **0.107** |
| Injected activation | ~0.06 | ~0.001 | **~0.30** |

### Why Luminous Gets Suppressed (Not What You'd Expect!)

The intuition "stronger gradient = better learning" is **wrong**. Here's why:

#### STDP Formula
```
LTP = A+ × pre_trace × |post_activation|
LTD = A- × post_trace × |pre_activation|
```

#### Key: post_trace Accumulates to ~95
Motor neurons are continuously activated by CPG babbling → `post_trace` grows
to its steady-state ceiling (~95). This is the same for all gradient channels.

#### The Asymmetry
```
For luminous (strong signal, |pre_activation| ≈ 0.30):
  LTP = 0.01 × pre_trace × |motor_act|    ← small (motor_act ≈ 0.05)
  LTD = 0.012 × 95 × 0.30 = 0.342         ← HUGE!
  Net: strongly negative → weight decreases

For acoustic (weak signal, |pre_activation| ≈ 0.06):
  LTP = 0.01 × pre_trace × |motor_act|    ← small but same as above
  LTD = 0.012 × 95 × 0.06 = 0.068         ← much smaller
  Net: less negative → weight survives → eventually grows
```

#### The Physical Mechanism
```
luminous (no medium):
  → Gradient signal is ALWAYS present (analytic 1/r² field)
  → High activation EVERY tick
  → Each tick: LTD >> LTP (because post_trace is always high)
  → Weight → 0

acoustic/thermal (with medium):
  → Gradient signal is INTERMITTENT (wave/diffusion propagation delay)
  → Low activation most ticks, occasional spikes
  → Spikes happen to correlate with motor babbling (temporal coincidence)
  → On spike ticks: LTP ≈ LTD
  → On quiet ticks: LTD ≈ 0 (pre_activation ≈ 0)
  → Net: slight LTP accumulation → weight grows
```

## Interpretation

### What This IS:
- A genuine physical effect: medium propagation creates temporal sparsity
  in the gradient signal, which is more compatible with STDP timing
- The system learns to prefer **intermittent** signals over **tonic** signals
- This is biologically plausible: neural circuits are known to ignore
  constant stimuli (habituation) and respond to changes (novelty detection)

### What This is NOT:
- ❌ NOT "the system correctly identified which food sources are more useful"
- ❌ NOT evidence that acoustic/thermal sources provide better navigation cues
- The differentiation is an artifact of STDP timing × medium infrastructure

### What This REVEALS:
- The STDP is working correctly: it prefers phasic (intermittent) over
  tonic (constant) pre-synaptic input
- The medium system provides a crucial temporal filter: it transforms
  tonic source fields into phasic signals compatible with STDP
- luminous should probably also have a medium lattice for fair comparison

> [!IMPORTANT]
> The key insight: **medium propagation is not just physical realism —
> it's a prerequisite for STDP-based learning.** Without temporal
> structure in the input signal, STDP's LTD dominates.

## Implications for the Architecture

1. **All gradient channels need medium propagation** for fair STDP training
2. The current result (luminous suppressed) is a calibration artifact,
   not a genuine emergent preference
3. Once luminous also has a medium, we should see **all three channels
   develop non-zero weights**, potentially with different magnitudes
   based on actual navigational utility (source position × particle dynamics)
4. The STDP timing constants (tau_pre=20, tau_post=20) and the LTP/LTD
   ratio (A+=0.01, A-=0.012) are tuned for phasic inputs — this is
   consistent with biological STDP which operates on spikes, not rates
