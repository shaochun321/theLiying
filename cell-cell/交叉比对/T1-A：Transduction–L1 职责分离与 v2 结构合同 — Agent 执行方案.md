# T1-A：Transduction–L1 职责分离与 v2 结构合同
## Agent 执行方案

### 0. 本轮定位

当前冻结顺序：

\[
\boxed{
WT0
\rightarrow
T1\text{-A}
\rightarrow
W1
\rightarrow
T1\text{-B}
\rightarrow
G0
}
\]

WT0 已完成接口资格审计，但终裁不是 `WT0_PASS`，而是：

```text
WT0_TRANSDUCTION_CONTRACT_UNRESOLVED
```

阻塞原因：

```text
TRANSDUCTION_ROLE = OVERLAPPING_UNRESOLVED
```

现状证据：

```text
Y_B
  ↓
legacy D_i = affine + clip
  ↓
u_i
  ↓
BaseGenerator.feed_from_skin()
  ↓
dT_raw
  ↓
L1 ThermalDeltaNeuron
```

其中：

- `D_i` 名义上只是单位／尺度转换；
- 实际却执行幅值窗选择、死区事件预筛、饱和压缩和动态范围选择；
- L1 `ThermalDeltaNeuron` 又承担热刺激的动态换能；
- `u_i` 当前按 `dT_raw` 速率语义进入 L1，而上游 legacy `D_i` 输入本质是温度幅值。

因此本轮不首先设计“新函数”。

本轮首先回答：

\[
\boxed{
\mathcal D_i\text{ 应在哪里结束，L1 应在哪里开始？}
}
\]

---

# 1. 本轮硬范围

本轮只允许修改／新增：

```text
research/transduction_v2/
research/transduction_requalification/
文档
测量脚本
诊断原型
```

以下保持只读：

```text
nexus_v1/
tss/
BaseGenerator
OccurrenceClosure
ThermalDeltaNeuron production implementation
World v1
WT0 frozen tests
```

除非为了读取和诊断，不得改母体。

禁止本轮：

```text
实现 production Transduction v2
建设 World v2
修改 G0
修改 L1
修改 TSS
重新标定最终 κ/b/clip
根据 occurrence 数量调参
启动 W1
启动 T1-B
```

---

# 2. 必须继承的 WT0 冻结事实

T1-A 不得重新争论以下结论。

## 2.1 三对象合同

保持：

\[
X_W(t)
\rightarrow
Y_B(t)
\rightarrow
u_i(t).
\]

其中：

- \(X_W\)：完整 World 状态；
- \(Y_B=B_W[X_W]\)：唯一允许跨环境边界传递的物理量；
- \(u_i=\mathcal D_i[Y_B]\)：进入 G0 的输入端口量。

禁止：

```text
G0 → X_W
D_i → X_W hidden state
```

---

## 2.2 Boundary Replay

冻结：

```text
HIDDEN_SIDE_CHANNEL = PASS
```

任何 T1-A diagnostic candidate 必须仍能通过：

```text
record Y_B
→ delete World
→ replay Y_B
→ downstream result identical
```

不得引入 World object reference、未来访问、global step 等隐藏通道。

---

## 2.3 World hidden dynamics

冻结：

```text
WORLD_HIDDEN_DYNAMICS_POSITIVE_CONTROL = ESTABLISHED
```

该现象属于 World 层。

禁止在 T1-A 中将其重新实现为：

```text
H_tau
额外 memory variable
软件 history cache
```

---

## 2.4 legacy 转导负结果

以下四项必须成为永久 regression：

```text
L1. 双侧资格窗过窄
L2. u_interior 合同未兑现
L3. baseline-zeroing amplification artifact
L4. downstream dynamic-range under-utilization
```

另加 WT0：

```text
L5. 顶棚饱和抹平大幅剂量差
L6. 纯时序历史可以被完全湮灭
L7. CO_ADAPTATION_RISK = HIGH
L8. D_i 与 L1 职责重叠
```

---

# 3. T1-A 第一任务：完整端口语义审计

建立：

```text
T1A_PORT_SEMANTICS_AUDIT.md
```

沿完整路径逐级追踪：

```text
World field
→ physical boundary
→ skin/contact
→ D_i input
→ D_i output
→ BaseGenerator.feed_from_skin()
→ internal propagate
→ L1 ThermalDeltaNeuron
→ collector
→ occurrence
```

