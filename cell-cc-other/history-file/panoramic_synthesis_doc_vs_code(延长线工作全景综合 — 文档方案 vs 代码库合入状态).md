# 延长线工作全景综合 — 文档方案 vs 代码库合入状态

> 扫描时间：2026-06-20（代码实物验证完成）
> 文档目录：`D:\cell-cc\cell\other\`（27 份文件）
> 代码库基准：commit `9257555` + V8 选择性合入
> **验证工具**：`diag_bundle_audit.py` 直接运行 VariantCircuit 输出参数

---

## 一、文档体系图谱

```
皮层除颤（P2/P1/P0）         ← 大一统方案的第一刀
    │
    ├── 除颤后病理暴露
    │     ├── DA 再饱和           → 影子层大一统方案 §4.2
    │     └── 钙离子死亡之谷       → 影子层大一统方案 §4.3
    │
    ├── 六刀修复（战役一至四）    ← 大一统方案执行
    │     ├── 战役三：XIN_GAIN 3→1
    │     ├── 影子归一：vr_base_rate 0.01→0.05
    │     ├── 战役一：DA 净空锁 w=0.1
    │     ├── 战役二：Col CRI 激活
    │     └── 战役四：脊髓扩音 gain=10, lr=0.05
    │               ↑ 仅热感束落地！vestibular 束仍旧值
    │
    ├── V8 引擎               ← 步骤2双轨并行方案
    │     ├── V8.1: LangevinNoise 组件化  ✅
    │     ├── V8.2: OU 注入 oto_x/y/z    ✅
    │     ├── V8.3: Memristor 负阻修复    ✅
    │     └── V8.4: 热编码CRI参数         ❌ 绝对否决
    │
    └── 双源驱动缝合
          ├── Phase 3: Thermal→Motor 差分对束  ✅ 已合入（±10.0 gain）
          ├── Phase 0: Memristor 钳位          ✅ 已合入
          └── Phase 1: 反射增强 + DA 门控      ⚠️ 部分合入
```

---

## 二、实物验证结果（diag_bundle_audit.py 输出）

```
=== bundles_vest_to_enc (aff→enc) ===
  aff_reg_to_enc_yaw:  initial_weight=0.2  weight_max=1.0  synapse_gain=2.0  lr=0.01
  aff_irr_to_enc_yaw:  initial_weight=0.2  weight_max=1.0  synapse_gain=2.0  lr=0.01
  (全部 12 束相同)

=== bundles_col_to_motor — vestibular 轴特异束 ===
  col_yaw_to_move_x:   initial_weight=0.4  weight_max=0.5  synapse_gain=5.0   lr=0.005
  col_pitch_to_move_y: initial_weight=0.4  weight_max=0.5  synapse_gain=5.0   lr=0.005
  col_roll_to_move_z:  initial_weight=0.4  weight_max=0.5  synapse_gain=5.0   lr=0.005

=== bundles_col_to_motor — thermal 差分对束 ===
  therm_therm_front_to_move_x:  initial_weight=0.1  weight_max=0.5  synapse_gain=+10.0  lr=0.05
  therm_therm_back_to_move_x:   initial_weight=0.1  weight_max=0.5  synapse_gain=-10.0  lr=0.05
  therm_therm_left_to_move_y:   initial_weight=0.1  weight_max=0.5  synapse_gain=+10.0  lr=0.05
  therm_therm_right_to_move_y:  initial_weight=0.1  weight_max=0.5  synapse_gain=-10.0  lr=0.05
