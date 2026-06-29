# 评估报告 — World 2.0 Phase 2 方案审查
**日期：** 2026-06-28  
**审查文档：** `cell-cell/交叉方案/整合版 Phase 2 方案（最终）.md`  
**审查人：** Claude Code  
**结论：** 方向正确，两处技术错误须修正，架构假设须调整

---

## 1. 方案概要

Phase 2 在 Phase 1 物理底座（World 2.0）验证通过后，目标是运行第一轮有学习的实验：STDP 在三维物理环境中习得稳定趋热行为，并实现能量自持（fill > 0 持续全程）。

方案包含：参数矩阵（13 项）、启动前三项诊断、前进束/偏航束协同学习框架、7 项监控指标、5 项启动前清单。整体结构清晰，三项诊断设计质量尤其高。

---

## 2. 发现的问题

### 问题 1（Critical）：热源再生速率单位混淆

**方案计算：**  
"regen_rate=0.01 → 2500 units / 500k 步，8000 初始 + 2500 再生 ≈ 10500 总可用"

**实际代码行为：**

```python
# nexus_v1/components/heat_source.py
def step(self, dt: float = 1.0):
    self.energy += self.regeneration_rate * dt
```

每步调用时 dt=0.001（由 variant_adapter 传入）：

```
每步再生 = 0.01 × 0.001 = 1×10⁻⁵ 单位
500k 步总再生 = 0.01 × 0.001 × 500,000 = 5 单位
```

方案预估 2500 units，实际仅 5 units，**误差 500 倍**。

**交叉验证（Phase 1 报告数据）：**  
regen_rate=0.002，100k 步 → 再生 0.002 × 0.001 × 100,000 = **0.2 单位**，与 Part 2 报告的能量账本吻合（"再生量 ≈ 0.2 units"）。

**后果：**
- energy=8000 必须完全自持，无法依赖再生补充
- 能量预算需重新计算：
  - Phase 1 消耗 342 units / 100k 步（eta=0.02，身体一半时间远离热源）
  - Phase 2 eta=0.15（7.5× 提升），预估消耗 ~2500 units / 100k 步（接近期）
  - 500k 步若学习成功（接近期占比约 50%）：~6,000–8,000 units 消耗
  - 8000 初始能量在学习成功时接近耗尽，学习失败时有富余
- **结论：8000 初始是合理的，但必须按"无再生"来理解，不是"10500 总可用"**

**修正选项（二选一）：**

| 选项 | regen_rate | 实际效果 | 适用场景 |
|------|-----------|---------|---------|
| A：接受无再生 | 0.002（Phase 1 原值）| 0.2 units / 100k 步 | 8000 能量完全自持 |
| B：真实补充 | 5.0 | 2500 units / 100k 步 | 若担心 8000 不够 |

推荐选项 A，保持 Phase 1 行为，初始能量 8000 自持。

---

### 问题 2（Architecture Blocker）：`rotate_yaw` 轴不存在

**方案提出：**  
"偏航束 therm_left/right → rotate_yaw：取代废弃的 therm_left/right → move_y"

**当前电机系统（variant_adapter.py 第 595 行）：**

```python
motor_keys = ['move_x', 'move_y', 'move_z']
```

**World 2.0 偏航实现（variant_adapter.py，Phase 1 实施）：**

```python
# 物理层直接施加，不经过突触束
delta_T_lr = T_left - T_right
self.world.body.apply_yaw_torque(delta_T_lr * YAW_GAIN, dt)
```

这条偏航通路是**固定物理反射**，不是突触束，不经过 STDP。

**添加 `rotate_yaw` 轴的实际代价：**
1. 在 hebbian.py 中新增 `rotate_yaw` 电机轴（修改母代码）
2. 新建 col_therm_left/right → rotate_yaw 突触束
3. 将电机输出值耦合到 `apply_yaw_torque()`（修改 variant_adapter.py step()）

这是三处代码变更，**与方案第六节"不涉及架构变更"矛盾**。

**更深层的问题：** Phase 2 的核心目标是"STDP 学习趋热"，而非"STDP 学习偏航"。物理层偏航（delta_T_lr × YAW_GAIN）在 Phase 1 中**已经有效运作**，body 在 W9 实验中从 dist=23 自主趋近至 dist=10（无任何学习）。增加可学习的 yaw 轴会引入额外变量，增加实验复杂度，不是 Phase 2 的必要条件。

---

### 问题 3（Minor）：`therm_left/right → move_y` 废弃需明确实施方式

该束定义在 `hebbian.py` 第 585-586 行（母代码）：

```python
('therm_left',  'move_y', +10.0),   # left heat → excite move_y
('therm_right', 'move_y', -10.0),   # right heat → inhibit move_y
```

"废弃"不能是"删除代码"（违反 RULES.md 不改母代码原则），应在实验脚本或 variant_adapter 中将对应束权重覆写为 0：

