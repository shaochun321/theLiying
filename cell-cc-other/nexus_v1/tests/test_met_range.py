"""P1: MET 动态范围诊断 + 修复。"""
import sys
sys.path.insert(0, '.')
from nexus_v1.vestibular.chain import VestibularChain

c = VestibularChain()

# Sweep input from 0 to 1
print("=== MET Dynamic Range Sweep ===\n")
print(f"{'Input':>8s}  {'MET_act':>8s}  {'HC_rel':>8s}")

for level in [0.0, 0.1, 0.2, 0.3, 0.5, 0.7, 0.8, 1.0]:
    c2 = VestibularChain()
    # Run to steady state
    for _ in range(3000):
        c2.step({'yaw': level}, 0.001)
    met = c2.met_neurons['yaw']
    hc = c2.haircell_neurons['yaw']
    print(f"{level:>8.2f}  {met.activation:>8.4f}  {hc.release_rate:>8.4f}")

# Problem: MET activation saturates.
# Even at input=0, MET output is ~1.98 because v_threshold=0.001 and
# the default channel is always conducting at any V > 0.001.
# The channel conducts: g × (V - E_rev) where E_rev=0.615.
# With no input, V sits near V_rest (which is 0.0 by default).
# So MET_act at rest ≈ some baseline from leak balance.

print(f"\nMET config check:")
met0 = c.met_neurons['yaw']
print(f"  v_rest: {met0.config.v_rest}")
print(f"  capacitance: {met0.config.capacitance}")
print(f"  r_leak: {met0.config.r_leak}")
print(f"  vdd: {met0.config.vdd}")
print(f"  r_supply: {met0.config.r_supply}")
ch = met0.config.channels[0]
print(f"  channel gm: {ch.gm}")
print(f"  channel v_thresh: {ch.v_threshold}")
print(f"  channel reversal: {ch.reversal}")
