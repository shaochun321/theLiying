# S.07 + A8 综合诊断报告

> **Date**: 2026-06-08 01:47

---

## 结果概要

| 验证 | 结果 | 发现 |
|---|---|---|
| **S.07 B-layer** | ✅ 存活 | 37/40 coupler 有 V_slow ≠ 0，但效应微弱 (±1.5%) |
| **A8 影子层收敛** | ❌ 不收敛 | ratio=18.4，enc→col 冻结，col→mot 单调衰减 |

---

## §1 B-layer 详情

```
40 couplers, 全部 B-layer enabled
37/40 V_slow ≠ 0 → B-layer 在工作

V_slow 范围:
  vest→enc:  -0.017 (负 = 下游活动 > 上游 → 减小 τ)
  enc→col:   -0.004 (负)
  col→mot:   +0.005 (正 = 上游 > 下游 → 增大 τ)

R_leak 调制:  1.93 ~ 2.03 (基线 2.0, 变化 ±1.5%)
τ_eff:        0.69 ~ 0.76 (vs τ_base = 2.0)
```

**诊断**: B-layer 存活但效应微弱。C-layer 占主导（τ_eff/τ_base = 0.35，65% 缩减来自 C-layer 自适应）。B-layer 的 ±1.5% 调制被 C-layer 的 65% 缩减淹没。

**不是阻断性问题** — B-layer 机制正确，只需调参（增大 blayer_gm 或 blayer_k）。

---

## §2 影子层：三个根因

### 根因 1：deviation 公式单向

```python
# circulation_proportion.py L161
deviation_input = max(0.0, v_ref - rho_h)
#                          0.7  - 0.87  = -0.17
#                     max(0, -0.17) = 0.0  ← 永远不触发！
```

ρ_homeo = 0.87 > setpoint 0.7，但公式只检测 ρ_homeo **下降**。
当前系统热稳定性高（体始于热源附近），所以 ρ_homeo 一直偏高。

**修复**: 改为双向检测 `deviation = |v_ref - rho_h|`，或接受单向但需要先有"扰动"使 ρ_homeo 下降。

### 根因 2：影子层 enc→col 权重冻结

```
W_shadow enc→col: 0.1001 不变 (100k 步)
```

BCM 学习规则需要 post 活动超过滑动阈值 θ 才能产生 LTP。
shadow col 有 spiking=True，但 calcium_rate 可能太低触不动 BCM θ。

**影子层接收的是 Xin 输入 (K_ema ≈ 4.8 亿)，但 DivisiveNorm 把它压到极小值。** enc→col 的 BCM 看到的 post 信号太弱。

### 根因 3：DA 无调制

```
DA = 0.018 恒定 (100k 步)
shadow→DA weight = 0.007 (极弱)
xin→DA weight = 0.062
xin_tension = -17.96 (巨大负值)
```

xin_relay 应该被 -17.96 的 Xin 驱动，但 Xin relay 是 abs(xi) 输入（正值）→ DA 应该有输入。问题：D2R 自受体 (d2_ec50=0.3) 在 DA=0.018 时不激活（太低），所以 D2R 不是瓶颈。

**瓶颈在 shadow→DA bundle 权重 = 0.007**。Shadow col 的 calcium_rate 太低 → STDP 没有足够的 pre-post 相关性来增强权重。

---

## §3 影响分析

```
阻断链:
  影子层 BCM 冻结 → 没有"正常态"吸引子
    → deviation = 0 (公式+数据双重归零)
      → DA 无调制
        → 三因子学习无差异化
          → 无热趋性行为
```

**所有问题都串行依赖。** 修复顺序：

1. deviation 公式 → 双向化（最简单）
2. 影子层 BCM 输入强度 → 验证 DivisiveNorm 输出是否足够
3. shadow→DA 权重初始化 → 可能需要更高初始值

---

## §4 与"人工进化"的关系

你说的"帮其选取环流耦合的区间和结构"，现在有具体目标了：

### 需要"选择"的参数（基因编码等价物）

| 参数 | 当前值 | 问题 | 候选调整 |
|---|---|---|---|
| `homeo_set_point` | 0.7 | 公式单向 | 改为双向 abs() |
| `deviation_threshold` | 0.05 | 从未触发 | 降到 0.01 |
| `deviation_gain` | 0.3 | 从未触发 | 提高到 1.0 |
| `blayer_k` | 2.0 | B-layer 效应弱 | 提高到 10.0 |
| shadow BCM `theta_m_tau` | 100 | 太快 | 提高到 10000 |
| shadow→DA `initial_weight` | 隐式 ~0.007 | 太弱 | 提高到 0.05 |

### 执行方案

```
Step 1: 修 deviation 公式（双向）+ 降阈值
Step 2: 提高 shadow→DA 初始权重 + BCM tau
Step 3: 跑 100k 验证 DA 调制 ≠ 0
Step 4: 如果 DA 有调制 → 跑热趋性测试
Step 5: 人工进化选择 → 保留使 distance_to_heat↓ 的参数
```

> [!IMPORTANT]
> **这些参数调整不是"hack"**——它们是系统的"先天基因"。
> 真实生物的 hypothalamic setpoint 也是基因编码的，不是学来的。
> 我们作为构建者选择这些参数 = 自然选择优化这些基因。
