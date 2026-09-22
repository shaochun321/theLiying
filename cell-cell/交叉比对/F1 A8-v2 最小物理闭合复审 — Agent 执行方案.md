# F1 A8-v2 最小物理闭合复审
## Agent 执行任务书

### 一、本轮任务定位

上一轮 canonical Scale-B 的 M1–M5 数值行为已经被外部重新复现。

因此本轮：

**不再重复证明 M1–M4。**

也：

**不进入 K-07。**

本轮只解决两个问题：

\[
\boxed{
1.\ F1\ 的反馈能量是否真正进入动力学
}
\]

以及：

\[
\boxed{
2.\ F1\ 的最小物理支撑到底是多少
}
\]

当前状态应临时记为：

```text
A8-v2 theoretical criterion       CANDIDATE
F1 Scale-B M1-M4                  REPRODUCED
F1 dynamical M5                   REPRODUCED
F1 physical support               BLOCKED
F1 minimality                     NOT_MET (N=3 non-minimal)
K-07                              DO_NOT_START
```

---

# 二、外部复验基线

以下结果必须作为本轮固定基准，不得通过调参改变。

canonical Scale-B：

```text
C = 0.001
R = 600
dt = 0.001
theta = 0.3
gm = 1.0
k_in = 0.5
```

旧 canonical：

```text
N_feedback = 3
fingerprint = 72c828f910f7243b
```

外部复验确认：

```text
Scale-A:
M1 ✓
M2 ✗

Scale-B:
M1 ✓
M2 ✓
M3 ✓
M4 ✓
```

Twin：

```text
max parent state diff = 3.897e-21
Z_A = 1
Z_B = 0
future max diff = 1
readout diff = 2.1
```

不得为了本轮物理闭合修改这些资格判据。

---

# 三、P0：PowerRail 当前不是因果供能源

当前代码结构：

```python
i_fb = sum(fet.conduct(v_read) for fet in self._fets)

self._rail.draw(i_fb)

self._cap.inject(i_fb + input_current, dt)
```

这里：

```python
PowerRail.draw()
```

的返回值没有参与：

```python
i_fb
```

或实际注入电容的电流。

外部实测：

```text
Vrail = 1.0 → Z=1
Vrail = 0.5 → Z=1
Vrail = 0.1 → Z=1
Vrail = 0.0 → Z=1
```

以及：

```text
r_internal = 0   → Z=1
r_internal = 1   → Z=1
r_internal = 100 → Z=1
```

即使：

```text
rail_v_actual = 0
```

反馈状态仍持续。

因此当前：

```text
ENERGY_SUPPORT = EXTERNAL_IDEAL_RAIL
```

不是动力学事实。

它只是账本标签。

---

# 四、P0-1：禁止通过简单乘 Vrail 修复

禁止重新引入旧错误：

\[
I_{\rm fb}
=
MOSFET.conduct(V_g)\times V_{\rm rail}
\]

因为：

```text
MOSFET.conduct → A
```

再乘：

```text
V
```

得到：

```text
W
```

不能作为电流注入。

不得为了让 rail 有作用而恢复量纲错误。

---

# 五、P0-2：先定义反馈供能物理契约

Agent 不得直接改代码。

先提交：

```text
F1_FEEDBACK_POWER_CONTRACT.md
```

回答：

### 1

`MOSFET.conduct(v_gate)` 在项目原语里的物理含义究竟是：

```text
A. 已假设 drain/source 供电存在后的漏极电流
```

还是：

```text
B. 只表示由 gate 决定的期望电流，需要供能源进一步裁定
```

当前代码语义更接近 A，但能源端没有显式进入。

必须明确。

### 2

反馈电流：

\[
I_{fb}
\]

由哪个物理端提供能量？

### 3

若：

\[
V_{\rm supply}=0
\]

必须满足：

\[
\boxed{
I_{fb}=0
}
\]

### 4

若供能源有有限内阻：

\[
R_s>0
\]

必须存在明确的：

\[
I-V
\]

自洽关系，而不是只把：

```text
v_actual
```

写进日志。

---

# 六、允许的两个实现方向

Agent 先分析，不预设必须采用哪一个。

## 路径 A：显式供电约束的受控电流支路

保留：

\[
I_{\rm request}
=
g_m\max(0,V_g-\theta)
\]

但真正允许进入反馈节点的电流是：

\[
I_{\rm fb}
=
F(I_{\rm request},V_{\rm supply},R_s)
\]

必须满足：

\[
I_{\rm fb}(V_{\rm supply}=0)=0
\]

并保证量纲：

\[
[I_{\rm fb}]=A.
\]

`F()` 必须有物理解释。

禁止任意经验缩放。

---

## 路径 B：显式电导原语

如果希望：

\[
I=G(V_g)V_{ds}
\]

则新增/使用真正的：

\[
G(V_g)
\]

其单位：

\[
S=A/V
\]

然后：

\[
I_{\rm fb}
=
G(V_g)V_{\rm supply}.
\]

