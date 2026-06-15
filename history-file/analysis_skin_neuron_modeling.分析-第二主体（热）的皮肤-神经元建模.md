# 分析：第二主体（热）的皮肤-神经元建模

> 2026-06-11 | 回答架构问题 + 建模分析

---

## 1. 时空梯度如何与运动势/时空测度联系

### 现有数学框架

```
运动判别的三个测度：
  时间测度: temporal_measure[ax] = irr_afferent._activation_ema   (AC 分量)
  空间测度: spatial_measure[ax] = reg_afferent._activation_ema    (DC 分量)
  运动势:   ν = dK/dt = Σ m·v_i·a_i                              (动能变化率)
```

### 热感受的对应测度

| 运动 (已有) | 热 (待建) | 物理对应 |
|---|---|---|
| 时间测度: dω/dt (角加速度变化) | **dT/dt per patch** (温度变化率) | 都是 AC 分量 |
| 空间测度: θ (静态倾斜) | **ΔT across patches** (空间温差) | 都是 DC 分量 |
| 运动势 ν = dK/dt | **热势 ν_th = dE_thermal/dt** (热能流入率) | 都是能量变化率 |

关键关系：

```
ν (运动势) 与 ν_th (热势) 的因果耦合：

  agent 向热源运动 → ν > 0 (加速)
                    → 前 patch T 升高, 后 patch T 不变
                    → ΔT_front-back > 0
                    → 同时 ν_th > 0 (热能流入增加)

  ν × ΔT 的相关性 = 「运动方向与热梯度方向一致」
  → 这就是 STDP 可以学到的信号
```

### 数学表达

定义热偏振度（类比运动偏振度 P_ν）：

```
P_th = max(|ΔT_i|) / Σ|ΔT_i|

P_th → 1: 热梯度高度定向（热源在一个明确方向）
P_th → 1/N: 均匀环境（无方向性）
```

可能的新守恒候选：

```
P_ν × P_th = const?  （运动越定向 ↔ 热感受越定向？）
```

需要实验验证，但数学结构是对称的。

---

## 2. 影子层与感受-行为抽象

### 影子层不需要修改

影子层预测 Column 输出。当热信号进入 Column 后，shadow **自动** 开始预测热相关的 Column 活动。

```
Before (只有运动):
  Column_yaw 活动 → Shadow 预测 → 误差 → DA

After (加入热):
  Column_yaw 活动 ─┐
  Column_therm 活动 ┤→ Shadow 预测 → 误差 → DA
                    │
  新的预测误差来源：agent 移动时 Column_therm 突然变化
                    → Shadow 未预期到
                    → DA 释放
                    → STDP 强化 「这个运动带来了热变化」
```

### MotionState 可以承载热状态

MotionState 是结构化状态对象，不是语义标签。加入热测度是合法的：

```python
# 已有：
motion_potential: float     # ν = dK/dt
temporal_measure: Dict      # per-axis AC
spatial_measure: Dict       # per-axis DC

# 可加入：
thermal_gradient: List[float]   # [ΔT_front-back, ΔT_left-right, ΔT_top-bottom]
thermal_potential: float        # ν_th = dE_thermal/dt
thermal_polarization: float    # P_th
```

这些不是语义标签（没有 "food_direction" 或 "escape_needed"），是物理测量值。

---

## 3. 环流记忆是否阻塞

**不阻塞。** 原因：

- N.13（环流记忆）是关于长时间尺度（进化级）的 ρ 比例存储
- B.02-B.04（感受链 + DA 闭环）只需要 **当前步** 的 ρ_deviation → DA
- 当前的 CirculationProportionCircuit 已经能实时计算 deviation
- 没有长期记忆，系统仍然能学习「刚才靠近热源，能量增加了」—— 这是几十步级别的 STDP 窗口，不需要进化记忆

环流记忆影响的是：「在上一个生命周期中，哪种 ρ 比例是最优的」。这是 Phase 3+ 问题。

---

## 4. 时间耦合器档案

时间耦合器在皮肤感受中有特殊意义：

| 层间跨越 | 时间尺度差异 | 耦合器作用 |
|---|---|---|
| Aff→Enc (运动) | ~5ms → ~50ms | 桥接 spike 与膜电位 |
| **Patch→感受神经元 (热)** | **~1s → ~50ms** | 桥接缓慢温度变化与快速神经响应 |

