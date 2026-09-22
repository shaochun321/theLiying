# MAINLINE V2 — G0-R0
## 统一物理时间与多率回接
### Agent 执行方案

---

# 0. 阶段定位

当前状态：

```text
TSS = FROZEN
WT0 = CLOSED
T1-A = CLOSED
W1 = WORLD_V2_RAW_QUALIFIED
T1-B = TRANSDUCTION_LAYER_QUALIFIED
A_LONG_TERM_PORT = QUALIFIED
B_RATE_PORT = QUALIFIED
```

但保留：

```text
G0_MULTIRATE_TIMEBASE_CONTRACT = REQUIRED
B_TO_G0_BRIDGE = NOT_YET_PHYSICALLY_QUALIFIED
```

本轮只解决：

\[
\boxed{
World/Boundary
\rightarrow
D_{v2}
\rightarrow
G_0
}
\]

在**同一物理时间轴**上的调度问题。

本轮不重新研究：

```text
World
Transduction architecture
TSS
NaturalUnit
Scale
higher generation
```

---

# 1. 核心问题

当前已冻结：

\[
\Delta t_{\rm ext}=1\,s
\]

作为 World/Boundary 的外部物理采样步。

同时现有 G0/神经元内部大量代码仍使用：

\[
\Delta t_G=0.001\,s.
\]

因此不能简单继续：

```text
1 boundary sample
→ 1 generator step
```

否则：

\[
1\,s
\]

的 World 时间只推进：

\[
1\,ms
\]

的神经动力学。

本轮必须正式解决：

\[
\boxed{
\Delta t_W
=
N_{\rm sub}\Delta t_G
}
\]

其中 canonical：

\[
\Delta t_W=1\,s
\]

\[
\Delta t_G=0.001\,s
\]

所以：

\[
\boxed{
N_{\rm sub}=1000.
}
\]

---

# 2. 时间原则

项目只有一条物理时间：

\[
\boxed{
t_{\rm phys}\in\mathbb R^+
}
\]

禁止重新定义：

```text
World clock
Generator clock
TSS clock
```

为彼此独立的真实时间。

各组件只有不同的：

\[
\boxed{
\Delta t_i
=
\text{numerical integration resolution}
}
\]

例如：

\[
\Delta t_W=1s
\]

\[
\Delta t_G=1ms.
\]

它们都是同一个：

\[
t_{\rm phys}
\]

上的不同积分分辨率。

---

# 3. 本轮第一任务：生产代码时间语义普查

建立：

```text
G0R0_TIME_SEMANTICS_AUDIT.md
```

扫描至少：

```text
BaseGenerator
ThermalDeltaNeuron
SynapticBundle
collector
membrane RC
calcium dynamics
delay bundle
OccurrenceClosure
SkinPatch
ThermalFieldGraph
```

对每个 `dt` 记录：

```text
代码位置
默认值
docstring 含义
实际公式中的作用
单位
是否明确为 s/ms
是否只是 iteration count
是否参与 exponential decay
是否参与 delay
是否参与 energy/power
```

必须区分：

```text
PHYSICAL_TIME
NUMERICAL_STEP
DISCRETE_COUNTER
LEGACY_AMBIGUOUS
```

---

# 4. 禁止仅靠变量名判断

例如：

```python
dt = 0.001
```

不能自动判：

```text
internal step only
```

如果它进入：

\[
e^{-dt/\tau}
\]

且：

\[
\tau
\]

单位是秒，

则：

\[
dt
\]

就是物理时间增量。

同理，如果：

```text
delay_ms / dt
```

用于计算延迟步数，

也属于物理时间语义。

---

# 5. 输出时间语义 census

形成表：

| 模块 | dt | 当前语义 | 是否物理秒 | G0-R0 处理 |
|---|---:|---|---|---|
| World | 1.0 | external integration | YES | 保留 |
| Boundary | 1.0 | sample interval | YES | 保留 |
| Generator | 0.001 | ? | 审计 | 待定 |
| L1 | 0.001 | ? | 审计 | 待定 |
| Synapse | 0.001 | ? | 审计 | 待定 |
| Closure | ? | ? | 审计 | 待定 |

