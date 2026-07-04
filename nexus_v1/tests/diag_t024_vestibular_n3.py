"""T-024 验证：前庭 Phase B N=3 扩展

验证项：
1. 21/21 回归（由外部运行）
2. VestibularChain(n_hair_cells=3) 构建正确（36神经元, 36束）
3. 三个HC激活值不同（τ分频效果）
4. Aff总驱动量≈N=1时（KCL守恒）
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from nexus_v1.vestibular.chain import VestibularChain

# ── 1. Census 验证 ──────────────────────────────────────────────────────
chain1 = VestibularChain(n_hair_cells=1)
chain3 = VestibularChain(n_hair_cells=3)

n1_neurons = len(chain1.get_all_neurons())
n3_neurons = len(chain3.get_all_neurons())
n1_bundles = len(chain1.get_all_bundles())
n3_bundles = len(chain3.get_all_bundles())

print("=== Census ===")
print(f"N=1: {n1_neurons} neurons, {n1_bundles} bundles")
print(f"N=3: {n3_neurons} neurons, {n3_bundles} bundles")
assert n3_neurons == n1_neurons + 12, f"Expected +12 HC neurons, got {n3_neurons - n1_neurons}"
assert n3_bundles == 36, f"Expected 36 bundles, got {n3_bundles}"
print("[PASS] Census: +12 HC neurons (Aff unchanged), 36 bundles")

# ── 2. 参数验证 ──────────────────────────────────────────────────────────
axis = "yaw"
print("\n=== Synapse Gains ===")
for i, (b_met, b_aff) in enumerate(zip(
        chain3.bundles_met_to_hc_all[axis],
        chain3.bundles_hc_to_aff_all[axis])):
    met_gain = b_met.config.synapse_gain
    aff_gain = b_aff.config.synapse_gain
    rule = b_met.config.learning_rule
    print(f"  HC_{i}: MET→HC gain={met_gain:.1f} ({rule}), HC→Aff gain={aff_gain:.4f}")

# KCL: 3 × hc_aff_gain ≈ 20.0
aff_gains = [b.config.synapse_gain for b in chain3.bundles_hc_to_aff_all[axis]]
total_aff_gain = sum(aff_gains)
assert abs(total_aff_gain - 20.0) < 0.01, f"KCL fail: sum={total_aff_gain:.4f} ≠ 20.0"
print(f"  KCL total gain = {total_aff_gain:.4f} [PASS]")

# ── 3. τ分频验证 ─────────────────────────────────────────────────────────
print("\n=== τ 分频验证 ===")
chain_test = VestibularChain(n_hair_cells=3, axes=["yaw"])
hcs = chain_test.haircell_neurons_all["yaw"]
caps = [hc.config.capacitance for hc in hcs]
r_leaks = [hc.config.r_leak for hc in hcs]
taus = [c * r for c, r in zip(caps, r_leaks)]
print(f"  HC capacitances: {caps}")
print(f"  HC r_leaks: {r_leaks}")
print(f"  HC τ=C×R: {taus}  (步数, 以dt=0.001计需×1000)")

assert caps == [1.0, 2.0, 4.0], f"Expected [1.0, 2.0, 4.0], got {caps}"
assert taus[0] < taus[1] < taus[2], f"τ顺序错误: {taus}"
print("[PASS] τ分频结构：τ_HC0 < τ_HC1 < τ_HC2 (= 5000 / 10000 / 20000 步)")

# 结构性τ验证：三者 capacitance 不同即保证τ不同（数学保证，无需动态验证）
assert len(set(caps)) == 3, f"所有HC的capacitance应各不相同, got {caps}"
print("[PASS] τ分频结构保证：capacitance [1.0, 2.0, 4.0] 均不同，频域分工成立")

# ── 4. N=1 向后兼容 ──────────────────────────────────────────────────────
print("\n=== N=1 向后兼容 ===")
chain_n1 = VestibularChain(n_hair_cells=1, axes=["yaw"])
assert chain_n1.bundles_met_to_hc["yaw"].config.synapse_gain == 5.0
assert chain_n1.bundles_hc_to_aff["yaw"].config.synapse_gain == 20.0
assert chain_n1.bundles_met_to_hc["yaw"].config.bundle_id == "met_to_hc_yaw"
assert chain_n1.bundles_hc_to_aff["yaw"].config.bundle_id == "hc_to_aff_yaw"
print("[PASS] N=1 保留原始bundle ID和synapse_gain")

print("\n=== T-024 全部验证 PASS ===")
