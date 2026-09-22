# MAINLINE V2 — T1-B
## Transduction v2 跨 World 标定与 G0 回接前置
### Agent 执行方案

---

# 0. 阶段状态

当前冻结状态：

```text id="t1b0"
TSS = FROZEN
WT0 = CLOSED
T1-A = CLOSED
W1 = CLOSED
WORLD_V2_RAW_QUALIFIED = TRUE
MAINLINE_V2 = ACTIVE
```

本轮：

```text id="t1b1"
NEXT = T1-B
```

完成后直接：

```text id="t1b2"
G0_RECONNECT
→ OCCURRENCE_REVALIDATION
→ SCALE-0
```

不得插入：

```text id="t1b3"
W1.1
T1-A2
new transduction theory branch
new TSS branch
```

---

# 1. 本轮唯一目标

完成：

\[
\boxed{
Y_B
\rightarrow
\mathcal D_{v2}
}
\]

的正式跨 World 合同。

并在进入 G0 以前冻结：

\[
\boxed{
\text{端口语义}
+
\text{量纲}
+
\text{timebase}
+
\text{层级职责}
}
\]

本轮不是重新设计 World。

也不是重新设计 G0。

---

# 2. 必须继承的 T1-A 结果

冻结：

```text id="t1b4"
T1A_ARCHITECTURE_READY
```

同时保留：

```text id="t1b5"
G0_PORT_CONTRACT_CHANGE_REQUIRED
LAYER_CATEGORY_CONFLICT
```

T1-A 已经确认：

- legacy \(D_i\) 过度承担幅值窗、死区、饱和和事件预筛；
- TSS WORLD_COUPLED 支路存在幅值→速率口错位；
- 生产支路 `SkinPatch.dT → L1` 本身语义自洽；
- 当前 `ThermalDeltaNeuron` runtime 实际只是半波整流 + 增益 + 上钳，不自行求导、不具适应态。

---

# 3. 候选集合冻结

本轮禁止新增候选族。

只保留：

## Candidate A — Thin-Amplitude Port

\[
u_A=S(Y_B-Y_{\rm ref})
\]

特点：

```text id="t1b6"
无 clip
无死区
无动态适应
无事件筛选
```

T1-A 中它是线性保真基准，但需要后续修改 L1/G0 端口语义。

## Candidate B — Explicit Rate Port

\[
u_B(t)=g\frac{Y_B(t)-Y_B(t-\Delta t)}{\Delta t}
\]

注意：

T1-A 原型是“每步差分”。

T1-B 必须升级为**显式物理时间速率**，不得继续使用模糊的：

\[
[T/\text{step}].
\]

Candidate B 当前与现有 L1 `dT_raw` 语义兼容，是过渡候选。

## Legacy

继续作为负控制。

不得获得最终资格。

---

# 4. Candidate C 保持冻结拒绝

保持：

```text id="t1b7"
CANDIDATE_C = REJECTED_AT_D_LAYER
```

适应态机制本身不删除。

登记为：

```text id="t1b8"
FUTURE_L1_INTERNAL_CANDIDATE
```

不得在 T1-B 重新把它塞回 Transduction。

T1-A 已明确：适应态在 D 层属于层位错误，而不是单纯数值表现不好。

---

# 5. 首先冻结层级归类

T1-B 开工第一项必须处理：

```text id="t1b9"
LAYER_CATEGORY_CONFLICT
```

只做文字/合同裁定，不改 production。

正式推荐归类：

\[
\boxed{
Boundary
\neq
Transduction
\neq
L1
\neq
OccurrenceClosure
}
\]

其中：

### Boundary

负责：

```text id="t1b10"
World ↔ organism 的物理接触
组织/介质热惯性
允许的有限观测
```

### Transduction \(D_i\)

负责：

```text id="t1b11"
typed port conversion
reference conversion
unit/scale conversion
```

### L1

负责：

```text id="t1b12"
真正的感受换能
整流
受体电流/激活
未来如需要的适应态
```

### OccurrenceClosure

继续独占：

