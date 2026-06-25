# World — 3D 物理环境

## 物理对应

- **BIO**: 外部环境 (深海热泉生态)
- **EE**: 3D Newtonian physics + 热场

## 文件

[world.py](../../components/world.py)

## 功能

### RigidBody (刚体)

- 位置、速度、加速度 (3D)
- 质量 + 阻尼 (粘性介质)
- 阻抗 Z = √(k×m) (用于 A4 阻抗匹配)
- kinetic_damping() → 速度衰减

### 热源

- 默认热源: [70,50,50], 温度=100, 半径=20
- `consume_nearby()` → 距离相关能量吸收
- `regenerate_sources()` → 深海热泉再生

### 能量流

```
HeatSource → consume_nearby(position, CONSUME_RATE, dt)
           → energy_absorbed
           → EnergyStore.deposit()
           → Vascular → neuron.energy
```

## 关键参数

| 参数 | 值 | 物理意义 |
|---|---|---|
| `CONSUME_RATE` | 0.15 | 能量吸收速率 (P2.1 校准) |
| Body initial pos | [50,50,50] | 起始位置 |
| Heat source pos | [70,50,50] | 热源位置 |
