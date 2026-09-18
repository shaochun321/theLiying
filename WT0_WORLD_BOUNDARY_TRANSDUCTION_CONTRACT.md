# WT0_WORLD_BOUNDARY_TRANSDUCTION_CONTRACT — 三对象合同 + 转导角色审计

日期：2026-09-18
依据：外部《WT0 方案》§3/§6/§8/§9/§10 + 用户裁定 R-1~R-4（2026-09-18，
见 `cell-cell/交叉比对/WT0与T1A方案评判_2026-09-18.md` §五）。
冻结序（R-1）：**WT0 → T1-A → W1 → T1-B → G0**（"T1-B"命名系 R-2 裁定）。

---

## 一、三对象合同（§3）

| 对象 | 定义 | 当前代码实体 |
|---|---|---|
| X_W(t) | 完整 World 状态 | `ThermalFieldGraph` 全部节点 charge（三点实例=3 标量） |
| Y_B(t)=B_W[X_W] | 允许跨边界传递的物理量 | 皮肤接触节点温度（组成见 §二） |
| u_i(t)=𝒟_i[Y_B] | 生成元输入 | `skin_transduction.transduce()` 输出 |

**访问禁令**（合同强制，审计入口）：
```text
G0 不得访问 X_W          —— 实测：wrap_base_generator 句柄无 World 引用；
                            Boundary Replay Gate1 逐位一致证明无隐藏通路
D_i 不得访问 X_W 隐藏态   —— transduce() 为纯函数，仅消费标量 q_skin
D_i 只能消费 Y_B          —— tick_from_skin(q_skin, ...) 签名即合同
```
唯一合法通路：X_W → B_W → Y_B → 𝒟_i → u_i。
边界重放实测（`research/wt0/wt0_boundary_replay.py`）：
`HIDDEN_SIDE_CHANNEL = PASS`（Gate0 自确定性 + Gate1 live/replay 均逐位一致）。

## 二、Y_B 组成的显式定义（R-3 落实）

登记两种边界配置，实验必须声明使用哪种，禁止隐含：

| 配置名 | Y_B 组成 | 隐藏态 | 用途 |
|---|---|---|---|
| `BOUNDARY_FULL_P2A` | {node0, node1, node2} 温度（现行 P2-A 接线，每节点独立 D_i） | **无**（三节点即全场，World v1 此配置下无隐藏自由度） | 既有 P2-A/G0 全部实验 |
| `BOUNDARY_REDUCED_N0` | {node0} 温度 | node1/node2 为隐藏动力学自由度 | WORLD_HIDDEN_DYNAMICS_POSITIVE_CONTROL 及后续有限观察实验 |

W17 资格（World v2 必须天然支持 X_A≠X_B 而 Y_A=Y_B 且未来 Y_A⁺≠Y_B⁺）
在 v1 上仅 `BOUNDARY_REDUCED_N0` 配置可表达——已由正对照 ESTABLISHED
（见 `WT0_POSITIVE_CONTROL_AND_REPLAY_REPORT.md`）。

## 三、LEGACY_TRANSDUCTION_ACTIVE_WINDOW 登记（§6）

```text
LEGACY_TRANSDUCTION_ACTIVE_WINDOW
    q_floor   = 40.01276      （u>0 ⇔ q>q_floor）
    q_ceiling = 69.09708      （u=0.04 ⇔ q≥q_ceiling）
    width     = 29.08432
```
（由 canonical κ/b 反解，评判已核实；与 T0 报告 T_floor/T_ceil 一致。）
资格域实测见 T0（scale∈[0.65,1.5] 三对全保留，双侧有界）与本轮
cross-pair 矩阵（κ 合法域内变化即可将全部历史推出窗外）。

## 四、TRANSDUCTION_REQUIREMENTS（§8/§10——本轮只立要求，不冻结参数）

目标 = **controlled physical reduction**（非 lossless encoding，非 I(Y;u)
最大化）。任何 Transduction v2 候选必须满足：

