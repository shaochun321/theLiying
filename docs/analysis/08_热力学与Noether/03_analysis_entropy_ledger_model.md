# 外部熵账本 — 理论模型

## 目的

**先建模型、导预测，再去系统里验证。**
不是 "射箭画靶"，而是 "画靶射箭"。

---

## 1. 理论基础

### Jaynes (1957) — 最大熵原理

> 给定约束条件下，信息最少的概率分布就是最大熵分布。

对本系统的意义：权重分布 {w_ij} 在无约束时应趋向均匀分布 (最大熵)。
学习（STDP/Oja）**减少了权重的熵** — 从均匀趋向稀疏的双模态。

**可观测量**：权重分布的 Shannon 熵
```
S_weights(t) = -Σ p(w) log₂ p(w)
```
其中 p(w) 是将 w ∈ [0,1] 分成 K 个 bin 后的归一化直方图。

### Landauer (1961) — 信息擦除下界

> 擦除 1 bit 信息的最小热耗散 = kT ln 2

推广到连续权重更新：每次权重变化 Δw 对应的信息变化为
```
ΔI = Σ_{i,j} |log₂(w_new / w_old)|   (简化: 每个权重的对数变化)
```
更严格地：
```
ΔS_weights = S_weights(t) - S_weights(t+1)    (熵减少量)
```
如果 ΔS_weights > 0（学习减少了不确定性），则必须向环境排出热量：
```
Q_dissipated ≥ kT × ln(2) × ΔS_weights        (Landauer bound)
```

### 连接

```
信息侧:  S_weights(t) → S_weights(t+1),  ΔS = S(t) - S(t+1)
热力学侧: Q_dissipated = Σ_neurons I²R + Σ_bundles transport_cost
约束:     Q_dissipated ≥ kT × ln(2) × max(0, ΔS)
```

---

## 2. 系统中已有的可观测量

| 量 | 计算位置 | 来源 |
|----|---------|------|
| `n.heat_output` | `activate()` L195 | I²R (每 neuron 每 tick) |
| `_total_heat` | `maintain()` L2206 | Σ heat_output (累积) |
| `_temperature` | `maintain()` L2207 | _total_heat / tick (时间平均) |
| `_free_energy` | `_column_forward_step()` L1245 | Σ energy - T × 0.1 |
| `transport_cost` | `propagate()` L461 | Bundle 传输开销 |
| `weights[i][j]` | 学习规则 L593-599, 676-683 | STDP/Oja 更新后的值 |
| `_energy_pool` | `_metabolic_step()` L3054 | 全局能量池 |
| `_energy_consumed` | `_metabolic_step()` L3108 | 每 tick 总消耗 |

### 缺失的量

| 量 | 需要什么 | 目的 |
|----|---------|------|
| **S_weights(t)** | 每 tick 计算权重分布的 Shannon 熵 | Landauer bound 左边 |
| **ΔS_weights** | S(t) - S(t+1) | 信息擦除量 |
| **Q_learning** | 学习步骤中的热耗散（区分于基础代谢） | Landauer bound 右边 |
| **kT** | 系统温度的物理标定 | Landauer bound 中间 |

---

## 3. 可证伪的预测

### 预测 P1: Landauer 下界

> **在每个学习步骤中，热耗散 Q 不小于 kT ln2 × 擦除的信息比特数。**

```
P1: Q_tick ≥ kT × ln(2) × max(0, ΔS_weights)
```

**如何证伪**: 如果存在某个 tick 使得 Q < kT × ln2 × ΔS（信息减少了但热没排够），
则系统违反 Landauer bound — 说明热力学建模有错。

**预期结果**: 应该 **始终满足**，因为 I²R 是物理耗散（始终为正），
而 ΔS 在学习收敛后趋向零。不等式应该有较大裕量 (Q >> kT ln2 ΔS)。

