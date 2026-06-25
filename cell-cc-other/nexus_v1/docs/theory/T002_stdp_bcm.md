# T002: 学习规则 — STDP / BCM / Hebbian+decay

> 状态: ✅ 已验证 (axis/cross ratio 6.8x)

## 三种学习规则

### STDP (Spine stage, M=0)

$$\Delta w = \eta \cdot \text{pre\_trace} \cdot \text{post\_trace} - \lambda \cdot w$$

- 乘性软边界: $\Delta w > 0$ 时 $\times (w_{max} - w)$
- 适用: 新生突触 (maturation_stage=0)
- BIO: Bi & Poo 1998

### BCM (Column stage, M=1)

$$\Delta w = \eta \cdot a_{pre} \cdot a_{post} \cdot (a_{post} - \theta_m)$$

- 滑动阈值: $d\theta/dt = (a^2 - \theta) / \tau_\theta$
- 适用: 成熟突触 (maturation_stage=1)
- BIO: Bienenstock, Cooper, Munro 1982

### Hebbian+decay (Cross-axis only)

$$\Delta w = \eta \cdot |a_{pre}| \cdot |a_{post}| - \lambda \cdot w$$

- 无竞争 theta → 跨模态关联保留
- 仅用于 cross_axis bundle (FIX-018)
- BIO: 联络纤维可塑性 (Abbott & Nelson 2000)

## 成熟度驱动的规则切换

```
PNN < 0.3  →  M=0 (Spine)  →  STDP     lr=0.18
PNN 0.3-0.7 → M=1 (Column) → BCM      lr=0.01
PNN ≥ 0.7  →  M=2 (Area)   →  Frozen   lr=0.001
```

## 代码位置

| 文件 | 行 | 功能 |
|---|---|---|
| circuit/bundle.py | L286-300 | STDP 实现 |
| circuit/bundle.py | L302-319 | BCM 实现 |
| circuit/bundle.py | L321-335 | Hebbian+decay 实现 |

## 验证

- 回归测试 T4.1: axis/cross weight ratio > 2.0 (实测 6.8x)
- 回归测试 T4.2: cross weight max < 0.20 (实测 0.073)