对每一个变量记录：

```text
变量名
代码位置
物理意义
数学意义
单位
是否有状态
是否做滤波
是否做微分
是否做阈值
是否做 clip
是否做事件选择
上游
下游
```

不得只看变量名称判断含义。

特别核实：

```text
q_skin
temperature
delta_temperature
dT_raw
u_i
activation
pre_trace
```

---

# 4. 必须完成量纲追踪

为当前生产路径写出：

\[
[Y_B]=?
\]

\[
[\mathcal D_i(Y_B)]=?
\]

\[
[u_i]=?
\]

\[
[dT_{\rm raw}]=?
\]

\[
[L1\ input]=?
\]

禁止：

```text
“normalized，所以无所谓单位”
```

作为答案。

如果 normalized 模式导致实际单位被缩放，必须登记：

\[
u_{\rm physical}
\overset{S}{\longrightarrow}
u_{\rm normalized}.
\]

并明确 \(S\) 的角色。

---

# 5. 核心审计：幅值与速率是否错位

必须形成两个明确定义：

### 幅值端口

\[
U_T:
\quad
T-T_{\rm ref}
\]

或相应带单位局部热状态。

### 速率端口

\[
U_{\dot T}:
\quad
\frac{dT}{dt}.
\]

然后核查当前路径到底属于哪一个。

如果 legacy D：

\[
T
\rightarrow
aT+b
\]

却进入：

```text
dT_raw
```

则正式登记：

```text
PORT_SEMANTIC_MISMATCH = CONFIRMED
```

否则必须提供代码和量纲证据反证。

---

# 6. 第二任务：职责矩阵

建立：

```text
T1A_RESPONSIBILITY_MATRIX.md
```

至少比较四层：

| 功能 | Boundary/contact | D_i | L1 | OccurrenceClosure |
|---|---|---|---|---|
| 接触物理 | ? | ? | ? | ? |
| 单位转换 | ? | ? | ? | ? |
| 尺度映射 | ? | ? | ? | ? |
| 温度→电信号换能 | ? | ? | ? | ? |
| 时间微分/速率提取 | ? | ? | ? | ? |
| 动态适应 | ? | ? | ? | ? |
| 半波整流 | ? | ? | ? | ? |
| 饱和 | ? | ? | ? | ? |
| 事件阈值 | ? | ? | ? | ? |
| trigger | ? | ? | ? | ? |
| exit | ? | ? | ? | ? |
| rearm | ? | ? | ? | ? |

目标不是让所有格子都有东西。

目标是让每项职责只有一个明确归属。

---

# 7. 默认职责假设

以下仅作为待验证设计假设，不可直接宣布冻结：

### Boundary/contact

负责：

```text
World ↔ organism 的真实物理交换
```

---

### D_i

优先考虑只负责：

```text
物理端口转换
单位转换
必要尺度转换
接触结构要求的静态转换
```

即：

\[
\boxed{
D_i\text{ 尽可能薄}
}
\]

---

### L1

负责真正的动态热换能，例如：

```text
phasic response
rate sensitivity
physical adaptation
half-wave physical response
```

但只有现有 `ThermalDeltaNeuron` 的代码和 Q1 证据支持时才保留。

---

### OccurrenceClosure

继续独占：

```text
trigger
exit
rearm
occurrence counting
```

D_i 不得预先通过 dead zone 决定事件是否存在。

---

# 8. T1-A 第三任务：L1 身份审查

不要默认现有 L1 一定正确。

建立：

```text
T1A_L1_IDENTITY_AUDIT.md
```

核实：

1. `ThermalDeltaNeuron` 当前方程；
2. 输入实际上是什么；
3. 是否真正有内部时间状态；
4. 是否真的实现 \(dT/dt\)；
5. 还是只把外部传入的所谓 `dT` 做：

\[
\max(0,k\,dT)
\]

这样的瞬时半波；
6. adaptation 是否真实存在；
7. 哪些功能只是 docstring 声称，而代码没有。

必须区分：

```text
BIO analogy
SEMI implementation
actual runtime behavior
```

三层。

---

# 9. Q1 文献审计

T1-A 必须完成热感受器／温度感受换能 Q1 文献卡。

目的不是寻找一个“像 sigmoid 的生物公式”。

