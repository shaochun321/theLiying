# MAINLINE V2 — G0-R1/OCC
## 生产回接、基础发生最终资格与 D2 入场
### 最后一个以 G0 为中心的主线阶段

---

# 0. 理论建筑地址

本轮理论地址：

\[
\boxed{D_0\rightarrow D_1\text{ 最终闭合}}
\]

服务对象：

\[
\boxed{
World
\rightarrow Boundary
\rightarrow D_{v2}
\rightarrow G_0
\rightarrow \chi^{(0)}
}
\]

本轮不是新理论层。

完成后立即进入：

\[
\boxed{
D_2 / P2\text{-B}
}
\]

即：

\[
\chi^{(0)}
\rightarrow
\mathcal N
\rightarrow
\mathcal C_\rho
\rightarrow
x_\rho
\]

并开始第一次真实关系生成。

旧路线已经规定：

\[
P2\text{-A}
=
\text{真实发生}
\]

\[
P2\text{-B}
=
\text{自然化后进入共同关系耦合}
\]

\[
P2\text{-C}
=
\text{验证其能否递归到更深生成关系}.
\]

因此本轮结束后禁止新增新的 G0 基础阶段。

---

# 1. 当前冻结状态

```text
W1 = WORLD_V2_RAW_QUALIFIED

T1-B = TRANSDUCTION_V2_QUALIFIED
A_LONG_TERM_PORT_QUALIFIED = YES
B_RATE_PORT_QUALIFIED = YES

G0-R0 = G0_MULTIRATE_TIMEBASE_QUALIFIED

t_phys = UNIQUE
dt_W = 1.0 s
dt_G = 0.001 s
N_sub = 1000
```

G0-R0 已实测确认：

\[
dt_G=0.001s
\]

是物理积分步，而不是独立内部时钟。

本轮不得重新打开这个问题。

---

# 2. 本轮唯一目标

最终得到一个可以交给 D2 消费的：

\[
\boxed{
\chi_i^{(0)}
}
\]

它必须满足：

\[
\chi_i^{(0)}
=
(
t_i^\uparrow,
t_i^\downarrow,
t_i^{rearm},
Addr_i,
\Lambda_i^{phys},
Y_i^{out}
)
\]

至少具有：

- 真实物理时间；
- trigger / exit / rearm；
- 明确生成谱系；
- 原始运行轨迹；
- 能量/耗散记录；
- 可再次被关系层消费的 typed output。

本轮不定义最终 NaturalUnit。

---

# 3. G0-R1 production 修改范围

本轮首次允许定点修改 production。

只修改已明确登记的项目：

## R1-1 Typed Port

正式落实：

\[
U_T
\]

和：

\[
U_{\dot T}.
\]

禁止继续让：

```text
u_i
dT_raw
```

同时表示幅值与速率。

---

## R1-2 B Transition Bridge

当前：

\[
B:
U_{\dot T}
=
g\dot T.
\]

B 只作为现有 L1 的过渡桥。

本轮需要在真实秒制下重新标定：

\[
g.
\]

原因是 G0-R0 已发现旧 canonical \(g\) 导致约 33.3% 子步进入 L1 钳位，属于：

```text
B_BRIDGE_L1_SATURATION
```

不得继承旧 step 制量级。

---

## R1-3 A Target Port Plumbing

Candidate A：

\[
U_T=S(Y-Y_{ref})
\]

只完成 production 接口和 future path。

本轮不要求立即完全替代现 L1。

如果 A 需要真正的 amplitude→receptor-current L1 改造，则只建立明确升级接口，不在本轮顺手重新设计整个感受神经元。

---

# 4. 三个时间债务必须一次清掉

## D1 — L1 trace

当前：

```text
0.99 / step
```

导致真实衰减时间随 dt 漂移。

改为：

\[
e^{-\Delta t_G/\tau}
\]

或等价 dt-aware 形式。

---

## D2 — SynapticBundle delay

当前：

```text
delay_steps
```

导致：

\[
5\ steps
\]

在不同 dt 下对应不同物理延迟。

必须改为保存：

\[
\tau_{delay}^{phys}
\]

