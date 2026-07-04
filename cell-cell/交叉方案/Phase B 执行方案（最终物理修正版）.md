# Phase B 执行方案（最终物理修正版）

**日期**：2026-07-04
**版本**：Phase-B-final-2
**性质**：结构性修复，替代原选项A/B/C及DirectionalComparator方案
**前置**：Phase A完成（region分配），200k基线数据揭示relay_to_da饱和、yaw漂移、DR5伪正


## 一、核心修正逻辑

200k基线实验暴露的缺陷，根源不在STDP参数，而在系统缺少物理合法的方向性信号路径。全局标量DA无法为空间分布的热感受器提供方向特异性纠正信号，而Actor层缺失可塑性的转向缆线，导致DA的价值评估无法转化为方向性行为强化。

本方案通过三项结构性修复，使方向特异性从感知层的侧向抑制中涌现，使DA回归因果事件标记的物理身份，使Actor获得被奖励塑造方向盘的物理能力。


## 二、修改清单

| 优先级 | 修改项 | 目标 | 文件 |
| :--- | :--- | :--- | :--- |
| P0 | Relay层侧向抑制网络 | 物理斩断多通道同步激活，Winner-Take-All | variant_adapter.py |
| P0 | 切除CPG→DA周期驱动 | DA回归RC-4微分差减触发（dT/dt>0） | variant_adapter.py |
| P0 | DR5重定义为距离变化指标 | 测量真实接近行为 | 实验脚本 |
| P1 | 铺设relay→motor_yaw可塑性缆线 | Actor获得方向性学习能力 | variant_adapter.py, hebbian.py |
| P2 | HC-023替代（Renshaw侧抑制） | 清除Motor注入硬编码 | variant_adapter.py（延后）|


## 三、P0修改细节

### 3.1 Relay层侧向抑制网络（Winner-Take-All）

**物理结构**：在4个relay神经元（front/back/left/right）之间建立相互抑制的硬连线Bundle。每条连接为负权重、冻结、不可塑。

**涌现机制**：哪怕右侧温度仅比左侧高0.1°C，relay_right的膜电位也会率先上升，通过抑制性连接将relay_left的膜电位压在阈值之下，实现物理静音。每次只有唯一胜出的relay通道能获得pre_trace，独享后续DA带来的LTP。全盘饱和从物理层面被根除。

**Bundle配置**（四条）：

| Bundle ID | 源 | 目标 | synapse_gain | initial_weight | plasticity |
| :--- | :--- | :--- | :--- | :--- | :--- |
| relay_lateral_inh_rl | relay_right | relay_left | -1.0 | 0.3 | False |
| relay_lateral_inh_lr | relay_left | relay_right | -1.0 | 0.3 | False |
| relay_lateral_inh_fb | relay_front | relay_back | -1.0 | 0.3 | False |
| relay_lateral_inh_bf | relay_back | relay_front | -1.0 | 0.3 | False |

**生物依据**：视网膜水平细胞/嗅球僧帽细胞的侧向抑制网络。REF: Hartline & Ratliff 1957 J Gen Physiol。

### 3.2 切除CPG→DA周期驱动

**当前问题**：CPG 2Hz节律周期驱动DA，导致DA与热通量变化失去因果锁相，STDP剪断突触（-82% LTD事件）。

**修改**：移除CPG对DA的直接驱动，DA恢复为仅在dT/dt > 0（温度正在上升的瞬间）时由RC-4微分差减电路触发Phasic爆发。

**物理身份**：DA不再是周期性节拍器，而是**真实因果事件的标记信号**——只有当环境温度正在朝向有利于生存的方向变化时，DA才释放。这恢复了STDP学习所依赖的因果锁相。

### 3.3 DR5重定义为距离变化指标

**原DR5**：`(T_r - T_l) * bv[x] + (T_f - T_b) * bv[y] > 0`（patch温差点积，伪正率100%）

**新DR5**：`d(t) < d(t - Δt)`的步数比例，Δt=1秒（1000步）。纯几何真值，直接测量body是否在接近热源。

**验收**：新DR5从基线44.1%提升到>60%。


## 四、P1修改细节：铺设relay→motor_yaw可塑性缆线

**物理结构**：建立relay→motor_yaw_ccw和relay→motor_yaw_cw的可塑性Bundle，受DA门控的STDP学习。

