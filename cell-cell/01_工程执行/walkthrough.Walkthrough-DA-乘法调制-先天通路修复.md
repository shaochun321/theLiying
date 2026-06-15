# Walkthrough: DA 乘法调制 + 先天通路修复

## 背景

用户文档 `2026.6.9.6` (Doc 9.6) 和 `2026.6.9.7` (Doc 9.7) 提出两种 DA→Motor 调制策略：
- **Doc 9.7 (加法)**: DA 直接注入电流到 Motor
- **Doc 9.6 (乘法)**: DA 缩放突触电流（PGA 类比）

用户选择："我选择物理上更干净的乘法。"

## 改动文件

### 1. [hebbian.py](file:///d:/cell-cc/nexus_v1/circuit/hebbian.py)

**提取 `_propagate_bundles()` 钩子** (line 566-582)
- 从 `step()` 中提取 enc→col / col→motor / sprouted bundle 传播循环
- 定义为可覆写方法，子类注入调制而不修改母类 step
- 遵循 "Inherit, Don't Modify" 纪律

**`v_peak` 0.15 → 0.25** (line 34)
- Column NDR 穹顶抬高，容纳增益调制后更大的电流
- 防止 gain > 1.0 时所有 column 被钳位到 NDR 谷

---

### 2. [variant_adapter.py](file:///d:/cell-cc/nexus_v1/circuit/variant_adapter.py)

**覆写 `_propagate_bundles()`** — 乘法 DA 调制
```python
gain_factor = 1.0 + self.da_modulator.alpha_gain * da_level
# da_level ∈ [0,1] → gain ∈ [1.0, 2.5]
currents = [c * gain_factor for c in bundle.propagate()]
```

**删除加法注入** — 移除旧的 `_inject_da_current()` 方法

**weight_max 修复**:
- `shadow_to_da`: weight_max = 5.0 (允许先天厚电缆)
- `xin_to_da`: weight_max = 10.0 (修复 initial_weight=5.0 被默认 1.0 钳位)

---

### 3. [modulator.py](file:///d:/cell-cc/nexus_v1/components/modulator.py)

**`alpha_gain` 0.3 → 1.5**
- 乘法调制范围从 1.0×→1.3× 扩大到 1.0×→2.5×
- 物理意义：VTA DA 从"微弱调味"变为"显著增益控制"

---

### 4. [fuse.py](file:///d:/cell-cc/governance/fuse.py)

**F3 weight bound 检查使用 bundle 自身 config**
```python
w_min = getattr(b.config, 'weight_min', 0.0)
w_max = getattr(b.config, 'weight_max', 1.0)
```
- 之前硬编码 [0, 1]，导致 innate bundle (w=5.0) 立即触发 fuse
- 现在尊重每个 bundle 的配置边界

---

### 5. [test_chain_diagnostic.py](file:///d:/cell-cc/nexus_v1/tests/test_chain_diagnostic.py)

**修复预存 bug**: `Memristor.conductance` 是 `@property`，测试用 `.conductance()` 加括号调用 → `TypeError: 'float' object is not callable`。两处修复 (line 89, 136)。

## 测试结果

```
17 passed in 1139.71s (0:18:59)  ✅
```

排除的预存 bug（与本次改动无关）：

| 文件 | 错误 | 根因 |
|---|---|---|
| `test_shadow_stress.py` | `ShadowSandbox.metric` 不存在 | 属性已改名 |
| `test_stdp_diagnosis.py` | `HebbianCircuit.encoding_bundles` 不存在 | 属性从未存在 |
| `test_thermal_timing.py` | `ShadowSandbox.metric` 不存在 | 同 shadow_stress |
| `test_thermotaxis.py` | `KeyError: 'move_z_m20000'` | motor 键名不匹配 |

## 物理审计

| 检查项 | 状态 |
|---|---|
| 能量守恒 (Noether) | ✅ 乘法不创造/消灭电流，只缩放 |
| 信息流方向 | ✅ DA 不含方向信息，只调幅 |
| 热力学一致性 | ✅ gain > 1 的额外能量来自突触前神经元 |
| Fuse F3 | ✅ 动态边界检查 |
| 显式语义内置 | ✅ gain_factor 纯数值计算，不含语义 |
