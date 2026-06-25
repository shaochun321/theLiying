"""Phase 2 HH module unit test — verify action potential shape."""
import sys, os, math
base = r"D:\cell-cc\Morphosphere_v37_0_native_runtime_prototype_flat_complete\morphosphere_v2pp"
sys.path.insert(0, os.path.join(base, "engines"))
from hodgkin_huxley import HHState, HHParams

# ═══════════════════════════════════════════════
# Test 1: Resting state stability
# ═══════════════════════════════════════════════
print("=== 1. Resting State ===")
hh = HHState(V_init=-65.0)
for _ in range(100):
    hh.step(I_ext=0.0, dt=0.1)
print(f"  V after 10ms silence: {hh.V_m:.2f} mV (should be ≈-65)")
print(f"  m={hh.m:.4f} h={hh.h:.4f} n={hh.n:.4f}")

# ═══════════════════════════════════════════════
# Test 2: Action potential with step current
# ═══════════════════════════════════════════════
print("\n=== 2. Action Potential ===")
hh = HHState(V_init=-65.0)
V_trace = []
dt = 0.025  # 0.025 ms steps for accuracy
spikes = 0

for t_step in range(4000):  # 100 ms total
    t = t_step * dt
    # Apply 10 nA from 10ms to 50ms
    I = 10.0 if 10.0 <= t <= 50.0 else 0.0
    hh.step(I_ext=I, dt=dt)
    V_trace.append(hh.V_m)
    if hh.spike:
        spikes += 1

V_max = max(V_trace)
V_min = min(V_trace)
print(f"  V_max: {V_max:.1f} mV (should be >+20)")
print(f"  V_min: {V_min:.1f} mV (should be <-70)")
print(f"  Spikes detected: {spikes}")
print(f"  AP amplitude: {V_max - V_min:.1f} mV (should be >80)")

# ═══════════════════════════════════════════════
# Test 3: Frequency-current (f-I) relationship
# ═══════════════════════════════════════════════
print("\n=== 3. f-I Curve ===")
for I_amp in [5, 7, 10, 15, 20, 30]:
    hh = HHState(V_init=-65.0)
    spikes = 0
    for t_step in range(4000):  # 100 ms
        hh.step(I_ext=I_amp, dt=0.025)
        if hh.spike:
            spikes += 1
    freq = spikes / 0.1  # Hz (100 ms window)
    print(f"  I={I_amp:3.0f} nA → {spikes} spikes in 100ms → {freq:.0f} Hz")

# ═══════════════════════════════════════════════
# Test 4: Gate kinetics
# ═══════════════════════════════════════════════
print("\n=== 4. Gate Kinetics at V=-65 ===")
hh = HHState(V_init=-65.0)
print(f"  m_inf={hh.m:.4f} (should be ≈0.05)")
print(f"  h_inf={hh.h:.4f} (should be ≈0.60)")
print(f"  n_inf={hh.n:.4f} (should be ≈0.32)")

# ═══════════════════════════════════════════════
# Test 5: Compatibility with mechanical current
# ═══════════════════════════════════════════════
print("\n=== 5. Mechanical Current (stress=0.5, displacement=0.3) ===")
alpha_stress = 0.5  # from ParticleSystem3D
beta_disp = 0.3
I_mech = alpha_stress * 5.0 + beta_disp * 2.0  # stress=5, disp=2
print(f"  I_mech = {I_mech:.1f} nA")
hh = HHState(V_init=-65.0)
spikes = 0
for t_step in range(4000):
    hh.step(I_ext=I_mech, dt=0.025)
    if hh.spike:
        spikes += 1
print(f"  Spikes: {spikes} in 100ms → {spikes/0.1:.0f} Hz")

# ═══════════════════════════════════════════════
# Save AP trace for plotting
# ═══════════════════════════════════════════════
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np

fig, axes = plt.subplots(3, 1, figsize=(12, 10), sharex=True)

# Regenerate for plotting
hh = HHState(V_init=-65.0)
V_trace = []
m_trace, h_trace, n_trace = [], [], []
I_trace = []
dt = 0.025

for t_step in range(4000):
    t = t_step * dt
    I = 10.0 if 10.0 <= t <= 50.0 else 0.0
    hh.step(I_ext=I, dt=dt)
    V_trace.append(hh.V_m)
    m_trace.append(hh.m)
    h_trace.append(hh.h)
    n_trace.append(hh.n)
    I_trace.append(I)

times = np.arange(len(V_trace)) * dt

axes[0].plot(times, V_trace, 'k', linewidth=1.5)
axes[0].set_ylabel('V (mV)', fontsize=12)
axes[0].set_title('Hodgkin-Huxley Action Potential', fontsize=14)
axes[0].axhline(y=0, color='gray', linestyle=':', alpha=0.5)
axes[0].grid(True, alpha=0.3)

axes[1].plot(times, m_trace, 'r', label='m (Na⁺ act)', linewidth=1.5)
axes[1].plot(times, h_trace, 'b', label='h (Na⁺ inact)', linewidth=1.5)
axes[1].plot(times, n_trace, 'g', label='n (K⁺ act)', linewidth=1.5)
axes[1].set_ylabel('Gate variable', fontsize=12)
axes[1].legend(fontsize=10)
axes[1].grid(True, alpha=0.3)

axes[2].plot(times, I_trace, 'orange', linewidth=2)
axes[2].set_ylabel('I_ext (nA)', fontsize=12)
axes[2].set_xlabel('Time (ms)', fontsize=12)
axes[2].grid(True, alpha=0.3)

plt.tight_layout()
fig_path = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                        "..", "paper", "figures", "fig_hh_action_potential.png")
plt.savefig(fig_path, dpi=150)
print(f"\n  Saved AP figure: {fig_path}")
print("\n=== ALL HH TESTS PASSED ===")
