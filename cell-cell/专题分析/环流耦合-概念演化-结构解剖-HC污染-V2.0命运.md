# 环流耦合 — 概念演化·结构解剖·HC污染·V2.0命运

> **类型**: 专题分析（融合版）
> **日期**: 2026-07-02
> **关联**: [[00_Dashboard/核心词条索引]] · [[工作报告/全链路审计综合报告_2026-07-02_Part1]] · [[docs/concept_C001_circulation_architecture]]
> **前置阅读**: `docs/technical_debt_hardcoding.md`（HC-014/016/017/030）, `nexus_v1/RULES.md`（结构优先原则）

---

## 一、概念演化时间线

环流耦合是本项目从 "标量奖励" 模型转向 "结构涌现" 模型的**分水岭**设计。以下是概念演化的完整时间线：

```
2026-05-17  提出"实践层 → 行为层"环形反馈（Xin 残差在闭环中的角色）
2026-05-18  正式提出"环流"概念——信号沿已有拓扑形成闭合回路
2026-05-21  四区划分：前馈/反馈/跨轴/影子（不同参数，同一 Bundle 类型）
2026-05-22  超图数学建模——环流 = 超边上的信号流，CirculationMeter 作为纯仪表
2026-05-23  concept_C001 定稿——环流架构与赫布超图（环流没有专属管道）
2026-05-29  "时空环流"——时间与空间各自独立生成，环流是两者耦合的载体
2026-06-04  C3' 设计：进食-运动-体征的环流耦合（替代标量 DA 奖励）
2026-06-05  CirculationProportionCircuit 实现（Capacitor×3 + MOSFET 比较器）
2026-06-06  实施计划 C3'（MotionState 扩展 + 三振幅计算 + DA 释放）
2026-06-07  有损热源→体征→环流因果链路完整追踪
2026-06-08  环路设计阻断分析（影子层本体 + 时间耦合器 + 生命编码）
2026-07-02  全链路审计：环流耦合被 4 项 HC 污染
```

**关键转折点**：C3' 设计文档明确宣告"奖励不是标量——奖励是环流模式回归平衡的过程"。这否定了之前"热源→DA↑→学习↑→简单强化"的标量范式，将 DA 的语义从"外部奖励信号"重新定位为"内部稳态偏离信号"。

---

## 二、环流是什么（结构定义）

### 2.1 环流不等于 CirculationProportionCircuit

这是最常被混淆的一点。需要区分三个概念：

| 概念 | 类型 | 本质 |
|------|------|------|
| **环流** (Circulation) | 涌现动力学模式 | 信号沿闭合路径流动 |
| **CirculationMeter** | 纯观测仪表 | 测量环流强度 μ 和 P/R 路径 |
| **CirculationProportionCircuit** | 信号比例传感器 | 检测 ρ_homeo 偏离并输出 DA 电流 |

> **环流没有专属管道。** 环流是信号沿已有拓扑结构形成闭合回路时涌现的动力学模式。就像河流不需要"环流管"——水在河床里流动，地形决定了漩涡出现的位置。

### 2.2 三层追踪：环流在哪层诞生？

来自 [[archive/undated/analysis_circulation_structural_anatomy.环流的结构解剖 — 三层追踪]] 的精确解剖：

| 层 | 有环流？ | 环路结构 | 专属载体？ |
|----|---------|---------|-----------|
| **母结构** (HebbianCircuit) | ❌ | 纯前馈链 Aff→Enc→Col→Mot，无任何反馈连接 | — |
| **交感层** (VariantAdapter) | ✅ **大环流** | Col→Bind→Mot→FBCap→Col | BindingLayer + FBCap（但它们不是"为环流建的"）|
| **影子层** (ShadowSandbox) | ✅ **微环流** | s_col_i ↔ s_col_j（cross-axis 双向 bundle）| cross-axis 双向连接 |

**母结构没有任何反馈连接**。`bundle_role="feedforward"` 全部是单向。环流是在 VariantAdapter 通过以下两条新增反馈路径后才形成的：

#### 反馈路径 A：Motor → Column 抑制反馈（传出副本）

```
Motor neurons spike
    ↓ inject into FBCap (Capacitor, τ=0.5)
    ↓ leak(R=1.0)
FBCap.voltage → -fb_current → Column._membrane.inject(-fb_current)
```

代码位置：`variant_adapter.py L1312-1342`。物理载体：
- `_feedback_caps: Dict[str, Capacitor]` — 每个 motor 一个电容
- `_feedback_gain = 0.05` — 抑制增益
- `_feedback_tau = 0.5` — 时间常数（500ms）

