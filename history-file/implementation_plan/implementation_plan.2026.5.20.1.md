# 半导体物理层重建计划 v2

## 背景

上一 session 的所有修改（semiconductor.py、MetaNeuron 半导体化、INFO_EQUIV 标签、Landauer bridge、hunger/CPG 修复）因文件回退而**全部丢失**。

本计划基于完整的 session 记录和 pyc 反编译结果进行**精简重建**，同时修复上次发现的 4 个 bug。

## 上次 Session 中发现的 Bug（本次必修）

> [!CAUTION]
> 这些 bug 在上次 session 中被逐一定位但未完全解决就丢失了。

| # | Bug | 根因 | 修复 |
|---|-----|------|------|
| 1 | CPG activation = 0 | `_cpg_step` 设 `activation`，但 `decay()` 用 `_membrane.leak()` → `activation = _membrane.voltage` 覆盖 | CPG tonic drive 必须注入 **membrane charge**，不是直接设 activation |
| 2 | hunger ceiling 被 floor 挡死 | `floor = target_rate×0.15 = 0.0045 > hunger_ceiling = target_rate×0.5×0.1 = 0.0015` | hunger 生效时 floor 也要降低 |
| 3 | 系统永远 hunger=1.0 | `_energy_capacity` 太小(0.15)，`heat_output` 无界增长 → 一个 tick 耗完 pool | 合理化 capacity 和 consumption 比例 |
| 4 | MOSFET 亚阈值泄漏用线性 | 真实物理是指数型 Boltzmann activation | 使用 `I_off × exp(Vgs / (n × VT))` |

## Proposed Changes

---

### Phase 1: 半导体元件库

#### [NEW] `engines/semiconductor.py`

4 个 dataclass：`Capacitor`, `MOSFET`, `Memristor`, `PowerRail`

- **Capacitor**: `charge`, `capacitance`, `voltage` property, `inject(I,dt)`, `leak(R,dt)`, `discharge_to(V)`
- **MOSFET**: `v_threshold`, `gm`, `conduct(v_gate)` (指数亚阈值 + 线性超阈值), `adapt_threshold()`
- **Memristor**: `w∈[0,1]`, `R_min`, `R_max`, `resistance/conductance` property, `conduct(v)`, `update(STDP)`
- **PowerRail**: `vdd`, `R_internal`, `draw(I)` → `V_actual`, `v_actual` property, `power_dissipated`

> [!IMPORTANT]
> MOSFET.conduct 使用**连续指数→线性过渡**:
> ```
> if Vgs > Vth:   I = gm × (Vgs - Vth)     # superthreshold linear
> else:           I = I_off × exp(Vgs/(n×VT)) # subthreshold exponential
> ```
> 两段在 Vgs = Vth 处连续 (I_off 由 gm×0 = I_off×exp(Vth/(n×VT)) 校准)

---

### Phase 2: MetaNeuron 半导体化

#### [MODIFY] `engines/hebbian_circuit.py` — MetaNeuron

**新增 3 个元件字段**:
```python
_membrane: Capacitor    # 替代 activation 手工衰减
_gate: MOSFET           # 替代 threshold if/else
_power: PowerRail       # 替代 energy 手工 recovery
r_leak: float = 1.0     # RC 泄漏电阻
```

**重写 `activate()`**:
```python
def activate(self, input_signal):
    current = input_signal / max(self.inertia, 0.5)
    v_avail = self._power.draw(abs(current))
    self._membrane.inject(current * (v_avail / max(self._power.vdd, 0.01)))
    vm = self._membrane.voltage
    self.activation = self._gate.conduct(vm)
    self.heat_output = current ** 2 * self._power.r_internal  # I²R
    ...
```

**重写 `decay()`**:
```python
def decay(self):
    self._membrane.leak(self.r_leak)
    self.activation = self._membrane.voltage
    # MOSFET Vth homeostatic adaptation
    error = self.calcium - self.target_rate
    self._gate.v_threshold += self.threshold_adapt_rate * error
    # hunger-aware floor+ceiling
    ceiling = getattr(self, '_hunger_ceiling', 0.5)
    base_floor = max(0.0001, self.target_rate * 0.15)
    floor = min(base_floor, ceiling * 0.8) if ceiling < 0.5 else base_floor
    self._gate.v_threshold = max(floor, min(ceiling, self._gate.v_threshold))
    self.threshold = self._gate.v_threshold
    ...
```

> [!WARNING]
> **Bug fix #1**: `_cpg_step()` 必须通过 `neuron._membrane.charge +=` 注入 tonic drive，不能直接写 `neuron.activation`。否则 `decay()` 会用 `_membrane.voltage` 覆盖。

---

### Phase 3: MetaSynapticBundle Memristor 化

#### [MODIFY] `engines/hebbian_circuit.py` — MetaSynapticBundle

- `weights[i][j]` → `_memristors[i][j].w` (Memristor array)
- `propagate()` 通过 `Memristor.conduct()` 计算输出
- Bundle 的 `cable_length` + `propagation_velocity` → `delay_ticks`
- `inject_pulse()` / `deliver_pulses()` 实现延迟线缆传播

---

### Phase 4: 代谢环流修复

#### [MODIFY] `engines/hebbian_circuit.py` — `_metabolic_step()`

**Bug fix #2 — hunger ceiling 须降低 floor**:
```python
# 在 _metabolic_step 中设每个 neuron 的 _hunger_ceiling
n._hunger_ceiling = n._base_threshold * hunger_factor
```

**Bug fix #3 — 能量预算平衡**:
```python
self._energy_capacity = 10.0  # 从 0.15 提升到 10.0
# consumption 限制: basal_consumption = min(tick_heat * 0.1, pool * 0.1)
```

**Bug fix #1 — CPG tonic drive**:
```python
# 在 _cpg_step 中:
neuron._membrane.charge += 0.1 * neuron._membrane.capacitance  # NOT neuron.activation += 0.1
neuron._membrane.charge *= 0.70  # CPG damping
```

---

### Phase 5: 涌现测试

6 项测试重写，修复上次所有测试中发现的问题:
1. hunger=0 vs hunger=1 的 Vth 对比（用合理 energy_capacity）
2. 权重分化（STDP + delay）
3. Landauer 学习约束
4. 空间功能分化 (Vdd 梯度)
5. 学习稀疏化
6. CPG-代谢耦合（membrane charge 注入 + 合理能量对比）

---

## Verification Plan

### Automated Tests
1. `semiconductor_test.py` — 4 元件物理验证
2. `regression_test.py` — 向后兼容
3. `e2e_semiconductor_test.py` — 端到端
4. `emergence_test.py` — 6 项涌现
5. `entropy_ledger_test.py` — Landauer bound

### Manual Verification
- 确保 `run_v40_integrated.py` 正常运行
