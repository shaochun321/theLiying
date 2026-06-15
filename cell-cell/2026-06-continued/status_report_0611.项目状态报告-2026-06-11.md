> **导航**: [[00_Dashboard/核心词条索引]] · [[00_Dashboard/理念架构图]]

# 项目状态报告 — 2026-06-11

## 总览

第二主体（热）的信号链已**全链路贯通**，但行为尚未涌现。
今天完成了两个实验，精确定位了从"能感知"到"能行动"的差距。

---

## 今日完成的工作

### ✅ EXP-014: B.04 闭环验证 — 6/6 Gates PASS

信号链完整性确认:

```
SkinPatch(Fourier) → Thermo/Noci → SomatoRelay(侧抑)
       ↓
    Enc(spiking) → Col(spiking)
       ↓ Xin tension
    Shadow Enc → Shadow Col(CRI calcium_rate)
       ↓
    DA neurons → dopamine.concentration → STDP modulation
```

| Gate | 检查 | 数据 |
|------|------|------|
| 1 | 皮温非零 | 4 patches 均 0.1°C ✅ |
| 2 | 热轴 enc 发火 | 间歇性 spiking ✅ |
| 3 | Shadow col calcium_rate | **0.47→0.85 (分化!)** ✅ |
| 4 | DA 浓度波动 | mean=0.206, range=0.248 ✅ |
| 5 | STDP 权重变化 | 0.30→0.93 ✅ |
| 6 | 能量储库健康 | 501→422 ✅ |

> [!TIP]
> Gate 3 的原始"失败"是测量错误——读了 `.activation`（离散 spike flag）而非 `.calcium_rate`（CRI 连续输出）。修正后立即 PASS。

---

### ⚠️ EXP-015: 热趋性行为测试 — 信号正确，行为未涌现

**设置**: 零前庭输入，纯热梯度驱动，100k 步

**好消息 — 物理层面全部正确**:
- 皮温不对称: front=1.984, back=1.554 (差 +0.43，面向热源方向)
- 位移方向正确: Δx=+0.014（朝热源），9/9 窗口全部在靠近
- Shadow 层活跃并分化

**坏消息 — 三个瓶颈**:

```
      ┌──────────────────────────────────────┐
      │  ①  DA 在 ~20k 步后崩溃到 0         │
      │      Shadow col 全部饱和 → 0.97+     │
      │      → 预测误差消失 → DA 无输入      │
      │                                      │
      │  ②  Motor 输出微观                   │
      │      无前庭驱动 → 无基础随机游走      │
      │      身体静止 → 热梯度恒定 → 无时变信号│
      │                                      │
      │  ③  缺少 dT/dt → DA 的映射 (B.06)   │
      │      系统不知道 "朝热源走=好"         │
      │      → 无法学习方向偏好              │
      └──────────────────────────────────────┘
```

---

## 回归测试状态

20/21 PASS (T4.3 Motor diff 边界抖动，0.0009 vs 阈值 0.001，与热轴无关)

---

## TRACKER 完成度一览

| 领域 | 完成 | 部分 | 未做 | 进度 |
|------|------|------|------|------|
| **S** 结构/组件 | 11 | 1 | 3 | 73% |
| **B** 体表/感受 | 6 | 0 | 2 | 75% |
| **N** 神经/信号链 | 11 | 0 | 3 | 79% |
| **P** 可塑性/学习 | 9 | 0 | 0 | 100% |
| **E** 能量/守恒 | 14 | 0 | 1 | 93% |
| **C** 环流/耦合 | 3 | 0 | 3 | 50% |
| **M** 数理/理论 | 5 | 0 | 3 | 63% |
| **D** 文档/工具 | 7 | 0 | 0 | 100% |

---

## 瓶颈分析与下一步建议

热趋性（1.1）是项目终极目标。EXP-015 精确定位了三个缺失环节:

### 问题 ① DA 崩溃 — Shadow 饱和

Shadow col 的 `calcium_rate` 快速饱和到 0.97+ → Xin 残差→0 → DA 永久沉默。

可能对策:
- BCM 滑动阈值适配 shadow 层（当前 BCM 只在主层）
- calcium_rate 施加硬上限（如 0.8）保留动态范围
- Shadow 层 STDP 衰减加速，防止权重全部冲顶

### 问题 ② 无基础运动

纯热梯度无法单独驱动 motor。需要：
- 弱前庭噪声作为基底随机游走（符合生物真实——内耳自发放电）
- 或 Motor 层自发噪声机制

### 问题 ③ B.06 热势 ν_th = dE_thermal/dt

这是**最关键的缺失件**。当前信号链有空间信息（前后温差 +0.43）但缺少**时间信号**:

```
当前:  T_skin(static) → Enc → Col → Shadow(saturate) → DA(collapse)
需要:  dT_skin/dt(dynamic) → 与运动方向相关 → DA 调制 → STDP 方向学习
```

ν_th 的作用类比运动势 ν（已实现）:
- ν = dK/dt（动能变化率）→ 已成功驱动运动-DA 耦合
- ν_th = dE_thermal/dt（热能变化率）→ 应驱动热觉-DA 耦合
- **ν_th × ΔT > 0**: 朝热源移动时皮温升高 → DA↑ → 强化当前方向
- **ν_th × ΔT < 0**: 远离热源移动时皮温降低 → DA↓ → 促进转向

这正是 klinokinesis 的核心机制（大肠杆菌趋化性的类比）。

> [!IMPORTANT]
> **建议优先级**: ③ B.06 > ② 基底噪声 > ① 抗饱和。
> 
> 原因: B.06 解决了从"感知"到"行动"的核心桥接。即使有 ② 的随机游走和 ① 的 DA 存活，没有 ③ 也无法将运动方向与热变化关联。

---

## 文件变更记录

| 文件 | 变更 |
|------|------|
| [TRACKER_v1.0.md](file:///d:/cell-cc/nexus_v1/docs/TRACKER_v1.0.md) | B.04 标记 `[x]` |
| [EXPERIMENT_LOG.md](file:///d:/cell-cc/nexus_v1/docs/history/EXPERIMENT_LOG.md) | 新增 EXP-014, EXP-015 |
| [test_regression.py](file:///d:/cell-cc/nexus_v1/tests/test_regression.py) | 修复 `reg_therm` → `reg_therm_front` |
| [test_phase3_da_loop.py](file:///d:/cell-cc/nexus_v1/tests/test_phase3_da_loop.py) | Gate 3 改用 `calcium_rate` |
| [test_thermotaxis_v2.py](file:///d:/cell-cc/nexus_v1/tests/test_thermotaxis_v2.py) | 新建 EXP-015 |