```text id="t1b13"
trigger
exit
rearm
occurrence identity
```

TSS 文档中将 `{transduce,L1,HC}` 整体归入 `D_i^sim` 的旧分类正式标为：

```text id="t1b14"
LEGACY_LAYER_CLASSIFICATION
```

不得继续作为 MAINLINE V2 的结构分类。

---

# 6. 数据集严格分三部分

建立：

\[
\mathcal W_{\rm ref}
\]

\[
\mathcal W_{\rm cal}
\]

\[
\mathcal W_{\rm hold}
\]

## Reference

World v1。

作用：

```text id="t1b15"
复现旧失败
保持历史可比性
```

不得成为主要参数依据。

## Calibration

World v2 合法域内预先采样的一组 episode。

允许用于参数确定。

## Held-out

World v2 另一组从未参与任何参数选择的 episode。

严格禁止参与：

```text id="t1b16"
参数选择
阈值修改
候选切换
失败后的重新标定
```

World v2 已经证明采样合法域本身存在不同自由度、不同时间尺度以及强耗散角落，因此校准集不能再用少数固定场景代替。

---

# 7. Held-out 必须覆盖困难角落

至少包括：

```text id="t1b17"
强环境耗散
弱隐藏历史
长历史保留
多 Source
错时 Source
低有效自由度 episode
高有效自由度 episode
不同 boundary node
```

特别必须加入：

\[
r_{\rm leak}\approx20
\]

一类“环境本身快速抹掉历史”的合法 episode。

不得因其“难检测”而删除。

W1 已明确登记这一角落。

---

# 8. 不允许用标签平衡数据集

禁止：

```text id="t1b18"
50% easy
50% difficult
50% occurrence
50% no occurrence
```

这不是分类任务。

Calibration/Held-out 必须来自 World v2 的物理参数域。

可使用 stratified sampling，

但 strata 只能依据：

```text id="t1b19"
κ
τ_env
source count
source duration
source energy
boundary size
effective DOF
```

等物理量。

---

# 9. T1-B 第一核心：timebase 合同

必须解决 T1-A 登记的 D2/D3。

当前债务：

```text id="t1b20"
SkinPatch.dT = 每步差分，不是 T/s
World 某些实验 dt=1
Generator 工程 dt=0.001
```

T1-B 必须建立：

```text id="t1b21"
MAINLINE_TIMEBASE_CONTRACT
```

规定：

外部统一物理时间：

\[
t^{ext}\ [s].
\]

所有速率量必须写成：

\[
\dot T
=
\frac{\Delta T}{\Delta t^{ext}}.
\]

禁止：

\[
\Delta T
\]

未经除以物理时间直接冒充速率。

---

# 10. Candidate B 必须重写为 dt-aware

研究原型：

\[
u_B(t)
=
g
\frac{Y_B(t)-Y_B(t-\Delta t)}{\Delta t}.
\]

要求：

若同一物理轨迹分别用：

\[
dt,\ dt/10,\ dt/100
\]

离散，

则 Candidate B 输出在重采样后应收敛。

否则：

```text id="t1b22"
RATE_PORT_DT_DEPENDENT_FAIL
```

不得冻结。

---

# 11. Candidate A 同样做 dt 不变性检查

理论上：

\[
u_A=S(Y_B-Y_{\rm ref})
\]

不应直接依赖 dt。

用相同物理轨迹三档积分验证：

```text id="t1b23"
AMPLITUDE_PORT_DT_INVARIANT
```

如果不是，

必须找到上游 Boundary 数值原因。

---

# 12. 参数标定不使用单一综合评分

禁止：

```text id="t1b24"
score(candidate, params)
→ argmax
```

改用：

\[
\boxed{\text{feasible parameter region}}
\]

即参数只需满足一组资格约束。

保留：

\[
\Theta_D^{legal}.
\]

而不是寻找：

\[
\theta_D^*.
\]

---

# 13. Candidate A 参数角色

仅允许：

\[
S
\]

与：

\[
Y_{\rm ref}
\]

作为主要参数。

其中：

