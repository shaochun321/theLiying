# STDP 冻结根因分析 + DA 链路完整审计

**日期**: 2026-07-08
**前置**: DA 架构分析报告 (DA_architecture_report_2026-07-08.md)
**状态**: 根因确认

---

## 执行摘要

经过完整的链路追踪，发现以下关键事实：

1. **CPG 通路是化石** — 为旧版两因子 STDP 设计，在三因子 eligibility trace 架构下不再有功能
2. **真正的冻结风险是 "源端静默"** — proj 神经元不发放 → pre_trace 衰减 → eligibility trace 停止充电 → LTP 归零
3. **pre_trace 公式有标度问题** — 脉冲神经元的 pre_trace 是不规范的"漏式累加器"，稳态值可达 `20.5×发放率`，极易触达 clamp=10
4. **E(t) (τ=300) 和 DA_ema (τ=5000) 的时间尺度失配** — 导致时间信用分配模糊

---

## 第一部分：CPG 通路 — 为何是化石

### 1.1 CPG 的设计意图

`variant_adapter.py:3037-3039`:
> "CPG 2Hz pacemaker → keeps DA.post_trace > 0 at steady state so relay_to_da STDP stays active"

CPG 是一个 2Hz Van der Pol 振荡器，通过 `cpg_to_da` 束（frozen, w=0.1, sg=0.1）对 DA 神经元注入微小振荡。振幅经 Phase-B 衰减 10× 后约 0.0011V。

### 1.2 为什么它不再有效

`bundle.py` 的 `learn()` 有四条学习路径：

| 路径 | 条件 | 读取 `tgt.post_trace`? |
|------|------|:---:|
| 三因子 eligibility | `use_eligibility_trace=True` | **否** |
| 两因子 STDP | `use_eligibility_trace=False` | **是** |
| BCM | maturation=1 | 否 |
| Hebbian decay | cross_axis | 否 |

**`relay_to_da` 束使用 `use_eligibility_trace=True`**（`variant_adapter.py:3021`）。三因子路径读的是 `_get_activity_signal(tgt)`，对非脉冲 DA 神经元返回 `_activation_ema`，**不是** `post_trace`。

### 1.3 CPG 移除后的影响

- `relay_to_da` STDP：不受影响（三因子路径不读 post_trace）
- DA 神经元 `post_trace`：从"极小正值"变为 0
- DA 浓度：`_activation_ema` 从 ~0.09+ε 变为 ~0.09，DA_ema 几乎无变化
- **唯一读取 `tgt.post_trace` 的两因子 STDP 路径**：当前代码中没有任何两因子 STDP 束以 DA 神经元为目标，所以不影响

**结论：CPG 可以安全移除。它是在两因子→三因子迁移时遗漏的残骸。**

### 1.4 暴露的深层问题

迁移时缺乏依赖审计。"谁依赖 post_trace？" 这个问题的答案从未被系统性地验证过。CPG 注释声称它解决 post_trace=0 导致 STDP 冻结，但迁移后 STDP 不再读 post_trace，注释变成误导。

---

## 第二部分：真正的冻结路径 —— "源端静默"

### 2.1 完整信号链

```
身体位置 → 皮肤温度 → ThermoInput → Thermoreceptor → Relay → Proj → DA STDP
```

### 2.2 逐级分析

#### Level 1: 皮肤温度

`world.py:Body.sample_skin()` → 12 个 SkinPatch → `World.temperature_at(pos)`

```python
T_env = ambient(0.1) + Σ src.effective_temperature() × max(0, 1 - d/radius)
```

T-092 实验中：source 在 [70,50,25]，body 在 [10,50,25]，toroidal 距离 40，radius=30。身体在热源半径之外，T_env = 0.1（纯环境温度）。

#### Level 2: Relay 激活

Relay 非脉冲神经元（C=2.0, R=10.0, MOSFET v_th=0.3）：

| 场景 | T_skin | ThermoInput.act | Relay.act (估算) |
|------|--------|-----------------|------------------|
| d > 30（OFF 期） | ~0.1 | 0.05 | **≈ 0** |
| d = 20 | ~1.77 | 1.72 | ~3.2 |
| d = 5 | ~4.27 | 4.22 | ~8.3 |

**结论：OFF 期间 relay 激活趋近于 0。**

