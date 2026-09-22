# A8/A9/K-06 时间方向组织候选研究轮
## Agent 执行任务书

### 一、任务目标

在现有冻结 TSS 主线之外，设计并验证一个**最小物理状态候选 \(Z\)**。

本轮不是继续增加关系递归深度，也不是构造“第三层生成元”。

本轮唯一核心问题：

\[
\boxed{
\text{生成深度增加，能否第一次带来新的独立物理状态自由度？}
}
\]

现有 C1 已证明：

\[
\text{relation}
\rightarrow
\text{re-eventization}
\rightarrow
H_\tau+\Theta
\rightarrow
c_{ro}
\]

工程链成立。

但现有 \(c_{ro}\) 可被父层同类 \(H_\tau+\Theta\) 完整重构，因此：

```text
C1 engineering recursion = PASS
A8 = NOT_MET
A9 static lineage = PASS
A9 runtime lineage = GAP
generator qualification = NOT_QUALIFIED
```

本轮不得修改这些冻结结论。

---

# 二、硬性约束

## 1. 不修改当前冻结 C1 物理路径

禁止修改：

```text
PhysicalHistoryKernel
PhysicalThetaComparator
PhysicalEntryGate
RelationEventAdapter
现有 C1 参数
现有 C1 阈值
现有 C1 PASS 测试
```

禁止为了得到 A8 非零残差而修改原有重构基线。

现有 T-C1-6b 的语义必须保持：

```text
PASS = A8_NOT_MET 被稳定复现
```

如果未来新候选产生稳定非零残差：

```text
不得修测试
不得扩大 tolerance
不得修改父层基线
```

应开启新候选资格审查。

---

## 2. 不允许软件身份直接控制物理输出

不得出现：

```python
if relation_instance_id == ...
if epoch_id == ...
if lineage_match:
    spike = ...
```

不得让：

```text
Python object identity
字符串 ID
GeneratedAddress 标签
relation window 元数据
epoch 编号
```

直接决定：

```text
spike
gate
Theta
电流
物理状态切换
```

A9 runtime lineage 只允许使用独立 sidecar 做：

```text
观察
记录
绑定
审计
```

sidecar 不得反向控制物理路径。

---

## 3. 禁止引入旧路线

本轮禁止接入：

```text
DA
STDP
Shadow
Xin
旧运动控制学习链
旧语义系统
```

也不启动：

```text
S1/S2 空间构建
完整 Event Kernel
第三层生成元
```

---

## 4. 禁止显式坐标/距离进入候选

候选 \(Z\) 不允许读取：

```text
x/y/z
Euclidean distance
site index
预写方向标签
```

候选只能消费已有物理 relation-event 信号及自身物理状态。

---

# 三、第一阶段：物理原语审计

先不要写新结构。

审计 `nexus_v1` 中已经存在的物理原语，寻找能够形成以下性质的最小组合：

\[
\boxed{\text{hysteresis / bistability / metastability / attractor}}
\]

重点检查已有：

```text
Neuron
SynapticBundle
Capacitor
MOSFET
Memristor（若当前母体确有）
已有反馈连接能力
已有能量耗散结构
```

输出一张审计表：

```text
primitive
state variable
decay law
nonlinearity
feedback possible?
hysteresis possible?
requires new parameter?
already qualified?
```

优先使用已经存在的母体物理元件。

若现有原语完全无法产生两个可区分稳定/亚稳定状态，才允许提出新的最小物理结构。

不得为了理论需要直接创造一个：

```python
state = 0/1
```

的软件状态变量。

---

# 四、候选 Z 的最低要求

候选必须至少具有两个物理可区分状态：

\[
Z_0,\quad Z_1
\]

它们不能只是：

\[
H_\tau(t)
\]

的两个不同数值。

更不能只是：

\[
H_{\tau_1}+H_{\tau_2}
\]

这种父事件指数历史的扩展。

候选必须表现出某种路径依赖，例如：

\[
Input_A \rightarrow Z_1
\]

而：

\[
Input_B \rightarrow Z_0
\]

在随后给两系统完全相同当前输入时：

\[
I_A(t)=I_B(t)
\]

仍存在：

\[
Z_A(t)\neq Z_B(t)
\]

并进一步：

\[
Future_A\neq Future_B
\]

候选可以考虑：

```text
最小双稳态反馈
物理迟滞回路
竞争性双节点
局部正反馈 + 耗散
具有吸引域的最小回路
```

但具体结构必须由现有物理原语审计决定，不预先硬编码方案。

---

# 五、A8 核心实验

这是本轮最高优先级。

## EXP-A8-NEW-01：历史匹配双胞胎实验

建立系统 A/B。

### Formation phase

给 A、B 不同的早期 relation-event 历史：

