

> **方案性质**：基于实测审计的最终修复与验证方案  
> **前置状态**：热觉链路四项修复已完成，验证通过  
> **状态**：最终方案，可直接执行


## 一、已完成状态确认

以下四项修复已在 2026-06-26 执行并验证通过：

| 修复 | 文件 | 修复前 | 修复后 | 验证 |
|------|------|--------|--------|------|
| Noci 参数修正 | `chain.py` | V=-134V | V∈[-0.3,0.25] | Noether \|V\|>100 归零 |
| 热感换能增益校准 | `chain.py` | reg_therm>1.0 | reg_therm∈[0.47,0.58] | 方向差异保留 |
| Shadow Census 补丁 | `variant_adapter.py` | 0 | 21个可见 | 熵账本出现 Shadow |
| Column v_peak 恢复 | `hebbian.py` | 0.10（全列）| 0.20（热列）| T5.1 0.49Hz PASS |

**方向性权重分化已启动**：Motor therm \|Δw\| = 0.00000 → **0.02041**（通过 DR1 阈值 0.02）


## 二、Phase 5 启动前须完成的配套项

| 序号 | 项目 | 当前值 | 目标值 | 涉及文件 | 性质 |
|------|------|--------|--------|----------|------|
| 1 | DA 注入缩放 | 无缩放（1.0）| `DA_INJECT_SCALE = 0.014` | `variant_adapter.py` | 参数新增 |
| 2 | Column 热列增益调优 | V≈0.17（距阈值0.03V）| V≥0.21（稳定跨阈）| `hebbian.py` enc→col gain | 参数调整 |
| 3 | DEVIATION_MOTOR_GAIN | 1.0 | 1000.0（临时量纲补偿）| `variant_adapter.py` | 参数调整 |
| 4 | Phase 5 完整参数 | 未配置 | 应用参数方案 | `exp_phase5.py`（新建）| 实验配置 |
| 5 | Noether violations=90 | 根因已转移至 DA 饱和 | 与 DA 修复同步 | `variant_adapter.py` | 待处理 |

**关于序号 2 的增益调优方向**：优先调整 `synapse_gain`（硬件级阻抗匹配），保持 `initial_weight` 不变。初始权重是 STDP 的学习起点，改动它等于透支未来的突触可塑性空间。`synapse_gain` 与 `initial_weight` 的物理区别：增益是固定放大器，权重是可塑记忆体。

**关于序号 5**：Noether violations=90 的根因已从 noci（\|V\|>100）转移到 DA 饱和（xin_to_da Xin=-37.9）。DA 饱和由 DA_INJECT_SCALE 直接处理，两者同源。DA_INJECT_SCALE=0.014 落地后，此问题应同步解决。


## 三、Phase 5 完整参数方案

### 3.1 热觉链路参数（已落地）

| 参数 | 值 | 位置 |
|------|-----|------|
| Noci v_peak | 0.25 | `chain.py` |
| Noci b_adapt | 0.0002 | `chain.py` |
| Noci tau_w | 0.5 | `chain.py` |
| THERMAL_TRANSDUCTION_GAIN | 0.1 | `chain.py` |
| Column 热列 v_peak | 0.20 | `hebbian.py` |

### 3.2 DA 与增益参数

| 参数 | 值 | 物理依据 |
|------|-----|----------|
| DA_INJECT_SCALE | 0.014 | RPE 峰值 5.0 → V_ss(DA) ≈ 0.35（≤v_peak），DA 不饱和 |
| DEVIATION_MOTOR_GAIN | 1000.0 | dt=0.001 量纲补偿（临时，Phase 5 后随 V-03 移除）|

### 3.3 学习与代谢参数

| 参数 | 值 | 对比 Phase 4 |
|------|-----|-------------|
| stdp_lr（热束）| 0.005 | 0.05 → 0.005（慢速学习，保留分化空间）|
| weight_max | 0.5 | 不变 |
| initial_weight（热束）| 0.02 | 不变 |
| lambda_yolk | 0.0015 | 0.001 → 0.0015（拉长续航）|
| yolk_initial_level | 500 | 不变 |
| lateral_gain | 0.3 | 不变 |
| Langevin tau | 3.0 | 不变（BIO 标注已更新）|
| 出生点 | [75,20,25] | 不变 |


## 四、执行步骤

### 步骤 1：热觉链路配置确认

确认四项修复已在代码中生效。运行 `run_full_audit.py`，应显示：

```
soma_noci V ∈ [-0.3, 0.25]  ✅
reg_therm avg ∈ [0.45, 0.60]  ✅
Shadow census: 21 neurons  ✅
col_therm_* act > 0.001  ✅
```

### 步骤 2：应用 Phase 5 参数配置

**DA_INJECT_SCALE**（`variant_adapter.py`，约 DA 驱动段）：
```python
DA_INJECT_SCALE = 0.014
_rpe_da = self.da_gate.step(...)
if _rpe_da > 0:
    _scaled_rpe = _rpe_da * DA_INJECT_SCALE
    for neuron in self.da_neurons.values():
        neuron._membrane.inject(_scaled_rpe, dt)
```