#### Level 3: Proj 神经元发放

Proj 神经元（脉冲型，v_peak=0.05, C=0.1, R=1.0）：

```
I_proj = G(w=0.3) × relay_act × 1.0 ≈ 0.142 × relay_act
V_ss = I × R = 0.142 × relay_act

需要 V > 0.05 才发放 → relay_act > 0.05/0.142 ≈ 0.35
```

- relay_act < 0.35 → **proj 不发放** → pre_trace 衰减
- relay_act ≥ 0.35 → proj 发放 → pre_trace 充电

#### Level 4: Eligibility Trace 充电

```python
# bundle.py:400-403
E[i][j] = E[i][j] × (1 - dt/300) + src.pre_trace × post_act × dt

# post_act = _get_activity_signal(DA_neuron) = DA._activation_ema
```

`src.pre_trace` 是 proj 神经元的 pre_trace。对于**脉冲神经元**：

```python
# neuron.py:589
pre_trace[t] = pre_trace[t-1] × exp(-dt/0.02) + abs(activation)
             = pre_trace[t-1] × 0.9512 + (1 if spiked else 0)
```

**这不是标准 EMA。** 这是漏式累加器。稳态值：

```
pre_trace_ss = f_spike / (1 - 0.9512) = f_spike × 20.49
```

| proj 发放率 | pre_trace_ss | 效果 |
|-------------|-------------|------|
| 0（OFF 期） | **0** | E 停止充电，衰减 |
| 0.01（100步/次） | 0.20 | E 缓慢充电 |
| 0.05（20步/次） | 1.02 | E 正常充电 |
| 0.1（10步/次） | 2.05 | E 快速充电 |
| 0.5（2步/次） | 10.25 → **clamp=10** | E 饱和充电 |

**关键：proj 一旦停发，pre_trace 在 ~40 步内衰减到 <10%，~100 步内接近 0。**

Eligibility trace E(t) 衰减：
```
E(t + k) = E(t) × (1 - 1/300)^k
k=300: E → 37%
k=1500: E → 0.7%
```

**OFF 期持续 12000 步。Proj 在整个 OFF 期不发放。E(t) 在前 1500 步已衰减殆尽。**

---

## 第三部分：pre_trace 公式的标度问题

### 3.1 当前公式

```python
# 脉冲神经元
pre_trace[t] = pre_trace[t-1] × decay_pre + abs(activation)

# decay_pre = exp(-dt / (trace_tau_pre × 0.001))
#            = exp(-0.001 / 0.02) = 0.9512
```

### 3.2 标准 EMA 应该是什么

```python
# 标准 EMA
pre_trace[t] = pre_trace[t-1] × decay + abs(activation) × (1 - decay)
```

当前公式缺了 `(1 - decay)` 缩放因子。在稳态：
- 当前：`pre_trace_ss = |act| / (1 - decay) = |act| × 20.5`
- 标准：`pre_trace_ss = |act|`（EMA 的无偏估计）

### 3.3 影响

proj 神经元发放一次（activation=1），pre_trace 跳升 1.0。在 τ_pre=20ms 下，这需要 ~40 步衰减。如果发放率 > 0.05，pre_trace 累积到 > 1.0，使 E(t) 充电速度比预期快 20 倍。

**E(t) 充电速率公式（代入典型值）：**

```
# proj 以 0.1 发放率（10步/次），pre_trace ≈ 2.05
# DA 神经元 _activation_ema ≈ 0.09
# E 增量 = 2.05 × 0.09 × 0.001 = 0.000185/步
# E 稳态 = 0.000185 × 300 = 0.055
# LTP = 1.0 × 0.055 × DA_ema = 0.055 × DA_ema
```

如果修正为 EMA：pre_trace ≈ 0.1 × 1.0 = 0.1，E 稳态 = 0.0027，LTP = 0.0027 × DA_ema — **差了 20 倍**。

### 3.4 pre_trace 和 post_trace 的语义不对称

| 变量 | 脉冲神经元 | 非脉冲神经元 |
|------|-----------|-------------|
| `pre_trace` | 漏式累加 spike count (0/1) | 漏式累加 `|activation|` (连续) |
| `post_trace` | 漏式累加 spike count (0/1) | 漏式累加 `|d(act)/dt|` (变化率) |