不得提前填答案。

---

# 6. 第二任务：建立 MultiRateScheduler 原型

只允许新增：

```text
research/g0_reconnect/r0/
```

production 暂不改。

建立研究层：

```text
MultiRateScheduler
```

接口：

```text
advance_boundary_interval(
    y_prev,
    y_next,
    dt_boundary,
    dt_generator
)
```

要求：

\[
N_{\rm sub}
=
\frac{\Delta t_B}{\Delta t_G}
\]

必须为整数或明确处理余数。

canonical：

```text
dt_boundary = 1.0 s
dt_generator = 0.001 s
N_sub = 1000
```

---

# 7. 本轮必须比较三种边界保持策略

## S0 — Zero-order hold

在整个 1 s 内：

\[
Y(t)=Y_n.
\]

即 1000 个 G0 子步吃同一边界值。

---

## S1 — Linear interpolation

在：

\[
Y_n
\rightarrow
Y_{n+1}
\]

之间：

\[
Y(t)
=
Y_n
+
\alpha(Y_{n+1}-Y_n).
\]

其中：

\[
\alpha=\frac{k}{N_{\rm sub}}.
\]

---

## S2 — Boundary resampling

如果原 World/Boundary 能够以更小：

\[
dt
\]

重放，则生成真正的：

\[
Y(t_n+k\Delta t_G).
\]

它作为参考，不一定成为 production 方案。

---

# 8. 不允许用 G0 occurrence 数量选择插值法

S0/S1/S2 的判定依据：

```text
物理一致性
数值收敛
边界重放一致性
G0 状态误差
对真实细采样 reference 的逼近
```

禁止：

```text
哪个产生 occurrence 最多
→ 用哪个
```

---

# 9. Candidate B 的多率定义

Candidate B 已冻结：

\[
U_{\dot T}
=
g
\frac{Y_B(t)-Y_B(t-\Delta t_B)}
{\Delta t_B}.
\]



本轮必须明确：

这个速率值如何在：

\[
N_{\rm sub}=1000
\]

个 G0 子步内消费。

至少比较：

### B0

整段保持：

\[
U_{\dot T}(t)=const.
\]

### B1

根据插值后的 \(Y(t)\) 每 1 ms 重新计算：

\[
U_{\dot T}^{(k)}
=
g
\frac{Y_{k}-Y_{k-1}}
{\Delta t_G}.
\]

两者物理意义不同。

不得混用。

---

# 10. Candidate A 的多率定义

A：

\[
U_T
=
S(Y-Y_{\rm ref}).
\]

若采用 S1：

每个子步：

\[
U_T^{(k)}
=
S(Y^{(k)}-Y_{\rm ref}).
\]

A 本身无时间状态，因此是最适合检查 scheduler 的 reference port。

---

# 11. 第三任务：构造 continuous-reference test

选 World v2 representative episode。

分别运行：

\[
dt_W=1
\]

\[
dt_W=0.1
\]

\[
dt_W=0.01.
\]

W1 已证明这些物理轨迹一阶收敛。

用最细：

\[
dt_W=0.01
\]

作为边界 reference。

然后比较：

```text
1s boundary + multirate reconstruction
vs
0.01s reference boundary
```

经过 A/B 后再进入 frozen G0 diagnostic。

---

# 12. 必须比较 G0 内部状态，而不只比较输出

至少记录：

```text
L1 activation
HC activation
ensemble membrane states
ensemble pre_traces
collector activation
collector pre_trace
OccurrenceClosure internal state
energy/resource ledger if present
```

比较：

\[
E_{\rm state}(t)
=
\|Z_{\rm reconstructed}(t)
-
Z_{\rm reference}(t)\|.
\]

---

# 13. Scheduler 资格不要求 bit-exact

不同积分方法可能不逐位相同。

允许：

