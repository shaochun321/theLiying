# MAINLINE V2 — Memory / Feedback Substrate-0

## MFS0-E0：G1 历史资格、后续调制与持久结构沉积的最小资格实验

### 0. 阶段定位

当前冻结主线：

\[
World
\rightarrow
Boundary
\rightarrow
Transduction
\rightarrow
G_0
\rightarrow
\chi^{(0)}
\rightarrow
\mathcal N
\rightarrow
\mathcal C_\rho
\rightarrow
\chi_\rho^{(1)}
\rightarrow
G_1
\]

已接受：

```text
G0_OCCURRENCE_V2_QUALIFIED
D2_RELATION_PROCESS_V0_QUALIFIED
D2_1_RECURSIVE_GENERATION_QUALIFIED
G1_QUALIFIED
```

Posterior-0 已结束。

当前不得继续：

```text
Posterior-1
Xin implementation
TOPRXin integration
Shadow reconnect
G1-v2
larger G1 network
new modality
old DA/STDP direct reconnect
```

本轮进入：

\[
\boxed{
Memory / Feedback Substrate-0
}
\]

本轮不是重新证明 G1，也不是直接证明 Posterior Construction。

唯一问题是：

> 一个已经资格化的 G1 relation occurrence，能否留下一个有限的物理历史资格状态；后来发生的另一个真实事件能否与该资格状态发生局部作用，把历史选择性沉积到一个持久结构状态中，并因此改变之后完全相同输入下的动力学？

---

# 1. 本轮核心结构

目标结构定义为：

\[
\boxed{
Past
\rightarrow e
\quad+\quad
Later
\rightarrow M
\Rightarrow
\Delta z
\rightarrow
Future
}
\]

其中：

### Past

使用已经资格化的 relation occurrence：

\[
\chi_\rho^{(1)}.
\]

不得回读：

```text
RelationCell membrane state
internal neuron state
hidden full state
manual relation label
```

只允许通过：

```text
RelationOccurrencePortV1
```

或与之严格同族的 typed interface 消费。

---

### 历史资格状态 \(e\)

定义：

\[
e_\rho(t).
\]

其含义严格限制为：

> 过去发生的 relation 在当前物理网络中仍存在一个有限时间的“可修改资格”。

它不是：

```text
memory label
relation ID cache
Python boolean
historical CSV flag
semantic tag
reward eligibility
```

首选物理候选：

\[
\boxed{
e(t)=V_{C_e}(t)
}
\]

即由实际 capacitor / RC state 承载。

最低动力学形式：

\[
C_e\frac{de}{dt}
=
I_\rho(t)
-
\frac{e}{R_e}.
\]

因此：

\[
\tau_e=R_eC_e.
\]

必须存在：

```text
charge/state
formation
decay
physical time constant
resource/energy accounting where measurable
```

不允许继续把普通 Python float list 直接称作 physical eligibility。

---

### Later

后来事件记为：

\[
\Delta.
\]

首轮优先使用已有资格化 occurrence，而不是增加新 modality。

可以选择：

\[
\chi_j^{(0)}
\]

作为 later physical occurrence。

其时间必须满足：

\[
t_\Delta>t_W.
\]

但必须落在：

\[
e_W(t_\Delta)
\]

仍然可测的资格窗口内。

禁止人为修改过去 occurrence 的绝对时间来制造 overlap。

---

### Modulation \(M\)

后来事件不得直接转成：

```python
M = 1
```

或：

```python
da_concentration = 0.5
```

作为正式资格路径。

它必须通过真实物理传播产生一个有限状态：

\[
\Delta
\rightarrow
M_\Delta(t).
\]

定义只允许：

\[
\boxed{
M(t)=\text{modulatory physical signal}
}
\]

禁止赋予：

```text
reward
punishment
success
error
good
bad
value
meaning
```

等语义。

旧 neuromodulator / DA 机制只允许作为低层物理原语参考。

若复用，必须首先完成：

```text
SEMANTIC_ERASURE_AUDIT
```

证明本轮不存在 reward side channel。

---

# 2. 持久状态候选

本轮主候选：

\[
\boxed{
z=w
}
\]

其中：

\[
w
\]

为 memristive / persistent conductance state。

原因不是它名字叫 memory，而是要求它满足：

\[
e,M\rightarrow0
\]

之后：

\[
w^+\neq w^-.
\]

并且：

\[
w
\rightarrow
R(w)
\rightarrow
G(w)
\rightarrow
I
\]

能够真实改变以后相同输入下的电路动力学。

首轮不要求：

