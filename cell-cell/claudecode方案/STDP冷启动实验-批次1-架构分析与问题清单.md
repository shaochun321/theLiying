# STDP冷启动实验 — 实现方案 批次1：架构分析与问题清单

> 对应实验文档：`cell-cell/交叉比对/STDP独立涌现趋热行为 — 冷启动实验方案.md`
> 目标系统：`cell-cc-other/`
> 写作日期：2026-06-25
> 状态：待用户确认 + 他AI交叉比对

---

## 一、补丁现状核查（对照代码实际状态）

| 补丁 | 状态 | 关键文件:行号 | 问题 |
|------|------|---------------|------|
| A AGC→Langevin | 部分 | `agc.py:221`, `langevin_noise.py:64`, `variant_adapter.py:836` | AGC.gain 已生成，但 Langevin σ 固定为 0.70，未接入 AGC |
| B Binding时间卷积 | 缺失 | `binding.py:56-62` | 仍为瞬时 AND 门，无 τ_w 参数 |
| C 卵黄囊 | 缺失 | `energy_store.py` | 仅有 EnergyStore，无 YolkSac 类 |
| D DA微分锚定 | 缺失 | `circulation_proportion.py:168,172` | DA 由绝对偏差触发：`abs(v_ref - rho_h)` |
| E Efference Copy监控 | 部分 | `variant_adapter.py:616-634` | 前向模型误差追踪存在，但无 Binding 事件抑制比例统计 |

---

## 二、补丁依赖关系图

```
Phase 0（必须同步落地）
├── C: YolkSac          ← 独立新组件，无依赖
├── D: DADifferentialGate ← 依赖 EnergyStore.fill 接口（已存在）
├── B: BindingCell时间卷积 ← 依赖 BindingCell 现有接口
├── A: AGC→Langevin接入  ← 依赖 AGC.gain（已存在）、LangevinNoise.sigma0
└── E: 抑制比例监控      ← 依赖 efference copy 现有结构

        ↓ Phase 0全部落地后

Phase 1: 移除 process_hunger    ← 依赖补丁A（AGC已改为Langevin输出）
        ↓
Phase 2: 激活 Binding→Motor 束  ← 依赖补丁B（Binding已有时间窗口）
        ↓
Phase 3: 1M步长程运行
```

**设计批次（不等于实施批次）：**
- 批次2文档：补丁C + D（新独立组件，互不依赖）
- 批次3文档：补丁A + B（对现有组件的修改/扩展）
- 批次4文档：补丁E + Phase 1集成 + 测试方案

**实施要求**：所有补丁必须在同一次提交中同步落地（实验文档第六节明确："阶段0必须与阶段1-3同时落地"）。分批设计但一次提交。

---

## 三、待澄清问题清单

### ISSUE-01 【阻断级】σ₀ 数值不一致

| 来源 | 数值 |
|------|------|
| 实验文档第八节 | σ₀ = **0.07** |
| `langevin_noise.py:64` (`sigma0=`) | σ₀ = **0.70** |

差10倍。补丁A落地后 σ_eff = σ₀ × (1 + G_agc)，若基础值错误则探索幅度整体偏移。

**所需回答**：哪个数值正确？还是文档σ₀=0.07是"目标值"而当前0.70是"待降低的现状"？

---

### ISSUE-02 【阻断级】τ_w 生物来源缺失

实验文档第八节注明 τ_w = 10-20步，来源为"估计运动→热变化延迟"。

这违反强制三问Q1（必须有生物文献或实验来源）。

**候选生物锚点供参考：**

| 生物机制 | τ 范围 | 换算（dt=0.001s） |
|----------|--------|-------------------|
| AMPA受体突触后电流衰减 | 5-20ms | 5-20步 ✓ 与文档一致 |
| 短程突触易化（STF）快成分 | 20-50ms | 20-50步 |
| NMDA受体慢成分 | 50-200ms | 50-200步 |
| 脊髓感觉传导延迟（皮肤→脊髓） | 10-30ms | 10-30步 |

