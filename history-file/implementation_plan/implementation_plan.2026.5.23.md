# L6 Motor 层母本分化 — 实施计划

## 问题描述

L6 Motor 层在 50000 步后能量降至 E=0.14，趋势 -0.076/步，heat=1000。
隔离分析确认根因：

### 能量收支方程

$$\frac{dE}{dt} = \text{VR\_recovery} - \text{heat} = 0.1 - (I/\text{inertia})^2 \times R_{\text{supply}}$$

在典型输入 I=0.917（col->mot propagation）下:

| 项目 | 值 | 公式 |
|------|-----|------|
| I_scaled | 1.83 | I / inertia = 0.917 / 0.5 |
| heat/step | 0.335 | I_scaled² × r_supply = 1.83² × 0.1 |
| VR recovery/step | ~0.1 | vr_base_rate (activity 贡献小) |
| **净消耗** | **-0.235/step** | 0.1 - 0.335 |

Motor 能量从 1.0 → 0.10 后，PowerRail 自限（V_avail → 0），达到"死平衡"：
- 够低不会死（E>0）
- 不够高不能 spike（V_mem 无法到 v_peak=0.3）

### 生物学对应

真实运动神经元有以下保护机制：
1. **Na⁺通道失活** — 反复放电后阈值升高（= adapt_threshold）
2. **突触缩放** — 长期高活动后突触后效率下调（Turrigiano 2008）
3. **ATP 感应** — ATP 耗尽时释放腺苷，全局抑制（= energy-gated suppression）

> [!IMPORTANT]
> 项目中 `MOSFET.adapt_threshold()` 已存在但**从未被调用**。
> 本次分化的核心是**连接已有机制**，而非创造新机制。

---

## Proposed Changes

### HebbianCircuit (母本)

#### [MODIFY] [hebbian.py](file:///d:/cell-cc/nexus_v1/circuit/hebbian.py)

**修改 1: Motor config — 调整 VR 参数匹配实际热耗散**

```python
# 当前:
vr_base_rate=0.1        # << heat=0.335 at typical input
vr_max_rate=3.0

# 修改为:
vr_base_rate=0.5        # 接近典型 heat 率
vr_activity_coeff=1.0   # 活跃时恢复更快
vr_max_rate=5.0         # 提高上限
```

推导: heat_typical = 0.335, 需要 VR ≥ 0.335。
base=0.5 + activity_coeff×EMA ≈ 0.5 + 1.0×0.1 = 0.6 > 0.335 ✓

**修改 2: 在 step() 中连接 adapt_threshold()**

在 `HebbianCircuit.step()` 中，每 100 步检查 Motor 能量，调用 adapt_threshold：

```python
# 在 learn() 之后添加:
# ── Motor homeostasis: adapt_threshold when energy is low ──
if self._step_count % 100 == 0:
    for key, mot in self.motor_neurons.items():
        if mot.energy < 0.3:  # energy critically low
            # Raise firing threshold → reduce spike rate → reduce heat
            channel = mot._channels.get("default")
            if channel:
                # Target: rate should decrease when energy is low
                actual_rate = mot.firing_rate()
                target_rate = actual_rate * (mot.energy / 0.5)  # scale down
                channel.adapt_threshold(actual_rate, target_rate, rate=0.005)
```

BIO: Na⁺通道失活 → 阈值升高。rate=0.005 给出缓慢适应（τ_adapt ≈ 200 步）。

**修改 3: 突触缩放 — 当 Motor 能量低时下调 col_to_motor synapse_gain**

```python
# Motor 能量低于阈值时，全局降低 col_to_motor gain
avg_motor_e = sum(m.energy for m in self.motor_neurons.values()) / len(self.motor_neurons)
if avg_motor_e < 0.4:
    energy_ratio = avg_motor_e / 0.4  # 0→1
    for b in self.bundles_col_to_motor:
        # synapse_gain 从 base_gain 缩放到 base_gain × energy_ratio
        b.config.synapse_gain = self._base_col_mot_gain * max(0.1, energy_ratio)
```

BIO: 突触缩放（Turrigiano 2008）— 当后突触细胞活动过高时，
AMPA 受体数量减少，降低突触效率。

---

## Open Questions

> [!IMPORTANT]
> **Q1**: adapt_threshold 修改的是 MOSFET.v_threshold，这属于**母本内部参数**的运行时修改。
> 这是否违反"母本不变"原则？
> 
> **分析**: 原则 11 明确说"从母本出发，逐块建模、调整"。adapt_threshold 本来就是
> 母本的 MOSFET 方法。在 HebbianCircuit.step() 中调用它是正当的母本分化。
> VariantCircuit 继承时会自动获得这个行为。

> [!NOTE]
> **Q2**: VR base_rate 从 0.1→0.5 是 5× 增加，是否有生物依据？
> 
> **推导**: Motor neuron 的代谢率高于感觉神经元（Roberts 2003）。
> 运动皮层 ATP 消耗率约为 sensory cortex 的 2-3×。
> 0.5/0.1 = 5× 偏高，但考虑到归一化和 I²R 模型的简化，可接受。
> 标注: `# ESTIMATED: ~5x sensory VR, CONFIDENCE: medium`

---

## Verification Plan

### Automated Tests
1. `python -m nexus_v1.run_variant_contracts` — 5/5 PASS (母本不退化)
2. 重跑 `test_motor_isolation.py` — Motor E 应稳定在 E>0.5（而非 0.10）
3. 重跑 `test_combined_entropy_shadow.py` — Motor heat 应显著降低
4. 验证 adapt_threshold 确实被调用（打印日志）

### 契约验证
Motor 层契约:
- output_type: spiking
- E > 0.3 (目前 FAIL: E=0.14)
- firing_rate: 1-50 Hz (目前 OK: ~7 Hz at I=2)
