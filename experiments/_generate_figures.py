"""生成论文图表 (PDF via matplotlib) + 包含拉丁方实验数据"""
import os, sys, math
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)),
    r"Morphosphere_v37_0_native_runtime_prototype_flat_complete\morphosphere_v2pp\engines"))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)),
    r"Morphosphere_v37_0_native_runtime_prototype_flat_complete\morphosphere_v2pp"))
from engines.practice_engine import PracticeEngine
from collections import Counter

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "paper", "figures")
os.makedirs(OUT, exist_ok=True)

plt.rcParams.update({
    'font.family': 'serif',
    'font.size': 11,
    'axes.linewidth': 1.2,
    'figure.dpi': 150,
})
COLORS = {'acoustic': '#4ecdc4', 'thermal': '#ff6b35', 'luminous': '#ffd700'}

# ─── Collect data (N=20, T=300) ───
N_SEEDS = 20
TICKS = 300

print("Collecting baseline data...")
counts = Counter()
L_data = {s: [] for s in ['acoustic', 'thermal', 'luminous']}
for i in range(N_SEEDS):
    engine = PracticeEngine(n_particles=30, seed=i*37+1)
    for _ in range(TICKS):
        engine.step({"move_x": 0.0, "move_y": 0.0, "move_z": 0.0})
    obs = engine._observer_position()
    levers = {}
    for src in engine.sources:
        _, _, _, r = src.compute_lever(obs)
        levers[src.source_type] = r
        L_data[src.source_type].append(r)
    counts[min(levers, key=levers.get)] += 1

# ─── Fig 1: Bar chart ───
print("Fig 1: Preference bar chart...")
fig, ax = plt.subplots(figsize=(5, 3.5))
sources = ['acoustic', 'thermal', 'luminous']
pcts = [100*counts.get(s,0)/N_SEEDS for s in sources]
bars = ax.bar(range(3), pcts, color=[COLORS[s] for s in sources], width=0.6, edgecolor='#333', linewidth=0.8)
ax.set_xticks(range(3))
ax.set_xticklabels([f'{s.capitalize()}\n(1/r)' if s=='acoustic' else f'{s.capitalize()}\n(1/r²)' for s in sources])
ax.set_ylabel('Fraction closest (%)')
ax.set_ylim(0, 100)
for bar, pct in zip(bars, pcts):
    ax.text(bar.get_x()+bar.get_width()/2, bar.get_height()+2, f'{pct:.0f}%', ha='center', fontweight='bold')
ax.spines['top'].set_visible(False)
ax.spines['right'].set_visible(False)
plt.tight_layout()
fig.savefig(os.path.join(OUT, 'fig1_preference.pdf'), bbox_inches='tight')
plt.close()
print("  -> fig1_preference.pdf")

# ─── Fig 2: Trajectory ───
print("Fig 2: Trajectory L(t)...")
engine = PracticeEngine(n_particles=30, seed=1)
traj = {s: [] for s in sources}
for k in range(400):
    engine.step({"move_x": 0.0, "move_y": 0.0, "move_z": 0.0})
    obs = engine._observer_position()
    for src in engine.sources:
        _, _, _, r = src.compute_lever(obs)
        traj[src.source_type].append(r)

fig, ax = plt.subplots(figsize=(6.5, 3.5))
for s in sources:
    decay = '1/r' if s == 'acoustic' else '1/r²'
    ax.plot(traj[s], color=COLORS[s], linewidth=1.2, alpha=0.85, label=f'{s.capitalize()} ({decay})')
ax.set_xlabel('Tick (t)')
ax.set_ylabel('Lever arm L(t)')
ax.legend(framealpha=0.9, fontsize=9)
ax.spines['top'].set_visible(False)
ax.spines['right'].set_visible(False)
plt.tight_layout()
fig.savefig(os.path.join(OUT, 'fig2_trajectory.pdf'), bbox_inches='tight')
plt.close()
print("  -> fig2_trajectory.pdf")