```text
History_A
History_B
```

使候选最终进入：

\[
Z_A\neq Z_B
\]

### Washout phase

等待足够长，使现有父层可测历史：

\[
H_\tau
\]

以及其它已有允许重构的父状态趋于相同。

必须验证：

\[
|H_A-H_B|<\epsilon
\]

而且近期 parent-event history 完全一致。

### Probe phase

给 A、B 完全相同的 relation-event 输入：

\[
E_A(t)=E_B(t)
\]

观察未来输出。

如果：

\[
Output_A=Output_B
\]

候选淘汰。

只有出现：

\[
\boxed{
Output_A\neq Output_B
}
\]

才进入下一步。

---

# 六、A8 强重构攻击

即使 EXP-A8-NEW-01 出现差异，也不能立即宣布 A8 MET。

必须主动建立最强父层重构器。

重构器允许消费：

```text
完整 parent event timing
完整 binary adapter outputs
已有 H_tau 状态
已有 Theta 输出
父 relation occurrence history
所有当前已资格化的父层同类状态
```

不得只使用简单解析公式。

优先直接实例化真实父层同型物理栈。

要求：

\[
\hat Z(t)
=
F(\text{all qualified parent-class states})
\]

计算：

\[
R_Z(t)=Z_{\text{actual}}(t)-\hat Z(t)
\]

如果：

\[
R_Z\approx0
\]

则 A8 继续：

```text
NOT_MET
```

如果出现跨：

```text
seed
formation history
probe history
```

都稳定存在的系统性非零残差，状态改为：

```text
A8_CANDIDATE
```

不得直接标记 MET。

---

# 七、禁止“伪 A8”

以下情况全部不能算 A8：

### 情况 A

只是增加第二个 RC：

\[
H_{\tau_1}+H_{\tau_2}
\]

### 情况 B

只是参数不同：

\[
\tau=600
\rightarrow
\tau=800
\]

### 情况 C

只是父关系幅度被重新保留下来。

### 情况 D

只是软件保存：

```text
previous_relation_id
epoch_id
instance_id
```

### 情况 E

只是增加计算复杂度，但仍能被父层状态完整重构。

### 情况 F

只是输出非线性：

\[
y=f(H_\tau)
\]

如果 \(f\) 已知且父状态足够重建，仍不是 A8。

---

# 八、K-07：独立未来可达作用

只有 A8_CANDIDATE 才能进入 K-07。

设计下游 `future_probe`。

要求三组：

### baseline

```text
formation
→ Z
→ future_probe
```

### candidate blocked

```text
formation
→ block Z physical support
→ future_probe
```

### parent-only replay

```text
相同 parent event history
→ 不允许 Z 建立
→ future_probe
```

需要出现：

\[
Future_Z\neq Future_{\text{blocked}}
\]

同时：

\[
Future_Z\neq Future_{\text{parent-only}}
\]

而且差异必须能被物理阻断消除。

如果 Z 虽然拥有状态，但对未来没有独立作用：

```text
K-07 = NOT_QUALIFIED
```

---

# 九、K-06：拓扑保护暂不先定义公式

不要先写抽象“拓扑保护指标”。

先实验得到：

\[
\text{robustness basin}
\]

与：

\[
\text{critical cut set}
\]

对候选 Z 的物理结构逐个做干预。

## 非关键扰动

例如：

```text
减弱一个边缘连接
移除一个冗余支撑
小幅改变某元件参数
```

要求：

\[
Z'\sim Z
\]

future probe 仍保持同类行为。

## 关键切断

寻找最小：

\[
C_{\rm critical}
\]

使：

\[
Z\xrightarrow{cut} \varnothing
\]

并且：

\[
Future_Z
\rightarrow
Future_{\rm baseline}
\]

或失去候选特征。

由数据反推：

```text
哪些改变仍属于同一组织
哪些改变使组织真正解体
```

在得到这组数据以前：

```text
R-E0-3 = RULING_REQUIRED
K-06 = BLOCKED
```

不得提前升级。

---

# 十、A9 sidecar

如果候选开始跨 occurrence 运行，再实现独立：

```text
RuntimeLineageSidecar
```

记录：

```text
physical occurrence instance
relation occurrence instance
parent relation pair
epoch
candidate activation interval
candidate physical support addresses
future probe consequence
```

要求：

```text
sidecar read-only
sidecar 不进 spike path
sidecar 不进 Theta
sidecar 不进 gate
sidecar 不改变 Z
```

sidecar 的目标只是回答：

> “运行中的这个物理状态到底由哪些实际 occurrence/relation instance 形成？”

而不是替物理系统决定身份。

---

# 十一、随机性实验必须拆成两个 seed

以后所有多 seed 实验必须明确：