#### 反馈路径 B：BindingLayer → Motor（间接闭合）

```
Col_i × Col_j → BindingCell_{i,j}.activation
    ↓ binding_motor_weights (Python dict, w=0.001)
Motor_m._membrane.inject(bind_current)
    ↓ (Motor spikes → FBCap → -fb → Col — 回到路径 A)
```

代码位置：`variant_adapter.py L1159-1175`。

完整闭合环路：

```
Col → Bind → Mot → FBCap → Col
 ↑                          ↓
 └──────────────────────────┘
```

### 2.3 影子层的微环流

影子层没有 Motor→Column 反馈，因此不存在大环流。但 s_col_i ↔ s_col_j 的双向 cross-axis bundle 形成 2-node 微环流：

```
s_col_yaw → s_cross_yaw_pitch → s_col_pitch → s_cross_pitch_yaw → s_col_yaw
```

信号在两个 column 之间振荡，振幅由 STDP 权重和 Xin 张力决定。

### 2.4 TemporalCoupler B-layer：环流的 "水位调节器"

B-layer 是一个**局部闭环**，不是环流本身：

```
ema_upstream → [MOSFET_up] → I_charge ↓
                                  [C_slow] → V_slow → R_leak_eff
ema_downstream → [MOSFET_dn] → I_drain ↑
```

- 上游 > 下游 → V_slow↑ → τ 变长 → 通过更多
- 下游 > 上游 → V_slow↓ → τ 变短 → 通过更少

B-layer 调节每条 bundle 上流过的"水量"，但环流的大环路（Col→Bind→Mot→FB→Col）是闭合路径。

> ⚠️ **已知问题**：审计 v1.0 发现 B-layer 电压 = 0.0，即 B-layer 从未实际工作。只有 C-layer（MOSFET 反馈）在工作，长时间基线追踪功能缺失。

---

## 三、C3' 环流比例模型（核心理念）

来自 [[archive/undated/design_homeostatic_circulation.C3-设计-进食-运动-体征的环流耦合]]：

### 3.1 三个子系统与环流通道

```
① 体征环流（主环流，平时 ρ≈0.7）：
   ThermalMembrane → ECM temperature → thermal signal → Enc → Col
   → 内部稳态参考 → 偏差信号 → 回到 ThermalMembrane

② 运动环流（通常 ρ≈0.2）：
   Motor → Muscle → Body → Otolith → Aff → Enc → Col → Motor
   （已存在且完整）

③ 进食环流（通常 ρ≈0.1）：
   thermal error → Col bias → Motor → Body move → 位置变化
   → 热源距离变化 → thermal 变化 → 回到 thermal error
```

### 3.2 环流比例动态

```
正常态：ρ_homeo≈0.7, ρ_motor≈0.2, ρ_feed≈0.1
        → DA 低，学习慢，系统维持现状

失衡态：thermal_err > θ_alert
        → ρ_homeo↓, ρ_motor↑, ρ_feed↑
        → 环流偏移 → DA ∝ |Δρ_homeo|
        → Motor STDP 增强 + Thermal→Col 增强
        → Body 向热源移动 → thermal_err↓ → ρ_homeo↑ → DA↓
```

### 3.3 影子层的角色

影子层通过 STDP 学到"正常态 = ρ_homeo≈0.7"的权重模式。当主层实际 ρ_homeo=0.4 时：

```
影子层 Xin = |预期 0.7 - 实际 0.4| = 0.3
影子层 ν = dXin/dt > 0
→ DA 释放（bundles_shadow_to_da）
→ 运动+进食被激活
→ 行动 → 回归 → 影子层 Xin→0 → DA 回落
```

**这就是 C1（shadow→DA）的正确解读**——不只是"误差驱动学习率"，而是**体征失衡驱动行为的完整机制**。

### 3.4 C5（三因子 Fruit）的自然消解

在环流耦合模型中，Fruit 不再需要独立设计：
- Fruit growing→ripe 的条件 = standing_wave_score 稳定 + DA 低（体征平衡）
- 如果 DA 持续高（体征失衡），Fruit 不成熟 → 系统保持可塑
- 只有环流回归平衡时，DA 下降，Fruit 才能成熟 → **垫支**
- "三者依靠影子层沉积"的实现——只有体征平衡时，结构才固化

---

## 四、代码实现现状

### 4.1 CirculationProportionCircuit（S0 合规）

`components/circulation_proportion.py`，TYPE:HYBRID。

