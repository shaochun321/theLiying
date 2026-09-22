# MAINLINE V2 — D2-1/P2-C
## 关系发生递归消费与首次 G1 资格
### 第一次真正检验生成深度能否递归

---

# 0. 当前冻结状态

```text
G0_OCCURRENCE_V2_QUALIFIED
D1_SUFFICIENT_FOR_D2

D2_RELATION_PROCESS_V0_QUALIFIED
RELATION_OCCURRENCE_CANDIDATE = YES
READY_FOR_D2-1 = YES

FREEZE G0-CENTRIC MAINLINE
FREEZE D2-0
```

D2-0 已冻结：

```text
g_rel = 0.25
theta_up_rho = 2.6164
rearm_rho = 456 steps
```

并已有：

\[
\chi_\rho^{(1)}
\]

共 9 个。

本轮禁止重新标定：

- RelationCell；
- g_rel；
- relation closure；
- parent site；
- N3；
- 更多自然化候选；
- 更多模态。

---

# 1. 理论建筑地址

当前：

\[
D_0
\rightarrow
D_1
\rightarrow
D_2
\]

已经得到：

\[
\chi^{(0)}
\rightarrow
\mathcal N
\rightarrow
\mathcal C_{\rho_1}
\rightarrow
x_{\rho_1}
\rightarrow
\chi_{\rho_1}^{(1)}.
\]

本轮检验：

\[
\boxed{
\chi_{\rho_1}^{(1)}
\stackrel{?}{\longrightarrow}
\mathcal N_1
\stackrel{?}{\longrightarrow}
\mathcal C_{\rho_2}
}
\]

如果成立，再问：

\[
\boxed{
\chi_{\rho_1}^{(1)}
\text{ 是否已经取得新的生成元资格}
}
\]

---

# 2. 本轮只回答两个问题

## Q1 — Recursive Consumability

能否把：

\[
\chi_\rho^{(1)}
\]

通过与基础 occurrence 相同原则的 typed interface 再次输入新的关系结构？

即：

\[
\chi_\rho^{(1)}
+
\chi_k^{(0)}
\rightarrow
\mathcal C_{\rho_2}
\]

至少必须成立。

---

## Q2 — Generator Qualification

如果递归消费成立，

\[
\chi_\rho^{(1)}
\]

是否真的提供了父层当前最小充分状态无法替代的新状态？

只有 Q1、Q2 都成立，才允许：

```text
G1_CANDIDATE_QUALIFIED
```

甚至进一步裁：

```text
G1_QUALIFIED
```

---

# 3. 新 occurrence 不等于新 generator

本轮继续执行：

\[
\boxed{
\text{new occurrence}
\neq
\text{new generator}
}
\]

D2-0 已经有：

\[
\chi_\rho^{(1)}.
\]

这只能证明：

```text
RELATION_OCCURRENCE_CANDIDATE
```

不能证明：

```text
G1
```

真正的 G1 至少需要：

1. 可再次被消费；
2. 有自己的最小充分状态；
3. 该状态不可由当前父状态完全替代；
4. 对未来真实过程产生可干预的因果差异；
5. 保留 typed port、lineage、resource/ledger。

---

# 4. 输入类型

本轮只使用两类输入。

## Type-A

基础发生：

\[
\chi_k^{(0)}.
\]

继续使用已冻结：

```text
OccurrencePortV2
```

---

## Type-B

关系发生：

\[
\chi_\rho^{(1)}.
\]

新增最薄接口：

```text
RelationOccurrencePortV1
```

最低字段：

```text
occurrence_id
generation_depth = 1
relation_lineage
parent_occurrence_ids
t_up_s
t_down_s
t_rearm_s
raw_relation_track_ref
typed_input_provenance
resource/energy reference
```

不得包含：

```text
is_order
is_direction
relation_type
semantic_label
```

---

# 5. RelationOccurrencePortV1 不读 RelationCell 微观内部态

接口只能读取已经资格化的 relation occurrence 轨迹和谱系。

禁止下一级：

