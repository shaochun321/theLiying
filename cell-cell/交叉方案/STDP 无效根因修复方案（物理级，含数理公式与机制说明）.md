# STDP 无效根因修复方案（物理级，含数理公式与机制说明）

**日期：** 2026-07-08
**性质：** 可执行架构修复方案（非参数调优）
**前置诊断：** STDP 无效根因复核报告（2026-07-08）+ DA=1.0修复方案评判（2026-07-08）
**目标：** 让 STDP 重新成为有意义的、能驱动行为涌现的学习机制


## 一、总体评估：两层锁，一把钥匙

### 1.1 当前架构的两个死锁

| 死锁 | 本质 | 表现 | 根因层级 |
|------|------|------|----------|
| **死锁一：DA 是死直流** | 三因子学习失去门控信息 | DA≡1.0（或Fix-2后DA≡0.0）| **底层（总闸门）** |
| **死锁二：学习目标冗余** | STDP 学的是硬连线已做的事 | 权重分化但行为不变（DR5=50%）| **顶层（架构拓扑）** |

**关键洞察**：两个死锁是独立叠加的，但**死锁一是死锁二的前提**——DA不携带信息时，无论STDP学什么（方向极性或增益调制），三因子规则都无法正确编码“何时该学、何时该停”。

### 1.2 修复路径

```
[先修总闸门] → DA恢复RPE编码 → [再改学习目标] → STDP产生行为增益
     ↓                    ↓                    ↓
 BCM滑动阈值        增益调制架构          DR5随情境变化
```

**死锁一（DA饱和）是本次修复的唯一焦点**。死锁二（学习目标冗余）在 DA 修复完成后单独处理（本文末给出方向）。


## 二、总闸门修复：DA 从死直流到 RPE 交流信号

### 2.1 病灶定位

DA 浓度被 shadow 层正反馈钉死在 1.0。病灶在 `variant_adapter.py` 中 shadow 层 `enc→col` 的 BCM 束（`stdp_lr=0.01, synapse_gain=10.0`），其权重更新规则**缺少滑动阈值（θ_M）**，导致无界发散：

```python
# 当前错误实现（伪代码）
Δw = η × pre × post  # 纯赫布，无约束，可无限增长
```

**问题本质**：当 post 持续活跃时，Δw 恒为正，权重单调增长 → calcium_rate 无界 → shadow_to_da 电流持续增加 → DA 被硬钳位至 1.0。

### 2.2 物理修复：BCM 滑动阈值

#### 数理公式

**突触权重更新方程（BCM 核心）**：

$$
\frac{dw_{ij}}{dt} = \eta \cdot x_i \cdot y_j \cdot (y_j - \theta_M)
$$

其中：
- $w_{ij}$：突触权重
- $\eta$：学习率（保留原 stdp_lr=0.01）
- $x_i$：突触前活动（enc 神经元激活值）
- $y_j$：突触后活动（col 神经元激活值）
- $\theta_M$：**滑动阈值**（动态量，非固定常数）

**滑动阈值动力学方程**：

$$
\tau_{\theta} \frac{d\theta_M}{dt} = y_j^2 - \theta_M
$$

其中 $\tau_{\theta}$ 是阈值滑动的时间常数（建议 1000 步，待实测校准）。

#### 物理机制

| 状态 | 条件 | 物理结果 |
|------|------|----------|
| 神经元兴奋过高 | $y_j > \theta_M$ | Δw > 0（LTP），权重增加，但 $\theta_M$ 同步升高 |
| 神经元活动适中 | $y_j = \theta_M$ | Δw = 0（稳态），无净变化 |
| 神经元活动低迷 | $y_j < \theta_M$ | Δw < 0（LTD），权重下降 |

**关键点**：$\theta_M$ 跟踪 $y_j$ 的平方（超线性），确保系统在 $\theta_M$ 附近存在唯一稳态。当 col 神经元持续活跃时，$\theta_M$ 升高使得 LTP 门槛变高，自动将网络活动压回稳态。

