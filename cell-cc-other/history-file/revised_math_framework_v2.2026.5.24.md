# nexus_v1 修订数理体系 v2.0

> 整合来源: C-001~C-005, G-001, Paper 1~3, 两份批判文档, 本轮讨论
> 状态: 草案, 待用户审批

---

## §1 双层架构

### 1.1 原则

```
客观层 (Objective): 物质结构 + 物理定律
  → 参与计算, 产生信号
  → 对项目(生物体)不显式
  → 项目不知道自己有阈值, 不知道F=ma
  → 但这些决定了它能感知什么、怎么运动

主观层 (Subjective): 输入流 + 内部构建
  → 项目通过自身输入流构建 ds², ν, Xin
  → 从不访问客观层的变量
  → 时空从输入流的关联中自生 (C-004)
```

### 1.2 客观层清单

| 组件 | 物理 | 代码 |
|------|------|------|
| 介质晶格 | 热扩散 ∂E/∂t = κ∇²E - λE | world.py (待迁移 Paper 3) |
| 身体 | F=ma, 惯性, 阻抗 Z=√(km)/d² | world.py Body |
| RC 膜 | dV/dt = (I - V/R) / C | neuron.py |
| MOSFET | 超阈: gm(V-V_th); 亚阈: exp | semiconductor.py |
| 忆阻器 | R = R_min + ΔR(1-w) | semiconductor.py |
| PowerRail | V_actual = Vdd - IR | semiconductor.py |
| 突触传播 | I = gain × Σ a_i × w_ij | bundle.py propagate() |
| STDP/BCM | Δw = f(pre, post, gate) | bundle.py learn() |
| 甲基化适应 | dM/dt = (T-M)/τ | thermal_membrane.py |
| PNN 成熟 | dPNN/dt = (target-PNN)/τ | ecm.py |
| CPG 振荡 | Hopf + ISI 同步 | oscillator.py |
| DA 调制 | concentration → threshold, lr | modulator.py |
| 相位门控 | g(t) = clamp((a_A-a_B)×α+0.5) | Paper 3, 待实现 |

### 1.3 主观层清单

| 构建 | 定义 | 来源 |
|------|------|------|
| 激活偏移 δa_i | a_i - a_baseline | 输入流偏离基线 |
| 度规 g_ij | w_cross(i,j) 经 BCM 学习 | 影子层跨轴权重 |
| 空间测度 ds² | Σ g_ij × δa_i × δa_j | 偏移的二次型 |
| 环流占比 ρ | μ_p / μ_total | 路径流量比 |
| 运动势 ν | dρ/dt | 占比变化率 |
| Xin | predicted - actual | 预测残差 |

---

## §2 主方法: ds² 和 ν

### 2.1 空间测度 (修订)

$$
ds^2 = \sum_{i,j} g_{ij} \cdot \delta a_i \cdot \delta a_j
$$

修正 (vs G-001 v1.0):
- ~~|a_i|~~ → **δa_i = a_i - a_baseline** (偏移, 有正负, 保留方向)
- g_ij 从 BCM 学习自然产生 (BCM 本身对称: |a_i|×|a_j|×(|a_j|-θ))
- g_baseline > 0 从基线活动中涌现 (不需要手动添加)

### 2.2 运动势 (修订)

$$
\nu_p = \frac{d\rho_p}{dt}, \quad \rho_p = \frac{\mu_p}{\mu_{\text{total}}}
$$

扩展:
- 旋度: ω_ij = ½(∂ν_i/∂a_j - ∂ν_j/∂a_i) → 旋转
- 散度: ∇·ν = Σ ∂ν_i/∂a_i → 卷缩 (<0) / 膨胀 (>0)
- 在离散框架中: 用差分代替微分

### 2.3 ds² ↔ ν 的连接

$$
T = \frac{1}{2} g_{ij} \dot{\delta a_i} \dot{\delta a_j}
$$

- T = 度规空间中的"动能"
- ν ∝ ∂T/∂(∂δa/∂t) → ν 是 δa 变化率在度规空间中的对偶
- 不需要显式的勒让德变换 → Xin 循环隐式完成这个计算

---

## §3 T/O/P/R/Xin 作为数学工具

### 3.1 替代变分