### \(Y_{\rm ref}\)

必须来源于明确物理参考。

不能用：

```text id="t1b25"
让输出最好看的 offset
```

优先：

```text id="t1b26"
environment/skin resting reference
```

或明确 episode-independent 的 reference contract。

### \(S\)

只做单位/尺度映射。

不得承担：

```text id="t1b27"
threshold
event selection
dynamic-range window
```

---

# 14. Candidate B 参数角色

主要参数：

\[
g.
\]

以及明确的：

\[
\Delta t.
\]

但 \(\Delta t\) 不是可调“滤波宽度”。

它必须来自物理采样时间。

禁止为了表现更好选择：

```text id="t1b28"
difference over 5 steps
difference over 20 steps
```

除非形成独立、有物理依据的时间窗口机制。

---

# 15. 参数资格约束

参数合法域至少满足：

```text id="t1b29"
finite output
no hidden clipping
no event dead-zone
sign semantics preserved where applicable
dt consistency
cross-World stability
held-out behavior not catastrophic
```

但不规定：

```text id="t1b30"
retention must equal 1
interior occupancy > X%
```

---

# 16. 保持 controlled physical reduction

目标不是：

\[
I(Y_B;u)
\]

最大。

Transduction 可以丢信息。

但必须能解释：

```text id="t1b31"
丢了什么
为什么丢
在哪种 World 条件下丢
是 D 的结构导致还是 World 本身已经抹掉
```

---

# 17. 必做 World-v2 hidden-twin 测试

必须使用 W1 两类 frozen twin：

### Field-hidden twin

边界当前近似一样，

隐藏 Field 状态不同，

未来分叉。

### Source-hidden twin

Field 当前逐位相同，

Source `energy_remaining` 不同，

未来分叉。

这两类已通过因果阻断确认 hidden state 真正影响未来。

---

# 18. Transduction 不需要恢复隐藏状态

对于 hidden twin：

如果：

\[
Y_A(t_0)=Y_B(t_0)
\]

则任何合法无未来访问的 Transduction 都应满足：

\[
u_A(t_0)=u_B(t_0).
\]

禁止把：

```text id="t1b32"
当前不可见 hidden state
```

“推断回来”作为成功标准。

真正要观察的是：

当未来边界开始分叉时，

\[
u_A(t>t_0)
\]

是否按其自身合同响应。

---

# 19. 这是一个重要负控制

如果某 Candidate 在：

\[
Y_A(t_0)=Y_B(t_0)
\]

时却输出不同：

```text id="t1b33"
HIDDEN_ACCESS_OR_STATE_LEAK = FAIL
```

除非差异完全来自 Candidate 自己合法的过去输入状态。

Candidate A 无状态，所以必须相同。

Candidate B 具有一个 previous-sample state，因此允许过去 \(Y_B\) 不同导致当前速率不同，但必须能够完整从边界 replay 解释。

---

# 20. Cross-pair 共谋攻击

Calibration 不只做：

```text id="t1b34"
World_A + parameter_A
World_B + parameter_B
```

最终参数必须固定一套：

\[
\theta_D.
\]

然后横跨所有 World 条件。

至少比较：

\[
W_i\times D(\theta_D)
\]

全部组合。

如果某参数只在某个 World 子域工作：

```text id="t1b35"
CO_ADAPTATION_RISK = HIGH
```

不得冻结。

---

# 21. Leave-one-region-out 攻击

除了普通 held-out，再做一次参数域区域留出。

例如：

Calibration 不包含：

\[
\tau_{\rm env}<50
\]

而 held-out 专门包含强耗散域。

或：

Calibration 不包含：

```text id="t1b36"
3-source episodes
```

held-out 专测。

目的：

不是要求完美泛化，

而是检查 Transduction 是否只是插值记住 calibration domain。

---

# 22. Legacy 必须全程陪跑

所有 calibration / held-out episode 同时运行：

```text id="t1b37"
Legacy
Candidate A
Candidate B
```

legacy 用于确认旧失败是否仍然出现：

