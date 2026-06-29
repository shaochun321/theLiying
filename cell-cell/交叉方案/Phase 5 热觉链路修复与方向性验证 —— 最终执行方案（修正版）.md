# Phase 5 热觉链路修复与方向性验证 —— 最终执行方案（修正版）

**修正依据**：document(43) 确认的前庭 v2.0 状态 + document(42) T2.3 抖动真相 + 本审计报告的四项修正项

**方案状态**：可执行

---

## 一、修正摘要（相对原方案 2026-06-26）

| 修正项 | 原方案 | 修正后 | 原因 |
| :--- | :--- | :--- | :--- |
| DA_INJECT_SCALE | 待落地 | ✅ 已落地（0.014） | document(43) 确认 |
| Noether violations=90 | 待处理 | ✅ 已解决（与 DA 饱和同源） | DA_INJECT_SCALE 修复 |
| DEVIATION_MOTOR_GAIN | 1000.0（临时量纲补偿）| **需重新标定，可能移除** | 前庭 v2.0 已改变运动驱动架构 |
| 执行步骤 | 4 步（热觉→参数→脚本→实验） | **5 步**（新增步骤 0：前庭 v2.0 状态确认）| 前庭 v2.0 已集成，需前置确认 |
| T2.3 抖动说明 | 无 | 新增“已结构性消除”状态 | document(42/43) 确认软饱和胜利 |
| 应急调整 | 3 项 | **4 项**（新增前庭行为贡献异常应急）| 前庭 v2.0 驱动行为需监控 |


## 二、前庭 v2.0 接入顺序（完整路径）

前庭 v2.0 的接入已按以下顺序完成，Phase 5 启动前应确认其状态。

### 2.1 已完成的接入阶段

| 阶段 | 时间 | 状态 | 说明 |
| :--- | :--- | :--- | :--- |
| **阶段 0：架构构建** | 2026-06-29 | ✅ 完成 | V-N1~V-N6：地址枚举、距离函数、FIFO、软饱和、gain_coeff、nearby |
| **阶段 1：并行验证** | 2026-06-29 | ✅ 完成 | v2.0 与 v1.0 并行运行，8/8 验证通过 |
| **阶段 2：运行时替换** | 2026-06-29 | ✅ 完成 | V2_ACTIVE_DRIVE 成为默认模式，v1.0 退役 |
| **阶段 3：T2.3 抖动消除** | 2026-06-29 | ✅ 完成 | 软饱和结构性消除了硬截断尖峰，T2.3 从 2.84x 跃升至 699x |

### 2.2 Phase 5 启动时的接入状态

```
前庭子系统：v2.0（已上线）→ 驱动 Motor，G_eff 动态调节，软饱和生效
热觉子系统：v1.0（未迁移）→ 方向性 STDP 学习，侧抑制竞争
影子层：v1.0（已补丁）→ 21 个节点可见，熵账本活跃
能量审计：P1/P2 已修复，P3（KCL 违规）延后
```

### 2.3 为什么热觉尚未迁移到 v2.0？

热觉地址隔离（原方案中作为“阶段3”设计）在 document(42/43) 审计后，其**紧急程度已降级**：

| 原目标 | 当前评估 |
| :--- | :--- |
| “隔离热觉旁路串扰” | ❌ 串扰不存在（document 42 证实）|
| “统一地址空间” | ✅ 仍为长期架构目标，但非 Phase 5 阻塞项 |
| “消除 T2.3 抖动” | ✅ 软饱和已消除，无需地址隔离介入 |

**结论**：热觉迁移至 v2.0 地址空间是长期演进目标，不阻塞 Phase 5 实验。

### 2.4 Phase 5 运行时 v2.0 的运作方式

| 组件 | 版本 | 与 Phase 5 热趋向的关系 |
| :--- | :--- | :--- |
| 前庭→Motor 驱动 | v2.0（软饱和 + FIFO + G_eff）| **辅助行为**——提供自主运动，与热趋向叠加 |
| 热觉→Motor 驱动 | v1.0（STDP 权重学习）| **核心行为**——方向性分化由热觉 STDP 驱动 |
| 两者叠加方式 | Motor += 前庭驱动 + 热觉驱动 | 前庭提供运动基底，热觉提供方向偏置 |
| G_eff 动态门控 | 工作正常 | 能量波动时前庭增益自动调整，不影响热觉 STDP |


## 三、已完成状态确认（Phase 5 前置条件）

以下状态应在执行 Phase 5 前逐项确认：

