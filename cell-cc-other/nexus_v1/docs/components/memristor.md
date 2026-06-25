# Memristor — 忆阻器 (可变电导突触)

## 物理对应

- **BIO**: AMPA 受体密度 → 突触强度
- **EE**: 可变电导器件 (忆阻器 / 浮栅 MOSFET)

## 文件

[semiconductor.py](../../components/semiconductor.py)

## 功能

- 权重存储: `w ∈ [weight_min, weight_max]`
- STDP 更新: `apply_dw(dw, w_min, w_max)` — 乘法软边界
- Noether 追踪: `_cum_ltp`, `_cum_ltd` (分项审计)
- Landauer 审计: 每次 dw 计入信息擦除代价

## 关键参数

| 参数 | 值 | 物理意义 |
|---|---|---|
| `w` | [0.0, 1.0] | 电导值 |
| `_cum_ltp` | 累积 | 长时增强总量 |
| `_cum_ltd` | 累积 | 长时抑制总量 |