不得继续调用返回 A 的：

```python
MOSFET.conduct()
```

冒充 conductance。

如果需要新增新的 MOSFET API：

```python
conductance(v_gate)
```

必须只在 research 隔离层尝试。

不得先修改母体。

---

# 七、P0-3：新增 Rail causality test

必须新增：

```text
exp_F1_rail_causality.py
```

至少测试：

```text
Vrail = 1.0
0.5
0.1
0.0
```

以及若有有限内阻：

```text
R_internal = 0
small
medium
large
```

要求：

### 正常供电

\[
Vrail=1
\]

保留候选预期行为。

### 断电

\[
Vrail=0
\]

必须：

\[
I_{fb}=0
\]

并使高态自然失去维持。

### 恢复供电

不得自动恢复高态。

如果输入历史没有重新形成候选：

\[
Z
\]

就不能“断电再上电自动记起”。

否则必须登记为新的器件历史效应并另审。

---

# 八、P0-4：能源账本改成因果账本

当前：

```python
E_fb += i_fb * v_read * dt
```

不能作为最终反馈供能定义。

`v_read` 是 gate/node 状态，并不自动等于 drain/source 供电压差。

必须按照实际反馈支路计算：

\[
E_{\rm supply}
=
\int V_{\rm supply} I_{\rm supply}\,dt.
\]

至少记录：

```text
requested_feedback_current
delivered_feedback_current
supply_voltage
supply_current
supply_energy
stored_capacitor_energy
clamp_dissipation
rail_internal_dissipation
```

要求局部账本：

\[
E_{\rm supply}+E_{\rm input}
\approx
\Delta E_{\rm stored}
+
E_{\rm leak}
+
E_{\rm clamp}
+
E_{\rm rail-loss}
\]

如果现有原语仍无法闭合：

```text
LOCAL_ENERGY_CLOSURE = NOT_MET
```

不得继续写：

```text
ENERGY_SUPPORT = EXTERNAL_IDEAL_RAIL
```

作为已证明事实。

---

# 九、P0-5：候选最小化 N=3 → N=1

外部已经实测：

Scale-B：

\[
N=1
\]

仍然有三个固定点：

\[
0,
\quad
V_u=0.301002506,
\quad
V_H.
\]

真实关系输入：

```text
gap100 → HIGH
gap400 → HIGH
gap600 → LOW
gap700 → LOW
single → LOW
none   → LOW
```

Twin：

\[
P_A-P_B
=
3.897\times10^{-21}
\]

\[
Z_A=1,
\quad
Z_B\approx0
\]

\[
FutureDiff=1
\]

\[
ReadoutDiff=2.1.
\]

因此：

\[
N=3
\]

不是最小结构。

canonical 新候选首先必须测试：

\[
\boxed{N=1}
\]

不得保留三条 FET 仅因为旧实验使用 N=3。

---

# 十、N=1 能源基准

外部测量：

120000 step：

```text
N=1:
feedback energy ≈ 83.6606
clamp dissipation ≈ 582.418
```

旧 N=3：

```text
feedback energy ≈ 250.982
clamp dissipation ≈ 5258.481
```

所以 N=1 不仅结构更小，而且显著降低无效钳位耗散。

只有 N=1 失败某个资格条件时，才允许考虑 N>1。

---

# 十一、P1：修正 finite clamp 固定点数学

当前：

```python
finite_clamp_fixed_point()
```

不能继续描述成同一离散 `RailLatch.step()` 的精确固定点。

实际 finite clamp 的顺序是：

```text
leak
→ feedback inject
→ 得到 V_preclamp
→ clamp current(V_preclamp)
→ clamp inject
```

因此必须分别给出：

```text
finite_discrete_map(V, dt)
finite_discrete_fixed_point(dt)
continuous_limit_fixed_point()
```

外部基准：

```text
N=3, dt/100:
actual discrete high = 1.2586377289

N=3, dt/1000:
actual discrete high = 1.2954276151

continuous limit:
≈1.29969
```

不得把三者混用。

---

# 十二、P1-2：clamp_integrity 固定真实物理时间

当前测试：

```python
steps = 200000 // div
dt = 0.001 / div
```

会使总物理时间随 div² 缩短。

修改为：

\[
steps
=
T_{\rm physical}/dt.
\]

所有 dt：

```text
dt
dt/10
dt/100
dt/1000
```

必须跑相同：

```text
physical duration
```

并报告：

```text
convergence error
fixed-point error
```

虽然外部等物理时长复验后当前“双稳存在”结论仍然保持，但测试方法必须修正。

---

# 十三、P1-3：Parent census 扩展容器递归

当前 census 对：

```text
dict
list
tuple
```

覆盖不完整。

必须递归进入：

```text
_channels
_channel_configs
_prev_source_acts
_delay_buffer
_memristors
spike_times
fire_steps
```

并区分：

```text
DYNAMIC_CAUSAL
HISTORICAL_LOG
STATIC
AUDIT_ONLY
```

外部全递归审计得到：