1. **丢失是明确的**——被删除的自由度可登记（哪段幅值/哪类时序被压掉）。
2. **丢失来自物理/接口能力**——不来自旧场景专用调参（稳态端点标定法已
   由 T1-A 方案 §4 裁定退役）。
3. **换合法 World 实例后不完全失效**——cross-pair 实测（本轮 §五.3）
   证明 legacy 不满足此条：κ=0.1 时 6/66 对完全湮灭、全网格无保真区。
4. **不产生 baseline-zeroing 假放大**——本轮矩阵实测 legacy 全部有效对
   retention∈[1.09, 5.03]（κ∈{0.025,0.05}档无一对 ≤1），即**全部处于
   失真放大区**；度量必须按 T1-A §8 并报绝对值+占用率。
5. **静息附近可见性**——现行 b=−0.055 把 q<40.01 全部藏入死区（T0 已证
   >92% 参考轨迹样本被地板 clip），v2 必须使静息以上偏离可见。

禁止（§2/§8）：以 occurrence 数量最大化为转导优化目标；本轮寻找新
κ/b/clip（只用 World v1 重标会再造 World_v1↔D_i 共适应）。

## 五、转导角色审计（§9）—— TRANSDUCTION_ROLE 判定

### 1. 证据链

- **𝒟_i 现状**：`skin_transduction.transduce()` = affine+clip 纯函数，
  TYPE:INFRA，自述"纯函数映射，不含物理机制"。
- **消费端语义**：`BaseGenerator.feed_from_skin()`（`base_generator.py`）
  将 u_i 送入 `_propagate()` 的 **dT_raw 位置**——该端口语义是"原始温度
  差"（`feed()` docstring），L1 按 `max(0, dT−T_THRESHOLD)` 消费。
- **L1 真实身份**：G0 的 L1 = `ThermalDeltaNeuron`
  （`nexus_v1/somatosensory/transducer_neurons.py:252`），BIO 合同 =
  Type II AMH **dT/dt 温升率检测器**（REF: LaMotte & Campbell 1978；
  Norris et al. 2021），SEMI = MOSFET 半波 `max(0, dT×200)`（clamp 10）。

### 2. 判定

```text
𝒟_i 名义角色 = 单位/尺度转换端口（TYPE:INFRA 自述）
𝒟_i 实际承担 = 幅值窗选择（clip 窗）+ 事件筛选（死区把 q<40 全部静默，
               直接决定 G0 可见事件集）+ 动态范围选择（interior 目标区）
且其输出被下游按【速率】语义消费，而幅值→速率的物理换能本应由
L1 ThermalDeltaNeuron（真实动态换能层）承担。

TRANSDUCTION_ROLE = OVERLAPPING_UNRESOLVED
```

affine+clip 纯映射在偷偷承担事件筛选/幅值分类/动态范围选择（§9 明令
禁止的三项），且存在幅值↔速率语义错位——**双重感受加工现状成立**。

### 3. 职责指派（T1-A 必须解决的合同要求，本轮不实现）

- 𝒟_i 只许做**单位/尺度/接触物理**（边界物理量→生成元输入量纲），
  一切动态换能（相位性/适应/速率检测）归 L1 物理层；
- u 端口语义必须与消费端一致（幅值进幅值口，速率进速率口）——语义
  错位登记为 T1-A 候选族的第一约束；
- 事件筛选归 OccurrenceClosure（θ_up/θ_down/rearm 已是其职责），
  不许在转导层预筛。

## 六、本合同的效力边界

- G0/TSS 全程 READ_ONLY（§21）：本轮只运行未修改；重新打开 G0 的条件
  =（World qualified + Boundary qualified + D_i qualified + u_i 在合法
  物理输入域内）之后 G0 仍失败。
- 本合同不冻结任何 v2 参数；T1-A 在本合同约束下建立候选族。