```text id="t1b38"
floor collapse
ceiling collapse
baseline-zeroing artifact
co-adaptation
dynamic-range collapse
```

不得因为已经知道 legacy 差就省略。

---

# 23. 参数扫描只用于找合法域

允许：

```text id="t1b39"
S ∈ log-space
g ∈ log-space
```

但输出必须是：

```text id="t1b40"
legal interval
failure boundaries
extreme cases
```

不是：

```text id="t1b41"
best S
best g
```

若最终生产必须选一个代表值：

选取合法域内部的 canonical reference point，

并注明：

```text id="t1b42"
CANONICAL_FOR_IMPLEMENTATION
≠
OPTIMAL
```

---

# 24. Candidate A 的资格问题

Candidate A 需要回答：

> 当 G0/L1 将来改成幅值输入语义时，它是否已经足够成为正式 \(D_{v2}\)？

必须测试：

```text id="t1b43"
跨 World 线性一致性
reference 稳定性
大幅输入不人为 clip
弱输入不人为 floor
held-out 不出现数值爆炸
```

---

# 25. Candidate B 的资格问题

Candidate B 需要回答：

> 在不改当前 L1 的情况下，它能否作为合法过渡接口？

重点：

```text id="t1b44"
dt convergence
noise sensitivity
slow World 的速率接近零是否合法
fast transient 是否不过度爆大
sign semantics
held-out stability
```

特别注意：

强耗散或缓慢环境中：

\[
\dot T\approx0
\]

不是失败。

World 若没有快速变化，Rate Port 本来就应该近零。

---

# 26. A 与 B 不允许综合排名

最后不能写：

```text id="t1b45"
A beats B
```

而应分别给：

```text id="t1b46"
A_LONG_TERM_PORT_QUALIFIED = YES/NO
B_TRANSITION_PORT_QUALIFIED = YES/NO
```

因为它们解决不同架构阶段的问题。

---

# 27. 推荐目标态

当前默认目标仍是：

\[
\boxed{
World
\rightarrow
Boundary
\rightarrow
Thin\ D
\rightarrow
L1_{\rm dynamic}
}
\]

也就是 Candidate A 类型。

Candidate B 是：

\[
\boxed{
World
\rightarrow
Boundary
\rightarrow
Explicit\ Rate\ Port
\rightarrow
L1_{\rm current}
}
\]

属于兼容过渡态。

只有数据和物理合同推翻这一点时才改变。

---

# 28. Q1 不再重新研究

T1-A Q1 已给出：

- 幅值→电流的换能应然在受体膜/L1；
- 速率敏感可由受体内部适应态涌现；
- 皮肤热惯性属于 Boundary；
- 压缩心理物理规律不能直接拿来作为 D 函数。

T1-B 不再开新文献树。

只在需要确认具体实现参数时补引用。

---

# 29. T1-B 的关键架构裁定

必须最终明确：

```text id="t1b47"
FINAL_D_ARCHITECTURE
```

允许：

### 状态 1

```text id="t1b48"
A_QUALIFIED
B_QUALIFIED_AS_TRANSITION
```

这是当前最可能的健康结果。

### 状态 2

```text id="t1b49"
A_NOT_YET_QUALIFIED
B_TRANSITION_ONLY
```

允许先用 B 回接 G0，但必须保留长期端口债务。

### 状态 3

```text id="t1b50"
NO_CANDIDATE_CROSS_WORLD_QUALIFIED
```

则不能进入 G0 reconnect。

不得临时发明 Candidate D 救场。

---

# 30. G0 port contract 必须在 T1-B 收口时冻结

无论是否本轮改代码，都必须产生：

```text id="t1b51"
G0_INPUT_PORT_CONTRACT_V2.md
```

至少定义两个 typed port：

\[
U_T
\]

幅值口，

与：

\[
U_{\dot T}
\]

速率口。

明确：

```text id="t1b52"
单位
时间基
符号语义
允许输入范围
谁产生
谁消费
```

禁止继续用一个模糊：

```text id="t1b53"
u_i / dT_raw
```

同时承担两种语义。

---

