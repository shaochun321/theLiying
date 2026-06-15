# Epoch 1 验证报告

> **Date**: 2026-06-08 01:59

---

## 判决：✅ 影子层控制阀苏醒

> DA 不再是 0.018 的死水。DA range = 0.6536，出现了潮汐调制。

---

## §1 修改清单 (Epoch 1 基因组)

| 修改 | 文件 | 旧→新 | 物理意义 |
|---|---|---|---|
| FIX-1 | circulation_proportion.py | `max(0,...)` → `abs(...)` | 全波整流，双向偏差检测 |
| FIX-2 | bundle.py | `_activation_ema` → `calcium_rate` | BCM 读正确的连续信号 |
| deviation_threshold | circulation_proportion.py | 0.05 → 0.01 | 降低死区 |
| deviation_gain | circulation_proportion.py | 0.3 → 1.0 | 增强 DA 响应 |
| theta_m_tau | shadow_sandbox.py | 100 → 10000 | 频域分离 |

---

## §2 数据

```
[10k] DA: range=[0.0000, 0.6536] Δ=0.6536  ← 初始爆发
      enc→col: 0.0996  col→mot: 0.0494  cross: 0.0011
      θ_m: 0.000199  cal_rate: 0.5556

[50k] DA: range=[0.0187, 0.0338] Δ=0.0150  ← 稳态调制
      enc→col: 0.1052  col→mot: 0.1490  cross: 0.0032
      θ_m: 0.005793  cal_rate: 0.9588
```

### 关键变化

| 指标 | 修复前 (A8) | Epoch 1 | 变化 |
|---|---|---|---|
| deviation | 0.0000 | 0.10-0.19 | **从零到有** |
| DA range | 0.0000 | 0.0150-0.6536 | **从零到有** |
| enc→col Δw | 0.0000 | +0.0056 | **BCM 解冻** |
| col→mot | 0.0456→0.0393 (衰减) | 0.0494→0.1490 (增长) | **方向反转** |
| cross | 0.0010 不变 | 0.0011→0.0032 | **跨轴苏醒** |

---

## §3 剩余问题

### shadow→DA 权重持续衰减

```
shadow→DA: 0.042 → 0.019 (50k 内 -55%)
```

**原因**: shadow→DA bundle 的 targets 是 DA 神经元 (maturation=0 → STDP)。
DA 神经元是 non-spiking，post_trace 追踪 |d(act)/dt|。
DA 活动平坦 → d(act)/dt ≈ 0 → post_trace ≈ 0 → LTP ≈ 0 → 只有 decay → LTD。

**影响**: 如果 shadow→DA 衰减到 0，shadow 对 DA 的直接调制消失。
但 xin→DA 权重 (0.076) 仍在，deviation→DA (C3') 仍在。
系统暂时可以依赖 C3' 路径。

**可能修复**: 将 shadow→DA bundle 的 learning_rule 设为 "frozen"（先天反射弧不可修改）。
这正是 6.8 分析中"脑干网状激活系统……生来就必须具备极粗的髓鞘"的实现。

### DA→行为闭环待验证

DA 在调制，但需要验证：
1. DA↑ → Column 增益↑ → Motor 输出↑ → body_speed↑ → ρ_motor↑ → ρ_homeo↓
2. ρ_homeo↓ → 接近 0.7 setpoint → deviation↓ → DA↓
3. 这是**负反馈**（稳定）还是**正反馈**（发散）？

当前数据：ρ_homeo 从 0.80→0.88（上升），deviation 从 0.10→0.19（上升），
DA 从 0.014→0.021（上升）。
**DA 上升未能使 ρ_homeo 下降** → DA→Motor 路径可能太弱，
或者 DA 增益调制 gain_factor 太小。

---

## §4 下一步

```
1. 将 shadow→DA learning_rule 设为 "frozen"（先天反射弧）
2. 验证 DA→Motor 的效应链：
   DA concentration → gain_factor() → Column 增益
   → Motor 输出 → body_speed → ρ_motor
3. 如果 DA→Motor 闭环确认，跑 100k 热趋性测试
4. 记录参数变更到 PARAM_CHANGELOG
```