| 序号 | 确认项 | 预期状态 | 验证命令 |
| :--- | :--- | :--- | :--- |
| 0 | 前庭 v2.0 驱动模式 | `V2_ACTIVE_DRIVE` 为默认 | 检查 `variant_adapter.VESTIBULAR_MODE` |
| 1 | Noci 参数修正 | V∈[-0.3, 0.25] | `run_full_audit.py` |
| 2 | 热感换能增益校准 | reg_therm∈[0.47, 0.58] | `run_full_audit.py` |
| 3 | Shadow Census | 21 个神经元可见 | `run_full_audit.py` |
| 4 | Column 热列 v_peak | 0.20（非 0.10）| `hebbian.py` 热列配置 |
| 5 | DA_INJECT_SCALE | 0.014 已落地 | `variant_adapter.py` |
| 6 | Noether violations | DA 饱和已解决 | `run_full_audit.py` 应显示 violations 归零或大幅下降 |
| 7 | T2.3 抖动 | 已结构性消除 | 回归测试 T2.3 PASS |

若上述 7 项全部通过，Phase 5 前置条件满足。


## 四、Phase 5 启动前须完成的配套项

| 序号 | 项目 | 当前状态 | 目标状态 | 涉及文件 | 优先级 |
| :--- | :--- | :--- | :--- | :--- | :--- |
| 1 | DA_INJECT_SCALE | ✅ 已落地（0.014）| 确认生效 | `variant_adapter.py` | 低（仅确认）|
| 2 | Column 热列增益调优 | ⚠️ **未完成** | V≥0.21（稳定跨阈）| `hebbian.py` enc→col gain | **高（阻塞）** |
| 3 | DEVIATION_MOTOR_GAIN | ⚠️ **待重新标定** | 待定（可能移除）| `variant_adapter.py` | **中（需决策）** |
| 4 | Phase 5 参数方案 | 已定义 | 应用至实验脚本 | `exp_phase5.py`（新建）| **高（阻塞）** |

**关于序号 3 的标定方法**：
1. 运行 `diag_motor_response.py`（需新建），记录前庭 v2.0 单独驱动下的 Motor 输出量级。
2. 若 Motor 输出量级与原方案预期一致（即有足够驱动力），则 `DEVIATION_MOTOR_GAIN` 可设置为 `1.0`（移除临时补偿）。
3. 若 Motor 输出量级不足，则按实测偏差调整增益值，但应明确记录其“补偿”性质，并在 Phase 5 后随 V-03 移除。


## 五、Phase 5 完整参数方案

### 5.1 热觉链路参数（已落地）

| 参数 | 值 | 位置 |
| :--- | :--- | :--- |
| Noci v_peak | 0.25 | `chain.py` |
| Noci b_adapt | 0.0002 | `chain.py` |
| Noci tau_w | 0.5 | `chain.py` |
| THERMAL_TRANSDUCTION_GAIN | 0.1 | `chain.py` |
| Column 热列 v_peak | 0.20 | `hebbian.py` |

### 5.2 DA 与增益参数

| 参数 | 值 | 状态 |
| :--- | :--- | :--- |
| DA_INJECT_SCALE | 0.014 | ✅ 已落地 |
| DEVIATION_MOTOR_GAIN | **待标定（见 §4）** | ⚠️ 待决策 |

### 5.3 学习与代谢参数

| 参数 | 值 | 说明 |
| :--- | :--- | :--- |
| stdp_lr（热束）| 0.005 | 慢速学习，保留分化空间 |
| weight_max | 0.5 | 不变 |
| initial_weight（热束）| 0.02 | 不变 |
| lambda_yolk | 0.0015 | 拉长续航 |
| yolk_initial_level | 500 | 不变 |
| lateral_gain | 0.3 | 不变 |
| Langevin tau | 3.0 | 不变 |
| 出生点 | [75,20,25] | 不变 |


## 六、执行步骤（修正版，5 步）

### 步骤 0：前庭 v2.0 状态确认（新增）

运行前庭诊断，确认 v2.0 已作为默认驱动模式运行：

```bash
python -m nexus_v1.tests.diag_vestibular_v2_status
```

确认项：
- `VESTIBULAR_MODE == "V2_ACTIVE_DRIVE"` ✅
- 软饱和已生效（无硬截断尖峰）
- G_eff 在初始能量 50% 下约为 8.4±0.5
- 前庭→Motor 输出量级已测量（记录 baseline，供 §4 标定参考）

**若前庭诊断未通过**：回退至 `V2_PARALLEL_LOG`，暂不执行 Phase 5，先排查前庭 v2.0 集成问题。

### 步骤 1：热觉链路配置确认

```bash
python -m nexus_v1.tests.run_full_audit.py
```

