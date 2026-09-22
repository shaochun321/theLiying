# MAINLINE V2 — Posterior Construction-0
## 既有 G1 状态的后验重组织资格
### 从“递归生成”进入第一次“后验构建”

---

# 0. 当前冻结起点

当前已接受：

```text id="6mlizg"
D2_1_RECURSIVE_GENERATION_QUALIFIED
G1_QUALIFIED
READY_FOR_POSTERIOR_0
```

D2-1 已证明：

\[
\chi_\rho^{(1)}
+
\chi^{(0)}
\rightarrow
\chi_{\rho_2}^{(2)}
\]

可以成立，而且 relation state：

1. 无法由当前父层接口状态直接替代；
2. 能改变未来 occurrence 是否发生；
3. 状态移植后未来差异消失。

本轮不得重新证明 G1。D2-1 已明确硬停止，并把 Posterior Construction-0 登记为唯一下一阶段。

冻结：

```text id="k8agvt"
G0 = READ_ONLY
D2-0 = READ_ONLY
D2-1 = READ_ONLY

g_rel2 = READ_ONLY
theta_2 = READ_ONLY
rearm_2 = READ_ONLY

NO G1-v2
NO extra relation cells
NO new modality
NO larger recursive sweep
```

---

# 1. 本轮只问一个问题

假设过去窗口：

\[
W
\]

已经真实形成一个资格化的关系状态：

\[
Z_W.
\]

在它完成以后，又出现一个真实的后续事件：

\[
\Delta\Gamma^{phys}.
\]

问：

\[
\boxed{
\Delta\Gamma^{phys}
\text{ 能否改变系统当前保存的 }Z_W
\text{ 及其未来作用？}
}
\]

不是修改过去发生过什么。

而是：

\[
\boxed{
\text{后来的事件能否重新组织“过去在当前系统中的存在方式”。}
}
\]

---

# 2. 绝对禁止的伪 Posterior

下面全部不算：

```text id="3tmbv7"
if later_event:
    old_relation_label = new_label
```

不算：

```text id="012dld"
rewrite historical CSV
```

不算：

```text id="gnazem"
offline recompute old score
```

不算：

```text id="p475rw"
analyst says old event now means something different
```

Posterior 必须是：

\[
\boxed{
\text{后续真实输入}
\rightarrow
\text{同一物理网络}
\rightarrow
\text{当前既有状态发生真实改变}
}
\]

---

# 3. 过去必须保持不可修改

原窗口：

\[
W
\]

的：

- raw track；
- occurrence boundaries；
- lineage；
- energy record；
- SHA256；

全部：

```text id="u9be3i"
IMMUTABLE
```

Posterior 后：

\[
W_{\rm raw}^{before}
=
W_{\rm raw}^{after}
\]

必须逐字节成立。

改变的是：

\[
Z_W(t)
\]

而不是历史文件。

---

# 4. 第一个硬门：必须先确认“过去还留着什么”

这是本轮最重要的 Step A。

D2-1 找到的 G1 状态载体是：

\[
Z_\rho
=
\text{RelationCell membrane state}.
\]

但还不知道在 relation occurrence 完成并 rearm 后，它是否仍保存可调用的历史残余。

所以先做：

\[
\boxed{
POSTERIOR\_SUBSTRATE\_AUDIT
}
\]

选一个已经资格化的：

\[
\chi_{\rho_2}^{(2)}.
\]

等待：

\[
t>t_{rearm}.
\]

此时要求：

```text id="f9oumr"
original occurrence = CLOSED
physical support = OFF
external drive = ZERO
```

然后检查：

\[
Z_W(t_{rearm}^{+}).
\]

---

# 5. 如果 rearm 后历史已经完全消失

如果：

\[
Z_W(t_{rearm}^{+})
\]

已经与：

\[
Z_{\varnothing}
\]

不可区分，

而且相同 probe 后未来也一样，

直接终止：

```text id="4f4x50"
POSTERIOR_SUBSTRATE_ABSENT
```

本轮 FAIL，但这是有效负结果。

禁止因此临时增加：

- memory cell；
- STDP；
- DA；
- Shadow；
- latch；
- 新 persistence mechanism。

因为那会把：

> “系统目前没有 posterior substrate”

改造成：

> “为了让 Posterior 成立而造一个 substrate”。

这两者不能混淆。

---

# 6. Posterior 时间必须在旧 occurrence 完整结束以后

