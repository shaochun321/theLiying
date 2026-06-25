"""Combined analysis: EntropyLedger + Shadow Layer.

Runs 50000 steps with differentiated vestibular input patterns,
then produces a joint thermodynamic + shadow contraction report.

Tests: Can the shadow layer distinguish different motion states
after Xin-driven contraction?
"""
import sys, os
sys.path.insert(0, '.')
os.environ['PYTHONIOENCODING'] = 'utf-8'

from nexus_v1.circuit.variant_adapter import VariantCircuit
from nexus_v1.components.entropy_ledger import EntropyLedger

circuit = VariantCircuit()
ledger = EntropyLedger(window_size=2000)

# ========================================================
# Phase 1: Mixed motion input (25000 steps)
# Alternating between yaw-dominant and pitch-dominant states
# to give shadow layer differentiated Xin patterns
# ========================================================
print("Phase 1: Mixed motion input (25000 steps)...")
for t in range(25000):
    if (t // 500) % 2 == 0:
        # YAW-dominant epoch
        inputs = {
            'yaw': 0.5,       # strong yaw
            'pitch': 0.05,    # weak pitch
            'roll': 0.02,
        }
    else:
        # PITCH-dominant epoch
        inputs = {
            'yaw': 0.05,
            'pitch': 0.5,     # strong pitch
            'roll': 0.02,
        }
    circuit.step(inputs, dt=0.001)
    if t % 10 == 0:  # sample every 10 steps for ledger
        ledger.record(circuit, dt=0.001 * 10)

# ========================================================
# Phase 2: Combined motion (25000 steps)
# YAW+PITCH simultaneously to test cross-axis correlation
# ========================================================
print("Phase 2: Combined yaw+pitch motion (25000 steps)...")
for t in range(25000, 50000):
    if (t // 500) % 3 == 0:
        # SIMULTANEOUS yaw+pitch
        inputs = {'yaw': 0.4, 'pitch': 0.4, 'roll': 0.02}
    elif (t // 500) % 3 == 1:
        # YAW only
        inputs = {'yaw': 0.5, 'pitch': 0.0, 'roll': 0.02}
    else:
        # PITCH only
        inputs = {'yaw': 0.0, 'pitch': 0.5, 'roll': 0.02}
    circuit.step(inputs, dt=0.001)
    if t % 10 == 0:
        ledger.record(circuit, dt=0.001 * 10)

# ========================================================
# Report
# ========================================================
print("\n" + "=" * 70)
print("COMBINED ANALYSIS: Entropy Ledger + Shadow Layer")
print("=" * 70)

# --- Entropy Ledger ---
r = ledger.summary()
print(f"\n--- Entropy Ledger (50000 steps, {r['time']:.1f}s) ---")
print(f"  Total spikes:        {r['total_spikes']}")
print(f"  Total heat:          {r['total_heat_dissipated']:.4f}")
print(f"  Entropy rate dS/dt:  {r.get('entropy_production_rate', 0):.6f}")
print(f"  Energy efficiency:   {r.get('energy_efficiency', 0):.4f} spk/heat")

print(f"\n  {'Layer':<12s}  {'Avg E':>8s}  {'Avg Heat':>10s}  {'Avg Act':>8s}  {'E trend':>8s}")
for layer_name in sorted(r.get('layers', {})):
    L = r['layers'][layer_name]
    print(f"  {layer_name:<12s}  {L['avg_energy']:>8.4f}  {L['avg_heat']:>10.6f}  {L['avg_activity']:>8.4f}  {L['energy_trend']:>+8.4f}")

# Energy balance
ok, msg = ledger.energy_balance_check()
print(f"\n  Energy balance: {'PASS' if ok else 'FAIL'} -- {msg}")

# ISI entropy for afferents
print(f"\n  ISI Entropy (bits):")
for nid in sorted(ledger._spike_history):
    n_spk = len(ledger._spike_history[nid])
    if n_spk > 5:
        h = ledger.compute_isi_entropy(nid)
        print(f"    {nid:<25s}: {h:.3f} bits ({n_spk} spikes)")

# --- Shadow Layer ---
shadow = circuit.get_variant_state()['shadow']
print(f"\n--- Shadow Layer ---")
print(f"  Neurons:  {shadow['n_neurons']}")
print(f"  Bundles:  {shadow['n_bundles']}")

c = shadow['contraction']
print(f"\n  Cross-axis contraction:")
print(f"    Active cross-links:  {c['n_active_cross']}")
print(f"    Silent bundles:      {c['n_silent']}")
if c['active_cross_links']:
    print(f"    Top cross-link weights:")
    for bid, w in sorted(c['active_cross_links'].items(), key=lambda x: -x[1])[:10]:
        marker = " <-- YAW+PITCH!" if ("yaw" in bid and "pitch" in bid) else ""
        print(f"      {bid}: w={w}{marker}")

e = shadow['energy']
print(f"\n  Shadow energy:")
print(f"    Total:  {e['total']:.4f}")
print(f"    Min:    {e['min']:.4f}")
print(f"    Heat:   {e['total_heat']:.6f}")

fe = shadow['free_energy']
print(f"\n  Free energy kernel:")
print(f"    K_ema:  {fe['K_ema']:.6f}")
print(f"    nu:     {fe['nu']:.8f}")
print(f"    Trend:  {fe['trend']}")

ds2 = shadow['ds2_sample']
print(f"\n  Minkowski ds^2 (yaw<->pitch): {ds2['ds2']} ({ds2['causal']})")

# --- Shadow neuron activations per axis ---
print(f"\n  Shadow neuron activations:")
for nid in sorted(circuit.shadow_sandbox.neurons):
    n = circuit.shadow_sandbox.neurons[nid]
    print(f"    {nid:<25s}: act={n.activation:>+8.4f}  E={n.energy:.4f}")

# --- Shadow bundle weights (all) ---
print(f"\n  Shadow bundle weights:")
for bid in sorted(circuit.shadow_sandbox.bundles):
    b = circuit.shadow_sandbox.bundles[bid]
    w = b.mean_weight()
    silent = " [SILENT]" if b.config.is_silent else ""
    print(f"    {bid:<30s}: w={w:.6f}{silent}")

# --- Cross-correlate shadow col activations ---
print(f"\n  Shadow column activation correlations:")
col_acts = {}
# We only have current activation, not history
# Use Xin tension as proxy for correlation
for bid, b in circuit.shadow_sandbox.bundles.items():
    if bid.startswith("s_enc_to_col_"):
        axis = bid.replace("s_enc_to_col_", "")
        col_acts[axis] = abs(circuit.shadow_sandbox.neurons[f"s_col_{axis}"].activation)

if col_acts:
    axes = sorted(col_acts.keys())
    print(f"    {'':>10s}", end="")
    for a in axes:
        print(f"  {a[:5]:>6s}", end="")
    print()
    for a in axes:
        print(f"    {a[:5]:>10s}", end="")
        for b_ax in axes:
            va = col_acts[a]
            vb = col_acts[b_ax]
            sim = min(va, vb) / max(va, vb, 1e-10)
            print(f"  {sim:>6.3f}", end="")
        print()

print(f"\n{'='*70}")
print("[DONE] Combined analysis complete.")