对脉冲神经元，pre_trace 和 post_trace **完全相同**（都累加 `|activation|`，即 spike 的 0/1）。这违反了 `NeuronConfig` 中注释声明的设计意图：

```python
# neuron.py:96-98
# NOTE: pre_trace and post_trace use DIFFERENT input signals
# pre_trace ← |activation| (level)
# post_trace ← |d(activation)/dt| (change rate)
```

这个"对称性打破"只对非脉冲神经元成立。对脉冲神经元，两者退化为同一个量。

---

## 第四部分：时间尺度失配

### 4.1 各时间常数一览

| 变量 | τ | 衰减到 37% | 功能 |
|------|-----|-----------|------|
| pre_trace | 20ms | 20步 | 源发放率 EMA |
| post_trace | 20ms | 20步 | 目标变化率 EMA |
| _activation_ema | 100ms | 100步 | 目标激活 EMA（硬编码 α=0.01）|
| Eligibility E(t) | 300 | 300步 | 突触共现记忆 |
| DA 神经元膜 | 2s | 2000步 | DA 浓度积分 |
| D2R 局部 [DA] | 1s | 1000步 | DA 自受体负反馈 |
| **DA_ema** | **5000** | **5000步** | DA 平滑 |
| 行为周期 ON | 8000步 | — | 热源活跃 |
| 行为周期 OFF | 12000步 | — | 热源关闭 |

### 4.2 关键失配

```
E(t) 记忆窗口:  ~300步
DA_ema 窗口:    ~5000步  (16.7×)
```

**场景：OFF→ON 转换**

1. Proj 开始发放 → pre_trace 在 ~40 步内建立 → E 开始充电
2. E 在 ~300 步内达到稳态
3. DA_ema 仍反映 OFF 期的 DA 水平（需要 ~5000 步才收敛到 ON 期水平）
4. **结果：E 代表了"当前 ON 期行为"，但 DA_ema 代表了"过去 5000 步的 DA 平均水平"**
5. 如果 OFF 期 hunger 导致 DA 偏高，ON 初期的行为会获得**不应有的高 LTP**

**场景：ON→OFF 转换**

1. Proj 停止发放 → pre_trace 在 ~100 步内衰减 → E 在 ~1500 步内衰减殆尽
2. DA_ema 仍在高位（ON 期 DA 水平的余晖）
3. **结果：OFF 初期的行为完全没有 E 支持（E=0），即使 DA_ema 还很高，LTP=0**
4. 但 DA_ema 衰减到 0 需要 ~5000 步 → 前 5000 步的 OFF 期内如果有任何其他通路激活 proj，就会获得有 DA_ema 加持的 LTP

---

## 第五部分：汇总 —— STDP 真正的冻结条件

### 5.1 什么时候 STDP 真正冻结？

三因子 eligibility trace 路径：

```
LTP = eligibility_gain × E(t) × DA_ema

E(t) 充电条件: src.pre_trace > 0 AND tgt._activation_ema > 0
E(t) 衰减: τ = 300 步
```

| 条件 | LTP 状态 | 触发场景 |
|------|---------|---------|
| proj 发放 + DA_ema > 0 | **活跃** | ON 期，身体近热源 |
| proj 停发 + DA_ema > 0 | **冻结**（E=0） | OFF 初期，DA_ema 余晖 |
| proj 停发 + DA_ema ≈ 0 | **深度冻结** | 长时间 OFF + 饱腹 |
| proj 发放 + DA_ema ≈ 0 | **弱 LTP** | ON 期但 DA 被 satiety 压制 |

### 5.2 核心矛盾

**DA_ema 过期了。** E(t) 的时间精度（300步）被 DA_ema（5000步）拖累。当前机制无法将学习归因到精确的行为时刻：

- 行为发生后 300 步：E(t) 已衰减 63%，无法再被 DA 门控
- 但 DA_ema 反映的是 5000 步窗口内的 DA，其中大部分与当前 E(t) 代表的行为无关

### 5.3 CPG 无法解决任何这些问题

即使 CPG 如设计的那样工作（保持 post_trace > 0），它也只影响两因子 STDP 路径。对于三因子路径：
- post_trace 完全不参与计算
- CPG 的微弱振荡（~0.001V）对 `_activation_ema` 的影响在 `bc_current=0.1 → activation≈0.09` 面前可以忽略
- DA_ema（τ=5000）会把 2Hz 振荡彻底平滑掉

