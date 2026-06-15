# 影子层（内省层）数学建模

> [!IMPORTANT]
> 本文档是当前正式定义的一部分，描述影子层的**结构化实现**。
> 影子层 = 感觉-运动层的 21 神经元精确副本，由真实元件构成。
> DEGRADED 目标（层级变分沙盒）见 `modeling_shadow_dual_metric.md`。

---

## §1 结构

### §1.1 影子层的元件构成

影子层由与感觉-运动层**相同类型的元件**构成，参数不同：

| 元件类型 | 数量 | 配置差异 |
|---------|------|---------|
| Neuron | 21 | τ_RC 慢 10×，能量初始 0.5，VR 恢复率 0.5× |
| SynapticBundle | ~30 | 初始权重同主系统拓扑，跨轴 bundle w=0.001 |
| ECM | 3（enc/col/mot） | 热容 5×，PNN 成熟速率 0.5× |
| VascularCooling | 1 | 基础流量 0.2×，NVC 增益 0.5× |

影子层不含：MET、HairCell、Afferent（不直接接触外部）、Oscillator（无 CPG 驱动）、Binding（不检测超边——它看的是主系统的 Xin）。

### §1.2 拓扑

影子层的初始拓扑 = 感觉-运动层的 Enc→Col→Mot 子图的精确副本：

```
Shadow Encoding (12 neurons):
  s_enc_reg_{axis}, s_enc_irr_{axis}  ×6 轴

Shadow Column (6 neurons):
  s_col_{axis}  ×6 轴

Shadow Motor (3 neurons):
  s_mot_{x,y,z}

Shadow Bundles (轴内，初始 w ≈ 主系统权重的副本):
  s_enc_{axis} → s_col_{axis}    ×6
  s_col_{axis} → s_mot_{xyz}     ×6→3 映射

Shadow Bundles (跨轴，初始 w = 0.001，几乎沉默):
  s_col_{axis_a} → s_col_{axis_b}   ×C(6,2) = 15 对
```

跨轴 bundle 初始沉默——它们的存在是**结构提供的可能性**，由 Xin 驱动的 STDP 决定哪些被激活。

### §1.3 输入

影子层的唯一输入 = **主系统的 Xin 张力**：

$$I_{\text{shadow},i}(t) = \xi_i^{\text{main}}(t)$$

每个主系统 bundle 的 Xin 张力作为 `I_ext` 注入对应的影子 encoding 神经元。

影子层**不接收外部感觉输入**——它是一面朝内的镜子。

---

## §2 收缩动力学

### §2.1 驱动方程

影子层的 step() 和感觉-运动层完全相同：

1. **传播**：shadow bundles propagate（Xin 信号通过 memristor 权重流动）
2. **激活**：shadow neurons step（RC 电路更新膜电位）
3. **学习**：shadow bundles learn（STDP 更新权重）
4. **代谢**：shadow neurons 消耗能量，shadow ECM 更新温度

**收缩 = STDP 在 Xin 驱动下的自然结果：**

- 相关 Xin → 同时激活 → STDP LTP → 跨轴 bundle 增强（"靠近"）
- 不相关 Xin → 不同步 → STDP decay → 冗余 bundle 弱化（"分离"）
- 活跃度迁移：增强的跨轴 bundle 注入电流 → 目标神经元接管部分表征

### §2.2 能量消耗（E_remodel）

每次 STDP 权重变化消耗来源神经元的能量：

$$E_{\text{remodel}} = \kappa \cdot |\Delta w| \cdot |a_{\text{pre}}| \cdot |a_{\text{post}}|$$

$\kappa$ = 重塑成本系数（建议 $\kappa = 0.01$）。

当 $E_{\text{neuron}} < E_{\text{min,remodel}}$ → STDP 停止 → 收缩自然终止。

### §2.3 收缩不能无限的三重保障

| 机制 | 元件 | 效果 |
|------|------|------|
| 能量耗尽 | Neuron.energy → 0 | STDP 停止 |
| 权重饱和 | Memristor.w → w_max | 乘法软边界 Δw → 0 |
| PNN 冻结 | ECM.pnn_maturity → 1 | plasticity_gate → 0 |

---

## §3 静默突触与收缩路径记录

### §3.1 静默条件

当影子 bundle 的权重衰减到阈值以下：

$$w_k < w_{\text{silence}} \quad \wedge \quad \dot{w}_k < 0$$

bundle 不销毁，进入**静默状态**（silent synapse）。

### §3.2 静默快照

进入静默时存储：

$$\text{snapshot}_k = (w_k^{\text{silence}}, \; \xi_k^{\text{silence}}, \; t_{\text{silence}}, \; \text{source\_id}, \; \text{target\_id})$$

这就是**收缩路径记录**——弃置链路的结构残留。

### §3.3 条件唤醒

当新的 Xin 模式与静默快照中的 $\xi_k^{\text{silence}}$ 余弦相似度 > 0.8：

$$\cos(\xi_{\text{current}}, \xi_k^{\text{silence}}) > 0.8 \implies \text{reactivate}(k)$$

唤醒时恢复 $w_k = w_k^{\text{silence}}$，消耗 $E_{\text{reactivate}}$。

---

## §4 影子层 ECM

独立的三区域 ECM（encoding/column/motor），参数特化：

$$\text{thermal\_capacity}_{\text{shadow}} = 5 \times \text{thermal\_capacity}_{\text{main}}$$

$$\text{pnn\_rate}_{\text{shadow}} = 0.5 \times \text{pnn\_rate}_{\text{main}}$$

影子层的 PNN 成熟独立于感觉-运动层——影子层的学习窗口关闭更晚。

---

## §5 外部审计：闵可夫斯基时空间隔

### §5.1 神经时空间隔

外部审计工具定义（**不是内部机制**）：

$$ds^2_{ij} = -(c_{\text{neural}} \cdot \Delta t)^2 + d_{\text{struct}}(i,j)^2$$

$c_{\text{neural}}$ = 最快信号速度 = $1 / \tau_{\min}$
$d_{\text{struct}}$ = bundle 链路距离（层级跳数 × 衰减）

| $ds^2$ | 含义 | 因果状态 |
|--------|------|---------|
| $< 0$ | 类时间隔 | 信号能到达 |
| $= 0$ | 类光 | 恰好到达 |
| $> 0$ | 类空间隔 | 信号到不了 |

### §5.2 收缩 = 光锥展宽

影子层的跨轴 bundle 增强 → $d_{\text{struct}}$ 减小 → $ds^2$ 从正变负 → **类空间隔 → 类时间隔**。

新的因果路径在影子层中涌现 = "深层跨链接"。

### §5.3 洛伦兹因子

$$\gamma_{ij} = \frac{d_{\text{main}}(i,j)}{d_{\text{shadow}}(i,j)}$$

$\gamma > 1$ = 影子层中因果可达性更强
$\gamma_{ij}$ 的分布图 = 影子层收缩的全局画像

---

## §6 时间尺度

| 操作 | 频率 | 理由 |
|------|------|------|
| Xin 注入 | 每步（和主系统同步） | 影子需要最新的预测残差 |
| Shadow step() | 每 $k=10$ 步 | 慢时间尺度 |
| Shadow learn() | 每 $k=10$ 步 | 和 step 同步 |
| ECM 更新 | 每 $100k$ 步 | 更慢 |
| 静默检查 | 每 $100k$ 步 | 和 ECM 同步 |
| ds² 审计 | 每 $1000k$ 步 | 极慢，纯外部观测 |