```text
read membrane charge directly
read RelationInputNeuron internal state
read frozen bundle trace
```

除非进入明确的：

```text
DIAGNOSTIC_INTERVENTION
```

实验。

运行接口和研究诊断必须分开。

---

# 6. 自然化原则

D2-0 的：

```text
N1/N2 = REPLAY_REFERENCE_ONLY
N3 = REJECTED
```

全部冻结。

本轮不重新做 N0-N3 比较。

对：

\[
\chi_\rho^{(1)}
\]

只建立最小：

\[
\mathcal N_\rho
\]

使其输出与下一关系结构的输入接口兼容。

优先复用：

\[
\vartheta_\rho(t)
\]

和物理持续时间：

\[
\tau_\rho^{phys}.
\]

如果这已经足够递归消费，就停止。

不新增 N4/N5。

---

# 7. 本轮仍然 Replay-First

当前 N1/N2 尚不是完整 live-causal 版本。

因此本轮：

\[
\boxed{
REPLAY/REFERENCE QUALIFICATION
}
\]

不做 live World→G0→D2→D3 全链。

这不是债务逃避，而是有意隔离问题：

先回答：

\[
\boxed{
\text{生成递归原则上是否存在？}
}
\]

再决定是否值得投入 live causal engineering。

---

# 8. 第一递归实验只做一种组合

主实验：

\[
\boxed{
\chi_\rho^{(1)}
+
\chi_k^{(0)}
}
\]

不要一开始做：

\[
\chi_{\rho_1}^{(1)}
+
\chi_{\rho_2}^{(1)}.
\]

理由：

只要 depth-1 occurrence 连 depth-0 occurrence 都无法共同进入新的 coupling，

就没有必要测试：

\[
1+1.
\]

---

# 9. 主输入选择

固定一个 D2-0 已资格化的 relation occurrence：

\[
\chi_{\rho_a}^{(1)}
\]

作为主 parent。

再配：

\[
\chi_c^{(0)}
\]

来自第三支撑 site23。

这样避免新关系只是重复消费构成：

\[
\rho_a
\]

本身的 site28/site31 parent。

目标结构：

\[
\boxed{
(\chi_{28}^{(0)},\chi_{31}^{(0)})
\rightarrow
\chi_{\rho_a}^{(1)}
}
\]

然后：

\[
\boxed{
\chi_{\rho_a}^{(1)}
+
\chi_{23}^{(0)}
\rightarrow
\mathcal C_{\rho_2}.
}
\]

---

# 10. 下一关系结构不得复制 D2-0 参数

结构模板可以复用。

但是：

\[
\mathcal C_{\rho_2}
\]

是新的物理实例。

禁止直接复制：

```text
theta_up = 2.6164
rearm = 456
```

作为资格参数。

允许复用：

```text
RelationInputNeuron
frozen SynapticBundle
RelationCell architecture
```

但必须重新测最小：

```text
alive
silent
saturation
decay
closure boundary
```

只做 adaptive boundary search。

---

# 11. 递归消费最低资格

要声明：

```text
RELATION_OCCURRENCE_RECONSUMABLE
```

必须满足：

### RC-1 Typed acceptance

\[
\chi_\rho^{(1)}
\]

不经手工解包或语义判断即可进入 adapter。

### RC-2 Physical transduction

必须重新经过：

\[
\mathcal N_\rho
\rightarrow
RelationInputNeuron
\rightarrow
FrozenBundle
\rightarrow
RelationCell_2.
\]

### RC-3 Stateful response

下一级：

\[
x_{\rho_2}
\]

产生真实内部状态。

### RC-4 Parent dependence

阻断：

\[
\chi_\rho^{(1)}
\]

会改变：

\[
x_{\rho_2}.
\]

### RC-5 Finite closure

如果形成：

\[
\chi_{\rho_2}^{(2)},
\]

必须有自己的：

\[
t^\uparrow,t^\downarrow,t^{rearm}.
\]

---

# 12. 最重要负对照：降深替换

构造：