应显示：
```
soma_noci V ∈ [-0.3, 0.25]  ✅
reg_therm avg ∈ [0.45, 0.60]  ✅
Shadow census: 21 neurons  ✅
col_therm_* act > 0.001  ✅
```

### 步骤 2：应用 Phase 5 参数配置

**Column 热列增益调优**（`hebbian.py`）：
- 优先调整 `synapse_gain`（硬件级阻抗匹配），保持 `initial_weight=0.02` 不变
- 将 `synapse_gain` 提升 1.2-1.5 倍（例如从 3.0 提至 4.0-4.5）
- 若 col_therm V 仍 <0.21，检查 TemporalCoupler 过载情况

**DEVIATION_MOTOR_GAIN**（`variant_adapter.py`）：
- 使用步骤 0 的测量结果决定最终值
- 若前庭 v2.0 单独驱动已足够 → 设为 1.0
- 若不足 → 按实测偏差调整，并标记为临时补偿

**学习与代谢参数**（`hebbian.py` 热束配置、`yolk_sac.py`）：
- `stdp_lr = 0.005`
- `lambda_yolk = 0.0015`

### 步骤 3：创建 Phase 5 实验脚本

基于 Phase 4 脚本（`exp_phase4_directional.py`），应用修正后的参数：

- `stdp_lr` 0.05 → 0.005
- `lambda_yolk` 0.001 → 0.0015
- `DA_INJECT_SCALE = 0.014`
- `DEVIATION_MOTOR_GAIN` = 步骤 2 标定值
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


## 七、验收标准（不变）

| 标准 | 目标 | 说明 |
| :--- | :--- | :--- |
| DR1 | \|w_left - w_right\| > 0.02（500k 步终点）| 方向性权重分化 |
| DR2 | Δy(200k) > 1.0 | 宏观位移 |
| DR3 | fill > 0 全程 | 代谢生存 |
| DR4 | 分化在 200k 步内出现，持续 >50k 步 | 非瞬时分化 |
| DR5 | grad_dot_v 在分化后持续为正 | 热趋向对齐度 |
| DR6 | DA 3/3 不持续饱和 | 动态范围保留 |


## 八、应急调整（4 项，新增第 4 项）

### 8.1 DA 动态范围保护

若 100k 步时 DA 神经元膜电位持续在 v_peak 附近徘徊，立即将 `DA_INJECT_SCALE` 下调 20-50%。

### 8.2 空间侧抑制应急

若 100k 步时 \|Δw\| < 0.005，立即将 `lateral_gain` 从 0.3 提升至 0.5-0.8。

### 8.3 grad_dot_v 实时监控

持续观察 `thermal_alignment` 输出：
- `grad_dot_v > 0` 持续出现 → 系统正向热源移动
- `grad_dot_v > 0` 持续但 \|Δw\| 仍低 → 考虑提升 `stdp_lr` 至 0.01

### 8.4 前庭 v2.0 行为贡献异常（新增）

若 100k 步时发现：
- 前庭驱动位移 >50 单位，与热趋向运动混合
- 或位移方向与热源无关（前庭压制了热趋向）

应急措施：
1. 检查 G_eff 是否异常升高（>12）
2. 若 G_eff 正常，检查 Motor 叠加中前庭/热觉增益比例
3. 必要时将 `VESTIBULAR_MODE` 回退至 `V2_PARALLEL_LOG`（前庭只记录不驱动）


## 九、执行时间线（修正版）

| 步骤 | 内容 | 预计时间 |
| :--- | :--- | :--- |
| 0 | 前庭 v2.0 状态确认 + Motor 响应标定 | 10 分钟 |
| 1 | 热觉链路配置确认 | 5 分钟 |
| 2 | 应用 Phase 5 参数（含增益调优）| 15 分钟 |
| 3 | 创建/更新实验脚本 | 10 分钟 |
| 4 | 10k 步探测测试 | 1 分钟 |
| 5 | 500k 步实验 | ~35 分钟 |

**总计**：约 1.5 小时（含新增的前庭标定）


## 十、回退条件（不变）

如 Phase 5 实验后仍无方向性分化，按以下顺序排查：

1. 检查 `grad_dot_v` 是否在分化窗口期出现正偏
2. 检查 `col_therm_*.ema` 是否 >0.05
3. 检查 DA 在进食事件后是否 >0.01（非饱和）
4. 检查 fill 是否在 250k 步前归零
5. 若前述 4 项全部通过但仍无分化 → 增大 `lateral_gain` 或延长 Langevin τ


**方案确认后即可执行。** 本方案已将前庭 v2.0 的接入状态完整纳入，并明确了热觉迁移至 v2.0 不阻塞 Phase 5 的结论。核心实验目标（方向性分化验证）与验收标准均未改变。