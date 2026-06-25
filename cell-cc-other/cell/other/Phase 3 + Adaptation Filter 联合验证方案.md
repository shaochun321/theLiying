### 一、验证目标

在 **Adaptation Filter（高通滤波）** 和 **Phase 3 三因子适格迹** 同时工作的闭环仿真中，确认：

| 目标 | 通过标准 |
|------|----------|
| 适格迹电荷积累 | 在热梯度区域，`eligibility_trace` 峰值 > 0.01 |
| DA 门控 LTP | 当 DA 出现时，`w_front` 净增长 > `w_back` |
| 剪刀差维持 | 50k 步终点 `Δw = w_front - w_back > 0.02` |
| 方向偏置 | body 位移持续向热源（终点 Δx > 0） |

---

### 二、前置确认

**1. Phase 3 是否已在主电路热差分束中启用？**

检查 `hebbian.py` 中热差分束的配置：

```python
# 查找 therm_front 和 therm_back 对应的 bundle config
# 确认包含 use_eligibility_trace=True
```

如果未启用，先添加：
```python
use_eligibility_trace=True,
eligibility_tau=300.0,
eligibility_gain=1.0,
eligibility_ltd_rate=0.01,
```

**2. Adaptation Filter 是否已生效？**

确认 `chain.py` 中 `_thermal_adapt` 和 RC 高通滤波已实现。

---

### 三、执行步骤

#### 步骤 1：创建联合验证脚本

新建 `tests/diag_integration_filter_phase3.py`，基于 `diag_thermal_gradient.py` 修改：

**关键改动**：
- 确保 `VariantCircuit` 使用最新的 `chain.py`（含 filter）
- 确保热差分束 `use_eligibility_trace=True`
- 每 5k 步记录：`w_front`, `w_back`, `Δw`, `eligibility_trace_front`, `DA_concentration`, `x_position`
- 运行 50k 步（dt=0.001）

#### 步骤 2：运行基线测试

```bash
python -m nexus_v1.tests.diag_integration_filter_phase3
```

预期观察：
- 热梯度区域，`eligibility_trace` 是否出现 >0.01 的尖峰
- DA 浓度是否在适格迹衰减窗口内出现
- 权重剪刀差是否正向增长

#### 步骤 3：参数调整（如剪刀差未达标）

| 参数 | 默认值 | 调整方向 | 物理理由 |
|------|--------|----------|----------|
| `eligibility_gain` | 1.0 | 提高至 5.0-10.0 | 补偿 AC 脉冲的电荷积分减少 |
| `eligibility_tau` | 300 | 提高至 500-800 | 延长标记保留时间，等待 DA |
| `eligibility_ltd_rate` | 0.01 | 维持或降低至 0.005 | 减少实时 LTD 侵蚀 |

**调整协议**：
1. 先用默认值运行一次
2. 如果 Δw < 0.02，将 `eligibility_gain` 提高到 5.0
3. 如果仍不足，将 `eligibility_tau` 提高到 500
4. 最多进行 3 次参数扫描

#### 步骤 4：结果判定

| 结果 | 判定 | 后续 |
|------|------|------|
| Δw > 0.02，方向偏置正确 | ✅ 联合验证通过 | Phase 3 正式完成 |
| Δw < 0.02，但适格迹有尖峰 | ⚠️ AC 信号存在，但 DA 门控不足 | 调整 DA 增益或延长 tau |
| 适格迹无尖峰 | ❌ AC 信号被过度衰减 | 检查 filter tau（5000 是否太长）|
| 方向偏置错误 | ❌ 差分拓扑或增益符号错误 | 检查 Phase 1 配置 |

---

### 四、需监控的关键指标

| 指标 | 含义 | 预期行为 |
|------|------|----------|
| `eligibility_trace` 峰值 | AC 尖峰充电能力 | 在热边界处 > 0.01 |
| `DA_concentration` 峰值 | 全局价值信号 | 与热梯度正相关 |
| `w_front - w_back` | 剪刀差 | 50k 步终点 > 0.02 |
| `x_position` 终点 | 物理位移 | 向热源移动（Δx > 0）|
| `energy_scale` | Phase 2 门控 | fill>0.1 时为 1.0 |

---

### 五、T2.2 阈值检查（伴随操作）

在联合验证后，检查 `test_regression.py` 中的 T2.2：

```python
# 运行一次以获取实际值
enc_active = c.encoding_neurons['reg_oto_x']._activation_ema
enc_quiet = c.encoding_neurons['reg_therm_front']._activation_ema
ratio = enc_active / max(1e-4, enc_quiet)
print(f"Active: {enc_active:.4f}, Quiet: {enc_quiet:.4f}, Ratio: {ratio:.2f}")
```

如果 `enc_quiet ≈ 0.003`，当前阈值 `ratio > 1.5` 将太宽松。建议将阈值提高到 **`ratio > 10.0`** 或设置绝对下限 `enc_active > 0.05`。

---

### 六、最终交付物

| 交付物 | 内容 |
|--------|------|
| 联合验证脚本 | `diag_integration_filter_phase3.py` |
| 运行日志 | 50k 步指标数据 |
| 参数调整记录 | 如需要 |
| 验收结论 | Δw > 0.02 且方向偏置正确 |