而是回答：

> 真实热感受系统中，幅值、变化率、适应、饱和分别可能由哪些物理／生理层承担？

输出：

```text
T1A_THERMORECEPTOR_Q1_REVIEW.md
```

每条候选机制必须注明：

```text
物理/生理对象
输入
输出
状态变量
时间尺度
是否动态
是否饱和
是否适应
是否适合当前项目分辨率
不能解决什么
```

禁止根据文献名称直接照搬整套生物系统。

---

# 10. 第四任务：建立候选架构族

本轮只建立架构候选，不冻结最终参数。

至少比较以下三类。

---

## Candidate A：Thin-Amplitude Port

\[
Y_B
\rightarrow
S(Y_B-Y_{\rm ref})
\rightarrow
L1.
\]

其中 D_i 只做：

```text
reference
units
scale
```

不做：

```text
clip
dead zone
dynamic adaptation
event filtering
```

若 L1 最终需要速率，则必须由 L1 自己形成。

---

## Candidate B：Explicit Rate Port

若代码／物理证据证明 L1 的合法输入就是：

\[
dT/dt,
\]

则建立显式速率端口候选：

\[
Y_B
\rightarrow
\mathcal P_{\dot T}
\rightarrow
U_{\dot T}
\rightarrow
L1.
\]

但必须回答：

> \(\mathcal P_{\dot T}\) 由谁承担？

若需要历史状态做差分：

\[
\frac{T_t-T_{t-\Delta t}}{\Delta t},
\]

不得偷偷藏在无状态 `transduce()` 名下。

必须有明确物理／结构身份。

---

## Candidate C：Physical Sensor State

仅当 Q1 与项目结构确实需要时，允许候选：

\[
Y_B
\rightarrow
X_D
\rightarrow
u_i
\]

其中：

\[
\dot X_D=F_D(X_D,Y_B).
\]

这是真正动态转导器。

但必须证明它没有重复 L1。

否则：

```text
CANDIDATE_C = REJECT_DUPLICATION
```

---

# 11. 禁止默认采用压缩函数

以下函数：

```text
sigmoid
tanh
log
softsign
Hill
Naka-Rushton
```

不得因为“动态范围好”直接进入方案。

只有当：

```text
Q1 对应
物理变量
单位
机制
参数来源
```

完整时，才允许作为 candidate。

否则只作为：

```text
MATHEMATICAL_CONTROL
```

用于对照，不得成为项目结构。

---

# 12. 第五任务：诊断原型

允许在：

```text
research/transduction_v2/prototypes/
```

实现候选。

但必须保证：

```text
不修改 production
不被 nexus import
不被 tss import
```

候选只消费冻结好的：

\[
Y_B(t)
\]

轨迹。

优先使用 WT0 已记录／可复现的 boundary trajectories。

---

# 13. Diagnostic Replay 套件

每个 candidate 必须吃完全相同的边界轨迹。

至少包含：

### R1 静息附近小偏离

检查：

```text
是否全部地板化
```

---

### R2 缓慢升温

检查幅值与速率是否被混淆。

---

### R3 快速升温

检查真正速率敏感性。

---

### R4 同峰值、不同上升速度

构造：

\[
T_{\max,A}=T_{\max,B}
\]

但：

\[
\dot T_A\neq\dot T_B.
\]

这是区分：

```text
amplitude-sensitive
vs
rate-sensitive
```

的核心测试。

---

### R5 同当前值、不同过去历史

使用 WT0 hidden-world positive control。

检查 candidate 本身是否添加了不必要历史。

---

### R6 大幅输入

攻击：

```text
ceiling collapse
```

---

### R7 弱输入

攻击：

```text
floor collapse
```

---

### R8 脉冲 vs 持续

检查时序结构是否被保留。

---

# 14. 不允许用 occurrence 作为 T1-A 主指标

本轮主测到 L1 输入／输出为止。

G0 occurrence 最多作为：

```text
secondary diagnostic
```

不得用于候选排序。

禁止：

```text
哪个 candidate occurrence 最多
→ 哪个最好
```

---

# 15. 新测量合同

所有 candidate 必须同时报告：

\[
D_{\rm boundary}^{abs}
\]

\[
D_{\rm port}^{abs}
\]

\[
D_{\rm L1}^{abs}
\]

以及相应 normalized 指标。