# 31. 不一定两个 port 都进入最终 production

typed port 的目的首先是消除歧义。

最终可裁：

```text id="t1b54"
G0_V2 uses U_T
```

或：

```text id="t1b55"
G0_transition uses U_dT
```

但代码命名必须反映真实含义。

---

# 32. G0 本轮仍然 READ_ONLY

T1-B 允许构建研究适配器：

```text id="t1b56"
research/transduction_v2/adapters/
```

但禁止修改：

```text id="t1b57"
BaseGenerator
ThermalDeltaNeuron
OccurrenceClosure
```

正式代码修改属于下一阶段：

```text id="t1b58"
G0_RECONNECT
```

---

# 33. 可以运行 L1 diagnostic

虽然 G0 production 不改，

允许把 Transduction 输出喂给冻结 L1 方程做离线诊断。

但：

```text id="t1b59"
L1 activation
```

只能作为接口后果。

不得成为参数优化目标。

---

# 34. 禁止 occurrence 调参

本轮原则继续保持：

```text id="t1b60"
NO_OCCURRENCE_OPTIMIZATION
```

可以在最终 canonical 参数冻结后做一次：

```text id="t1b61"
occurrence smoke test
```

只检查：

```text id="t1b62"
链路不会完全失效
```

不得根据结果回调 D 参数。

真正的 occurrence 资格属于下一阶段。

---

# 35. 度量合同

继续使用 T1-A 合同。

至少报告：

\[
D_{\rm boundary}^{abs}
\]

\[
D_{\rm port}^{abs}
\]

以及 normalized 值。

同时：

```text id="t1b63"
zero occupancy
saturation occupancy
sign preservation
timing preservation
rate response
dt convergence
```

所有 normalized ratio 必须同报绝对分子/分母。

---

# 36. 新增跨 World 稳健指标

不是综合评分。

逐 episode 登记：

```text id="t1b64"
QUALIFIED
DEGRADED
STRUCTURALLY_EXPECTED_ZERO
NUMERIC_FAIL
SEMANTIC_FAIL
```

例如：

强耗散环境下 Candidate B 输出很弱，

如果边界本身变化率就弱：

应登记：

```text id="t1b65"
STRUCTURALLY_EXPECTED_ZERO
```

不能记 FAIL。

---

# 37. 区分 World loss 与 D loss

每个失败案例必须回答：

\[
D_{boundary}\approx0?
\]

还是：

\[
D_{boundary}>0,\quad D_{port}\approx0?
\]

前者：

```text id="t1b66"
WORLD_ALREADY_REDUCED
```

后者：

```text id="t1b67"
TRANSDUCTION_LOSS
```

这是本轮必须保留的核心区分。

---

# 38. Source-hidden twin 是特别好的检查

若当前边界完全一样，

Candidate A 必须相同。

Candidate B 如果过去边界也一样，也必须相同。

只有 Source 的隐藏能量未来作用到 Boundary 后，

D 才允许产生分叉。

这将继续验证：

\[
\boxed{
D\text{ 不偷读 }X_W
}
\]

---

# 39. Boundary Replay 必须升级到 v2

选 World v2 calibration + held-out representative episodes。

执行：

```text id="t1b68"
live World
→ record Y_B
→ delete World
→ replay Y_B
→ D_v2
```

要求 Candidate A：

```text id="t1b69"
bit-exact / tolerance-exact
```

Candidate B：

如果保存 previous-sample state 初始化条件，

也必须重放一致。

---

# 40. 参数冻结前做 blind held-out

流程必须严格：

```text id="t1b70"
1. freeze calibration set
2. determine legal parameter region
3. choose canonical reference point
4. write canonical config + fingerprint
5. lock
6. run held-out once
```

如果 held-out 失败：

不得直接改参数再重跑。

先登记：

```text id="t1b71"
FIRST_HELDOUT_RESULT
```

然后判断失败属于：

```text id="t1b72"
合法边界
设计错误
参数域错误
数值错误
```

---

# 41. Held-out 失败不自动否决

如果某 held-out episode 本身：

