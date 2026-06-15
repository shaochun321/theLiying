# 会话总结 — 2026-05-24

## 完成的工作

### 1. FIX-017: Motor PowerRail 崩溃修复
- **根因**: Col→Motor 电流 1437 vs 允许上限 6.67（61× 过载）
- **数学建模**: `I_max = (VDD×E/V_th - 1)/R_s = 6.67`
- **修复**: gain 3.0→0.1, w_max 1.0→0.5, threshold 0.3→0.2, bc_current 加入
- **发现**: homeostasis 机制在运行时覆盖 gain（`_base_col_mot_gain` 硬编码为 3.0）
- **结果**: Motor 放电 1131 次/20k步，闭环完全激活

### 2. 热趋性实验 (50k 步)
- 身体向热源靠近 0.20 单位 (15.0→14.8)
- **关键发现**: 运动无方向选择性 (33.3%/33.3%/33.3%)
- 暴露了热膜 6 方向簇的设计缺陷

### 3. 热膜重构: 6 方向簇 → 1 标量传感器
- **核心洞察**: 温度是标量场，一个点上不可能测方向梯度
- **生物依据**: C. elegans 用 1 个 AFD 神经元 + 时间导数实现热趋性
- **设计**: 方向信息从 运动×热变化 的跨模态 Hebbian 学习涌现

### 4. FIX-018: 跨模态 Hebbian+decay 学习规则
- **问题**: BCM 竞争淘汰杀死最强跨模态关联（反直觉!）
- **原因**: BCM θ 由目标神经元总活动设定（被轴内输入主导），跨模态信号微弱
- **修复**: cross_axis 束用 `dw = η|a_src||a_tgt| - λw`（无竞争 θ）
- **结果**: w(oto_x,therm)/w(oto_y,therm) = **1.49×** → 方向学习成功!

## 核心里程碑

```
系统从纯标量热信号 + 运动方向相关性中
涌现出了"热在 x 方向"的空间知识。

= 没有方向性热传感器
= 没有预编程的方向偏好
= 纯粹从经验学习中产生

这验证了 C-004 的核心思想:
  "用自身为尺度丈量世界"
```

## 修改的文件

| 文件 | 变更 |
|------|------|
| [hebbian.py](file:///d:/cell-cc/nexus_v1/circuit/hebbian.py) | FIX-017: gain/threshold/bc_current/homeostasis 同步修复 |
| [chain.py](file:///d:/cell-cc/nexus_v1/vestibular/chain.py) | FIX-017: Afferent bc_current + VR rate |
| [thermal_membrane.py](file:///d:/cell-cc/nexus_v1/components/thermal_membrane.py) | 6 方向簇 → 1 标量传感器 |
| [bundle.py](file:///d:/cell-cc/nexus_v1/circuit/bundle.py) | FIX-018: hebbian_decay 学习规则 |

## 当前架构状态

```
闭环信号流:
  Motor(1096 spikes) → Muscle(1.13J) → Body(+0.18u) → World
      → ThermalMembrane(1标量, dT/dt) → Encoding → Column → Motor

学习系统:
  轴内: BCM (竞争修剪, 选择性强化) ← 不变
  跨轴: Hebbian+decay (关联学习, 方向涌现) ← NEW
  PNN: 发育性冻结 ← 不变

跨模态知识:
  w(oto_x, therm) = 0.0037  ← "x 方向有热"
  w(oto_y, therm) = 0.0025  ← 对照
  ratio = 1.49×             ← 方向学习!
```
