# 熵账本重构 — 完成总结

## 变更概览

将分散的熵/能量追踪系统整合为 `nexus_v1/ledger/` 子包，首次安装 EntropyLedger，修复回归测试基础设施。

---

## 新文件结构

```
nexus_v1/ledger/                   ← [NEW] 子包
├── __init__.py                    ← 统一导出接口
├── weight_entropy.py              ← WeightEntropyProbe (from toprxin_ledger.py)
├── toprxin.py                     ← TOPRXinLedger (from toprxin_ledger.py)
├── structural.py                  ← RecursionTracker, UltrametricSpace,
│                                    StructuralEntropy, StructuralBridge,
│                                    GuidedConstructionAuditor (from toprxin_ledger.py)
├── energy_ledger.py               ← EntropyLedger (from components/entropy_ledger.py)
│                                    + 扩展覆盖: Shadow + DA 层
└── noether_probe.py               ← NoetherProbe (from circuit/noether_probe.py)
```

## 修改的文件

### [variant_adapter.py](file:///d:/cell-cc/nexus_v1/circuit/variant_adapter.py)
- Imports 改为 `from ..ledger import ...`
- 新增: `self._energy_ledger = EntropyLedger()` (首次安装)
- 新增: `self._energy_ledger.record(self, dt)` 在 `_ledger_post_step()` 每 1000 步调用
- 重命名: `_entropy_ledger_pre_step` → `_ledger_pre_step`
- 重命名: `_entropy_ledger_post_step` → `_ledger_post_step`
- diagnostic report 增加 `energy_ledger` 字段

### [energy_ledger.py](file:///d:/cell-cc/nexus_v1/ledger/energy_ledger.py)
- 层覆盖扩展: `S_Enc`, `S_Col`, `S_Mot`, `DA`
- 神经元 ID 路由增强: `reg_*` → L4_Enc, `move_*` → L6_Mot
- 层间传递分析增加影子层和 DA 对

### [test_regression.py](file:///d:/cell-cc/nexus_v1/tests/test_regression.py)
- 修复 pytest 兼容: guard `sys.stdout` 包装
- 添加 12 个 pytest wrapper 函数
- 新增 T10: `test_energy_ledger_installed`
- 新增 T10.2: `test_energy_ledger_layer_coverage`
- `TestResult` → `_TestResult` (避免 pytest 收集)

### Re-export shims (向后兼容)
- [circuit/toprxin_ledger.py](file:///d:/cell-cc/nexus_v1/circuit/toprxin_ledger.py) — 空壳 re-export
- [circuit/noether_probe.py](file:///d:/cell-cc/nexus_v1/circuit/noether_probe.py) — 空壳 re-export
- [components/entropy_ledger.py](file:///d:/cell-cc/nexus_v1/components/entropy_ledger.py) — 空壳 re-export

---

## 验证结果

| 入口 | 结果 |
|---|---|
| `python -m nexus_v1.tests.test_regression` | 21/21 PASS |
| `python -m pytest nexus_v1/tests/test_regression.py` | 12/12 PASS |
| 导入兼容 (新路径 + 旧路径 re-export) | 全部 OK |

---

## 关键修复

1. **EntropyLedger 首次安装**: 473 行代码从"存在但从未使用"变为"每 1000 步记录一次"
2. **影子层 + DA 覆盖**: energy_ledger 现在追踪 10 个层级而非原来的 6 个
3. **pytest 可发现**: 回归测试同时支持直接运行和 pytest 发现
4. **命名修正**: `_entropy_ledger_pre_step` → `_ledger_pre_step`（名称不再误导）
