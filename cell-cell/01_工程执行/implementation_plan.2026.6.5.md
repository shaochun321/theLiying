# 实施计划：第一批并行任务

## 执行顺序与理由

```
D1 (频谱分析) ──→ 先做，零风险，获取信息指导后续
      ↓
C1 (ν→DA)    ──→ 最小改动(~10行)，最大解锁（C3/C5/C8）
      ↓
C2 (Motor 侧向抑制) ──→ 修复最大结构缺陷（N_eff=1）
      ↓
C4 (驻波检测) ──→ 启用垫支判定
```

每个任务完成后 `git commit`，形成可回退的还原点。

---

## D1：Xin 频谱分析

**目标**：确认 Oto Xin 的 19-147 振荡是周期极限环还是混沌。

**方法**：
1. 跑 500k 步，每 100 步记录所有 bundle 的 Xin
2. 对 Oto Xin 时间序列做：
   - FFT（功率谱密度）
   - 自相关函数 $C(\delta)$
   - 最大 Lyapunov 指数估计（正=混沌，负=极限环）

**实现**：写一个独立的分析脚本（scratch），不改主代码。

**输出**：频谱图 + 判断（周期/准周期/混沌）。

---

## C1：影子层 ν → DA 调制

**目标**：让影子层的运动势 ν = dK/dt 调制 DA 释放量。

### 改动文件

#### [MODIFY] [variant_adapter.py](file:///d:/cell-cc/nexus_v1/circuit/variant_adapter.py)

**位置 1**：L625-636（DA 释放区域），在现有 xin_da_signal 释放之后，追加影子层 ν 的贡献。

```python
# 现有：xin_da_signal 驱动 DA 释放
if xin_da_signal > 0.001:
    self.dopamine.release(min(xin_da_signal, 0.5))

# 新增：影子层 ν 调制 DA
# ν > 0（误差增大）→ 额外释放 DA → 提高学习率（探索）
# ν < 0（误差减小）→ 不额外释放 → 降低学习率（收敛）
shadow_nu = self.shadow_sandbox._nu  # dK/dt, already computed
if shadow_nu > 0.001:
    # 映射 ν 到 DA 释放量：ν ∈ [0, 0.1] → release ∈ [0, 0.2]
    nu_da = min(shadow_nu * 2.0, 0.2)
    self.dopamine.release(nu_da)
```

**验证**：
- DA 浓度不再恒定在 baseline
- 当输入变化时 DA 应升高（ν > 0），稳定时回落

---

## C2：Motor 侧向抑制

**目标**：同轴 motor 之间加负权重连接，打破克隆对称性。

### 改动文件

#### [MODIFY] [motor_decision.py](file:///d:/cell-cc/nexus_v1/circuit/motor_decision.py)

在 `MotorDecisionLayer` 中新增 `LateralInhibition` 子系统。

```python
class LateralInhibition:
    """Winner-take-all competition within same-axis motors.
    
    Each motor inhibits all other same-axis motors proportionally
    to its own activation. Strongest motor suppresses others.
    
    BIO: Renshaw cells in spinal cord provide recurrent inhibition
    between motor neurons of the same pool.
    """
    
    def __init__(self, inhibition_strength: float = 0.3):
        self._strength = inhibition_strength
        self._active = True
    
    def compete(self, activations: List[float]) -> List[float]:
        """Apply lateral inhibition within a group.
        
        Args:
            activations: list of motor activations for ONE axis
            
        Returns:
            Inhibited activations (same length)
        """
        if len(activations) <= 1:
            return activations
        
        total = sum(abs(a) for a in activations)
        if total < 1e-6:
            return activations
        
        result = []
        for i, a in enumerate(activations):
            # Each motor is inhibited by the sum of all others
            others = total - abs(a)
            inhibition = self._strength * others / len(activations)
            result.append(a - inhibition * (1 if a >= 0 else -1))
        return result
```

#### [MODIFY] [variant_adapter.py](file:///d:/cell-cc/nexus_v1/circuit/variant_adapter.py)

**位置**：L354-363（motor 激活聚合处），在聚合之后、送入 MotorDecisionLayer 之前，对每个轴的 motor 分别施加侧向抑制。