任何 ratio 都必须同时提供分子和分母。

同时记录：

```text
zero occupancy
saturation occupancy
interior occupancy
sign preservation
timing preservation
peak timing
rise-time sensitivity
decay sensitivity
```

---

# 16. 防止 baseline-zeroing 假放大

如果：

\[
D_{\rm port}^{norm}>D_{\rm boundary}^{norm}
\]

不得写：

```text
information amplified
```

必须检查：

\[
D_{\rm boundary}^{abs}
\]

与：

\[
D_{\rm port}^{abs}.
\]

如果 normalized 上升只是由于共同 baseline 被抹掉：

```text
BASELINE_ZEROING_ARTIFACT = TRUE
```

---

# 17. 不预设“最佳保留率”

T1-A 不规定：

```text
retention = 1 最好
```

也不规定：

```text
越高越好
```

因为转导允许合法简并。

本轮只回答：

> 差异为什么被保留／削弱／删除？

而不是给候选打单一总分。

---

# 18. 极端案例必须保存

每个 candidate 必须报告：

```text
最大保留案例
最大丢失案例
最大假放大案例
最严重地板案例
最严重饱和案例
最明显时序丢失案例
```

不得只报告平均。

---

# 19. 参数纪律

T1-A candidate 可以有参数。

但参数只能用于：

```text
机制扫描
量纲检查
稳定性分析
```

不得根据 World v1 找最佳点。

禁止：

```text
grid search → maximize score → freeze parameter
```

本轮只能冻结：

```text
parameter role
legal domain
physical meaning
```

不能冻结：

```text
final value
```

---

# 20. 与 World v1 的关系

World v1 本轮只是：

```text
diagnostic stimulus generator
```

不是：

```text
Transduction v2 calibration set
```

任何 candidate 在 World v1 表现漂亮都不能获得最终资格。

最终标定属于：

\[
T1\text{-B}.
\]

---

# 21. T1-A 的核心决策门

最终必须在以下结构决策中给出明确结果。

## Gate A：D_i 是否应该是无状态薄接口？

```text
YES / NO / UNRESOLVED
```

---

## Gate B：L1 是否应该承担速率提取？

```text
YES / NO / UNRESOLVED
```

---

## Gate C：现有 ThermalDeltaNeuron 是否已经真正实现该职责？

```text
YES / PARTIAL / NO
```

---

## Gate D：是否需要独立动态传感器状态 X_D？

```text
REQUIRED / NOT_REQUIRED / UNRESOLVED
```

---

## Gate E：当前 G0 端口是否必须在后续改名／改语义？

```text
PORT_CHANGE_REQUIRED
PORT_CHANGE_NOT_REQUIRED
UNRESOLVED
```

本轮不执行改动。

---

# 22. 允许出现“需要修改 G0 接口”的结论

G0 本轮 READ_ONLY 不表示：

```text
G0 当前接口永远正确
```

如果严格审计证明：

```text
feed_from_skin()
dT_raw
ThermalDeltaNeuron
```

之间存在无法仅通过 D_i 修复的语义冲突，

允许 T1-A 输出：

```text
G0_PORT_CONTRACT_CHANGE_REQUIRED
```

但：

```text
不在本轮改代码
```

留到 T1-B/G0 回接阶段处理。

---

# 23. 防止将错误修到转导层

如果真正的问题是：

```text
L1 接口定义错误
```

禁止通过设计一个复杂 D_i 来伪造正确输入。

例如：

```text
错误 L1 需要 rate
→ D_i 人工生成 rate
→ 看起来系统恢复工作
```

不能自动视为正确。

必须先判：

> rate extraction 在项目物理结构上究竟属于 D 还是 L1？

---

# 24. T1-A 必须保留两个对照

### Negative control

legacy：

\[
affine+clip.
\]

---

### Mathematical control

允许一个明显标注的非物理宽动态范围函数，仅作为：

```text
“如果只追求数值表现，能达到什么”
```

的控制组。

不得升级为项目 candidate。

用途是防止：

> 因为物理 candidate 数值不够漂亮，就误以为结构失败。

---

# 25. 结果不得使用综合评分

禁止：

```text
Candidate A = 8.7
Candidate B = 6.4
```

也禁止：

```text
WINNER
```

必须用资格门分别表达：