```text
long-term biological memory
memory consolidation
lifelong learning
semantic memory
```

只要求：

\[
\boxed{
persistent\ physical\ state
}
\]

成立。

RailLatch 保留为：

```text
PERSISTENT_STATE_POSITIVE_CONTROL
```

不作为首轮主要写入载体。

---

# 3. 最小假设

本轮只测试一个假设：

\[
H_1:
\]

存在局部物理组合，使：

\[
\chi_\rho^{(1)}
\rightarrow e_\rho
\]

且：

\[
\Delta
\rightarrow M_\Delta,
\]

并满足：

\[
\boxed{
\dot w
=
G(e_\rho,M_\Delta,w)
}
\]

最简研究近似允许写为：

\[
\dot w
\propto
e_\rho M_\Delta.
\]

但这里的乘积不得实现为：

```python
if e > threshold and M:
    w += constant
```

一类人为通过规则。

必须尽可能沿用已有：

```text
local plasticity
memristive update
conductance/write-current
modulatory gate
```

物理原语。

---

# 4. 两阶段研究策略

本轮严格分成：

## Phase A — Physical Binding

先证明：

\[
Past\rightarrow e
\]

和：

\[
Later\rightarrow M.
\]

不测试最终 memory qualification。

只有 A 成立才进入：

## Phase B — Persistent Deposition

测试：

\[
(e,M)\rightarrow\Delta w.
\]

不得为了让 Phase B PASS 而回头调整 Phase A 的资格定义。

---

# 5. Step 0 — 冻结和版本封存

开工第一步创建：

```text
research/memory_feedback_substrate_v0/
```

production：

```text
READ_ONLY
```

冻结：

```text
G0
D2-0
D2-1
RelationOccurrencePortV1
OccurrencePortV2
g_rel
g_rel2
theta / closure parameters
rearm parameters
existing frozen parent/relation traces
```

对当前使用的：

```text
G0 traces
D2-0 relation traces
D2-1 relation occurrence manifests
lineage records
```

生成 SHA256 seal。

结束后重新计算。

要求：

```text
BEFORE == AFTER
```

否则：

```text
MFS0-INTEGRITY = FAIL
```

---

# 6. Step A — Eligibility Physicalization

构造 research-only：

```text
eligibility_physical.py
```

输入只能来自：

\[
RelationOccurrencePortV1.
\]

使用与当前 D2 typed consumption 同原则的 drive。

禁止：

```text
read RelationCell.x
copy previous membrane residual
use relation ID as state
```

relation occurrence 经物理换能后给 capacitor：

\[
\chi_\rho^{(1)}
\rightarrow
I_e
\rightarrow
C_e.
\]

输出：

\[
e(t)=V_{C_e}(t).
\]

必须测出：

```text
e_peak
t_peak
tau_e
last_step_above_epsilon
query_relevant_window
charge/resource trace
```

必须有对照：

```text
W=1 → e > floor
W=0 → e ≈ baseline
```

并检查：

\[
e(t)\rightarrow0.
\]

如果找不到物理资格载体：

```text
MISSING_PHYSICAL_ELIGIBILITY_BINDING
STOP
```

---

# 7. Step B — Modulation Physicalization

建立：

```text
modulation_physical.py
```

later occurrence：

\[
\Delta
\]

经 typed physical input 进入 modulation path。

要求产生：

\[
M_\Delta(t)
\]

而不是研究脚本直接赋值。

测：

```text
M_peak
tau_M
support interval
baseline
resource/energy where available
```

必须满足：

\[
\Delta=1\Rightarrow M>floor
\]

\[
\Delta=0\Rightarrow M\approx baseline.
\]

并且：

\[
M(t)\rightarrow0.
\]

如果只能靠：

```python
modulation = preset_number
```

运行：

```text
PHYSICAL_MODULATION_ENTRY_NOT_ESTABLISHED
STOP
```

---

# 8. Step C — Persistent Candidate Baseline

在正式做 \(e\times M\) 写入以前，单独审计：

\[
z=w.
\]

确认：

1. \(w\) 是真实内部状态；
2. 改变 \(w\) 会改变 conductance；
3. 外部写入停止以后 \(w\) 不立即回到基线；
4. 相同未来 probe 对不同 \(w\) 产生不同 response；
5. 不存在隐藏 Python cache 参与 readout。

如果：

\[
w_A\neq w_B
\]

但：

\[
Response(Q|w_A)
=
Response(Q|w_B),
\]

则：

```text
PERSISTENT_STATE_CAUSALITY_NOT_ESTABLISHED
```

不继续主实验。

---

# 9. Step D — 冻结时间窗口

