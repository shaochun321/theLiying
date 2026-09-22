# Transduction v2 与 World v2 分阶段闭合方案

## 一、当前裁定

接受本轮结论：

```text
TRANSDUCTION_V2 = REQUIRED
WORLD_V2 = REQUIRED
```

但两者不得同时调参建设。

新的执行顺序冻结为：

\[
\boxed{
T1\text{-A：转导结构合同}
\rightarrow
W1：World v2
\rightarrow
T1\text{-B：跨 World 标定}
\rightarrow
G0：重新资格化
}
\]

TSS 保持冻结。

---

## 二、为什么不能直接完整建设 T1

T0 已证明旧线性 affine+clip：

\[
u=\operatorname{clip}(\kappa q+b,0,0.04)
\]

存在双侧塌缩。

低侧：

\[
q<T_{\rm floor}
\Rightarrow
u=0.
\]

高侧：

\[
q>T_{\rm ceil}
\Rightarrow
u=0.04.
\]

而真实轨迹绝大多数时间落在低侧死区，强输入又进入高侧饱和。

因此简单改：

```text
κ
b
clip ceiling
```

不能视作 Transduction v2。

否则只是重新选择一个更宽的线性窗口。

更严重的是，如果现在直接根据 World v1 调出“好看的”新参数，会重新建立：

\[
World_{v1}
\leftrightarrow
D_{v2}
\]

的专用共适应。

所以 T1-A 不允许冻结最终数值。

---

## 三、T1-A 的唯一目标

回答：

> 一个合格的热环境→G0 转导结构应该保留什么物理性质，又允许丢失什么？

只建立：

```text
TRANSDUCTION_V2_CONTRACT
```

不建立最终：

```text
TRANSDUCTION_V2_CALIBRATION
```

---

## 四、首先撤销旧标定逻辑

以下方法正式退役：

```text
用若干场景最终稳态端点温度
→ 反推 κ/b
→ 定义整个动态转导区间
```

原因已经由 T0 实测确认：

真实输入不是稳态点集合，而是：

\[
q(t)
\]

的连续轨迹。

包括：

\[
\text{静息}
\rightarrow
\text{上升}
\rightarrow
\text{峰值}
\rightarrow
\text{停注}
\rightarrow
\text{衰减}
\rightarrow
\text{恢复}.
\]

所以 Transduction v2 必须以：

\[
\boxed{\text{trajectory calibration}}
\]

为基础。

---

## 五、静息锚定重新定义

T1-A 可以接受：

```text
去偏置静息锚定
```

作为候选原则，但不得简单规定：

\[
u=k(q-q_0)
\]

就是最终方案。

必须区分：

\[
q_{\rm rest}
\]

是环境绝对参考，

还是：

\[
q_{\rm local\ baseline}(t)
\]

是由真实局部物理历史形成的慢变量。

如果需要动态 baseline：

它必须有明确物理载体或感受器机制。

禁止使用软件滑动平均仅为了扩大动态范围。

---

## 六、Transduction v2 候选族

T1-A 不选择赢家，只允许建立候选族。

至少保留三类：

```text
A. 改良线性 / piecewise physical mapping

B. 饱和压缩型 monotonic mapping

C. 带真实适应状态的 dynamic transduction
```

其中 B/C 的具体形式必须先完成：

```text
Q1：热感受器 / thermoreceptor 生物物理对应物
Q2：实际状态与物理信号路径
Q3：参数来源
```

禁止为了得到更漂亮的动态范围直接选择 sigmoid / tanh / log。

数学压缩函数不能代替物理机制说明。

---

## 七、T1-A 不以“最大保真”为目标

转导本来就应该简并信息。

所以不要优化：

\[
\max I(q;u).
\]

也不要追求：

```text
所有 World 差异都必须保留
```

需要的是：

\[
\boxed{
\text{有结构、有原因、可重复的信息损失}
}
\]

即明确知道：

什么被保留；

什么被压缩；

什么被完全删除；

什么只留下时间结构而丢失幅值；

什么只在极端条件下消失。

---

## 八、冻结新的测量方法

旧的 ratio 指标已经暴露 baseline-zeroing artifact。

因此以后不允许单独使用：

\[
\widehat D_{\rm supp}/D_{\rm world}
\]

作为“放大/保真”证据。

必须同时保存原始：

\[
D_{\rm world}
\]

\[
D_{\rm boundary}
\]

\[
D_{\rm transduced}
\]

以及：

```text
floor occupancy
ceiling occupancy
interior occupancy
absolute RMS difference
normalized difference
trajectory timing difference
```

任何 normalized ratio 必须同时报告分子与分母。

---

## 九、不要提前规定新的“合格比例”

本轮禁止规定：

```text
interior occupancy 必须 > 80%
floor occupancy 必须 < 10%
```

之类硬标准。

原因是这会再次把转导设计成围绕评判标准优化的循环系统。

首先观察合法 World ensemble 自然产生的分布。

然后用：

```text
最强保留案例
最强丢失案例
最低幅轨迹
最高幅轨迹
最长/最短时间尺度轨迹
```

描述能力边界。

继续沿用：

> 不扔最高分和最低分。

---

## 十、T1-A 的停止点

T1-A 结束时只允许得到：

```text
TRANSDUCTION_V2_ARCHITECTURE_READY
```

不得得到：

```text
TRANSDUCTION_V2_VALIDATED
```

不得冻结最终：

```text
κ
offset
ceiling
adaptation tau
compression exponent
```

---

# 十一、随后进入 W1

W1 只设计 World v2。

不得读取：

```text
T1-A 候选函数的具体工作区间
G0 occurrence 成功率
```

