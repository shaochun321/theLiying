# Phase 4: AGC 自动增益控制 — 实施计划

## 背景

Phase 3 联合验证 (EXP-020) 确认学习机制完整 (4/5 PASS)，但 C4 (方向偏置 Δx>0) 因能量耗竭失败。AGC 解决的核心问题：**行为-能量耦合** — 当能量低/DA低时，自动提升行为增益以打破静止死锁。

## 核心公式

```
S_energy = max(0, 0.5 - fill_fraction)          # 能量匮乏信号
S_da     = max(0, 0.2 - DA_concentration)         # DA匮乏信号
S_drive  = 1.0 × S_energy + 0.5 × S_da            # 复合驱动

G_agc(t+dt) = G_agc(t) × (1 - dt/τ_agc) + S_drive × (dt/τ_agc)    # RC漏积分
G_clamped   = min(G_agc, 4.0)                      # 安全钳位
g_eff       = g_base × (1.0 + G_clamped)           # 最大5倍增益
```

τ_agc = 40000 步 (30k-50k 范围中值)。

## 时间尺度分离

| 机制 | τ | 作用 |
|------|---|------|
| Phase 2 能量冻结 | 瞬时 | 突触 dw 门控 |
| Phase 3 适格迹 | ~300步 | LTP 标记 |
| **Phase 4 AGC** | **~40k步** | **行为增益缩放** |

无相位干涉。

---

## Proposed Changes

### Component: AGC Controller

#### [NEW] [agc.py](file:///D:/cell-cc/nexus_v1/components/agc.py)

新建 `AutomaticGainControl` 类。使用 `Capacitor` 实现 RC 漏积分器 + MOSFET 钳位。

```python
class AutomaticGainControl:
    """Phase 4: 行为增益自动调节。
    
    物理原语: Capacitor(RC漏积分) + MOSFET(钳位) + 乘法器(增益缩放)
    
    S_drive → [Capacitor: τ=40k] → G_agc → [MOSFET clamp: max=4.0] → G_clamped
    g_eff = g_base × (1.0 + G_clamped)
    """
    def __init__(self, tau=40000, alpha=1.0, beta=0.5, g_max=4.0): ...
    def step(self, fill_fraction, da_concentration, dt=1.0) -> float: ...
    @property
    def gain(self) -> float: ...        # 1.0 + G_clamped
    @property
    def g_raw(self) -> float: ...       # 未钳位 G_agc
    @property
    def g_clamped(self) -> float: ...   # 钳位后
    @property
    def s_drive(self) -> float: ...     # 当前驱动信号
    def summary(self) -> dict: ...
```

内部使用 `Capacitor` (漏积分器) 和 `MOSFET` (钳位)，满足 RULE S0。

---

### Component: Variant Adapter Integration

#### [MODIFY] [variant_adapter.py](file:///D:/cell-cc/nexus_v1/circuit/variant_adapter.py)

**4 处修改：**

1. **`__init__` (~L308 附近)**: 实例化 `self.agc = AutomaticGainControl()`

2. **`step()` (~L807 后, fill_fraction 已计算处)**: 调用 `self.agc.step(fill, da_conc, dt)`，记录 `ms.agc_gain`

3. **Hunger reflex 注入 (~L768)**: 将 `(1 + G_clamped)` 作为新参数 `gain_multiplier` 传入 `process_hunger()`

4. **`_propagate_bundles()` (~L1318)**: Col→Motor 增益缩放加入 AGC：
   ```python
   # 现有 DA gain
   total_gain = da_gain * self.agc.gain  # AGC × DA
   currents = [c * total_gain for c in currents]
   ```

5. **`get_variant_state()` (~L1533)**: 添加 AGC 状态到诊断输出

---

### Component: Spinal Reflex (hunger approach)

#### [MODIFY] [spinal_reflex.py](file:///D:/cell-cc/nexus_v1/components/spinal_reflex.py)

在 `process_hunger()` 签名中添加 `gain_multiplier: float = 1.0`。在最终输出处乘以 `gain_multiplier`：

```python
def process_hunger(self, thermo_activations, fill_fraction,
                   da_concentration=0.5, gain_multiplier=1.0, dt=1.0):
    # ... 现有逻辑不变 ...
    return {
        "move_x": raw_x * gate_factor * gain_multiplier,
        "move_y": raw_y * gate_factor * gain_multiplier,
        "move_z": 0.0,
    }
```

> [!NOTE]
> 痛觉撤退反射 (`process()`) **不**接入 AGC。撤退是 L2 硬接线，不应被代谢状态放大。

---

### Component: MotionState

#### [MODIFY] [motor_decision.py](file:///D:/cell-cc/nexus_v1/circuit/motor_decision.py)

在 `MotionState` 中添加 `agc_gain: float = 1.0` 字段，供外部诊断读取。

---

### Component: Validation Script

#### [NEW] [diag_agc_validation.py](file:///D:/cell-cc/nexus_v1/tests/diag_agc_validation.py)

对比实验：有/无 AGC 的位移对比。

```
实验设计:
  1. Run A (AGC enabled):  VariantCircuit + AGC, 20k steps
  2. Run B (AGC disabled): VariantCircuit + AGC(tau=1e12) [实质禁用], 20k steps
  
验证标准:
  C1: Δx(AGC) > Δx(noAGC)           # AGC 改善行为
  C2: G_agc 随 fill↓ 而上升         # 增益响应正确
  C3: G_clamped ≤ 4.0               # 饱和保护
  C4: G_agc 无明显振荡              # 稳定性
```

---

## Verification Plan

### Automated Tests

```bash
# 回归测试 (12/12 全绿)
python -m nexus_v1.tests.test_regression

# AGC 对比验证
python -m nexus_v1.tests.diag_agc_validation
```

### Manual Verification

- 确认 `G_agc` 在 fill_fraction < 0.5 时开始上升
- 确认 `G_clamped` 从不超过 4.0
- 确认撤退反射不受 AGC 影响

## Open Questions

> [!IMPORTANT]
> **τ_agc 取值**: 方案指定 30k-50k 步。计划使用 40k (中值)。可以吗？

> [!NOTE]
> **Col→Motor AGC 作用方式**: 计划在 `_propagate_bundles()` 中叠加到现有 DA gain 上 (`total_gain = da_gain * agc.gain`)。这意味着 AGC 和 DA 增益是乘法耦合。如果需要加法耦合，请指出。