本轮强制：

\[
\boxed{
t_{\Delta}
>
t_{rearm,W}
}
\]

而不是只：

\[
t_{\Delta}>t_{\downarrow,W}.
\]

原因：

如果后续事件发生在旧 occurrence 的 recovery 期间，

很容易只是同一次过程的继续。

本轮要测试真正：

\[
\boxed{
\text{closed past}
+
\text{later event}.
}
\]

---

# 7. 本轮继续 Replay-First

D2-1 当前资格仍是：

```text id="in3qdn"
REPLAY/REFERENCE QUALIFICATION
```

因为自然化 phase 使用完整 occurrence 的 `t_rearm`。

因此 Posterior-0 也沿用：

\[
\boxed{
REPLAY/REFERENCE
}
\]

本轮不解决：

```text id="8smzqu"
CAUSAL_VARIANT_REQUIRED_BEFORE_LIVE_D2
```

这一遗留问题。

Posterior 原理先成立，再谈 live 化。

---

# 8. 不增加新 site

优先全部复用已有：

```text id="jviwud"
site28
site31
site23
```

以及现有：

```text id="vl7tdl"
depth-0 traces
depth-1 relation traces
depth-2 relation traces
```

如果现有 site23 trace 已足以构造 posterior event：

```text id="wj1hzv"
NEW_PHYSICAL_G0_TRAJECTORIES = 0
```

只有时间位置不够时，最多补：

\[
4
\]

条 site23 真实 G0 trajectory。

---

# 9. 后续事件 ΔΓphys 的身份

第一轮不赋予任何语义。

禁止：

```text id="ezmf4z"
confirmation
contradiction
reward
punishment
evidence
```

只叫：

\[
\boxed{
\Delta_A
}
\]

和必要时：

\[
\Delta_B.
\]

它们只是：

> 在旧 relation occurrence 已 rearm 后进入同一网络的合法物理 occurrence。

---

# 10. 最小 Posterior 实验必须是 2×2

这是本轮核心设计。

两个条件：

### Past

\[
W=1
\]

有先前 G1 relation history。

\[
W=0
\]

没有该 prior relation，但时间、基线、资源尽量匹配。

### Later event

\[
\Delta=1
\]

有 posterior event。

\[
\Delta=0
\]

sham。

所以四臂：

\[
(W,\Delta)
=
(0,0),(1,0),(0,1),(1,1).
\]

---

# 11. 为什么必须做 2×2

只比较：

\[
W
\quad vs\quad
W+\Delta
\]

不够。

因为那只能说明：

> 新输入改变了系统。

任何动态系统都会这样。

真正 Posterior 要求：

\[
\Delta
\]

对系统的作用取决于：

\[
W
\]

是否曾经存在。

定义：

\[
Y_{11}=Y(W=1,\Delta=1)
\]

\[
Y_{10}=Y(W=1,\Delta=0)
\]

\[
Y_{01}=Y(W=0,\Delta=1)
\]

\[
Y_{00}=Y(W=0,\Delta=0).
\]

定义 posterior interaction：

\[
\boxed{
I_W
=
(Y_{11}-Y_{10})
-
(Y_{01}-Y_{00})
}
\]

如果：

\[
I_W=0,
\]

说明 later event 只是普通加法作用。

如果：

\[
I_W\neq0,
\]

说明 later event 的作用依赖 prior history。

---

# 12. Posterior 不要求直接读取“意义”

本轮测量：

\[
Y
\]

只允许是：

- relation state trajectory；
- query response；
- occurrence existence；
- occurrence timing；
- reachable state；
- resource path。

不定义：

```text id="ou4smo"
meaning
belief
interpretation
truth
```

这些词本轮禁止进入代码。

---

# 13. 最关键测量：washout 后再 probe

Posterior event：

\[
\Delta
\]

结束以后，

必须先进入：

```text id="5iov9n"
ZERO EXTERNAL DRIVE
```

等待固定 washout。

然后四组系统当前外部输入再次完全相同。

这时施加同一个：

\[
Q
\]

standardized query probe。

比较：

\[
Response_Q(W,\Delta).
\]

如果差异只在 \(\Delta\) 输入期间存在，

输入一停就完全消失，

那只是普通响应。

不能叫 posterior reorganization。

---

# 14. Query probe Q

优先从已经冻结的弱输入中选择。

要求：

