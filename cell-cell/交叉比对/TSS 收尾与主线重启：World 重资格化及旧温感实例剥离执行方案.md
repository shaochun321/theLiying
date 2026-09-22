# TSS 收尾与主线重启执行方案
## World 重资格化、旧温感实例剥离、G0 恢复与 TSS 成果回接

### 0. 总裁定

从本轮开始：

```text
TSS_RESEARCH = FREEZE
K-07 = DO_NOT_START
F3/F5 = FROZEN
```

最新 F1 状态冻结为：

```text
F1_A8v2_PHYSICALLY_VALIDATED = CONDITIONAL
```

其用途为：

```text
生成资格审计参考实例
```

而不是：

```text
正式新生成元
主线必须采用的结构
后续生成元模板
```

主线重新启动。

但：

```text
不得从旧 P2 的温感链路直接续跑。
```

原因：

旧 P2 同时混合了：

```text
World 实例
温度物理
动态皮肤
D_i^sim
十神经元 G_i
Occurrence
关系原语
```

其中只有部分属于通用项目结构。

本轮首先把它们拆开。

---

# 1. 本轮建立四个正式状态

旧系统中的对象重新登记为：

| 对象 | 新状态 |
|---|---|
| 十神经元 BaseGenerator | `RETAINED_CORE` |
| OccurrenceClosure / trigger-exit-rearm | `RETAINED_CORE` |
| GeneratorTrajectory / 物理账本 | `RETAINED_CORE` |
| ThermalFieldGraph / 热源 / 热皮肤 | `LEGACY_WORLD_INSTANCE` |
| 温感 `D_i^sim` | `LEGACY_TRANSDUCTION_INSTANCE` |
| 旧 normalized World | `REQUALIFICATION_REQUIRED` |
| TSS occurrence→relation | `FROZEN_RELATION_SUBSTRATE` |
| TSS C1 | `FROZEN_RECURSION_RESULT` |
| A8-v2 / F1 | `FROZEN_QUALIFICATION_METHOD` |

关键原则：

> 温感实例可以保留作为回归样本，但不得继续承担“项目默认 World / 默认输入 / 默认基础生成路径”的资格。

---

# 2. Phase F0 — TSS 正式冻结

建立：

```text
TSS_FREEZE_2026-09-18.md
```

内容只登记事实。

至少冻结：

```text
Occurrence / Entry
H_tau
Theta relation
relation re-eventization
C1 engineering recursion
C1 reconstructibility
amplitude loss
cross-occurrence reconstruction
A8-v1 NOT_MET
A8-v2 criterion draft
F1 physical candidate result
known LIM XFAIL
all negative results
```

明确：

```text
C1 PASS
!=
new generator
```

以及：

```text
F1 physical validation
!=
A8 MET
!=
new generator
```

研究目录转为：

```text
tss/core/
tss/qualification/
tss/findings/
tss/archive/
```

此后除 bugfix / 回归修复：

```text
禁止新增 TSS 理论模块。
```

---

# 3. Phase M0 — 旧主线考古与结构剥离

本阶段不改动力学。

只回答：

> 旧 P2 中哪些东西是项目本体，哪些东西只是温感实验实例？

自动扫描：

```text
nexus_v1/generators/
world/
thermal*
skin*
P2*
```

输出：

```text
MAINLINE_COMPONENT_AUDIT.md
```

将每个组件归入以下类别：

```text
A. GENERIC_PHYSICAL_PRIMITIVE
B. GENERIC_GENERATOR_CORE
C. GENERIC_INTERFACE
D. THERMAL_SPECIFIC
E. WORLD_INSTANCE_SPECIFIC
F. LEGACY_RELATION
G. OBSERVATION_ONLY
```

重点核实：

```text
BaseGenerator
OccurrenceClosure
GeneratorTrajectory
SynapticBundle
collector
D_i^sim
ThermalFieldGraph
SkinThermalState
q_skin
kappa_i
r_prec
r_rho
```

禁止因为某个组件曾成功运行，就把：

```text
THERMAL_SPECIFIC
```

升级为：

```text
GENERIC
```

---

# 4. Phase M1 — 恢复 G0，但不重定义 G0

十神经元基础生成元不重新发明。

沿用已经建立的结构合同：