# ─── Fig 3: Histogram ───
print("Fig 3: Lever arm histogram...")
fig, ax = plt.subplots(figsize=(6, 3.2))
bins = np.arange(2, 15, 1)
for s in sources:
    ax.hist(L_data[s], bins=bins, alpha=0.6, color=COLORS[s],
            label=f'{s.capitalize()} (E[L]={np.mean(L_data[s]):.1f})', edgecolor='#555', linewidth=0.5)
ax.set_xlabel('Final lever arm distance L')
ax.set_ylabel(f'Count (N={N_SEEDS})')
ax.legend(fontsize=9)
ax.spines['top'].set_visible(False)
ax.spines['right'].set_visible(False)
plt.tight_layout()
fig.savefig(os.path.join(OUT, 'fig3_histogram.pdf'), bbox_inches='tight')
plt.close()
print("  -> fig3_histogram.pdf")

# ─── Fig 4: Latin Square causal evidence ───
print("Fig 4: Latin square causal evidence...")
# Pre-computed data from the experiment
# Experiment B: acoustic has n=1
B_data = {
    'aco→x': {'acoustic': 10.97, 'thermal': 7.66, 'luminous': 5.21},
    'aco→y': {'acoustic': 10.79, 'thermal': 4.80, 'luminous': 8.71},
    'aco→z': {'acoustic': 9.55,  'thermal': 9.44, 'luminous': 4.75},
}
# Experiment C: thermal has n=1
C_data = {
    'the→y': {'acoustic': 8.66, 'thermal': 10.74, 'luminous': 4.61},
    'the→z': {'acoustic': 5.90, 'thermal': 9.47,  'luminous': 7.80},
    'the→x': {'acoustic': 5.82, 'thermal': 10.80, 'luminous': 6.86},
}

fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(10, 4), sharey=True)

# Panel A: acoustic has n=1
x = np.arange(3)
w = 0.25
for i, (label, data) in enumerate(B_data.items()):
    for j, s in enumerate(sources):
        is_n1 = (s == 'acoustic')
        ax1.bar(x[i] + (j-1)*w, data[s], w*0.9, color=COLORS[s],
                edgecolor='black' if is_n1 else '#999',
                linewidth=2.0 if is_n1 else 0.5, alpha=0.85)
ax1.set_xticks(x)
ax1.set_xticklabels(['aco→x\nthe→y\nlum→z', 'aco→y\nthe→z\nlum→x', 'aco→z\nthe→x\nlum→y'], fontsize=8)
ax1.set_ylabel('E[L]')
ax1.set_title('(a) Acoustic has n=1', fontweight='bold', fontsize=10)
ax1.axhline(y=0, color='black', linewidth=0.5)
ax1.spines['top'].set_visible(False)
ax1.spines['right'].set_visible(False)

# Panel B: thermal has n=1
for i, (label, data) in enumerate(C_data.items()):
    for j, s in enumerate(sources):
        is_n1 = (s == 'thermal')
        ax2.bar(x[i] + (j-1)*w, data[s], w*0.9, color=COLORS[s],
                edgecolor='black' if is_n1 else '#999',
                linewidth=2.0 if is_n1 else 0.5, alpha=0.85)
ax2.set_xticks(x)
ax2.set_xticklabels(['aco→x\nthe→y\nlum→z', 'aco→y\nthe→z\nlum→x', 'aco→z\nthe→x\nlum→y'], fontsize=8)
ax2.set_title('(b) Thermal has n=1 (swap)', fontweight='bold', fontsize=10)
ax2.spines['top'].set_visible(False)
ax2.spines['right'].set_visible(False)

# Shared legend
patches = [mpatches.Patch(color=COLORS[s], label=s.capitalize()) for s in sources]
patches.append(mpatches.Patch(facecolor='white', edgecolor='black', linewidth=2, label='n=1 (bold border)'))
fig.legend(handles=patches, loc='upper center', ncol=4, fontsize=9, bbox_to_anchor=(0.5, 1.02))

plt.tight_layout(rect=[0, 0, 1, 0.92])
fig.savefig(os.path.join(OUT, 'fig4_latin_square.pdf'), bbox_inches='tight')
plt.close()
print("  -> fig4_latin_square.pdf")

print("\nAll PDF figures generated!")
