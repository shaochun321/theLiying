# v40.10 Practice Layer — Task List

## Phase A: Motor Layer
- [x] Add motor layer (move_x, move_y, move_z) to circuit builder
- [x] Add inter-layer bundles: encoding→motor, cpg→motor, motor→encoding

## Phase B: PracticeEngine
- [x] Create `practice_engine.py` with closed-loop step()
- [x] N=30 particles, 20 steps/tick
- [x] Motor output → perturbation composition (CPG + motor cortex)
- [x] Sensory feedback → signal entropy channels

## Phase C: Dual-Drive Init
- [x] Reflex module (avoidance + orienting)
- [x] Babbling with decaying ε
- [x] Bernstein freeze-then-release schedule

## Phase D: Motor-Sensory STDP
- [x] Motor-sensory bundle STDP in circuit loop (respects freeze)
- [x] Motor convergence node detection (cx_gam_xin formed)

## Phase E: Origin Layer
- [x] Independent `origin` layer in Hebbian circuit (5 neurons)
- [x] OriginTracker: divergence field computation
- [x] Bandwidth neuron (expandable region)
- [x] Origin → encoding recursive bundle

## Phase F: Energy Accounting
- [x] Work tracking in PracticeEngine
- [ ] `v40_motor_energy_ledger` DB table (deferred — engine tracks internally)

## Integration
- [x] `DATA_SOURCE=practice` mode in runner
- [x] Closed-loop circuit main loop
- [x] Self-test for practice_engine.py ✅
- [x] Full pipeline test (exit 0, all layers active)
- [x] Physics mode backward-compatible (cos=0.474 ✅)
