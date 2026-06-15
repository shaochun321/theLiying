# 批判审视：2026.5.17.txt 中的四大公式

## 总体评价

文档的文学性远超其科学严谨性。四个公式中：
- **1个精确** (公式2的数学形式)
- **1个部分正确** (公式1)
- **1个结构性正确但细节错** (公式3)
- **1个被实验证伪** (公式4)

---

## 公式一：赫布超图拓扑演化

$$\frac{dW_{ij}}{dt} = -\alpha \frac{\partial \text{Xin}}{W_{ij}} - \beta(T_s) \cdot W_{ij}$$

### 批判

| 声明 | 实际代码 | 判定 |
|---|---|---|
| "连结朝降低Xin方向梯度下降" | STDP 基于 pre/post timing，不对 Xin 求导 | ⚠️ **过度理想化** |
| "温度驱动突触收缩" | `maintain()` 中确实有 T_layer 依赖的收缩 | ✅ 正确 |
| "自由能最小化" | 系统没有显式 free energy functional | ⚠️ **类比，非实现** |

**实际情况**：代码中的 STDP 是标准的 `ΔW ∝ pre_trace × post_act`，加上 energy-gated pruning。它不是对 Xin 的梯度下降。Xin 影响的是张力驱动的果实激活，而不是权重更新方向。

**可挽救的公式**：
$$\Delta W_{ij} = \eta \cdot \text{pre}_i \cdot \text{post}_j - \beta(T_s) \cdot W_{ij} \cdot \mathbb{1}[E_{ij} < E_{threshold}]$$

---

## 公式二：泄漏积分器

$$I_c(t+1) = (1 - \lambda_c) I_c(t) + \gamma_c \cdot \ln(1 + |u_c(t)|) \cdot \text{sgn}(u_c(t))$$

### 批判

| 声明 | 实际代码 | 判定 |
|---|---|---|
| 数学形式 | 完全匹配 `IntegratorColumn.step()` | ✅ **精确** |
| λ 是常数 | λ_eff = max(0.001, λ_base - correction) | ⚠️ 遗漏了CPG矫正 |
| γ 从 lognormal 采样 | `math.exp(rng.gauss(0, σ))` | ✅ 正确 |
| "趋光性来自γ不对称" | **实验B证伪：等γ后轨迹不变** | ❌ **错误因果归因** |

**实际精确公式**（包含CPG矫正）：
$$I_c(t+1) = (1 - \lambda_c^{eff}(t)) \cdot I_c(t) + \gamma_c \cdot \ln(1 + |u_c(t)|) \cdot \text{sgn}(u_c(t))$$
$$\lambda_c^{eff}(t) = \max(0.001, \lambda_c^{base} - \kappa \cdot \text{CPG}_{slow}(t))$$

---

## 公式三：NMDA门控STDP

$$\Delta W = \eta \cdot \exp\left(-\frac{|\Delta t|}{\tau}\right) \cdot \Theta(\text{Xin}_t - \text{Threshold})$$

### 批判

| 声明 | 实际代码 | 判定 |
|---|---|---|
| 指数时间窗口 | `pre_trace` 指数衰减 ✓ | ✅ 近似正确 |
| Θ(Xin - threshold) 门控 | `motor_frozen` 布尔标志 | ⚠️ **不是连续的Xin阈值** |
| "NMDA代理" | 代码中没有电压门控 | ❌ **过度生物化解读** |

**实际机制**：motor 层在 babbling 阶段 freeze schedule 控制，不是 Xin 门控。STDP 在 `if not practice.motor_frozen:` 条件下运行，这是一个时间调度，不是张力阈值。

---

## 公式四：对称性破缺吸引子

$$\frac{\gamma_{acoustic}}{\lambda_{acoustic}} \ln\left(1 + \frac{c_a}{(L^*)^2}\right) = \frac{\gamma_{luminous}}{\lambda_{luminous}} \ln\left(1 + \frac{c_l}{(L^*)^2}\right)$$

### 批判

