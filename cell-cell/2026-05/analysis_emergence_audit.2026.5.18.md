# 涌现基础审计：什么是真的，什么是假的

## 当前因果链

```
源 → 介质传播 → 梯度读取
                    ↓
              compute_reflex()     ← ⚠️ 硬编码!
                    ↓
              reflex motor force
                    ↓
       CPG + circuit_motor + reflex + babbling
                    ↓
              粒子物理引擎
                    ↓
              位置更新 → sensory dict
                    ↓
              HebbianCircuit.step()
                    ↓
              circuit_motor (下一 tick)
```

## 问题诊断

### ⛔ 硬编码的部分

```python
# compute_reflex(), 第 498-517 行:
if intensity > AVOIDANCE_THRESHOLD:
    scale = -TAXIS_GAIN * min(intensity - AVOIDANCE_THRESHOLD, 1.0)
else:
    scale = TAXIS_GAIN * intensity / AVOIDANCE_THRESHOLD
motor["move_x"] += scale * ux
```

> [!CAUTION]
> **这不是涌现 — 这是直接写死的 "if 强度高就跑, 强度低就靠近"。**
>
> 整个 taxis 行为的核心决策来自这 6 行代码，不来自：
> - ❌ HH 离子通道 (spike 没有参与决策)
> - ❌ 前庭系统 (输出到 sensory 但不影响 motor)
> - ❌ 本体感觉 (同上)
> - ❌ HebbianCircuit (其 motor 输出被 reflex 压过)
> - ❌ 介质物理 (只改变了 gradient 的数值，不改变决策逻辑)

### ✅ 真正涌现的部分

| 现象 | 涌现来源 | 是否真涌现 |
|---|---|---|
| 平衡距离 L* | 梯度力 vs CPG+babbling | ✅ 但依赖硬编码 reflex |
| 穿透深度 L_pen | 材料三元组 (m,k,γ) | ✅ 纯物理涌现 |
| AP 波形 | HH 方程 Na⁺/K⁺ | ✅ 纯物理涌现 |
| 前庭信号 | 粒子运动 → ω, a | ✅ 纯物理涌现 |
| 本体感觉 | 弹簧角度/应力 | ✅ 纯物理涌现 |
| **偏好排序** | **reflex × gradient** | **⚠️ 半涌现** |

> [!WARNING]
> **偏好排序是"半涌现"**：L* 的数值从物理涌现，但 agent "决定" 趋向源这件事是硬编码的。真正的涌现应该是 agent **自己发现** 趋向源有利。

---

## 涌现的必要条件

真正的涌现需要闭环，且环中**没有硬编码的决策**：

```
     感知 (物理)
       ↓
     神经处理 (HH spike 网络)     ← 当前断开!
       ↓
     运动输出 (从 spike → force)   ← 当前断开!
       ↓
     物理后果 (身体在介质中运动)
       ↓
     新的感知 (物理)
       ↓
     ...循环...
```

### 当前系统缺少的 3 个环节

#### 缺口 1: 感知 → 神经

HH 神经元的输入来自 `α·stress + β·displacement`（机械应力），**不来自外部信号源**。

介质读取的 gradient 和 intensity 直接送入 `compute_reflex()`，绕过了神经网络。

#### 缺口 2: 神经 → 运动

HH spike 不产生运动。spike 只传播为 `I_syn`（突触电流到邻居），没有"运动神经元"将 spike 转化为力。

运动来自 `compute_reflex()` + `HebbianCircuit.step()`，后者是独立的线性映射，不连接 HH。

#### 缺口 3: 成本信号

agent 没有"不舒服"或"能量低"的信号来驱动学习。STDP 会修改权重，但修改方向没有目标——因为系统中没有 reward/cost。

---

## 诚实的涌现路径评估

### 方案 A: 在当前架构上加 STDP

```
效果: STDP 修改 syn_weight
      → 改变 spike 传播模式
      → 改变 sensory["synchrony_H"] 等熵通道
      → 通过 HebbianCircuit 间接影响 motor
      
涌现程度: ★☆☆☆☆ (极弱)
原因: reflex 仍然主导 motor，STDP 效应被淹没
```

### 方案 B: 移除 reflex，让 circuit 全权负责

```
效果: 删除 compute_reflex()
      → motor 只来自 HebbianCircuit
      → circuit 必须学会 gradient → motor 映射
      
涌现程度: ★★★☆☆ (中等)
问题: HebbianCircuit 是线性的，学不会非线性 taxis
      而且 HebbianCircuit 的输入是 sensory dict (59 通道)
      不是 spike — 还是断开的
```

### 方案 C: 构建 "感觉→中间→运动" 三层 spike 网络

```
感觉神经元 (接收 gradient/intensity)
    ↓ HH spike
中间神经元 (整合, 决策)
    ↓ HH spike + STDP
运动神经元 (spike → 力)
    ↓
粒子运动 → 新的 gradient

涌现程度: ★★★★★ (真涌现)
代价: 需要重构粒子系统的角色
```

---

## 我的建议

> [!IMPORTANT]
> **不要在当前架构上硬加 STDP。** 它不会产生有意义的涌现。
>
> 正确的路径是 **先闭合感觉-运动回路**，再加 STDP。

### 闭合回路的最小改动

不需要重写整个系统。可以在现有 30 粒子中**分化出功能角色**：

```
30 个粒子:
  ├─ 6 个 "感觉粒子" (表面, 接收 gradient → I_ext)
  ├─ 18 个 "中间粒子" (内部, spike 整合)
  └─ 6 个 "运动粒子" (表面, spike rate → 力)

感觉粒子: I_ext = α_sens · intensity + β_sens · gradient
           (物理来源: 介质能量场直接激励表面粒子)

运动粒子: 如果最近 τ 内 spike ≥ 阈值 → 产生定向力
           (物理来源: 肌动蛋白收缩 ← 钙离子信号)

中间粒子: 纯 HH 整合, STDP 在这里起作用
```

### 为什么这是物理的

- 感觉粒子在"体表"→ 直接暴露在介质能量场中 → **物理上合理**
- 运动粒子在"体表"→ spike 驱动收缩 → **物理上合理** (纤毛/鞭毛)
- 中间粒子在"体内"→ 只接收突触信号 → **物理上合理** (中间神经元)
- STDP 在中间层 → 因果 spike 链被增强 → **涌现出 taxis 策略**

### 顺序

```
Step 1: 粒子功能分化 (感觉/中间/运动)
Step 2: 感觉耦合 (介质 → I_ext for 感觉粒子)
Step 3: 运动耦合 (spike rate → 力 for 运动粒子)
Step 4: 移除 compute_reflex()
Step 5: 验证: agent 能否通过 spike 网络自发趋向源?
Step 6: 加 STDP → 验证: taxis 是否改善?
```
