# VestibularChain — 前庭链

## 物理对应

- **BIO**: 前庭器官 (3 半规管 + 3 耳石器)
- **EE**: MET → HC → Aff 信号链

## 文件

[compensation.py](../../components/compensation.py)

## 功能

6 轴信号链 (yaw, pitch, roll, surge, heave, sway):

```
机械输入 → MET (机械电转换)
         → HairCell (Ca²⁺ ribbon synapse)
         → Aff_regular (规则放电, spiking)
         → Aff_irregular (不规则放电, spiking)
```

## 层级

| 层 | 类 | 数量 | 模式 | 功能 |
|---|---|---|---|---|
| MET | MET | 6 | continuous | 机械→电转换 |
| HC | HairCell | 6 | continuous | 突触囊泡释放 |
| Aff_reg | Neuron | 6 | spiking | 规则传入 (DC) |
| Aff_irr | Neuron | 6 | spiking | 不规则传入 (AC) |

## 热感旁路

热感信号跳过前庭链，直接注入 Encoding 层:
- `therm` → 绝对温度感知
- `dtherm` → 温度变化率