> [!CAUTION]
> **这个公式被实验直接证伪。**

| 声明 | 实验结果 | 判定 |
|---|---|---|
| "γ不等导致吸引子" | 等γ后 lever 完全一致 | ❌ **γ无效** |
| "L*由γ/λ比决定" | L*由 seed(babbling) 决定 | ❌ **预测变量错误** |
| "acoustic 1/r²" | acoustic 是 1/r | ❌ **物理事实错误** |
| "acoustic可被趋近" | 8/8 seeds acoustic从不最近 | ❌ **不可能** |

**正确的因果链** (实验证实)：
1. 衰减律: acoustic=1/r, thermal/luminous=1/r² → 梯度力不对称
2. 1/r²源梯度 ∝ 1/r³ (强引力) vs 1/r源梯度 ∝ 1/r² (弱引力)
3. reflex + babbling RNG → 系统被1/r²源吸引
4. seed 决定 thermal 还是 luminous

---

## 项目实际能产出的数理公式

基于代码和实验**已验证**的数学关系：

### 公式 I：积分器动力学 (已验证 ✅)

$$I_c(t+1) = \left(1 - \max(0.001, \lambda_c - \kappa \cdot \phi_{CPG}(t))\right) I_c(t) + \gamma_c \cdot \text{sgn}(u_c) \ln(1 + |u_c|)$$

- 实验证据：retention_ratio = 0.915~0.966, 能量守恒 residual=0.000000

### 公式 II：量源场方程 (已验证 ✅, ratio=1.000)

$$\Phi_c(\mathbf{r}) = \frac{A_c}{|\mathbf{r} - \mathbf{r}_c|^{n_c}}, \quad n_c = \begin{cases} 1 & \text{acoustic} \\ 2 & \text{thermal, luminous} \end{cases}$$

$$\nabla \Phi_c = -n_c A_c \frac{\hat{\mathbf{L}}}{|\mathbf{L}|^{n_c+1}}$$

### 公式 III：环流测度 (已验证 ✅, μ(G)>0 持续)

$$\mu(G) = \sum_c |I_c| \cdot \sum_m |a_m| \cdot \sum_e |a_e|$$

- 满足 $\mu(G) > 0$ 当且仅当积分器持续 AND 运动/编码层响应非零
- 自持测试: 源撤除后 persistence = 37%

### 公式 IV：结晶条件 (已验证 ✅)

$$\text{crystallize}(n) = \begin{cases} 1 & \text{if } \text{strength}(n) > \theta_s \text{ AND } \text{age}(n) > \theta_a \text{ AND } \mu(G) > 0.1 \\ 0 & \text{otherwise} \end{cases}$$

### 公式 V：新原点得分 (已验证 ✅, 计算误差=0.0)

$$S_{origin} = \text{confidence} \cdot \min(\mu(G), 5.0)$$

$$\text{crystallize}_{origin} = \mathbb{1}[\text{confidence} > 0.3] \cdot \mathbb{1}[\mu(G) > 0.5] \cdot \mathbb{1}[\text{balance} > 0.3]$$

### 尚未有公式的关键现象

| 现象 | 状态 | 需要 |
|---|---|---|
| 为什么 1/r 源永远不被接近 | 实验确认 | 梯度力分析 + 稳定性证明 |
| px_ 振荡而非衰减 | 自持测试观察到 | 闭环动力系统分析 |
| 为什么 thermal 和 luminous 各50% | 实验观察 | 对称破缺理论 |

---

## 对文档风格的批判

1. **"非线性具身拓扑动力学"** — 这不是一个已有的学科名称，是自造的
2. **"自然哲学的数学原理"** — 严重过度类比
3. **声称能投 Physical Review E** — 需要：
   - 至少一个被验证的解析预测（目前公式4被证伪）
   - 与已有理论的定量对比
   - 统计显著性（N>30 seeds 的分布）
4. **真正可发表的贡献**：积分器+衰减律→行为偏好的涌现，如果做好统计分析和解析推导
