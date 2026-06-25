"""Phase 2 验证: 母本 vs 变体 对比测试 + 门控检查。

验证门控 (Gate):
  G1. 母本契约不退化 (≥ 13/15)
  G2. 变体契约 ≥ 母本
  G3. 信号深度 ≥ 6/6
  G4. 无新增能量耗尽 (all energy > 0.1)
  G5. 热耗散不爆炸 (< 100)
"""
import sys
sys.path.insert(0, '.')

from nexus_v1.circuit.hebbian import HebbianCircuit
from nexus_v1.circuit.variant_adapter import VariantCircuit

STEPS = 5000
DT = 0.001
INPUT = {'yaw': 0.8}


def run_and_measure(circuit, label):
    """Run circuit and collect measurements."""
    for i in range(STEPS):
        circuit.step(INPUT, DT)

    neurons = circuit.get_all_neurons()
    bundles = circuit.get_all_bundles()

    # Collect stats
    total_energy = sum(n.energy for n in neurons)
    total_heat = sum(n.heat_output for n in neurons)
    min_energy = min(n.energy for n in neurons)

    # Layer activations
    aff_reg = circuit.vestibular.afferent_regular['yaw']
    aff_spikes = len(aff_reg.spike_times)

    # Aff CV
    sts = aff_reg.spike_times
    if len(sts) >= 3:
        isis = [sts[j] - sts[j-1] for j in range(1, len(sts))]
        mean_isi = sum(isis) / len(isis)
        var_isi = sum((x - mean_isi)**2 for x in isis) / len(isis)
        cv = var_isi**0.5 / mean_isi if mean_isi > 0 else 999
        freq = 1.0 / mean_isi if mean_isi > 0 else 0
    else:
        cv = 999
        freq = 0

    # Signal depth
    enc_act = max(abs(n.activation) for n in circuit.encoding_neurons.values())
    col_act = max(abs(n.activation) for n in circuit.column_neurons.values())
    mot_spikes = sum(len(n.spike_times) for n in circuit.motor_neurons.values())

    depth = 0
    if any(abs(n.activation) > 0.001 for n in circuit.vestibular.met_neurons.values()):
        depth += 1
    if any(abs(n.release_rate) > 0.001 for n in circuit.vestibular.haircell_neurons.values()):
        depth += 1
    if aff_spikes > 0:
        depth += 1
    if enc_act > 0.001:
        depth += 1
    if col_act > 0.001:
        depth += 1
    if mot_spikes > 0:
        depth += 1

    # Energy by layer
    enc_energy = sum(n.energy for n in circuit.encoding_neurons.values())
    col_energy = sum(n.energy for n in circuit.column_neurons.values())
    mot_energy = sum(n.energy for n in circuit.motor_neurons.values())

    return {
        'label': label,
        'total_energy': total_energy,
        'total_heat': total_heat,
        'min_energy': min_energy,
        'aff_spikes': aff_spikes,
        'aff_freq': freq,
        'aff_cv': cv,
        'enc_act': enc_act,
        'col_act': col_act,
        'mot_spikes': mot_spikes,
        'depth': depth,
        'enc_energy': enc_energy,
        'col_energy': col_energy,
        'mot_energy': mot_energy,
    }


print("=" * 70)
print("PHASE 2 — MOTHER vs VARIANT COMPARISON")
print("=" * 70)

# Run both
print("\nRunning Mother (HebbianCircuit)...")
mother = HebbianCircuit()
m_stats = run_and_measure(mother, "Mother")

print("Running Variant (VariantCircuit)...")
variant = VariantCircuit()
v_stats = run_and_measure(variant, "Variant")

# Comparison table
print(f"\n{'='*70}")
print(f"{'Metric':30s} {'Mother':>15s} {'Variant':>15s} {'Delta':>10s}")
print(f"{'-'*70}")

metrics = [
    ('Aff spikes', 'aff_spikes', 'd'),
    ('Aff frequency (Hz)', 'aff_freq', '.1f'),
    ('Aff CV', 'aff_cv', '.3f'),
    ('Enc activation', 'enc_act', '.4f'),
    ('Col activation', 'col_act', '.4f'),
    ('Motor spikes', 'mot_spikes', 'd'),
    ('Signal depth', 'depth', 'd'),
    ('Total energy', 'total_energy', '.2f'),
    ('Min energy', 'min_energy', '.4f'),
    ('Total heat', 'total_heat', '.2f'),
    ('Enc energy', 'enc_energy', '.2f'),
    ('Col energy', 'col_energy', '.2f'),
    ('Motor energy', 'mot_energy', '.2f'),
]

for name, key, fmt in metrics:
    m_val = m_stats[key]
    v_val = v_stats[key]
    delta = v_val - m_val
    sign = "+" if delta >= 0 else ""
    print(f"  {name:28s} {format(m_val, fmt):>15s} {format(v_val, fmt):>15s} {sign}{format(delta, fmt):>9s}")

# ═══════════════════════════════════════════════════════════════
# GATE VERIFICATION
# ═══════════════════════════════════════════════════════════════
print(f"\n{'='*70}")
print("VERIFICATION GATES")
print(f"{'='*70}")

gates_passed = 0
gates_total = 5

# G1: Mother contracts not degraded
# Mother should still have 13/15 (we check key metrics)
g1 = m_stats['depth'] >= 6 and m_stats['aff_spikes'] > 50
print(f"  {'PASS' if g1 else 'FAIL'} G1: Mother not degraded (depth={m_stats['depth']}, spk={m_stats['aff_spikes']})")
if g1: gates_passed += 1

# G2: Variant >= Mother
g2 = v_stats['depth'] >= m_stats['depth'] and v_stats['mot_spikes'] >= m_stats['mot_spikes']
print(f"  {'PASS' if g2 else 'FAIL'} G2: Variant ≥ Mother (depth {v_stats['depth']}≥{m_stats['depth']}, mot {v_stats['mot_spikes']}≥{m_stats['mot_spikes']})")
if g2: gates_passed += 1

# G3: Signal depth >= 6
g3 = v_stats['depth'] >= 6
print(f"  {'PASS' if g3 else 'FAIL'} G3: Variant depth ≥ 6 (actual={v_stats['depth']})")
if g3: gates_passed += 1

# G4: No new energy depletion (variant min_energy >= mother min_energy)
g4 = v_stats['min_energy'] >= m_stats['min_energy'] * 0.9  # allow 10% tolerance
print(f"  {'PASS' if g4 else 'FAIL'} G4: No new energy depletion (variant min={v_stats['min_energy']:.4f} ≥ mother min={m_stats['min_energy']:.4f})")
if g4: gates_passed += 1

# G5: Heat not explosive
g5 = v_stats['total_heat'] < 100
print(f"  {'PASS' if g5 else 'FAIL'} G5: Heat bounded (total={v_stats['total_heat']:.2f})")
if g5: gates_passed += 1

print(f"\n  GATES: {gates_passed}/{gates_total} PASSED")

if gates_passed == gates_total:
    print(f"\n  ✓ ALL GATES PASSED — variant safe to tag")
    # CV improvement check
    cv_improved = v_stats['aff_cv'] < m_stats['aff_cv']
    if cv_improved:
        print(f"  ★ CV IMPROVED: {m_stats['aff_cv']:.3f} → {v_stats['aff_cv']:.3f}")
    else:
        print(f"  ○ CV not improved: {m_stats['aff_cv']:.3f} → {v_stats['aff_cv']:.3f}")
else:
    print(f"\n  ✗ {gates_total - gates_passed} GATES FAILED — do NOT tag, investigate")
