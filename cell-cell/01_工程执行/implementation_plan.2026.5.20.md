# MetaNeuron 半导体元件化

## 目标

用 4 种半导体元件的物理模型**统一替换** MetaNeuron 中 12+ 个 DEGRADED proxy，使每个机制都有真实物理依据而非特设简化。

## 映射表

| 生物 proxy (DEGRADED) | → 半导体元件 | 物理方程 |
|----------------------|-------------|---------|
| 膜电位积累 | **Capacitor** | Q = CV, dV/dt = I/C |
| 离子通道门控 (L232) | **MOSFET** | I = gm(Vgs - Vth) |
| ATP/ADP 循环 (L128) | **PowerRail** | V_actual = Vdd - I×R_i |
| 突触权重 | **Memristor** | R = R_min + ΔR(1-w) |
| 泄漏电流 | **R_leak** | I_leak = V/R |
| 阈值适应 (L263) | **MOSFET Vth 漂移** | NBTI/PBTI |
| 囊泡动力学 (L276) | **Memristor 恢复** | w 漂移时间常数 |
| ATP 合成 (L242) | **PowerRail Vdd** | = 基质 node_energy |
| 钙积分器 (L111) | **RC 时间常数** | τ = R×C |
| 基因表达 (L287) | **Vth 慢漂移** | 长 τ_adapt |
| 代谢恢复 (L245) | **PowerRail 充电** | 基质 inject |
| 热输出 (L131) | **I²R 功耗** | P = I²×R |

## 等效电路

```
                Vdd (from SubstrateNetwork)
                 │
                 R_supply (PowerRail 内阻)
                 │
        ┌────────┤ V_internal
        │        │
 in ──[M]──┬──[C]──┤
 (忆阻器)  │       │
          [R_leak] GND
           │
          GND

 V_C > Vth → [MOSFET] → output pulse
 output → discharge C → refractory
```

## Proposed Changes

---

### 半导体元件库

#### [NEW] `engines/semiconductor.py`

4 个 dataclass: `Capacitor`, `MOSFET`, `Memristor`, `PowerRail`
- 从 scratch 测试中提取（已验证 4/4 通过）
- 纯物理模型，无生物学 proxy 注释

---

### MetaNeuron 重构

#### [MODIFY] `engines/hebbian_circuit.py` — MetaNeuron 类

**新增字段:**
```python
_membrane: Capacitor       # 替代 activation + 手工 decay
_gate: MOSFET              # 替代 threshold + 阈值判断 if/else
_power: PowerRail          # 替代 energy + 手工 recovery
```

**修改 `activate()`:**
```python
def activate(self, input_signal):
    # 旧: if abs(effective) < threshold → leak * 0.1
    # 新: current = input / memristor_R → membrane.inject(current * Vdd_ratio)
    #     output = gate.conduct(membrane.voltage)
    current = input_signal / max(self.inertia, 0.5)
    v_avail = self._power.draw(abs(current))
    self._membrane.inject(current * (v_avail / max(self._power.vdd, 0.01)))
    self.activation = self._membrane.voltage
```

**修改 `decay()`:**
```python
def decay(self):
    # 旧: activation += rate * (resting - activation), 6 个独立 proxy
    # 新: membrane.leak(R_leak) + gate Vth adapt + power reset
    self._membrane.leak(self.r_leak)
    self.activation = self._membrane.voltage
    # Vth adaptation (replaces calcium + threshold dual proxy)
    ...
```

**删除的 DEGRADED proxy:**
- `_activation_ema` (L101) → Capacitor 天然积分
- `_metabolic_recovery_rate` (L132) → PowerRail.vdd 从基质拉取
- threshold 手工适应 (L263-270) → MOSFET Vth 漂移
- calcium 手工积分 (L201-202) → RC 时间常数
- `heat_output` 手工计算 (L205-206) → I²R 自动产生

> [!IMPORTANT]
> MetaNeuron 的字段保持向后兼容：`activation`, `threshold`, `energy` 作为 property 从元件状态计算。

---

### transport() 延迟传播

#### [MODIFY] `engines/hebbian_circuit.py` — `transport()` 方法

```python
# 旧: tgt_acts = bundle.propagate(src_acts) → 即时
# 新: bundle.inject_pulse(propagated, tick) → 延迟
#     delivered = bundle.deliver_pulses(tick) → 到达时投递
```

> [!CAUTION]
> 这是行为变更：所有信号将有 ≥1 tick 延迟。需要验证下游不依赖即时传播。

---

### PowerRail ↔ SubstrateNetwork 连接

#### [MODIFY] `engines/hebbian_circuit.py` — `_metabolic_step()` 

```python
# 每 tick: 从基质节点读取能量 → 设置每个神经元的 PowerRail.vdd
for neuron_id, sub_node in substrate._neuron_binding.items():
    neuron._power.vdd = substrate.node_energy[sub_node]
```

## Open Questions

> [!IMPORTANT]
> **向后兼容**: 现有 runner 直接读取 `neuron.activation`, `neuron.energy`, `neuron.threshold`。
> 方案 A: 保留为 property（推荐）
> 方案 B: 全面重构 runner
> 建议选 A — 最小化变更范围。

> [!WARNING]
> **Memristor 放在哪一层?**
> 选项 1: 放在 MetaSynapticBundle 中（每个 Bundle 内每对 src-tgt 一个 Memristor）
> 选项 2: 放在 MetaNeuron 中（每个输入突触一个 Memristor）
> 建议选 1 — Bundle 本身就是超边，Memristor 放在超边上最自然。

## Verification Plan

### Automated Tests
1. 运行现有 regression_test.py — 验证向后兼容
2. 运行 semiconductor_test.py — 验证元件物理
3. 新增: transport 延迟测试 — 验证信号不再即时

### Manual Verification
- 运行 `run_v40_integrated.py` 全流程 — 确认 pipeline 不崩溃
