# MAINLINE V2 — W1
## 条件物理 World v2 与有限观察环境池构建
### Agent 执行方案

---

# 0. 阶段宣告

从本轮开始，项目正式退出连续资格审计支线。

阶段状态：

```text
TSS = FROZEN
WT0 = CLOSED
T1-A = CLOSED
MAINLINE_V2 = STARTED
```

当前下一阶段：

```text
W1_WORLD_V2
```

本轮不是：

```text
新的 TSS 实验
新的转导资格审计
新的 G0 重构
```

而是：

\[
\boxed{
\text{MAINLINE V2 的第一个正式建设阶段}
}
\]

---

# 1. 新主线总图

从本轮开始，项目主线冻结为：

\[
\boxed{
\mathcal W
\rightarrow
\mathcal B
\rightarrow
\mathcal D
\rightarrow
G_0
\rightarrow
\xi^{occ}
\rightarrow
\mathcal S
\rightarrow
\mathcal R_{\rm TSS}
\rightarrow
\mathcal O
\rightarrow
G_1?
}
\]

其中：

\[
\mathcal W=\text{World Environment}
\]

\[
\mathcal B=\text{Physical Boundary}
\]

\[
\mathcal D=\text{Thin Typed Transduction}
\]

\[
G_0=\text{既有十神经元基础生成元}
\]

\[
\mathcal S=\text{Scale / Degeneracy Qualification}
\]

\[
\mathcal R_{\rm TSS}=\text{冻结后的关系构造底座}
\]

本轮只建设：

\[
\boxed{\mathcal W+\mathcal B}
\]

不进入后续阶段。

---

# 2. World v2 的正式定义

World 不再等同于：

```text
ThermalFieldGraph
```

也不等同于：

```text
某几个预设热场场景
```

正式定义：

\[
\boxed{
\mathcal W
=
(
X_0,
\Theta_W,
\mathcal E,
\mathcal S_W,
\mathcal C_W,
\mathcal U_{\rm ext},
\mathcal B_W
)
}
\]

其中：

- \(X_0\)：初始环境状态；
- \(\Theta_W\)：环境物理参数；
- \(\mathcal E\)：环境介质／Field；
- \(\mathcal S_W\)：Sources；
- \(\mathcal C_W\)：环境内部耦合；
- \(\mathcal U_{\rm ext}\)：外部驱动历史；
- \(\mathcal B_W\)：对 organism 开放的物理边界。

World 的定位：

> **受真实物理方程约束的条件采样环境池。**

---

# 3. World 不是数据集

禁止将 World v2 实现成：

```text
scene_1
scene_2
scene_3
scene_4
```

然后在若干固定场景之间切换。

每次 World episode 应由：

\[
(X_0,\Theta_W,U_{\rm ext})
\sim
P_W(\cdot|c)
\]

产生。

条件 \(c\) 只允许限制：

```text
物理合法范围
材料范围
源数量范围
源位置范围
初始状态范围
耗散范围
驱动范围
```

不得包含：

```text
必须产生 occurrence
必须让 G0 激活
必须让 TSS 得到 relation
```

---

# 4. World 的两阶段原则

每个 episode 必须严格分为：

## Phase A：条件采样

采样：

\[
X_0,\Theta_W,U_{\rm ext}.
\]

允许随机性存在。

## Phase B：物理演化

一旦 episode 开始：

\[
\dot X_W
=
F_W(X_W,U_{\rm ext};\Theta_W).
\]

不得再因为下游结果动态修改 World 参数。

即：

\[
\boxed{
\text{随机性选择世界，
物理方程决定世界的历史。}
}
\]

---

# 5. 本轮继续使用单一热物理域

W1 不增加：

```text
光
声音
压力
化学
```

等额外感受模态。

继续以现有热物理域作为 World v2 的第一实现。

原因：

当前缺口已经定位为：

