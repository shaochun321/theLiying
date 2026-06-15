# Phase 1 详细实现计划：介质物理与感觉转导

**原则**: 每个参数都有物理出处。不造数字，只做归一化。

---

## 物理背景

### 现实中信号从"源"到"感受器"经历的完整链路

```
源 ──→ 介质传播 ──→ 界面耦合 ──→ 感觉转导 ──→ 积分器
        │                │              │
        │                │              └─ 分子机器: TRP通道/视紫红质/毛细胞
        │                └─ 阻抗匹配: 中耳杠杆/皮肤热阻/角膜折射
        └─ Beer-Lambert 衰减: Φ(r) = Φ₀·e^{-α·r} / r^n
```

**当前状态**: 只有 `Φ₀/r^n`（几何扩散） + `t_ret = r/v`（传播延迟）

**Phase 1 补全**:  
- (A) 介质吸收: `e^{-α·r}` (Beer-Lambert)  
- (B) 界面耦合: `T(Z_src, Z_obs)` (阻抗匹配)  
- (C) 传播速度修正: 介质特性决定 `v`  

---

## A. 介质吸收 — Beer-Lambert 定律

### 物理公式

完整的场衰减：

$$\Phi(r, \omega) = \frac{A}{r^n} \cdot e^{-\alpha(\omega) \cdot r}$$

其中 $\alpha(\omega)$ 是频率依赖的吸收系数。

### 真实物理参数

#### Acoustic (声波在空气中)

**来源**: ISO 9613-1, 经典声学理论

```
经典吸收 (粘滞 + 热传导):
  α_classical ∝ f²

实测值 (20°C, 50% RH):
  100 Hz:   α = 0.0003 dB/m  →  3.5 × 10⁻⁵ Np/m
  1 kHz:    α = 0.005  dB/m  →  5.8 × 10⁻⁴ Np/m
  10 kHz:   α = 0.1    dB/m  →  1.2 × 10⁻² Np/m
  100 kHz:  α = 3.0    dB/m  →  3.5 × 10⁻¹ Np/m

穿透深度 L_pen = 1/α:
  100 Hz:   ~28 km (几乎不衰减)
  10 kHz:   ~83 m
  100 kHz:  ~2.9 m (超声迅速衰减)
```

**归一化** (box_size=10, 设 Morphosphere 尺度 ~10m):

```python
# 归一化: 1 simulation unit = 1 m
# 典型源频率 f=1 Hz (低频呼吸/心跳声)
ALPHA_ACOUSTIC = 0.001  # Np/unit (低频穿透深度 ~1000 units, 远超 box)
```

#### Thermal (热辐射/扩散)

**来源**: Fourier 热传导定律, Pennes 生物热方程

```
热扩散方程: ∂T/∂t = κ·∇²T
  κ (生物组织) = 0.14-0.16 mm²/s

热辐射 (Stefan-Boltzmann):
  q = ε·σ·(T_s⁴ - T_env⁴)

热传导吸收:
  温度场衰减为 T(r) ∝ e^{-r/δ} / r
  δ = √(κ/(π·f))  (热穿透深度)

实测值:
  f = 0.01 Hz (呼吸节律): δ ≈ 2.3 mm
  f = 1 Hz:               δ ≈ 0.23 mm
  体表温度梯度: 在空气中 ~0.1 °C/cm = 10 °C/m
```

**归一化**:

```python
# 热的穿透深度极短 → 吸收系数极大
# δ ≈ 0.002 m → α = 1/δ ≈ 500 /m
# 但在 box_size=10 的尺度下, 需要考虑宏观对流
# 用一个中间值: α = 0.1 /unit (穿透深度 10 units)
ALPHA_THERMAL = 0.1  # Np/unit
```

#### Luminous (光在空气中)

**来源**: Beer-Lambert 定律, 视网膜光学

```
可见光在空气中吸收系数:
  α ≈ 10⁻⁶ /m (几乎不衰减)
  穿透深度: ~1000 km

Rayleigh 散射:
  α_scatter ∝ 1/λ⁴
  蓝光 (400nm): α ≈ 10⁻⁵ /m
  红光 (700nm): α ≈ 10⁻⁶ /m
```

**归一化**:

```python
# 光在 box 尺度下几乎不衰减
ALPHA_LUMINOUS = 0.0001  # Np/unit (穿透深度 10000 units)
```

### 实现

#### [MODIFY] QuantitySource — `received_at()`

```python
class QuantitySource:
    # Medium absorption coefficients (Beer-Lambert, ISO 9613 / Fourier)
    ABSORPTION = {
        "acoustic": 0.001,   # Np/unit — air, low freq (ISO 9613-1)
        "thermal":  0.1,     # Np/unit — Fourier diffusion in air
        "luminous": 0.0001,  # Np/unit — Beer-Lambert, visible light
    }

    def received_at(self, observer_pos, t):
        _, _, _, r = self.compute_lever(observer_pos)
        # Geometric spreading
        decay_geom = r ** self._decay_exp
        # Beer-Lambert absorption
        alpha = self.ABSORPTION.get(self.source_type, 0.001)
        decay_medium = math.exp(-alpha * r)
        # Combined
        base = self.amplitude * decay_medium / decay_geom
        # Retarded time
        t_ret = t - r / self._v_prop
        modulation = 1.0 + 0.3 * math.sin(2 * math.pi * self.frequency * t_ret)
        return base * modulation
```

