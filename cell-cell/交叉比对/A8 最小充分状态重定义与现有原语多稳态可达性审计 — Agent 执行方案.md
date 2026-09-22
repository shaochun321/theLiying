# A8 最小充分状态重定义与现有原语多稳态可达性审计
## Agent 执行任务书

### 一、任务定位

本轮暂停继续构造新的 \(Z\) 候选。

不再尝试：

```text
新 RC
新 Memristor 拓扑
第三层递归
更多参数扫描来“撞”出 A8
```

本轮只解决两个基础问题：

1. **重新精确定义 A8 的“父层不可重构”到底意味着什么。**
2. **数学审计现有物理原语及其最小反馈组合是否真的可能产生多个稳定/亚稳定物理状态。**

本轮结束前不得宣布：

```text
new generator
organization generator
A8 MET
现有原语不可能实现 A8
```

---

# 二、当前冻结结果

必须保持以下状态不变：

```text
C1 engineering recursion = PASS
A8 = NOT_MET
A9 static lineage = PASS
A9 runtime lineage = GAP
generator qualification = NOT_QUALIFIED
K-06 = BLOCKED / R-E0-3 RULING_REQUIRED
```

上一轮研究候选：

```text
ZLinearRC       → reconstructible
ZSaturating     → reconstructible
ZMemristive     → Z1 reached, Z2 NOT_MET
```

其中 ZMemristive 不得复活为 A8 候选。

已有负结果作为本轮约束资产保存。

---

# 三、首先修正 A8 的逻辑问题

## 3.1 禁止把“确定性可模拟”当成 A8 失败

旧式强重构如果允许同时知道：

\[
x(0)
\]

完整输入历史：

\[
u(0:t)
\]

以及候选自身动力学：

\[
\dot x=f(x,u)
\]

那么对于确定性系统：

\[
x(t)=\Phi_t(x_0,u_{0:t})
\]

原则上当然可以重放。

这证明的是：

```text
系统是确定性的 / 模型可复现
```

不能直接证明：

```text
候选没有新的状态自由度
```

因此本轮不得使用：

> “已知完整历史和初值可以计算候选”

作为单独的 A8 反资格判据。

---

# 四、A8 建议重定义

把当前：

> 父层同类不可重构

进一步形式化为：

> **父层当前最小充分状态不足以闭合候选及其未来动力学。**

定义：

\[
P_t
\]

为父层已经取得资格、且在时刻 \(t\) 足以表示父层未来动力学的最小状态集合。

例如可能包含：

```text
当前 H_tau 物理状态
当前合法 parent relation-event 状态
当前 Theta/gate 必要物理状态
其它已经资格化且真实存在的父层状态
```

候选增加：

\[
Z_t
\]

若存在父层允许的瞬时状态映射：

\[
Z_t=F(P_t)
\]

则候选没有证明新增独立自由度。

但如果可以构造两个系统：

\[
P_t^{(A)}=P_t^{(B)}
\]

同时：

\[
Z_t^{(A)}\neq Z_t^{(B)}
\]

随后施加完全相同未来输入：

\[
u_{t:t+T}^{(A)}
=
u_{t:t+T}^{(B)}
\]

并产生：

\[
Future_A\neq Future_B
\]

则说明：

\[
P_t
\]

不足以闭合未来动力学。

必须扩展状态：

\[
S_t=(P_t,Z_t)
\]

才能闭合。

这才进入：

```text
A8_CANDIDATE
```

而不是直接 A8 MET。

---

# 五、明确区分两种“重构”

以后所有报告必须分开：

## Reconstruction-R1：历史重放

允许：

```text
完整 formation history
完整 candidate equations
candidate initial state
完整输入轨迹
```

回答：

> 知道过去以后能否模拟候选？

该测试只证明 reproducibility。

不得作为 A8 核心资格。

---

## Reconstruction-R2：父层状态闭合

只允许使用时刻：

\[
t_0
\]

父层已经资格化的当前充分状态：

\[
P_{t_0}
\]

以及之后相同的未来输入。

不得给重构器：

```text
候选内部 Z 状态
candidate hidden initial state
用于区别 A/B 的 formation label
Python instance identity
更早且已不属于父层当前状态的完整历史
```

核心问题：

\[
P_{t_0}
\]

是否已经足以预测未来。

这才是 A8 的主要反资格攻击。

---

# 六、新的 A8 双胞胎实验规范

设计：

```text
EXP-A8-SUFF-01
```

## Phase A：不同形成历史

系统 A：

\[
History_A
\]

系统 B：