\[
Y_B
\]

几乎没有变化，

Candidate B 近零是正确行为。

只有出现：

\[
D_{boundary}>0
\]

而：

\[
D_{port}
\]

因 D 结构无理由塌缩，

才构成真正失败。

---

# 42. 禁止为了 held-out 改 World

任何 held-out 暴露的问题：

不能修改：

```text id="t1b73"
World v2
Source
boundary
τ_env
κ
```

W1 已经冻结。

如果问题来自 World 合法角落：

Transduction 必须接受它。

---

# 43. Canonical config fingerprint

最终每个通过候选产生：

```text id="t1b74"
candidate_name
architecture_version
parameter_roles
canonical_values
timebase_contract
reference definition
SHA/fingerprint
```

历史 config 保留为：

```text id="t1b75"
LEGACY
```

不得覆盖。

---

# 44. 参数值必须注明来源

例如：

```text id="t1b76"
PHYSICAL
MEASURED
CALIBRATED
CANONICAL_REFERENCE
LEGACY
```

不得仅写：

```text id="t1b77"
S = 0.023
```

而无来源。

---

# 45. T1-B 六门

## T1B-M1 — Port semantics

幅值/速率语义、单位、timebase 全明确。

## T1B-M2 — Cross-World

同一候选、同一固定参数横跨 World v1/v2 calibration 合法工作。

## T1B-M3 — No co-adaptation

Cross-pair / leave-region-out 不出现专配式失效。

## T1B-M4 — Held-out

首次 blind held-out 无结构性崩溃。

## T1B-M5 — Replay purity

World 删除后边界重放完全复现 D 输出。

## T1B-M6 — Controlled reduction

所有主要信息损失都能明确归因于：

```text id="t1b78"
World
Boundary
D
```

之一。

---

# 46. 不设置 occurrence 门

本轮没有：

```text id="t1b79"
T1B-M7 occurrence success
```

因为那属于 G0 reconnect。

---

# 47. T1-B 终态

只允许四种：

### A

```text id="t1b80"
TRANSDUCTION_V2_QUALIFIED
```

至少有一个正式长期候选。

### B

```text id="t1b81"
TRANSITION_RATE_PORT_QUALIFIED
LONG_TERM_AMPLITUDE_PORT_PENDING_G0
```

允许进入 G0 reconnect，但明确是过渡结构。

### C

```text id="t1b82"
T1B_HELDOUT_FAIL
```

不得进入 G0。

### D

```text id="t1b83"
T1B_PORT_CONTRACT_UNRESOLVED
```

量纲/timebase/语义仍不清楚。

---

# 48. 推荐的最终判定表达

不要写：

```text id="t1b84"
Candidate A wins
```

而写类似：

```text id="t1b85"
A_LONG_TERM_PORT_QUALIFIED = YES
B_TRANSITION_PORT_QUALIFIED = YES
FINAL_MAINLINE_TARGET = A
G0_RECONNECT_BRIDGE = B
```

如果数据支持。

---

# 49. G0 reconnect 前必须解决的文本债务

T1-B 收口时完成：

```text id="t1b86"
LAYER_CATEGORY_CONFLICT = RESOLVED_AT_CONTRACT_LEVEL
```

以及：

```text id="t1b87"
G0_PORT_CONTRACT_V2 = FROZEN
```

但 production code 仍不改。

---

# 50. 下一阶段 G0 reconnect 只做定点修改

T1-B 通过后，

下一轮禁止重新研究：

```text id="t1b88"
World
Transduction architecture
TSS
```

只做：

```text id="t1b89"
typed port implementation
L1 input semantics
timebase plumbing
legacy compatibility
```

然后重跑 occurrence。

---

# 51. G0 reconnect 后立即做 Occurrence Revalidation

重新验证：

\[
\chi_i^k=
(
t^\uparrow,
t^\downarrow,
t^{rearm}
)
\]

以及：

```text id="t1b90"
trigger
exit
rearm
duration
energy
lineage
```

不得沿用旧 P2-A 的 occurrence 正结果作为新 World/Transduction 下的当然事实。

