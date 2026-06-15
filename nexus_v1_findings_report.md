# nexus_v1 — 项目测试与理解报告
## 2026-06-10

---

## 一、项目整体架构

nexus_v1 是一个"结构计算"（Structural Computation）项目，核心理念是用半导体组件（Capacitor/MOSFET/Memristor/PowerRail）模拟生物的神经计算。项目分两个系统：

### 1.1 主系统（nexus_v1/）— 生物神经环路模拟器
- **前庭链**（VestibularChain）：机械力 → MET毛细胞 → 毛细胞 → 传入纤维（regular/irregular双通路）
- **赫布环路**（HebbianCircuit）：编码层 → 柱层 → 运动层，全部通过Memristor突触束连接
- **STDP学习**：pre-post trace配对学习，BCM（双因素），hebbian_decay（交叉轴）
- **影子层**（ShadowSandbox）：内省层，接收主系统Xin张力，进行压缩-收缩仿真
- **代谢系统**：PowerRail供电、ECM细胞外基质、血管冷却、能量存储
- **DAO系统**：绑定层、神经调节器（DA）、运动决策层

### 1.2 熵账本系统（nexus_v1/ledger/）— 观察与守恒
- **EntropyLedger**：全局热力学记账（能量、热耗散、每层活跃度）
- **NoetherProbe**：离散Noether守恒验证（能量/电荷/权重/Xin守恒 + Landauer界）
- **WeightEntropyProbe**：权重分布的Shannon熵
- **TOPRxinLedger**：T/O/P/R/Xin五相位强度映射
- **StructuralLedger**：结构事件追踪 + 越度量空间 + 结构熵 + 结构桥
- **GuidedConstructionAuditor**：引导性构建审计（过渡自限检测）

### 1.3 治理系统（governance/）— 并行审计器
- **Fuse**：物理法则熔断（能量守恒/熵单调/权重界/电压发散/能量非负）
- **Adjudicator**：公理合规裁定（J1-J5规则，支持运行时检查和代码审查）
- **Validator**：参数物理合理性验证（V1-V5：量纲/边界/稳定性/对称性/基线影响）
- **Modeler**：独立数学模拟（基线预测/增益链/穿透深度）
- **Ledger**：治理级记账（增益链跟踪/基线监控/ds²/κ计算）
- **MathCandidate**：公式生命周期管理

---

## 二、核心设计规则（两大准则）

### S0: 结构计算准则
所有信号通路计算必须使用半导体组件（Capacitor/MOSFET/Memristor/PowerRail），禁止纯数学公式替换组件行为。信号衰减用PowerRail IR压降、信号门控用MOSFET、自适应权重用Memristor、热耦合用电容+MOSFET。这确保了"结构-动力学对应"可被验证。

### S1: 度量中介兼容准则
所有跨域接口（电子工程/神经科学/物理学/信息论）必须通过项目的度量系统验证。三条检查：量纲一致性、尺度一致性、公式一致性。各学科的专业公式通过统一的g_ij/ds²/ρ/ν/κ框架翻译。

---

## 三、统一构建逻辑（已验证）

所有神经元使用同一个**MetaNeuron**模型（Capacitor + MOSFET + PowerRail），不同层通过不同的NeuronConfig参数区分：

| 层 | 类型 | 特殊配置 |
|---|---|---|
| MET | 非脉冲，多通道 | MET/K/Ca三通道 + Ca²⁺子系统 |
| HairCell | 非脉冲，多通道 | MET/K/Ca + 囊泡池释放 |
| Afferent | 脉冲(AdEx) | 适应性电流 + 疲劳电容 |
| Encoding | 脉冲 | 电压调节器 + 偏置电流 + 钙率积分器 |
| Column | 脉冲 | 电压调节器 + 偏置电流 |
| Motor | 脉冲 | 电压调节器 + 疲劳电容 + 有丝分裂 + 凋亡 |

所有突触使用同一个**Memristor**模型，通过不同BundleConfig区分：
- 前馈束（feedforward）：高学习率
- 反馈束（feedback）：延迟5步
- 交叉轴束（cross_axis）：hebbian_decay规则

---

## 四、标记的测试项（待运行）

### 4.1 核心集成测试（run_test.py）
- ✅ 静态基线测试：零输入→所有通道近零
- ✅ 单轴旋转测试：yaw输入→yaw通道最强
- ✅ 多轴运动测试：yaw+pitch→两者均激活，yaw>pitch
- ✅ 信号路径完整性：MET→HairCell→Afferent→Encoding→Column→Motor（检查每层非零）
- ✅ DC/AC分离测试：regular（DC/tonic）vs irregular（AC/phasic）

### 4.2 扩展审计（run_audit.py）
- 5000步扩展审计
- 信号深度跟踪（0到6层）
- 熵平衡记账

