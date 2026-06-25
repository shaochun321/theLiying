# 动力学因果链路追踪 — 从元结构出发

> 追踪规则：每个字段必须有 **写入点 → 读取点 → 下游效应** 的完整链条。
> 链条断裂 = 动力学不完整。

## MetaNeuron 字段链路

### ✅ 完整链路

```mermaid
graph LR
    subgraph "activation 链"
        A1["activate(): input_signal/inertia - threshold"] -->|写入| ACT[activation]
        ACT -->|读取| D1["decay(): → resting_potential"]
        ACT -->|读取| CA["calcium += (|act| - ca) / tau"]
        ACT -->|读取| POT["potential += |act| × 0.01"]
        ACT -->|读取| EMA["_activation_ema += 0.001 × ..."]
        ACT -->|读取| INE["inertia: deviation < 0.01 → +0.001"]
        ACT -->|读取| LAT["maintain(): Column suppression field"]
        ACT -->|读取| STDP["stdp_update(): ltp/ltd 计算"]
        ACT -->|读取| EN["energy -= |act| × 0.01"]
    end
```

| 写入点 | 读取点 | 下游效应 | 状态 |
|--------|--------|---------|:----:|
| `activate()` L173-178 | `decay()` L203 | → resting_potential 目标 | ✅ |
| | `activate()` L184 | → calcium 积分 | ✅ |
| | `decay()` L204 | → potential 积累 | ✅ |
| | `decay()` L216 | → _activation_ema 更新 | ✅ |
| | `decay()` L237 | → inertia 稳定/波动 | ✅ |
| | `maintain()` L943 | → Column suppression force | ✅ |
| | `stdp_update()` L349 | → LTP/LTD 计算 | ✅ |
| | `activate()` L187-189 | → energy 消耗, heat_output | ✅ |

---

```mermaid
graph LR
    subgraph "calcium 链"
        ACT2["|activation|"] -->|积分| CA2[calcium]
        CA2 -->|读取| TH["threshold += adapt_rate × (ca - target)"]
        CA2 -->|读取| PRP["prp_emission: ca > prp_threshold → emit"]
        CA2 -->|读取| SUP["lateral suppression: field_strength = ca/target"]
        CA2 -->|读取| REC["energy recovery ∝ calcium"]
        CA2 -->|读取| PRT["prp_threshold += 0.01 × (ca×1.5 - thr)"]
    end
```

| 写入点 | 读取点 | 下游效应 | 状态 |
|--------|--------|---------|:----:|
| `activate()` L184 | `decay()` L248-252 | → threshold 适应 | ✅ |
| | `maintain()` L948-953 | → PRP emission 门控 | ✅ |
| | `maintain()` L934 | → suppression field_strength | ✅ |
| | `decay()` L227 | → energy recovery rate | ✅ |
| | `decay()` L269 | → prp_threshold 适应 | ✅ |

---

```mermaid
graph LR
    subgraph "energy 链"
        REC3["decay(): recovery ∝ calcium"] -->|增| EN3[energy]
        ACT3["activate(): |act| × 0.01"] -->|减| EN3
        TC3["transport(): transport_cost"] -->|减| EN3
        EN3 -->|读取| ALV["is_alive(): energy > 0"]
    end
```

| 写入点 | 读取点 | 下游效应 | 状态 |
|--------|--------|---------|:----:|
| `decay()` L227-228 | `is_alive()` L319 | 死亡判定 | ✅ |
| `activate()` L189 | | | ✅ |
| `transport()` L696-699 / L724-727 | | | ✅ |

---

```mermaid
graph LR
    subgraph "inertia 链"
        MAT["try_mature(): column → 2.0"] -->|设| INE4[inertia]
        STAB["decay(): stable → +0.001"] -->|增| INE4
        VOL["decay(): volatile → -0.001"] -->|减| INE4
        INE4 -->|读取| ACT4["activate(): effective = input / inertia"]
        INE4 -->|读取| STDP4["stdp_update(): delta /= inertia"]
        INE4 -->|读取| TC4["propagate(): cost /= inertia"]
    end
```

---

```mermaid
graph LR
    subgraph "stdp_ltp_boost 链"
        MAT5["try_mature(): column → 2.0"] -->|设| BOOST[stdp_ltp_boost]
        DEC5["decay(): recovery → base"] -->|恢复| BOOST
        STDP5["stdp_update(): depletion"] -->|消耗| BOOST
        BOOST -->|读取| LTP5["stdp_update(): ltp × boost"]
    end
```

---

```mermaid
graph LR
    subgraph "prp_emission 链"
        CA6["calcium > prp_threshold"] -->|增| PRP6[prp_emission]
        DEC6["maintain(): × 0.95"] -->|减| PRP6
        PRP6 -->|读取| CAP6["maintain(): PRP Capture → fruit trace +"]
    end
```

---

```mermaid
graph LR
    subgraph "resting_potential 链"
        EMA7["_activation_ema"] -->|驱动| REST7[resting_potential]
        REST7 -->|读取| DEC7["decay(): act → resting_potential"]
        REST7 -->|读取| INE7["decay(): deviation = |act - rest|"]
    end
```

---

### MetaSynapticBundle 字段链路

```mermaid
graph LR
    subgraph "xin_dormant_fruit 链"
        XIN8["xin_tension > 0.5"] -->|创建| FRUIT8[dormant_fruit]
        TRACE8["trace_strength × effective_decay"] -->|衰减| FRUIT8
        PRP8["PRP Capture"] -->|延长| FRUIT8
        XIN9["xin_tension magnitude"] -->|第三因子| FRUIT8
        FRUIT8 -->|读取| ACT8["try_activate_fruit(): effective_tension"]
    end
```

---

## 断裂链路修复状态

### 1. ~~`heat_output`~~ — ✅ **已修复 v40.7d**

```
写入: activate() L188: self.heat_output = cost
读取: maintain() L1075: tick_neuron_heat += n.heat_output
下游: _total_heat → _temperature → lateral_inhibition strength
```

链路: `activate() → heat_output → maintain() → _total_heat → _temperature → _apply_lateral_inhibition()`

### 2. ~~`activation_count`~~ — ✅ **已修复 v40.7d**

```
写入: activate() L180: self.activation_count += 1
读取: try_mature() L290: if self.activation_count < 20: return
下游: 门控 spine→column 和 column→area 的成熟
```

链路: `activate() → activation_count++ → try_mature() gate → maturation → 所有 Column 特权`

### 3. ~~`plasticity`~~ — ✅ **已修复 v40.7d**

```
定义: L142-144: {"spine": 0.18, "column": 0.01, "area": 0.001}
读取: stdp_update() L414: avg_post_plasticity = sum(pn.plasticity...) / 0.18
下游: A_plus *= plasticity, A_minus *= plasticity
```

链路: `maturation → plasticity → stdp_update() → ÇW 缩放 → Column 学习更慢`

### 4. `proxy_for` / `is_proxy_host` — 🟡 **PLACEHOLDER**

明确标记为架构预留位，无动力学耦合。待实现代理委托机制时连接。

### 5. `degraded_features` — 🟢 **ANNOTATION_ONLY**

明确标记为结构性元数据，不参与计算。这是可接受的。