运行时：

\[
N_{delay}
=
round\left(
\frac{\tau_{delay}^{phys}}
{\Delta t_G}
\right).
\]

保留 legacy adapter。

---

## D3 — OccurrenceClosure 时间

内部允许继续保存 step counter。

但必须提供：

\[
t^{phys}=n\,\Delta t_G.
\]

正式 occurrence：

\[
t^\uparrow,t^\downarrow,t^{rearm}
\]

必须可以直接输出物理秒。

G0-R0 已确认当前 `rearm=500` 是 500 generator steps，即 0.5 s，而不是 500 秒。

---

# 5. Live Scheduler 最终裁定

G0-R0 中：

- S1 linear interpolation 最适合 reference/replay；
- 但需要下一 Boundary frame，因此 live 会产生 1 个 World sample 的滞后；
- S0 ZOH 是零未来访问的 causal baseline。

本轮必须明确区分：

```text
REFERENCE_RECONSTRUCTION_POLICY
LIVE_CAUSAL_POLICY
```

推荐先验：

```text
Reference/replay = S1
Live production  = S0
```

除非实验证据证明其他 causal 方法更合适。

禁止让 live production 使用未来 Boundary sample。

---

# 6. Occurrence Revalidation 不看逐神经元状态相等

G0-R0 已得到：

```text
G0_OSCILLATOR_PHASE_SENSITIVITY
```

ensemble / collector 的自持振荡可因相位失相干导致完整状态向量长期 O(1) 差异，而接口层仍正常一阶收敛。

因此本轮正式规定：

\[
\boxed{
\text{G0 资格面 = event/statistical level}
}
\]

不是：

\[
Z_A(t)=Z_B(t)
\]

逐状态一致。

保留逐状态数据作为诊断，但不得作为 occurrence PASS 的主要判据。

---

# 7. Occurrence 最终合同

一次基础发生：

\[
\chi_i^k
\]

必须具有三物理边界：

\[
\boxed{
\chi_i^k=
(
t_{i,k}^{\uparrow},
t_{i,k}^{\downarrow},
t_{i,k}^{rearm}
)
}
\]

分别验证：

### Trigger

真实 Boundary→D→G0 输入导致闭合进入。

### Sustain

过程具有有限持续时间，不是单步阈值 crossing。

### Exit

输入结束或内部动力学退出后离开发生态。

### Rearm

经过真实恢复过程后重新允许下一次发生。

禁止用外部 episode 标签直接指定这些时刻。

---

# 8. 参数重标原则

本轮只允许重新标：

```text
B bridge g
OccurrenceClosure thresholds
rearm physical duration
```

且顺序必须是：

\[
\text{timebase fix}
\rightarrow
\text{port fix}
\rightarrow
\text{measure}
\rightarrow
\text{calibrate}.
\]

禁止为了让 occurrence 数量好看而调参。

每个参数必须输出：

```text
physical meaning
legal region
failure boundary
canonical reference
provenance
```

不寻找“最佳值”。

---

# 9. Calibration / Held-out

重新建立：

\[
G0_{\rm cal}
\]

与：

\[
G0_{\rm hold}.
\]

episode 直接继承 W1/T1-B 已冻结 World v2 条件。

必须包括：

- 普通 World；
- 强耗散 World；
- 多 Source；
- 不同 Boundary；
- hidden twin；
- 弱输入；
- 持续输入；
- 相邻多 occurrence 输入。

held-out 不能参与 closure/g 参数重标。

---

# 10. 必须测试 occurrence 的 dose 结构

旧系统曾出现：

不同强度输入最终都只形成近似相同 occurrence。

本轮必须检查：

\[
A_1<A_2<A_3
\]

的物理输入是否至少能在某些可测输出维度上保持差异，例如：

\[
latency,
duration,
internal activity,
energy,
rearm,
trajectory.
\]

不要求：

\[
\text{dose}\rightarrow\text{occurrence count}
\]

单调。

但禁止所有物理剂量差异被 saturation 完全抹掉而仍宣称合格。

---

# 11. 外部观察轨重新接回主线

本轮恢复已有：

