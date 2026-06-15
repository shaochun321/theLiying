# LOCAL: 前庭链 — vestibular chain

> **Version**: v1.7.2 | **File**: [compensation.py](../../components/compensation.py)

---

## 信号流

```
外部机械输入 (oto_x/y/z 等)
  │
  ▼
MET ×6 (MET.step)
  │  机械→电转换: V = gain × displacement
  ▼
HairCell ×6 (HairCell.step)
  │  Ca²⁺ ribbon synapse
  │  非线性: sigmoid(V_met) × Ca_dynamics
  ▼
┌─────────────────┬──────────────────┐
│                 │                  │
Aff_regular ×6    Aff_irregular ×6
│ spiking mode    │ spiking mode
│ DC 编码          │ AC 编码
│ 空间信息          │ 时间信息
└────────┬────────┴────────┬─────────┘
         │                 │
    Bundle aff→enc     Bundle aff→enc
    (gain=2, coupler)  (gain=2, coupler)
         │                 │
         ▼                 ▼
    Encoding reg_*    Encoding irr_*
    (continuous)      (continuous)
```

## 轴定义

| 轴 | BIO | 感受器 | 输入键 |
|---|---|---|---|
| yaw | 水平半规管 | 角加速度 | oto_x |
| pitch | 前半规管 | 角加速度 | oto_y |
| roll | 后半规管 | 角加速度 | oto_z |
| surge | 椭圆囊 (前后) | 线加速度 | *(从 body.acceleration)* |
| heave | 球囊 (上下) | 线加速度 | *(从 body.acceleration)* |
| sway | 椭圆囊 (左右) | 线加速度 | *(从 body.acceleration)* |

## 热感旁路

热感信号**不经过**前庭链，直接注入 Encoding:
- `therm` → ThermalMembrane → Encoding (绝对温度)
- `dtherm` → ThermalMembrane → Encoding (温度变化率)

## 关键耦合

- **A4 阻抗匹配**: 机械输入 × T_impedance (MOSFET divider)
- **振荡器调制**: Aff 膜电压 × osc_modulation (post-hoc)
- **NDR 不应期**: Aff 膜电荷 × (1 - h_gate reduction) 

## 已知限制

- 6 轴中只有 yaw/pitch/roll 有外部输入 (oto_x/y/z)
- surge/heave/sway 完全依赖 body.acceleration 反馈
- MET gain 为常数，未适应