### Full condition

\[
\chi_\rho^{(1)}
+
\chi_{23}^{(0)}
\rightarrow
\mathcal C_{\rho_2}.
\]

然后替换：

\[
\chi_\rho^{(1)}
\]

为它的原始父输入：

\[
\chi_{28}^{(0)},\chi_{31}^{(0)}.
\]

即：

\[
(\chi_{28}^{(0)},\chi_{31}^{(0)})
+
\chi_{23}^{(0)}.
\]

如果后者可以完全重构前者所有未来：

\[
x_{\rho_2}^{depth1}
\equiv
x_{\rho_2}^{parents},
\]

则：

```text
DEPTH_COLLAPSE
```

本轮不得宣称新生成深度。

---

# 13. A8-v2 在这里正式成为 G1 核心门

设父层当前最小充分状态：

\[
P.
\]

关系候选状态：

\[
Z_\rho.
\]

构造 twin：

\[
P_A(t_0)=P_B(t_0)
\]

但：

\[
Z_{\rho,A}(t_0)
\neq
Z_{\rho,B}(t_0).
\]

然后给完全相同未来输入：

\[
U_A^+=U_B^+.
\]

若：

\[
Future_A\neq Future_B,
\]

说明：

\[
P
\]

不是充分状态。

再做干预：

\[
Z_{\rho,B}
\leftarrow
Z_{\rho,A}.
\]

如果：

\[
Future_B'
\approx
Future_A,
\]

则登记：

```text
G1_STATE_DIMENSION_CAUSALLY_SUPPORTED
```

---

# 14. 什么叫父状态 P

禁止使用“所有过去历史”作为 P。

P 是：

\[
\boxed{
\text{当前时刻父层最小充分状态候选}
}
\]

至少包括：

- 当前有效 \(\chi^{(0)}\) 接口状态；
- 当前 parent support；
- 当前必要 physical resource state；
- 已被先前实验证明必须保留的状态。

不允许用无限历史回放把所有差异都解释掉。

---

# 15. Full-history reconstructibility 不自动否决 G1

即使：

\[
Z_\rho(t)
\]

可以通过完整历史：

\[
\Gamma_{-\infty:t}
\]

重新算出来，

也不能因此否定新状态。

真正的判据是：

\[
\boxed{
\text{当前父层最小充分状态能否关闭未来}
}
\]

而不是：

\[
\text{完整历史能否离线重放}.
\]

这是此前 A8-v2 的关键纪律。

---

# 16. 第二个核心门：未来行为作用

即使：

\[
Z_\rho
\]

是不可约状态，

如果它不影响任何未来可达过程，

仍不能取得最终 G1 资格。

做：

\[
\Gamma_{\rm with,\rho}^{+}
\]

对比：

\[
\Gamma_{\rm blocked,\rho}^{+}.
\]

要求：

\[
\boxed{
\Gamma_{\rm with,\rho}^{+}
\not\sim
\Gamma_{\rm blocked,\rho}^{+}
}
\]

差异至少体现在：

- 下一 relation trajectory；
- closure；
- reachable state；
- physical resource path；

之一。

---

# 17. 不能以 parameter difference 当成新状态

如果：

\[
Z_\rho
\]

只是：

```text
fixed parameter
site id
delay constant
gain constant
```

则不能作为新生成元状态。

必须是：

\[
\boxed{
\text{运行过程中形成、持续并可改变未来的动态状态}
}
\]

---

# 18. 四个主要实验

本轮只做四组。

## E1 — Recursive acceptance

验证：

\[
\chi_\rho^{(1)}
+
\chi_{23}^{(0)}
\]

能驱动：

\[
x_{\rho_2}.
\]

---

## E2 — Depth-collapse attack

用原 parent occurrence 替代：

\[
\chi_\rho^{(1)}.
\]

检查未来是否完全可替代。

---

## E3 — A8-v2 twin

当前父状态相同、relation state 不同、未来输入相同。

检查：

\[
Future_A\neq Future_B.
\]

然后 relation-state intervention。