**因果关系**：
- body随机向右偏转→右侧皮肤升温→relay_right胜出（侧向抑制）→relay_right产生pre_trace
- 右侧升温触发dT/dt>0→DA Phasic爆发（全局LTP门控）
- 此时只有relay_right→motor_yaw_cw的突触上残留着刚放过电的eligibility trace
- STDP结算：因果律锁定，该路径发生猛烈LTP

**Bundle配置**（两条，可塑）：

| Bundle ID | 源 | 目标 | initial_weight | stdp_lr | plasticity |
| :--- | :--- | :--- | :--- | :--- | :--- |
| relay_right_to_yaw_cw | relay_right | motor_yaw_cw | 0.1 | 0.005 | True |
| relay_left_to_yaw_ccw | relay_left | motor_yaw_ccw | 0.1 | 0.005 | True |

**与其他组件的衔接**：
- relay侧向抑制确保每次只有一侧relay激活，方向特异性自然涌现
- DA的RC-4微分触发确保LTP仅在温度上升时刻发生
- 此Actor缆线与已有的C1趋热束（phasic_relay→spinal_turn）在后续阶段可整合，当前独立验证


## 五、100k验证实验

**配置**：单热源[70,50,25]，body起始[50,50,25]，DT=0.001，STEPS=100,000。

**验收标准**：

| 指标 | 基线（200k） | 目标（100k） |
| :--- | :--- | :--- |
| relay层多通道同步激活 | 始终同步 | 每次仅1个relay激活 |
| wR - wL（relay_to_da分化） | 0.0000 | >0.01（右偏时应为正） |
| DR5（新定义） | 44.1% | >60% |
| yaw偏转方向 | 持续漂移远离 | 向热源方向偏转 |
| DA爆发模式 | CPG周期性 | dT/dt>0事件驱动 |


## 六、执行流程

```
1. 修改 variant_adapter.py：
   - 新建4条relay侧向抑制Bundle（frozen）
   - 切除CPG→DA连接，恢复RC-4微分触发
2. 新建relay→motor_yaw可塑性Bundle（2条）
3. 修改实验脚本：DR5重定义为距离变化指标
4. 运行21/21回归 → 必须PASS
5. 运行100k验证实验 → 记录relay激活模式、wR-wL、DR5
6. 判定：
   - 若DR5>60%且wR-wL>0.01 → 进入500k长程验证
   - 若DR5无改善 → 检查RC-4微分触发是否生效
   - 若relay仍同步激活 → 增大侧向抑制gain（-1.0→-2.0）
```


## 七、与原方案的差异总结

| 原方案 | 本方案 | 理由 |
| :--- | :--- | :--- |
| 降低stdp_lr + 增强LTD | 建立relay侧向抑制 | 参数调整不解决拓扑死局 |
| 新建DirectionalComparator | 废弃 | 负电压会导致超极化封锁，推挽结构复杂 |
| 方向特异性DA神经元 | 保持DA全局标量 | 侧向抑制使每次仅一个relay获得pre_trace，DA无需分裂 |
| CPG继续驱动DA | 切除，恢复RC-4 | DA必须回归因果事件标记 |
| relay→motor无直接连接 | 铺设可塑性Actor缆线 | Critic的价值需Actor执行 |


## 八、关键提醒

1. **侧向抑制增益可调**：若-1.0不足以产生清晰的Winner-Take-All，可增至-2.0。但需注意过强抑制可能导致所有relay被静音，需在验证中观测。
2. **RC-4微分触发需验证**：恢复后应确认DA仅在dT/dt>0时爆发，而非持续或周期性。
3. **Actor缆线的初始权重**：0.1为保守值，若热趋性出现但转向幅度不足，可在后续实验中逐步提高。
4. **ν的远期整合**：当系统热趋性稳定后，可将全局ν作为抑制性底噪打入relay侧向抑制网络，使系统在困惑时（ν>0）压制所有确定性动作，仅保留随机探索——这符合已确立的ν极性反转原则。当前版本不实施此项，预留接口即可。


**本方案是热趋性学习的结构性修复最终版。它放弃了对STDP参数的雕琢，转而从感知层（侧向抑制）、调制层（DA因果化）和执行层（Actor缆线）三个物理层面重建方向特异性信号路径。执行后，系统将首次具备从局部温差中提取方向信息，并将其转化为定向运动强化的完整物理链路。**