\[
History_B
\]

要求尝试把候选推向不同内部物理状态：

\[
Z_A\neq Z_B
\]

---

## Phase B：父层状态对齐

不是单纯“等固定 20000 步”。

Agent 必须实际测量并证明：

\[
P_A(t_0)\approx P_B(t_0)
\]

分别报告所有父层状态分量差异。

例如：

```text
H_tau difference
gate state
Theta-side capacitor/state
parent event active state
relation adapter output state
其它父层动态变量
```

要求：

\[
\|P_A-P_B\|<\epsilon_P
\]

其中 tolerance 必须来自数值地板/已有误差规范，不得为候选手调。

---

## Phase C：候选状态检查

此时检查：

\[
Z_A(t_0),Z_B(t_0)
\]

如果：

\[
Z_A=Z_B
\]

则：

```text
Z2 NOT_MET
candidate淘汰
```

如果：

\[
Z_A\neq Z_B
\]

进入下一阶段。

---

## Phase D：相同未来输入

给：

\[
u_A(t)=u_B(t),\quad t\ge t_0
\]

观察：

\[
Future_A,Future_B
\]

只有：

\[
Future_A\neq Future_B
\]

才记：

```text
HISTORY_DISTINGUISHABLE
A8_CANDIDATE
```

---

# 七、这一轮的主体：原语固定点审计

不要先写新候选代码。

首先审计以下现有原语：

```text
Neuron
Capacitor
MOSFET
Memristor
SynapticBundle
当前允许的连接/反馈结构
已有电压源/能量供给结构
```

对每种原语给出：

```text
动态状态变量
微分/差分方程
输入输出关系
静态非线性
动态非线性
饱和性质
是否有内部记忆
是否允许反馈
耗散项
能量来源
```

---

# 八、建立连续或离散动力系统表达

对于候选组合，不允许只依赖 simulation search。

尽可能写成：

\[
\dot{\mathbf x}
=
\mathbf f(\mathbf x,\mathbf u;\theta)
\]

若代码实际是离散步：

\[
\mathbf x_{n+1}
=
F(\mathbf x_n,\mathbf u_n;\theta)
\]

也可使用离散形式。

明确：

\[
\mathbf x=
(V,Q,w,\ldots)
\]

每个状态变量对应哪个真实物理对象。

禁止无物理对应的软件状态。

---

# 九、固定点搜索

在零输入或固定允许输入：

\[
u=u_0
\]

下解：

\[
\mathbf f(\mathbf x^*;u_0)=0
\]

或：

\[
F(\mathbf x^*;u_0)=\mathbf x^*
\]

寻找全部可达固定点。

不是只从默认初值跑一次。

至少使用：

```text
多初值扫描
解析/半解析求根
数值 root finder
phase-space grid
必要时 continuation
```

结果必须区分：

```text
不存在固定点
唯一固定点
多个固定点
连续固定点集合
周期轨道
数值伪固定点
```

---

# 十、稳定性审计

连续系统计算：

\[
J(\mathbf x^*)
=
\frac{\partial \mathbf f}{\partial \mathbf x}
\]

若：

\[
\Re[\lambda_i(J)]<0
\]

则局部稳定。

若离散系统：

\[
J=
\frac{\partial F}{\partial x}
\]

稳定条件：

\[
|\lambda_i(J)|<1
\]

对每个固定点输出：

```text
eigenvalues
stable / unstable / marginal
```

若解析 Jacobian 困难，可使用有限差分，但必须报告步长敏感性。

---

# 十一、重点审计“无恒流源是否必然不能双稳”

不得预设答案。

上一轮“需要独立恒流偏置”的结论降格为：

```text
HYPOTHESIS-H1
```

而不是冻结事实。

检查至少以下最小反馈类：

### F1 单节点正反馈

\[
\dot x=-ax+b\,g(x)
\]

检查非线性 \(g(x)\) 是否允许三个交点：

\[
x_-^*,x_0^*,x_+^*
\]

其中：

```text
stable
unstable
stable
```

---

### F2 两节点互激

\[
\dot x=-ax+g(y)
\]

\[
\dot y=-ay+g(x)
\]

检查对称/非对称固定点。

---

### F3 两节点互抑/竞争

若现有 MOSFET/Neuron 支持等效抑制：

\[
\dot x=f(x)-g(y)
\]

\[
\dot y=f(y)-g(x)
\]

检查是否形成 winner-state 双吸引域。

---

### F4 Memristor-feedback

不要只使用上一轮 topology。

系统审计：

\[
\dot w=f(w,V,I)
\]

