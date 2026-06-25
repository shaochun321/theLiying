# T006: 理论锚点 — 物理学对标

> **Status**: Verified alignment
> **Date**: 2026-06-07
> **Source**: External review (2026.6.7.4)

---

## 1. Landauer 原理 → T↔I 换算率

**对标理论**: Landauer's Principle (1961), Stochastic Thermodynamics

**核心定律**:
$$\Delta E \geq kT \ln 2 \cdot |\Delta H|$$

每次信息擦除（状态不可逆改变）必须向环境耗散至少 $kT \ln 2$ 的热量。

**项目对应**:
- 消除 Xin 误差 = 信息擦除 → 必须消耗能量
- 改变突触权重 = 电流流过忆阻器 → 焦耳热 $I^2R$
- metabolic_tax: $\kappa \times |\Delta W / \Delta t|$ = Landauer 代价的电路实现
- NoetherProbe T1.3: 验证 Landauer bound 在每步成立

**项目验证**: 回归测试 T1.3 持续通过 (21/21)

**结构推论**: 
废除 MAX_BUNDLES 硬上限后，Landauer 原理自动提供容量上限：
每个 bundle 维持其信息状态的最小功耗 ≥ $kT \ln 2 \times$ 信息位数。
当 $N_b \times P_{maintain} > P_{input}$ 时，系统在物理上被绝对逼停。

---

## 2. 自由能原理 (FEP) → I 驱动 S 与 T

**对标理论**: Karl Friston, Free Energy Principle (FEP) & Active Inference

**核心主张**: 自组织系统必须最小化变分自由能（预测误差 / Surprise）。

**项目对应**:
- $\Xi = |P - R|$ = FEP 的 Surprise（电路版）
- Friston: 连续概率密度上的变分微积分
- 本项目: 绝对电压差代替概率惊奇

**降低自由能的三条路径**:

| 路径 | Friston FEP | 本项目 | 时间尺度 |
|---|---|---|---|
| 感知路径 | 更新 posterior | STDP 权重调整 | ms (AC) |
| 行动路径 | 改变 sensory input | Motor → Body → 改变感知 | s |
| **结构路径** | *(FEP 未涵盖)* | **Fruit expand/contract** | **ks (DC)** |

**项目的独特贡献**: FEP 只有两条路径（perception + action）。
本项目新增第三条——结构路径（Xin → Fruit → Sprout/Prune）。
这对应大脑发育中的 structural plasticity，是 FEP 的自然扩展。

**DC/AC 分离** (来自 Review 2026.6.7.3):
- 结构变化由信号的 **DC 成分**驱动（Fruit 的 500-tick 成熟期 = 低通滤波器）
- 权重变化由 **AC 成分**驱动（STDP 响应毫秒级 spike timing）

---

## 3. 耗散结构 + 建构定律 → S↔T 凝结

**对标理论**: 
- Ilya Prigogine, Dissipative Structures (Nobel 1977)
- Adrian Bejan, Constructal Law (1996)

**核心主张**: 
有限规模的流动系统为了在时间中存续，必然会演化其宏观拓扑结构，
以提供让流体（能量流、误差流）更容易释放的通道。

**项目对应**:
- Sprout = 为最大化耗散效率而演化拓扑
- Crystallization（垫支）= 非平衡定态 (NESS)
- Standing wave = 稳态振荡模式
- E1 验证: mean_xi 从 1644.7 → 1160.9 (-29%) = 耗散效率提升

**结构凝结的条件**:
当系统找到了能以最低内部摩擦力将外部振荡能量耗散的拓扑时，
结构固化 → crystallization → PNN maturation → 临界期关闭。

**代码验证**:
$$\frac{dE_S}{dt} = \kappa \times \left|\frac{\Delta W}{\Delta t}\right|$$
metabolic_tax 就是结构变化的能量代价。

**推论**: 废除 MAX_BUNDLES 不会导致无限增长——
建构定律保证系统会在耗散效率最优的拓扑处自动停止增长。

---

## 4. Margolus-Levitin + 代谢预算 → 全局约束

**对标理论**:
- Margolus-Levitin Theorem: 给定能量下状态演化的绝对速度上限
- Bekenstein Bound: 给定空间和能量下的最大信息量
- Laughlin et al.: 大脑代谢能量预算

**全局约束方程**:
$$N_{eff} \cdot \Delta w \cdot f_{osc} \cdot \bar{\xi}_{vest} \leq P_{input}$$

**T·S·I 的可能闭合路径**:

将各因子映射到 T·S·I:
- $S \approx N_{eff} \cdot \langle\Delta w\rangle$ → 结构复杂度 × 学习容量
- $T \approx 1/f_{osc}$ → 振荡周期 = 时间尺度
- $I \approx \bar{\xi}$ → 平均预测误差 = 信息需求

因此: **$T \cdot S \cdot I \leq P_{input}$** 

这不是守恒律，而是**代谢功率约束**。当系统撞到功率上限时：
- S↑ (更多结构) → 迫使 T↑ (更慢的周期) 或 I↓ (更低的误差容忍)
- I↑ (更多误差) → 迫使 S↓ (更简单的结构) 或 T↑ (更慢)
- T↓ (更快振荡) → 迫使 S↓ 或 I↓

这正是 Laughlin 的大脑代谢预算在电路层面的翻译。

---

## 对项目路线图的影响

1. **废除 MAX_BUNDLES=80**: Landauer + 建构定律提供物理上限
2. **T·S·I 重构**: T = 动态恢复时间, S·I ≤ P/T
3. **影子层设计**: 影子层 = DA 门控的智能控制器 (FEP action path)
4. **DC/AC 分离**: 影子层处理 DC (结构), 主层处理 AC (权重)