先测：

\[
\tau_e,\qquad\tau_M.
\]

然后只冻结两个 later timing：

### NEAR

\[
t_\Delta
\]

位于：

\[
e_W(t)>floor
\]

的合法区间。

### TIMING CONTROL

保持相同 later-event identity、剂量和物理路径，

但令：

\[
e_W(t_\Delta)\approx0.
\]

不得通过更换 later event 强度制造 control。

不得：

```text
shift historical W
change G1 parameters
change relation parameters
increase later-event amplitude until PASS
```

如果当前物理窗口根本不能容纳合法 later event：

```text
ELIGIBILITY_WINDOW_UNREACHABLE
```

并停止，不继续寻找参数漏洞。

---

# 10. Step E — 主 2×2 实验

正式建立：

\[
W\in\{0,1\},
\qquad
\Delta\in\{0,1\}.
\]

四臂：

```text
00 = no past / no later
10 = past only
01 = later only
11 = past + later
```

所有非目标条件：

```text
same initial w
same physical duration
same query
same random seed where applicable
same circuit topology
same frozen parameters
```

记录：

\[
w_{00},w_{10},w_{01},w_{11}.
\]

主结构指标：

\[
\boxed{
I_z
=
(w_{11}-w_{10})
-
(w_{01}-w_{00})
}
\]

要求：

\[
|I_z|>\epsilon_z.
\]

它回答：

> later event 对 persistent state 的作用是否依赖于过去留下的 eligibility。

仅仅：

\[
w_{11}\neq w_{00}
\]

不够。

---

# 11. Washout 硬门

主实验完成以后，不立即 query。

必须首先等待：

\[
e\rightarrow baseline
\]

且：

\[
M\rightarrow baseline.
\]

定义：

\[
t_{washout}
\]

必须基于实测：

\[
\tau_e,\tau_M
\]

而不是任意固定步数。

在：

\[
t\ge t_{washout}
\]

重新读取：

\[
w.
\]

核心要求：

\[
\boxed{
e\approx0,\quad
M\approx0,\quad
w_{11}\neq w_{10}.
}
\]

如果差异只存在于：

```text
eligibility residual
modulator residual
membrane residual
threshold tail
```

则：

```text
PERSISTENT_DEPOSITION = FALSE
```

---

# 12. Step F — Future Query

washout 完成后给所有 arm 完全相同：

\[
Q.
\]

Q 必须来自已有 typed occurrence/reference path。

禁止为 query 新增：

```text
amplitude multiplier
semantic probe
special memory read command
```

至少同时记录：

### Continuous

\[
D_Q^{traj}
=
D(
Response(Q|w_{11}),
Response(Q|w_{10})
).
\]

### Event

如形成 occurrence，则记录：

```text
existence
t_up
t_down
t_rearm
margin
```

Continuous 为主。

Occurrence difference 是强化证据，不是必需条件。

---

# 13. Step G — 状态移植因果门

这是 MFS0-E0 最重要的因果实验。

选：

```text
arm 10
arm 11
```

在 washout 后、query 前：

\[
do(w_{10}\leftarrow w_{11}).
\]

其他状态不得移动。

然后施加完全相同：

\[
Q.
\]

要求：

\[
Response_{10}'
\approx
Response_{11}.
\]

如预算允许再反向：

\[
do(w_{11}\leftarrow w_{10}),
\]

要求 response 随 state 一起反向移动。

如果单独移植 \(w\) 足以关闭未来差异：

```text
MFS0_MINIMAL_SUFFICIENT_STATE_CANDIDATE
STOP_DEEPER_DECOMPOSITION
```

不得继续拆 memristor 内部微态。

---

# 14. Step H — Path Block

第二因果控制：

在 query 前不删除 \(w\)，而物理阻断：

\[
w
\rightarrow
future\ circuit
\]

的有效 conductance contribution。

如果原本：

\[
Response_{11}\neq Response_{10},
\]

阻断后：

\[
Response_{11}^{block}
\approx
Response_{10}^{block},
\]

则进一步支持：

\[
w
\]

确实是未来差异的 causal carrier。

如果 state transplant 强成立而 path block 因结构原因不可解释，不自动 FAIL，但必须登记：

```text
BLOCK_LIMITATION
```

---

# 15. 必须执行的负对照

至少包含：

### NC1 — No Past

\[
W=0,\Delta=1.
\]

验证 later signal 不能单独造成与 11 等价的写入。

### NC2 — No Later

\[
W=1,\Delta=0.
\]

验证 eligibility 本身不能无限自动沉积。

