"""Phase 1 图表: DERC Phase 0 vs Phase 1 对比 + 介质穿透深度"""
import sys, os, math, json
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np

# ═══════════════════════════════════════════════
# Load data
# ═══════════════════════════════════════════════
paper_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "paper")

# Phase 1 data (just generated)
with open(os.path.join(paper_dir, "data_derc_medium.json")) as f:
    d1 = json.load(f)
ns_p1 = sorted([float(k) for k in d1])
EL_p1 = [d1[str(n)]["mean"] for n in ns_p1]
SD_p1 = [d1[str(n)]["std"] for n in ns_p1]

# Phase 0 analytic predictions (L* = (nA√N/σ)^{1/(n+1)})
A, N_part, sigma = 5.0, 30, 0.3
EL_p0 = [(n * A * math.sqrt(N_part) / sigma) ** (1/(n+1)) for n in ns_p1]

# Also load Phase 0 measured if available
try:
    with open(os.path.join(paper_dir, "data_derc_n50.json")) as f:
        d0 = json.load(f)
    EL_p0_meas = [d0[str(n)]["mean"] for n in ns_p1 if str(n) in d0]
    ns_p0_meas = [n for n in ns_p1 if str(n) in d0]
except FileNotFoundError:
    EL_p0_meas, ns_p0_meas = None, None

# ═══════════════════════════════════════════════
# Fig 1: DERC Comparison (Phase 0 vs Phase 1)
# ═══════════════════════════════════════════════
fig, axes = plt.subplots(1, 2, figsize=(14, 6))

# Left: DERC curves
ax = axes[0]
ax.plot(ns_p1, EL_p0, 'b--', linewidth=2, label='Phase 0 (analytic $L^*$)', marker='s', 
        markersize=6, alpha=0.6)
if EL_p0_meas is not None:
    ax.plot(ns_p0_meas, EL_p0_meas, 'b-', linewidth=2, 
            label='Phase 0 (measured)', marker='o', markersize=6)
ax.errorbar(ns_p1, EL_p1, yerr=SD_p1, fmt='r-o', linewidth=2.5, capsize=4,
            label='Phase 1 (Medium3D)', markersize=7)
ax.axhspan(0, 5, alpha=0.08, color='green', label='Medium saturation zone')
ax.axvline(x=1.0, color='gray', linestyle=':', alpha=0.5, label='n=1 threshold')
ax.set_xlabel('Decay Exponent $n$', fontsize=13)
ax.set_ylabel('$\\mathbb{E}[L]$ (mean lever arm)', fontsize=13)
ax.set_title('DERC: Phase 0 (analytic) vs Phase 1 (medium)', fontsize=14)
ax.legend(fontsize=10, loc='upper right')
ax.set_xlim(0.3, 3.2)
ax.set_ylim(0, 15)
ax.grid(True, alpha=0.3)

# Annotate staircase
ax.annotate('Staircase\n(injection threshold)',
            xy=(0.75, 8.16), xytext=(0.5, 11),
            arrowprops=dict(arrowstyle='->', color='red'),
            fontsize=10, color='red', ha='center')

# Right: Ratio E[L]_medium / E[L]_analytic
ax2 = axes[1]
ratios = [EL_p1[i]/EL_p0[i] if EL_p0[i] > 0 else 0 for i in range(len(ns_p1))]
ax2.bar(ns_p1, ratios, width=0.2, color='steelblue', alpha=0.8, edgecolor='navy')
ax2.axhline(y=1.0, color='black', linestyle='--', alpha=0.5)
ax2.set_xlabel('Decay Exponent $n$', fontsize=13)
ax2.set_ylabel('$\\mathbb{E}[L]_{medium} / L^*_{analytic}$', fontsize=13)
ax2.set_title('Medium Effect: Deviation from Analytic Prediction', fontsize=14)
ax2.set_ylim(0, 2.2)
ax2.grid(True, alpha=0.3)

# Annotate regions
ax2.axvspan(0.3, 1.05, alpha=0.1, color='red', label='Plateau (n≤1)')
ax2.axvspan(1.05, 2.2, alpha=0.1, color='blue', label='Descent (1<n<2.2)')
ax2.axvspan(2.2, 3.2, alpha=0.1, color='green', label='Convergence (n>2.2)')
ax2.legend(fontsize=9)

plt.tight_layout()
fig_path = os.path.join(paper_dir, "figures", "fig_derc_phase1_comparison.pdf")
os.makedirs(os.path.dirname(fig_path), exist_ok=True)
plt.savefig(fig_path, dpi=150, bbox_inches='tight')
plt.savefig(fig_path.replace('.pdf', '.png'), dpi=150, bbox_inches='tight')
print(f"Saved: {fig_path}")

# ═══════════════════════════════════════════════
# Fig 2: Medium penetration depth + signal profiles
# ═══════════════════════════════════════════════
fig2, axes2 = plt.subplots(1, 2, figsize=(14, 6))

