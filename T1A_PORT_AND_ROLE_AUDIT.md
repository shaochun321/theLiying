# T1A_PORT_AND_ROLE_AUDIT — 端口语义 / 量纲 / 职责矩阵 / L1 身份（审计三合一）

日期：2026-09-18
依据：外部《T1-A 执行方案》§3-§8（经评判 A1-A5 修正采纳）；WT0 冻结事实全部继承。
方法：只读代码审计，逐条带代码位置；不改任何 production。

---

## 一、端口语义逐级追踪（§3）——两条支路必须分开审

### 支路 P（生产量子元支路，`circuit.step()` 驱动）

| 变量 | 代码位置 | 物理/数学意义 | 状态? | 滤波? | 微分? | 阈值? | clip? | 事件选择? |
|---|---|---|---|---|---|---|---|---|
| T_env | `world.temperature_at(pos)` | 环境温度场点值 [T] | 场态 | — | — | — | — | — |
| SkinPatch.current_temperature | `world.py:215-237`（step_thermal） | 接触后皮肤温度：Fourier 传导 q̇=G(T_env−T) + RC 积分 + Langevin 噪声 [T] | **有**（RC 电容态 + _prev_temperature 寄存器） | RC 低通 | — | — | — | — |
| dT | `world.py:263-266`（property） | **每步离散差分** current−prev [T/step] | 消费 prev 寄存器 | — | **是** | — | — | — |
| L1 入口 dT_raw | `variant_adapter.py:1920` `l1_warm.step(dT)` / `l1_cool.step(-dT)` | 带符号温升率 [T/step] | — | — | — | — | — | — |
| L1 activation | `transducer_neurons.py:305-323` | `clip(max(0, dT_raw×200), 0, 10)` [无量纲激活] | **无**（瞬时；pre_trace/EMA 是输出侧痕迹） | — | — | 半波 max(0,·) | 上钳 10 | — |
| HC→ensemble→collector | `base_generator.py:184-198` | 毛细胞→阶梯阈值→AND 汇聚 [激活] | 神经元态 | 膜 RC | — | 各级阈值 | ±10 惯例 | — |
| collector.pre_trace | `sense()` | 发生检测信号 | 有 | trace 衰减 | — | — | — | — |
| occurrence | `closure.update()` | trigger/exit/rearm 状态机 | 有 | — | — | θ_up/θ_down | — | **是（唯一合法处）** |

**支路 P 语义自洽**：速率提取物理载体 = SkinPatch（RC 接触 + prev 寄存器），
L1 消费的确实是带符号温升率。

### 支路 W（TSS WORLD_COUPLED 支路，`tick_from_skin()` 驱动）

| 变量 | 代码位置 | 意义 | 备注 |
|---|---|---|---|
| X_W | `ThermalFieldGraph.cells[*].temperature` | 场节点温度 [T] | 三点实例=全场 |
| Y_B=q_skin | 调用方读 `cells[i].temperature` | 边界温度**幅值** [T] | 配置声明见 WT0 合同 §二 |
| u_i | `skin_transduction.transduce()` | `clip[κ(q−q0)+b]` [生成元输入单位 u] | 无状态纯函数；κ:[u/T]、b:[u] |
| feed 端口 | `base_generator.py:226-241` `feed_from_skin`→`_propagate(u_i)` | u_i 被送进 **dT_raw 位置** | `_propagate` 第一行 `self.l1.step(u_i, dt)` |
| L1 及以下 | 同支路 P | — | — |

**支路 W 语义错位**：幅值映射产物 u（[u]，源于温度**幅值**）被 L1 按
温升率（[T/step]）消费。

## 二、量纲追踪（§4）

| 量 | 量纲（约定单位，A5 纪律：如实登记不硬造） |
|---|---|
| [Y_B] | 温度 a.u.（Capacitor.charge 解释为温度） |
| [𝒟_i(Y_B)]=[u_i] | 生成元输入单位 u（无独立物理量纲；目标域 𝒟_disc^G） |
| [dT_raw]（端口声称） | 温度 a.u./步（**每步差分，未除以 dt**——见发现 D2） |
| [L1 input]（runtime 消费） | 与喂入者相同；×WARM_ONSET_GAIN=200 [激活/(T/step)] |
| S 映射 | **S_in,i = TransductionConfig**（已有代码登记：`natural_unit.py` `NaturalUnit.input_scale`）；S_out,i = dt（duration_seconds） |

**量纲发现**：
- **D1（支路 W 核心）**：[u] ≠ [T/step]，无任何 S 声明衔接——u 直接顶替
  dT_raw。`NaturalUnit.input_scale` 登记了 κ/b/clip，但**没有登记
  "幅值→速率口"这次隐式换类**。
- **D2**：`SkinPatch.dT` 是每步差分（未除 dt）——dt 改变则 dT 数值随之
  缩放，量纲上是 [T/step] 而非 [T/s]。生产路径 dt 恒定无害，登记为约束。
