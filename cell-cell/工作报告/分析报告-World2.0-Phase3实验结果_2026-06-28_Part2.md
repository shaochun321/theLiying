# 分析报告 — World 2.0 Phase 3 实验结果
## Part 2：根本原因分析与 Phase 4 建议

**日期：** 2026-06-28  
**关联：** 本文档是 Part 1 的续篇

---

## 5. 根本原因分析

### 5.1 STDP 对称死锁（核心失败）

**现象：** w_front 与 w_brake 几乎同步增长，100k 步时比值仅 **1.001**，双束同时饱和于 0.498。

**机制：** STDP 三因子规则为：
```
dw_ltp = eligibility_gain × E(t) × DA(t)
E(t)  ← 由 pre(therm_col) × post(move_x) 积累
DA(t) ← 能量增加时释放（fill 上升 → DA 脉冲）
```

问题在于 body 在步 60k 后稳定在 S1 正前方（yaw≈-3°，几乎面向 S1），以 Langevin 噪声在 S1 周围**双向振荡**：

```
向前振荡 → front 皮肤靠近 S1 → therm_front 激活 → fill↑ → DA↑ → front 束 E(t) 充电
向后振荡 → back 皮肤靠近 S1 → therm_back 激活 → fill↑ → DA↑ → brake 束 E(t) 充电
```

两个方向都是「接近 S1」→ 两个方向都触发 DA。STDP 无从区分「朝向」与「背向」，因为两者都导致相同的奖励信号。

**这是物理架构的内在约束**：STDP 在单点振荡场景下无法学习方向性，除非 body 能持续**单向**接近热源。

### 5.2 eligibility_gain 过大导致过早饱和

Phase 3 将 eligibility_gain 从 1e-5 提升至 **3e-5**，目的是加速学习。实际效果：

| 步数 | w_front | w_brake | 增速/10k步 |
|------|---------|---------|-----------|
| 10k→20k | 0.010→0.037 | 0.010→0.043 | +0.027/+0.033 |
| 20k→30k | 0.037→0.156 | 0.043→0.198 | +0.119/+0.155 |
| 30k→50k | 0.156→0.384 | 0.198→0.409 | 快速上升 |
| 90k→100k | 0.485→0.490 | 0.485→0.490 | 趋于停止 |

权重在约 **100k 步内从 0.01 饱和至 0.49**，速度是 Phase 2（70k 步内从 0.010 到 0.013）的 **30 倍以上**。饱和速度远快于方向性分化所需时间：STDP 来不及建立差异，就已经双束同时打到天花板。

**关键判断**：eligibility_gain=3e-5 + weight_max=0.5 的组合创造了过大的学习空间（峰值积累速率），在方向选择性出现之前就完成了饱和。

### 5.3 能量供给距离错配

即使 eta=0.50，body 在 dist_surface≈19-20 时的实测 intake 约为 0.001-0.002/step，与代谢消耗相当或略低。能量正平衡窗口：

| 距离区间 | intake/s（Phase 3 实测） | 代谢消耗/s（估计） | 净收支 |
|---------|------------------------|------------------|-------|
| dist_surf < 15 | — (未达到) | ~0.001 | 未知 |
| dist_surf 15-20 | 0.001-0.003 | ~0.001 | ≈ 平衡 |
| dist_surf 20-25 | 0.0004-0.002 | ~0.001 | 轻微负 |

早期（10k-60k）fill 能上升至 0.73，是因为 body 在 S2/S3 叠加场中，温度场更强。一旦 body 定居于 S1 附近（单源场），供能减弱，fill 单调下降。

**结论**：eta=0.50 在多源叠加场中有效，在单源 dist_surface=20 时处于临界平衡，无法抵御饱和后 STDP 行为驱动力消失带来的轻微负收支。

### 5.4 附录：ThermalMouth 能量簿记 Bug

`thermal_mouth.py` 固定从 `cylindrical_sources[0]`（S1）扣除能量：
```python
for src in world.cylindrical_sources:
    if src.alive:
        src.absorb(total_heat_flux)
        break  # ← 永远只扣 S1
```

表现：E2/E3 在 270k 步全程均保持 8000，E1 降至 7102。  
影响：物理温度场计算（`temperature_at()`）正确（对所有源求和），STDP 学习不受影响。仅能量簿记失真。需在 Phase 4 修复。

---

## 6. P3-FIX-04 风向标评估

K_VANE=0.001 确实阻止了 Phase 2 中的 yaw 单调发散（Phase 2 到 250k 时 yaw=97°，Phase 3 同等步数时 yaw=-45°）。但其贡献有限：
- 步 0-100k：yaw 基本维持在 ±6° 以内（正常工作）
- 步 100k 后：STDP 饱和，行为驱动消失，yaw 开始慢速漂移（270k 时 -86°）

**结论**：K_VANE=0.001 在 STDP 活跃阶段有效地抑制了 yaw 发散；但 STDP 饱和是更根本的失败原因，并非 yaw 问题导致实验失败。风向标机制本身运作正常，问题在 STDP 层。