```text
NoetherProbe
EntropyLedger
WeightEntropyProbe
StructuralEntropy
NuProbe / diagnostic probes
state census
```

但保持：

\[
\boxed{\text{READ-ONLY}}
\]

现有 ledger 本来就是只读观察系统，不写回运行结构。

本轮原则：

```text
REUSE
NOT REBUILD
```

不得再建立一套新的熵系统。

---

# 12. Hidden Dynamics Observation Contract

每个关键 occurrence 实验同时记录：

\[
O(t)
=
(
Y_{visible},
E,
H,
\nu_{diag},
Z_{candidate},
Lineage
).
\]

这些字段只存在于研究观察面。

G0 内部禁止出现：

```text
hidden_state = True
important_relation = True
```

等研究者语义标签。

---

# 13. Hidden Dynamics Closure 实验

本轮至少构造一类：

\[
Y_A(t_0)\approx Y_B(t_0)
\]

但内部状态不同的 G0 twin。

观察：

\[
Future_A
\stackrel{?}{=}
Future_B.
\]

如果未来 occurrence 不同，则利用 probe / ledger 定位候选隐藏状态：

\[
Z.
\]

然后做干预：

\[
Z_B(t_0)\leftarrow Z_A(t_0)
\]

或阻断候选载体。

若未来差异消失：

```text
HIDDEN_STATE_CAUSALLY_SUPPORTED
```

否则：

```text
CORRELATIONAL_ONLY
```

---

# 14. Hidden Dynamics 的停止规则

这是本轮非常重要的新方法学。

假设当前状态描述为：

\[
P.
\]

发现隐藏候选：

\[
Z.
\]

若加入：

\[
P^*=(P,Z)
\]

后，在当前实验分辨率、合法参数域及相同未来输入下：

\[
P_A^*(t_0)=P_B^*(t_0)
\Rightarrow
Future_A\approx Future_B,
\]

则登记：

```text
CURRENT_MINIMAL_SUFFICIENT_STATE_CANDIDATE
STOP_DEEPER_DECOMPOSITION
```

禁止继续拆：

```text
Z → Z1 → Z2 → Z3...
```

除非出现新的反例：

\[
P_A^*=P_B^*
\]

但：

\[
Future_A\neq Future_B.
\]

---

# 15. 振荡相位专门作为第一例

优先利用已经发现的：

```text
G0_OSCILLATOR_PHASE_SENSITIVITY
```

建立：

\[
\phi_A\neq\phi_B
\]

但可见输出近似相同的 twin。

测试：

\[
\phi
\]

是否真正改变后续 occurrence。

若不改变：

```text
OSCILLATOR_PHASE = MICROSTATE_ONLY
```

停止深挖。

若改变：

再寻找最低维可追踪的 phase/state representation。

禁止直接把全部 neuron state 都提升为生成元状态。

---

# 16. 熵账本的资格边界

Entropy / StructuralEntropy 只能用于：

```text
candidate localization
change-point detection
state divergence detection
```

不能使用：

\[
\Delta H\neq0
\]

直接证明：

```text
new generator
new relation
new scale
```

Noether/energy ledger 只回答：

\[
\boxed{\text{物理过程是否合法}}
\]

而不回答：

\[
\boxed{\text{生成深度是否提升}}
\]

---

# 17. NuProbe 的身份

旧 `NuProbe` 继续作为诊断探针。

但本轮明确：

```text
NuProbe != theoretical ν
```

不得把旧实现数值直接解释成当前理论里的运动势。

只登记：

```text
DYNAMIC_TENSION_DIAGNOSTIC
```

未来是否与运动势形成正式对应，留给深层阶段。

---

# 18. occurrence 输出必须保存双轨

沿用旧 P2-A 思路。

## Physical Track

\[
\Lambda^{phys}
\]

保存：

- Boundary/input trajectory；
- D output；
- L1/G0 activity；
- physical timestamps；
- energy / heat / resource；
- saturation；
- lineage；
- failure/recovery。

## Organization Track

本轮只保存最低组织接口。

例如：

\[
\Lambda^{org}
=
(
occurrence\ identity,
typed\ output,
local\ phase\ candidate
)
\]