```text
tolerance-equivalent
```

但 tolerance 必须预登记。

至少要求：

随着：

\[
dt_B:
1\to0.1\to0.01
\]

G0 状态误差下降。

否则：

```text
MULTIRATE_NONCONVERGENT
```

---

# 14. 第四任务：重新解释 generator dt

本轮结束时必须二选一。

## 状态 A

```text
GENERATOR_DT = PHYSICAL_INTEGRATION_STEP
```

即：

\[
0.001s.
\]

这是当前代码证据很可能支持的解释。

---

## 状态 B

```text
GENERATOR_DT = PURE_NUMERICAL_SUBSTEP
```

只有当所有受影响组件证明：

\[
dt
\]

没有独立物理秒含义时才允许。

不能仅靠合同文字宣布。

---

# 15. 如果状态 A 成立

MAINLINE 时间合同修改为：

\[
\boxed{
\text{one physical time axis + multirate integration}
}
\]

而不是：

```text
generator dt is not physical time
```

正式写：

\[
t_{\rm phys}
\]

唯一；

\[
\Delta t_W=1s
\]

\[
\Delta t_G=0.001s.
\]

---

# 16. 如果状态 B 成立

必须证明：

所有：

```text
RC
delay
calcium
synaptic decay
membrane decay
```

都已通过其他物理参数映射恢复正确秒制。

否则不允许状态 B。

---

# 17. 第五任务：时间尺度不变性攻击

固定一个 physical episode。

分别使用：

```text
dt_G = 0.002
dt_G = 0.001
dt_G = 0.0005
```

保持：

\[
T_{\rm physical}
\]

完全相同。

比较：

```text
membrane trajectory
synaptic trace
collector
energy
occurrence state
```

正常情况应表现收敛。

如果：

\[
dt_G
\]

改变导致物理时间常数直接漂移，

登记：

```text
G0_DT_COUPLED_PHYSICS_FAIL
```

---

# 18. 延迟语义单独审计

例如一个：

\[
5ms
\]

传播延迟，

在：

\[
dt_G=1ms
\]

时应约：

\[
5\text{ steps}.
\]

在：

\[
dt_G=0.5ms
\]

时应约：

\[
10\text{ steps}.
\]

但物理延迟仍：

\[
5ms.
\]

如果代码固定成 5 step：

```text
DELAY_STEP_COUPLING_FAIL
```

---

# 19. RC 时间常数单独审计

对于：

\[
\tau=5ms
\]

或其他已声明物理时间常数，

改变：

\[
dt_G
\]

后拟合实际 decay。

要求：

\[
\tau_{\rm measured}
\]

基本不变。

---

# 20. 不在本轮修 closure threshold

T1-B smoke：

```text
L1_max = 10
collector_max ≈ 1.0017
occurrence = 0
```

已经登记。

本轮禁止调整：

```text
theta_up
theta_down
rearm
```

原因：

在 multirate timebase 冻结前，

这些参数的物理持续时间语义还没有完全确定。

---

# 21. OccurrenceClosure 时间量纲审计

只审计，不改参数。

必须回答：

```text
rearm=500
```

到底是：

\[
500\text{ generator steps}
\]

还是：

\[
500ms
\]

还是：

\[
500\text{ boundary samples}.
\]

同样审计：

```text
duration
t_up
t_down
t_rearm
```

它们当前到底记录：

```text
step index
generator physical time
external physical time
```

---

# 22. 最终目标是统一到物理时间戳

未来 occurrence 推荐：

\[
\chi_i^k
=
(
t_{\uparrow}^{phys},
t_{\downarrow}^{phys},
t_{\rm rearm}^{phys}
).
\]

内部可以保留 step counter，

但必须能映射：

\[
n\rightarrow t_{\rm phys}.
\]

---

# 23. Boundary/G0 同步点合同

每个 boundary frame 必须带：

```text
t_phys
dt_boundary
sample_id
```

每个 G0 internal step 至少能得到：

```text
t_phys
dt_generator
substep_index
```