热的时间尺度 (~1s 温度扩散) 比机械振动 (~5ms) 慢 **200 倍**。感受链需要专门的耦合器参数：

```
运动耦合器: τ_couple = C(1.0) × R(2.0) = 2.0 (2ms 级)
热感受耦合器: τ_couple = C(50.0) × R(2.0) = 100.0 (100ms 级)
```

> **建议**: 当 B.02 实施时，为 Patch→感受神经元 bundle 配置长 τ 的 TemporalCoupler。不需要新组件——参数不同就行。值得在时间耦合器文档中补充热感受模式的参数推导。

---

## 5. 皮肤与感受神经元的对应关系

### 生物学参照

| 受体类型 | 密度 | 感受域 | 项目对应 |
|---|---|---|---|
| 温度受体 (TRPV1/TRPM8) | 0.4-5/cm² | ~1cm² | 1 patch → 1 thermoreceptor |
| 机械受体 (Meissner) | ~40/mm² | ~1mm² | 不适用于热主体 |
| 痛觉受体 (free endings) | ~200/cm² | ~0.5mm² | 1 patch → 1 nociceptor |

### 皮肤→神经元映射

**压电方式是正确的物理类比。**

生物中温度受体使用 TRP 离子通道——温度改变蛋白构象→通道开放→离子流入→去极化。这在功能上等价于压电效应：

```
压电: 机械应力 → 电荷分离 → 电压
TRP:  温度变化 → 构象改变 → 离子流 → 电压
```

项目中已有完美的类比：**MET 元件**。MET 就是机械-电转换器（mechanotransducer）。热感受可以用同样的 NeuronConfig 模式，只改物理参数：

```python
def _thermoreceptor_config(patch_id: str) -> NeuronConfig:
    """热感受神经元 — 类 MET 但时间常数更长。
    
    BIO: DRG neuron expressing TRPV1 (>43°C) or TRPM8 (<25°C)
    EE: 压电式热-电转换器，τ >> MET
    """
    return NeuronConfig(
        neuron_id=f"thermo_{patch_id}",
        capacitance=5.0,       # MET 的 5 倍 — 温度变化慢
        r_leak=20.0,           # τ = 100ms (vs MET τ=5ms)
        channels=[
            ChannelConfig(
                name="trp",         # 类比 MET 通道
                v_threshold=0.01,   # 低阈值 — 对温差敏感
                gm=1.0,
                tau_gate=0.05,      # 50ms 门控 (MET=0ms)
                reversal=0.5,
                sign=1.0,
            ),
        ],
        ...
    )
```

### 多少体积 → 一个神经元？

最小配置：

```
体表面积 = 4πr² (假设球体 r=1)
4 patch → 每 patch ≈ π 面积单位
每 patch → 1 thermoreceptor + 1 nociceptor = 2 神经元

总计: 4 patch × 2 = 8 感受神经元
```

扩展配置（如果需要更高分辨率）：

```
32 patch (足球形分割) × 2 = 64 感受神经元
— 分辨率 ~11.25° → 可区分 32 个方向
```

**带宽 = patch 数。** 每个 patch 的代谢成本是恒定的（EnergyStore 持续扣款），所以最大带宽由 P_inflow 限制。

---

## 6. 直接到交汇层 vs 经过特殊区域？

### 这是最深的架构问题

生物中，皮肤感受不直接到大脑皮层。中间有两级处理：

```
皮肤受体 → DRG (背根神经节) → 脊髓背角 → 丘脑 VPL → 体感皮层 S1
              ↓                   ↓             ↓
         一级感受神经元       空间-时间滤波     特征提取
         (无计算，只传递)      (体感图谱)       (跨模态)
```

### 脊髓背角/丘脑 = 体感图谱层

这个中间层做的关键事情：

1. **空间拓扑保持**：相邻皮肤 patch 的信号投射到相邻神经元
2. **感受域整合**：多个 patch 汇聚到一个二级神经元（中心-环绕拮抗）
3. **时序编码**：不同传导速度的纤维到达同一目标，产生时间间隔 → 距离编码

**这个层级的结构就是你说的「靠这个区域的结构来赋值元与元之间系统内时序和空间」。**

### 在项目中的对应