```text
局部自由度不足
时间尺度绑定
Source/Drive 历史单一
边界观察结构有限
```

而不是“物理模态数量不够”。

---

# 6. 环境对象继续模块化

不得建立一个包含全部逻辑的：

```text
WorldV2GodObject
```

保持至少以下独立对象：

```text
Source
Field
Coupling
Boundary
Sampler
EpisodeConfig
Ledger
```

推荐逻辑结构：

\[
Source
\rightarrow
Field
\rightarrow
Boundary
\]

其中：

### Source

提供：

```text
energy_remaining
power
position
temporal drive state
```

### Field

负责：

```text
局部状态
扩散
内部传输
环境耗散
```

### Coupling

负责：

```text
Source → Field
Field ↔ Field
Field → Boundary
```

### Boundary

只暴露有限的环境物理量。

---

# 7. 现有组件优先复用

优先复用并审计：

```text
DynamicHeatSource
ThermalFieldGraph
ThermalFieldLocator
ThermalSourceCoupler
ThermalContact
JointThermalStepPlan
```

W1 不因名字旧就重写。

每个组件分别标记：

```text
REUSE_AS_IS
REUSE_WITH_PARAMETER_GENERALIZATION
REFACTOR_REQUIRED
LEGACY_ONLY
```

---

# 8. World v2 第一目标：增加局部自由度

World v1 三节点只能提供非常有限的内部状态空间。

W1 至少测试：

```text
N = 3   legacy control
N = 5
N = 10
N = 20
```

这不是要求最终 World 使用 20 节点。

目的是观察：

\[
N_W\uparrow
\]

以后是否自然增加：

```text
隐藏态数量
局部传播路径
不同历史产生的未来分叉
局部热结构寿命
```

不得用 G0 结果选择 N。

---

# 9. 不用“节点越多越好”作为标准

N 的增加只有在带来新的独立物理状态时才有意义。

测量：

\[
\operatorname{rank}_{eff}(X_W)
\]

或相应有效自由度指标。

如果：

\[
N=20
\]

但状态始终高度共线，

不得写：

```text
World complexity increased 6.7×
```

必须如实登记：

```text
effective DOF remains low
```

---

# 10. 第二目标：解除时间尺度绑定

现有 World 中：

\[
r_{\rm leak}
\]

与：

\[
\kappa
\]

存在固定比例关系。

W1 必须解除。

定义独立参数：

\[
\tau_{\rm diffusion}
\]

和：

\[
\tau_{\rm environment}.
\]

允许至少覆盖：

\[
\tau_{\rm env}
\ll
\tau_{\rm diff}
\]

\[
\tau_{\rm env}
\approx
\tau_{\rm diff}
\]

\[
\tau_{\rm env}
\gg
\tau_{\rm diff}.
\]

不得选择一个“最佳比值”。

World 应保留合法参数域。

---

# 11. 第三目标：丰富 Source 历史

World v2 的复杂性优先来自真实环境对象的历史，而不是人工噪声。

Source 至少允许：

```text
不同位置
不同能量预算
不同功率
不同起始时间
不同持续时间
间歇驱动
多个 Source 共存
Source 耗尽
```

如果实现移动 Source，必须具有明确运动规则，不得直接 teleport 到目标节点。

移动 Source 不是 W1 必须项。

---

# 12. 多 Source 不是多标签

多个热源不能预定义成：

```text
source A = class A
source B = class B
```

World 不产生语义标签。

Source 只具有：

\[
(E,P,x,t,\text{physical parameters}).
\]

内部系统不知道：

```text
source identity
scene identity
condition label
```

---

# 13. 第四目标：建立真实隐藏动力学

World v2 必须能够天然存在：

\[
X_A(t_0)\neq X_B(t_0)
\]

同时：

\[
Y_A(t_0)\approx Y_B(t_0)
\]

但未来：

\[
Y_A(t>t_0)\neq Y_B(t>t_0).
\]

