# DA 结构化回路：分析报告

> 2026-06-05 01:47 — 供明天思考

---

## 1. 完成了什么

### 1.1 结构搭建（已入代码）

DA 通路从"一行代码读一个 float"变成了真实的神经回路：

```
变更前：
  shadow._weight_change_ema ──[Python 变量]──→ dopamine.release(float)
  
变更后：
  Shadow col neurons ──[SynapticBundle, STDP]──→ DA neurons (3个)
  Xin relay neuron   ──[SynapticBundle, STDP]──→ DA neurons
  DA neuron.activation ─────────────────────────→ dopamine.concentration
```

**涉及的文件：**

- [variant_adapter.py](file:///d:/cell-cc/nexus_v1/circuit/variant_adapter.py)
  - `__init__`: 新增 3 个 DA neuron + 1 个 Xin relay neuron（L345-390）
  - `_init_da_circuit()`: 延迟初始化 shadow→DA 和 xin→DA bundles（L1098-1180）
  - `_update_neuromodulation()`: 结构化 DA 信号流（L627-695）
  - `get_all_neurons()` / `get_all_bundles()`: 纳入 DA 组件（L1182-1200）

- [shadow_sandbox.py](file:///d:/cell-cc/nexus_v1/components/shadow_sandbox.py)
  - `_construction_power` 设为 False（L149）

### 1.2 熵账本集成（已验证）

| 检查项 | 状态 |
|--------|------|
| `get_all_neurons()` 包含 DA neurons + xin_relay | ✅ 62 neurons |
| `get_all_bundles()` 包含 shadow→DA + xin→DA | ✅ 41 bundles |
| Noether 能量守恒 | ✅ balance_avg < 0.004 |
| Noether 权重稳定性 | ✅ drift < 0.0005/step |
| Noether 违规 | ✅ 0 violations |
| 血管供能覆盖 DA neurons | ✅ 通过 get_all_neurons |
| 代谢税覆盖 DA bundles | ✅ 通过 get_all_bundles |

---

## 2. 发现的问题

### 2.1 影子层 col 激活值无限增长

这是最核心的问题。实验数据：

```
Step      s_col_yaw   s_col_pitch   s_col_therm   能量
 5000      0.094        0.105         0.033       0.95
10000      2.492        3.159         1.167       0.90
15000      5.173        4.110         0.694       0.85
20000      6.960        2.942         0.353       0.80
25000      6.948        2.105         0.179       0.75
```

> [!WARNING]
> s_col_yaw 激活值从 0.09 增长到 6.95——增长 77 倍。
> 这与 `construction_power` 无关（ON/OFF 结果一致）。
> 影子血管系统（base_flow=0.2）已提供足够能量（avg=0.8）。

**原因链**：
```
主层 Xin 持续增长 → XIN_GAIN 放大 → 影子 enc 输入增长
→ 影子 enc→col bundle 传播增长 → 影子 col 激活增长
→ 影子 col VoltageRegulator 未能有效限制
→ 影子 col 激活值达到 7.0
```

影子 col 的 VR 参数（来自 `create_shadow_config`）：
- `vr_base_rate=0.01`（非常弱）
- `vr_activity_coeff=0.5`
- `vr_max_rate=5.0`

当 activation=7.0 时：VR rate = min(0.01 + 0.5×7, 5.0) = 3.51。
这远小于输入电流（来自 synapse_gain=10.0 的 bundle），所以 VR 无法遏制增长。

### 2.2 差分对（exc + inh）完全对消

添加兴奋性 + 抑制性两条 shadow→DA 通路后，DA 永远为 0：

```
ExcW=0.045119  InhW=0.045825  → 净输入 ≈ 0 → DA = 0
```

**失败原因**：两条通路共享相同的源 neuron（shadow cols），权重初始值相同（0.05），STDP 学习相同的相关性。5× 的 lr 差异（0.005 vs 0.001）在绝对值极小的变化面前没有意义。

### 2.3 `construction_power` 不是根因

实验证明 ON/OFF 对影子层行为几乎无影响。但 `construction_power=False` 是正确的方向——它不该是永久脚手架。问题出在影子血管系统已经提供了足够能量，所以开关无所谓。

---

## 3. 当前代码状态

> [!CAUTION]
> 当前代码中 DA 功能处于**不正确**状态：
> - 差分对（exc + inh bundle）导致 DA 永远为 0
> - 需要恢复或重新设计才能让 DA 正常工作

**保留的正确部分**：
- DA neuron 池（3 个真实 Neuron）✓
- Xin relay neuron ✓  
- 延迟初始化机制 ✓
- get_all_neurons/bundles 注册 ✓
- Noether 集成 ✓

**需要修复的部分**：
- shadow→DA 的信号源和差分机制
- 影子 col 的无限增长问题

---

## 4. 三个候选设计方向

### 方向 A：修复影子层自身的增长问题

在源头解决。影子 col 激活值应当有界。

**做法**：
- 增强影子 col 的 VR（`vr_base_rate` 从 0.01 → 0.5）
- 或降低 shadow bundle 的 `synapse_gain`（10.0 → 2.0）
- 影子 col 激活值被限制在 0~1.0 范围

**效果**：shadow→DA 的单条兴奋性通路就够用了，不需要差分对。DA neuron 的 VR 提供慢适应，自然产生新奇检测。

**风险**：这是"调参数"的思路。影子层增长可能有其存在意义（累积信息）。

### 方向 B：差分对 + 结构性不对称

保持双通路，但让两条通路在结构上不同（不只是 lr 不同）。

**做法**：
- 兴奋性通路：shadow col → DA（直接）
- 抑制性通路：shadow **motor** → DA（间接，更慢）
- 两组不同的源 neuron → 自然产生权重分化

**原理**：shadow col 反映"感知状态"，shadow motor 反映"运动响应"。当感知变了但运动还没适应 → exc > inh → DA 升高。适应完成后 → exc ≈ inh → DA 回落。

**风险**：假设 shadow motor 能反映"期望"，需要验证。

### 方向 C：影子层 Xin 作为 DA 信号源

回到最初的思路，但通过结构化通路。

**做法**：
- 创建"影子 Xin 中继 neuron"（每个轴一个）
- 其输入 = 对应 shadow bundle 的 |Xin tension|
- 这些中继 neuron → DA（通过 SynapticBundle）

**原理**：影子 Xin = 影子层内的预测误差。Xin 高 = 影子模型惊讶 = 新奇。Xin 低 = 预测准确 = 熟悉。

**优势**：
- Xin 天然是差分信号（predicted - actual），不需要人工构造差分对
- Xin 收敛到 0 → DA 回落到 baseline（自归一化）
- 中继 neuron + bundle = 结构化通路

**风险**：影子 Xin 可能也有单调增长问题（需要验证）。

---

## 5. 深层问题：影子层为何无限增长？

这不仅影响 DA。影子 col 激活值 = 7.0 意味着影子层的"内部模型"是发散的。

```
影子层输入 = 主层 Xin × XIN_GAIN(3.0)
主层 Xin = Σ|predicted - actual| 
           → 随着 sprout 增多，Xin 来源变多
           → 总 Xin 单调增长
           → 影子层输入单调增长
           → 影子 col 单调增长
```

这暴露了一个更深的问题：**主层 Xin 的总量没有守恒上界**。每个新 sprout 贡献自己的 Xin，总 Xin 随 bundle 数量线性增长。Noether probe 检查的 `xin_bound = max(1000, len(bundles) × 50)` 是一个随 bundle 数量膨胀的软上界，不是真正的守恒。

> [!IMPORTANT]
> 影子 col 无限增长的根因可能不在影子层，而在**主层 Xin 的总量**没有被正确归一化。
> 这是一个架构级问题，影响范围超出 DA 回路。

---

## 6. 建议的明天优先级

1. **决定方向 A/B/C**（或提出方向 D）
2. **是否需要先修复影子 col 增长问题**（这是 DA 问题的前置依赖）
3. **影子层 construction_power** 是否恢复为 True（当前为 False，但实验证明无影响）

---

## 附录：代码变更清单

| 文件 | 行号 | 变更 | 状态 |
|------|------|------|------|
| variant_adapter.py | L25 | 新增 Neuron 导入 | ✅ 保留 |
| variant_adapter.py | L345-390 | DA neuron 池 + xin relay | ✅ 保留 |
| variant_adapter.py | L627-695 | 结构化 DA 信号流 | ✅ 保留 |
| variant_adapter.py | L1098-1180 | _init_da_circuit（含差分对）| ⚠️ 需修复 |
| variant_adapter.py | L1182-1200 | get_all 覆盖 | ✅ 保留 |
| shadow_sandbox.py | L149 | construction_power=False | ⚠️ 待决定 |
