# 自身坐标 × 虚位 × 复位耦合 — 是否启动？

## 结论：**不需要启动。三者是假问题。真问题在物理接口。**

---

## 1. 三个概念的当前状态

| 概念 | 代码实体 | 状态 | 架构决策 |
|---|---|---|---|
| **自身坐标结构** | [B.03](file:///D:/cell-cc/nexus_v1/docs/TRACKER_v1.0.md#L37) | **已废弃** | 2026-06-11: "外感受预测由 Shadow 层 STDP 自然学习，禁止人工比较器" |
| **虚位** | [D.10](file:///D:/cell-cc/nexus_v1/docs/TRACKER_v1.0.md#L185) | **显式延后** | 触发条件: sprout/prune 频率 >10/1k步 **且** 虚位回收率 <20% — 两个条件均未满足 |
| **复位耦合** | 无代码实体 | **概念阶段** | spike reset ([neuron.py:L484](file:///D:/cell-cc/nexus_v1/components/neuron.py#L484)) 与 coupler 之间无结构耦合 |

> [!IMPORTANT]
> 三个概念中，一个被废弃 (B.03)，一个被显式延后 (D.10)，一个未实现。
> 将三者组合启动 = 同时违反两个已有架构决策 + 引入一个未验证假设。

---

## 2. 逐个判杀

### 2.1 自身坐标结构 — 已有隐式实现

[SomatoRelay](file:///D:/cell-cc/nexus_v1/docs/TRACKER_v1.0.md#L36) 的拓扑结构已经提供了**隐式**自身坐标：

```
4 relay 神经元 (front/back/left/right)
+ 邻接侧抑 bundle (禁止 front↔back 对角线)
= 体表 2D 流形的神经拓扑编码
```

SomatoRelay 的连接拓扑 + 时间编码 → 隐式 3D/4D 流形 (体表×时间×模态)。

**显式**自身坐标模块被废弃的原因是：它违反了 "预测热觉变化 = Shadow 层 STDP 本职工作" 的原则。如果 Shadow STDP 需要一个人工坐标系来工作，那说明 STDP 本身有问题——应该修 STDP，不是加拐杖。

### 2.2 虚位 — 触发条件远未达到

D.10 的触发条件是 **两个联合条件**：
1. sprout/prune 频率 >10/1k步
2. 虚位回收率 <20%

当前系统的 sprout/prune 频率远低于此阈值。虚位回收机制 (熵账本赫布超边) 足够处理当前负载。

### 2.3 复位耦合 — 问的不对，但暴露了真问题

"复位耦合" 作为概念有一个正确的直觉：**spike reset 是一个物理事件，它应该与时间耦合器产生某种结构性交互**。

当前的事实是：

```
神经元 spike → v_reset (L484)
               ↓
          activation = 1.0 (L516，持续 1 个 dt)
               ↓
          pre_trace += 1.0 (L575)
               ↓
          bundle.propagate() → current = pre_trace × w × gain
               ↓
          coupler.step(current) → 积分 → 输出
               ↓
          target.step(coupler_output)
```

reset 事件通过 pre_trace → propagate → coupler 链条已经**自然传播**。没有断链。

---

## 3. 真正的问题不在这三个概念里

EXP-018 v2 的数据说：
- 反射层工作 (Δx=0.551) ✅
- STDP bundles **不生长** (weight decay -7.5%) ❌
- DA 崩溃到 0 ❌

**这不是坐标/虚位/复位的问题。这是一个信号链增益标定问题。**

### 3.1 信号链断点分析

```
热梯度 (ΔT)
    ↓
SkinPatch → Thermoreceptor → SomatoRelay
    ↓ (_activation_ema)                    ← 信号到这里没问题
直接注入 Encoding (gain=1.0)
    ↓
Encoding 神经元 spikes
    ↓
[Temporal Coupler: τ=2.0] ← ★ 饱和点 ★ (见 analysis_adaptive_coupler_math.md)
    ↓
Column 100% 饱和 → calcium_rate 饱和
    ↓
Shadow 预测 = 常数 1.0 → 所有 shadow 输出相同
    ↓
Shadow→DA bundle: 所有 shadow 输出相同 → DA 输入无分化
    ↓
DA = 0 → 三因子学习 = 0 → STDP 无效
```

> [!CAUTION]
> 根源是 **Coupler τ=2.0 导致 Column 饱和**。
> 不是坐标问题，不是虚位问题，不是复位问题。
> 是一个 RC 参数标定问题。

### 3.2 物理接口上的解药

当前的 TemporalCoupler 已经有 **C-layer** (逆行信使反馈) 和 **B-layer** (突触缩放)，两者都已启用 ([hebbian.py:L476-L483](file:///D:/cell-cc/nexus_v1/circuit/hebbian.py#L476-L483)):

```python
coupler_adapt_vth=0.2,      # C-layer: target 20% duty
coupler_adapt_gm=2.0,       # C-layer: moderate feedback
coupler_blayer_c_slow=100.0, # B-layer: τ_slow = 1000 steps
```

**问题**：C-layer 读的是 `tgt._activation_ema` ([bundle.py:L226](file:///D:/cell-cc/nexus_v1/circuit/bundle.py#L226))。
对于 spiking Column:
- _activation_ema 跟踪的是 `|activation|` 的 EMA
- activation = 0 或 1 (spike = 1, otherwise = 0)
- 当 Column 100% 饱和时，ema → 1.0

C-layer MOSFET: `conduct(1.0)` → `gm × max(0, 1.0 - 0.2) = 2.0 × 0.8 = 1.6`

这个反馈**应该在工作**，但 coupler 的基础 τ=2.0 太大了。即使 C-layer 增加了额外 leak，V_ss 仍然远超目标：

```
无 C-layer: V_ss = 0.54 × gain = 1.62 >> v_peak
有 C-layer: V_ss ≈ 0.54 / (1 + 1.6) ≈ 0.21 × gain → 仍 > v_peak
```

### 3.3 正确的修复路径

不是启动新概念，而是**标定已有结构的参数**：

| 参数 | 当前值 | 问题 | 建议 |
|---|---|---|---|
| `coupler_r_leak` | 2.0 | τ_couple = 2.0 → V_ss 远超需求 | 按 [分析文档](file:///L:/Users/%E7%BB%8D%E6%98%A5/.gemini/antigravity-ide/brain/b28b1552-1fcc-4344-b53a-904fd4f4bced/analysis_adaptive_coupler_math.md#L83): τ_eq ≈ 0.135 → r_leak ≈ 0.135 |
| `coupler_adapt_gm` | 2.0 | 反馈强度不足以克服基础 τ 过大 | 增大到 5.0-10.0，或降低基础 τ |
| `coupler_v_clamp` | 2.0 | 削峰上限太高 | 降到 0.5 (Column v_peak 的 2-3 倍) |

---

## 4. 最终判断

```
自身坐标结构 → 已废弃 (B.03)，隐式实现已存在          → 不启动
虚位重整化   → 触发条件未满足 (D.10)                   → 不启动
复位耦合     → spike reset 已自然传播，无断链            → 不启动

真正需要做的:
  → 标定 Temporal Coupler 的 r_leak / adapt_gm / v_clamp
  → 使 Column 脱离 100% 饱和
  → 使 Shadow 输出分化
  → 使 DA ≠ 0
  → 使三因子学习恢复
```

> [!TIP]
> **原则：在物理接口上寻找解药。**
> 解药不是新概念，是已有 RC 参数的热力学标定。
> Coupler 的 B-layer + C-layer 是正确的结构，参数需要对齐。
