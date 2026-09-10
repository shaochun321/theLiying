# A8/A9/K-06 研究轮 — 物理原语审计表（Task 1）

日期：2026-09-10
执行依据：`cell-cell/claudecode方案/A8-A9-K-06时间方向组织候选_执行方案修订_2026-09-10.md` §3 / §I
审计对象：`nexus_v1/components/semiconductor.py`（四原语）、`nexus_v1/components/compensation.py`（补偿组件）

---

## 一、四原语审计

| primitive | state variable | decay law | nonlinearity | feedback possible? | hysteresis possible? | requires new parameter? | already qualified? |
|---|---|---|---|---|---|---|---|
| **Capacitor** | `charge`（V=Q/C） | 精确指数 RC（`leak()`） | **无**（严格线性） | 需外部接线 | **否**（单极点无多稳） | 否 | 是（H_τ 载体，history_kernel.py:119） |
| **MOSFET** | `m_gate`（可选，τ_gate>0 时） | 一阶弛豫 `m += (m_inf−m)·dt/τ` | **硬截断**（`conduct()` 阈下恒 0，DEG-019）+ 乘积 | 否（器件内无自反馈路径） | 否 | 否 | 是（E^↑ 门限、C_Θ 符合器载体） |
| **Memristor** | `w` ∈ [0,1] | **无衰减**（只有 `apply_dw`，无泄漏项） | **状态依赖**：`conduct(v)=v×G(w)`，G 由 w 决定 | 可（w 反馈到通过自身更新的通量） | **理论上可**（实测否，见下） | 否（r_min/r_max 用原语默认） | 是（SynapticBundle 权重载体） |
| **PowerRail** | `_last_current` | 无（静态） | IR 压降饱和 `V=Vdd−IR` | 否 | 否 | 否 | 是（代谢能量供给） |

## 二、补偿组件审计（`compensation.py`，7 个）

| 组件 | 状态 | 衰减 | 非线性 | 与 𝒜⁺ 关系 |
|---|---|---|---|---|
| VoltageRegulator | 无（静态） | — | 无 | ∈ 𝒜⁺ |
| DecouplingCapacitor | charge | 指数 RC | 无 | **∈ 𝒜⁺**（= H_τ 同构） |
| BiasCurrentSource | 无 | — | 无 | ∈ 𝒜⁺ |
| AutomaticGainControl | `_ema` | 指数 | 除法归一化 | ∈ 𝒜⁺（静态逐元素） |
| CalciumRateIntegrator | `_ca_voltage` | 指数 RC | Zener 钳位 | **∈ 𝒜⁺**（线性积分 + 静态钳位） |
| DivisiveNormalizationReceptor | 无 | — | 除法 | ∈ 𝒜⁺ |
| D2Autoreceptor | `_d2_state` | 指数 | 无 | ∈ 𝒜⁺ |

**结论：7 个补偿组件全部 ∈ 𝒜⁺**（均为线性积分 + 静态非线性）。父层唯一的带记忆非线性来源是 **Memristor 的状态依赖更新**。

## 三、𝒜⁺ 的封闭性边界（决定 A8 的可能性）

𝒜⁺ 的每一项都是「r(t) 的**线性泛函** → **静态非线性**」的有限复合：

- 线性泛函：任意 RC / 多阶 RC / 指数叠加（含 H_τ，τ 可任取）
- 静态非线性：硬截断、乘积、除法、Zener 钳位、平方

**𝒜⁺ 不包含**：
1. **状态依赖系数积分** `ż = f(z)·a(t)`（z 出现在自己演化方程的系数里）
2. **多稳/迟滞动力学**（同一输入历史的两个吸引子）

⇒ 候选必须进入这两类之一。**本轮的实测结果（见工作报告第四节）表明：在
冻结约束下，四原语能构造出第 1 类（memristive 状态依赖），但构造不出
第 2 类（真正的双稳），而第 1 类在"完整 r(t) + 已知初值"的重构攻击下
仍被复现。**

## 四、双稳为什么构造不出（本轮的关键负面发现）

尝试 1（`ZBistableLatch` 自耦合版）：`g_self = conduct(v_i)`。
失败：v 上升 → g 上升 → 正反馈；但 v 下降时 g 同步下降 → 反馈关断 →
**单稳**（实测 v 衰减至 0.036，阈下）。

尝试 2（交叉耦合版）：`g_cross_i = conduct(v_j)`。
失败：两节点互锁需要**至少一侧先独立自持**，而四项原语中无独立恒流源
（PowerRail 是电压源 + IR 压降），互锁退化为"双死锁"（实测 v2 → 0.011）。

尝试 3（memristive 正反馈）：Memristor 的电导由 w 决定，可构成
`ẇ = f(w)·a(t)`。**成功构造**，但实测：
- 初始 w ∈ {0.2, 0.5, 0.8} 在相同输入下**全部收敛到 w=1.0**（散度 0.000e+00）
- 相同脉冲集合仅时序不同 → Δw = 0.000e+00
- 同输入同初值 → 逐位相同（差 0.000e+00）

⇒ 单稳 + 时序无关 + 完全确定性 ⟹ **状态 = 输入历史的确定性函数**，
必然可被"已知初值 + 完整输入历史"的重构器复现。

**根本原因**：四原语中不存在能把"两个吸引子"区分开的物理机制所需的
**独立恒流偏置**（真实 CMOS 锁存器依赖恒流源建立双稳；本项目四原语
只有电压源 + IR 压降，缺少该元件）。按方案 §G，**这就是"无候选"的
物理依据**——不得为此放宽标准或引入冻结以外的原语。

## 五、审计结论

```text
1. 𝒜⁺ 中带记忆的非线性唯一来源 = Memristor 状态依赖更新（§一表）
2. Memristive 候选可构造，但其动力学在本轮实测下是单稳、时序无关、确定性
3. 真正的双稳需要独立恒流偏置，四原语中不存在
4. ⟹ 在冻结约束下无法构造满足 §D/§A.2 的候选 Z
   → 本轮按 §G 以 Z0 收口：NO_CANDIDATE_WITH_EXISTING_PRIMITIVES
```