```python
# 收集每轴的单独 motor 激活（不再直接求和）
axis_individual = {'x': [], 'y': [], 'z': []}
for key, mot in self.motor_neurons.items():
    if 'move_x' in key:
        axis_individual['x'].append(mot._activation_ema)
    elif 'move_y' in key:
        axis_individual['y'].append(mot._activation_ema)
    elif 'move_z' in key:
        axis_individual['z'].append(mot._activation_ema)

# 侧向抑制 → 打破对称性
for axis_key in axis_individual:
    axis_individual[axis_key] = self.motor_decision.lateral.compete(
        axis_individual[axis_key])

# 聚合为总轴力
axis_acts = [
    sum(axis_individual['x']),
    sum(axis_individual['y']),
    sum(axis_individual['z']),
]
```

**验证**：
- 2000 步后检查同轴 motor 的 EMA 方差 > 0（不再全同）
- 权重熵 > 0

---

## C4：驻波检测（O(1) 在线算法）

**目标**：用零交叉率检测 Xin 是否形成驻波。

### 改动文件

#### [MODIFY] [bundle.py](file:///d:/cell-cc/nexus_v1/circuit/bundle.py)

在 `BundleConfig` 中新增驻波检测状态：

```python
# Standing wave detection (O(1) online)
_xin_prev: float = 0.0
_xin_zero_crossings: int = 0
_xin_steps_since_reset: int = 0
_standing_wave_score: float = 0.0  # ZCR, higher = more periodic
```

在 `compute_xin()` 末尾追加：

```python
# Standing wave: zero-crossing rate of dξ/dt
dxi = self.config.xin_tension - self.config._xin_prev
self.config._xin_prev = self.config.xin_tension
if self.config._xin_steps_since_reset > 0:
    # Count sign changes of derivative
    if hasattr(self.config, '_dxi_prev_sign'):
        cur_sign = 1 if dxi >= 0 else -1
        if cur_sign != self.config._dxi_prev_sign:
            self.config._xin_zero_crossings += 1
    self.config._dxi_prev_sign = 1 if dxi >= 0 else -1
self.config._xin_steps_since_reset += 1

# Update ZCR every 1000 steps
if self.config._xin_steps_since_reset >= 1000:
    self.config._standing_wave_score = (
        self.config._xin_zero_crossings / 1000.0)
    self.config._xin_zero_crossings = 0
    self.config._xin_steps_since_reset = 0
```

**ZCR 解释**：
- ZCR ≈ 0：Xin 单调变化（无振荡）
- ZCR ≈ 0.5：高频噪声
- ZCR ∈ [0.05, 0.3]：有规律的振荡 → **驻波候选**

**验证**：跑 10k 步后检查 Oto bundle 的 standing_wave_score。

---

## 验证计划

### 自动化测试

```bash
# 1. 现有治理测试不能回归
python nexus_v1/tests/test_governance.py

# 2. 新增：DA 不再恒定
python -c "
from nexus_v1.circuit.variant_adapter import VariantCircuit
import math
c = VariantCircuit()
da_values = []
for i in range(5000):
    c.step({'yaw': 0.5*math.sin(i*0.001), ...}, 0.001)
    if i % 100 == 0:
        da_values.append(c.dopamine.concentration)
da_var = sum((d - sum(da_values)/len(da_values))**2 for d in da_values) / len(da_values)
assert da_var > 1e-6, f'DA still constant! var={da_var}'
print(f'DA variance = {da_var:.6f} ✓')
"

# 3. 新增：Motor 分化
python -c "
...
motor_emas = [m._activation_ema for k, m in c.motor_neurons.items() if 'move_x' in k]
var = sum((e - sum(motor_emas)/len(motor_emas))**2 for e in motor_emas) / len(motor_emas)
assert var > 1e-8, f'Motors still cloned! var={var}'
print(f'Motor variance = {var:.8f} ✓')
"
```

### 手动验证

- D1 频谱图目视确认周期性
- C1 后跑 100k 步观察 DA 轨迹
- C2 后跑 100k 步观察 $N_{eff}$ 变化
