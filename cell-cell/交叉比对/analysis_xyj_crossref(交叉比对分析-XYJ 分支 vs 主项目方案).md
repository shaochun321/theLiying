# 交叉比对分析：XYJ 分支 vs 主项目方案

**日期**: 2026-06-25  
**比对对象**:
- **XYJ 分支** (`cell-cc-other/`): Claude Code 五补丁方案，已执行 1M 步验证
- **主项目** (`cell-cc/nexus_v1/`): Antigravity 自我坐标方案 (`implementation_plan.md`)，仅草拟未执行

---

## 一、根因诊断对比

| 维度 | XYJ 分支诊断 | 主项目诊断 | 一致性 |
|------|-------------|-----------|--------|
| STDP 无方向分化 | ✅ 确认 | ✅ 确认 | **一致** |
| 信用分配失败 | 隐含（DA 差分方案间接解决） | **显式指出**（信号流平行无交汇） | 主项目更深 |
| `process_hunger` 是 L2 违规 | ✅ Phase 1 禁用 | ✅ Phase 0 废弃 | **一致** |
| 代谢不足 | ✅ YolkSac 补偿 | ✅ deposit rate 0.05→0.12 | 路径不同，目标一致 |
| Binding 层休眠 | ✅ 补丁 B: TemporalBinding | ✅ Phase 1: Binding→Motor STDP | 都激活 Binding，方式不同 |

> [!IMPORTANT]
> **两条路线共享同一个根因诊断**：热感 STDP 权重回归均值，因为运动通路和热感通路平行无交汇，缺乏跨模态因果信号。

---

## 二、解决方案结构对比

### 2.1 五补丁方案（XYJ 已实施）

| 补丁 | 物理原语 | 集成方式 | L层级判断 |
|------|---------|---------|----------|
| A: AGC→Langevin | 噪声振幅随饥饿放大 | `variant_adapter.py:703` 修改 sigma | L2（选择） ✅ |
| B: TemporalBindingLayer | 前庭轴 Capacitor 时间卷积 τ_w=30 | 子类替换 BindingLayer | L1（涌现）✅ |
| C: YolkSac | Capacitor 单向放电 | 新组件，step 前注入 | L2（选择）✅ |
| D: DADifferentialGate | Δfill/dt → DA（半波整流） | 新组件，step 中触发 | L1（涌现）⚠️ |
| E: Efference 监控 | 抑制比例统计 | INFRA 监控 | INFRA ✅ |
| Phase 1: 禁用 process_hunger | 注释掉调用 | `variant_adapter.py:837` | 清理 ✅ |

### 2.2 自我坐标方案（主项目，未实施）

| 阶段 | 物理原语 | 集成方式 | L层级判断 |
|------|---------|---------|----------|
| Phase 0: 废弃 process_hunger | 方法返回零 | spinal_reflex.py | 清理 ✅ |
| Phase 1: Binding→Motor STDP 束 | 12 个 SynapticBundle（DA-gated eligibility trace） | 替换 _binding_motor_weights 字典 | L1（涌现）✅ |
| Phase 2: Efference→Binding 调制 | motor_efficacy 调制 Binding 前庭输入 | variant_adapter.py 步骤 6b | L1（涌现）✅ |

---

## 三、关键差异分析

### 3.1 DA 信号来源

| | XYJ 方案 | 主项目方案 |
|-|---------|-----------|
| DA 触发机制 | **新组件** `DADifferentialGate`：Δfill/dt × η_da | **沿用现有** `circulation_proportion.py` 的 DA 系统 |
| DA 物理依据 | Schultz 1997 RPE，半波整流 MOSFET | 已有 Xin tension → DA 通路 |
| DA 与量纲 | `Δfill/dt` 除以 dt=0.001 → 放大 1000×，需 clip_max=5.0 | 无量纲问题 |

> [!WARNING]
> **DADifferentialGate 的量纲问题**：`raw = η_da × delta_fill / dt`，当 dt=0.001 时除以 0.001 = ×1000 放大。
> η_da=7.5 在 dt=0.001 下等效 η_eff=7500。这是否是有意设计需要确认。
> 报告显示 DA 在前 20k 步饱和 =1.0（yolk 注入），之后长期为 0（无进食）。
> **该组件绕过了现有的 circulation_proportion DA 系统**，形成了双 DA 源。

### 3.2 Binding Layer 策略

| | XYJ 方案 | 主项目方案 |
|-|---------|-----------|
| 修改方式 | 子类 `TemporalBindingCell` 替换 | 给 BindingCell 添加 STDP 接口 + 12 个 SynapticBundle |
| 时间窗口 | τ_w=30 步 EMA（STF 模型） | 无额外时间窗口，依赖 STDP eligibility trace τ=500 |
| Binding→Motor | 保留原有 `_binding_motor_weights` 字典（0.001 dormant） | **替换为正式 SynapticBundle**（DA-gated STDP） |
| 信用分配 | 隐含：TemporalBinding 延长前庭信号，间接配对 | **显式**：SynapticBundle 的 eligibility trace + DA gate |