```text
10 neuron ensemble
+
SynapticBundle
+
collector
+
trigger / exit / rearm
+
physical trajectory ledger
```

以及接口：

\[
\mathcal G_i:
(u_i,z_i)
\mapsto
(\dot z_i,\xi_i^{occ})
\]

本阶段只验证：

```text
旧实现是否仍存在
接口是否仍完整
是否被后续 TSS 修改污染
测试是否仍可运行
```

不得重新讨论：

```text
G0 应该是什么
```

除非代码和冻结文档已经明显冲突。

---

# 5. Phase W0 — World 不再默认合格

旧 World 的状态正式改成：

```text
LEGACY_WORLD_V1
```

不再使用：

```text
WORLD_QUALIFIED
```

旧资格只保留为：

```text
QUALIFIED_FOR_OLD_P2A_LOCAL_OCCURRENCE
```

即：

> 它曾经足够产生一个局部真实发生。

不能推导出：

```text
适合规模研究
适合关系生成
适合多源区分
适合空间生成
适合长期组织生成
适合真实神经复杂度
```

---

# 6. World 重新资格化的问题

不要先写新 World。

先审计当前 World 能提供什么。

至少测量以下结构性质：

### W0-A 自由度

真实动态状态数：

\[
N_{\mathrm{dyn}}
\]

及实际活跃自由度。

检查当前 World 是否本质上只是：

```text
少数节点
+
单变量
+
近线性扩散
```

如果是，明确登记。

---

### W0-B 局部相互作用

检查：

\[
x_i(t+\Delta t)
\]

是否真正受到多个邻域/过程共同作用。

区分：

```text
independent channel
weakly coupled field
strong coupled field
```

---

### W0-C 时间尺度

统计实际出现的：

\[
\tau_1,\tau_2,\ldots
\]

不得所有 World 动力学都由一个 RC/一个衰减尺度控制。

如果只有单时间尺度：

```text
MULTISCALE_SUPPORT = NOT_ESTABLISHED
```

---

### W0-D 非线性

禁止为了“看起来复杂”主动加入混沌。

先测试当前 World：

```text
线性
弱非线性
强非线性
多稳
敏感依赖
```

分别处在哪里。

混沌不是资格前置。

---

### W0-E 可区分世界历史

这是最重要的一门。

构造不同世界历史：

\[
\Gamma_A^{world},
\Gamma_B^{world},
\Gamma_C^{world}
\]

要求它们不是单纯幅值变化。

然后观察经过局部支撑后：

\[
X_A^{support},
X_B^{support},
X_C^{support}
\]

是否仍然可区分。

如果：

\[
D_{world}(A,B)\gg0
\]

但：

\[
D_{support}(A,B)\approx0
\]

则记录：

```text
WORLD_TO_SUPPORT_COLLAPSE
```

不得让后端神经元“猜回来”。

---

# 7. 不预设新 World 一定需要多模态

本轮不要直接建设：

```text
温度 + 压力 + 光 + 声音 + ...
```

因为这很容易再次人为堆结构。

先判断当前 World 缺的是：

```text
自由度
耦合
非线性
多尺度
局部空间结构
外部驱动复杂性
```

中的哪一些。

只有实测证明单一物理场无法支撑目标现象时，才增加新的物理过程。

---

# 8. Phase W1 — World v2 最低要求

如果 W0 判定当前 World 不足，则设计：

```text
WORLD_V2
```

但 World v2 不以“更复杂”为目标。

最低要求是：

> 存在大量不同微观过程，同时允许形成可重复的局部有效结构。

要求至少具有：

```text
局部相互作用
开放边界
耗散
真实外部驱动
不同时间尺度
多个可独立变化的局部自由度
```

允许存在：

```text
noise
stochastic perturbation
nonlinear coupling
```

但不得硬要求：

```text
chaos
```

---

# 9. World v2 的成功标准不得是固定输出

禁止：

```text
刺激 A → 状态 1
刺激 B → 状态 2
```

作为 World 的主要成功标准。

因为这会重新变成分类器。

World 只负责产生：

\[
\Gamma^{world}(t)
\]

即真实物理过程。

资格重点是：

```text
过程丰富度
局部可追踪性
不同历史可区分性
同类历史统计等价性
耗散和能量来源
```

不预设语义类别。

---

# 10. Phase T0 — 转导层重新资格化

从 World 到 G0 中间建立通用接口：

