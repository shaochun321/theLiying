# 变体安全实施策略 — 零损坏回档保障

> **日期**: 2026-05-22
> **核心关切**: 实施后出现问题无法回档

---

## 0. 回档保障机制

### 已建立的安全网

```
D:\cell-cc\.git\
  └── commit 6077050: BASELINE (13/15, depth 6/6)
      ← 随时可以 git checkout master 回到这里
```

### 实施策略: 每步一个 git tag

```
BASELINE ──→ v0.1-oscillator-standalone ──→ v0.2-oscillator-integrated
                                                     │
                                        (验证失败? git reset --hard v0.1)
```

**回档命令** (任何时候都可以执行):
```bash
# 回到最初的安全基线
git checkout master
git reset --hard 6077050

# 回到任意检查点
git reset --hard <tag_name>
```

---

## 1. 实施原则: 隔离层架构

> [!IMPORTANT]
> **核心原则: 新元件是纯新增文件，Phase 1 完全不修改现有代码。**

```
nexus_v1/
├── components/
│   ├── semiconductor.py      ← 不动
│   ├── compensation.py       ← 不动
│   ├── neuron.py              ← 不动
│   │
│   ├── oscillator.py          ← [NEW] 独立文件，零依赖
│   ├── ndr.py                 ← [NEW] 独立文件，零依赖
│   ├── damper.py              ← [NEW] 独立文件，零依赖
│   ├── router.py              ← [NEW] 独立文件，零依赖
│   └── modulator.py           ← [NEW] 独立文件，零依赖
│
├── circuit/
│   ├── hebbian.py             ← Phase 1 不动; Phase 2 用适配器包装
│   ├── bundle.py              ← Phase 1 不动
│   │
│   └── variant_adapter.py     ← [NEW] 适配器，包装不修改
│
└── tests/
    └── test_components.py     ← [NEW] 独立验证
```

### 为什么这样安全？

| 操作 | 影响范围 | 回档成本 |
|------|---------|---------|
| 新增文件 | 零影响原系统 | 删除文件即可 |
| 适配器包装 | 不修改原接口 | 删除适配器即可 |
| 集成开关 | 用 flag 控制 | 关闭 flag 即可 |

---

## 2. 四阶段实施计划 (每阶段独立可回档)

### Phase 1: 独立构建 + 数学验证 (不碰母本)

```
目标: 5 个新元件各自独立工作，通过数学验证
风险: 零 (纯新增文件，不修改任何现有代码)
回档: 删除 5 个新文件
```

#### Step 1.1: ResonantOscillator
```python
# oscillator.py — 完全独立，不 import 任何 nexus 代码
class ResonantOscillator:
    def step(self, dt: float) -> float:
        """返回当前振荡电流值。"""
        ...
    
# 验证: 独立脚本检查频率/幅度/相位
# → git tag v0.1-oscillator-standalone
```

#### Step 1.2: NDRElement  
```python
# ndr.py — 完全独立
class NDRElement:
    def conduct(self, voltage: float) -> float:
        """I-V 非线性特性。"""
        ...

# 验证: I-V 曲线是否展现 NDR 区
# → git tag v0.2-ndr-standalone
```

#### Step 1.3 ~ 1.5: Damper, Router, Modulator (同理)

**Phase 1 结束时**: 5 个独立元件，各自通过数学验证，**母本完全没动**。

---

### Phase 2: 适配器集成 (用包装器，不改原代码)

```
目标: 通过适配器将振荡器注入 Afferent 层
风险: 低 (适配器是新文件; 集成点用 flag 控制)
回档: 删除适配器 + 关闭 flag
```

#### Step 2.1: 创建 VariantCircuit 继承 HebbianCircuit

```python
# circuit/variant_adapter.py — 新文件

from .hebbian import HebbianCircuit
from ..components.oscillator import ResonantOscillator

class VariantCircuit(HebbianCircuit):
    """在 HebbianCircuit 基础上叠加变体元件。
    
    设计: 继承不修改。HebbianCircuit 原封不动。
    回档: 直接用 HebbianCircuit 代替即可。
    """
    
    def __init__(self):
        super().__init__()          # 母本初始化 100% 保留
        
        # ── 新增: 振荡器 ──
        self.oscillators = {
            axis: ResonantOscillator(freq=50.0)
            for axis in self.vestibular.axes
        }
    
    def step(self, inputs, dt):
        # 1. 母本的完整 step (不改动一行)
        super().step(inputs, dt)
        
        # 2. 振荡器叠加 (在母本之后，对母本无副作用)
        for axis, osc in self.oscillators.items():
            osc_current = osc.step(dt)
            aff = self.vestibular.afferent_regular[axis]
            # 注入微小振荡电流 (不修改 Neuron.step, 直接注入膜)
            aff._membrane.inject(osc_current * dt, dt)
```