```

---

## 三、逐项合入状态

### ✅ 已完全合入（代码已验证）

| 项目 | 来源文档 | 代码位置 & 实际参数 |
|------|---------|-------------------|
| 皮层除颤三刀 (P2/P1/P0 — Langevin+OU注入) | 皮层除颤大一统方案 | `variant_adapter.py` L666-668 |
| 战役三：XIN_GAIN 3→1 | 战役三 | `shadow_sandbox.py` |
| 影子归一：vr_base_rate 0.01→0.05 | 战役三 | `shadow_sandbox.py` |
| 战役一：shadow_to_da w=0.1 | 战役一 | `variant_adapter.py` |
| 战役二：Col CRI 激活 (Ca ΔCa/γ≈20) | 战役二 | `hebbian.py` |
| **aff→enc synapse_gain=2.0** | 皮层除颤大一统方案 §4.4 | `hebbian.py` L377,403 ✅ |
| V8.1 LangevinNoise (σ₀=0.70, OU) | V8/步骤2架构方案 | `components/langevin_noise.py` |
| V8.2 OU 注入 oto_x/y/z (宏微观同构) | V8方案 | `variant_adapter.py` L666-668 |
| V8.3 Memristor w_safe 钳位 | 双源驱动 §Phase 0 | `semiconductor.py` L222-223 |
| conductance 硬上限 | 双源驱动 §Phase 0 | `semiconductor.py` |
| **Phase 3 Thermal→Motor 差分对束** | 双源驱动/最终执行蓝图 | `hebbian.py` L532-573: ±10.0 gain, lr=0.05 ✅ |
| Phase 4 AGC (τ≈40k, g_max=4) | Phase 4 AGC 方案 | `components/agc.py` |
| 饥饿驱动趋热反射 (AGC×gain_multiplier) | Phase 4 AGC 方案 | `variant_adapter.py` L790-796 |

---

### ❌ 未合入（代码验证后确认缺失）

| 项目 | 文档要求 | 代码实际 | 来源文档 | 影响 |
|------|---------|---------|---------|------|
| **aff→enc initial_weight** | 2.5（Class 1 Driver） | **0.2** | 皮层除颤大一统方案 §4.4 P0 | Enc 被 Aff 驱动不足；<br>但注释说当前 gain=2.0 下 Vm≈0.8 正常 |
| **aff→enc weight_max** | 5.0 | **1.0** | 同上 | STDP 成长天花板低 |
| **vestibular col→motor synapse_gain** | 10.0（战役四） | **5.0** | 战役四工作报告 | 旋转/平移→Motor 驱动力减半 |
| **vestibular col→motor stdp_lr** | 0.05（战役四） | **0.005** | 战役四工作报告 | vestibular STDP 学习速度比 thermal 慢 10× |
| **Phase 1 DA 浓度直接门控反射** | `gain = DA × (max-min) + min` | AGC 间接门控 | 双源驱动方案 §3.2 | 间接实现，非完整 |
| **长程演化验证 500k-1M 步** | 500k-1M 步 | EXP-022: 200k 步 | V8引擎点火报告 §六 | 未完成 |

> **注意**：战役四文档要求 vestibular 轴特异束 gain 5→10, lr 0.005→0.05。
> 代码审计发现：**该提升只被应用到了 thermal 差分对束**（±10.0, lr=0.05），
> `col_yaw/pitch/roll_to_motor` 束仍保留旧值（5.0, 0.005）。
> 这是一个**遗漏的半实施**。

---

### 🚫 绝对否决（永不合入）

| 项目 | 来源文档 | 否决理由 |
|------|---------|---------|
| V8.4 热编码改非脉冲 + CRI 参数修改 | V8方案 §4 | 破坏 Phase 1-3 已验证回归；用户明确否决 |
| Phase 2 Klinotaxis (dT→转向硬编码) | 双源驱动方案 §178 | 语义捷径，违背物理涌现原则 |
| 修改 C_max=20（束容量上限） | 影子层大一统方案 §3.1 | "颅骨闭合不可修改"——物理边界 |
| cross-axis 增益提升 | 双源驱动方案 §151 | 维持自由度隔离 |

---

## 四、关键差距分析

### 差距一：战役四半实施（最高优先级）

战役四的核心目标是"脊髓扩音"——提升 Col→Motor 的驱动力。
但当前代码只把 gain=10, lr=0.05 施加到了**热感束（thermal）**，
vestibular 轴束（负责旋转/平移运动）仍在旧值 gain=5.0, lr=0.005。

`hebbian.py` 相关位置：
- [L480-500](file:///D:/cell-cc/nexus_v1/circuit/hebbian.py#L480-L500)：vestibular 轴特异束定义（旧值）
- [L532-573](file:///D:/cell-cc/nexus_v1/circuit/hebbian.py#L532-L573)：thermal 差分对束定义（新值）

**修复方法**（2 行改动，`hebbian.py` L484-485）：
```python
# 当前
stdp_lr=0.005,
synapse_gain=5.0,

# 改为（战役四完整落地）
stdp_lr=0.05,
synapse_gain=10.0,
```

### 差距二：aff→enc Class 1 Driver 权重

文档要求 `initial_weight=2.5`，实际 `initial_weight=0.2`。
但代码注释说 `gain=2.0 → I=0.17 → Enc Vm≈0.8, act≈0.7 (healthy)`，
说明**当前系统通过 gain 而非 weight 来保证皮层击穿**。

如果 Enc 确实能够激活（EXP-022 已显示皮层觉醒），这个差距可能不是紧急问题。
若未来遇到 Enc 静默的情况，才需要提升 initial_weight。

---

## 五、文档覆盖率总表

| 文档 | 核心方案 | 合入状态 |
|------|---------|---------|
| 皮层除颤大一统方案 | P2/P1/P0（Langevin + Class 1 gain） | ✅ gain=2.0 合入；initial_weight=0.2（非2.5） |
| 影子层大一统方案 | 六刀修复（战役一至四） | ⚠️ 战役四 vestibular 束未完整落地 |
| 步骤2双轨并行方案 | VitalOscillator + Langevin 双轨 | ✅ 全部合入 |
| V8引擎选择性合入方案 | V8.1-3 合入，V8.4 否决 | ✅ 按方案执行 |
| 双源驱动统一方案 | Phase 0/3 合入，Phase 1 部分 | ⚠️ Phase 1 DA 门控待落地 |
| 最终执行蓝图（拓扑修补） | Phase 0+3 | ✅ 已合入 |
| V8引擎点火长程验证 | 200k 步验证 | ✅ EXP-022 完成 |
| 战役一/二/三/四工作报告 | 六刀执行记录 | ⚠️ 战役四 vestibular 束遗漏 |
| Phase 4 AGC 方案 | AGC + 饥饿驱动 | ✅ 全部合入 |
| 长程演化验证方案 | 100k 步基准 | ✅ EXP-021/022 完成 |
| 热趋性行为分析 v1/v2 | 诊断报告 | 参考文档（非执行） |
| soma_to_da 参数分析 | DA 参数标定 | ✅ 战役一落地 |
| 熵账本修复报告 | 能量账本安装 | ✅ 已合入 |

---

## 六、建议执行顺序

### 🔴 立即可做（2行改动，低风险）
补全战役四——将 vestibular col→motor 束的参数与 thermal 束对齐：
- `hebbian.py` L484: `stdp_lr=0.005` → `0.05`
- `hebbian.py` L485: `synapse_gain=5.0` → `10.0`

运行 `pytest -x -q` 验证回归。

### 🟡 条件性（需观察）
- **Phase 1 DA 门控**：若 AGC 间接门控已足够，可暂缓
- **aff→enc initial_weight 2.5**：若 Enc 激活正常，不需要修改

### 🟢 长期
- **代谢壁调查**：fill 100k 步耗竭的能量预算分析（独立于以上）
- **500k+ 长程运行**：验证 STDP 权重成熟时间线
