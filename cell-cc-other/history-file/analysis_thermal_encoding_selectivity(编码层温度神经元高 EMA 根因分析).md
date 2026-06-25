# 编码层温度神经元高 EMA 根因分析

## 症状

`test_encoding_selectivity` 断言 `enc_quiet < 0.5`（热编码神经元应安静），但实测 `reg_therm_front._activation_ema = 1.135`。

---

## 信号链路追踪

测试只给 `oto_x` 输入，但 `VariantCircuit.step()` 自动执行闭环体感：

```
World.ambient_temp=0.1
      ↓
Body.sample_skin() → SkinPatch Fourier 热传导 → T_skin ≈ 0.1
      ↓
SomatosensoryChain.step(T_skin=0.1)
      ↓
Thermoreceptor(v_th=0.01, R=5.0): V_ss = 0.1×5.0 = 0.5 → act = 1.0×(0.5-0.01) = 0.49
      ↓
Bundle(w=0.3, gain=3.0): I_relay = 0.49×0.3×3.0 ≈ 0.44
      ↓
Relay(R=10.0): V_ss = 0.44×10.0 = 4.4 → act ≈ 4.1  ← 即使只有 ambient！
      ↓
get_mechanical_inputs() → therm_front = relay._activation_ema ≈ 1.03
      ↓
Hebbian extra_axes: I_enc = 1.03 × EXTRA_AXIS_GAIN(0.04) = 0.041
      ↓
Encoding neuron(R=5.0, v_th=0.10, gm=0.5): V_ss=0.205, act=0.053 → EMA ≈ 0.20
```

## 三层根因

### 根因 1：体感 relay 增益过高（核心问题）

| 条件 | relay_front EMA | reg_therm_front EMA |
|------|----------------|---------------------|
| 无热源接触（ambient only） | 1.026 | 0.203 |
| 身体靠近热源（dist=11.7） | 4.779 | 0.584 |
| 身体极近热源 + 有利漂移 | 4.675 | 0.698 |

**ambient_temp=0.1 就能把 relay 推到 activation=4.1**。温度感受器 `v_threshold=0.01` 太低 + relay 增益链太强 → 编码层温度神经元永远无法"安静"。

> [!IMPORTANT]
> 这不是 bug，是物理模型的预期行为：生物体始终处于有温度的环境中，温度感受器应该有基线活动。问题在于 **测试预期与物理模型不匹配**。

### 根因 2：pytest fixture 缺少随机种子

[test_regression.py:L345-359](file:///D:/cell-cc/nexus_v1/tests/test_regression.py#L345-L359): `circuit_10k()` fixture 没有调用 `random.seed(42)`，而 `run_test_suite()` 有。

`HeatSource.__post_init__` 创建随机漂移向量 → 不同运行热源漂移方向不同 → 某些运行中热源漂入身体附近 → relay 暴增。

实测 6 次运行的 `reg_therm_front` EMA：

```
seed=42:   0.203  (PASS < 0.5)
noseed-0:  0.203  (PASS)
noseed-1:  0.584  (FAIL!)
noseed-2:  0.205  (PASS)
noseed-3:  0.000  (PASS)
noseed-4:  0.698  (FAIL!)
```

**约 1/3 的概率失败。**

### 根因 3：测试前提有误

测试假设"不给热输入 → 热编码安静"，但 `VariantCircuit` 的闭环世界 **始终有温度场**：
- 3 个硬编码热源 + ambient=0.1
- `Body.sample_skin()` 每步都感知环境温度
- 体感链每步都将 relay 输出注入编码层

"不给热输入"只是指不在 `mechanical_inputs` dict 中显式提供 `therm_*` 键，但 [variant_adapter.py:L632-635](file:///D:/cell-cc/nexus_v1/circuit/variant_adapter.py#L632-L635) 会自动用体感链输出覆盖它。

---

## 修复选项

### A. 修复测试（最小改动）

1. pytest fixture 添加 `random.seed(42)`
2. 放宽阈值到 `enc_quiet < 1.5`（或比较 `enc_active / enc_quiet > 1.5`）
3. 改用相对选择性比而非绝对阈值

### B. 修复体感增益链（物理层面）

提高温度感受器 `v_threshold` 使 ambient 不触发基线活动：
- `v_threshold: 0.01 → 0.20`：ambient V_ss=0.5 → act=(0.5-0.2)×1.0=0.3（降低但非零）
- 或降低 relay R_leak：`10.0 → 2.0`，降低 relay V_ss

> [!WARNING]
> 修改增益链会影响所有趋热性实验（EXP-009, EXP-016 等），需要重新校准。

### C. 添加基线减法（推荐）

在 `get_mechanical_inputs()` 中减去 ambient 基线：
```python
baseline = self._ambient_relay_baseline  # 初始化时记录
result[f"therm_{pid}"] = max(0, self.relays[pid]._activation_ema - baseline)
```
这等价于生物体的**适应**（habituation）：恒定刺激不产生信号。
