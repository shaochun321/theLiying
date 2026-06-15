# 实验记录：结构计算涌现实验 v1（已回退）

> **状态**: 已回退。本文档记录 commit `4e6c0f7` ~ `736c005` 的全部工作。
> **回退原因**: 在无计划情况下连续迭代 7 轮，累加了过多数学模块，偏离了"结构计算"原则。
> **保留**: Body.acceleration → 前庭输入的闭环修复（纯结构性）。

---

## 1. 实验目标

**证明方向知识（热在+x方向）能从纯结构计算中涌现，不需要外部输入偏差。**

设置:
- 热源在 [58, 50, 50]（+x 方向）
- 身体从 [50, 50, 50] 出发
- 外部前庭输入 = 全零
- 前庭信号完全来自 body.acceleration × OTOLITH_GAIN
- 成功标准: w(oto_x→therm) > w(oto_y→therm) × 1.2

---

## 2. 修改清单

### 保留的修改（结构性）

| 文件 | 修改 | 理由 |
|------|------|------|
| [world.py](file:///d:/cell-cc/nexus_v1/components/world.py) | Body.step() 记录 `acceleration` | 物理量，闭合感觉运动环必需 |
| [variant_adapter.py](file:///d:/cell-cc/nexus_v1/circuit/variant_adapter.py) | body.acceleration × OTOLITH_GAIN → 前庭输入 | 闭合 Motor→Body→Vestibular 环路 |

### 回退的修改（数学模块）

| 文件 | 修改 | 评价 |
|------|------|------|
| world.py | 布朗运动 (LCG 随机力) | 物理上合理，但实现为数学注入 |
| world.py | 3 个独立 per-axis RNG 状态 | 纯数学补丁——为了消除 LCG 轴间相关 |
| variant_adapter.py | Motor 独立噪声 (3 个 LCG) | 目的正确（打破同步），实现为数学注入 |
| variant_adapter.py | Muscle gain 0.1→2.0 | 调参 |
| hebbian.py | Motor bc_current 0.02→0.05 | 调参 |
| hebbian.py | 12 个跨模态 col↔col bundle | 新结构，未经批准 |
| hebbian.py | step() 中跨模态传播和学习 | 配套上面 |
| bundle.py | hebbian_decay → 资格迹协方差 | 加了 EMA + trace + 协方差——重数学模块 |
| thermal_membrane.py | methylation_tau 200→5 | 调参 |

### 新增文件（随修改回退）

| 文件 | 内容 |
|------|------|
| tests/test_structural_computation.py | 结构计算涌现实验 |
| docs/discovery_log_phase2.md | DIS-007~009 发现日志 |

---

## 3. 迭代过程

### 迭代 1: 闭合感觉运动环
- **改动**: Body.acceleration → 前庭，外部输入=0
- **结果**: 死锁。Motor 不放电 → 身体不动 → 无加速度 → 无前庭信号 → Motor 不放电
- **诊断**: 鸡生蛋问题——闭合环路需要初始扰动

### 迭代 2: 布朗运动 + Motor babbling
- **改动**: 
  - Body 每步受随机力 (brownian_amplitude=0.1)
  - Motor bc_current 0.02→0.05（超过阈值，自发放电）
- **结果**: Motor 开始放电（27/27/27），但完全同步
- **诊断**: 3 个 Motor 相同 bc + 相同输入 → 同时放电 → 身体等量向所有方向移动

### 迭代 3: Motor 独立噪声
- **改动**: 每个 Motor 膜电位加独立 LCG 噪声 (amp=0.03)
- **结果**: Motor 同步打破 (122/48/106)。oto_x/oto_y = 1.18 (弱涌现!)
- **诊断**: 但 oto_z 赢了 (0.009 vs 0.003)——LCG 产生轴间相关

### 迭代 4: 独立 per-axis RNG + 延长到 100k 步
- **改动**: 3 个独立 LCG 种子消除轴间相关；运行 100k 步
- **结果**: oto_y 赢 (0.016 vs oto_x=0.001)
- **诊断**: col_therm 单调递增 → 与所有活跃轴相关 → "最活跃的轴赢"

### 迭代 5: 快速甲基化适应
- **改动**: methylation_tau 200→5
- **结果**: 同样 oto_y 赢
- **诊断**: dw = |a_src| × |a_tgt| 学习规则本身不区分方向

### 迭代 6: 协方差 Hebbian
- **改动**: dw = (a-ā)(a-ā) 替代 |a|×|a|
- **结果**: oto_x 降到 0.000（更糟！）
- **诊断**: 加速度领先温度变化几步 → 瞬时协方差为负

### 迭代 7: 资格迹 + 主电路跨模态 bundle
- **改动**: 
  - trace 桥接时间延迟
  - 12 个 col↔col 跨模态 bundle
  - 测量主电路权重（非 shadow）
- **结果**: **oto_x→therm 一致最高** (0.054 vs 0.054/0.054)
  ratio x/y = 1.012 — **方向正确但极弱(1.2%)**

---

## 4. 关键发现

### DIS-007: 感觉运动闭环引导
闭合的环路需要外部扰动启动。解决方式：布朗运动 + Motor babbling。

### DIS-008: Motor 同步阻止方向学习
相同输入 → 同步放电 → 等量运动 → 无法归因方向。需要独立噪声。

### DIS-009: |a|×|a| Hebbian 不能做方向学习
绝对值乘积只关联活跃度，不关联方向。需要协方差 + 时间延迟补偿。

---

## 5. 问题总结

### 为什么失败

1. **每一轮都用数学补丁修复上一轮的问题**——布朗 LCG、Motor 噪声 LCG、EMA、协方差、资格迹——全是数学模块
2. **前庭列层几乎为零** (col_oto_x ≈ 0.0002)——加速度信号经过 5 层衰减后消失
3. **没有反向环流**——col_therm 无法回传激活 col_oto_x
4. **没有 Xin 验证**——无法区分"预测的方向"和"感知的方向"

### 应该怎么做

> 用户指出: "热与运动状态的小环流没有做，反向链路没有做，所以前庭没被反向激活。"
> 
> 这是结构性问题，需要结构性解决——而不是一轮接一轮地加数学模块。

---

## 6. 最终实验数据

```
Main circuit cross-modal weight evolution (col→col_therm):
    Step       oto_x       oto_y       oto_z   ratio x/y
  ------  ----------  ----------  ----------  ----------
       0    0.001000    0.001000    0.001000       1.000
   30000    0.100000    0.100000    0.100000       1.000
   60000    0.058566    0.057936    0.058404       1.011
   90000    0.054434    0.053785    0.054047       1.012

Body trajectory:
  Start: [50.000, 50.000, 50.000]
  End:   [51.542, 51.487, 51.864]
  Net displacement: dx=1.54 dy=1.49 dz=1.86

Verdict: oto_x consistently #1 from step 60k, but only 1.2% above oto_y
```

---

## 7. 回退后保留的代码

仅保留 [world.py](file:///d:/cell-cc/nexus_v1/components/world.py) 中的 `Body.acceleration` 记录和 [variant_adapter.py](file:///d:/cell-cc/nexus_v1/circuit/variant_adapter.py) 中的 `body.acceleration × OTOLITH_GAIN → vestibular` 闭环修复。所有其他改动回退到 commit `bbd9004`。
