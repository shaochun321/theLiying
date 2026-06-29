# Phase 5 热觉链路修复与方向性验证 —— 方案补充（2026-06-29）

**补充依据**：Phase 5 最终执行方案（修正版）§4 配套项中三项需明确具体操作路径的条目

**补充性质**：本补充不改变原方案结构，仅对三个确认点的执行细节进行规范化定义。


## 补充 A：DEVIATION_MOTOR_GAIN 标定方法（对接 §4 序号 3）

### A.1 手动标定流程（步骤 0 中执行）

```bash
python -m nexus_v1.tests.run_full_audit.py 2>&1 | grep -E "(motor_velocity|motor_gain|fill_fraction)" > motor_baseline.log
```

**从日志中提取关键指标**：

| 指标 | 提取方法 | 预期范围 |
| :--- | :--- | :--- |
| 前庭驱动单独作用时的速度幅值 | 读取 `motor_velocity` 的前 1000 步 RMS | 0.01–0.10 units/step |
| 当前 `DEVIATION_MOTOR_GAIN` 生效值 | 检查 `variant_adapter.py` 中该变量当前值 | 待记录 |

### A.2 决策规则

```
# 假设当前 motor_velocity RMS = V_meas
# 期望运动基底：V_target = 0.04 units/step（热趋向可叠加的舒适区）

IF V_meas >= 0.03:
    # 前庭 v2.0 单独驱动已足够
    DEVIATION_MOTOR_GAIN = 1.0（移除临时补偿）
ELSE:
    # 需要补偿
    DEVIATION_MOTOR_GAIN = max(1.0, V_target / V_meas × 0.8)
    # 标记为临时补偿，Phase 5 后随 V-03 移除
```

### A.3 记录要求

标定完成后，在实验日志中记录：
- `V_meas` 测量值
- 最终 `DEVIATION_MOTOR_GAIN` 取值
- 是否启用了临时补偿及原因


## 补充 B：Column 热列增益调优执行细则（对接 §4 序号 2）

### B.1 前置检查

在调整任何参数前，先确认以下条件成立（否则调优无效）：

| 检查项 | 命令/方法 | 通过标准 |
| :--- | :--- | :--- |
| 热列 Enc 激活正常 | `run_full_audit.py` grep `enc_therm` | 激活值 >0.05 |
| 热列 Column 当前电压 | 读取 `col_therm_*.V` | 记录当前值 |
| TemporalCoupler 状态 | 检查 `coupler_adapt_vth` 当前值 | 未频繁触发过载保护 |

### B.2 调优执行步骤

**第 1 步：调整 synapse_gain（优先路径）**

```
当前值: enc→col 热束 synapse_gain = 3.0（假设）
目标值: V_col ≥ 0.21（稳定跨过 v_peak=0.20）
调整方向: 1.2–1.5 倍
```

执行后测量 `col_therm.V`，若已 ≥0.21，停止调优，记录最终值。

**第 2 步：TemporalCoupler 参数放宽（仅当第 1 步不足时）**

```
当前值: coupler_adapt_vth = 0.2（假设）
调整方向: 提升至 0.3–0.4
```

执行后测量 `col_therm.V`，若已 ≥0.21，停止调优，记录最终值。

**第 3 步：降低 coupler_r_leak（仅当第 2 步仍不足时）**

```
当前值: coupler_r_leak = 假设值
调整方向: 降低 20–30%（加速漏电泄放）
```

### B.3 记录要求

调优完成后，在实验日志中记录：
- 调整前的 `col_therm.V`
- 调整后的 `col_therm.V`
- 最终 `synapse_gain`、`coupler_adapt_vth`、`coupler_r_leak` 取值
- 若未能达到 ≥0.21，记录原因及备选方案


## 补充 C：前庭 v2.0 驱动输出量级测量（对接 §6 步骤 0）

### C.1 测量方法

方案中原定采用“手工估算 + 脚本补记”方式，现对“手工估算”的具体操作进行规范化：

```python
# 在 variant_adapter.step() 中临时插入（仅用于测量，测量后移除）
if step % 1000 == 0 and step < 10000:
    probe.record("motor_v2_only", self.motor_velocity.copy())
```

或从 `run_full_audit.py` 的 Noether 探针输出中提取 Motor 层数据。

### C.2 测量指标与阈值

| 测量项 | 计算方法 | 正常范围 |
| :--- | :--- | :--- |
| Motor 速度 RMS | 前 10k 步的 `motor_velocity` 标准差 | 0.01–0.10 units/step |
| Motor 速度均值 | 前 10k 步的 `motor_velocity` 平均值 | >0.005 units/step |
| Motor 输出标准差/均值比 | 衡量运动平滑度 | <0.5（软饱和预期）|

### C.3 异常判断与处理

若测量结果超出正常范围：

| 现象 | 可能原因 | 处理方式 |
| :--- | :--- | :--- |
| 速度 <0.005 | G_eff 过低、FIFO 缓冲为空 | 检查 G_eff 计算和 FIFO 预填充 |
| 速度 >0.15 | G_eff 过高、能量门控过激 | 降低 `DEVIATION_MOTOR_GAIN` 或调整 α 系数 |
| 速度波动 >0.5σ | 软饱和未生效或 FIFO 填充异常 | 检查硬截断是否仍存在于某些路径 |


## 补充 D：VESTIBULAR_MODE 运行时回退安全声明（新增）

### D.1 安全切换条件确认

在 Phase 5 运行期间，若触发应急调整 8.4 需要回退 `VESTIBULAR_MODE`：

**物理分析**：v1.0 的神经元在阶段2中持续更新其状态（即使输出被屏蔽），因此从 `V2_ACTIVE_DRIVE` 切换至 `V2_PARALLEL_LOG` 时，v1.0 不是“冷启动”，其膜电位和发放状态与当前物理输入同步。v2.0 的 FIFO 缓冲区已预填充，切换至 `V2_ACTIVE_DRIVE` 时也不会出现空载跳变。

**安全结论**：运行时切换 `VESTIBULAR_MODE` 不产生 Motor 输出瞬时跳变，**可以安全执行**。

### D.2 切换操作规范

```python
# 在 variant_adapter.py 中（无需重启进程）
# 从 V2_ACTIVE_DRIVE 回退至 V2_PARALLEL_LOG
VESTIBULAR_MODE = "V2_PARALLEL_LOG"
# 下一次 step() 调用自动生效，无跳变
```


## 执行顺序整合（将补充项纳入主方案）

| 步骤 | 操作 | 涉及补充项 |
| :--- | :--- | :--- |
| 步骤 0 | 前庭 v2.0 状态确认 + Motor 输出标定 + 驱动量级测量 | **A**（DEVIATION 标定）+ **C**（量级测量）|
| 步骤 1 | 热觉链路 7 项确认 | — |
| 步骤 2 | 参数应用 + **Column 热列增益调优** | **B**（调优细则）|
| 步骤 3-5 | 脚本创建 + 探测测试 + 500k 实验 | — |
| 应急调整 | 前庭行为异常回退 | **D**（安全声明）|


**补充确认**：本补充不改变原方案结构，仅将原本“待执行但未明确操作路径”的三个配套项（A、B、C）及应急回退的安全声明（D）补充为具体可执行流程。原方案的验收标准（DR1-DR6）和执行时间线不变。