```text
1500 scalar leaves
```

Twin A/B 只有 16 个非零差异。

最大非历史动态差仍：

\[
3.897\times10^{-21}.
\]

历史显著差异主要来自：

```text
fire_steps
spike_times
```

这些必须明确证明：

```text
不进入当前 parent future dynamics
```

而不能简单因为是 list 就忽略。

---

# 十四、P1-4：消除 k_in 默认值歧义

当前：

```python
RailLatch.k_in default = 1.0
```

但 canonical：

```text
k_in=0.5
```

而且 `rail_latch.py` docstring 仍有旧 `k_in=1.0` 描述。

要求：

- RailLatch 不得拥有与 canonical 不同的隐式默认；
- 或要求初始化时必须显式传 config；
- `rail_latch.py` 独立自检也必须打印 fingerprint。

避免未来再次出现：

```text
同一个类，不同隐式尺度
```

的问题。

---

# 十五、P1-5：交付包真正可独立复现

本次包包含：

```text
tss/
research/
VERSION.txt
```

但没有：

```text
nexus_v1/
```

外部本轮借用了此前上传的 `nexus_v1 (2)`。

`test_version_pairing.py`：

```text
2/2 PASS
```

但因为交付包没有母体源码或文件 hash，无法仅凭这个包证明它就是 VERSION.txt 声明的 commit。

下一轮至少提供二选一：

### A

直接打包只读：

```text
nexus_v1/
```

### B

提供：

```text
NEXUS_SOURCE_MANIFEST.json
```

包含所有 research/TSS 实际 import 文件的：

```text
relative path
SHA256
expected commit
```

例如：

```text
components/semiconductor.py
components/neuron.py
circuit/bundle.py
components/structural_address.py
...
```

---

# 十六、新 canonical 暂定规则

在理论侧没有进一步裁定前，研究候选暂定：

```text
Scale-B
C=0.001
R=600
dt=0.001

N_feedback=1
theta=0.3
gm=1.0

k_in=0.5
```

但是新的 fingerprint 必须在**供能因果闭合以后**重新生成。

旧：

```text
72c828f910f7243b
```

不得继续作为最终候选 fingerprint。

---

# 十七、从零重跑 M1–M5

Rail causality 修复 + N=1 最小化后：

全部状态清零。

重新跑：

```text
M1 mathematical multistability
M2 physical reachability
M3 parent-state matched
M4 future divergence
M5 A8 candidate
```

禁止继承上一轮：

```text
F1_M5_VALIDATED
```

---

# 十八、新增第六门：M5-P physical support

即使 M1–M5 全通过，再增加：

```text
M5-P PHYSICAL_SUPPORT
```

要求同时满足：

\[
V_{\rm supply}=0
\Rightarrow
I_{fb}=0
\]

\[
Z_{\rm high}
\xrightarrow{\rm power\ cut}
Z_{\rm low}
\]

以及：

\[
\text{local energy accounting}
\]

至少达到可审计状态。

最终只有：

```text
M1 ✓
M2 ✓
M3 ✓
M4 ✓
M5 ✓
M5-P ✓
```

才记：

```text
F1_A8v2_PHYSICALLY_VALIDATED
```

仍然不写：

```text
A8 MET
new generator
organization
```

---

# 十九、K-07 守卫

只有：

```text
F1_A8v2_PHYSICALLY_VALIDATED
```

成立后，才开启 K-07。

如果出现：

```text
M1-M5 ✓
M5-P ✗
```

状态应保持：

```text
DYNAMICAL_CANDIDATE_ONLY
```

不得进入生成元资格链。

---

# 二十、不要推进 F3/F5

F3/F5 继续冻结。

不得用更复杂候选绕过：

```text
Rail power closure
minimality
energy accounting
```

的问题。

F1 是最小审计对象。

---

# 二十一、最终交付

输出：

```text
F1_A8v2最小物理闭合复审工作报告_YYYY-MM-DD.md
```

至少包含：

1. rail supply contract；
2. 供电电流方程；
3. 完整量纲；
4. N=1 最小性证明；
5. 新 fingerprint；
6. power-cut experiment；
7. finite clamp 离散/连续固定点；
8. equal-physical-time dt audit；
9. 完整 parent census；
10. local energy ledger；
11. 从零 M1–M5；
12. M5-P；
13. 所有失败和勘误；
14. 是否允许进入 K-07。

最终只能给：

```text
F1_REJECTED
```

或：

```text
F1_A8v2_PHYSICALLY_VALIDATED
```

不得为了继续项目而强行选择后者。

---

# 二十二、研究纪律

这一轮的核心问题不是：

> “这个 latch 能不能记住一件事？”

这已经证明了。

真正的问题是：

> **这个持久状态能不能由一个真实受能源约束、最小、量纲闭合的物理回路维持？**

如果：

\[
V_{\rm supply}=0
\]

而：

\[
I_{fb}\neq0
\]

那么无论 Twin 实验多漂亮，都还不能成为项目所要求的物理生成候选。