\[
\mathcal D_i:
X_{local}^{world}
\rightarrow
u_i
\]

注意：

\[
\mathcal D_i
\]

不是温度换算器。

它是一个：

```text
typed physical transduction contract
```

旧：

```text
D_i^thermal
```

只是：

```text
D_i
```

的一种 legacy implementation。

---

# 11. 转导层红线

\(\mathcal D_i\) 只能完成：

```text
物理量转换
量纲转换
局部耦合
必要的物理滤波
```

不得完成：

```text
事件切分
threshold success label
burst classification
方向判断
World 类型判断
语义编码
```

这些仍由下游物理结构形成。

---

# 12. 保留温感链路，但只作基准

旧温感链路不得删除。

冻结成：

```text
LEGACY_THERMAL_REFERENCE
```

它以后用于：

```text
回归
比较
负控制
World v1/v2 对照
```

而不是主线输入。

这样以前大量工作不丢。

---

# 13. Phase G1 — 用新 World / Transduction 重新喂既有 G0

这一阶段才重新测试：

\[
\mathcal D_i
\rightarrow
\mathcal G_i
\]

不改 G0。

重新测：

\[
u_{\rm silent},
u_{\rm on},
u_{\rm work},
u_{\rm sat},
u_{\rm unsafe}
\]

以及：

\[
L_{\rm first},
f_{\rm occ},
N_{\rm occ},
t_{\rm exit},
t_{\rm rearm},
E_{\rm generator}
\]

但这次目的不是重新定义 G0。

而是判断：

> G0 是只在旧温感标定下工作，还是对新的物理输入合同具有结构稳定性？

---

# 14. G0 若失败，不立即改十神经元结构

如果新输入下失败：

第一顺位检查：

```text
World
D_i
scale
units
input envelope
```

只有证明：

```text
合法输入已进入 G0 工作域
```

而 G0 仍无法形成稳定 occurrence，才允许重新审查十神经元内部结构。

避免把上游问题错误修到生成元内部。

---

# 15. Phase S0 — 规模资格检查

这是本次回归主线新增的一门。

但暂时不建设“规模理论”。

只问：

> 当前十神经元 G0 是否只是一个孤立小电路，还是开始表现出可扩展的有效元性质？

测试：

```text
1 × G0
3 × G0
10 × G0
30 × G0
```

每个 G0 内部仍保持十神经元结构。

---

# 16. SCALE-0 不使用平均值作为唯一统计

同时记录：

\[
\mu(t)
\]

但不把均值设为主要生成标准。

增加：

\[
L_q(t),
U_q(t)
\]

即低/高持续边界。

推荐先记录：

```text
q = 1%, 5%, 95%, 99%
```

及边界附近物理质量：

\[
\rho_L,\rho_U
\]

但：

```text
不得预先规定哪一个 q 才正确。
```

---

# 17. SCALE-0 核心观察

寻找：

\[
D_{\rm micro}
\]

与：

\[
D_{\rm boundary}
\]

是否出现：

\[
D_{\rm micro}\uparrow
\]

同时：

\[
D_{\rm boundary}\downarrow
\]

即：

```text
微观轨迹越来越分散
宏观可达边界反而稳定
```

如果出现：

```text
MICRO_DIVERGENCE_MACRO_CONVERGENCE
```

只登记现象。

暂不宣布：

```text
新自然单位
粗粒化定律
重整化
混沌等效
```

---

# 18. 混沌的处理原则

混沌不作为构造目标。

本轮只允许：

```text
MEASURE
```

不允许：

```text
ENGINEER_CHAOS_TO_PASS
```

可以测：

```text
扰动增长
轨迹分叉
长期相关
状态熵
局部 Lyapunov 候选指标
```

但只有系统自然出现敏感动力学时才继续分析。

---

# 19. Phase R0 — TSS 回接点

只有 World、D_i、G0、SCALE-0 完成最低资格后，才重新接 TSS。

正式接口：

\[
\mathcal G_i
\rightarrow
\xi_i^{occ}
\rightarrow
\text{TSS}
\]

TSS 不接：

```text
raw World
raw skin
raw neuron membrane voltage
```

默认入口必须是：

```text
qualified physical occurrence
```

除非专项实验明确要求更低层。

---

# 20. 旧 P2 与 TSS 的对应审计