```text
port semantics
dimensional consistency
role separation
causal purity
dynamic duplication
floor behavior
ceiling behavior
timing behavior
physical support
```

---

# 26. T1-A PASS 条件

只有同时满足以下条件：

1. D_i / L1 / OccurrenceClosure 职责无重叠；
2. 幅值／速率端口语义明确；
3. 每个端口量纲可追踪；
4. 候选架构至少存在一个结构上自洽方案；
5. candidate 不依赖 World hidden state；
6. replay 仍可成立；
7. 不依赖 legacy floor/ceiling 事件预筛；
8. 不通过 occurrence 数量调参；
9. 未冻结 World-v1 专用参数；
10. 若 G0 端口必须改，已明确登记而非绕开。

则：

```text
T1A_ARCHITECTURE_READY
```

---

# 27. T1-A 不通过的三种状态

### A

```text
T1A_ROLE_UNRESOLVED
```

D_i / L1 职责仍无法分离。

---

### B

```text
T1A_PORT_SEMANTICS_UNRESOLVED
```

幅值／速率及量纲仍对不上。

---

### C

```text
T1A_G0_INTERFACE_CONFLICT
```

证明真正问题在 G0/L1 接口，无法只通过 Transduction v2 合法解决。

这不是失败。

它是正确定位问题。

---

# 28. T1-A 交付物

必须交：

```text
T1A_PORT_SEMANTICS_AUDIT.md
T1A_RESPONSIBILITY_MATRIX.md
T1A_L1_IDENTITY_AUDIT.md
T1A_THERMORECEPTOR_Q1_REVIEW.md
T1A_CANDIDATE_ARCHITECTURES.md
T1A_METRIC_CONTRACT.md
T1A_DIAGNOSTIC_REPORT.md
T1A_FINAL_RULING.md
```

原始数据：

```text
research/transduction_v2/data/
```

至少包括：

```text
candidate_response.csv
extreme_cases.csv
port_semantics.csv
diagnostic_replay.json
legacy_regression.json
```

---

# 29. 必须复现的冻结回归

运行：

```text
WT0 hidden-world positive control
WT0 boundary replay
WT0 dose attack
WT0 cross-pair
test_regression
tss version_pairing
tss fast
```

T1-A 不得破坏任何已有结果。

---

# 30. 最终报告必须明确回答的九个问题

最终 `T1A_FINAL_RULING.md` 首屏直接回答：

1. 当前 D_i 真正承担了哪些职责？
2. 当前 L1 真正承担了哪些职责？
3. 两者在哪里重复？
4. 当前 \(u_i\) 到底是幅值还是速率？
5. 当前端口是否量纲一致？
6. Transduction v2 应是无状态还是有状态？
7. 速率提取应该属于 D_i 还是 L1？
8. G0 端口合同是否必须修改？
9. 是否满足：

```text
T1A_ARCHITECTURE_READY
```

---

# 31. T1-A 后的执行顺序

如果：

```text
T1A_ARCHITECTURE_READY
```

则下一轮：

\[
\boxed{W1}
\]

开始建设 World v2。

此时仍不做 Transduction v2 最终参数标定。

W1 冻结后：

\[
\boxed{T1\text{-B}}
\]

使用：

```text
World v1 reference
World v2 calibration ensemble
World v2 held-out ensemble
```

共同完成最终转导标定。

最后才回：

\[
\boxed{G0}.
\]

---

# 32. 本轮最重要的红线

不要把：

\[
\boxed{\text{“旧转导不好”}}
\]

理解成：

\[
\boxed{\text{“需要更复杂的转导”}}.
\]

当前证据反而优先支持另一种可能：

\[
\boxed{
\text{旧转导承担得太多，
Transduction v2 可能应该更薄。}
}
\]

只有 T1-A 的物理／代码审计证明必须增加新的独立动态状态时，才允许让它变复杂。

---

# 33. 研究原则

本轮最终目标不是产生一个表现更好的函数。

而是建立：

\[
\boxed{
World
\rightarrow
Boundary
\rightarrow
Transduction
\rightarrow
L1
\rightarrow
Occurrence
}
\]

之间真正有类型、有量纲、有物理职责边界的链路。

每一级只做自己应该做的事。

只有做到这一点，下一阶段 World v2 扩展出来的新自由度才不会再次被一个设计含义混乱的转导接口提前加工掉。