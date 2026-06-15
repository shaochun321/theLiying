# v41.1 Heterogeneous Medium + BCM + Feedback Emergence

## 日期
2026-05-18

## 路线
降级回升三连：heterogeneous_medium → BCM_learning_rule → emergent_feedback_topology

## 核心理念

### 异质介质
均匀介质 = 所有方向/通道平等。这不是真实世界。
真实组织有不同的密度、弹性、阻抗。
k(x), m(x) 的空间变化 → 折射 → 通道分化 → 位置依赖的感知光谱。

### BCM 学习规则
Simple EMA = 所有输入平等。BCM = 滑动阈值创造选择性。
θ_M 跟踪 ⟨y²⟩，只有超过阈值的输入才能 potentiate。
这是 Bienenstock-Cooper-Munro (1982) 解释 V1 方向选择性的规则。

### 反馈涌现
手工设计反馈拓扑 = 偷换结论。
全连接 + 小随机初始权重 + STDP → 拓扑自动涌现。
结果：transition/drift/gamma_desync/magnitude 存活 (0.93-0.96)，
potential_disp/churn 死亡 (0.00)。三种子一致 = 因果性结构。

## 测试结果
| Seed | acoustic→motor | luminous→motor | BCM w_range | θ_M range | 涌现反馈 |
|------|---------------|----------------|-------------|-----------|---------|
| 42 | 0.972 | 0.978 | [0.10,0.18] | [0.004,0.008] | 5/7 存活 |
| 123 | 0.976 | 0.979 | [0.10,0.18] | [0.005,0.009] | 5/7 存活 |
| 999 | 0.975 | 0.979 | [0.10,0.18] | [0.005,0.010] | 5/7 存活 |

## 降级变化
- RECOVERED: `heterogeneous_medium`
- RECOVERED: `BCM_learning_rule`
- RECOVERED: `emergent_feedback_topology` ×2
- 总降级: 44 → 40
