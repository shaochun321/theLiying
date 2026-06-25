# v40.9 Task Tracker — COMPLETE

## CPG Bio-Substrate Layer
- `[x]` Half-center reciprocal inhibition oscillator (4 neurons, 2 pairs)
- `[x]` Visceral zone in encoding layer (visc_rhythm, visc_baseline)
- `[x]` CPG → encoding inter-layer bundles
- `[x]` CPG diagnostics in runner output
- `[x]` 500 tick validation ✅

## Ghost Resurrection (CPG-driven)
- `[x]` Inter-layer ghost stores source/target neuron IDs
- `[x]` Inter-layer ghost decay (0.995/tick)
- `[x]` CPG-driven ghost resurrection (source calcium > 0.001, age > 100)
- `[x]` Move inter-layer operations out of per-layer loop (bug fix)
- `[x]` Resurrected bundle strength = 0.2 (above 0.1 contraction threshold)
- `[x]` 500 tick validation: 2 ghosts resurrected, PRP > 0, cx_→column restored ✅