禁止只依赖：

```text
_step_serial
```

作为跨层时间。

---

# 24. 不增加新的全局时钟对象

不要新建：

```text
GlobalClock
MasterClock
```

项目继续遵守：

> 外部物理时间是共同底板，但内部模块只按自己的局部积分分辨率推进。

Scheduler 只是：

```text
time coordination
```

不是新的物理对象。

---

# 25. 第六任务：B bridge 实测资格

只有 scheduler 冻结以后，才重新测试：

\[
Y_B
\rightarrow
B
\rightarrow
L1
\rightarrow
G0.
\]

至少测试：

```text
World v1 reference
World v2 ordinary
World v2 strong dissipation
World v2 multi-source
World v2 hidden twin
```

但仍不调整 occurrence 参数。

---

# 26. B bridge 本轮判据

只检查：

```text
输入量纲正确
时间推进正确
L1 不因 scheduler 错误产生 1000× 能量/激活
状态连续
replay 可复现
不同 dt_G 收敛
```

不检查：

```text
occurrence must happen
```

---

# 27. Replay 升级为 multirate replay

流程：

```text
World
→ record timestamped Y_B
→ delete World
→ MultiRateScheduler
→ B
→ G0
```

live 与 replay 必须：

```text
same scheduler config
same dt_G
same initial G0 state
```

然后比较：

```text
G0 internal state trajectory
```

---

# 28. 隐藏 twin 再使用一次

Twin-2：

当前边界历史逐位相同直到 source hidden state 开始影响未来。

要求：

在相同边界阶段：

\[
G0_A=G0_B
\]

在边界未来真正分叉后：

\[
G0_A\neq G0_B
\]

才允许出现。

否则：

```text
CROSS_LAYER_HIDDEN_LEAK
```

---

# 29. 能量/输入剂量审计

对 B bridge：

定义：

\[
E_{\rm input}^{proxy}
=
\int |U_{\dot T}|dt
\]

或项目当前已有更合法的资源指标。

比较：

```text
1s direct/old
multirate 1ms
fine-boundary reference
```

防止：

同一个 1 秒输入被复制 1000 次后，

产生：

\[
1000\times
\]

的无意剂量。

---

# 30. Zero-order hold 的特殊风险

如果 B 的 rate 值：

\[
U_{\dot T}
\]

在 1 秒内保持 1000 个 1ms 子步，

必须确认 L1 的增益/积分是否把：

\[
\text{1-second rate}
\]

误当成：

\[
\text{1000 independent impulses}.
\]

这是本轮必须攻击的错误。

---

# 31. A 本轮只做 scheduler reference

A 不接最终 L1 production。

因为 T1-B 已登记：

\[
A
\]

需要 L1 幅值语义改造。

本轮利用 A 的无状态线性性质检测 scheduler。

不要修改 L1 来接 A。

---

# 32. 本轮绝不同时做 L1 redesign

禁止：

```text
add adaptation to L1
change ThermalDeltaNeuron model
change gain
change clamp
```

否则无法判断误差来自：

```text
scheduler
还是
L1 改造
```

---

# 33. G0-R0 六门

## R0-M1 — Time semantics

所有关键 dt 的代码语义已审计。

## R0-M2 — Single physical time

跨层只有：

\[
t_{\rm phys}
\]

一条底板。

## R0-M3 — Multirate convergence

World coarse → G0 fine 的调度在细化时收敛。

## R0-M4 — Delay/RC invariance

改变 dt_G 后真实物理时间常数不漂移。

## R0-M5 — Replay purity

timestamped boundary replay 能重现完整 G0 状态。

## R0-M6 — No dose duplication

1000 substeps 不造成无意 1000× 输入剂量。

---

# 34. 不设置 occurrence 门

不存在：

```text
R0-M7 occurrence > 0
```

本轮不允许出现。

---

# 35. G0-R0 终态

只允许：

### A

```text
G0_MULTIRATE_TIMEBASE_QUALIFIED
```