禁止冻结最终 NaturalUnit。

---

# 19. D2 消费接口必须在本轮尾部产生

本轮最终交付一个：

```text
OccurrencePortV2
```

概念合同即可，名称可调整。

至少提供：

\[
id
\]

\[
generation\_depth=0
\]

\[
parent/physical\ lineage
\]

\[
t^\uparrow,t^\downarrow,t^{rearm}
\]

\[
raw\ physical\ track
\]

\[
typed\ relation\ input\ candidates.
\]

D2 不允许回头直接读取 G0 内部 neuron state。

---

# 20. D2 入场最小条件

只要满足：

1. occurrence 可重复产生；
2. 有 trigger/exit/rearm；
3. 时间全部物理化；
4. input/output typed；
5. lineage 完整；
6. ledger 可审计；
7. held-out 不结构性崩溃；
8. hidden dynamics 已达到当前最小充分状态或确认不影响 occurrence；
9. D2 可直接消费 occurrence port；

则：

\[
\boxed{
D_1 = SUFFICIENT_FOR_NEXT_GENERATION
}
\]

不是：

```text
D1 perfect
```

---

# 21. 明确允许基础层“不完美”

以下情况如果不阻塞 occurrence 与 D2，不得继续扩展本轮：

- 个别微观状态相位不一致；
- 某些未消费 trace 仍有卫生问题；
- G0 神经元数量未证明最优；
- World 仍是简化热环境；
- NaturalUnit 尚未最终定义；
- NuProbe 尚未获得理论身份；
- 全局熵理论未完成。

这些全部不能阻止进入 D2。

---

# 22. 六门

## OCC-M1 — Physical Time

所有 occurrence 时间、delay、rearm 均可映射到：

\[
t_{phys}.
\]

## OCC-M2 — Typed Chain

\[
Boundary
\rightarrow D
\rightarrow L1
\rightarrow G_0
\]

无幅值/速率语义混用。

## OCC-M3 — Finite Closure

真实完成：

\[
trigger
\rightarrow sustain
\rightarrow exit
\rightarrow rearm.
\]

## OCC-M4 — Held-out

冻结参数在 held-out World 条件下不存在结构性失败。

## OCC-M5 — Physical Ledger

energy/resource/lineage 可审计，无隐藏 side channel。

## OCC-M6 — Hidden Dynamics Closure

已完成：

```text
same-visible/different-future
→ probe localization
→ intervention
→ stop/deepen ruling
```

至少一轮正式实验。

---

# 23. 不设“完美神经动力学”门

不存在：

```text
OCC-M7 all neuron trajectories converge
```

不存在：

```text
OCC-M8 G0 globally minimal
```

不存在：

```text
OCC-M9 entropy theory complete
```

---

# 24. 最终状态只允许三种

## A

```text
G0_OCCURRENCE_V2_QUALIFIED
D1_SUFFICIENT_FOR_D2
```

立即进入 D2。

---

## B

```text
G0_OCCURRENCE_PARTIAL
BLOCKING_DEFECT = <specific defect>
```

只允许修这个 blocking defect。

禁止新开基础研究分支。

---

## C

```text
G0_OCCURRENCE_ARCHITECTURE_FAIL
```

仅当真实发生合同在跨 World 条件下无法成立时使用。

---

# 25. 硬停止规则

一旦：

```text
D1_SUFFICIENT_FOR_D2 = TRUE
```

立即执行：

```text
FREEZE G0-CENTRIC MAINLINE
```

禁止：

```text
G0-R2
G0-R1b
Occurrence-v3
Entropy redesign
World-v3
Transduction-v3
```

除非 D2 产生明确、可复现、会阻断生成递归的反例。

---

# 26. 下一阶段提前写死

本轮通过后：

\[
\boxed{
D2\text{-}0 / P2\text{-B
}
}
\]

目标：

多个真实：

\[
\chi_i^{(0)}
\]

经过候选自然化：

\[
\mathcal N_i
\]

进入真实关系结构：

\[
\mathcal C_\rho.
\]

然后：

\[
D2\text{-}1 / P2\text{-C
}
\]