1. 单独 Q 不产生大规模 saturation；
2. 四臂使用逐位相同 Q；
3. Q 不参与 calibration；
4. Q 自己不是 semantic query。

它只是：

> 一个标准化的物理探针，观察当前状态对未来输入的响应。

最强结果是：

\[
occ_Q:
0\rightarrow1
\]

或：

\[
1\rightarrow0.
\]

但轨迹/边界显著改变也可接受。

---

# 15. Posterior 三层资格

本轮把结果分成三层。

### P0 — Immediate response

\[
\Delta
\]

输入期间状态不同。

只算普通输入响应。

---

### P1 — Persistent state change

\[
\Delta
\]

结束、外部输入归零以后：

\[
Z_{11}\neq Z_{10}.
\]

说明留下状态。

---

### P2 — Prior-dependent reorganization

并且：

\[
I_W\neq0.
\]

即：

\[
\Delta
\]

留下的作用依赖过去 \(W\)。

只有 P2 才是 Posterior candidate。

---

# 16. 第一个负对照：Later-event-only

比较：

\[
Y_{01}-Y_{00}.
\]

如果：

\[
Y_{11}-Y_{10}
\]

与：

\[
Y_{01}-Y_{00}
\]

完全一样，

则：

```text id="52ssfa"
POSTERIOR_EFFECT_ADDITIVE_ONLY
```

这是普通新记忆，

不是过去状态的后验重组织。

---

# 17. 第二个负对照：History-only

比较：

\[
Y_{10}-Y_{00}.
\]

它测的是：

> 过去 \(W\) 自己残留多少。

Posterior 效应不能仅仅等于：

\[
history\ residual.
\]

必须有：

\[
W\times\Delta
\]

interaction。

---

# 18. 第三个负对照：同剂量错时 Δ

构造：

\[
\Delta_{\rm timing-control}
\]

保持：

- 总输入剂量；
- duration；
- amplitude；

近似相同，

只改变相对于 prior state 的时序。

如果所有时序效果都一样，

则可能只是总能量叠加。

如果存在时间窗：

\[
I_W(\delta t)
\]

明显变化，

才支持真实 state-dependent interaction。

---

# 19. 后验时间窗

禁止大网格。

只测：

\[
\delta t
=
\{1,2,4\}\times\tau_{\rm residual}
\]

或根据 substrate audit 自适应选 3 点：

```text id="ijdm33"
near
middle
far
```

找到：

```text id="toqe89"
interaction alive
→ boundary
→ interaction gone
```

即可停止。

不寻找“最佳 posterior timing”。

---

# 20. 最重要的因果实验：阻断 posterior 路径

如果：

\[
I_W\neq0
\]

必须做：

\[
\Delta
\]

保持存在，

但阻断它进入：

\[
Z_W
\]

的物理通路。

例如合法阻断：

```text id="y4y9ep"
posterior input bundle disabled
```

而不是改数据。

若：

\[
I_W
\rightarrow0,
\]

登记：

```text id="xdkzps"
POSTERIOR_PATH_CAUSALLY_SUPPORTED
```

---

# 21. 状态移植实验

如果找到了 posterior 后状态：

\[
Z_{11},
Z_{10},
\]

做：

\[
Z_{10}
\leftarrow
Z_{11}.
\]

然后施加完全相同的 query：

\[
Q.
\]

如果：

\[
Response_{10}'
\approx
Response_{11},
\]

说明该当前状态确实承载 posterior effect。

找到足够低维状态后：

```text id="bo6bx9"
STOP_DEEPER_DECOMPOSITION
```

不继续拆元件微态。

---

# 22. 一个非常重要的区分

如果：

\[
\Delta
\]

只是建立自己的新状态：

\[
Z_\Delta
\]

而原：

\[
Z_W
\]

完全不受影响，

但最终 query 因 \(Z_\Delta\) 不同而不同，

那么只能登记：

```text id="yltxwn"
PARALLEL_NEW_STATE
```

不能叫：

```text id="5dx80t"
POSTERIOR_REORGANIZATION
```

---

# 23. 如何证明“旧关系本身被改变”

定义 prior-conditioned readout：

\[
H_W
=
\mathcal P_W[Z].
\]

这里：

\[
\mathcal P_W
\]

不是语义解释器。

它只是固定的、预注册的历史状态投影，例如：

- 原 relation carrier state；
- 相同 lineage probe response；
- 原关系重放后的 response；
- relation-state component identified by intervention。

