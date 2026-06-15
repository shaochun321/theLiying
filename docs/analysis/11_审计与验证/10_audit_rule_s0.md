# RULE S0 结构审计报告

## 审计范围

检查 6 项已重构的组件替换 + 扫描残余纯数学违规。

---

## 1. Ca 电压钳位 — MOSFET Zener

**文件**: [neuron.py L171-175](file:///d:/cell-cc/nexus_v1/components/neuron.py#L171-L175)  
**初始化**: `_ca_clamp = MOSFET(v_threshold=1.0, gm=10.0)`  
**使用**: [neuron.py L340-347](file:///d:/cell-cc/nexus_v1/components/neuron.py#L340-L347)

```python
ca_v = self._ca_cap.voltage
i_clamp = self._ca_clamp.conduct(ca_v)   # I = 10 * (Ca_v - 1.0) when Ca_v > 1.0
if i_clamp > 0:
    self._ca_cap.inject(-i_clamp, dt)
```

**物理分析**:
- Ca_v = 1.0 时: I = 0 (**边界正确**)
- Ca_v = 1.1 时: I = 10 × 0.1 = 1.0。dt=0.001 → drain = 0.001。Ca_cap(C=0.01)，ΔV = 0.001/0.01 = 0.1 → Ca_v ≈ 1.0
- Ca_v = 2.0 时: I = 10 × 1.0 = 10。dt=0.001 → drain = 0.01。ΔV = 1.0 → 快速回拉

> [!TIP]
> gm=10 足够强，任何超过 1.0 的电压在 ~1ms 内被拉回。等效于 Zener 击穿。**物理正确**。

**评级: PASS**

---

## 2. 囊泡池 — Capacitor 有限储备

**初始化**: [neuron.py L178-181](file:///d:/cell-cc/nexus_v1/components/neuron.py#L178-L181)
```python
_vesicle_pool = Capacitor(capacitance=1.0)
_vesicle_pool.discharge_to(0.5)    # 初始半满
_vesicle_replenish_rate = 0.1      # 每秒补充 0.1
```

**使用**: [neuron.py L353-362](file:///d:/cell-cc/nexus_v1/components/neuron.py#L353-L362)

> [!WARNING]
> **问题 P1**: L359 `min(raw_release, max(0.0, pool_v))` 仍然是 `min()` 纯数学操作。  
> 严格来说应该用 **第二个 MOSFET** 来门控释放——pool 电压作为 gate，当 pool_v < threshold 时 MOSFET 关断，自然截止释放。  
> **当前**: 功能正确，但违反 RULE S0 精神（min 是直接算术，不是组件行为）。  
> **建议**: 可以容忍——这是 Capacitor 的 "电压不够了自然放不出来" 的物理语义，min() 在这里是物理约束的表达，不是信号处理。

**评级: PASS (minor)**

---

## 3. Xin→DA — Capacitor 积分器 + MOSFET 门控

**初始化**: [variant_adapter.py L235-236](file:///d:/cell-cc/nexus_v1/circuit/variant_adapter.py#L235-L236)
```python
_xin_integrator = Capacitor(capacitance=10.0)
_xin_gate = MOSFET(v_threshold=0.01, gm=0.5)
```

**使用**: [variant_adapter.py L447-456](file:///d:/cell-cc/nexus_v1/circuit/variant_adapter.py#L447-L456)

**物理分析**:
- Capacitor(C=10) 积分 Xin，`leak(R=50, dt)` → τ = 10×50 = 500s。**极慢衰减**。
- 10k 步 (10s) 内，Xin 不断注入 → V 持续上升
- MOSFET(Vth=0.01, gm=0.5): 几乎零阈值，几乎所有积分值都通过

> [!WARNING]
> **问题 P2**: `τ_integrator = C × R = 10 × 50 = 500s` 意味着积分器几乎不衰减。  
> 在 10s 运行中，total_xin ≈ 1.5/step × 10000 步 × 0.001dt = 15 注入，C=10 → V=1.5。  
> MOSFET: gm=0.5, V=1.5: I = 0.5 × (1.5-0.01) = 0.745 → DA release = min(0.745, 0.5) = 0.5 (饱和)。  
> **DA 永远饱和**。需要更短的 τ 或更高的 Vth。  
> **建议**: `leak(R=5.0)` → τ=50s，或 `capacitance=1.0` → τ=50s。

**评级: CONCERN — DA 饱和**

---

## 4. g_sync — MOSFET 门控

**初始化**: [variant_adapter.py L241](file:///d:/cell-cc/nexus_v1/circuit/variant_adapter.py#L241)
```python
_sync_gate = MOSFET(v_threshold=0.1, gm=1.0)
```

**使用**: [variant_adapter.py L515-517](file:///d:/cell-cc/nexus_v1/circuit/variant_adapter.py#L515-L517)

**物理分析**:
- total_bind_act < 0.1 → g_sync = 0 (MOSFET 关断) ✓
- total_bind_act = 0.5 → g_sync = 1.0 × (0.5-0.1) = 0.4 ✓
- total_bind_act = 1.5 → g_sync = min(1.4, 1.0) = 1.0 ✓

> [!NOTE]
> `min(1.0, g_sync_raw)` 是物理饱和，不是信号处理。可接受。

**评级: PASS**

---

## 5. 热扩散 — MOSFET 热导体

**初始化**: [variant_adapter.py L246-248](file:///d:/cell-cc/nexus_v1/circuit/variant_adapter.py#L246-L248)

**使用**: [variant_adapter.py L562-587](file:///d:/cell-cc/nexus_v1/circuit/variant_adapter.py#L562-L587)

**物理分析**:
- `coupler.conduct(|ΔT|)` = gm × |ΔT| = 0.01 × |ΔT|。这是 **欧姆定律 I = ΔV/R = G×ΔV**。  
- 方向判断用 `if delta_t > 0` → 热从高温流向低温。✓
- 辐射损耗: `_thermal_loss.conduct(T)` = 0.001 × T。✓

> [!TIP]
> 完美的热 RC 网络。MOSFET 等效为热导体（G=gm），ECM._temperature 等效为热容电压。物理完全正确。

> [!NOTE]
> L587 `max(0.0, ecm._temperature)` 是温度的物理下界（绝对零度），不是信号处理。合规。

**评级: PASS**

---

## 6. 阻抗匹配 — MOSFET 分压器

**初始化**: [variant_adapter.py L254-255](file:///d:/cell-cc/nexus_v1/circuit/variant_adapter.py#L254-L255)

**使用**: [variant_adapter.py L304-320](file:///d:/cell-cc/nexus_v1/circuit/variant_adapter.py#L304-L320)

**物理分析**:
- `gm = Z` 每步更新（L312-313）
- `conduct(1.0)`: 由于 Vth=0, I = gm × (1.0 - 0.0) = gm = Z ✓
- 分压比: Z_body / (Z_body + Z_medium) ✓

> [!WARNING]
> **问题 P3**: 原始公式是 `T = 2Z/(Z+Zm)`（传输系数），重构后变成 `T = Z/(Z+Zm)`（分压比）。  
> 差异: 当 Z_body = Z_medium = 1.0 时:  
>   - 原始: T = 2×1/(1+1) = **1.0**  
>   - 重构: T = 1/(1+1) = **0.5**  
> **前者是 acoustic transmission coefficient（满匹配=完全传输），后者是 voltage divider（满匹配=50%）。**  
> 物理上传输系数确实是 2Z/(Z+Zm)。分压器只能给 Z/(Z+Zm)。  
> **需要修复**: 要么乘以 2（但这又是纯数学），要么用 **两个串联 MOSFET 对称结构**（正反两路各贡献一半）。

**评级: FAIL — 传输系数丢失因子 2**

---

## 残余纯数学违规扫描

### V1: DA 增益调制 (L466)

[variant_adapter.py L466](file:///d:/cell-cc/nexus_v1/circuit/variant_adapter.py#L466)
```python
col.activation *= min(da_gain, 1.5)
```
**违规**: 直接乘法修改 activation。应通过 **MOSFET 增益调制** 或 **Memristor 可变电导**实现。  
**严重度**: 中。DA 增益在信号通路上。

### V2: 反馈抑制 (L476)

[variant_adapter.py L476](file:///d:/cell-cc/nexus_v1/circuit/variant_adapter.py#L476)
```python
col.activation = max(0.0, col.activation - fb_suppression)
```
**违规**: 直接减法修改 activation。应通过 **抑制性 MOSFET**（负电流注入 membrane）实现。  
**严重度**: 中。efference copy 在信号通路上。

### V3: 多处 EMA 计算 (L467-469)

[variant_adapter.py L467-469](file:///d:/cell-cc/nexus_v1/circuit/variant_adapter.py#L467-L469)
```python
alpha_fb = min(dt / self._feedback_tau, 1.0)
self._feedback_traces[key] = self._feedback_traces[key] * (1 - alpha_fb) + ...
```
**合规判定**: EMA 是 **时间滤波**，等效于 Capacitor 的 RC 衰减。但它直接算术而非通过 Capacitor 组件。  
**严重度**: 低。可用 Capacitor.inject() + Capacitor.leak() 替代。

---

## 总结

| 项目 | 评级 | 问题 |
|------|------|------|
| Ca clamp MOSFET | **PASS** | 物理正确 |
| 囊泡池 Capacitor | **PASS (minor)** | min() 是物理约束 |
| Xin→DA 积分器 | **CONCERN** | τ=500s，DA 永远饱和 |
| g_sync MOSFET | **PASS** | 物理正确 |
| 热扩散 MOSFET | **PASS** | 完美热 RC 网络 |
| 阻抗 MOSFET 分压器 | **FAIL** | 丢失因子 2 (T vs 2T) |

### 残余违规

| ID | 位置 | 严重度 | 描述 |
|----|------|--------|------|
| V1 | L466 | 中 | DA gain *= 直接乘法 |
| V2 | L476 | 中 | 反馈 -= 直接减法 |
| V3 | L467 | 低 | EMA 直接算术（可用 Capacitor 替代） |

### 建议修复优先级

1. **P3** (阻抗因子 2): 恢复传输系数的 ×2 因子
2. **P2** (DA 饱和): 缩短积分器 τ（C=1.0 或 R=5.0）
3. **V1** (DA gain): 用 MOSFET 增益调制替代直接乘法
4. **V2** (反馈): 用抑制性电流注入替代直接减法