允许进入：

```text
G0-R1
```

---

### B

```text
G0_TIME_SEMANTICS_CONFLICT
```

production 内存在无法统一解释的 dt。

---

### C

```text
MULTIRATE_SCHEDULER_NONCONVERGENT
```

需要重新检查跨层采样策略。

---

### D

```text
G0_DT_COUPLED_PHYSICS_FAIL
```

神经/延迟/RC 模型把 step count 错当物理时间。

---

# 36. G0-R1 才处理什么

R0 通过后进入：

\[
\boxed{
G0\text{-R1}
}
\]

只做：

```text
typed port implementation
B transition bridge
A target port plumbing
L1 input semantics rename
legacy compatibility
```

然后：

\[
Occurrence\ Revalidation.
\]

---

# 37. 本轮代码范围

新增：

```text
research/g0_reconnect/r0/
```

建议：

```text
time_semantics_audit.py
multirate_scheduler.py
multirate_reference_test.py
g0_dt_convergence.py
delay_rc_audit.py
multirate_replay.py
final_qualification.py
```

production：

```text
READ_ONLY
```

---

# 38. 数据文件

至少：

```text
time_semantics_census.csv
scheduler_comparison.csv
g0_state_convergence.csv
delay_invariance.csv
rc_invariance.csv
dose_audit.csv
replay_results.json
qualification_summary.json
```

---

# 39. 文档交付

压缩成四份：

```text
G0R0_TIMEBASE_CONTRACT.md
G0R0_MULTIRATE_EXPERIMENT_REPORT.md
G0R0_PHYSICAL_TIME_AUDIT.md
G0R0_FINAL_RULING.md
```

另保存：

```text
G0R0_NEGATIVE_RESULTS.md
```

---

# 40. 必须保留的负结果

特别记录：

```text
generator dt 某组件仍混用 step/s
某 delay 随 dt_G 漂移
某 RC tau 随 dt_G 漂移
ZOH 造成输入剂量重复
linear interpolation 不收敛
1:1 old coupling 与真实物理时间不一致
occurrence 仍为 0
```

最后一项不是本轮 FAIL。

---

# 41. 压缩包纪律

本轮完成时必须生成一个真正自包含的复现包。

至少包含：

```text
nexus_v1/
tss/
research/world_v2/
research/transduction_v2/
research/g0_reconnect/r0/
```

以及对应报告。

禁止再次出现：

```text
报告存在
但 research 实现未进入提交包
```

---

# 42. 回归

必须运行：

```text
nexus_v1 regression
tss version_pairing
tss fast
WT0
T1-A
W1
T1-B
G0-R0
```

若某套耗时过长，

必须明确写：

```text
NOT_COMPLETED
```

不能把未跑完算 PASS。

---

# 43. G0R0_FINAL_RULING 首屏必须回答

1. 项目是否只有一条物理时间？
2. World dt 是多少物理秒？
3. G0 dt 是多少物理秒？
4. 1 个 World step 对应多少 G0 substep？
5. Boundary 在 substeps 中如何提供信号？
6. A 如何调度？
7. B 如何调度？
8. delay 是否保持物理时长？
9. RC 是否保持物理时间常数？
10. replay 是否重现 G0 状态？
11. 是否有剂量重复？
12. occurrence 时间字段当前是什么单位？
13. 是否达到：

```text
G0_MULTIRATE_TIMEBASE_QUALIFIED
```

14. 是否允许进入：

```text
G0-R1
```

---

# 44. 本轮最重要的原则

不要用一句：

```text
generator dt is internal
```

把问题解决掉。

必须让：

\[
\boxed{
dt\text{ 的实际代码行为}
}
\]

与：

\[
\boxed{
dt\text{ 的物理解释}
}
\]

一致。

---

# 45. 一句话目标

\[
\boxed{
\text{把 World 的 1 秒和 G0 的 1 毫秒真正接在同一条物理时间轴上，
而不是靠重新命名 dt 来绕开时间冲突。}
}
\]