### NC3 — Timing Control

相同：

\[
W,\Delta
\]

但：

\[
e_W(t_\Delta)\approx0.
\]

若仍产生与 NEAR 相同的 \(\Delta w\)，则：

```text
ELIGIBILITY_SELECTIVITY = FAIL
```

### NC4 — Eligibility Path Block

保留 W 与 Δ，但物理阻断：

\[
W\rightarrow e.
\]

要求 persistent write 显著下降或消失。

### NC5 — Modulation Path Block

保留 W 与 Δ，但阻断：

\[
\Delta\rightarrow M.
\]

要求 persistent write 显著下降或消失。

### NC6 — Query Write Freeze

query 期间：

\[
M=0.
\]

要求 query 不重新训练 \(w\)。

读取：

\[
w_{beforeQ}
\]

和：

\[
w_{afterQ}.
\]

必须确认 query 的主要角色是 read，而不是第二次 learning。

---

# 16. MFS0 六门资格

## MFS0-M1 — Typed Historical Entry

\[
\chi_\rho^{(1)}
\]

经合法 typed port 进入 eligibility path。

不得读取父级隐藏微态。

---

## MFS0-M2 — Physical Eligibility

存在真实：

\[
e(t)
\]

有形成、衰减和有限时间常数。

Python trace 不单独算 PASS。

---

## MFS0-M3 — Physical Later Modulation

later occurrence 经真实物理路径形成：

\[
M(t).
\]

不得直接赋常数。

---

## MFS0-M4 — Selective Persistent Deposition

washout 后：

\[
|I_z|>\epsilon_z
\]

且：

\[
e,M\approx0.
\]

即：

\[
Past+Later
\]

产生真正 persistent structural difference。

---

## MFS0-M5 — Future Causal Action

相同未来：

\[
Q
\]

下：

\[
Response(Q|z^+)
\neq
Response(Q|z^-).
\]

---

## MFS0-M6 — State Causality + Integrity

必须至少：

```text
state transplant PASS
```

同时：

```text
frozen upstream SHA unchanged
budget legal
held-out locked
no semantic side channel
no production modification
```

全部满足。

六门全部 PASS 才允许资格化。

---

# 17. Held-out

在 calibration 全部结束后冻结：

```text
tau_e
tau_M
write parameters
timing
query
epsilon
initial w range
all thresholds
```

然后生成：

```text
hold6
```

建议：

```text
3 × W+Δ
3 × matched controls
```

hold 数据第一次执行前：

```text
SHA256 lock
```

禁止根据 hold 结果调参数。

---

# 18. 数值 floor

不得运行以后才定义“明显变化”。

在正式 factorial 之前预注册：

\[
\epsilon_e,
\epsilon_M,
\epsilon_z,
\epsilon_Q.
\]

优先来源：

1. deterministic replay floor；
2. sham-repeat difference；
3. numeric precision；
4. independent no-write controls。

不得按照主实验 effect size 反向设阈值。

---

# 19. 时间单位纪律

项目只有：

\[
t_{phys}.
\]

所有：

```text
eligibility decay
modulator decay
write window
hold
washout
delay
retention
```

必须用：

```text
seconds
```

作为 canonical 参数。

如果底层：

\[
dt=0.001s
\]

则步数只能由：

\[
N=\frac{T}{dt}
\]

派生。

禁止新增：

```text
eligibility_tau_steps
da_tau_steps
memory_window_steps
```

作为 canonical 参数。

旧 step-based STDP 参数只能作为历史参考，不得直接继承。

---

# 20. 计算预算

建议第一轮上限：

```text
eligibility calibration       <= 6
modulation calibration        <= 6
persistent-state calibration  <= 6
timing points                 <= 4
factorial sets                <= 4
timing controls               <= 3
state interventions           <= 4
path blocks                   <= 3
heldout                       = 6
```

所有 attempted run 都计数。

包括：

```text
error
support failure
duplicate
unreachable
aborted run
```

不得通过改名回避预算。

---

# 21. 建议目录

```text
research/memory_feedback_substrate_v0/

    mfs0_common.py
    primitive_audit.py

    eligibility_physical.py
    modulation_physical.py
    persistent_state_audit.py

    calibration.py
    factorial_trials.py
    timing_controls.py

    state_intervention.py
    path_block.py
    heldout_eval.py
    final_qualification.py

    data/
        frozen_upstream_seal.json
        primitive_audit.json
        eligibility_characterization.json
        modulation_characterization.json
        persistent_state_characterization.json
        calibration_ledger.json
        factorial_results.json
        timing_controls.json
        causal_interventions.json
        heldout_manifest.json
        qualification_summary.json
        budget_ledger.json
```

