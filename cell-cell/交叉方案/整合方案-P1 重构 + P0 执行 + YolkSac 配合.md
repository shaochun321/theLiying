

### 一、外部审计官的主要建议

| 建议 | 我的判断 | 采纳 |
|------|----------|------|
| P0 回退 v_peak 到 0.10 通过 | 正确，是最小侵入的合法修复 | ✅ |
| P1 不应给 RPE 加 baseline | 同意——RPE 加 baseline 违反其物理定义 | ✅ |
| P1 用绝对饥饿信号（旧 DA 系统）与 RPE 取 max | 更物理的保底机制，不污染 RPE | ✅ |
| YolkSac 降低释放速率至 0.001/步，500 单位不变 | 制造缓慢能量下降压力 | ✅ |

### 二、P1 重构方案

**原方案问题**：给 RPE 加常数 baseline=0.02，是在“没有奖励”的情况下强制 DA 输出，污染学习信号。

**新方案**：DA 输出取 RPE 与绝对饥饿信号的**较大值**。

```
DA = max(
    RPE(t) = max(0, η_da × (fill_t - fill_{t-1}) / dt),
    Hunger(t) = max(0, θ_hunger × (0.5 - fill_t))
)
```

- `RPE`：从 `DADifferentialGate` 输出
- `Hunger`：从旧的 `circulation_proportion` 或简化阈值函数输出
- `θ_hunger = 1.0`：饥饿信号增益（待标定），目标是在 fill 接近 0.2 时产生 ~0.3 的 DA 信号

当能量储备满载时，饥饿信号归零，RPE 接管；当能量濒危时（fill 从 0.5 下降至 0.2 以下），饥饿信号强制输出，打破僵局。此机制是纯物理的——饥饿信号是 fill 的绝对阈值函数，没有语义标签（不是“饥饿”这个标签驱动行为，而是低能量储备产生的物理信号），与 RPE 同源。

**实施位置**：`variant_adapter.py` 中 DA 驱动段，在 `da_gate.step()` 之后：

```python
rpe_da = self.da_gate.step(fill_fraction, dt)
hunger_da = self._hunger_signal.step(fill_fraction)  # 新增
da_drive = max(rpe_da, hunger_da)
```

### 三、YolkSac 调整

| 参数 | 旧值 | 新值 | 效果 |
|------|------|------|------|
| `lambda_yolk` | 0.002/步 | **0.001/步** | 释放速率减半 |
| `initial_level` | 500 | **500**（不变）| 释放时间从 250k 步延长至 500k 步 |

**计算校验**：
- 释放速率减半后，总释放时间 = 500 / 0.001 = 500,000 步
- fill 下降速率 ≈ 代谢消耗（~0.0005/步）- 释放（0.001/步）= 0.0005/步（下降）——产生缓慢的饥饿信号
- YolkSac 耗尽时，STDP 已有充足的学习窗口

### 四、三刀整合

| 优先级 | 修复 | 操作 | 文件 |
|--------|------|------|------|
| **P0** | Column 放电 | `v_peak`: 0.25 → 0.10 | `hebbian.py` |
| **P1** | DA 非零 | RPE 与饥饿信号取 max | `variant_adapter.py` |
| **P1 配套** | YolkSac 调整 | `lambda_yolk`: 0.002 → 0.001 | `yolk_sac.py` |

**不再执行**：
- DA baseline=0.02（被 max 方案替代）
- P2（Shadow 静默，保持现状）

### 五、执行顺序

1. 回退 Column v_peak 到 0.10
2. 将 YolkSac lambda_yolk 降至 0.001/步
3. 在 variant_adapter 中实现 DA = max(RPE, Hunger)
4. 运行 5k 步诊断：确认 column EMA > 0.1，DA > 0.01
5. 运行 100k 步实验：观察方向性权重分化

### 六、回退条件

如果在 100k 步后仍无方向性分化，优先检查以下两项：

| 检查项 | 方法 | 预期 |
|--------|------|------|
| Column 是否放电 | 检查 `col_therm_front.ema` | >0.1 |
| RPE 与饥饿信号的竞争窗口 | 检查 DA 输出是否来自饥饿信号而非 RPE | 饥饿信号占主导表示尚未发生有效进食 |
| 权重分化 | 检查 therm 四方向权重差值 | 至少一对 >0.02 |
| 代谢平衡 | 检查 fill 是否仍在下降 | 下降速率应低于 0.0005/步，否则表示窗口不足 |