该性质登记为：

```text
WORLD_V2_HIDDEN_DYNAMICS
```

但不得通过人为 hidden variable 实现。

合法来源包括：

```text
不同 Field 内部状态
不同 Source 剩余能量
不同 Source 位置
不同局部传输历史
不同边界条件历史
```

---

# 14. World 的隐藏自由度不是软件秘密变量

禁止：

```text
hidden_memory
history_code
latent_id
future_class
scene_token
```

参与 World 动力学。

Hidden DOF 必须属于：

\[
X_W.
\]

并且具有物理未来效应。

如果删除该状态不影响未来：

它只是 audit metadata，

不是 hidden dynamical state。

---

# 15. World v2 Boundary 正式化

定义：

\[
Y_B(t)=B_W[X_W(t)].
\]

World v2 必须明确：

```text
完整状态 X_W
```

与：

```text
可观测边界 Y_B
```

不是同一东西。

---

# 16. Boundary 至少保留两种实验配置

继续保留：

```text
BOUNDARY_FULL
BOUNDARY_REDUCED
```

### FULL

用于：

```text
物理调试
守恒审计
World 本体资格
```

### REDUCED

用于：

```text
有限观察
隐藏动力学
后续 organism 接口
```

不得隐含切换。

每次实验必须记录：

```text
boundary_config
observable_count
observable_addresses
```

---

# 17. World v2 不固定只观察 node0

`BOUNDARY_REDUCED_N0` 是 World v1 的正对照工具。

World v2 应允许：

\[
B_W^{(k)}
\]

从多个合法物理边界位置采样。

例如：

```text
1-point
2-point
local patch
```

但：

\[
|Y_B|
\ll
|X_W|
\]

应作为有限观察研究的常见配置。

---

# 18. Boundary 不负责事件检测

Boundary 不允许：

```text
threshold
peak detector
event start
event end
relation detection
```

Boundary 只负责：

\[
\text{物理状态交换／观察}.
\]

事件属于后续内部结构。

---

# 19. 本轮不接正式 Transduction v2

W1 的硬红线：

```text
NO T1-B
```

World v2 的正式资格测试只做到：

\[
X_W
\rightarrow
Y_B.
\]

不得因为 Candidate A/B 的工作范围修改：

```text
Source power
κ
r_leak
node count
boundary scale
```

---

# 20. Candidate A/B 只可作为离线观察器

如需诊断：

Candidate A/B 可在研究脚本中离线读取：

\[
Y_B(t)
\]

但：

```text
不得反馈 World
不得参与 World 参数选择
不得作为 W1 PASS 判据
```

它们只能回答：

> “这组 raw boundary 以后有没有可能进入既有接口研究。”

---

# 21. 不接 G0

整个 W1：

```text
G0 = READ_ONLY / DISCONNECTED
```

World v2 是否成功不得由：

```text
occurrence count
collector activation
L1 activation
```

决定。

这是防止新的 World↔G0 共适应。

---

# 22. 不追求混沌

禁止：

```text
ENGINEER_CHAOS
```

不添加混沌项只为了“更真实”。

允许测量：

```text
perturbation growth
trajectory divergence
autocorrelation
state entropy
relaxation spectrum
```

如果自然出现强敏感动力学：

登记。

如果没有：

```text
CHAOS_NOT_REQUIRED
```

---

# 23. 不强求人造噪声

World 可以有噪声。

但必须明确来源：

```text
thermal noise
source fluctuation
boundary fluctuation
```

不得用：

```text
random.normal()
```

单纯把轨迹“弄复杂”。

如果使用 Langevin 类项：

必须单独记录：

\[
\sigma,\ dt,\ seed
\]

以及能量／量纲解释。

---

# 24. World v2 的五类 episode

至少建立五类物理 episode family。

它们不是语义类别，只是实验覆盖族。

### E1 — Single-source relaxation

单源注入→停止→自由衰减。