---

# 52. 但不得重新定义 G0

G0 reconnect：

\[
\neq
\]

重新发明十神经元生成元。

只验证原 G0 在新合法物理入口下是否仍然成立。

---

# 53. World v2 本轮保持完全冻结

必须复跑 W1：

```text id="t1b91"
M1-M6
hidden twins
energy audit
dt audit
```

确认 T1-B research 代码没有污染 World。

W1 当前已有：

\[
\boxed{WORLD\_V2\_RAW\_QUALIFIED}
\]

并且因果 hidden twins、能量闭合和 dt 收敛均已建立。

---

# 54. 代码范围

新增：

```text id="t1b92"
research/transduction_v2/t1b/
```

建议：

```text id="t1b93"
dataset_builder.py
calibration_scan.py
heldout_eval.py
cross_world_attack.py
replay_eval.py
timebase_audit.py
final_qualification.py
```

不得修改：

```text id="t1b94"
nexus_v1/
tss/
research/world_v2/
```

---

# 55. 数据文件

至少保存：

```text id="t1b95"
dataset_manifest.csv
calibration_episodes.csv
heldout_episodes.csv
parameter_legal_regions.csv
cross_world_matrix.csv
heldout_results.csv
timebase_convergence.csv
replay_results.json
extreme_cases.csv
qualification_summary.json
```

---

# 56. 文档交付压缩为四份

```text id="t1b96"
T1B_PORT_AND_TIMEBASE_CONTRACT.md
T1B_CALIBRATION_AND_CROSS_WORLD_REPORT.md
T1B_HELDOUT_AND_REPLAY_REPORT.md
T1B_FINAL_RULING.md
```

另保存：

```text id="t1b97"
T1B_NEGATIVE_RESULTS.md
```

---

# 57. Negative Results 必须特别记录

例如：

```text id="t1b98"
A 在当前 L1 下常燃
B 在极慢环境下合法近零
某 calibration 子域不存在统一参数
某 held-out 区域第一次 blind 失败
World 已经抹掉历史而 D 无法恢复
legacy 再次出现 floor/ceiling collapse
```

这些不能删。

---

# 58. T1B_FINAL_RULING 首屏必须回答

1. Candidate A 是否跨 World 合格？
2. Candidate B 是否跨 World 合格？
3. 两者分别是什么架构身份？
4. 最终长期 Transduction 目标是哪一个？
5. G0 reconnect 是否需要 bridge？
6. \(U_T\) 与 \(U_{\dot T}\) 的正式单位是什么？
7. 全项目统一 physical dt 合同是什么？
8. Layer category conflict 如何裁定？
9. Calibration 和 held-out 是否严格隔离？
10. 首次 held-out 是否通过？
11. 是否存在 World↔D 共适应？
12. 是否允许进入：

```text id="t1b99"
G0_RECONNECT
```

---

# 59. 本轮硬停止条件

只要得到：

```text id="t1b100"
TRANSDUCTION_V2_QUALIFIED
```

或合法的：

```text id="t1b101"
TRANSITION_RATE_PORT_QUALIFIED
```

并且允许 G0 reconnect，

T1-B 立即停止。

禁止继续寻找：

```text id="t1b102"
更好的 nonlinear transform
更好的 compression
更高 retention
更多 sensor models
```

---

# 60. 主线之后的顺序不得再改变

\[
\boxed{
T1\text{-B}
}
\]

↓

\[
\boxed{
G0\ reconnect
}
\]

↓

\[
\boxed{
Occurrence\ revalidation
}
\]

↓

\[
\boxed{
SCALE\text{-}0
}
\]

↓

\[
\boxed{
TSS\ Relation\ reconnect
}
\]

然后才允许重新进入：

\[
\boxed{
\text{higher generation}
}
\]

---

# 61. 一句话目标

\[
\boxed{
\text{不是找到一个“最好用”的转导函数，
而是冻结一条跨不同物理 World 都成立、
不偷做事件判断、并且可以合法接回 G0 的物理接口。}
}
\]