验证：

\[
\chi_\rho^{(1)}
\]

是否能够再次作为输入参与关系生成。

旧总纲明确规定，单纯 \(R+R\to R'\) 仍不能证明它已经取得结构/行为算子资格；后续还要通过保留/阻断历史关系对未来真实过程的影响来资格化。

---

# 27. G1 资格门预登记，但本轮不执行

未来：

\[
\chi_\rho^{(1)}
\]

必须继续接受：

### 独立状态门

父层当前最小充分状态相同，候选新状态不同，并导致未来不同。

### 闭合门

候选关系结构具有自己的：

\[
trigger/sustain/exit/rearm.
\]

### 端口门

能够再次被下游关系结构消费。

### 因果作用门

保留/阻断该历史关系：

\[
\Gamma_{\rm with,\rho}^{+}
\not\sim
\Gamma_{\rm without,\rho}^{+}.
\]

这些是下一生成元真正形成的资格门。

---

# 28. 代码范围

允许修改：

```text
nexus_v1/generators/
relevant typed-port adapter
ThermalDeltaNeuron time handling
SynapticBundle delay handling
OccurrenceClosure timestamp mapping
```

新增研究区：

```text
research/g0_reconnect/r1_occ/
```

建议只保留：

```text
r1_port_and_time_fix.py
r1_calibration.py
occurrence_revalidation.py
hidden_dynamics_closure.py
final_qualification.py
```

---

# 29. 外部观察基础设施

直接复用：

```text
nexus_v1/ledger/
existing probes
existing census
```

不新造大框架。

如果需要统一导出，最多增加：

```text
observation_frame.jsonl
```

或：

```text
hidden_dynamics.csv
```

不要求建立新 runtime class。

---

# 30. 数据交付

至少：

```text
port_calibration.csv
occurrence_trials.csv
occurrence_heldout.csv
closure_timing.csv
energy_ledger.csv
hidden_twin_pairs.csv
hidden_interventions.csv
minimal_state_ruling.json
qualification_summary.json
```

---

# 31. 文档交付

压缩为：

```text
G0R1_PORT_AND_TIME_FIX_REPORT.md
OCCURRENCE_V2_REVALIDATION_REPORT.md
HIDDEN_DYNAMICS_CLOSURE_REPORT.md
G0R1_OCC_FINAL_RULING.md
NEGATIVE_RESULTS.md
```

不要再生成十几份中间报告。

---

# 32. 回归

完成后运行：

```text
nexus regression
W1 frozen suite
T1-B frozen suite
G0-R0 frozen suite
G0-R1/OCC
TSS fast/version pairing
```

所有未真正跑完的项目必须写：

```text
NOT_COMPLETED
```

---

# 33. 最终报告首屏必须回答

1. live scheduler 最终采用什么？
2. B→L1 是否仍有饱和？
3. A target port 是否已建立正式 production 路径？
4. delay 是否物理时间不变？
5. L1 trace 是否 dt-aware？
6. occurrence 是否输出物理秒？
7. trigger/exit/rearm 是否在 held-out 中成立？
8. 不同输入剂量是否仍保留可测差异？
9. energy / Noether 是否闭合？
10. hidden twin 是否存在？
11. 哪个状态真正造成不同未来？
12. causal block 是否确认？
13. 是否已经达到当前最小充分状态？
14. 是否可以停止继续下钻？
15. 是否得到：

```text
G0_OCCURRENCE_V2_QUALIFIED
```

16. 是否得到：

```text
D1_SUFFICIENT_FOR_D2
```

17. 是否立即进入：

```text
D2-0 / P2-B
```

---

# 34. 本轮真正的成功标准

不是：

\[
G_0\text{ 被解释得越来越彻底。}
\]

而是：

\[
\boxed{
G_0
\text{ 已经足够可靠地把真实物理过程变成下一生成深度可以消费的发生。}
}
\]

达到这里就停止。

---

# 35. 一句话目标

\[
\boxed{
\text{结束基础层时代：把 G0 做到“足够生成”，
而不是做到“无限可解释”，然后第一次真正进入 }D_2.
}
\]