```
                       前庭链                         热感受链
                  ┌─────────────┐              ┌──────────────┐
Layer 1 (受体):    MET                          Thermoreceptor
Layer 2 (放大):    HairCell                     [可能不需要]
Layer 3 (释放):    Ca²⁺ release                 [可能不需要]
Layer 4 (编码):    Afferent (reg/irr)           SomatoRelay ← 新层级
                  └──────┬──────┘              └──────┬───────┘
                         ↓                            ↓
Layer 5 (汇聚):        Encoding ←──────────────→ Encoding
Layer 6 (整合):        Column
Layer 7 (输出):        Motor
```

### SomatoRelay：体感中继层

这是一个新的神经层级（对应脊髓背角），功能：

1. **接收**：每个 patch 的 thermoreceptor 输出
2. **空间滤波**：相邻 patch 做中心-环绕（类似 Column 间的 lateral inhibition）
3. **时序编码**：不同 patch 的信号到达时间差 → 编码空间关系

```python
# 结构设想
class SomatoRelay:
    """体感中继层 — 脊髓背角类比。
    
    不做语义计算（不知道"左"和"右"）。
    只做空间滤波：
      - 中心兴奋 + 环绕抑制 → 增强梯度
      - 时间延迟差 → 隐式距离编码
    """
    neurons: Dict[str, Neuron]  # 每 patch 一个中继神经元
    lateral_inhibition: InhibitorySynapse  # 相邻 patch 互抑
```

### 隐式流形

你提到的「隐式四维/三维流形」——这正是 SomatoRelay 的涌现性质：

```
SomatoRelay 的连接结构：
  Patch_front → Relay_front ─── lateral inhibition ──→ Relay_back
  Patch_left  → Relay_left  ─── lateral inhibition ──→ Relay_right

连接拓扑 = 体表的邻接图
邻接图 = 2D 流形（球面拓扑）
加上时间维度 = 3D 流形
加上温度模态 = 4D 流形
```

**外部观测者看到的**：SomatoRelay 的权重矩阵隐式编码了一个 2D 球面流形（体表），嵌入在 N 维神经活动空间中。系统不知道这个流形存在，但它的结构就是流形。

这与 ultrametric space（已有的数学框架）可以关联：

```
体表 patch 之间的 ultrametric 距离 d_U(patch_i, patch_j)
  = 沿 SomatoRelay 连接的最短路径上的最大权重差
  ≈ 体表的测地线距离（当拓扑保持时）
```

---

## 7. 架构总结图

```
                    第一主体 (运动)                    第二主体 (热)
                    ─────────────                    ──────────────
                    
外部世界:           惯性力 (6 轴)                    温度场 T(x,y,z)
                        ↓                                 ↓
转导器:             MET → HairCell → Release          Patch → Thermoreceptor
                        ↓                                 ↓
编码器:             Afferent (reg/irr)                SomatoRelay (空间滤波)
                        ↓                                 ↓
                    ┌───────────────────────────────────────┐
交汇层:             │        Encoding (per-axis)           │
                    │        Column (integration)          │
                    │        Shadow (prediction)           │
                    │        DA (prediction error)         │
                    └───────────────┬───────────────────────┘
                                    ↓
输出:                           Motor → Muscle → Body
                                                    ↓
                                              位置变化 → 新的温度/惯性力输入
                                                    ↑
                                              闭环 ──┘
```

---

## 8. 开放设计决策

1. **SomatoRelay 是否需要 reg/irr 分化？**
   - 温度变化缓慢 → 可能只需要 DC (tonic) 通道
   - 但 nociception 是快事件 → 需要 AC (phasic)
   - 建议：thermoreceptor → reg only; nociceptor → irr only

2. **SomatoRelay 的 lateral inhibition 参数？**
   - 强抑制 → 高梯度增强 → 高空间分辨率，但丢失弱信号
   - 弱抑制 → 保留弱信号，但梯度模糊
   - 可以从 Column 的 lateral inhibition (gain=0.05) 开始

3. **热源分化：温度阈值？**
   - T < T_comfort (~35°C): 正常代谢温度
   - T_comfort < T < T_noci (~43°C): 温暖，营养性
   - T > T_noci: 伤害性
   - 阈值由 nociceptor 的 v_threshold 决定（物理参数，不是标签）

4. **与 Binding Layer 的交互**
   - Binding 做 C(n,2) 两两关联
   - 加入热轴后：C(8,2) = 28 binding cells (from 21)
   - 新的 binding：yaw × therm_front, oto_x × therm_gradient...
   - 这些 binding 是方向学习的关键信号源

---

*此文档供架构决策使用。B.02 的具体实现取决于上述设计选择。*
