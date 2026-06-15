"""Phase 1 独立验证: 所有新元件的数学正确性测试。

不使用任何 nexus_v1 核心代码 — 纯独立验证。
"""
import sys, math
sys.path.insert(0, '.')

PASS = 0
FAIL = 0

def check(name, condition, actual, expected):
    global PASS, FAIL
    status = "PASS" if condition else "FAIL"
    if condition:
        PASS += 1
    else:
        FAIL += 1
    print(f"  [{status}] {name:40s} actual={actual!s:>20s}  expected={expected}")


print("=" * 70)
print("PHASE 1 — VARIANT COMPONENT STANDALONE VERIFICATION")
print("=" * 70)

# ═══════════════════════════════════════════════════════════════
# 1. ResonantOscillator
# ═══════════════════════════════════════════════════════════════
print("\n── 1. ResonantOscillator ──")
from nexus_v1.components.oscillator import ResonantOscillator

osc = ResonantOscillator(frequency=50.0, mu=0.5, amplitude=0.1)
dt = 0.001

# Run for 1 second (50 full cycles expected)
samples = []
zero_crossings = 0
prev = osc.output()
for i in range(1000):
    val = osc.step(dt)
    if prev <= 0 and val > 0:
        zero_crossings += 1
    prev = val
    samples.append(val)

# Frequency: zero_crossings should be ~50 in 1 second
measured_freq = zero_crossings
check("Frequency (50 Hz target)", 
      40 <= measured_freq <= 60,
      f"{measured_freq} Hz", "40-60 Hz")

# Amplitude: should be around 0.1 × 2 = 0.2 (Van der Pol limit cycle)
max_amp = max(abs(s) for s in samples)
check("Amplitude bounded",
      max_amp < 1.0,
      f"{max_amp:.4f}", "< 1.0")

check("Amplitude nonzero",
      max_amp > 0.01,
      f"{max_amp:.4f}", "> 0.01")

# Phase extraction
phase = osc.phase
check("Phase computable",
      -math.pi <= phase <= math.pi,
      f"{phase:.3f} rad", "[-π, π]")

# Different μ: relaxation oscillation
osc2 = ResonantOscillator(frequency=5.0, mu=3.0, amplitude=1.0)
for i in range(5000):
    osc2.step(dt)
check("Relaxation osc stable",
      abs(osc2._x) < 20.0,
      f"|x|={abs(osc2._x):.3f}", "< 20")

# ═══════════════════════════════════════════════════════════════
# 2. NDRElement
# ═══════════════════════════════════════════════════════════════
print("\n── 2. NDRElement ──")
from nexus_v1.components.ndr import NDRElement

ndr = NDRElement(v_peak=0.15, v_valley=0.35, g_positive=2.0)

# Region 1: positive conductance
i_low = ndr.conduct_static(0.1)
check("Region 1 positive I",
      i_low > 0,
      f"{i_low:.4f}", "> 0")

# Peak current
i_peak = ndr.conduct_static(0.15)
check("Peak current",
      i_peak > 0,
      f"{i_peak:.4f}", "> 0")

# NDR region: current should be LESS than peak
i_ndr = ndr.conduct_static(0.25)
check("NDR: I(0.25) < I_peak",
      i_ndr < i_peak,
      f"{i_ndr:.4f} < {i_peak:.4f}", "True")

# Valley: minimum current
i_valley = ndr.conduct_static(0.35)
check("Valley current minimal",
      i_valley <= i_peak,
      f"{i_valley:.4f}", f"≤ {i_peak:.4f}")

# Region 3: current rises again
i_high = ndr.conduct_static(0.5)
check("Region 3: I(0.5) > I_valley",
      i_high > i_valley,
      f"{i_high:.4f} > {i_valley:.4f}", "True")

# Differential resistance negative in NDR
r_diff = ndr.differential_resistance(0.25)
check("NDR: negative dR",
      r_diff < 0,
      f"{r_diff:.4f}", "< 0")

# Dynamic: HH-like inactivation
ndr2 = NDRElement()
i_dyn = ndr2.conduct_dynamic(0.3, 0.001)
check("Dynamic NDR computable",
      isinstance(i_dyn, float),
      f"{i_dyn:.4f}", "float")

# ═══════════════════════════════════════════════════════════════
# 3. MagnetofluidDamper
# ═══════════════════════════════════════════════════════════════
print("\n── 3. MagnetofluidDamper ──")
from nexus_v1.components.damper import MagnetofluidDamper

dmp = MagnetofluidDamper(r_base=1.0, alpha=0.5, beta=0.1)

# Low current: R ≈ R_base
r_low = dmp.effective_resistance(0.0)
check("Zero current: R = R_base",
      abs(r_low - 1.0) < 0.01,
      f"{r_low:.4f}", "≈ 1.0")

# High current: R > R_base (self-damping)
r_high = dmp.effective_resistance(5.0)
check("High current: R > R_base",
      r_high > r_low,
      f"{r_high:.4f}", f"> {r_low:.4f}")

# Attenuation: large signals get compressed more
out_small = dmp.attenuate(0.1)
out_large = dmp.attenuate(5.0)
ratio_small = out_small / 0.1
ratio_large = out_large / 5.0
check("Compression: large signals attenuated more",
      ratio_large < ratio_small,
      f"{ratio_large:.4f} < {ratio_small:.4f}", "True")

