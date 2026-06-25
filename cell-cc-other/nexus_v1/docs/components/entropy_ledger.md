# EntropyLedger — 结构事件审计账本

## 物理对应

- **BIO**: 代谢/热力学审计 (ATP 消耗记账)
- **EE**: 能量核算系统

## 文件

[entropy_ledger.py](../../components/entropy_ledger.py)

## 功能

- **Pre-step guard**: 每步前检查守恒不变量，异常时冻结结构操作
- **Post-step audit**: 记录 sprout/prune/mitosis 事件
- **结构冻结**: `_structural_freeze` 标志阻止不安全操作
- 集成 registry.json 交叉引用

## 事件类型

| 事件 | 触发 | 记录 |
|---|---|---|
| SPROUT | \|ξ\| > XI_SPROUT | parent, child, xi, N |
| PRUNE | ξ < 0, age > grace | bundle, reason |
| MITOSIS | motor_potential > θ | parent, child |
| MATURATION | phi > threshold | neuron, stage |