```
不需要:                     替代方案:
  δS = 0 (连续变分)     →   Xin → 0 (离散迭代)
  ∂L/∂x (梯度)          →   ξ = ŷ - a (残差)
  测地线方程             →   环流稳态路径
  哈密顿量               →   ρ 向量 + ν
  瑞利耗散               →   RC leak (已内建)
  光滑化 ReLU→Softplus   →   MOSFET 亚阈值已是指数(光滑)
```

### 3.2 Xin 的本质 (修订)

```
Xin ≠ 定量驱动力
Xin = 定性验证器

递归特性:
  每层都在消化 Xin → Xin 递归衰减 → 趋向 0
  Xin ≈ 0 = 度规正确 = 系统安静
  Xin ≠ 0 = 意外事件 = 触发新 T/O/P/R 循环

信息在:
  1. 何时 Xin 从 0 变为非 0 (时刻)
  2. 在哪些维度 (方向/结构)
  3. dXin/dt (急迫度)
```

### 3.3 P→R 的客观层实现

```
理论: C-003 (Nature 论文: CF 同步 → 去抑制 → 学习)

实现路径 (全部在客观层):
  1. compute_xin() 计算 ξ          ← 物理: 预测 vs 实际
  2. |ξ| → DA 释放 ∝ |ξ|           ← 物理: 残差 → 调质分泌
  3. DA → Modulator.concentration    ← 物理: 浓度积累
  4. concentration → alpha_lr        ← 物理: 调质 → 突触属性
  5. alpha_lr → plasticity_gate      ← 物理: 可塑性变化
  6. plasticity_gate → learn() Δw    ← 物理: 权重更新

  项目不知道 "ξ 大了所以学快了"
  只是物质化学过程的结果

  同步门控 (C-003.5):
  7. 绑定层共激活 → gate_sync        ← 物理: 双列同时超阈
  8. gate_sync × plasticity_gate      ← 物理: 乘性门控
  
  当前代码:
  步骤 1 ✅ (compute_xin 存在)
  步骤 2-6 ❌ (管线断开)
  步骤 7-8 ❌ (绑定输出未接学习门)
```

---

## §4 客观层物理 (Paper 3 迁移)

### 4.1 热介质

```
当前: T(r) = A / ||r - r_source||^n  (解析, 瞬时, 无穿透限制)
目标: ∂E/∂t = κ∇²E - λE               (扩散, 有延迟, 有穿透深度)

Paper 3 参数:
  (m=5.0, k=0.2, γ=0.02) → v=0.4, L_pen=0.71

迁移到 nexus_v1:
  World 中添加热介质晶格
  热源注入能量 → 扩散传播 → 身体位置采样
  ThermalMembrane 感知的是晶格在身体处的能量值
  不再是 A/r^n
```

### 4.2 阻抗匹配

```
当前: body.mass=1.0, body.total_volume=9 (不参与计算)
目标: Z_body = √(k_b × m_b) / d_b²
      T = min(1, 2Z_body / (Z_body + Z_medium))

迁移:
  身体的物理属性 (质量, 刚度) → 决定信号传输效率
  信号进入身体时经过阻抗匹配 → 部分反射
  这解决尺度问题: 身体的物理属性自然影响感知灵敏度
```

### 4.3 CPG 相位门控

```
当前: VPO 调制前庭增益 (乘性)
目标: g(t) = clamp((a_A - a_B) × α + 0.5, 0, 1)
      s_gated(t) = s_raw(t) × g(t)

迁移:
  VPO 的输出不是增益调制 → 是通过/截止门控
  信号只在 "开窗" 期间进入电路
  = TRN 的物理实现 (Paper 3 §4.4)
  → P 相的 "选择" 从物理门控中涌现
```

---

## §5 基线活动 (运动势垫支)

### 5.1 问题

```
当前: 无输入 → V < V_th → activation = 0 → 系统沉默
应该: 无输入 → 基线活跃 → δa = 0 → "静止"状态 (非沉默)
```

### 5.2 客观层解决