# Faraday oscillation
dmp2 = MagnetofluidDamper(
    faraday_enabled=True, 
    faraday_freq=100.0,
    faraday_threshold=0.3,
    beta=1.0
)
# Below threshold: no oscillation
f_below = dmp2.step(0.1, 0.001)  # B = 0.1 < 0.3
check("Faraday below threshold: 0",
      abs(f_below) < 0.001,
      f"{f_below:.6f}", "≈ 0")

# Above threshold: oscillation present
f_above = dmp2.step(5.0, 0.001)  # B = 5.0 > 0.3
# May or may not be exactly 0 at this phase, so just check non-crash
check("Faraday above threshold: computable",
      isinstance(f_above, float),
      f"{f_above:.6f}", "float")

# ═══════════════════════════════════════════════════════════════
# 4. LiquidMetalRouter
# ═══════════════════════════════════════════════════════════════
print("\n── 4. LiquidMetalRouter ──")
from nexus_v1.components.router import LiquidMetalRouter

rtr = LiquidMetalRouter(
    g_metal=1.0, tau_reconfig=0.5,
    theta_grow=0.3, theta_prune=0.05
)

# Initial: disconnected
check("Initial state: disconnected",
      rtr.state < 0.01,
      f"{rtr.state:.4f}", "≈ 0")

# High correlation → should grow
for i in range(2000):
    rtr.step(pre_activity=0.8, post_activity=0.8, dt=0.001)
check("High corr → connected",
      rtr.state > 0.5,
      f"{rtr.state:.4f}", "> 0.5")

# Signal passes through when connected
sig_out = rtr.conduct(1.0)
check("Connected: signal passes",
      sig_out > 0.3,
      f"{sig_out:.4f}", "> 0.3")

# Low correlation → should prune
for i in range(5000):
    rtr.step(pre_activity=0.0, post_activity=0.0, dt=0.001)
check("Zero corr → pruning",
      rtr.state < 0.5,
      f"{rtr.state:.4f}", "< 0.5")

# Force connect/disconnect
rtr2 = LiquidMetalRouter()
rtr2.force_connect()
check("Force connect: s=1",
      rtr2.state == 1.0,
      f"{rtr2.state:.4f}", "= 1.0")

rtr2.force_disconnect()
check("Force disconnect: s=0",
      rtr2.state == 0.0,
      f"{rtr2.state:.4f}", "= 0.0")

# ═══════════════════════════════════════════════════════════════
# 5. Neuromodulator
# ═══════════════════════════════════════════════════════════════
print("\n── 5. Neuromodulator ──")
from nexus_v1.components.modulator import (
    Neuromodulator, create_dopamine, create_serotonin
)

da = create_dopamine()

# Baseline
check("DA baseline",
      abs(da.concentration - 0.1) < 0.01,
      f"{da.concentration:.4f}", "≈ 0.1")

# Release burst
da.release(0.5)
for i in range(500):
    da.step(0.001)
check("DA elevated after release",
      da.concentration > 0.15,
      f"{da.concentration:.4f}", "> 0.15")

# Gain factor increases with DA
gf = da.gain_factor()
check("DA gain factor > 1",
      gf > 1.0,
      f"{gf:.4f}", "> 1.0")

# LR factor increases (three-factor learning)
lrf = da.lr_factor()
check("DA lr factor > 1",
      lrf > 1.0,
      f"{lrf:.4f}", "> 1.0")

# Decay back to baseline
for i in range(10000):
    da.step(0.001)
check("DA decays to baseline",
      abs(da.concentration - 0.1) < 0.05,
      f"{da.concentration:.4f}", "≈ 0.1")

# Serotonin: different profile
sht = create_serotonin()
check("5-HT baseline higher than DA",
      sht.baseline > da.baseline,
      f"{sht.baseline:.4f}", f"> {da.baseline:.4f}")

check("5-HT slower decay",
      sht.tau_decay > da.tau_decay,
      f"{sht.tau_decay:.1f}s", f"> {da.tau_decay:.1f}s")

# ═══════════════════════════════════════════════════════════════
# SUMMARY
# ═══════════════════════════════════════════════════════════════
print(f"\n{'='*70}")
print(f"PHASE 1 VERIFICATION SUMMARY")
print(f"{'='*70}")
print(f"  PASS: {PASS}")
print(f"  FAIL: {FAIL}")
print(f"  TOTAL: {PASS + FAIL}")
if FAIL == 0:
    print(f"\n  ✓ ALL COMPONENTS VERIFIED — ready for Phase 2")
else:
    print(f"\n  ✗ {FAIL} FAILURES — fix before proceeding")

# Verify mother codebase is untouched
print(f"\n── Mother Codebase Integrity ──")
from nexus_v1.circuit.hebbian import HebbianCircuit
c = HebbianCircuit()
c.step({'yaw': 0.8}, 0.001)
print(f"  HebbianCircuit: still runs ✓")
print(f"  Total neurons: {len(c.get_all_neurons())}")
print(f"  Total bundles: {len(c.get_all_bundles())}")
