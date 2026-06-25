# MotorDecision — 运动决策层

## 物理对应

- **BIO**: 运动皮层 → 脊髓 → 肌肉命令
- **EE**: CPG + force 集成 + muscle 驱动

## 文件

[motor_decision.py](../../circuit/motor_decision.py)

## 功能

- **CPG**: 耦合振荡器 (Ijspeert model, 120° 相位耦合)
- **Lateral inhibition**: Renshaw cell 竞争 (break clone symmetry)
- **Force integration**: Col raw acts → decided acts
- 当前: 大部分为 passthrough (stubs)

## 子系统

| 子系统 | 状态 | 功能 |
|---|---|---|
| CPG | stub | 中央模式发生器 |
| Direction | stub | 方向决策 |
| Navigator | stub | 导航 |
| Lateral | ✅ active | Renshaw 竞争 |
