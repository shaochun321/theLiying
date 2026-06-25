# 阶段 0 + 2a 实施完成

## 新增文件

### [rlis_observer.py](file:///D:/cell-cc/Morphosphere_v37_0_native_runtime_prototype_flat_complete/morphosphere_v2pp/engines/rlis_observer.py)

**RLIS 外部观测器** — 读取 HebbianCircuit 状态，不修改任何内容。

| 类 | 功能 |
|---|---|
| `TickSnapshot` | 每 tick 的电路状态冻结副本 (深拷贝) |
| `RhoMeasure` | ρ 7 分量归一化测度: p_core, p_band, r_core, r_band, masking, xin, unresolved |
| `XinFlow` | Xin 守恒记录: 来源 / 吸收 / 果实消耗 / 守恒误差 |
| `CircuitObserver` | 主类: observe() → compute_rho() → track_xin_conservation() |

---

### [vestibular_store.py](file:///D:/cell-cc/Morphosphere_v37_0_native_runtime_prototype_flat_complete/morphosphere_v2pp/engines/vestibular_store.py)

**前庭存储** — 固化的环流模式作为系统坐标系。

| 类 | 功能 |
|---|---|
| `CirculationBaseline` | 固化时的基线: 神经元 active_state + global_threshold + phase_order |
| `SolidifiedPattern` | 一个固化的运动状态参考 (含 4-score 健康模型) |
| `PatternDistance` | XOR 比对结果: distance, xor_count, phase_alignment |
| `VestibularStore` | 主类: store_pattern() → compare_snapshot() → get_nearest_pattern() |

---

## 关键设计决策

### 1. XOR 比对使用全局中位数阈值

```
阈值 = 所有参与神经元均值激活的中位数
高于阈值 → active
低于阈值 → inactive
XOR: 基线 active ≠ 当前 active → mismatch
```

### 2. ρ 的分配逻辑

```
total_budget = circulation_measure + xin_total + baseline(0.01)
p_core = P 路径精确匹配的 cycle flow / budget
r_core = R 路径精确匹配的 cycle flow / budget
p_band = 与 P 共享 bundle 的 cycle flow / budget
masking = 同时与 P 和 R 共享的 cycle flow / budget
xin = xin_total / budget
unresolved = 1 - (上述之和)
```

### 3. 与已有 vestibular_system.py 的关系

```
VestibularSystem (已有) = 物理层 6 轴 IMU (传感器硬件)
VestibularStore  (新建) = 信息层模式存储 (固化的坐标系)
两者独立, 不互相依赖
```

---

## 测试结果

```
Test 1: ρ normalization      → TOTAL=1.000000  ✅
Test 2: Xin conservation     → error=0.000000  ✅
Test 3: ρ empty circuit      → unresolved=1.0  ✅
Test 4: VestibularStore      → health=0.791    ✅
Test 5: XOR same pattern     → distance=0.000  ✅
Test 6: XOR diff patterns    → A=0.0, B=1.0   ✅
Test 7: Ledger accumulation  → 5 entries       ✅
Test 8: Serialization        → OK              ✅
```