# Left: Energy profiles for acoustic vs thermal
base = r"D:\cell-cc\Morphosphere_v37_0_native_runtime_prototype_flat_complete\morphosphere_v2pp"
sys.path.insert(0, os.path.join(base, "engines"))
sys.path.insert(0, base)
from engines.medium_system import MediumLattice3D

ax3 = axes2[0]
for med_type, mode, color, label in [
    ("acoustic", "wave", "blue", "Acoustic (wave)"),
    ("thermal", "diffusion", "red", "Thermal (diffusion)")]:
    med = MediumLattice3D(med_type, box_size=10.0, spacing=1.0, mode=mode)
    # Inject at origin for 50 ticks
    for t in range(50):
        med.inject((0, 0, 0), amplitude=1.0)
        med.step()
    # Read along x-axis
    distances = list(range(0, 6))
    energies = [med.read_at((d, 0, 0)) for d in distances]
    ax3.semilogy(distances, [max(e, 1e-8) for e in energies], 
                 f'{color[0]}-o', linewidth=2, markersize=7, label=label)
    # Theoretical penetration depth
    ax3.axvline(x=med.penetration_depth, color=color, linestyle=':', alpha=0.5,
                label=f'$L_{{pen}}$={med.penetration_depth:.1f}')

ax3.set_xlabel('Distance from source (units)', fontsize=13)
ax3.set_ylabel('Energy (log scale)', fontsize=13)
ax3.set_title('Signal Penetration: Acoustic vs Thermal', fontsize=14)
ax3.legend(fontsize=10)
ax3.grid(True, alpha=0.3)
ax3.set_ylim(1e-4, 1e2)

# Right: Impedance matching
ax4 = axes2[1]
Z_body_range = np.linspace(0.1, 5.0, 50)
for med_type, mode, color in [("acoustic", "wave", "blue"), ("thermal", "diffusion", "red")]:
    med = MediumLattice3D(med_type, box_size=4.0, spacing=2.0, mode=mode)
    T_vals = [med.coupling_coefficient(z) for z in Z_body_range]
    ax4.plot(Z_body_range, T_vals, color=color, linewidth=2,
             label=f'{med_type} (Z_med={med.impedance:.2f})')
# Mark current body impedance
Z_body_actual = math.sqrt(2.0 * 1.0) / (2.0 * 2.0)
ax4.axvline(x=Z_body_actual, color='green', linestyle='--', linewidth=2,
            label=f'Body Z={Z_body_actual:.2f}')
ax4.axhline(y=1.0, color='gray', linestyle=':', alpha=0.5)
ax4.set_xlabel('Body Impedance $Z_{body}$', fontsize=13)
ax4.set_ylabel('Transmission Coefficient $T$', fontsize=13)
ax4.set_title('Impedance Matching: T(Z_body, Z_medium)', fontsize=14)
ax4.legend(fontsize=10)
ax4.grid(True, alpha=0.3)
ax4.set_ylim(0, 1.1)

plt.tight_layout()
fig2_path = os.path.join(paper_dir, "figures", "fig_medium_physics.pdf")
plt.savefig(fig2_path, dpi=150, bbox_inches='tight')
plt.savefig(fig2_path.replace('.pdf', '.png'), dpi=150, bbox_inches='tight')
print(f"Saved: {fig2_path}")

# ═══════════════════════════════════════════════
# Fig 3: Latin Square results with medium
# ═══════════════════════════════════════════════
fig3, ax5 = plt.subplots(figsize=(10, 6))

configs = ['B-xyz', 'B-yzx', 'B-zxy', 'C-xyz', 'C-yzx', 'C-zxy']
n1_ranks = [2, 1, 1, 1, 1, 2]
colors_lat = ['#e74c3c' if r > 1 else '#27ae60' for r in n1_ranks]
bars = ax5.bar(configs, n1_ranks, color=colors_lat, edgecolor='black', alpha=0.85)
ax5.axhline(y=1, color='green', linestyle='--', alpha=0.7, label='Target: Rank #1')
ax5.set_xlabel('Latin Square Condition', fontsize=13)
ax5.set_ylabel('n=1 Source Rank (1=closest)', fontsize=13)
ax5.set_title('Latin Square: n=1 Preference Ranking with Medium3D', fontsize=14)
ax5.set_ylim(0, 3.5)
ax5.legend(fontsize=11)

# Annotate
ax5.annotate('4/6 conditions\nn=1 → Rank #1',
             xy=(2.5, 0.3), fontsize=12, ha='center',
             bbox=dict(boxstyle='round', facecolor='lightyellow', alpha=0.8))

plt.tight_layout()
fig3_path = os.path.join(paper_dir, "figures", "fig_latin_square_medium.pdf")
plt.savefig(fig3_path, dpi=150, bbox_inches='tight')
plt.savefig(fig3_path.replace('.pdf', '.png'), dpi=150, bbox_inches='tight')
print(f"Saved: {fig3_path}")

print("\n=== ALL FIGURES GENERATED ===")