---

## E4 — With/Block future action

保留/阻断 relation state，

比较后续真实关系过程。

---

# 19. 可选 E5：1+1 递归

只有 E1-E4 全部通过后，才允许一次：

\[
\chi_{\rho_a}^{(1)}
+
\chi_{\rho_b}^{(1)}
\rightarrow
\mathcal C_{\rho_3}.
\]

它只是加固证据。

不是 G1 资格必要条件。

如果预算不足可以不做。

---

# 20. Hidden Dynamics 直接复用

如果 E3 未来仍然分叉，但当前候选：

\[
Z_\rho
\]

无法完全解释，

按旧五步：

\[
same\ visible
\rightarrow
different\ future
\rightarrow
probe
\rightarrow
intervention
\rightarrow
STOP/deepen.
\]

最多 4 次 intervention。

一旦找到：

\[
P^*=(P,Z_\rho)
\]

能够关闭未来：

```text
STOP_DEEPER_DECOMPOSITION
```

---

# 21. 本轮禁止 Posterior Construction

即使发现历史状态：

\[
Z_\rho,
\]

也不立即做：

\[
\mathfrak B_{\Delta\Gamma}^{W}.
\]

Posterior-0 只在：

```text
G1_QUALIFIED
```

以后开启。

否则我们连可递归生成元都还没确认，就没有稳定对象讨论后验重组织。

---

# 22. 计算预算

本轮应该比 D2-0 更轻。

```text
new G0 physical trajectories <= 8
depth-1 relation replays <= 16
relation-2 calibration points <= 10
A8 twins <= 4
state interventions <= 4
held-out <= 6
```

优先复用 D2-0 cache。

禁止重新生成全部 22 条 parent trace。

---

# 23. 参数搜索

继续执行：

```text
canonical
→ lower fail
→ upper fail
→ bracket
→ minimal refinement
```

不得二维全网格。

新的 RelationCell_2 参数只求：

```text
legal working region
```

不求 optimal。

---

# 24. Held-out

如果 E1-E4 calibration 成立，

再冻结：

```text
hold6
```

覆盖：

- 未见 relation duration；
- 未见 relative timing；
- site23 dose variant；
- weak relation occurrence；
- stronger relation occurrence；
- one structural-no-relation case。

先 SHA256，

后运行，

零回调。

---

# 25. 六门

## D21-M1 — Recursive Port

\[
\chi_\rho^{(1)}
\]

可通过 typed port 重新进入关系结构。

---

## D21-M2 — Physical Recursion

下一级状态：

\[
x_{\rho_2}
\]

由真实换能/Bundle/Cell 产生。

---

## D21-M3 — Depth Non-Collapse

不能由当前父层接口状态无损替代：

\[
\chi_\rho^{(1)}.
\]

---

## D21-M4 — A8-v2 Irreducibility

同父当前状态、异 \(Z_\rho\)、同未来输入 ⇒ 异未来；

移植 \(Z_\rho\) 后差异消失。

---

## D21-M5 — Future Causal Action

保留/阻断 relation state：

\[
\Gamma_{\rm with}^{+}
\not\sim
\Gamma_{\rm blocked}^{+}.
\]

---

## D21-M6 — Held-out / Replay / Ledger

hold6 不结构性崩溃；

lineage、resource、replay 均可审计。

---

# 26. G1 最终定义

只有六门全部通过：

```text
G1_QUALIFIED
```

才允许登记。

其含义非常有限：

> 当前项目已经证明，一个由多个 depth-0 occurrence 形成的 relation process，可以形成自己的 occurrence，重新进入更深 coupling，并携带一个当前父层最小充分状态无法替代、且能改变未来过程的动态状态。

它不代表：

- 高层认知；
- 抽象概念；
- world model；
- intelligence；
- stable representation。

---

# 27. 如果只有递归，没有不可约状态

如果：

```text
M1 PASS
M2 PASS
M3 FAIL
```

或：

```text
M4 FAIL
```

终态：