---

## 第六部分：发现的所有问题汇总

| # | 问题 | 严重度 | 位置 |
|---|------|--------|------|
| 1 | CPG 是化石 — 为两因子 STDP 设计，三因子路径不读 post_trace | 中 | `cpg_neuron.py`, `variant_adapter.py:3037` |
| 2 | pre_trace 公式缺 `(1-decay)` 缩放 — 稳态值放大约 20.5× | **高** | `neuron.py:589` |
| 3 | 脉冲神经元的 pre_trace 和 post_trace 退化相同 — 违反设计意图 | 中 | `neuron.py:589,592` |
| 4 | E(t) τ=300 vs DA_ema τ=5000 — 时间尺度失配 16.7× | **高** | `bundle.py:121,399` |
| 5 | _activation_ema 硬编码 α=0.01，独立于任何配置参数 | 低 | `neuron.py:603` |
| 6 | 真正的冻结风险是"源端静默"（proj 不发放），不是 post_trace | **高** | relay→proj→DA 链路 |
| 7 | `gain_factor()` 身兼两职（突触调制 + 学习门控） | 中 | `modulator.py:171`, `variant_adapter.py:2483,2686` |
| 8 | `dopamine.step()` 死代码 — 存在但从不调用 | 低 | `modulator.py:136` |
| 9 | D2Autoreceptor 类默认 `da_r_leak=100.0` vs 配置 `d2_da_r_leak=1.0` — 需核实生效值 | 中 | `compensation.py:411`, `variant_adapter.py:657` |

---

## 第七部分：建议修复优先级

### P0: 修正 pre_trace 公式

```python
# 当前 (neuron.py:589):
self.pre_trace = self.pre_trace * decay_pre + abs(self.activation)

# 修正:
self.pre_trace = self.pre_trace * decay_pre + abs(self.activation) * (1.0 - decay_pre)
```

影响所有束的 eligibility trace 充电速率。这是**标度错误**，不是调参。

### P1: 对齐 E(t) 和 DA_ema 的时间尺度

- 方案 A: 缩短 DA_ema τ 到 200-500（匹配 eligibility）
- 方案 B: 引入双 DA_ema（快/慢），快通道用于 LTP 门控，慢通道用于上下文调制

### P2: 移除 CPG 通路

安全删除，不影响任何当前学习路径。

### P3: 修复 DA 门控语义

```python
# 当前:
LTP = η × E × DA_ema

# 修正:
LTP = η × E × max(0, DA_ema - DA_baseline)
```

### P4: 验证 D2R 的 da_r_leak 生效值

检查 `neuron.py` 中 `D2Autoreceptor` 实例化时是否使用配置值还是类默认值。

---

## 附录：关键文件速查

| 文件 | 行号 | 内容 |
|------|------|------|
| `components/neuron.py` | 589 | pre_trace 公式（脉冲 + 非脉冲） |
| `components/neuron.py` | 592-597 | post_trace 公式 |
| `components/neuron.py` | 603 | _activation_ema 硬编码 α=0.01 |
| `circuit/bundle.py` | 389-435 | 三因子 eligibility trace 学习 |
| `circuit/bundle.py` | 439 | 两因子 STDP（唯一读 post_trace 处） |
| `circuit/bundle.py` | 514-534 | _get_activity_signal() |
| `circuit/variant_adapter.py` | 2861-3192 | _init_da_circuit() — 全部 DA 输入通路 |
| `circuit/variant_adapter.py` | 2955-2977 | Proj 神经元配置 (v_peak=0.05, CRI clamp=1.0) |
| `circuit/variant_adapter.py` | 3009-3034 | relay_to_da STDP 束配置 |
| `circuit/variant_adapter.py` | 3037-3039 | CPG 通路注释（声称保持 post_trace>0） |
| `components/gated_reflex.py` | 66-75 | hunger→gain_gate 束配置 |
| `somatosensory/chain.py` | 212-233 | Relay 神经元配置 |
| `components/compensation.py` | 368-454 | D2Autoreceptor 实现 |
| `components/compensation.py` | 411 | D2R 类默认 da_r_leak=100.0 |