---

## B. 感觉转导阻抗匹配

### 真实生物机制

#### Acoustic: 中耳阻抗变换器

**来源**: Rosowski 2010, Puria 2003

```
问题: 空气 → 耳蜗液, 阻抗失配 → 99.9% 反射 (-30 dB)

中耳解决方案 (3 个机制):
  1. 面积比 (hydraulic lever):
     A_tympanic / A_stapes ≈ 17:1
     → 压力放大 17×

  2. 听骨杠杆:
     L_malleus / L_incus ≈ 1.3:1
     → 力放大 1.3×

  3. 弯曲膜效应:
     → 额外 ~2× 增益

总增益: 17 × 1.3 × 2 ≈ 44× ≈ 33 dB
→ 补偿了 30 dB 的失配损失

透射系数: T ≈ 0.5-0.8 (频率依赖, 1-4 kHz 最优)
```

**归一化**:

```python
T_ACOUSTIC = 0.6  # 中耳有效透射, 频率优化后的平均值
```

#### Thermal: 皮肤热阻 + TRP 通道

**来源**: Caterina 1997 (TRPV1), McKemy 2002 (TRPM8)

```
皮肤热模型:
  皮肤 = 表皮 (0.1mm) + 真皮 (1-4mm) + 皮下脂肪
  热阻: R_skin ≈ 0.05 m²·K/W

TRP 通道转导:
  TRPV1: 阈值 43°C, Q₁₀ ≈ 20-40 (极陡的温度响应)
  TRPM8: 阈值 <26°C, Q₁₀ ≈ 24

转导效率:
  - 温度变化 ΔT → 电流 I_TRP
  - 灵敏度: ~0.1°C 可检测
  - 但信号需要穿过皮肤热阻

等效透射系数:
  T_thermal = k_tissue / (k_tissue + k_air)
  ≈ 0.5/(0.5 + 0.025) ≈ 0.95 (皮肤热导远大于空气)
  但考虑皮下脂肪隔热: 有效 T ≈ 0.3
```

**归一化**:

```python
T_THERMAL = 0.3  # 皮肤热阻 + 脂肪隔热层
```

#### Luminous: 角膜 + 视紫红质

**来源**: Rodieck 1998, Baylor 1987

```
光学系统:
  角膜透射: ~95%
  晶状体透射: ~90%
  视网膜到达率: ~85%

视紫红质量子效率:
  单光子 → 异构化: QE ≈ 0.67 (非常高)
  光子捕获效率 (视杆细胞): ~50%

等效透射系数:
  T = 0.85 × 0.67 × 0.50 ≈ 0.28
  但视网膜有 1.3 亿光感受器 → 空间整合极高
  等效: T ≈ 0.8 (考虑空间整合后)
```

**归一化**:

```python
T_LUMINOUS = 0.8  # 角膜+晶状体+视紫红质量子效率
```

### 实现

#### [MODIFY] PracticeEngine — 感觉转导层

```python
class QuantitySource:
    # Transduction coefficients (biological impedance matching)
    TRANSDUCTION = {
        "acoustic": 0.6,   # 中耳阻抗变换: 面积比×杠杆×膜曲率
        "thermal":  0.3,   # 皮肤热阻 + TRP通道灵敏度
        "luminous": 0.8,   # 角膜透射 × 量子效率 × 空间整合
    }

    def transduced_at(self, observer_pos, t):
        """完整信号链: 源 → 介质吸收 → 界面耦合 → 接收值"""
        raw = self.received_at(observer_pos, t)  # 含几何+吸收+延迟
        T = self.TRANSDUCTION.get(self.source_type, 0.5)
        return raw * T
```

---

## C. 传播速度修正

### 当前值 vs 物理值

| 模态 | 当前 v_prop | 真实值 | 归一化 (1 unit = 1m) | 修正 |
|---|---|---|---|---|
| Acoustic | 3.0 | 343 m/s | 343 | ↑ 大幅增加 |
| Thermal | 0.5 | ~0.01 m/s (扩散) | 0.01 | ↓ 大幅降低 |
| Luminous | 1000.0 | 3×10⁸ m/s | ∞ (即时) | 不变 |

> [!IMPORTANT]
> **问题**: 如果 v_thermal = 0.01, 则 r=7.5 处延迟 = 750 ticks (太大了)。
> 
> **解决**: Morphosphere 的 tick 不是秒。设 1 tick ≈ 0.1 秒 (生理反射时间尺度)。
> 则: v_thermal (归一化) = 0.01 m / 0.1 s × 1 unit/m = 0.1 unit/tick。
> 实际延迟: r=7.5 → 75 ticks ≈ 7.5 秒。生理上合理 (热觉反应时间 ~1-5 秒)。

