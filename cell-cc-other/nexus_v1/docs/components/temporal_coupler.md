# TemporalCoupler — 时间尺度桥接器

## 物理对应

- **BIO**: 树突膜电容 + 内源性大麻素反馈 + 突触缩放
- **EE**: RC coupler + C-layer MOSFET + B-layer 差分放大器

## 文件

[temporal_coupler.py](../../components/temporal_coupler.py)

## 功能

每个 Bundle target 有独立的 TemporalCoupler，包含：
- **C-layer**: RC 滤波 + MOSFET 适应 (短时增益控制)
- **B-layer**: 差分比较器 (长时基线追踪)
- 输出: 自适应增益 g ∈ [0, 1]

## 信号流

```
source activation → C-layer Capacitor → charge → MOSFET → adaptation
                  → B-layer slow Cap → baseline tracking
                  → Output gain = f(C_fast - B_slow)
```

## 关键参数

| 参数 | 值 | 物理意义 |
|---|---|---|
| `capacitance` | 1.0 | C-layer 电容 |
| `r_leak` | 2.0 | C-layer 漏电阻 (τ=2s) |
| `adapt_vth` | 0.2 | MOSFET 适应阈值 |
| `blayer_c_slow` | 100.0 | B-layer 慢电容 (τ=100s) |