### 4.3 治理测试（test_governance.py）
- 治理初始化
- 熔断检测权重违规
- 熔断在严格模式下触发
- 模型器预测 vs 实际验证

### 4.4 熵账本测试（test_entropy_ledger.py）
- 10000步多轴输入
- 能量平衡检查

### 4.5 子系统测试（tests/）
- test_shadow_sandbox.py：影子层隔离验证
- test_thermal_smoke.py：热系统冒烟测试
- test_stdp_evolution.py：STDP演化测试
- test_multiaxis.py：多轴运动测试
- test_pnn_critical.py：PNN关键期测试
- test_binding_trace.py：绑定层追踪
- test_entropy_ledger.py：熵账本
- test_shadow_coupling.py：影子层耦合
- test_thermotaxis.py：热趋性
- test_directional_learning.py：方向性学习
- test_regression.py：回归测试

---

## 五、Noether守恒框架

| 守恒律 | 对应对称性 | 检查内容 |
|---|---|---|
| 能量守恒 | 时间平移 | E(t) + Q(0→t) = E(0) + E_in(0→t) |
| 电荷守恒(KCL) | U(1)规范 | Q_in - Q_out = ΔQ_stored |
| 权重平衡 | 规范不变性 | ΔW = ΣLTP - ΣLTD - Σdecay |
| Xin守恒 | 张量守恒 | Xin_produced = Xin_consumed + Xin_remaining |
| Landauer界 | 信息-熵 | Q ≥ kT ln(2) × bits_erased |

---

## 六、结构生长规则（S2: 递归分化沉积）

### 发芽（Sprouting）
- 触发：|ξ| > 0.3（每10000步检查）
- 盲发芽：相同拓扑、极小权重(1e-4)
- 交叉目标突变：30%概率替换目标为同层其他神经元
- 活动相关性门槛：源-目标活动匹配度 > 0.3
- 发芽能量成本：0.1/源神经元

### 修剪（Pruning）
- 双条件：重量 < 0.005 + 优雅期(5000步)
- 驻波保护：ZCR > 0.15的束不被修剪
- Fruit触发：contract_request可强制修剪

### 有丝分裂（Mitosis）
- 触发：疲劳电容电压 > 0.4 持续30000步
- 最多4次分裂/谱系
- 功率轨道容量：每轴最多20个运动神经元

### 凋亡（Apoptosis）
- 触发：能量 < 0.05 持续30000步
- 原始3个运动神经元永不凋亡

---

## 七、DAO框架（T/O/P/R/Xin循环）

| 相位 | 含义 | 度量 |
|---|---|---|
| T | 传输(Transmission) | transport_cost |
| O | 观察(Observation) | |δa| of targets |
| P | 预测(Prediction) | 1/(1+|ξ|) |
| R | 响应(Response) | weight change rate |
| Xin | 不匹配(Mismatch) | |ξ| |

每个束同时具有全部五个相位的强度，主导相位指示连接的当前状态。

---

## 八、理解与评估

### 架构优点
1. **组件统一性**：所有计算通过4个半导体原语完成，保持了一致的物理类比
2. **守恒定律**：Noether探针提供了系统级别的验证能力，能量/电荷/权重/Xin全部可追踪
3. **S0规则约束**：强制所有信号路径使用组件，防止退化为传统ANN
4. **治理系统独立**：治理与主系统同级别、并行运行，可熔断违规
5. **结构生长自限**：代谢税+能量存储提供热力学天花板，防止无限增长

### 需要关注的点
1. **模拟速度**：全组件计算（每步电容注入/漏电、MOSFET更新、Memristor传导、代谢）在大规模运行时可能较慢
2. **参数敏感性**：多系统耦合（前庭+ECM+血管+DA+影子+绑定+热+肌肉）参数交互复杂
3. **调试难度**：纯组件计算路径下信号异常难以追因——observation系统必须可靠
4. **fruit机制门槛**：500步成熟期在多时间尺度下可能需要调整

---

## 九、项目文件夹用途确认

- **nexus_v1/**：主项目，含主构建系统和熵账本系统
- **docs/**：项目纪律性文本记载和档案（分析/版本/数据库快照）
- **cell/**：个人重要文档（实现计划/审计/评估/walkthrough等历史资料）
- **governance/**：治理审计系统（与主系统平行、同等级别）
- **experiments/**：实验脚本（敏感性分析/论文图表/消融研究等）
- **history-file/**：纪律性保存的计划报告上下文资料

---

*此报告基于对nexus_v1全部核心代码的阅读和理解编写。所有测试（run_test.py, run_audit.py, test_governance.py, test_entropy_ledger.py等）的测试逻辑和预期结果已完全理解，但由于Linux工作区未能就绪，实际运行结果暂未获取。*