### E2 — Source-location variation

同源物理参数，不同空间位置。

### E3 — Multi-source interference

多个 Source 同时／错时作用。

### E4 — Timescale contrast

改变扩散／耗散关系。

### E5 — Hidden-history twins

边界当前值近似一致，但内部历史不同。

---

# 25. Episode family 不允许专门调 G0

任何 episode 参数只能来源于：

```text
World legal parameter domain
```

不得因为：

```text
Candidate B 没反应
```

而提高 power。

不得因为：

```text
旧 G0 饱和
```

而降低 Field。

---

# 26. Hidden-history twin 作为核心正对照

World v1 已经有正对照。

World v2 必须建立更一般版本：

给定：

\[
\epsilon_B
\]

寻找：

\[
\|Y_A(t_0)-Y_B(t_0)\|<\epsilon_B
\]

同时：

\[
\|X_A(t_0)-X_B(t_0)\|>\epsilon_X
\]

并在未来窗口：

\[
\max_{\tau>0}
\|Y_A(t_0+\tau)-Y_B(t_0+\tau)\|
>
\epsilon_F.
\]

阈值不能事后为了 PASS 修改。

先根据 World v1 正对照与数值尺度预登记。

---

# 27. 新增 Source-hidden twin

额外构造：

\[
Y_A(t_0)\approx Y_B(t_0)
\]

Field 局部状态也尽量接近，

但：

\[
E_{\rm source,A}
\neq
E_{\rm source,B}.
\]

随后未来：

\[
Y_A^+\neq Y_B^+.
\]

用于证明：

> World hidden dynamics 不只来自 Field 内部节点，也可来自环境对象的未来因果状态。

---

# 28. 建立因果阻断实验

对于每类隐藏状态 \(Z_W\)：

进行：

```text
intact
vs
causal block
```

例如：

```text
Source energy remaining → block future source output
```

如果阻断：

\[
Z_W
\]

后未来边界差异消失，

则登记：

```text
HIDDEN_STATE_CAUSALLY_SUPPORTED
```

否则：

```text
HIDDEN_STATE_CORRELATIONAL_ONLY
```

---

# 29. World 的信息复杂度不以熵单指标定义

可以记录：

\[
H(X_W),
H(Y_B)
\]

或相关统计。

但禁止：

```text
entropy higher = world better
```

World 资格关注：

```text
独立自由度
历史可区分性
有限观察
因果未来作用
物理闭合
```

而不是单一复杂度数。

---

# 30. World v2 必须有完整能量谱系

每一步至少追踪：

\[
E_{\rm source}
\]

\[
E_{\rm field}
\]

\[
E_{\rm boundary}
\]

\[
E_{\rm leak}
\]

以及：

\[
R_E.
\]

内部 Field 转移必须：

\[
\sum_i \Delta E_i^{internal}\approx0.
\]

外部变化必须能归因于：

```text
Source injection
boundary transfer
environment loss
```

---

# 31. 不要求全项目能量闭合

W1 只要求：

```text
WORLD_LOCAL_ENERGY_AUDITABLE
```

不宣称：

```text
GLOBAL_PROJECT_ENERGY_CLOSURE
```

因为 G0、TSS 等尚未回接。

---

# 32. 数值稳定性必须独立资格化

每个参数域检测：

\[
\eta_{\rm diffusion}
\]

及对应数值稳定条件。

必须区分：

```text
physical instability
numerical instability
```

禁止把数值爆炸当作复杂动力学。

---

# 33. dt 收敛实验

选至少三档：

\[
dt,\quad dt/10,\quad dt/100.
\]

保持相同物理时长：

\[
T_{\rm physical}.
\]

比较：

```text
boundary trajectory
total energy
hidden-state divergence
relaxation constants
```

禁止再次出现：

```text
步数与 dt 同时缩放导致物理时长变化
```

---

# 34. World 的参数域不寻找最佳点