> [!IMPORTANT]
> **核心分歧**：XYJ 方案在 Binding 层加了时间卷积但**没有给 Binding→Motor 加 STDP 学习**。
> Binding→Motor 仍然是 0.001 的固定权重。这解释了为什么 1M 步后四方向 therm 束差异极小（最大 0.0078）——
> Binding 层虽然被激活了，但它的输出无法通过学习增强。
> 
> 主项目方案直接解决这个问题：用 12 个 DA-gated SynapticBundle 替换固定权重。

### 3.3 Efference Copy 角色

| | XYJ 方案 | 主项目方案 |
|-|---------|-----------|
| 用途 | **监控**：R_supp 统计（INFRA） | **功能**：motor_efficacy 调制 Binding 前庭输入 |
| 因果区分 | 无 | ✅ 区分主动/被动运动 |

---

## 四、1M 步验证结果的启示

```
CR1: max(Δw_ij) = 0.4004  ← therm 束整体 LTP，但方向不分化
CR2: Δx(200k) = +0.0232   ← Langevin 噪声积分，非定向运动
CR3: fill_min = 0.0000     ← 代谢崩溃 @270k
CR4: R_supp = 0.0000       ← efference 无过抑制
```

**关键教训**：

1. **STDP 工作正常**（therm 权重从 0.1→0.45），但**缺乏方向选择性**（四方向差 < 0.008）
2. 报告自己诊断了原因：*"若所有方向都读取同一个 ThermalMembrane 值，则 STDP 无法产生方向性权重分化"*
   - 但实际上**不是传感器问题**——项目已有 4 patch 差分传感器（front/back/left/right 独立 relay）
   - 真正原因是 **Binding→Motor 无 STDP**，所以 Binding 的跨模态信息无法转化为方向性学习
3. **代谢崩溃**：yolk 200 单位 / 0.002/步 = 100k 步，但 100k 步内进食不足 → 270k 崩溃
   - 主项目的 `max_deposit_per_step=0.12` 已标定到 P_in > P_out

---

## 五、迁移决策

### 方案 A：直接迁移到主项目

**优点**：
- 主项目有完整 git 历史、存档点 `e9d1c8a`
- 主项目的 `max_deposit_per_step=0.12` 已解决代谢问题
- 回归测试体系完整

**缺点**：
- XYJ 方案的新组件（YolkSac、DADifferentialGate、TemporalBindingLayer）需逐个审查 L 层级合规
- DADifferentialGate 与现有 DA 系统可能冲突
- 需要大量代码适配

### 方案 B：在 `cell-cc-other` 上继续试行修改（推荐）

**优点**：
- 五补丁已落地且运行正常（21/21 回归 PASS）
- 已有 1M 步基线数据可做对照
- 隔离环境，不影响主项目
- 可以快速验证"加上 Binding→Motor STDP 后方向性是否出现"

**缺点**：
- 代码与主项目可能 drift
- 需要手动同步 deposit rate 等标定参数

> [!TIP]
> **推荐方案 B**：在 `cell-cc-other` 上叠加主项目方案的 Phase 1（Binding→Motor STDP），
> 因为 XYJ 分支已经具备了 TemporalBinding（补丁 B）和 process_hunger 禁用（Phase 1），
> 缺的恰恰是**主项目方案的核心**——Binding→Motor STDP 束。
> 
> 这是最快的验证路径：在已有基础上只需增加一个组件，而非重做全套。

---

## 六、推荐的后续修改（在 `cell-cc-other` 上）

| 优先级 | 修改 | 来源 | 预估 |
|--------|------|------|------|
| P0 | **Binding→Motor: 固定权重 → DA-gated SynapticBundle** | 主项目 Phase 1 | 40 min |
| P1 | `max_deposit_per_step` 0.05 → 0.12 | 主项目 EXP-023 标定 | 2 min |
| P2 | Efference copy → Binding 调制（主动/被动区分） | 主项目 Phase 2 | 15 min |
| P3 | YolkSac 增容 200→500（Phase 4 草案） | XYJ 报告建议 | 2 min |
| 延后 | DADifferentialGate 与现有 DA 系统的统一 | 待验证后决定 | — |

**验证实验**：修改后运行 500k 步，对照指标：
- 四方向 therm 束最大差值 > 0.05（vs 当前 0.008）
- fill_min > 0（vs 当前 0.000）
- dist 轨迹显示趋向热源趋势

---

## 七、关于 DADifferentialGate 的 L 层级审查

> [!CAUTION]
> `DADifferentialGate` 需要特别审查。它用 `Δfill/dt` 触发 DA，这是对 **EnergyStore 状态变化率**的直接读取。
> 
> **问题**：现有 DA 系统通过 `circulation_proportion.py` 的 Xin tension 触发，
> 是物理循环的自然结果（L1）。DADifferentialGate 直接读取 fill 变化率是否构成"语义捷径"？
> 
> **辩护**：VTA DA 神经元确实编码 RPE（Schultz 1997），fill 变化率是进食的物理后果。
> 但 `η_da=7.5 / dt=0.001 = 有效增益 7500` 的量纲处理需要确认是否有意。
> 
> **建议**：暂时保留，但用 `da_concentration = max(existing_da, da_gate_output)` 
> 合并两个 DA 源，避免双通道互相覆盖。
