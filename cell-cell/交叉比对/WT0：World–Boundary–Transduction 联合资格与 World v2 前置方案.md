# WT0：World–Boundary–Transduction 联合资格轮
## World v2 建设前置执行方案

### 一、裁定

接受：

```text
WORLD_V2 = REQUIRED
```

作为“现有 World 结构最终需要升级”的阶段判断。

但不接受：

```text
NEXT = W1 IMPLEMENTATION
```

下一轮改为：

```text
WT0 = World–Boundary–Transduction Joint Qualification
```

顺序冻结为：

\[
WT0
\rightarrow
W1
\rightarrow
T0\text{-B}
\rightarrow
G0
\]

其中：

- WT0：冻结边界与转导合同，不建 World v2；
- W1：在合同约束下建设 World v2；
- T0-B：用 World v1 + v2 + held-out World 实例重新定标转导；
- 最后才重新接 G0。

禁止 World v2 和转导器同时调参互相迎合。

---

# 二、WT0 的核心问题

本轮只回答：

> World 中真实存在的隐藏动力学，在经过有限边界和当前 \(\mathcal D_i\) 后，到底保存了多少？

不是：

> 怎样让 G0 更容易触发。

不得以 occurrence 数量最大化作为转导优化目标。

---

# 三、建立 World–Boundary–Transduction 三对象合同

正式区分：

\[
X_W(t)
\]

完整 World 状态；

\[
Y_B(t)=B_W[X_W(t)]
\]

允许跨 World 边界传递的物理量；

\[
u_i(t)=\mathcal D_i[Y_B](t)
\]

基础生成元输入。

强制约束：

```text
G0 不得访问 X_W
D_i 不得访问 X_W hidden state
D_i 只能消费 Y_B
```

World 与内部之间唯一合法通路：

\[
X_W
\rightarrow
B_W
\rightarrow
Y_B
\rightarrow
\mathcal D_i
\rightarrow
u_i
\]

---

# 四、建立 Hidden-World Positive Control

将以下实验正式加入主线资格测试。

构造两段合法 World 历史：

\[
X_A(t_0)\neq X_B(t_0)
\]

同时要求：

\[
Y_A(t_0)=Y_B(t_0).
\]

然后统一撤去未来外部输入。

必须观察：

\[
Y_A(t>t_0)\neq Y_B(t>t_0).
\]

外部复验基准：

```text
World: three-point thermal field
history A: node0 drive
history B: node2 drive × approximately 1.996
```

在 \(t_0\)：

```text
boundary A = 36.29714981792817
boundary B = 36.29714981792817
```

隐藏状态：

```text
A ≈ [36.2971, 24.0154, 18.1847]
B ≈ [36.2971, 47.9353, 72.4499]
```

未来边界最大分叉：

```text
max |qA-qB| ≈ 18.68
```

该实验冻结为：

```text
WORLD_HIDDEN_DYNAMICS_POSITIVE_CONTROL
```

它证明：

> 即使完整 World 是确定动力系统，有限边界观测也可以表现出历史依赖。

不得把这个现象改造成 TSS 的 Hτ。

它属于 World 层。

---

# 五、建立 Boundary Replay Test

对任意 World 运行：

记录：

\[
Y_B(0:T).
\]

然后完全移除 World，只把这条边界物理轨迹重放给：

\[
\mathcal D_i+G_0.
\]

要求在相同下游初态与 RNG 条件下：

\[
Output_{\rm live}
=
Output_{\rm replay}
\]

到机器误差/允许浮点误差。

如果不同：

```text
HIDDEN_SIDE_CHANNEL = FAIL
```

必须查找：

```text
shared RNG
world object reference
global step
update order
node ID
coordinates
shared normalization state
future access
```

在 Replay PASS 前不得建设 World v2。

---

# 六、当前转导窗正式登记为信息瓶颈

当前：

\[
u=\operatorname{clip}(\kappa q+b,0,0.04).
\]

由现有 canonical 参数反解：

\[
u>0
\iff
q>40.01276
\]

且：

\[
u=0.04
\iff
q\ge69.09708.
\]

所以完整非钳位窗口只有：

\[
\boxed{
40.01276<q<69.09708
}
\]

宽度：

\[
29.08432.
\]

登记：

```text
LEGACY_TRANSDUCTION_ACTIVE_WINDOW
    q_floor = 40.01276
    q_ceiling = 69.09708
```

---

