# Phase B P3 最终执行方案（含三项必做修正）

**日期**：2026-07-04
**版本**：Phase-B-P3-final
**性质**：结构性修复最终版，替代原P3-A/P3-C
**前置**：Phase B P0+P1完成，P3-B三问已闭环


## 一、三项必做修正

| 修正项 | 原方案 | 修正后 | 理由 |
| :--- | :--- | :--- | :--- |
| LTD束可塑性 | `plasticity=True` | `plasticity=False` | 三因子STDP下抑制性可塑束是“死胎”——犯错时权重衰减，做对时无LTP。刹车必须焊死 |
| Phasic信号实现 | Python浮点数相减 | 物理PhasicRelayNeuron + KCL加减 | 减法必须发生在细胞膜上，通过真实离子电流实现，纳入TSI审计 |
| 整流阈值 | Python `max(0, ...)` | ChannelConfig.v_threshold | 阈值是神经元的物理属性，不是Python层的数值截断 |


## 二、PhasicRelayNeuron物理规格

**结构**：新建4个PhasicRelayNeuron（对应front/back/left/right），region=0x03。

**输入**（两条冻结Bundle）：
- `relay → PhasicRelay`：兴奋性，synapse_gain=+1.0
- `slow_relay → PhasicRelay`：抑制性，synapse_gain=-1.0

**物理过程**：正负电流在PhasicRelayNeuron膜电容上完成KCL加减，膜电位反映relay与slow_relay的差值。仅当差值>0且超过v_threshold时，神经元发放——实现硬阈值整流，无需Python层数值截断。

**输出**：PhasicRelayNeuron的激活值作为C1趋热束的唯一信号源。


## 三、Push-Pull Bundle配置

**LTP通路**（可塑，保持不变）：
```
relay_right → yaw_cw ：plasticity=True,  synapse_gain=+1.0, initial_weight=0.1, weight_max=0.3
relay_left  → yaw_ccw：plasticity=True,  synapse_gain=+1.0, initial_weight=0.1, weight_max=0.3
```

**LTD通路**（冻结，必做修正）：
```
relay_right → yaw_ccw：plasticity=False, synapse_gain=-1.0, initial_weight=0.5
relay_left  → yaw_cw ：plasticity=False, synapse_gain=-1.0, initial_weight=0.5
```

**物理涌现**：右侧偏热→relay_right胜出→yaw_cw LTP（踩油门）+ yaw_ccw 被硬连线抑制（踩刹车）。左侧偏热时反转。LTP负责学习，LTD负责防超调。


## 四、修改清单

| 序号 | 修改项 | 约束 |
| :--- | :--- | :--- |
| 1 | 新建PhasicRelayNeuron类（膜电容KCL加减 + v_threshold整流） | 不可用Python浮点数相减 |
| 2 | 实例化4个PhasicRelayNeuron，铺设输入Bundle | 两条冻结Bundle/每个 |
| 3 | C1趋热束信号源切换为PhasicRelayNeuron | 替代原relay |
| 4 | relay_to_yaw新增两条LTD交叉抑制Bundle（frozen） | plasticity=False |
| 5 | 21/21回归 | 必须PASS |
| 6 | 100k验证 | 验收标准见下 |


## 五、验收标准

| 指标 | 目标 |
| :--- | :--- |
| 早期方向分化 | wR-wL > 0.01（20k内） |
| yaw超调 | < 30°超过最优朝向后可反转 |
| DR5 | >60%（全程平均） |
| 热源中心行为 | d<10区域有驻留，非穿越后远离 |