**关键**: `VariantCircuit` 是 **HebbianCircuit 的子类**。
- 不修改 `hebbian.py` 一行代码
- 想回档? 用 `HebbianCircuit()` 替换 `VariantCircuit()` 即可
- 两者可以**并行跑对比**

#### Step 2.2: 创建 variant_contracts.py

```python
# 对比验证: 母本 vs 变体
from nexus_v1.circuit.hebbian import HebbianCircuit
from nexus_v1.circuit.variant_adapter import VariantCircuit

baseline = run_contracts(HebbianCircuit())   # 13/15
variant  = run_contracts(VariantCircuit())   # 目标 14/15+

# 如果变体更差 → 不合并，删除适配器
# 如果变体更好 → 保留，打 tag
```

```
# → git tag v1.0-variant-oscillator-integrated
# 验证: 对比表
# → 如果回归: git reset --hard v0.5
```

---

### Phase 3: 逐步集成其他元件 (每个独立验证)

```
同 Phase 2 模式:
  每个元件 → 适配器 → 对比验证 → 通过则 tag
  
顺序:
  1. NDR → 抑制回路
  2. MagnetofluidDamper → 粘弹阻尼
  3. LiquidMetalRouter → 动态拓扑
  4. Neuromodulator → 全局调制
  
每一步都可以独立回档到上一个 tag
```

---

### Phase 4: 母本合并 (可选，需显式批准)

```
只有当变体稳定运行、全部契约通过后，才考虑:
  - 将适配器代码合并进母本
  - 更新 RULES.md 加入新元件原则
  
这一步是可选的 — 适配器架构可以永久使用
```

---

## 3. 具体的验证门控

每一步都必须通过以下检查才能进入下一步:

```
┌─────────────────────────────────────────────┐
│                验证门控 (Gate)                │
├─────────────────────────────────────────────┤
│ G1. 母本契约不退化                            │
│     → run_contracts(HebbianCircuit) ≥ 13/15  │
│                                             │
│ G2. 变体契约 ≥ 母本                           │
│     → run_contracts(VariantCircuit) ≥ 13/15  │
│                                             │
│ G3. 信号深度 ≥ 6/6                           │
│     → run_audit(VariantCircuit) depth=6/6    │
│                                             │
│ G4. 无新增能量耗尽                            │
│     → 所有层 energy > 0.1                    │
│                                             │
│ G5. 热耗散不爆炸                              │
│     → total_heat < 100 (当前基线: 25)        │
│                                             │
│ 全部通过 → git tag → 进入下一步               │
│ 任一失败 → git reset --hard 上一个 tag        │
└─────────────────────────────────────────────┘
```

---

## 4. 回档速查表

| 场景 | 命令 | 效果 |
|------|------|------|
| 新元件数学错误 | 删除对应 .py 文件 | 回到上一步 |
| 适配器集成崩溃 | `git reset --hard v0.5` | 回到独立元件 |
| 变体比母本差 | 用 HebbianCircuit 替换 | 完全回到母本 |
| 全部失败 | `git reset --hard 6077050` | 回到今天的基线 |

---

## 5. 时间线估计

| Phase | 步骤数 | 风险 | 预计时间 |
|-------|--------|------|---------|
| Phase 1 (独立构建) | 5 个文件 | **零** | 1 轮 |
| Phase 2 (振荡器集成) | 2 个文件 | **低** | 1 轮 |
| Phase 3 (其他元件) | 4×2 个文件 | **中** | 2-3 轮 |
| Phase 4 (合并, 可选) | 修改原文件 | **高** | 需审批 |

---

## Open Questions

> [!IMPORTANT]
> 1. 是否同意 Phase 1 立即开始？（纯新增文件，零风险）
> 2. Phase 2 的集成策略（继承适配器）是否可接受？
> 3. 如果振荡器解决了 CV 问题，是否还需要继续 Phase 3-4？