```text
physical_seed
world_rng_seed
```

不能再用一个“seed”概念混合：

```text
bundle physical variation
+
global Langevin/world trajectory
```

至少提供：

```text
deterministic mode:
world_rng_seed 固定

stochastic mode:
physical_seed × world_rng_seed
```

初步资格建议：

\[
5\times5
\]

进入正式冻结资格后再扩大到：

\[
10\times10
\]

或依据计算成本裁定。

---

# 十二、数据输出

所有新实验必须保存结构化数据，不只打印 PASS。

至少：

```text
run_id
physical_seed
world_rng_seed

formation_history
probe_history

parent_event_times
parent_relation_times

H_tau states
Theta states

Z physical variables

candidate_output

future_probe_output

blocked_control_output

reconstructor_output
A8_residual

perturbation_type
perturbation_target

runtime_lineage_sidecar ids
```

建议输出：

```text
research/A8_candidate/
    runs.csv
    traces/*.npz
    summary.json
```

---

# 十三、淘汰规则

Agent 必须主动淘汰候选。

出现任何一条即停止继续包装：

### FAIL-1

父层同类算子能够数值重构：

\[
residual\approx0
\]

### FAIL-2

只有在 parent history 尚未衰减时才能看到差异。

### FAIL-3

差异来自 software identity。

### FAIL-4

差异来自不同当前输入，而不是内部状态。

### FAIL-5

状态存在但对 future probe 无独立作用。

### FAIL-6

状态只能通过某个新写死阈值/标签维持。

### FAIL-7

跨 seed 不可复现。

淘汰后必须保留失败数据和原因。

禁止不断调参直到通过。

---

# 十四、本轮成功状态分级

不使用单一 PASS。

采用：

```text
Z0 — COMPONENT_EFFECT
仅发现组件级迟滞/状态

Z1 — PHYSICALLY_REACHABLE
在合法 relation-event 工作域可到达

Z2 — HISTORY_DISTINGUISHABLE
相同近期父历史下仍存在不同 Z

Z3 — A8_CANDIDATE
最强父层同类重构出现稳定非零残差

Z4 — K07_CANDIDATE
Z 对未来具有独立可阻断作用

Z5 — K06_CANDIDATE
表现出 robustness basin + critical cut set

Z6 — GENERATOR_REVIEW_READY
才允许提交理论审查
```

任何阶段都不得自动称：

```text
new generator
organization
方向生成元
```

最终命名权留到理论审查。

---

# 十五、Agent 第一轮具体交付

第一轮不要做完整 K-06。

只完成：

### 任务 1
物理原语审计。

### 任务 2
提出最多 **3 个**最小 Z 候选。

每个候选写清：

```text
物理元件
状态变量
状态维数
形成机制
耗散机制
为什么不是另一个 H_tau
新增参数及来源
```

### 任务 3
选择最小的一个候选实现于：

```text
research/
```

或独立实验目录。

不得进入正式 TSS 主路径。

### 任务 4
运行：

```text
EXP-A8-NEW-01 history-matched twins
EXP-A8-NEW-02 parent-class reconstruction attack
EXP-A8-NEW-03 candidate block / future probe
```

### 任务 5
至少：

```text
5 physical_seed
×
5 world_rng_seed
```

完成数据采样。

若计算量过大，可以先：

```text
3×3 discovery
```

发现正信号以后再 5×5。

### 任务 6
输出工作报告：

```text
A8新候选研究轮工作报告_YYYY-MM-DD.md
```

报告必须包含：

```text
候选结构
所有新增参数出处
实验设计
原始数据位置
PASS/FAIL/NOT_MET/GAP
最大重构残差
future probe effect size
seed 稳定性
负结果
淘汰理由
下一步建议
```

---

# 十六、本轮禁止事项

禁止：

```text
修改冻结 C1 使其通过 A8
第三层 H_tau+Theta 递归
修改 adapter 阈值保存 amplitude
把 adapter 亚阈值短记忆冒充组织状态
用 Python ID 建 runtime identity
加入 STDP
加入 DA
加入 Xin
加入 Shadow
加入 S1/S2
增加语义标签
显式坐标/距离
为了 PASS 调低标准
删除或 xfail 新失败
```

---

# 十七、最重要的研究纪律

Agent 应把目标理解为：

> 不是“设计一个能够通过 A8 的结构”。

而是：

> **寻找最小物理结构，并尽最大努力证明它仍然只是父历史的可重构结果。**

只有所有合理反例都没有把它击穿之后，才允许把它升级成候选。

现有 C1 已经给出一个很好的负例：

```text
复杂
≠
不可约

递归
≠
新生成元

有历史
≠
有组织身份
```

本轮必须延续这一纪律。