```
thermal_stability ──→ [Cap_H] ──→ V_homeo
body_speed        ──→ [Cap_M] ──→ V_motor
feed_alignment    ──→ [Cap_F] ──→ V_feed

V_total = V_homeo + V_motor + V_feed
ρ_homeo = V_homeo / (V_total + ε)        ← 从电压比涌现，非 Python 除法

V_ref (set point=0.7) ──→ [Cap_ref]

deviation = |V_ref - ρ_homeo|             ← FIX-1: 双向偏差
da_current = MOSFET(gm=1.0, v_th=0.01).conduct(deviation)  ← S0 合规比较器
```

**设计优点**：
- 三个 Capacitor 做 RC 积分（τ=RC=200×50=10000步=10秒），符合下丘脑时间尺度
- MOSFET 比较器替代 `if deviation > 0.05`，硬阈值变成物理 v_threshold
- 比例从电压比较中涌现，不用 `a/(a+b+c)` Python 除法

**参数（"基因编码"等价物）**：
- `capacitance=200`, `leak_resistance=50`, `homeo_set_point=0.7`
- `deviation_threshold=0.01`（Epoch 1: 0.05→0.01，降低死区）
- `deviation_gain=1.0`（Epoch 1: 0.3→1.0，增强 DA 响应）

### 4.2 variant_adapter 中的调用链

```python
# L930-951: 信号采集
thermal_stability = 1.0 / (1.0 + thermal_err * 10.0)   # ← HC-014
body_speed = self.world.body.speed()
feed_alignment = max(thermo_vals) - min(thermo_vals)    # 已从 God-view 改为 patch 温差

# L950: CPC 步进
circ = self.circulation_proportion.step(thermal_stability, body_speed, feed_alignment, dt)

# L953-960: 写入 MotionState
ms.homeo_amplitude = circ['v_homeo']
ms.rho_homeo = circ['rho_homeo']
ms.homeo_deviation = circ['deviation']

# L1008-1013: Deviation → Motor 直接注入  ← HC-016
if deviation > 0.1:
    motor_drive = (deviation - 0.1) * DEVIATION_MOTOR_GAIN
    for mot in self.motor_neurons.values():
        mot._membrane.inject(motor_drive, dt)
```

### 4.3 DA DifferentialGate 替代了 CPC 的 da_current

`variant_adapter.py L315-317`:
```python
# Patch D: DADifferentialGate (VTA RPE signal)
# Replaces c3_da_current from circulation_proportion (absolute deviation).
self.da_gate = DADifferentialGate(initial_fill=self.energy_store.fill_fraction)
```

CPC 的 `da_current` 输出**已被 DADifferentialGate 替代**。DA 现在来自能量填充的变化率（RPE），不是来自环流比例的绝对偏差。这是正确的方向——DA 从"静态偏差信号"变为"动态变化检测"。

但 CPC 的 `deviation` 输出仍在使用（直接注入 Motor，HC-016）。

---

## 五、HC 污染全景

环流耦合的设计思想是干净的，CPC 的 Capacitor+MOSFET 实现也是 S0 合规的。但**输入端和输出端均被 Python 语义层短路**：

### 5.1 输入端污染

| 信号 | 代码 | HC | 问题 |
|------|------|----|------|
| `thermal_stability` | `1.0/(1.0+thermal_err*10.0)` | **HC-014** | Python soft-sigmoid，factor 10.0 无 BIO:。应为 ThermalMembrane 输出电压经 MOSFET 比较器 |
| `body_speed` | `world.body.speed()` | 干净 | 物理传感器信号 |
| `feed_alignment` | `max(thermo_vals)-min(thermo_vals)` | **部分干净** | 已从全局热源坐标改为 patch 温差，但上游 soma_output 被 HC-009 污染（thermoreceptors 直接注入） |

### 5.2 输出端污染

| 输出路径 | 代码 | HC | 问题 |
|---------|------|----|------|
| CPC.da_current → DA 注入 | 已被 DA DifferentialGate 替代 | **HC-017** | 原方案 `da_current` 直接 `inject` DA 膜，无 SynapticBundle |
| CPC.deviation → Motor 直接注入 | `mot._membrane.inject(motor_drive, dt)` | **HC-016** | 所有 Motor 等量注入，无方向性，无 SynapticBundle |
| Binding→Motor | `mot._membrane.inject(b_act * w * 0.1, dt)` | **HC-024** | Python dict 权重 (w=0.001)，无 Noether/census 可见性 |
| Motor→Column 反馈 | `col._membrane.inject(-fb_current, dt)` | **HC-016 延伸** | 虽有 Capacitor 滤波（S0 合规），但注入仍是 `_membrane.inject()` 直连而非 SynapticBundle |

### 5.3 结构性 HC 汇总