# 七、外部剂量攻击必须纳入 WT0

外部复验得到：

```text
drive 0.01–0.50
→ q_max approximately 0.76–37.96
→ u identically 0
→ G0 occurrence = 0
```

而：

```text
drive 1.25 → q_max ≈ 94.91
drive 50   → q_max ≈ 3796.27
```

虽然原始物理幅度相差约 40 倍，

但均大量进入：

```text
u = 0.04
```

G0 最终都只产生一次 occurrence，强输入区 duration 大致压缩到：

```text
approximately 390 steps
```

因此冻结：

```text
W0_E_TRANSDUCTION_BOTTLENECK = CONFIRMED
```

这不是说 clipping 一定错误。

而是说：

> 现有 clipping 是按旧六场景反推得到的 legacy 参数，不能再作为 World v2 默认接口。

---

# 八、WT0 不立刻重新标定 κ/b/clip

禁止本轮直接寻找：

```text
new kappa
new b
new clip
```

因为只用 World v1 重新定标会再次产生：

```text
World v1 ↔ D_i
```

共适应。

本轮只建立：

```text
TRANSDUCTION_REQUIREMENTS
```

不冻结最终参数。

---

# 九、审计 D_i 到底应该承担什么

特别检查当前结构中：

```text
skin_transduction.py
```

与：

```text
ThermalDeltaNeuron
haircell
```

是否存在功能重叠。

回答：

\[
\mathcal D_i
\]

究竟只是：

```text
单位/尺度转换端口
```

还是包含：

```text
真实动态换能
```

如果真正物理换能已经由 L1 ThermalDeltaNeuron / haircell 承担，

那么纯 affine+clip 映射不得再偷偷承担：

```text
事件筛选
幅值分类
动态范围选择
```

否则会形成双重感受加工。

输出：

```text
TRANSDUCTION_ROLE_AUDIT.md
```

---

# 十、不要用“最大信息保存”作为新标准

WT0 不要求：

\[
I(Y;u)
\]

最大化。

因为物理感受器本来就应该丢失信息。

真正要求：

```text
1. 丢失是明确的
2. 丢失来自物理/接口能力
3. 不是来自旧场景专用调参
4. 换合法 World 实例后不会完全失效
5. 被删除的自由度能够登记
```

目标是：

\[
\boxed{
controlled physical reduction
}
\]

而不是：

\[
lossless encoding.
\]

---

# 十一、建立“最高—最低”边界审计

不以平均性能决定 D_i。

对每组合法 World history 保存：

```text
最强保留案例
最强丢失案例
```

即同时寻找：

\[
D_{\rm preserve}^{max}
\]

和：

\[
D_{\rm loss}^{max}.
\]

禁止只汇报平均 distinguishability。

目的：

> 暴露接口真正能够保留和真正必然丢掉的两端边界。

---

# 十二、建立 Cross-Pair Matrix，但暂不建设 W2

WT0 只使用现有 World v1 的合法参数变化：

```text
initial state
drive position
drive amplitude
drive timing
kappa 合法范围
r_leak 合法范围
```

与同一套 D 合同交叉。

不得每个 World 配一套自己的 κ/b/clip。

如果只有：

```text
World_A + D_A
World_B + D_B
```

能工作，而交叉全部失败：

登记：

```text
CO_ADAPTATION_RISK = HIGH
```

---

# 十三、WT0 结束后才正式建设 W1

WT0 不否定 Agent 已找出的 World 缺口。

W1 仍应解决：

```text
1. 局部自由度数量不足
2. 独立时间尺度不足
3. 外部驱动复杂性不足
```

特别是当前：

\[
R_{\rm leak}\propto 1/\kappa
\]

固定比例关系必须解除。

扩散尺度和环境耗散尺度不能天然锁死成：

\[
\tau_{\rm leak}=10\tau_{\rm diffusion}
\]

这一种情况。

---

# 十四、W1 不需要增加新物理模态

保持单一热物理场即可。

不要增加：

```text
光
压力
声音
化学
```

除非后续实验证明单热场结构上无法满足需求。

World v2 的复杂度来自：

```text
更多局部自由度
独立时间尺度
真实空间局部作用
更丰富但仍物理合法的外部驱动
```

而不是增加感官类型。

---

# 十五、W1 不追求混沌

禁止：

```text
ENGINEER_CHAOS
```

允许自然测量：

```text
trajectory divergence
history dependence
multiscale relaxation
local nonlinear response
```