与：

\[
V/I=g(w,\ldots)
\]

闭环后是否形成：

\[
\dot w=G(w)
\]

具有多个稳定零点。

---

# 十二、必须区分四种“记忆”

报告中必须明确分类：

### M1 衰减历史

例如：

\[
H_\tau
\]

已知父层状态。

### M2 慢变量

例如 memristor \(w\)，但只有一个吸引子。

不能自动视作组织状态。

### M3 多稳态

同一外部条件下：

\[
Z_0,Z_1
\]

均稳定/亚稳定。

这是重点。

### M4 吸引子/极限环/更高维状态

如果不存在固定点双稳，但出现稳定 limit cycle 等，也允许作为研究候选。

不得把 A8 人为限制成“只能双稳”。

---

# 十三、参数纪律

本轮允许做**数学参数域审计**，但不等于可以修改冻结 TSS 参数。

分三层报告：

```text
Domain A:
当前实际冻结参数

Domain B:
现有物理原语允许的默认/合法参数范围

Domain C:
只有通过新增物理原语或新参数才能到达
```

如果多稳态只在 Domain C 存在：

```text
EXISTING_PRIMITIVES_CURRENT_DOMAIN = NOT_REACHABLE
```

但不能写：

```text
现有物理原语数学上不可能
```

如果 Domain B 内存在区域，则记录：

```text
MULTISTABILITY_REGION_FOUND
```

再决定是否值得构造实验候选。

---

# 十四、必须进行 continuation / bifurcation 式扫描

如果发现反馈增益 \(g\) 或其它自然参数可能控制稳定性：

扫描：

\[
g_{\min}\rightarrow g_{\max}
\]

记录固定点数量与稳定性。

寻找可能的：

```text
saddle-node bifurcation
pitchfork-like transition
Hopf-like transition
其它稳定性改变
```

不要求正式证明属于哪一类经典分岔。

但必须找出：

\[
\text{single-state region}
\rightarrow
\text{multi-state region}
\]

是否存在。

---

# 十五、物理可达性审计

即使数学存在多个稳定点，也不能直接成为候选。

必须检查：

\[
x_1^*,x_2^*
\]

是否能通过合法 relation-event 输入到达。

不得通过：

```text
直接赋值 x=...
直接设置 w=...
修改 initial state 后称 formation
```

来冒充可达性。

必须使用当前允许的物理输入路径：

\[
relation\ event
\rightarrow
candidate
\]

使不同历史分别进入不同 basin。

---

# 十六、状态保持时间

如果找到两个状态，测：

\[
T_{\rm persistence}
\]

至少与当前关键尺度比较：

```text
adapter 亚阈状态衰减尺度
H_tau≈600 step
可读窗≈723 step
entry/occurrence epoch≈1204 step
```

如果候选差异：

\[
T_{\rm persistence}\ll1204
\]

默认只能：

```text
COMPONENT_EFFECT
```

不能升级为跨 occurrence 候选。

---

# 十七、本轮状态分级

使用：

```text
M0 — NO_MULTISTABILITY_FOUND
当前扫描域未发现多稳/高维吸引态

M1 — MATHEMATICAL_MULTISTABILITY
方程存在多个稳定状态

M2 — PHYSICALLY_REACHABLE
合法 relation-event 输入可以进入不同吸引域

M3 — PARENT_STATE_MATCHED
可以让父层 P 完全对齐但候选 Z 保持不同

M4 — FUTURE_DIVERGENCE
相同未来输入产生不同未来

M5 — A8_CANDIDATE
达到重新定义后的 A8 候选条件
```

本轮最高只到：

```text
M5 A8_CANDIDATE
```

不得直接写 A8 MET。

---

# 十八、上一轮报告状态修正

将：

```text
NO_CANDIDATE_WITH_EXISTING_PRIMITIVES
```

暂时降格为：

```text
NO_CANDIDATE_FOUND_IN_TESTED_TOPOLOGIES
```

原因：

上一轮只实际测试：

```text
Linear RC
Saturating RC
一个 Memristive topology
有限的自反馈/交叉反馈尝试
```

尚未完成整个原语组合空间的固定点与稳定性证明。

只有本轮审计若证明：

\[
\forall\theta\in D_{\rm allowed}
\]

系统至多存在一个稳定可达状态，才允许升级成：

```text
NO_MULTISTABLE_CANDIDATE_IN_ALLOWED_PRIMITIVE_DOMAIN
```

仍避免声称数学上绝对不可能。

---

# 十九、A8 正式建议文本