参数扫描目的：

```text
寻找合法域
寻找失稳域
寻找退化域
寻找边界案例
```

禁止：

```text
score → grid search → best configuration
```

最终保留一个：

\[
\Theta_W^{legal}
\]

区域。

---

# 35. 极端边界原则

继续采用：

> 不只看平均，也保留最低和最高表现。

对于每个参数维度保存：

```text
最弱有效耦合
最强有效耦合
最快时间尺度
最慢时间尺度
最小隐藏分叉
最大隐藏分叉
最大能量残差
```

不得只报告 mean/std。

---

# 36. World v2 不需要“成功事件”

World 可以产生一段 organism 看起来几乎没有变化的物理历史。

这仍然是合法 World。

即：

\[
\boxed{
\text{World validity}
\neq
\text{internal detectability}
}
\]

后者属于 T1-B/G0。

---

# 37. 新 World API 候选

建议研究层先建立：

```text
WorldEpisodeSpec
WorldEpisode
WorldSampler
BoundaryView
WorldFrame
WorldLedger
```

其中：

```text
WorldEpisodeSpec
```

只描述初始条件和物理参数。

```text
WorldEpisode
```

运行真实动力学。

```text
BoundaryView
```

只能读取批准的 \(Y_B\)。

---

# 38. 不得让 BoundaryView 读取隐藏状态

结构上强制：

```text
BoundaryView
```

不能持有：

```text
graph.cells
source objects
episode internals
```

最好只接收 World 暴露的：

```text
boundary_frame
```

以减少未来软件侧信道。

---

# 39. Boundary replay 必须继续成立

对每类 World v2 episode：

记录：

\[
Y_B(0:T).
\]

然后完全删除 World，

只保存 boundary trace。

未来 T1-B 必须能够：

\[
Replay[Y_B]
\]

得到相同的下游输入。

本轮只验证：

```text
boundary recording deterministic
boundary data self-contained
```

---

# 40. World v2 最重要的负控制

必须至少有：

### NC1 — No Source

确认无外部注入时只剩自由耗散。

### NC2 — Disconnected Source

Source 存在但 coupling=0。

### NC3 — No Field Coupling

节点彼此不交换。

### NC4 — Full Boundary

全部状态可见。

此时：

```text
hidden dynamics due to partial observation
```

应显著下降或消失。

### NC5 — Reduced Boundary

恢复隐藏动力学。

---

# 41. Full vs Reduced 是关键因果对照

同一个 World episode：

\[
X_W(t)
\]

分别产生：

\[
Y_{\rm full}
\]

和：

\[
Y_{\rm reduced}.
\]

如果只有 Reduced 表现出：

```text
same-current / different-future
```

而 Full 能区分当前状态，

则说明隐藏动力学确实来自：

\[
\boxed{\text{partial observation}}
\]

而不是 World 算法本身的随机黑箱。

---

# 42. Source / Field / Boundary 必须可独立替换

W1 完成后应该能够：

```text
same Field + different Source
same Source + different Field parameters
same World + different Boundary
```

而不修改其他模块。

这是防止 World 内部再次形成不可拆解“共谋”的基本要求。

---

# 43. 不重新引入语义

禁止变量：

```text
dangerous_source
rewarding_temperature
target_region
important_node
stimulus_class
```

这类语义进入动力学。

允许：

```text
source_0
node_4
boundary_patch_2
```

纯物理地址。

---

# 44. 物理地址要保留

每个对象具有稳定物理地址：

```text
world_id
episode_id
source_id
field_node_id
boundary_id
```

这些只做：

```text
lineage
audit
replay
```

不得参与动力学判定。

---

# 45. World v2 第一轮不做空间生成理论

虽然 World 有空间地址，

但本轮不建立：

```text
spatial generator
space relation
geometry semantics
```

位置只是环境物理计算所需变量。

空间生成留到以后。

---