然后定义：

\[
H_W^-
=
\mathcal P_W[Z(t_\Delta^-)]
\]

和：

\[
H_W^+
=
\mathcal P_W[Z(t_{query})].
\]

Posterior candidate 要求：

\[
\boxed{
H_{W,\Delta}^+
\neq
H_{W,sham}^+
}
\]

并有物理干预支持。

---

# 24. 后验算子的第一版定义

只有实验通过后，才允许记：

\[
\boxed{
\mathfrak B_{\Delta\Gamma}^{W}
:
H_W
\mapsto
H'_W
}
\]

其中：

\[
H'_W
=
\mathfrak B_{\Delta\Gamma}^{W}(H_W).
\]

非平凡条件：

\[
\boxed{
\mathfrak B_{\Delta\Gamma}^{W}
\neq id
}
\]

具体操作化为：

\[
\|H'_W-H_W^{sham}\|
>
\epsilon_{\rm replay}
\]

并且：

1. interaction \(I_W\neq0\)；
2. posterior path block 消除效应；
3. state transplant 重建效应；
4. past raw record 不变。

---

# 25. 暂时不要叫 Xin

即使：

\[
\mathfrak B_{\Delta\Gamma}^{W}\neq id
\]

也只登记：

```text id="42ra71"
POSTERIOR_OPERATOR_CANDIDATE
```

禁止：

```text id="sgirv5"
Xin = QUALIFIED
```

只有多个不同：

\[
W,\Delta\Gamma
\]

重复出现同一类后验变换，

Posterior-1 才允许开始：

```text id="d130m6"
OPERATOR_FAMILY_EXTRACTION
```

之后再讨论 Xin 是否对应其中某类。

---

# 26. 六门资格

## PC0-M1 — Closed History Substrate

旧 occurrence 已：

```text id="1ze0yy"
t > t_rearm
```

仍存在可调用的 prior-conditioned state。

---

## PC0-M2 — Physical Posterior Entry

\[
\Delta\Gamma^{phys}
\]

经过正常 typed/physical path 进入同一网络。

无 direct state write。

---

## PC0-M3 — Persistent Effect

posterior event 结束、washout 后：

\[
Z_{11}\neq Z_{10}.
\]

---

## PC0-M4 — Non-Additive History Interaction

\[
\boxed{
I_W
=
(Y_{11}-Y_{10})
-
(Y_{01}-Y_{00})
\neq0
}
\]

超过 replay/numerical floor。

---

## PC0-M5 — Causal Reorganization

posterior path block：

\[
I_W\rightarrow0.
\]

状态移植：

\[
Response'
\rightarrow
Response_{posterior}.
\]

---

## PC0-M6 — Immutable Past + Held-out

历史 raw record SHA 不变。

hold 一次通过。

replay / lineage / ledger 合法。

---

# 27. Held-out

只做：

```text id="b18gvg"
hold6
```

覆盖：

1. 未见 posterior timing；
2. 未见 posterior duration；
3. 未见 dose；
4. weak posterior event；
5. strong posterior event；
6. structurally-no-posterior condition。

先：

\[
SHA256
\]

冻结，

再跑一次，

零回调。

---

# 28. 参数与阈值纪律

不得调：

```text id="1iomc7"
g_rel2
theta_2
rearm_2
G1 state parameters
```

Posterior-0 只允许标定：

- posterior event timing；
- query probe scale；
- washout duration；

而且 query scale 必须在 hold lock 前冻结。

禁止为了得到 interaction 去改 G1 参数。

---

# 29. 数值判据

系统当前是高度确定性的。

因此 numerical floor 首先由：

```text id="p9schc"
same replay × same input
```

估计。

定义：

\[
\epsilon_{num}
=
\max(
10\times\epsilon_{replay},
10^{-6}
)
\]

对于 normalized trajectory metric。

要求：

\[
\|I_W\|
>
\epsilon_{num}.
\]

如果达到 occurrence existence：

\[
0\leftrightarrow1
\]

则作为更强证据单独登记。

---

# 30. 计算预算

本轮预算建议：

```text id="zxmr7d"
new G0 physical trajectories <= 4
prior-state replays <= 12
posterior timing points <= 4
2x2 factorial sets <= 4
state interventions <= 4
path blocks <= 3
held-out = 6
```

超过预算必须登记：

```text id="wep7rp"
EXPECTED_NEW_INFORMATION
```