```python
# 实验启动后，在 circuit 初始化之后执行：
for b in circuit.get_all_bundles():
    if 'therm_left_to_move_y' in b.config.bundle_id or \
       'therm_right_to_move_y' in b.config.bundle_id:
        b.weight = 0.0
        b.config.weight_max = 0.0  # 冻结，STDP 不能恢复
```

这样不改 hebbian.py，符合 RULES.md。

---

## 3. 修正后的架构方案

去掉 `rotate_yaw`，用"物理层偏航 + STDP 前进"组合：

```
保留（已有，Phase 2 主学习目标）:
  therm_front → move_x  (gain=+10, STDP)  ← 前热 → 前进加速
  therm_back  → move_x  (gain=-10, STDP)  ← 后热 → 前进制动

保留（物理层，不参与 STDP）:
  delta_T_lr × YAW_GAIN → apply_yaw_torque()  ← 温差驱动转向反射

废弃（初始权重=0，在实验脚本中覆写）:
  therm_left  → move_y  (disable: weight=0, weight_max=0)
  therm_right → move_y  (disable: weight=0, weight_max=0)

不需要（Phase 2 范围外）:
  rotate_yaw 轴
```

**逻辑完整性：**
- 身体靠近热源时 → therm_front 激活 → STDP 强化 move_x → 前进加速 → 到达更近处 → 供能增加 → DA ↑ → STDP 进一步强化 → **闭环**
- 偏航由物理层自动维持，无需 STDP 介入
- move_y 废弃消除侧滑干扰（World 2.0 中 body 朝向由 yaw 控制，侧移无生物意义）

---

## 4. 其余参数评估

| 参数 | 方案值 | 评估 | 备注 |
|------|-------|------|------|
| 感官增益 | 0.02 | ✓ | 需诊断 1 确认 enc_therm≥0.05 |
| 对流漂移 k_conv | 0.15 | ✓ | 比 Phase 1（0.5）弱，STDP 承担更多 |
| 口器效率 eta | 0.15 | ✓ | 约覆盖基础代谢，合理 |
| 热源初始能量 | 8000 | ✓（修正后）| 按"无再生"理解，8000 一次性消耗 |
| 热源再生速率 | 0.002 | 推荐降回此值 | 修正问题 1 |
| YolkSac 初始 | 500 | ✓ | 学习参考基线 |
| Z 轴锁定 | Z=25 | ✓ | Phase 1 已验证 |
| weight_max（新束）| 0.3 | ✓ | 防前进束过早饱和 |
| initial_weight（新束）| 0.01 | ✓ | 从零学习，正确方向 |
| eligibility_gain | 1e-5 | ✓ | 保守起点 |
| K_impact | 0.01 | ✓ | 监控中可实时下调 |

---

## 5. 三项诊断评估

| 诊断 | 设计 | 通过标准 | 意见 |
|------|------|---------|------|
| 诊断 1：信号链静态 | ✓ 优秀 | enc_therm≥0.05，col_therm≥1Hz | 应补测 `therm_front/back`，不只是 `therm_*` |
| 诊断 2：碰撞预算 | ✓ 优秀 | <5 次/10k，repair_cost<0.0005/步 | K_impact=0.01 下调至 0.005 可能就够 |
| 诊断 3：热源能量审计 | ✓ 必要 | 500k 步后 energy>0 | 修正 regen 理解后，8000 应可撑住 |

---

## 6. 启动前清单（修正后完整版）

### 原方案 5 项
- [ ] 诊断 1：enc_therm_* 激活值 ≥0.05，col_therm_* spike 频率 ≥1Hz
- [ ] 碰撞预算核算：K_impact 监控代码就位
- [ ] 热源能量审计：采样代码就位
- [ ] 前进束/偏航束配置已更新（见修正方案）
- [ ] 回归测试：21/21 PASS

### 新增修正项
- [ ] regen_rate 设定：确认 0.002（无实质再生），energy=8000 按一次性消耗计算
- [ ] `therm_left/right → move_y` 废弃方式：实验脚本中覆写 weight=weight_max=0，不改 hebbian.py
- [ ] 确认不添加 `rotate_yaw` 轴（Phase 2 偏航由物理层承担）
- [ ] initial_weight=0.01 的 EXP 或 BIO 来源（目前无引用，违反 RULES.md Q3）

---

## 7. 结论

方案在高层次上是正确的执行蓝图。两处技术错误修正后，Phase 2 的最小可行实施路径为：

1. **参数调整**：eta 0.02→0.15，k_conv 0.5→0.15，energy 1000→8000，weight_max=0.3，initial_weight=0.01
2. **废弃侧滑**：实验脚本中将 `therm_left/right → move_y` 束权重置零
3. **执行三项诊断**（按方案原文）
4. **不新增 `rotate_yaw` 轴**（延至 Phase 3 或更晚）
5. **STDP 主体**：`therm_front/back → move_x` 通路学习前进行为

预期实验时长：500k 步（≈37 分钟，与 Phase 5 Round 4 相当），目标验收：fill>0.1 全程，方向性权重分化 >0.02，mouth_intake 在接近期 >0.001/步。