来调 World。

World v2 的目标仍按 W0 结果：

\[
\boxed{
\text{增加局部自由度}
+
\text{解除时间尺度绑定}
+
\text{增加外部驱动复杂性}
}
\]

不增加新物理模态。

不强求混沌。

---

## 十二、World v2 的环境对象结构

继续保持已有模块化方式：

\[
\boxed{
Source
\rightarrow
Field
\rightarrow
Boundary
}
\]

其中 World 环境实例包括：

\[
X_W=
(
X_{\rm field},
X_{\rm source},
\theta_W,
U_{\rm ext}
).
\]

Skin 不属于 World。

World→Skin 的物理接触属于 boundary。

禁止创建一个巨型 `WorldV2` 类把全部对象揉在一起。

---

## 十三、World v2 必须增加的不是“场景数量”

不能做成：

```text
场景1
场景2
场景3
...
```

World v2 应成为条件采样池：

\[
(X_0,\theta,U_{\rm ext})
\sim P_W(\cdot|c).
\]

不同 episode 来自连续参数域。

尤其需要允许：

```text
多个热源位置
不同有限能量预算
不同启动/停止历史
不同空间分布
不同环境耗散
不同扩散时间尺度
不同外部驱动序列
```

但这些都仍属于同一热物理域。

---

## 十四、必须解除旧时间尺度锁定

W0 已指出当前：

\[
r_{\rm leak}
\]

与扩散参数存在固定比例绑定。

W1 必须使：

\[
\tau_{\rm diffusion}
\]

和：

\[
\tau_{\rm environment}
\]

成为独立物理参数。

然后允许：

\[
\tau_{\rm environment}
\ll
\tau_{\rm diffusion},
\]

\[
\tau_{\rm environment}
\sim
\tau_{\rm diffusion},
\]

\[
\tau_{\rm environment}
\gg
\tau_{\rm diffusion}.
\]

不是选一个“最佳比例”。

而是保留整个合法区域。

---

# 十五、World v2 先只做 Raw Boundary Qualification

W1 完成以后：

只观察：

\[
Y_B(t).
\]

不接 Transduction v2。

不接 G0。

测试：

\[
X_A(t_0)\neq X_B(t_0)
\]

而：

\[
Y_A(t_0)=Y_B(t_0)
\]

以后能否：

\[
Y_A^+\neq Y_B^+.
\]

同时测试不同 World 条件下：

```text
边界轨迹是否出现不同幅值
不同持续时间
不同恢复尺度
不同多峰/单峰结构
不同历史依赖
```

这些属于 World 资格。

---

# 十六、World v2 冻结后才进入 T1-B

此时构造：

```text
World v1 reference set
+
World v2 calibration set
+
World v2 held-out set
```

只有前两组允许用于 Transduction v2 参数估计。

held-out 条件禁止参与调参。

---

## 十七、T1-B 才真正选择 Transduction v2

在同一个 World ensemble 上比较 T1-A 候选族。

最终选择的不是：

> G0 触发最多的。

而是能够在合法 World 范围内表现出：

```text
不过度地板化
不过度顶棚化
不产生 baseline-zeroing 假放大
保留一部分历史差异
明确压掉另一部分自由度
跨 held-out World 仍保持同类性质
```

的最小物理结构。

---

# 十八、World–Transduction 共谋攻击

T1-B 必须做 cross-pair。

例如：

\[
W_A,W_B,W_C
\]

与：

\[
D_1,D_2,D_3.
\]

禁止只报告：

\[
W_A-D_A,\quad
W_B-D_B,\quad
W_C-D_C.
\]

必须交叉。

如果只有专配组合能工作：

```text
CO_ADAPTATION_RISK = HIGH
```

不得冻结。

---

# 十九、最终才重新接 G0

只有：

```text
WORLD_V2_RAW_QUALIFIED
TRANSDUCTION_V2_CROSS_WORLD_QUALIFIED
```

以后才重新运行：

\[
World
\rightarrow
Boundary
\rightarrow
D_{v2}
\rightarrow
G0.
\]

G0 保持原十神经元结构不改。

然后重新测：

\[
\xi^{occ}
\]

的：

```text
trigger
exit
rearm
duration
frequency
energy
```

---

# 二十、下一轮 Agent 实际任务

下一轮只做：

\[
\boxed{T1-A}
\]

不做 W1 实现。

交付：

```text
T1A_TRANSDUCTION_V2_CONTRACT.md
T1A_THERMORECEPTOR_Q1_REVIEW.md
T1A_CANDIDATE_FAMILIES.md
T1A_METRIC_CONTRACT.md
T1A_LEGACY_FAILURE_BASELINE.json
```

允许写 diagnostic prototype。

不允许写 production Transduction v2。

---

# 二十一、T1-A 必须保留本轮四个负结果

作为永久 regression：

```text
1. 双侧资格窗过窄
2. u_interior 合同未兑现
3. baseline-zeroing amplification artifact
4. downstream dynamic-range under-utilization
```

以后任何 Transduction v2 都必须与这些旧失败进行对照。

不得只汇报新方案的正结果。

---

# 二十二、研究纪律

这一阶段最重要的原则：

\[
\boxed{
\text{Transduction 不负责制造 World 的丰富度}
}
\]

以及：

\[
\boxed{
\text{World 不负责迎合 Transduction 的窗口}
}
\]

World 负责产生物理自洽的、不完备可观测的历史。

Transduction 负责对这些历史实施有限、可解释的物理采样与简并。

G0 再负责形成内部真实发生。

三者允许物理啮合，

但必须禁止通过共同调参制造成功。