#### 实现代码（variant_adapter.py shadow 层）

```python
class ShadowBCMSynapse:
    """带滑动阈值的 BCM 突触"""
    def __init__(self, initial_weight=0.001, stdp_lr=0.01, theta_tau=1000.0):
        self.weight = initial_weight
        self.stdp_lr = stdp_lr
        self.theta_tau = theta_tau
        self.theta_m = 0.1  # 初始滑动阈值
    
    def update(self, pre_act, post_act, dt):
        # 1. 更新滑动阈值（慢动力学）
        # dθ_M/dt = (post² - θ_M) / τ_θ
        theta_delta = (post_act**2 - self.theta_m) * (dt / self.theta_tau)
        self.theta_m += theta_delta
        
        # 2. BCM 权重更新
        # dw/dt = η × pre × post × (post - θ_M)
        delta_w = self.stdp_lr * pre_act * post_act * (post_act - self.theta_m) * dt
        
        # 3. 应用更新（保留物理边界，避免数值溢出）
        self.weight += delta_w
        self.weight = max(0.0, min(1.0, self.weight))
```

### 2.3 配套修复：DA 浓度回归基线动力学

当前 `dopamine._concentration` 通过 `mean_da` 硬钳位设定，绕过 `modulator.step()` 的自然衰减。需改为带基线回归的微分方程：

#### 数理公式

$$
\tau_{DA} \frac{dC_{DA}}{dt} = I_{DA\_input} - (C_{DA} - C_{baseline})
$$

其中：
- $C_{DA}$：多巴胺浓度（输出）
- $\tau_{DA}$：DA 动力学时间常数（建议 10 步，使其能快速响应相位信号）
- $I_{DA\_input}$：DA 输入电流（来自 shadow 层输出 + 其他 DA 源）
- $C_{baseline}$：稳态基线（建议 0.1，代表紧张性 DA 发放）

#### 物理机制

- 没有净输入时（$I_{DA\_input} - (C_{DA} - C_{baseline}) = 0$），DA 浓度自然回归到 $C_{baseline}$。
- 输入突然增加（新热源、预期外奖励）→ DA 快速上升（相位爆发）。
- 输入突然降低（热源消失、预期落空）→ DA 快速下降（抑制 dip），为重新动员创造条件。

#### 实现代码（modulator.py）

```python
def update_dopamine(self, net_da_input, dt):
    tau_da = 10.0           # DA 浓度时间常数
    baseline_da = 0.1       # 紧张性稳态基线（需从 T-083 实测标定）
    
    # dC_DA/dt = (I_input - (C_DA - C_baseline)) / τ_DA
    da_delta = (net_da_input - (self._concentration - baseline_da)) * (dt / tau_da)
    new_da = self._concentration + da_delta
    
    # 物理极限保护（0-1 范围）
    self._concentration = max(0.0, min(1.0, new_da))
```

**注意**：移除原代码中的 `max(0, min(1, mean_da))` 硬钳位赋值，改用上述微分方程。`net_da_input` 仍为所有 DA 源（shadow_to_da、intake_to_da、satiety_to_da、hunger_to_da 等）的电流物理求和。

### 2.4 DA 恢复 RPE 编码的判定标准

修复后，DA 信号应满足以下物理特征（可通过 T-083 验证）：

| 场景 | DA 行为 | 物理含义 |
|------|---------|----------|
| 静止无热源 | $C_{DA} \approx 0.1$（基线）| 无奖励、无预测误差 |
| 接近新热源（phasic 爆发）| $C_{DA}$ 快速上升至 >0.6 | 正向 RPE（预期外奖励）|
| 贴源饱腹（fill 稳定）| $C_{DA}$ 回落至 0.1~0.2 | 预期内奖励，无新信息 |
| 撤源（热源消失）| $C_{DA}$ 快速 dip 至 <0.05 | 负向 RPE（预期落空）|
| 撤源后重新动员 | $C_{DA}$ 恢复至 0.1~0.3 | 基线回归，允许探索 |