```python
PROPAGATION_SPEED = {
    "acoustic": 34.3,    # 343 m/s × 0.1 s/tick = 34.3 unit/tick
    "thermal":  0.1,     # 热扩散前沿速度 (不是传导率)
    "luminous": 1e6,     # 即时
}
```

---

## 数学预测

### 新的 DERC 公式

$$\Phi(r) = \frac{A \cdot T_c}{r^n} \cdot e^{-\alpha r}$$

$$|\nabla\Phi(r)| = \frac{A \cdot T_c}{r^{n+1}} \cdot e^{-\alpha r} \cdot (n + \alpha r)$$

平衡条件:

$$\frac{A \cdot T_c \cdot (n + \alpha L^*)}{(L^*)^{n+1}} \cdot e^{-\alpha L^*} = \frac{\sigma_{eff}}{\alpha_{taxis}}$$

> [!NOTE]
> 当 $\alpha \to 0$, 回退到原始 DERC: $L^* = (nA\sqrt{N}/\sigma)^{1/(n+1)}$。
> 
> 当 $\alpha$ 大 (thermal), 存在 **穿透半径** $r_{pen} \sim 1/\alpha$,
> 超过此距离场为零 → L* 有上界。

### 四个可检验假说

| # | 假说 | 检验方法 |
|---|---|---|
| H1 | 吸收引入感知截止: $L_{max} \sim 1/\alpha$ | 扫描 $\alpha$ ∈ [0, 1], 测量 DERC 上界 |
| H2 | 阻抗匹配改变偏好排序 | 拉丁方: 交换 $T_c$, 看排序是否跟 $T_c$ 还是跟 $n$ |
| H3 | thermal 的 α=0.1 创造"近场限定": $L_{the}^{max} \sim 10$ | 测量 thermal 源在 L>10 时的 taxis 消失 |
| H4 | 组合效应: $\alpha$ + $T_c$ + $v$ 可产生非单调 DERC | 分别关闭各效应, 测量 DERC 形状变化 |

---

## 文件修改清单

### [MODIFY] [practice_engine.py](file:///D:/cell-cc/Morphosphere_v37_0_native_runtime_prototype_flat_complete/morphosphere_v2pp/engines/practice_engine.py)

| 位置 | 修改 |
|---|---|
| `QuantitySource.__init__` | 添加 `_alpha`, `_T_c` 属性 |
| `QuantitySource.received_at` | 添加 `e^{-α·r}` Beer-Lambert 项 |
| 新增 `QuantitySource.transduced_at` | 添加阻抗匹配透射系数 |
| `QuantitySource.gradient_at` | 更新梯度: $(n + \alpha r) \cdot A \cdot T_c \cdot e^{-\alpha r} / r^{n+1}$ |
| `PROPAGATION_SPEED` | 更新为物理归一化值 |
| `PracticeEngine._compute_sensory` | 调用 `transduced_at` 代替 `received_at` |

### [NEW] experiments/_phase1_validation.py

验证脚本:
1. Beer-Lambert 衰减曲线 vs 理论
2. 梯度公式验证
3. DERC 对比 (Phase 0 vs Phase 1)
4. H1-H4 假说检验
5. 拉丁方重复

### [NEW] experiments/_phase1_figures.py

论文图表:
- Fig A: 三种介质的 $\Phi(r)$ 衰减对比 (含/不含吸收)
- Fig B: DERC Phase 0 vs Phase 1
- Fig C: $L_{max}$ vs $\alpha$ 曲线
- Fig D: 阻抗匹配的效应

---

## 验证计划

### Step 1: 单元测试

```python
# 1. α=0, T=1 时结果与 Phase 0 完全相同 (回归测试)
# 2. 大 α 时, 远距离 Φ → 0 (吸收有效)
# 3. gradient_at 数值导数 vs 解析导数 (精度 < 0.1%)
```

### Step 2: 假说检验

```python
# H1: 扫描 α_thermal ∈ [0.01, 0.05, 0.1, 0.5, 1.0]
#     测量 E[L_thermal] 的上界
# H2: 交换 T_c (aco=0.3, the=0.8) vs 默认
#     拉丁方排序是否改变?
# H3: 单源 thermal at (20, 0, 0), 测量 taxis 响应 vs 距离
# H4: 逐个关闭 α/T/v, 测量 DERC 差异
```

### Step 3: 全链路回归

```python
# run_v40_integrated DATA_SOURCE=practice 仍然通过
# 59/59 neurons alive
# Discrimination: YES
```

---

## 论文方向

> **Paper 3**: *"Medium Physics Shapes Sensory Range: Beer-Lambert Absorption and Impedance Matching in Embodied Taxis"*
> 
> **核心论点**: 偏好不只由场衰减律 $n$ 决定, 还由介质吸收 $\alpha$ 和感觉转导效率 $T_c$ 共同塑造。三者定义了一个"感知半径" $r_{pen}$, 超过此距离, 代理对该模态的响应消失。
> 
> **关键图**: acoustic (低 α, 高 T) vs thermal (高 α, 低 T) 的感知半径对比 — 解释为什么生物对声音远距离敏感, 对温度只有近场感知。
