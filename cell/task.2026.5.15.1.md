# v39 Shadow Hypergraph Hardening — Task Checklist

## Phase 1: Core Architecture
- [x] Shadow Hypergraph SQL migration (031_v39_shadow_hypergraph.sql)
- [x] ShadowHypergraph class (inter, check_resonance, slow_wave_maintenance)
- [x] HebbianHypergraph unified read-only entry
- [x] Engine B topological hysteresis (d_σ_t leaky integrator)
- [x] Xi lifecycle closure → shadow interment
- [x] FHPMSWriter diagnostic read methods

## Phase 2: Entropy Ledger Physical Grounding
- [x] Replace `abs(avg_V)*0.05` proxy with Shannon entropy from transport edges
- [x] Candidate fragment entropy from hypothesis type diversity
- [x] Origin support entropy from cell spatial variance
- [x] Residual accumulation entropy from Xi mass distribution
- [x] Automatic entropy anomaly detection (z-score > 2.5σ)
- [x] All schema versions updated to v39.0

## Phase 3: Gap Fixes
- [x] **Gap 1**: Real z_t via HebbianSignalTransform at Xi creation → v39_xi_z_t_cache
- [x] **Gap 1**: Xi lifecycle closure retrieves real z_t from cache (no more fabricated vectors)
- [x] **Gap 2**: P-Core death interment (failed P_candidate → shadow layer)
- [x] **Gap 3**: Per-window shadow resonance in Allen runner validation loop
- [x] **Gap 3**: Multiple calibration shadows interred (real windows, not synthetic)
- [x] **Gap 3**: Resonance distribution reporting by regime

## Phase 4: Verification
- [x] Allen Integration: 6/6 PASS
- [x] Final Report: 12/12 PASS, Acc=0.849, Cohen's d=9.08
- [x] Cross-Experiment: 7/7 PASS, 377 cells across VISp/VISl/VISpm
- [x] Shadow resonance: 5 cal shadows, 2/19 strong_echo, 17/19 no_resonance
- [x] Architecture iron law: shadow_influences_pipeline=False
