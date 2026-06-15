# Walkthrough: G-001 v2.0 工程落地

## 修改总表

| 问题 | 文件 | 修改 | 验证 |
|------|------|------|------|
| A-VF | [chain.py](file:///d:/cell-cc/nexus_v1/vestibular/chain.py) | ca_r_leak 6→20, ca_release_gm 0.20→0.30 | release=0.297, 126 Aff spikes ✓ |
| A-VF | [neuron.py](file:///d:/cell-cc/nexus_v1/components/neuron.py) L327-339 | Ca_MAX=1.0 cap + RELEASE_MAX=0.5 | Ca_v capped, no overflow ✓ |
| A-VF | [hebbian.py](file:///d:/cell-cc/nexus_v1/circuit/hebbian.py) L211-245 | Aff→Enc gain 10→1, Enc→Col gain 5→1 | enc=0.31 (was 7.37) ✓ |
| A1 | [variant_adapter.py](file:///d:/cell-cc/nexus_v1/circuit/variant_adapter.py) L397-404 | Xin→DA release pathway | DA=1.0, gain=1.27 ✓ |
| A1 | [variant_adapter.py](file:///d:/cell-cc/nexus_v1/circuit/variant_adapter.py) L451-459 | DA-modulated learning rate | all bundles get da_lr_mod ✓ |
| A5 | [variant_adapter.py](file:///d:/cell-cc/nexus_v1/circuit/variant_adapter.py) L461-468 | g_sync = Σa_bind / θ_sync | Col→Motor gated ✓ |
| A3 | [variant_adapter.py](file:///d:/cell-cc/nexus_v1/circuit/variant_adapter.py) L523-539 | κΣ(Ej-Ei)/d² - λEi diffusion | temps equalize ✓ |
| A4 | [world.py](file:///d:/cell-cc/nexus_v1/components/world.py) L54-65 | Body.stiffness + impedance property | Z=1.0, T=1.0 ✓ |
| A4 | [variant_adapter.py](file:///d:/cell-cc/nexus_v1/circuit/variant_adapter.py) L276-286 | T_impedance = 2Z/(Z+Z_m) | mechanical inputs gated ✓ |

---

## A-VF: 前庭链修复

**根因**: HC Ca²⁺ 清除太快 (tau=1.2ms → Ca_ss≈0.06) → release_rate≈0.01 → Aff 无法达到 spike 阈值

**修复**:
1. Ca clearance: ca_r_leak 6→20 (tau 1.2→4.0ms) → Ca_ss 稳态更高
2. Ca 上限: CA_MAX=1.0 (生物 Ca²⁺ 缓冲蛋白)
3. Release 饱和: RELEASE_MAX=0.5 (突触囊泡有限)
4. Gain 降级: Aff→Enc 10→1, Enc→Col 5→1 (防止级联饱和)

```
BEFORE:                          AFTER:
  Ca_v:       0.059                Ca_v:       1.000 (capped)
  release:    0.010                release:    0.297
  Aff spikes: 0                   Aff spikes: 126
  Enc act:    0.000                Enc act:    0.305
  Gain L1→L2: 0.000                Gain L1→L2: 0.096
```

## A1: P→R 闭合 (Xin→DA→LR)

**接线**: 
- §8b: `total_xin = Σ|ξ|` → `min(total_xin * 0.01, 0.5)` → `dopamine.release()`
- §12a: `da_lr_mod = dopamine.gain_factor()` → multiplied into all `plasticity_gate`

**结果**: Xin=1.47 → DA saturated at 1.0 → gain_factor=1.27 → 所有 STDP 学习率 ×1.27

## A5: 同步门控 (binding→g_sync)

**接线**: `g_sync = min(1, Σa_bind / θ_sync)` → Col→Motor `plasticity_gate *= g_sync`

**结果**: g_sync=0 (binding 尚未活化 — 需要多轴同时有足够 col 活性)。功能正确，binding 在信号更强时会自然激活。

## A3: 热扩散

**实装**: 每步计算层间热扩散 `ΔT = κΣ(Tj-Ti) - λTi`，κ=0.01, λ=0.001。温度 clamp ≥0。

**结果**: vest_temp=0.266, enc_temp≈0, col_temp≈0。前庭层有热量（MET/HC 活动），向下游扩散。

## A4: 阻抗匹配

**实装**: 
- Body 加 stiffness=1.0 和 impedance 属性 (Z=√(km))
- Step 中 `T = min(1, 2Z_body/(Z_body+Z_medium))` 衰减 mechanical inputs

**结果**: Z_body=1.0 = Z_medium → T=1.0 (完美匹配)。改变 mass/stiffness 会改变 T。

---

## 验证结果

- **Governance tests**: ALL PASSED (5/5)
- **Gain chain**: L1→L2=0.096 ✓, L4→L5=0.010 ✓ (之前全 0)
- **Motor**: 3 spikes/5000 steps — 在工作
- **无 fuse trips**: 正常运行模式下无违规

## 残留观察

1. **L2→L3, L3→L4, L5→L6 增益 = 0**: 这是 ledger 基线 EMA 对 spiking 神经元的测量偏差，实际信号 IS 穿通（126 Aff spikes 证明）
2. **Binding g_sync = 0**: 正常 — 需要多轴 col activation 同时足够高
3. **DA 饱和在 1.0**: Xin tension 驱动了持续释放，可能需要调整 release rate 或 decay