---

## 7. Phase 2 vs Phase 3 对比

| 指标 | Phase 2 结果 | Phase 3 结果 | 改进/退步 |
|------|-------------|-------------|---------|
| fill 峰值 | 0.52 | **0.733** | +41%（eta 提升有效） |
| fill 归零时间 | 250k | **160k** | 更早（STDP 饱和后行为丧失更快） |
| w_front/w_brake 比值 | 1.25（合理分化） | **1.001**（死锁） | **退步** |
| 权重饱和速度 | 未饱和（0.013 at 70k） | **100k 步饱和** | eligibility_gain 过大 |
| approach_count | —（未计量） | 0 | 无改善 |
| dist_surface 最近点 | 14.65（Phase 2 w/ k_conv） | 17.65 | 略差 |
| yaw 控制 | 97° @ 250k | **-86° @ 270k** | 改善（风向标有效） |
| 能量簿记 | 单源正确 | **多源 bug（只扣 S1）** | 新问题 |

---

## 8. Phase 4 建议

三个 Phase 的实验积累揭示了 STDP 热趋向学习的根本约束：**body 必须能从单一方向、持续地接近热源，STDP 才能建立方向性权重差异**。任何导致 front/back 对称热暴露的动态（振荡、穿越）都会锁死学习。

### 8.1 必须解决的核心问题

**P4-CORE-01：消除 STDP 对称死锁**

三个可行路径，可组合：

| 路径 | 方案 | 原理 |
|------|------|------|
| A | 大幅降低 eligibility_gain（如 5e-6） | 延长学习时间，使方向选择性在饱和前出现 |
| B | 非对称初始权重（w_front=0.05，w_brake=0.001） | 给方向学习一个物理初始偏置 |
| C | 强制单向接近相（前 50k 步固定 yaw 指向热源） | 预热 STDP 方向偏置后再释放 yaw |

**推荐 A+B 组合**：无需修改母代码，符合物理原则（B 类似突触修剪的初始选择性）。

**P4-CORE-02：修复 ThermalMouth 能量簿记**

```python
# 修复：从最近的活跃源扣除能量
def _nearest_alive_source(world, body):
    best, best_d = None, float('inf')
    for s in world.cylindrical_sources:
        if s.alive:
            d = dist_to_surface(body.position, s)
            if d < best_d:
                best_d, best = d, s
    return best

# 替换原 break 逻辑
src = _nearest_alive_source(world, body)
if src: src.absorb(total_heat_flux)
```

但这是母代码（`thermal_mouth.py`）修改，需评估是否符合 RULES.md。替代方案：在实验脚本中 monkeypatch。

**P4-CORE-03：能量供给阈值确认**

在 Phase 4 之前用静态实验确认：body 固定在 dist_surface=10/12/15，测量 eta=0.50 时的 intake vs 代谢消耗，找到能量正平衡的准确临界距离。

### 8.2 参数建议

| 参数 | Phase 3 | Phase 4 建议 | 原因 |
|------|---------|-------------|------|
| eligibility_gain | 3e-5 | **5e-6** | 降低60×，给方向分化留时间 |
| w_front init | 0.01 | **0.05** | 初始偏置（非语义硬编码，仅物理初条件） |
| w_brake init | 0.01 | **0.005** | 初始不对称 |
| weight_max | 0.5 | **0.5**（保持） | 已验证安全 |
| K_VANE | 0.001 | **0.001**（保持） | 有效防 yaw 发散 |
| eta | 0.50 | **0.50**（保持） | 多源场中有效 |
| 起始位置 | [50,50,25] | **[65,50,25]**（偏向 S1） | 给 body 一个明确的初始接近方向 |

### 8.3 验收标准（Phase 4）

| 指标 | 目标 |
|------|------|
| W13 | ≥2 次 dist_surface < 15 |
| W14 | w_front/w_brake > 2.0 @ ≤300k |
| W15 | fill > 0.05 @ 500k 全程 |
| W17（新）| w_front/w_brake > 1.5 @ 100k（早期验证，防提前饱和） |

---

## 9. 总结

| 方面 | Phase 3 结论 |
|------|-------------|
| **eta=0.50** | 有效，多源场 fill 峰值 0.733（Phase 2: 0.52）|
| **三热源布局** | 功能正常（碰撞检测、温度场叠加均正确），但 body 最终只定居于一个源附近 |
| **eligibility_gain=3e-5** | 过大，100k 步内权重饱和，方向性分化无从发展 |
| **K_VANE=0.001** | 有效抑制 yaw 发散，但无法解决更根本的 STDP 对称死锁 |
| **STDP 对称死锁** | 本次实验的核心失败机制：body 双向振荡于热源附近，front/back 热信号对称，DA 无法区分方向 |
| **Phase 4 核心方向** | 降低 eligibility_gain + 非对称初始权重，让方向选择性在饱和前出现 |

---

*报告作者：Claude (Sonnet 4.6)，日期：2026-06-28*