本轮禁止新增 production module。

如果确实需要 adapter，先放：

```text
research/memory_feedback_substrate_v0/
```

资格化以后再讨论迁移。

---

# 22. 终态

## A — 最小基底资格成立

```text
MFS0_PHYSICAL_MEMORY_SUBSTRATE_CANDIDATE_QUALIFIED
```

要求：

```text
MFS0-M1..M6 = PASS
```

允许表述：

> 系统已经存在一个由历史资格、后续物理调制和持久结构状态组成的最小因果记忆基底候选。

不允许表述：

```text
memory solved
learning solved
consolidation solved
Posterior qualified
Xin qualified
cognition
semantic learning
```

---

## B — Eligibility 载体失败

```text
MFS0_PHYSICAL_ELIGIBILITY_NOT_ESTABLISHED
```

即：

\[
Past\not\rightarrow e_{physical}.
\]

---

## C — Modulation 路径失败

```text
MFS0_PHYSICAL_MODULATION_NOT_ESTABLISHED
```

即：

\[
Later\not\rightarrow M_{physical}.
\]

---

## D — 只有瞬态交互

```text
MFS0_PERSISTENT_DEPOSITION_NOT_ESTABLISHED
```

即：

\[
e,M
\]

可以互动，但 washout 后：

\[
z^+=z^-.
\]

这是最接近 Posterior-0 失败类型的终态。

---

## E — 持久变化存在但无未来因果性

```text
MFS0_PERSISTENT_STATE_CAUSALITY_NOT_ESTABLISHED
```

即：

\[
z^+\neq z^-
\]

但：

\[
Response(Q|z^+)
=
Response(Q|z^-).
\]

---

## F — 非选择性写入

```text
MFS0_NONSELECTIVE_OR_ADDITIVE_WRITE_ONLY
```

即 later event 自己就能产生相同写入，或：

\[
I_z\approx0.
\]

这不能叫历史依赖 memory。

---

# 23. 本轮硬停止

只要得到其中任一终态：

```text
A / B / C / D / E / F
```

立即：

```text
STOP
```

不得在同一轮：

```text
增加更多 relation cells
加入 Shadow
恢复旧 DA reward
恢复完整 STDP network
增加 recurrence depth
增加 modality
调 G1 参数
打开 Posterior-1
实现 Xin
```

特别是如果 A 成立：

不要立即进入大型 learning network。

先冻结：

\[
\boxed{
Past\rightarrow e
+
Later\rightarrow M
\rightarrow z
\rightarrow Future
}
\]

作为新的已资格化物理链，再单独设计下一轮。

---

# 24. 如果 A 成立，下一轮才问什么

MFS0-E0 不回答 consolidation。

下一轮才允许问：

\[
\boxed{
\text{一次 persistent deposition 能否被再次修改？}
}
\]

即：

\[
z_0
\xrightarrow{W_1,\Delta_1}
z_1
\xrightarrow{W_2,\Delta_2}
z_2.
\]

到那一步，项目才真正有条件重新讨论：

```text
practice
feedback
memory update
posterior reconstruction
```

甚至更后面的：

```text
Xin
```

而不是现在强行把 Xin 塞进一个线性 RelationCell。

---

# 25. 本方案最终研究判断

当前 G1 已经回答：

\[
\boxed{
\text{关系过程能不能成为新的因果参与者？}
}
\]

答案已经是 YES。

MFS0-E0 只继续追问：

\[
\boxed{
\text{这个因果参与者发生以后，
能不能留下一个短暂的物理修改资格？}
}
\]

以及：

\[
\boxed{
\text{后来发生的事件，
能不能利用这个资格，
把过去沉积为一个持久结构变化？}
}
\]

最终要求不是：

\[
W+\Delta
\rightarrow
\text{different output}
\]

而必须是：

\[
\boxed{
W
\rightarrow e
}
\]

\[
\boxed{
\Delta
\rightarrow M
}
\]

\[
\boxed{
(e,M)
\rightarrow
z^+\neq z^-
}
\]

并且在：

\[
e,M\rightarrow0
\]

之后：

\[
\boxed{
Response(Q|z^+)
\neq
Response(Q|z^-).
}
\]

再通过：

\[
do(z_B\leftarrow z_A)
\]

使未来差异随 \(z\) 一起转移。

只有到这里，才允许登记：

```text
MFS0_PHYSICAL_MEMORY_SUBSTRATE_CANDIDATE_QUALIFIED
```

这就是本轮的全部目标。