```
不是添加 baseline 参数
而是确保物理结构产生基线:

方案 A: bc_current (偏置电流)
  已存在: NeuronConfig.bc_current
  Enc/Col = 0.001, Motor = 0.01
  稳态: V_ss = bc_current × R_leak = 0.001 × 5 = 0.005
  → V_ss = 0.005 < V_th = 0.3 → 仍然沉默!
  
  需要: bc_current = V_th / R = 0.3 / 5 = 0.06
  → V_ss = 0.06 × 5 = 0.3 → 恰好在阈值
  → 任何扰动 → activation > 0

方案 B: PowerRail Vdd
  当前 Vdd = 1.0, R_internal = 0.1
  如果 Vdd → 膜电位基线
  → 需要 Vdd 与 V_th 的关系正确

方案 C: 亚阈值活动
  MOSFET 亚阈值: I ∝ exp((V-V_th)/(n·VT))
  V_th=0.3, n=1.5, VT=0.026
  当 V=0.2 → I = exp((0.2-0.3)/0.039) = exp(-2.56) ≈ 0.077
  → 亚阈值活动 > 0!
  
  但当前是否被忽略了？
  需要检查: activation 是否取自 MOSFET.conduct() 还是 max(0, V-V_th)
```

---

## §6 问题盘点

### 6.1 架构级 (必须解决)

| # | 问题 | 当前状态 | 解决方向 | 优先级 |
|---|------|---------|---------|--------|
| A1 | P→R 断裂 | Xin 算了没人用 | Xin→DA→plasticity_gate | ★★★★★ |
| A2 | 基线活动为零 | bc_current 太小 | 调整 bc_current 或用亚阈值 | ★★★★★ |
| A3 | 热场是解析公式 | A/r^n 瞬时 | 迁移 Paper 3 热扩散晶格 | ★★★★ |
| A4 | 身体无物理属性 | mass/volume 不参与计算 | 阻抗匹配 Z_body | ★★★★ |
| A5 | 绑定层→学习门未接 | C-003.5 第三因子 | bind→plasticity_gate | ★★★★ |

### 6.2 度规级 (重要但可延后)

| # | 问题 | 当前状态 | 解决方向 | 优先级 |
|---|------|---------|---------|--------|
| M1 | ds² 用 \|a\| 非 δa | 无基线, 两者等价 | 先解决 A2 → 自然解决 | ★★★ |
| M2 | w_cross 对称性 | BCM 自然对称 | 验证, 非强制 | ★★ |
| M3 | ν 只有标量, 无旋度 | 未计算 ω_ij | 在 CirculationMeter 中添加 | ★★★ |
| M4 | κ 收缩度公式 | 用 \|a\|, 非 δa | 依赖 A2 | ★★ |

### 6.3 尺度级 (依赖 A3/A4)

| # | 问题 | 当前状态 | 解决方向 | 优先级 |
|---|------|---------|---------|--------|
| S1 | 前庭链 5 层衰减到零 | col_oto ≈ 0.0002 | A2+A4 解决后重新评估 | ★★★ |
| S2 | Motor 同步 | 3 Motor 等权 | 需噪声 + A5 解决 | ★★★ |
| S3 | 热穿透无限 | 解析公式无限远 | A3 解决 | ★★★ |

### 6.4 理论级 (长期)

| # | 问题 | 当前状态 | 解决方向 | 优先级 |
|---|------|---------|---------|--------|
| T1 | 递归链身份判别 | 无法区分"同链"/"新链" | 需要形式化定义 | ★★ |
| T2 | PNN 无解冻机制 | 冻结 = 永久 | DA→PNN 降解 (生物: 糖皮质激素) | ★★ |
| T3 | Xin→结构变化触发规则 | fruit lifecycle 效果微弱 | 重新设计 fruit 或替代机制 | ★★ |
| T4 | 诺特异常的离散形式 | A = \|dμ/dt\|/J 存在 | 验证与 Paper 3 结果一致 | ★ |

---

## §7 实施路线建议

```
Phase 1: 基线与管线 (A1 + A2)
  1. 调整 bc_current → 基线活动 > 0
  2. Xin → DA → plasticity_gate 管线
  3. 绑定共激活 → 学习门
  → 验证: 前庭列层活跃, 学习受 Xin 调制

Phase 2: 客观层物理 (A3 + A4)
  4. 热扩散晶格替代 A/r^n
  5. 身体阻抗匹配
  → 验证: 热穿透有限, 身体物理属性影响感知

Phase 3: 度规验证 (M1~M4)
  6. 基线存在后, ds² 自然用 δa
  7. 验证 BCM 产生的 w_cross 对称性
  8. CirculationMeter 添加旋度计算
  → 验证: ds² 能区分方向, ν 能描述旋转

Phase 4: 耦合测试 = Procedure P
  9. 静止热源 + 随机游走
  10. 前庭 × 热梯度 → 中心/带宽 涌现
  → 验证: 方向知识从 P 中构建出来
```