# 46. W1 不碰 NaturalUnit 最终定义

本轮不讨论：

```text
natural unit
new generator
organization
```

World 是上游环境。

它不是生成元。

---

# 47. W1 的资格门

最终至少设置六门。

## W1-M1：Physical closure

物理演化／能量账本自洽。

## W1-M2：Independent DOF

存在多个真正独立的动态自由度。

## W1-M3：Independent timescales

扩散与耗散不再固定绑定。

## W1-M4：Conditional sampling

多个 episode 能从合法参数域自动采样产生。

## W1-M5：Partial observability

Full 与 Reduced boundary 有明确区别。

## W1-M6：Hidden causal dynamics

存在：

\[
X_A\neq X_B,\quad
Y_A\approx Y_B,\quad
Y_A^+\neq Y_B^+.
\]

并能通过因果阻断证明差异来源。

---

# 48. W1 不设置“复杂度 PASS”

禁止：

```text
WORLD_COMPLEXITY > threshold
```

作为门。

也禁止：

```text
chaos = PASS
```

六门全部是结构／物理资格。

---

# 49. World v2 的最终状态只能有三种

### A

```text
WORLD_V2_RAW_QUALIFIED
```

表示可以进入 T1-B。

### B

```text
WORLD_V2_PHYSICAL_SUPPORT_FAIL
```

物理／能量／数值支撑存在问题。

### C

```text
WORLD_V2_PARTIAL_OBSERVABILITY_NOT_ESTABLISHED
```

环境能跑，但无法产生需要的有限观察隐藏动力学。

---

# 50. W1 通过后不再继续扩 World

如果：

```text
WORLD_V2_RAW_QUALIFIED
```

立即停止 W1。

禁止继续：

```text
增加节点
增加 Source 类型
增加混沌
增加物理模态
```

只因为“还能更真实”。

World v2 不是模拟宇宙项目。

---

# 51. W1 完成后的下一步

只有 W1 冻结：

```text
WORLD_V2_RAW_QUALIFIED
```

以后，正式进入：

\[
\boxed{T1\text{-B}}
\]

T1-B 使用：

```text
World v1 reference
World v2 calibration ensemble
World v2 held-out ensemble
```

完成 Transduction v2 的最终选择和参数标定。

---

# 52. T1-B 前不修改 G0

即使 W1 发现：

```text
boundary amplitude too large
boundary dynamics too slow
```

也不得直接修 G0。

这些首先属于：

```text
T1-B typed interface
```

问题。

---

# 53. 已登记的 G0 债务暂缓

保持：

```text
G0_PORT_CONTRACT_CHANGE_REQUIRED
```

不在 W1 修。

同时保持：

```text
LAYER_CATEGORY_CONFLICT
```

不在 W1 修。

它们的解决点是：

```text
T1-B → G0 reconnect
```

---

# 54. W1 后面的主线不再变化

如果 W1/T1-B/G0 回接完成：

正式恢复：

\[
G_0
\rightarrow
\xi^{occ}.
\]

然后下一大阶段：

\[
\boxed{SCALE\text{-}0}
\]

研究：

```text
多个 G0
微观轨迹分散
宏观边界
简并
规模等价
```

之后才重新接：

\[
\mathcal R_{\rm TSS}.
\]

---

# 55. 本轮代码范围

建议新增：

```text
research/world_v2/
```

允许：

```text
research/world_v2/models/
research/world_v2/episodes/
research/world_v2/qualification/
research/world_v2/data/
```

Production world 先保持不改。

待 W1 qualification 完成后再决定是否迁入：

```text
nexus_v1/components/
```

---

# 56. 第一批实验文件

至少实现：

```text
w1_episode_sampler.py
w1_field_dof_scan.py
w1_timescale_scan.py
w1_hidden_twin.py
w1_source_hidden_twin.py
w1_boundary_full_vs_reduced.py
w1_energy_ledger.py
w1_dt_convergence.py
w1_final_qualification.py
```