| HC-ID | 严重度 | 位置 | 对环流耦合的影响 |
|-------|--------|------|-----------------|
| HC-014 | HIGH | variant L934 | thermal_stability 的 soft-sigmoid 无 BIO:，污染 CPC 的主输入 |
| HC-016 | HIGH | variant L1008-1013 | CPC.deviation → Motor 无 Bundle 注入，无方向性 |
| HC-017 | HIGH | variant L793-800 (原) | CPC.da_current → DA 直接注入（已由 DA DifferentialGate 替代）|
| HC-024 | HIGH | variant L1159-1175 | Binding→Motor 权重为 Python dict + inject，对 Noether/census 不可见 |
| HC-007 | CRITICAL | hebbian L547-561 | extra_axes 无 SynapticBundle，热觉信号的第一跳无 STDP/Xin |
| HC-009 | CRITICAL | somatosensory L345 | thermoreceptors 直接注入，L0 感觉边界违规，feed_alignment 上游被污染 |
| HC-030 | HIGH | neuron L593 | I²R 用钳位前电流，高估耗散→能量不守恒→反馈抑制计算偏差 |

### 5.4 关键缺口（非 HC，但阻塞环流闭合）

1. **damage_integral 不回传体征**（来自 `analysis_heat_damage_circulation`）：组织损伤不引起 VitalOsc 频率下降、EnergyStore 代谢增加、ECM 炎症。有害热源没有"有害"的物理后果。
2. **B-layer 电压 = 0.0**（审计 v1.0）：TemporalCoupler 长时间基线追踪功能从未生效。
3. **无硬连线撤退反射**：伤害回避需经 `Noci→Relay→extra_axes→Enc→Col→Motor` 学习路径，初始权重下无法驱动有效运动。唯一非学习路径（C.04 deviation→Motor）不区分方向。

---

## 六、实验历史中的环流状态

### 6.1 环流=0 诊断（2026-05-23）

```
bind_yaw_pitch 激活 = 10.0     ← 绑定层工作
col_yaw 激活 = 1.73            ← Column 工作
bind→mot 权重 = 0.001          ← 极弱
feedback_trace = 0.004         ← 弱但存在

flow = 1.73 × 10.0 × 0.001 × 0.004 = 0.00007
MIN_FLOW = 0.001
0.00007 < 0.001 → 被过滤 → μ=0
```

根因：`binding_motor_weights=0.001` 是瓶颈，不是 MIN_FLOW 阈值太高。绑定层激活已经很强（=10.0），但绑→运权重太低。

### 6.2 环流 μ 已可测（2026-05-24 修复后）

MIN_FLOW 降低为 `1e-5` 后，环流变为可测量：
- 活跃路径: 60 条
- P 路径: yaw→bind_yaw_pitch→move_x (flow=0.000396)
- μ_total: 0.0205
- flow 方差: 7.7e-6

### 6.3 Phase 5/6/7/8 中的环流

环流测量在这些实验中**持续运行但从未被独立分析**。因为在 HC-005/006/012 三重污染下，行为由 Python 层驱动，环流只是被动跟随的信号涟漪——不是涌现，是附带现象。

---

## 七、V2.0 中的环流耦合命运

### 7.1 保留（Preserve）

| 保留项 | 理由 |
|--------|------|
| `CirculationProportionCircuit` | Capacitor+MOSFET 实现正确（S0 合规），稳态检测逻辑干净 |
| `CirculationMeter` | 可观测性基础设施，纯仪表无污染 |
| C3' 三比例模型 | 设计思想正确（ρ 驱动稳态回归），只是信号输入/输出被短路 |
| FBCap 反馈路径 | Motor→Capacitor→Column 的 Capacitor 滤波是 S0 合规的 |
| DA 三因子门控框架 | DA→STDP 门控机制正确 |
| Shadow→DA 路径 | Xin→DA 的 SynapticBundle 传播是真实涌现（EP-002） |

### 7.2 删除（Delete）

| 删除项 | HC | 理由 |
|--------|-----|------|
| `thermal_stability = 1/(1+err×10)` | HC-014 | Python soft-sigmoid 替代为 ThermalMembrane MOSFET 输出 |
| CPC.deviation → Motor `inject()` | HC-016 | 所有 Motor 无差注入，替代为 Renshaw 中间神经元 SynapticBundle |
| CPC.da_current → DA `inject()` | HC-017 | 已被 DA DifferentialGate 替代（确认已删除）|
| `binding_motor_weights` Python dict | HC-024 | 隐藏连接，对 census 不可见 |
| World `get_heat_source_position()` | HC-006 延伸 | God-view 坐标，已被 patch 温差替代（确认） |

