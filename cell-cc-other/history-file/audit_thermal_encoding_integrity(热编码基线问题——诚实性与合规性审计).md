# 热编码基线问题——诚实性与合规性审计

> **审计范围**: 所有涉及热编码神经元的实验(EXP-009~EXP-017)和回归测试(T1~T10)
> **审计标准**: 发现的信号链基线（ambient 0.1 → relay EMA ≈ 1.0 → 编码 EMA ≈ 0.20）是否影响已发表结论

---

## 审计结论

| 类别 | 数量 | 状态 |
|------|------|------|
| 结论需撤回的实验 | **0** | ✅ |
| 证据力度被削弱的 gate | **1** | ⚠️ EXP-014 Gate 2 |
| 测试前提有误 | **1** | ❌ T2.2 |
| 测试基础设施缺陷 | **1** | ❌ pytest fixture 缺种子 |

> [!IMPORTANT]
> **没有数据伪造或不诚实**。所有实验忠实报告了实测数值。问题仅在于一个 gate 的证据力度不足，以及一个回归测试的物理前提有误。

---

## 逐项审计

### EXP-009: 对称热趋性测试 ✅ 不受影响

结论是 **❌ 无热趋性**（诚实报告失败）。高基线 EMA 可能是热趋性失败的**贡献因素之一**——编码层基线噪声降低了热梯度的信噪比。但实验从未声称热趋性成功，结论依然有效。

### EXP-012: DA 系统开环标定 ✅ 不受影响

使用**钳位 DA 浓度**（0.00→1.00），不依赖热信号链。Motor 响应测量完全独立于热编码基线。

### EXP-013: TemporalCoupler 独立验证 ✅ 不受影响

测量 coupler 动态（V_couple, tau_eff, R_leak 调制范围），不测量编码层活跃度。观察到 `therm V_slow=-0.036`（"最大失配"）现在有了解释：**ambient 基线驱动热感通路持续活跃，与零外部输入的期望不匹配**。但这不影响 coupler 功能验证的结论。

### EXP-014: Phase 3 DA 闭环验证 ⚠️ **Gate 2 证据力度不足**

6 个 gate 逐一审查：

| Gate | 检查项 | 受基线影响？ | 判定 |
|------|--------|------------|------|
| 1 | Skin T 非零 | 不影响 | ✅ 物理正确——skin 当然有温度 |
| **2** | **编码层发火** | **⚠️ 受影响** | **此 gate 会因 ambient 基线而自动 PASS** |
| 3 | Shadow col 分化 | 部分影响，但分化是真实的 | ✅ 分化 (0.85 vs 0.48) 需要梯度信号 |
| 4 | DA 浓度波动 | 不直接受影响 | ✅ |
| 5 | STDP 权重变化 | 不直接受影响 | ✅ |
| 6 | 能量健康 | 不受影响 | ✅ |

**Gate 2 问题详解**：
- Gate 2 检查 `any(v > 0 for v in snapshot.values())` —— 至少一个热编码神经元有非零 activation
- 由于 ambient 基线 → relay EMA ≈ 1.0 → EXTRA_AXIS_GAIN × 1.0 = 0.04 → 编码 V_ss = 0.20 → activation > 0
- **即使体感链完全断开，只要 ambient 温度存在，此 gate 就会 PASS**
- 它是一个**重言式证据**（tautological evidence）——不能区分"信号链工作"和"基线存在"

**但 EXP-014 的核心结论不受影响**：
- Gate 3 的 shadow col 空间分化（front=0.85 vs left/right=0.48）**不可能仅由均匀基线产生**
- Gate 5 的差分权重增长（front 0.297→0.928 vs left 0.444→0.706）也需要真实梯度信号
- 信号链闭环的结论由 Gate 3+5 支撑，Gate 2 是冗余证据

> [!WARNING]
> **需要修正**: Gate 2 应改为检查 thermal encoding **差分**：`enc_front - enc_back > threshold`，而非绝对值 > 0。这才能证明信号链传递了梯度信息。

### EXP-015: Thermal Taxis v2 ✅ 不受影响

诚实报告 **⚠️ 信号链正确但行为未涌现**。实验数据包括：
- 皮温不对称 front-back=+0.43 — 这是**真实的梯度信号**，不是基线
- DA 崩溃到 0 — 真实观测
- Motor 微观输出 — 真实观测

基线 EMA 不改变这些观测，也不改变"三个缺失环节"的诊断。

### EXP-016: Phase 1 100k 对照 ✅ 结论有效，但需注记

EXP-016 表格中的 `enc_f` / `enc_b` 是 `reg_therm_front` / `reg_therm_back` 的 EMA。

审查数据：
```
 10k: enc_f=0.000  enc_b=0.000   ← 初始阶段，基线尚未稳定
 20k: enc_f=0.476  enc_b=0.000   ← front 远高于基线(0.20)，有真实梯度贡献
 80k: enc_f=0.000  enc_b=0.000   ← 能量耗竭后编码静默
```

**关键观察**：
- `enc_f=0.476` 显著高于 ambient 基线 (≈0.20) → 有真实热源信号叠加
- Δw 测量（w_front - w_back）是**差分量**，对共模基线鲁棒
- 结论 "Δw=+0.027 > 0.02，系统自稳定" 依赖差分权重，不依赖绝对编码水平

> [!NOTE]
> 该实验使用 `random.seed(42)`（通过 `run_test_suite` 入口），所以结果是确定性的。基线值为 0.20，远低于测试阈值。