```text
RELATION_RECURSION_ENGINEERING_PASS
G1_NOT_QUALIFIED
```

这和此前 TSS 的经验一样：

\[
\boxed{
\text{recursion}
\neq
\text{new generator}
}
\]

---

# 28. 如果不可约但无未来作用

如果：

```text
M4 PASS
M5 FAIL
```

终态：

```text
G1_STATE_CANDIDATE
BEHAVIOR_OPERATOR_NOT_QUALIFIED
```

不继续强推。

---

# 29. 最终状态只允许四种

## A

```text
D2_1_RECURSIVE_GENERATION_QUALIFIED
G1_QUALIFIED
READY_FOR_POSTERIOR_0
```

---

## B

```text
RELATION_RECURSION_ENGINEERING_PASS
G1_NOT_QUALIFIED
```

---

## C

```text
G1_STATE_CANDIDATE
FUTURE_CAUSAL_ACTION_NOT_MET
```

---

## D

```text
RELATION_OCCURRENCE_NOT_RECONSUMABLE
```

---

# 30. 终态 A 后的硬停止

一旦：

```text
G1_QUALIFIED
```

禁止：

```text
D2-1b
G1-v2
more relation cells
more sites
more modalities
large recursive sweep
```

下一阶段直接：

\[
\boxed{
Posterior\ Construction\text{-}0
}
\]

---

# 31. Posterior-0 的预登记

只有终态 A 后才开启：

后续真实物理发生：

\[
\Delta\Gamma^{phys}
\]

进入同一网络，

观察它是否改变已有：

\[
\chi_\rho^{(1)}
\]

的当前组织投影或未来作用。

检验：

\[
\mathfrak B_{\Delta\Gamma}^{W}
\neq id.
\]

本轮不实现。

---

# 32. 代码范围

建议：

```text
research/d2_recursive_v1/
```

包含：

```text
dataset_builder.py
relation_occurrence_port.py
recursive_adapter.py
recursive_trials.py
a8v2_attack.py
future_action_attack.py
heldout_eval.py
final_qualification.py
```

production：

原则上零修改。

只有当：

\[
RelationOccurrencePortV1
\]

需要最薄 adapter 时，允许扩展：

```text
tss/adapters/
```

---

# 33. 数据输出

```text
relation_occurrence_manifest.csv
recursive_trials.csv
depth_collapse_attack.csv
a8v2_twins.csv
state_interventions.csv
future_action_attack.csv
recursive_heldout.csv
qualification_summary.json
```

---

# 34. 报告输出

只生成：

```text
D2_1_RECURSION_REPORT.md
D2_1_G1_QUALIFICATION_REPORT.md
D2_1_NEGATIVE_RESULTS.md
D2_1_FINAL_RULING.md
```

---

# 35. 最终首屏必须回答

1. \(\chi_\rho^{(1)}\) 能否再次被消费？
2. 是否真的进入物理 RelationCell_2？
3. 有没有生成 \(\chi_{\rho_2}^{(2)}\)？
4. 用 depth-0 parents 替代 depth-1 occurrence 后能否完全重构结果？
5. 当前父状态相同而 relation state 不同时，未来是否不同？
6. relation-state transplant 是否关闭未来差异？
7. relation state 被阻断后，未来过程是否改变？
8. hidden state 最小充分候选是什么？
9. 是否触发 STOP_DEEPER_DECOMPOSITION？
10. hold6 是否一次通过？
11. 最终是递归工程 PASS，还是 G1 真正 QUALIFIED？
12. 是否允许进入 Posterior-0？

---

# 36. 本轮真正的成功标准

不是：

\[
R+R\rightarrow R'
\]

成立。

真正成功必须是：

\[
\boxed{
\text{一个由父发生形成的关系过程，
能够作为新的发生再次进入生成，
并携带父层当前状态无法替代的未来因果状态。}
}
\]

---

# 37. 一句话目标

\[
\boxed{
\text{这一次不再证明“关系可以继续组合”，
而是证明“关系本身已经成为新的生成元”。}
}
\]