- **D3（双时钟）**：TSS 实验中皮肤 `g.step(dt=1.0)` 与生成元
  `tick_from_skin(..., DT=0.001)` 混用两个 dt（与 DEG-018 双时钟属同族，
  此处只登记不判死）。

## 三、§5 判定

```text
PORT_SEMANTIC_MISMATCH = CONFIRMED（支路级：仅 TSS WORLD_COUPLED 支路）
```
- 支路 W：legacy D 做 T→aT+b（幅值），进入 dT_raw（速率）口 → CONFIRMED。
- 支路 P：SkinPatch 差分产生真速率进速率口 → 语义一致（反证成立，不冤枉
  生产路径）。全局性表述被否决；后续文档引用本判定必须带支路限定词。

## 四、职责矩阵（§6）——现状实测（非应然）

| 功能 | Boundary/contact | D_i (transduce) | L1 (ThermalDelta) | OccurrenceClosure |
|---|---|---|---|---|
| 接触物理 | ✔ SkinPatch Fourier+RC（P）/ ThermalFieldGraph 热接触（W） | — | — | — |
| 单位转换 | — | ✔ κ,b | ×200 增益（隐性二次缩放） | — |
| 尺度映射 | — | ✔（[43.65,61.83]→[0.005,0.03]） | — | — |
| 温度→电信号换能 | — | — | ✔（activation 生成） | — |
| 时间微分/速率提取 | **✔ SkinPatch.dT（支路 P）** | ✘（无状态，不可能做） | ✘（无内部时间状态） | — |
| 动态适应 | — | ✘ | ✘（docstring 声称 phasic，runtime 无适应态） | — |
| 半波整流 | — | ✘ | ✔ max(0,·) | — |
| 饱和 | — | **✔ clip 0.04（越权）** | ✔ 上钳 10 | — |
| 事件阈值 | — | **✔ 死区 q<40 预筛（越权）** | 半波即隐性阈 0 | ✔ θ_up/θ_down（合法） |
| trigger/exit/rearm | — | — | — | ✔ 独占（合法） |

**重叠/越权清单**：①饱和三处（D_i clip、L1 上钳、Neuron ±10 惯例）；
②事件预筛两处（D_i 死区 vs closure θ_up——前者越权，WT0 已裁）；
③速率提取在支路 P 位于 Boundary 层、支路 W 缺位（幅值冒充）。

**类目冲突（新发现，本轮登记）**：`base_generator.py:100-103` 字段注释
自称 "l1/hc — **D_i^sim 转导层引用**（不属于生成元核心本身）"——TSS 轨
把 L1+HC 归入转导层；nexus 轨把 ThermalDeltaNeuron 归入 L1 感觉链。
**职责重叠有一半是两轨类目边界画得不一致**，登记：
```text
LAYER_CATEGORY_CONFLICT = CONFIRMED（TSS: D_i^sim ⊇ {transduce, L1, HC} vs
nexus: D_i = transduce, L1 = 感觉换能层）
```

## 五、L1 身份三层剥离（§8）

| 层 | 内容 | 实证 |
|---|---|---|
| BIO analogy | Type II AMH dT/dt 温升检测器，LPB→VTA 温暖奖励 | docstring REF: LaMotte & Campbell 1978；Norris 2021 |
| SEMI implementation | MOSFET 半波 + 增益 + 上钳 | `activation=clip(max(0,dT_raw×200),0,10)` |
| actual runtime | **瞬时无态整流器**：无 dT/dt 计算（消费外部差分）、无适应（"PHYS: step() bypasses RC"自证；pre_trace 0.99 衰减是突触前痕迹非受体适应）、每步输出只依赖当步输入 | `transducer_neurons.py:305-323` 全文 |

§8 七问答案：①方程=上式；②输入=外部供给的带符号每步温差（生产=
SkinPatch.dT，TSS=被冒充的 u）；③**无内部时间状态**；④**不实现
dT/dt**；⑤正是"把外部 dT 做 max(0,k·dT) 瞬时半波"；⑥adaptation
**不存在**（docstring 的 warm-onset 语义靠上游差分实现，非自身）；
⑦docstring 声称而代码没有的：速率检测（在上游）、phasic 适应（无处）。

## 六、决策门预登记（供终裁引用）

- Gate C（ThermalDeltaNeuron 是否真正实现速率职责）＝ **PARTIAL**
  （半波整流+增益是它的；微分不是它的，在 SkinPatch）。
- Gate E 素材：feed 端口的**声称语义**（dT_raw 速率）与 **de facto 用法**
  （P2-A 全部实验按抽象 u 喂）已分裂——端口需要改名或声明双语义。
- §23 红线适用性：支路 P 证明"由边界层物理载体做差分再喂 L1"在本项目
  是既存结构，Candidate B 的 𝒫_Ṫ 不必发明新对象。