如果混沌自然出现，再研究。

如果没有：

```text
CHAOS_NOT_REQUIRED
```

---

# 十六、World v2 定位为条件采样池

正式接口候选：

\[
W
=
W(
X_0,
\theta,
U_{\rm ext}
).
\]

每次 episode：

\[
(X_0,\theta,U_{\rm ext})
\sim
P_W(\cdot|c).
\]

条件 \(c\) 只能限制物理允许域。

不能包含：

```text
必须产生 occurrence
必须形成 relation
必须令 G0 成功
```

采样完成以后，后续轨迹只由物理动力学推进。

---

# 十七、World v2 必须天然支持有限观察

完整状态：

\[
X_W.
\]

边界：

\[
Y_B=B_W(X_W).
\]

必须允许存在：

\[
X_A\neq X_B
\]

但：

\[
Y_A=Y_B.
\]

并允许未来：

\[
Y_A^+\neq Y_B^+.
\]

这不是 bug。

这是 World 的：

```text
HIDDEN_DYNAMICAL_DEGREES_OF_FREEDOM
```

资格。

---

# 十八、W1 不能根据旧转导窗调参

禁止：

```text
把 World 输出调到 40–69
```

禁止：

```text
把 World amplitude 调到刚好触发 G0
```

禁止：

```text
把 World 时间常数调成 G0/TSS 的 600
```

World v2 首先只接受：

```text
raw physical boundary tests
```

通过后才接转导。

---

# 十九、World v2 完成后进入 T0-B

这时才使用：

```text
World v1
+
World v2 training ensemble
+
held-out World v2 ensemble
```

共同定标 D_i。

必须保留 held-out 世界条件。

禁止全部 World 实例参与转导调参。

---

# 二十、T0-B 的成功条件

不是：

```text
G0 每次都发生
```

而是：

同一套 \(\mathcal D_i\) 在多个合法 World 实例下：

```text
不全部沉底
不全部饱和
保留部分隐藏历史产生的未来差异
同时明确删除另一部分差异
```

最后才测试 G0 occurrence。

---

# 二十一、G0 在本轮保持完全冻结

WT0/W1/T0-B 全程：

```text
BaseGenerator = READ_ONLY
OccurrenceClosure = READ_ONLY
TSS = FROZEN
```

不得因为 World/D 的问题修改 G0。

只有证明：

```text
World qualified
Boundary qualified
D_i qualified
u_i lies inside valid physical input domain
```

后 G0 仍失败，才能重新打开 G0。

---

# 二十二、本轮交付物

下一轮 Agent 只交付 WT0：

```text
WT0_WORLD_BOUNDARY_TRANSDUCTION_CONTRACT.md
WT0_HIDDEN_WORLD_POSITIVE_CONTROL.md
WT0_BOUNDARY_REPLAY_REPORT.md
WT0_TRANSDUCTION_ROLE_AUDIT.md
WT0_CROSS_PAIR_MATRIX.csv
WT0_INFORMATION_REDUCTION_REPORT.md
```

以及原始数据。

不得实现 World v2。

---

# 二十三、WT0 最终只能给三种裁定

```text
WT0_PASS
```

表示接口边界已明确，可开始 W1。

```text
WT0_SIDE_CHANNEL_FAIL
```

表示 World 与下游存在未声明耦合，先修接口。

```text
WT0_TRANSDUCTION_CONTRACT_UNRESOLVED
```

表示 D_i 的职责仍与 L1/haircell 重叠，不能开始 W1。

---

# 二十四、下一阶段

仅在：

```text
WT0_PASS
```

后：

```text
START W1_WORLD_V2
```

W1 只建设 World。

World v2 完成并冻结 raw boundary qualification 后：

```text
START T0-B
```

再重新定标转导。

---

# 二十五、核心研究纪律

必须避免两个循环：

第一种：

\[
World
\rightarrow
D
\rightarrow
G0
\rightarrow
\text{根据 G0 结果反调 World}
\]

第二种：

\[
World
\rightarrow
D
\rightarrow
\text{根据 D 的工作窗设计 World}
\]

正确顺序是：

\[
\boxed{
\text{先冻结因果接口}
\rightarrow
\text{独立建设 World}
\rightarrow
\text{跨 World 集合定标 D}
\rightarrow
\text{最后接 G0}
}
\]

这样允许 World 和感受链路真实啮合，

但不允许设计阶段形成隐藏共谋。