### 7.3 新建（Add）

| 新建项 | 替代 HC | 生物对应 |
|--------|---------|---------|
| `bundles_homeo_drive_to_da` | HC-017 | 下丘脑→VTA 通路 |
| `homeostasis_relay` Neuron | HC-017 | 稳态驱动继电神经元 |
| `Renshaw_interneuron_{axis}` + 两条 Bundle | HC-016 | Renshaw 细胞侧抑制 |
| `half_wave_rectifier` ChannelConfig | HC-021 | Xin 方向分离 MOSFET |
| 修复 B-layer 电压=0 问题 | (审计 L05) | 时间尺度分离 |
| `damage→VitalOsc` 物理链路 | (缺口1) | 损伤→体征→环流闭合 |

### 7.4 V2.0 优先级

```
P0（必须先做）:
  ① 删除 HC-014（thermal_stability 改用 ThermalMembrane MOSFET 输出）
  
P2（DA 路径结构化）:
  ② 删除 HC-016（Motor 直接注入→Renshaw SynapticBundle）
  ③ 创建 bundles_homeo_drive_to_da（替代 HC-017）
  ④ 删除 HC-024（binding_motor_weights→SynapticBundle）

P3（Shadow + 运动系统）:
  ⑤ 创建全 col→mot 稀疏连接（替代 HC-011 mot_assignment）
  ⑥ B-layer 修复（审计 L05）

P5（体征-环流闭合）:
  ⑦ damage→VitalOsc 物理链路
  ⑧ damage→EnergyStore 代谢增加
```

---

## 八、核心结论

### 8.1 一句话

> **环流耦合是本项目从标量奖励转向结构涌现的关键设计。其思想是干净的（ρ 比例驱动稳态回归，影子层沉积正常态），CPC 实现是 S0 合规的（Capacitor+MOSFET），但信号的输入端（HC-014 thermal_stability 的 Python sigmoid）和输出端（HC-016 Motor 直接注入、HC-024 Binding 隐藏权重）都被 Python 语义层短路，导致环流无法作为涌现机制独立运行。**

### 8.2 设计哲学

环流耦合不是失败的设计——它是正确的方向，只是在 V1 实施中被四面八方的 HC 违规围困。V2.0 P0+P2 修复后，预期可以：

1. **方向性热趋性**从结构中涌现：patch-specific soma_to_da + transducer 换能束 → right patch 更热 → right DA↑ → right STDP LTP → wR>wL → motor_yaw_right 增强 → body 右转
2. **能量依赖的行为切换**：PowerRail 限流 → 活动降低 → Xin 累积 → 结构生长 → 新束连接能量获取路径
3. **DA 调制的学习速度控制**：成功接近热源 → DA↑ → plasticity_by_stage↑ → 学习更快。失败远离 → DA↓ → 学习慢

### 8.3 C3' vs C1：两条 DA 通路的分工

```
C1 (微观): shadow Xin → bundles_shadow_to_da → DA → 快速精细调制（单 bundle 级）
C3' (宏观): CPC deviation → bundles_homeo_drive_to_da → DA → 慢全局调制（系统级）
```

两条通路互补：C1 做精细的"这个连接该不该学"，C3' 做全局的"现在是不是该行动了"。

C1 已在代码中完整实现（SynapticBundle + STDP）。C3' 缺的只是：输入端去 HC-014（改用 ThermalMembrane MOSFET 输出），输出端去 HC-016/017（改用 SynapticBundle）。

---

**关联文件**:
- `docs/concept_C001_circulation_architecture.md` — 环流架构概念定义
- `docs/theory/T004_circulation.md` — 环流理论文档
- `archive/undated/analysis_circulation_structural_anatomy.环流的结构解剖 — 三层追踪.md` — 三层解剖
- `archive/undated/design_homeostatic_circulation.C3-设计-进食-运动-体征的环流耦合.md` — C3' 设计
- `archive/undated/analysis_heat_damage_circulation(有害热源 → 体征 → 环流：因果链路完整追踪).md` — 有害热源因果链
- `2026-06/analysis_loop_design_blockers.环路设计阻断分析-影子层本体-时间耦合器-生命编码.md` — 环路阻断分析
- `2026-05/analysis_circulation_zero_diagnosis.2026.5.23.md` — 环流=0 诊断
- `nexus_v1/components/circulation_proportion.py` — CPC 源码
- `nexus_v1/circuit/circulation.py` — CirculationMeter 源码
- `nexus_v1/circuit/variant_adapter.py` — 环流耦合调用链源码