---

# 57. 数据必须原始保存

至少输出：

```text
episode_manifest.csv
world_parameters.csv
boundary_trajectories.csv
hidden_twin_pairs.csv
timescale_scan.csv
energy_ledger.csv
dt_convergence.csv
qualification_summary.json
```

每个 episode 保存：

```text
seed
initial state
source parameters
field parameters
boundary configuration
dt
physical duration
```

---

# 58. 正结果和负结果同等保存

例如：

```text
某参数域隐藏分叉不存在
某 Source 组合被快速耗散
高 N 仍有效自由度低
某时间尺度组合数值不稳定
```

均必须进入：

```text
W1_NEGATIVE_RESULTS.md
```

不得只留下成功 World。

---

# 59. 最终交付物

建议收口为五份文档：

```text
MAINLINE_V2_WORLD_CONTRACT.md
W1_WORLD_V2_IMPLEMENTATION_REPORT.md
W1_HIDDEN_DYNAMICS_REPORT.md
W1_PHYSICAL_AND_NUMERICAL_AUDIT.md
W1_FINAL_RULING.md
```

另附：

```text
W1_NEGATIVE_RESULTS.md
```

和完整数据目录。

---

# 60. W1_FINAL_RULING 首屏必须回答

1. World v2 的完整状态是什么？
2. 哪些参数是 episode 条件采样变量？
3. 哪些变量是真动态状态？
4. Source 与 Field 如何交换能量？
5. World 有多少有效自由度？
6. 有哪些独立时间尺度？
7. Full / Reduced Boundary 分别暴露什么？
8. hidden dynamics 是否成立？
9. hidden state 是否具有因果未来作用？
10. 能量与数值闭合状态如何？
11. 是否达到：

```text
WORLD_V2_RAW_QUALIFIED
```

12. 是否允许进入：

```text
T1-B
```

---

# 61. 最重要的禁止事项

W1 绝对禁止出现以下逻辑：

```text
if G0 fails:
    modify World
```

禁止：

```text
if transduction saturates:
    lower World amplitude
```

禁止：

```text
if relation not formed:
    lengthen source interval
```

禁止：

```text
find parameters that maximize downstream success
```

---

# 62. 本阶段方法论

World 不负责：

```text
提供干净标签
制造 occurrence
制造 relation
模拟完整真实宇宙
```

World 只负责：

\[
\boxed{
\text{产生真实、连续、物理自洽、有限可观测的环境历史。}
}
\]

它允许被简化。

但简化必须显式。

它不需要人工制造混沌。

但它必须具有：

\[
\boxed{
\text{内部不可见、未来仍有效的真实动力学自由度。}
}
\]

---

# 63. 主线重新启动的正式标志

如果本轮开始执行：

```text
research/world_v2/
```

则项目阶段正式登记为：

```text
MAINLINE_V2_STARTED = TRUE
```

从这里开始：

> 所有新的研究任务必须明确指出它属于主线中的哪个节点。

不得再默认开启新的平行理论树。

---

# 64. 最终执行顺序

严格执行：

\[
\boxed{
W1\ World\ v2
}
\]

通过后：

\[
\boxed{
T1\text{-B}\ Transduction\ v2
}
\]

然后：

\[
\boxed{
G0\ reconnect
}
\]

然后：

\[
\boxed{
Occurrence\ revalidation
}
\]

然后：

\[
\boxed{
SCALE\text{-}0
}
\]

然后：

\[
\boxed{
TSS\ Relation\ reconnect
}
\]

再以后才重新讨论：

```text
更高生成
P/R
Xin
Shadow
TOPRXin
```

---

# 65. 本轮一句话目标

\[
\boxed{
\text{不是做一个更复杂的 World，
而是建立一个不需要迎合内部系统、
却足以提供真实隐藏动力学的物理环境。}
}
\]