**enc→col 热列增益调优**（`hebbian.py`，热列对应的 enc→col bundle）：
- 优先调整 `synapse_gain`（硬件级阻抗匹配），保持 `initial_weight` 不变
- 将 `synapse_gain` 提升 1.2-1.5 倍（例如从 3.0 提至 4.0-4.5）
- 若增益提升后 col_therm V 仍 <0.20，检查该 Bundle 的 TemporalCoupler 是否过载：
  - 适度放宽 `coupler_adapt_vth`（如从 0.2 调至 0.3-0.4）
  - 降低 `coupler_r_leak`（加速漏电泄放）

**学习与代谢参数**（`hebbian.py` 热束配置、`yolk_sac.py`）：
- `stdp_lr = 0.005`
- `lambda_yolk = 0.0015`
- `weight_max = 0.5`（不变）
- `initial_weight = 0.02`（不变）

### 步骤 3：创建 Phase 5 实验脚本

基于 Phase 4 脚本（`exp_phase4_directional.py`），应用新的参数配置。关键差异：

- `stdp_lr` 0.05 → 0.005
- `lambda_yolk` 0.001 → 0.0015
- `DA_INJECT_SCALE = 0.014`
- 移除 `DA = max(RPE, Hunger)`（RPE only）

### 步骤 4：运行 10k 步探测测试

```bash
python -m nexus_v1.tests.diag_phase5_signal
```

确认四项体征：
1. `soma_noci` 不再进入 -134V 深渊
2. `reg_therm_left/right` 呈现方向差异
3. `col_therm` 在 v_peak=0.20 下可靠放电（V≥0.21）
4. DA 3/3 不持续饱和

### 步骤 5：运行 Phase 5 500k 步实验

```bash
python -m nexus_v1.tests.exp_phase5_directional
```

预计运行时间 ~35 分钟。


## 五、验收标准

| 标准 | 目标 | 说明 |
|------|------|------|
| DR1 | \|w_left - w_right\| > 0.02（500k 步终点）| 方向性权重分化 |
| DR2 | Δy(200k) > 1.0 | 宏观位移 |
| DR3 | fill > 0 全程 | 代谢生存 |
| DR4 | 分化在 200k 步内出现，持续 >50k 步 | 非瞬时分化 |
| DR5 | grad_dot_v 在分化后持续为正 | 热趋向对齐度（新增观测）|
| DR6 | DA 3/3 不持续饱和 | 动态范围保留 |


## 六、执行时间线

| 步骤 | 内容 | 预计时间 |
|------|------|----------|
| 1 | 热觉链路配置确认 | 5 分钟 |
| 2 | 应用 Phase 5 参数 | 15 分钟 |
| 3 | 创建实验脚本 | 10 分钟 |
| 4 | 10k 步探测测试 | 1 分钟 |
| 5 | 500k 步实验 | ~35 分钟 |

**总计**：约 1 小时


## 七、应急调整（实验期间监控）

### 7.1 DA 动态范围保护

若 100k 步时监控发现 DA 神经元膜电位持续在 v_peak 附近徘徊（饱和），立即将 `DA_INJECT_SCALE` 下调 20-50%。宁可学习速率降低，也不容许 DA 饱和抹平信号差异。DA 激活维持在 0.1-0.3 的半饱状态是理想的工作点。

### 7.2 空间侧抑制应急

若 100k 步时 \|Δw\| < 0.005（分化极弱），立即将 `SomatosensoryChain` 中的 `lateral_gain` 从 0.3 提升至 0.5-0.8。这相当于强行拉开四个方向皮层的竞争强度，迫使 STDP 形成赢者通吃的剪刀差。

### 7.3 `grad_dot_v` 实时监控

Phase 5 运行期间，持续观察控制台 `thermal_alignment` 输出：
- `grad_dot_v > 0` 持续出现 → 系统正在向热源方向移动
- `grad_dot_v > 0` 持续出现但 \|Δw\| 仍低 → `stdp_lr` 可能过低，考虑提升至 0.01


## 八、已知风险与缓解

| 风险 | 缓解 |
|------|------|
| Noether violations=90（DA 饱和）| DA_INJECT_SCALE 直接处理，属于同源问题 |
| col_therm 增益需调优 | 步骤 2 在 Phase 5 前闭环 |
| Phase 5 仍可能失败 | 失败时数据将是干净的（无物理信号链阻塞），可据此判断是学习规则不足还是能量预算不足 |
| DEVIATION_MOTOR_GAIN=1000 与 STDP 运动指令叠加 | 实验分析时留意行为来源区分 |


## 九、回退条件

如 Phase 5 实验后仍无方向性分化，按以下顺序排查：

1. 检查 `grad_dot_v` 是否在分化窗口期出现正偏
2. 检查 `col_therm_*.ema` 是否 >0.05
3. 检查 `DA` 在进食事件后是否 >0.01（非饱和）
4. 检查 `fill` 是否在 250k 步前归零
5. 若前述 4 项全部通过但仍无分化 → 增大 `lateral_gain` 或进一步延长 Langevin τ


**方案确认后即可执行。** 本方案是对此前热觉链路四项修复验证通过后，剩余配套项及 Phase 5 实验启动的完整执行文档。所有参数均有物理/生物依据，无新组件，无语义硬编码。