## 三、后续：死锁二修复方向（DA 修复后实施）

**原则**：STDP 不应学“方向极性”（硬连线已做的），而应学“增益调制”（在什么情境下放大或抑制天生反射）。

### 3.1 当前问题（必须修改）

```
硬连线反射（w=0.3，冻结）：thermo_left → yaw_ccw（左热→左转）
STDP 学习的（w=0.2，可塑）：phasic_left → spinal_ccw → yaw_ccw（也是左热→左转）
                                                      ↑
                                              学习目标完全冗余
```

### 3.2 增益调制架构（改后）

```
硬连线反射（保留，基础驱动力）：
  thermo_left ────────────────────────────(G_eff)──→ yaw_ccw
                                              ↑
                                              │ 乘法门控
STDP 增益调制（学习“何时放大/衰减反射”）：
  phasic_left ──(STDP)──→ spinal_ccw ──(frozen, 增益调制节点)──┘
                                   ↑
                                   │ 上下文门控（饥饿度、CPC偏差）
```

### 3.3 关键物理机制

**乘法门控而非加法驱动**：

- **旧方案（加法，已失效）**：$I_{motor} = I_{thermo} + I_{spinal}$。STDP 仅贡献微小电流（0.1%），被淹没。
- **新方案（乘法，待实施）**：$I_{motor} = I_{thermo} \times G_{eff}(spinal)$。STDP 控制放大倍数，少量 STDP 权重可产生显著行为增益（如 3× 放大）。

**上下文门控**：$G_{eff}$ 的幅度受饥饿度、CPC偏差等情境变量调制，使学习产生“在饥饿时放大趋热，在饱腹时抑制”的情境依赖行为。


## 四、修复执行检查清单

### 阶段 0：总闸门修复（本文档§2）

- [ ] **BCM 滑动阈值**：修改 shadow 层 `enc→col` 的权重更新规则
  - [ ] 为每个 shadow col 神经元添加 `theta_m` 状态
  - [ ] 实现 `dθ_M/dt = post² - θ_M` 更新
  - [ ] 实现 `dw/dt = η × pre × post × (post - θ_M)` 更新
  - [ ] 保留权重物理边界（0-1）

- [ ] **DA 回归基线动力学**：修改 `modulator.py` 中的 DA 更新
  - [ ] 移除 `mean_da` 硬钳位赋值
  - [ ] 实现 `dC_DA/dt = (I_input - (C_DA - C_baseline)) / τ_DA`
  - [ ] 设置 `C_baseline = 0.1`，`τ_DA = 10`

- [ ] **回退 Fix-2**：
  - [ ] satiety_to_da 恢复至 `sg=-1.0`, `w=0.3`（或 `sg=-1.5`，但需重新推导）
  - [ ] 确认 `shadow_to_da` 维持 `w=0.01`（Fix-1 可保留，但不解决根本问题）

### 阶段 1：验证（T-083 重跑）

- [ ] 重跑 `exp_T083_da_reversibility.py`
- [ ] 确认撤源后 DA 可逆升降
- [ ] 确认新源出现时 DA 可产生相位爆发（>0.6）
- [ ] 确认基线 DA ≈ 0.1（非 0 或 1）

### 阶段 2：学习目标重构（死锁二修复）

- [ ] 三问审查通过
- [ ] 将 `spinal→yaw` 从加法驱动改为乘法门控
- [ ] 验证 DR5 随情境变化（饥饿 vs 饱腹）


## 五、最终裁定

> **DA 饱和是 STDP 无效的总闸门。BCM 滑动阈值修复从物理上解除 shadow 层无界发散，使 DA 从恒定直流恢复为相位交流（RPE 编码）。这是所有后续拓扑自组织、影子层超图、时空环流分离能够生效的前提。在 DA 验证通过之前，任何更高层的架构讨论都不具备工程意义。**