否则停止。

---

# 31. 代码范围

新建：

```text id="wk346s"
research/posterior_v0/
```

建议：

```text id="vsz0j6"
p0_common.py
substrate_audit.py
dataset_builder.py
posterior_trials.py
interaction_analysis.py
posterior_path_block.py
state_intervention.py
heldout_eval.py
final_qualification.py
```

production：

\[
\boxed{
0\text{ modifications preferred}
}
\]

如果确实需要新 typed record，

先放 research。

Posterior-0 PASS 后才考虑 production port。

---

# 32. 数据输出

```text id="dtx24y"
prior_state_manifest.csv
posterior_event_manifest.csv
posterior_factorial_trials.csv
posterior_interaction.csv
posterior_timing_window.csv
posterior_path_block.csv
posterior_state_intervention.csv
posterior_heldout.csv
qualification_summary.json
```

---

# 33. 报告输出

只生成四份：

```text id="j89bwd"
POSTERIOR0_STATE_REPORT.md
POSTERIOR0_CAUSAL_INTERACTION_REPORT.md
POSTERIOR0_NEGATIVE_RESULTS.md
POSTERIOR0_FINAL_RULING.md
```

不额外生成大量重复说明文档。

---

# 34. 最终状态只允许四种

## A

```text id="kpi1nx"
POSTERIOR_STATE_REORGANIZATION_V0_QUALIFIED
POSTERIOR_OPERATOR_CANDIDATE = YES
READY_FOR_POSTERIOR_1 = YES
```

---

## B

```text id="zjeoiw"
POSTERIOR_SUBSTRATE_ABSENT
```

旧 occurrence rearm 后没有可调用历史状态。

---

## C

```text id="yu7bpu"
POSTERIOR_EFFECT_ADDITIVE_ONLY
```

later event 有作用，但：

\[
I_W=0.
\]

只是新状态叠加。

---

## D

```text id="jkfyp2"
POSTERIOR_CAUSAL_REORGANIZATION_NOT_ESTABLISHED
```

观察到 interaction，但 causal block / transplant 不能确认。

---

# 35. 终态 A 后也必须停止

如果：

```text id="5qs3fe"
POSTERIOR_STATE_REORGANIZATION_V0_QUALIFIED
```

成立：

立即冻结 Posterior-0。

禁止：

```text id="esmmc4"
Posterior-v2
more sites
new modality
STDP
DA
Shadow
Xin implementation
TOPRXin integration
large timing sweep
```

下一步才是：

\[
\boxed{
Posterior\text{-}1:
\text{跨多个 }W,\Delta\Gamma
\text{ 提取重复出现的后验算子族}
}
\]

---

# 36. 本轮最重要的失败也很有价值

如果终态 B：

\[
POSTERIOR\_SUBSTRATE\_ABSENT,
\]

它会告诉我们：

> 当前 G1 虽然能够递归生成，但 closure/rearm 后没有保存足够长的历史状态，因此还没有真正意义上的后验重组织基础。

这会是一个非常重要的结构性结果。

不能视作项目失败。

它意味着未来必须先回答：

\[
\boxed{
\text{历史究竟沉积在哪里？}
}
\]

而不是提前把 Shadow 或 Xin 塞回来。

---

# 37. 最终首屏必须回答

1. 旧 G1 occurrence 在 \(t>t_{rearm}\) 后是否仍有 causal history substrate？
2. posterior event 是否通过正常物理路径进入？
3. past raw record 是否逐字节不变？
4. \(\Delta\) 单独会产生什么？
5. \(W\) 单独会留下什么？
6. \(W+\Delta\) 是否超过简单相加？
7. interaction \(I_W\) 是多少？
8. washout 后 interaction 是否仍存在？
9. standardized query 是否改变？
10. posterior path block 是否消除效应？
11. state transplant 是否重建效应？
12. 找到的最小充分 posterior carrier 是什么？
13. 是否触发 STOP_DEEPER_DECOMPOSITION？
14. hold6 是否一次通过？
15. 最终是 A/B/C/D 哪一态？
16. 是否第一次得到：

\[
\mathfrak B_{\Delta\Gamma}^{W}\neq id
\]

的物理证据？

---

# 38. 一句话目标

\[
\boxed{
\text{不是证明“后来又发生了一件事”，
而是证明“后来发生的事真正改变了过去关系在当前系统中的组织和未来作用”。}
}
\]