> [!IMPORTANT]
> **kT 的标定问题**: 系统中的 "温度" T 是 `_total_heat / tick`，
> 量纲不明确。k 可以约定为 1（自然单位），
> 但需要确认 T 的量纲与 Q 的量纲兼容。
> 如果不兼容，P1 只能验证 **定性**（Q > 0 当 ΔS > 0），不能验证 **定量**。

### 预测 P2: 学习-耗散相关性

> **信息变化速率越大，热耗散越大。**

```
P2: corr(|dS/dt|, Q) > 0
```

**如何证伪**: 如果 |dS/dt| 和 Q 无相关或负相关，
则热力学-信息耦合不存在。

**预期结果**: 正相关。学习初期（权重剧烈变化）→ 高耗散；
学习后期（权重收敛）→ 低耗散。

### 预测 P3: 信息-自由能等价

> **系统自由能的变化等于可用功减去信息成本。**

```
P3: ΔF = ΔE - TΔS_thermo
    其中 ΔS_thermo 包含权重熵贡献:
    ΔS_thermo ≥ ΔS_weights × ln(2)   (Jaynes-Landauer bridge)
```

**如何证伪**: 如果 ΔF 和 ΔE - T × ΔS_total 之间没有线性关系，
则自由能公式 (L1245) 不是热力学自由能的有效代理。

**预期结果**: 弱线性关系（因为 L1245 的 `0.1` 系数是特设的，不是从信息量导出的）。
如果关系不成立，需要用真实的 S_weights 替换 `0.1` 常数。

---

## 4. 测量协议（在写代码之前确定）

### 需要的探针（不修改系统动力学，只读）

1. **权重熵探针**: 每 N tick 采样所有权重 → 计算 Shannon 熵 S(t)
   - bin 数: K = 50 (覆盖 [0,1])
   - 采样频率: 每 10 tick（避免噪声）
   
2. **学习热探针**: 在 STDP/Oja 更新前后分别记录权重 → 计算 ΔS
   - 同时记录该 tick 的 Q = Σ heat_output
   
3. **自由能探针**: 记录 F, E, T, S_weights 的时间序列
   - 检验 ΔF ≈ ΔE - T × ΔS

### 分析方法

- **P1**: 散点图 Q vs ΔS, 画 kT ln2 × ΔS 参考线，检查所有点在线上方
- **P2**: Pearson/Spearman 相关系数 + p-value
- **P3**: 线性回归 ΔF ~ ΔE - T × ΔS, 检查 R²

---

## 5. 可能的结果场景

| 场景 | P1 | P2 | P3 | 含义 |
|------|----|----|-----|------|
| **A: 全通** | ✅ | ✅ | ✅ | Jaynes-Landauer bridge 成立；系统是热力学一致的信息处理器 |
| **B: P1 ✅ P2 ✅ P3 ❌** | ✅ | ✅ | ❌ | Landauer 成立但 L1245 的自由能公式不对；需要修正 `0.1` → S_weights |
| **C: P1 ✅ P2 ❌** | ✅ | ❌ | — | Landauer 成立但信息-耗散无因果关系；耗散来自基础代谢而非学习 |
| **D: P1 ❌** | ❌ | — | — | 系统违反 Landauer bound；热力学建模有根本错误 |

> [!WARNING]
> **场景 B 是最可能的**。因为 `_free_energy = Σ energy - T × 0.1` 中的 `0.1` 
> 是人为常数，不是从权重熵导出的。这正是"射箭画靶"的一个实例——
> 如果 P3 失败，说明这个 `0.1` 需要被真实的 S_weights 替换。

---

## 6. 决策点

> [!IMPORTANT]
> **请确认**:
> 1. 三个预测 P1/P2/P3 是否覆盖了你想验证的核心构想？
> 2. 如果 P3 失败（自由能公式需要修正），你是否接受修改 L1245？
> 3. kT 标定：接受 k=1 自然单位，还是需要显式的 Boltzmann 常数映射？