### EXP-017: Phase 2 冬眠护盾 ✅ 不受影响

测量 w_front / w_back 差分和对称冻结行为。差分量对共模基线鲁棒。核心结论（Δw 在能量冻结后保持稳定）不依赖编码层绝对水平。

---

## 回归测试审计

| 测试 | 涉及热编码？ | 受影响？ | 判定 |
|------|------------|---------|------|
| T0.1 Circuit builds | 否 | 否 | ✅ |
| T0.2 10k steps complete | 否 | 否 | ✅ |
| T1.1 Noether violations | 间接 | 否 | ✅ 守恒律不依赖信号水平 |
| T1.2 Energy balance | 间接 | 否 | ✅ 基线贡献的能量流在收支中平衡 |
| T1.3 Landauer bound | 间接 | 否 | ✅ |
| **T2.1** Active encoding > 0.3 | 否 | 否 | ✅ 测量 `reg_oto_x`（前庭） |
| **T2.2** Quiet encoding < 0.5 | **是** | **是** | **❌ 前提有误** |
| **T2.3** Selectivity ratio > 1.5x | **是** | **边缘** | ⚠️ 见下文 |
| T3.1 Vest column > 0.3 | 否 | 否 | ✅ |
| **T3.2** Thermal col < vest col | **是** | **边缘** | ⚠️ 见下文 |
| T4.1 Axis/cross ratio | 否 | 否 | ✅ |
| T4.2 Cross weight max | 否 | 否 | ✅ |
| T4.3 Motor diff | 否 | 否 | ✅ |
| T5 FFT periodicity | 否 | 否 | ✅ |
| T6 Sprouting sanity | 否 | 否 | ✅ |
| T7 Kinetic energy | 否 | 否 | ✅ |
| T8 Structural entropy | 否 | 否 | ✅ |
| T10 Energy ledger | 否 | 否 | ✅ |

### T2.2 "Quiet encoding < 0.5" ❌ 前提有误

```python
# L108, L120-123:
enc_quiet = c.encoding_neurons['reg_therm_front']._activation_ema
assert enc_quiet < 0.5  # "therm encoding should be quiet with no thermal input"
```

**注释写的是 "with no thermal input"，但事实是闭环世界始终有温度场。** 这个测试基于错误的物理假设——认为不在 `mechanical_inputs` 中给 `therm_*` 键就等于"无热输入"。实际上 [variant_adapter.py:L632-635](file:///D:/cell-cc/nexus_v1/circuit/variant_adapter.py#L632-L635) 会自动注入体感链输出。

- 用 `random.seed(42)`: `enc_quiet=0.203` → PASS（偶然通过，不是物理正确）
- 无 seed (pytest): `enc_quiet` 范围 0.00~0.70 → **约 1/3 概率 FAIL**

### T2.3 Selectivity ratio > 1.5x ⚠️ 边缘

```python
assert enc_active > enc_quiet * 1.5
# seed=42: 0.652 > 0.203 * 1.5 = 0.305 → PASS (ratio = 3.2x)
```

- 用 seed=42 通过是因为 `enc_quiet=0.203` 较低
- 无 seed 时 `enc_quiet` 可能高达 0.70 → `0.652 > 0.70 * 1.5 = 1.05` → FAIL
- 但即使 seed=42 下的 3.2x ratio 也是**真实的选择性**：前庭编码确实比热编码更活跃（因为有 200sin 输入）

### T3.2 Thermal col < vest col ⚠️ 边缘

- 如果热编码基线高 → 热 column 也被驱动 → `col_therm` 可能接近 `col_vest`
- 但 seed=42 下 column 分化仍然成立（前庭有 200sin 强驱动）

---

## 影响总结

### 不受影响的结论

1. **Noether 守恒** — 基线能量流在收支中平衡
2. **STDP 差分拓扑** — Δw 测量对共模基线鲁棒
3. **DA 闭环** — 由 Gate 3+5 支撑，不依赖 Gate 2
4. **冬眠护盾** — 对称冻结行为不依赖编码水平
5. **Motor 拓扑** — axis/cross 权重分化不涉及热编码

### 需要修正的项目

| # | 修正内容 | 严重性 |
|---|---------|--------|
| 1 | **T2.2**: 改为差分选择性或提高阈值 | 中——测试前提错误 |
| 2 | **pytest fixture**: 添加 `random.seed(42)` | 中——测试不确定性 |
| 3 | **EXP-014 Gate 2**: 改为差分检查 | 低——冗余证据 |
| 4 | **EXP-016 注记**: 标注 enc_f 包含 ambient 基线成分 | 低——数据记录完整性 |

### 诚实性判决

> [!TIP]
> **系统整体诚实**。所有关键结论都基于**差分测量**（Δw、空间分化、ratio），而非绝对值。差分测量对共模基线天然鲁棒。唯一的物理假设错误在 T2.2 的注释中——"no thermal input" 在闭环世界中不成立。这是概念错误，不是不诚实。

---

## 建议修复优先级

1. **立即**: pytest fixture 添加 `random.seed(42)` — 消除不确定性
2. **立即**: T2.2 改为 `enc_active / enc_quiet > 2.0`（相对选择性）
3. **下次实验前**: EXP-014 Gate 2 改为差分检查
4. **文档**: EXP-016 数据表添加 "基线 ≈ 0.20" 注脚
