"""更新论文2图表 (N=50, 有传播延迟)"""
import json, math, os
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "paper", "figures")

# Load N=50 data
with open(os.path.join(os.path.dirname(os.path.abspath(__file__)),
                       "..", "paper", "data_n_sweep_N50.json")) as f:
    raw = json.load(f)

n_vals = sorted([float(k) for k in raw.keys()])
means = [raw[str(n)]["mean"] for n in n_vals]
stds = [raw[str(n)]["std"] for n in n_vals]

A, N_p, sigma = 5.0, 30, 0.3
n_theory = np.linspace(0.3, 3.5, 100)
L_theory = (n_theory * A * np.sqrt(N_p) / sigma) ** (1.0 / (n_theory + 1))

plt.rcParams.update({'font.family': 'serif', 'font.size': 11, 'axes.linewidth': 1.2})

# Fig 5: DERC with N=50
fig, ax = plt.subplots(figsize=(7, 4.5))
ax.plot(n_theory, L_theory, 'k--', linewidth=1.5, alpha=0.6,
        label=r'Theory: $L^* = (nA\sqrt{N}/\sigma)^{1/(n+1)}$')
ax.errorbar(n_vals, means, yerr=stds, fmt='o', markersize=7,
            color='#e74c3c', ecolor='#e74c3c', elinewidth=1.5,
            capsize=4, capthick=1.5, label=r'Measured $\mathbb{E}[L]$ (N=50)',
            zorder=5)
ax.annotate('Rebound\n(propagation\ndelay effect)',
            xy=(3.0, 8.97), xytext=(3.3, 12),
            fontsize=9, color='#8e44ad',
            arrowprops=dict(arrowstyle='->', color='#8e44ad'),
            ha='center')
ax.axvspan(0.3, 0.6, alpha=0.05, color='green')
ax.axvspan(2.0, 3.5, alpha=0.05, color='red')
ax.text(0.45, 14.5, 'Agreement\nzone', fontsize=8, ha='center',
        color='green', alpha=0.7)
ax.text(2.75, 2.0, 'Rebound\nzone', fontsize=8, ha='center',
        color='red', alpha=0.7)
ax.set_xlabel('Decay exponent $n$')
ax.set_ylabel(r'Mean equilibrium distance $\mathbb{E}[L]$')
ax.set_xlim(0.2, 3.5)
ax.set_ylim(0, 18)
ax.legend(fontsize=10, loc='upper right')
ax.spines['top'].set_visible(False)
ax.spines['right'].set_visible(False)
ax.grid(alpha=0.2)
plt.tight_layout()
fig.savefig(os.path.join(OUT, 'fig5_EL_vs_n.pdf'), bbox_inches='tight')
plt.close()
print("-> fig5_EL_vs_n.pdf (N=50)")

# Fig 6: Residual
fig2, (ax1, ax2) = plt.subplots(1, 2, figsize=(10, 4))
L_pred = [(n * A * math.sqrt(N_p) / sigma) ** (1.0 / (n + 1)) for n in n_vals]
ratios = [m / p for m, p in zip(means, L_pred)]
ax1.bar(range(len(n_vals)), ratios,
        color=['#27ae60' if 0.85 < r < 1.15 else '#f39c12' if r < 1.5 else '#e74c3c' for r in ratios],
        width=0.6, edgecolor='#333', linewidth=0.5)
ax1.set_xticks(range(len(n_vals)))
ax1.set_xticklabels([f'{n:.2f}' for n in n_vals], fontsize=9)
ax1.set_xlabel('Decay exponent $n$')
ax1.set_ylabel(r'$\mathbb{E}[L] / L^*_{theory}$')
ax1.axhline(y=1.0, color='k', linewidth=0.8, linestyle='-')
ax1.axhspan(0.85, 1.15, alpha=0.1, color='green')
ax1.set_title('(a) Theory/measurement ratio', fontweight='bold', fontsize=10)
ax1.spines['top'].set_visible(False)
ax1.spines['right'].set_visible(False)

ax2.bar(range(len(n_vals)), stds, color='#3498db', width=0.6,
        edgecolor='#333', linewidth=0.5)
ax2.set_xticks(range(len(n_vals)))
ax2.set_xticklabels([f'{n:.2f}' for n in n_vals], fontsize=9)
ax2.set_xlabel('Decay exponent $n$')
ax2.set_ylabel(r'$\sigma_L$')
ax2.set_title('(b) Fluctuation amplitude', fontweight='bold', fontsize=10)
ax2.spines['top'].set_visible(False)
ax2.spines['right'].set_visible(False)

plt.tight_layout()
fig2.savefig(os.path.join(OUT, 'fig6_residual.pdf'), bbox_inches='tight')
plt.close()
print("-> fig6_residual.pdf (N=50)")