最相关的生物对应：**短程突触易化（STF，facilitating synapse）**——前庭信号在Binding突触处的短时残余（calcium remnant），允许后到达的热感信号与之配对。

**所需回答**：确认 dt 值，选择上表哪个生物锚点，提供文献引用（或授权使用"实验标定"）。

---

### ISSUE-03 【阻断级】η_da 增益未指定

补丁D的DA释放公式：`DA(t) = max(0, η_da × d(fill)/dt)`

实验文档未给出 η_da 值。

**分析**：`d(fill)/dt` 在正常代谢下量级约为 `0.0001/步`（basal_drain=0.0001），进食时约 `0.12 × 0.9 / step ≈ 0.108/步`。要使 DA 浓度达到与现有系统可比的量级（需核查当前DA正常运行幅度），η_da 量级估计在 10~100 之间。

**所需回答**：提供 η_da 值或授权以现有DA激活幅度为参照进行标定实验。

---

### ISSUE-04 【需确认】process_hunger 移除时序

当前代码结构（`variant_adapter.py:790-796`）：

```python
# AGC通过gain_multiplier传入hunger reflex
hunger_drives = self.spinal_reflex.process_hunger(
    thermo_activations, fill_fraction,
    da_concentration=..., gain_multiplier=self.agc.gain, dt=dt)
```

Phase 0补丁A：AGC.gain 接入 LangevinNoise，AGC同时保留对 process_hunger 的 gain_multiplier 输出。

Phase 1：移除 process_hunger 调用（切断硬编码趋热）。

**问题**：Phase 0落地后、Phase 1之前，存在"AGC双输出期"（既调制Langevin又调制hunger），此期间行为会有偏差。这是否可接受？还是要求Phase 0和Phase 1在同一次提交中同步完成？

---

### ISSUE-05 【需确认】BindingCell 修改策略

`binding.py` 是组件文件，修改它涉及"是否改母代码"的判断。

**方案A（原地修改）**：在 `BindingCellConfig` 中添加 `tau_w: Optional[int] = None`，compute() 内部条件分支。向后兼容，改动最小。

**方案B（子类扩展）**：创建 `components/binding_temporal.py`，定义 `TemporalBindingCell(BindingCell)`，在 VariantCircuit 中替换实例化。符合"不改母代码"原则，但需更新 VariantCircuit 实例化逻辑。

**项目规则倾向**：方案B（RULES.md"不改母代码"原则）。

**所需回答**：确认选择方案A还是方案B。

---

## 四、实施前置条件确认清单

进入批次2（开始写代码规格）前需要：

- [ ] ISSUE-01 解决：σ₀ 正确值确认
- [ ] ISSUE-02 解决：τ_w 生物来源确认（或授权"实验标定"）
- [ ] ISSUE-03 解决：η_da 值或标定授权
- [ ] ISSUE-04 解决：Phase 0/1 是否同步提交
- [ ] ISSUE-05 解决：BindingCell 修改策略选择

---

## 五、不受问题阻断的部分

以下内容在上述问题解决前已可确定，将在批次2文档中完整规格化：

**补丁C（卵黄囊）**：参数完整，物理结构清晰，三问可完整回答。
- Q1 BIO: Yolk sac（卵黄囊），胚胎发育期唯一能量来源（非进食），Davidson 2006
- Q2 TYPE:BIO — Capacitor（初始充能=yolk_equivalent×capacity，单向放电至EnergyStore）
- Q3 λ_yolk=0.002/步：yolk_equivalent=200单位 / 100k步目标持续时长 = 0.002单位/步 ✓

**补丁D（DA微分）基础结构**：生物来源清晰，只缺 η_da 增益值（ISSUE-03）。
- Q1 BIO: VTA DA神经元奖励预测误差信号（Schultz et al. 1997）
- Q2 TYPE:BIO|SEMI — Capacitor（保存前一步fill）+ MOSFET（半波整流器，门控正导数）

**补丁E（监控）**：纯INFRA监控逻辑，不涉及新信号路径，三问不适用。

---

*下一批次：批次2文档将给出补丁C和D的完整代码规格（含接口定义、集成点、骨架代码）。*
