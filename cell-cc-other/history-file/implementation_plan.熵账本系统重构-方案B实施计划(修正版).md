# 熵账本系统重构 — 方案 B 实施计划 (修正版)

> **重要修正**: 前次审计存在严重误判。A7 运动势 (ν, K, P_ν) 和结构熵 (H_struct, H_flow, Ω, P_ν×H_flow) **均已实现**。回归测试 21/21 PASS。

> [!CAUTION]
> **审计错误原因**: grep 搜索 `kinetic_energy` 时在 variant_adapter.py 中未命中（代码在 L538 存在但搜索可能因编码/缓存问题遗漏）。后续结论全部基于错误前提推导。这正是用户批评的"纪律性缺失"的体现——**应该先跑回归测试确认现状，再做审计结论**。

---

## 实际现状 (回归测试确认)

```
T7.1 Kinetic energy > 0: 0.005706    ✅ ν 已计算 (variant_adapter.py L533)
T7.2 Polarization [0.3,1.0]: 0.5574  ✅ P_ν 已计算 (variant_adapter.py L550)
T8.1 H_struct > 0: 4.1841            ✅ 结构熵已实现 (noether_probe.py L320)
T8.2 H_flow > 0: 4.0588              ✅ 流程熵已实现 (noether_probe.py L338)
回归测试: 21 passed, 0 failed, 27.2s
```

### 真正缺失的只有：

| 条目 | 文件 | 状态 |
|---|---|---|
| **EntropyLedger 未安装** | entropy_ledger.py 存在但未实例化 | ❌ 唯一真缺 |
| **影子层/DA 能量不追踪** | EntropyLedger.record() 不覆盖 | ❌ 需扩展 |
| **代码结构分散** | 3个熵系统分散在2个文件 | ⚠️ 需要整理 |
| **命名混乱** | `_entropy_ledger_pre_step` 不调用 EntropyLedger | ⚠️ 需要重命名 |
| **pytest 不兼容** | test_regression.py 用自定义框架 | ⚠️ 需要改造 |

---

## 修正后的实施方案

### Phase 1: 创建 ledger/ 子包，迁移文件

#### [NEW] nexus_v1/ledger/__init__.py

```python
"""nexus_v1.ledger — Unified thermodynamic & information-theoretic bookkeeping.

All classes in this package are READ-ONLY observers. They NEVER modify
circuit state. Their role is accounting, verification, and diagnostics.

Architecture:
  - weight_entropy.py:  WeightEntropyProbe (Shannon entropy of weights)
  - toprxin.py:         TOPRXinLedger (phase intensities per bundle)
  - structural.py:      RecursionTracker, UltrametricSpace, StructuralEntropy
  - energy_ledger.py:   EntropyLedger (global energy/heat/spike accounting)
  - noether_probe.py:   NoetherProbe (conservation law verification)
"""
```

#### 文件迁移

| 源文件 | 目标文件 | 操作 |
|---|---|---|
| components/entropy_ledger.py | ledger/energy_ledger.py | MOVE |
| circuit/toprxin_ledger.py → WeightEntropyProbe | ledger/weight_entropy.py | SPLIT |
| circuit/toprxin_ledger.py → TOPRXinLedger | ledger/toprxin.py | SPLIT |
| circuit/toprxin_ledger.py → Recursion+Ultra+Structural+Bridge+Auditor | ledger/structural.py | SPLIT |
| circuit/noether_probe.py | ledger/noether_probe.py | MOVE |

#### [MODIFY] circuit/variant_adapter.py
- 更新 imports: `from ..ledger import ...`
- 重命名: `_entropy_ledger_pre_step` → `_ledger_pre_step`
- 重命名: `_entropy_ledger_post_step` → `_ledger_post_step`

#### [DELETE after verification]
- components/entropy_ledger.py（留空 re-export 过渡）
- circuit/toprxin_ledger.py（留空 re-export 过渡）

#### 验证: 回归测试仍然 21/21 PASS

---

### Phase 2: 安装 EntropyLedger + 扩展覆盖

这是**唯一真正的新功能**：

#### [MODIFY] circuit/variant_adapter.py

```python
# __init__ 中添加:
from ..ledger.energy_ledger import EntropyLedger
self._energy_ledger = EntropyLedger()

# _ledger_post_step 中添加（每 1000 步）:
if tick % 1000 == 0:
    self._energy_ledger.record(self, dt)
```

#### [MODIFY] ledger/energy_ledger.py — 扩展层覆盖

```python
# record() 方法中，扩展 layers dict:
layers = {
    # 主层
    'L1_MET': [], 'L2_HC': [], 'L3_Aff': [],
    'L4_Enc': [], 'L5_Col': [], 'L6_Mot': [],
    # 影子层
    'S_Enc': [], 'S_Col': [], 'S_Mot': [],
    # DA
    'DA': [],
}
# 添加 shadow neuron 路由
for n in neurons:
    nid = n.config.neuron_id
    if nid.startswith('s_enc_'):
        layers['S_Enc'].append(n)
    elif nid.startswith('s_col_'):
        layers['S_Col'].append(n)
    elif nid.startswith('s_mot_'):
        layers['S_Mot'].append(n)
    elif nid.startswith('da_'):
        layers['DA'].append(n)
```

#### [MODIFY] variant_adapter.py — diagnostic report 添加 energy_ledger

```python
"energy_ledger": self._energy_ledger.summary(),
```

---

### Phase 3: 回归测试 pytest 化

#### [MODIFY] nexus_v1/tests/test_regression.py

保留现有 `run_test_suite()` 作为直接运行入口，新增 pytest 包装：

```python
import pytest

@pytest.fixture(scope="module")
def circuit_10k():
    """Shared 10k-step circuit for all regression tests."""
    c = VariantCircuit()
    for i in range(10000):
        t = i * 0.001
        c.step({'oto_x': 200 * math.sin(2 * math.pi * 0.5 * t)}, 1.0)
    return c

def test_noether_violations(circuit_10k):
    assert circuit_10k._noether_probe.summary()['violations'] == 0

def test_energy_ledger_installed(circuit_10k):
    """EntropyLedger must be recording after 10k steps."""
    ledger = circuit_10k._energy_ledger
    assert ledger._total_steps > 0
    
# ... 等等
```

---

## Open Questions

> [!IMPORTANT]
> **Q1**: 旧文件删除策略 — 直接删除还是留空 re-export 过渡？
> 建议: 留空 re-export + deprecation warning，给一个版本的过渡期。

> [!IMPORTANT]
> **Q2**: noether_probe.py 迁入 ledger/ 后，它的 H_struct/H_flow/Ω 是否应拆到 flow_entropy.py？
> 当前它在 noether_probe.py 中，但功能上属于"结构追踪"而非"守恒验证"。

---

## 验证计划

### 自动化
```bash
python -m nexus_v1.tests.test_regression       # 直接运行
python -m pytest nexus_v1/tests/ -v --tb=short  # pytest 兼容
```

### 手动
- 20k 运行后打印 `_energy_ledger.print_report()`
- 确认影子层 S_Enc/S_Col/S_Mot 有非零 avg_energy 和 avg_heat
- 确认 DA 层有非零数据