建立：

```text
P2_TSS_RECONCILIATION_MATRIX.md
```

逐项比较：

| 旧主线 | TSS | 判定 |
|---|---|---|
| \(\xi_i^{occ}\) | occurrence / entry | SAME / SUPERSET / DIFFERENT |
| \(\chi_i^k\) | occurrence identity | SAME / DIFFERENT |
| \(r_\prec^\tau\) | Hτ+Theta temporal relation | REPLACE / COEXIST |
| \(r_\rho^\tau\) | TSS 当前机制 | COVERED / NOT_COVERED |
| P2-C relation-relation | C1 | SAME / PARTIAL / DIFFERENT |
| relation qualification | A8-v2 | EXTENSION |

任何一项不得凭名字判断相同。

必须根据：

```text
input
state
equations
physical support
output
future effect
```

逐项比对。

---

# 21. TSS 回接后的原则

如果旧关系机制和 TSS 重复：

保留证据更强、物理闭合更完整者。

另一个：

```text
archive
```

如果两者表示不同关系：

允许并存。

禁止为了“架构整洁”强行统一。

---

# 22. A8-v2 在主线中的新位置

A8-v2 不再是下一阶段建设任务。

改成：

```text
qualification test
```

以后只有某个候选声称：

```text
我是新的生成深度
```

才调用 A8-v2。

它不是日常主链。

---

# 23. F1 在主线中的位置

F1 冻结为：

```text
REFERENCE_A8_POSITIVE_CONTROL
```

用途：

验证未来资格测试没有失效。

不自动植入：

```text
G0
relation layer
World
Shadow
Xin
```

---

# 24. 主线重新启动后的路线

新的主线顺序：

\[
\boxed{
World\ Qualification
}
\]

↓

\[
\boxed{
Generic\ Transduction
}
\]

↓

\[
\boxed{
Existing\ Ten\text{-}Neuron\ G0
}
\]

↓

\[
\boxed{
Physical\ Occurrence
}
\]

↓

\[
\boxed{
Scale\ Qualification
}
\]

↓

\[
\boxed{
TSS\ Temporal/Relation\ Substrate
}
\]

↓

\[
\boxed{
Relation\ Organization
}
\]

↓

\[
\boxed{
New\ Generator\ Qualification
}
\]

---

# 25. 明确暂停的内容

完成以上回接以前，不启动：

```text
Xin
Shadow
TOPRXin
运动势
K-07
K-06
F3/F5
正式空间生成元
高层组织命名
```

也不重新扩大温感系统。

---

# 26. 第一轮 Agent 实际只做 F0 + M0 + W0

不要一次把整个方案实现。

第一轮只交付：

```text
TSS_FREEZE_2026-09-18.md
MAINLINE_COMPONENT_AUDIT.md
WORLD_V1_REQUALIFICATION_REPORT.md
P2_TSS_RECONCILIATION_DRAFT.md
```

以及 World v1 的测量数据。

禁止这一轮：

```text
创建 World v2
修改 G0
修改 TSS
增加新物理原语
```

---

# 27. 第一轮必须回答的五个问题

最终只回答：

1. 旧 P2 中到底哪些组件真正通用？
2. 哪些组件实际上只是温感实例？
3. 旧 World 到底有多少有效动态自由度？
4. 它在哪一级把不同世界历史压平？
5. TSS 与旧 P2-B/P2-C 到底重叠多少？

回答完才决定 World v2 是否需要建设。

---

# 28. 停止条件

如果现有 World 被证明已经足以：

```text
产生丰富可区分局部过程
支持多时间尺度
支持不同历史
支持规模测试
```

则：

```text
WORLD_V2 = NOT_REQUIRED
```

不要为了“升级”而升级。

如果 World 不足：

才进入 W1。

---

# 29. 研究纪律

这次主线回归必须避免两个相反错误。

错误 A：

> 因为温感链路已经有很多代码，所以继续把整个项目当成温感系统。

错误 B：

> 因为温感只是实例，所以把以前所有成果推倒重来。

正确做法是：

\[
\boxed{
\text{保留已证明的通用结构，撤销未经证明的实例泛化。}
}
\]

最终目标不是获得一个“更复杂 World”。

而是得到：

> 一个足以让基础生成元、规模效应和关系生成在真实物理约束下接受检验的 World。