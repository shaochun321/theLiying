# Cell-CC 系统状态文档

> **版本**: v0.9.0  
> **日期**: 2026-06-06  
> **上次更新者**: Antigravity (对话 b28b1552)

---

## 版本历史

| 版本 | 日期 | 变更概要 |
|------|------|----------|
| v0.9.0 | 2026-06-06 | 母本分化 (DN/CRI/D2R) + 熵账本前置化 |

---

## 一、结构总览

```
VariantCircuit (variant_adapter.py)
├── VestibularChain: MET → HairCell → Afferent_reg + Afferent_irr
├── HebbianCircuit (hebbian.py)
│   ├── Encoding: 2/axis (reg+irr) × 4 axes (x,y,z + therm)
│   ├── Column: 1/axis × 4 axes
│   ├── Motor: 3 base (move_x/y/z) + mitosis children
│   ├── Bundles: vest→enc, enc→col, col→motor + sprouts
│   └── Structural: sprout/prune/mitosis (gated by _structural_freeze)
├── Shadow Sandbox (shadow_sandbox.py)
│   ├── Shadow Enc: with DivisiveNormalization (DN)
│   ├── Shadow Col: with CalciumRateIntegrator (CRI), spiking
│   └── Shadow→DA bundles (calcium_rate signal)
├── DA Circuit (variant_adapter._init_da_circuit)
│   ├── DA neurons × 3: with D2Autoreceptor, gm=8.0, bias_current
│   ├── Xin relay neuron
│   └── DA→learning gate (三因子: PNN × DA × sync)
├── Entropy Ledger System
│   ├── Phase 0 (PRE-STEP): NoetherProbe + WeightEntropy + TOPRXIN
│   ├── Phase Z (POST-STEP): StructuralEntropy + StructuralBridge
│   └── GuidedConstructionAuditor (Section 7)
├── ECM + Vascular + Thermal
├── Oscillators (per axis)
├── LiquidMetalRouters (per axis)
├── Lateral Inhibition (binding layer)
└── CirculationMeter
```

## 二、数理基础

### 信号流度量
```
ds²/ν = Σ_bundles w²·G²·(Δa)² / Σ_bundles w²·G²
```
- w: Memristor 权重
- G: gated conductance
- Δa: 目标 activation 变化

### 守恒律 (Noether, T4)
1. **能量守恒** (时间平移对称): E_stored(t) + Q(0→t) = E_stored(0) + E_in(0→t)
2. **权重平衡** (规范不变): ΔW = Σ(LTP) - Σ(LTD) - Σ(decay)
3. **Xin 簿记** (张力守恒): Xin_produced = Xin_consumed + Xin_remaining
4. **Landauer 界** (信息-熵耦合): Q ≥ kT·ln2·bits_erased

### 组件物理
- **Neuron**: RC 膜 + MOSFET 通道 + PowerRail
- **Bundle**: Memristor 矩阵 + STDP (Δw = η·pre·post - λ·w)
- **分化组件**:
  - CRI: Capacitor 积分 + Zener MOSFET 钳位 → calcium_rate ∈ [0,1]
  - DN: output = raw / (σ + pool), pool via Capacitor 低通
  - D2R: MOSFET (Shockley) + Capacitor → GIRK K⁺ 超极化

### T/O/P/R/Xin 递归语法
- T(transmission), O(observation), P(prediction), R(response), Xin(mismatch)
- 每个 bundle 同时具有五个相位强度
- 结构事件 (sprout/prune/mitosis) 对应递归周期
- 超度量距离: d_u(a,b) = 1/(1+depth(LCA(a,b)))

## 三、核心理念

1. **"奖励不是标量——奖励是环流模式回归平衡的过程"**
2. **"信号功耗 ≠ 信息功耗"** (ξ²G²/R 是焦耳热, P_Landauer 是信息擦除代价)
3. **"我不做降级，降级只会让项目走偏"**
4. **"每套特殊结构都应该有对应的特殊分化元组件"** (引导性构建)
5. **熵账本系统是事前守卫，不是事后审计**

## 四、当前待办

| 优先级 | 项目 | 状态 |
|--------|------|------|
| **P0** | **C3': 进食-运动-体征的环流耦合** | 下一步 |
| P1 | B1: Noether strictness | 未开始 |
| P1 | B5: Polarization operator | 未开始 |
| P2 | 维度审计 (T/S/I → dE/dt) | 进行中 |

## 五、关键文件索引

| 文件 | 用途 | 最后修改 |
|------|------|----------|
| `variant_adapter.py` | 主电路 + step() 流程 | 2026-06-06 |
| `hebbian.py` | 母电路 + 结构生长 | 2026-06-06 |
| `neuron.py` | 神经元 + 分化组件集成 | 2026-06-05 |
| `compensation.py` | CRI/DN/D2R 组件 | 2026-06-05 |
| `noether_probe.py` | Noether 守恒验证 | 2026-06-05 |
| `toprxin_ledger.py` | T/O/P/R/Xin 账本 | 2026-06-05 |
| `shadow_sandbox.py` | 影子层 | 2026-06-05 |
| `bundle.py` | 突触束 + CRI 信号路径 | 2026-06-05 |
