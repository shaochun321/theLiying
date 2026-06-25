# PowerRail — 共享电源轨

## 物理对应

- **BIO**: 血管区域能量预算 (局部 ATP 供应)
- **EE**: 共享电源轨 + 内阻 (I×R 电压降)

## 文件

[semiconductor.py](../../components/semiconductor.py)

## 功能

- 每层固定电源电压 `Vdd`
- 内阻 `R_internal` 产生负载相关电压降
- 多神经元共享 → 高活动区域电压下降 → 自然抑制
- Motor 层独占: 能量竞争驱动轴分化

## 关键参数

| 参数 | 值 | 物理意义 |
|---|---|---|
| `vdd` | 1.0 | 电源电压 |
| `r_internal` | 2.0 | 内阻 |