Agent 本轮需要提交一个新的 A8 草案，但不得自行冻结。

建议起点：

> **A8 — 父层最小充分状态不可闭合性**
>
> 对候选生成深度 \(d+1\) 的物理状态 \(Z\)，若存在两个合法物理历史，使得在某时刻 \(t_0\) 父层深度 \(d\) 的全部已资格化最小充分状态 \(P_d(t_0)\) 相同，但候选状态 \(Z^{(A)}(t_0)\neq Z^{(B)}(t_0)\)，且在 \(t_0\) 后施加相同物理输入时产生可重复的不同未来，则父层状态 \(P_d\) 不足以闭合该动力学，候选取得 A8_CANDIDATE。
>
> 从完整历史、初始状态及候选自身动力学对 \(Z\) 的确定性重放，不构成 A8 反资格；A8 检验的是父层当前状态空间的充分性，而非物理系统是否可模拟。

Agent 可以修改数学表述，但必须保留这一逻辑区别。

---

# 二十、本轮代码边界

优先新增：

```text
research/A8_state_audit/
```

建议：

```text
primitive_equations.py
fixed_point_solver.py
stability_audit.py
parameter_continuation.py
reachability_probe.py
state_matched_twins.py

reports/
data/
```

不得改：

```text
tss/**
nexus_v1/**
```

除非只是只读 import。

---

# 二十一、数据输出要求

至少保存：

```text
primitive
topology
parameter_set
fixed_points
eigenvalues
stability
basin_initial_conditions
formation_sequence
parent_state_at_t0
candidate_state_at_t0
parent_state_difference
candidate_state_difference
future_probe_difference
persistence_time
classification
```

输出：

```text
fixed_points.csv
stability.csv
continuation.csv
reachability.csv
twins.csv
summary.json
```

---

# 二十二、本轮停止条件

### STOP-A

扫描后没有多稳定/高维吸引态：

```text
M0
```

停止，不再构造候选。

### STOP-B

有数学多稳，但 relation-event 无法到达不同 basin：

```text
M1 only
```

停止。

### STOP-C

不同状态可达，但父层状态无法被对齐：

```text
M2 only
```

说明差异仍可由父层解释，停止。

### STOP-D

父状态对齐且 Z 不同，但未来相同：

```text
M3 only
```

说明状态没有独立未来作用，停止。

### CONTINUE

只有：

\[
P_A=P_B,\quad
Z_A\neq Z_B,\quad
Future_A\neq Future_B
\]

才进入：

```text
M5 / A8_CANDIDATE
```

随后另开 K-07/K-06 轮。

---

# 二十三、本轮明确禁止

禁止：

```text
继续修改 ZMemristive 直到 PASS
直接新增恒流源
新增第三层 H_tau+Theta
STDP
DA
Xin
Shadow
S1/S2
显式坐标/距离
Python instance ID 控制物理状态
新增语义标签
靠增大 tau 获得“记忆”
将确定性重放视为 A8 失败
只跑 simulation 不做固定点分析
只找到一个 attractor 就称“组织”
为了获得多稳态随意调冻结参数
```

---

# 二十四、最终交付

输出：

```text
A8最小充分状态与原语多稳态审计工作报告_YYYY-MM-DD.md
```

必须包含：

1. A8 旧定义为何可能过强；
2. A8 新定义草案；
3. R1 历史重放与 R2 父状态闭合的区别；
4. 所有原语动力学方程；
5. 被分析的反馈拓扑；
6. 固定点数量；
7. Jacobian / eigenvalue；
8. 参数域；
9. 多稳态区域是否存在；
10. 是否可由合法 relation event 进入不同 basin；
11. 状态保持时间；
12. parent-state-matched twin 实验；
13. future divergence；
14. 所有失败候选；
15. 最终 M0–M5 状态；
16. 是否值得进入下一轮。

---

# 二十五、研究纪律

本轮目标不是：

> “证明项目能够产生新的生成元。”

而是：

> **判断现有物理系统的状态空间，究竟有没有能力出现一个父层当前充分状态无法闭合的新自由度。**

必须允许最终结论是：

```text
M0 — 当前允许域没有多稳态
```

也必须允许：

```text
M1 — 数学上存在但物理不可达
```

或者：

```text
M2/M3 — 有状态但仍不够资格
```

只有实验和数学同时支持：

\[
P_A=P_B,
\qquad
Z_A\neq Z_B,
\qquad
Future_A\neq Future_B
\]

才允许提交：

```text
A8_CANDIDATE
```

不要为了完成任务而制造候选。