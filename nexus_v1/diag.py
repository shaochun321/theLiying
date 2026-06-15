"""Block 5 round 3: Derive correct Enc parameters for dt=0.001.

Root cause chain:
  Aff spike → activation=1.0 → G(0.2)=0.125 → gain=40 → current=4.99
  → Enc inertia=0.5 → scaled=9.97 → AGC×5 = 49.9
  → PowerRail: 1.0 - 49.9×0.1 = -3.99 → clamped to 0 → BLOCKED

Solution: reduce the effective current to keep scaled_current × r_supply < 1.0
  → |scaled| < 1.0 / r_supply = 10.0

Working backwards:
  scaled = input / inertia × agc_gain
  Want: |scaled| < 10 → |input| < 10 × inertia / agc_gain

With inertia=0.5, AGC=5: max_input < 10 × 0.5 / 5 = 1.0
Current I_spike = 4.99 → needs to be < 1.0

Options:
  A. Reduce synapse_gain: 40 → 40 × (1.0/4.99) = 8.0
  B. Reduce AGC: 5 → 1.0 (disables gain control)
  C. Increase inertia: 0.5 → 0.5 × 4.99 = 2.5
  D. Reduce r_supply: 0.1 → 0.02 (less PowerRail limiting)
  E. Combination

Let me derive the proper way:
  Target: Enc should reach threshold (0.01) within one ISI (80 steps)
  → Need bias + spike contribution ≥ 0.01 × C / (ISI × dt)
     = 0.01 × 10 / (80 × 0.001) = 1.25

  So the effective current per step should be ~1.25 / 80 = 0.0156
  
  With spike duty cycle 1/80:
    Per-spike current × 1/80 = 0.0156
    Per-spike current = 1.25
  
  I_spike × v_ratio / inertia × agc = 1.25
  
  With v_ratio near 1.0 (small current):
    I_spike = 1.25 × inertia / agc_gain = 1.25 × 0.5 / 1.0 = 0.625
    → gain = I_spike / (act × G_w) = 0.625 / (1.0 × 0.125) = 5.0
    
  With AGC=1.0, gain=5.0:
    scaled = 5.0 / 0.5 × 1.0 = 10.0
    v_ratio = 1.0 - 10 × 0.1 = 0 → still blocked!
    
  With r_supply=0.01:
    scaled = 5.0 / 0.5 = 10
    v_ratio = 1.0 - 10 × 0.01 = 0.9 → OK!
    
  OR: remove AGC from Enc entirely (it's not biologically essential for
  encoding neurons — AGC is more for cortical homeostasis)
"""
import sys, math
sys.path.insert(0, '.')

# Test different parameter combinations
print("=" * 70)
print("PARAMETER SPACE EXPLORATION")
print("=" * 70)

combos = [
    # (name, gain, agc, inertia, r_supply)
    ("Current",        40.0, 5.0, 0.5, 0.1),
    ("No AGC, gain=40", 40.0, 1.0, 0.5, 0.1),
    ("No AGC, gain=5",   5.0, 1.0, 0.5, 0.1),
    ("No AGC, gain=10", 10.0, 1.0, 0.5, 0.1),
    ("gain=5, low r_sup", 5.0, 1.0, 0.5, 0.01),
    ("gain=10, low r_sup", 10.0, 1.0, 0.5, 0.01),
    ("gain=40, no AGC, low r", 40.0, 1.0, 0.5, 0.01),
]

G_w = 1.0 / (0.1 + 9.9 * 0.8)  # w=0.2
print(f"\nG(w=0.2) = {G_w:.4f}")
print(f"Aff spike activation = 1.0")
print(f"Bias current = 0.001")
print(f"Enc: C=10, R_leak=20, v_threshold=0.01")
print(f"dt = 0.001")

print(f"\n{'Config':25s} {'I_spike':>8s} {'scaled':>8s} {'v_ratio':>8s} {'I_eff':>8s} {'dV/spike':>10s} {'V_ss_bias':>10s} {'Status':>8s}")
print(f"{'-'*25} {'-'*8} {'-'*8} {'-'*8} {'-'*8} {'-'*10} {'-'*10} {'-'*8}")

for name, gain, agc, inertia, r_sup in combos:
    I_spike = 1.0 * G_w * gain
    I_bias = 0.001
    
    # Spike path
    sc_spike = I_spike / inertia * agc
    vr_spike = max(0, 1.0 - abs(sc_spike) * r_sup)
    I_eff_spike = sc_spike * vr_spike
    dV_spike = I_eff_spike * 0.001 / 10.0  # dt/C
    
    # Bias path (constant, so no duty cycle)
    sc_bias = I_bias / inertia * agc
    vr_bias = max(0, 1.0 - abs(sc_bias) * r_sup)
    I_eff_bias = sc_bias * vr_bias
    V_ss_bias = I_eff_bias * 20.0  # I × R_leak (steady state)
    
    blocked = "BLOCKED" if vr_spike == 0 else ("OK" if V_ss_bias + dV_spike * 80 > 0.005 else "LOW")
    print(f"{name:25s} {I_spike:8.3f} {sc_spike:8.2f} {vr_spike:8.4f} {I_eff_spike:8.4f} {dV_spike:10.7f} {V_ss_bias:10.6f} {blocked:>8s}")

# Best option: No AGC + lower r_supply + moderate gain
print(f"""
RECOMMENDATION:
  1. Remove AGC from Encoding/Column (not biologically essential)
  2. Keep r_supply=0.1 (PowerRail current limiting is realistic)
  3. Adjust synapse_gain so scaled < 10

  With no AGC, gain=40, inertia=0.5, r_supply=0.1:
    I_spike = 1.0 × 0.125 × 40 = 4.99
    scaled = 4.99 / 0.5 = 9.97
    v_ratio = 1.0 - 9.97 × 0.1 = 0.003 → barely passes!
    But per-spike dV is tiny.
    
  Better: gain=10
    I_spike = 1.0 × 0.125 × 10 = 1.25
    scaled = 1.25 / 0.5 = 2.5
    v_ratio = 1.0 - 2.5 × 0.1 = 0.75 → good!
    dV = 2.5 × 0.75 × 0.001 / 10 = 0.000188
    After 80 spikes: 0.015 → above threshold!
""")
