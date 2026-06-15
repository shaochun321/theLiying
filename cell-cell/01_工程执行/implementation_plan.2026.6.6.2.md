# 熵账本系统前置化 — 实施计划（v2）

## 背景

熵账本系统现有**三层时间尺度采样**：

| 尺度 | 组件 | 采样间隔 | 功能 |
|------|------|----------|------|
| **每步** | `WeightEntropyProbe.accumulate_heat()` | 1 步 | 热量累积（Landauer 追踪） |
| **中尺度** | `WeightEntropyProbe.measure()` | 100 步 | 权重熵快照（Shannon） |
| | `TOPRXinLedger.measure()` | 100 步 | T/O/P/R/Xin 相位强度 |
| | `RecursionTracker.update_phases()` | 100 步 | 递归周期相位更新 |
| | `NoetherProbe.check()` | 100 步 | 4 项守恒验证 |
| **慢尺度** | `StructuralEntropy.measure()` | 1000 步 | 树复杂度 |
| | `StructuralBridge.structural_influence()` | 1000 步 | ds²/ν ↔ 超度量桥 |
| | 结构生长 `_structural_growth()` | 10000 步 | sprout/prune |
| | 有丝分裂 `_check_mitosis()` | 10000 步 | 神经元分裂 |

这套多尺度采样不需要改变——它已经很成熟。需要改变的是**运行入口的位置**。

## 当前问题

```
variant_adapter.step():
  Phase 0-2:  Input + Mother step (propagation + learning)
  Phase 3-9:  Post-hoc modulation, DA, motor feedback
  Phase 10:   Maturation
  Phase 11:   _structural_growth()  ← 结构修改在这里
  Phase 12:   _check_mitosis()      ← 结构修改在这里
  Phase 13:   Xin accumulation
  Phase 14-16: Fruit, Circulation, Shadow
  Phase 17:   Entropy ledger        ← 审计在这里（太晚了）
  Phase T4:   Noether check         ← 验证在这里（太晚了）
  Phase 5-7:  ECM, Vascular, Learning gates
```

问题：**结构修改（Phase 11-12）先于审计（Phase 17）执行**。如果本步的结构修改违反了规则，审计只能在下一个 100 步周期才检测到，但结构已经不可逆地改变了。

## 目标架构

```
variant_adapter.step():
  ┌─ Phase 0: 熵账本守卫 (PRE-STEP)
  │   ├─ 每步: accumulate_heat (上一步的热量)
  │   ├─ 100步: Noether pre-check → _structural_freeze flag
  │   ├─ 100步: WeightEntropyProbe.measure() → 约束快照
  │   └─ 100步: TOPRXinLedger.measure() + RecursionTracker
  │
  ├─ Phase 1-2: Input + Mother step
  ├─ Phase 3-9: Modulation, DA, motor
  ├─ Phase 10: Maturation
  ├─ Phase 11: _structural_growth() ← GATED by _structural_freeze
  ├─ Phase 12: _check_mitosis()     ← GATED by _structural_freeze
  ├─ Phase 13-16: Xin, Fruit, Circulation, Shadow
  │
  └─ Phase Z: 熵账本复核 (POST-STEP)
      ├─ 1000步: StructuralEntropy + StructuralBridge (慢尺度)
      └─ 记录本步结构事件的 outcome
```

> [!IMPORTANT]
> **三层时间尺度完整保留**。每步热量、100 步周期测量、1000 步慢尺度——全部保持原有间隔。唯一变化：从 step 末尾移到 step 开头。

---

## Proposed Changes

### [MODIFY] [variant_adapter.py](file:///d:/cell-cc/nexus_v1/circuit/variant_adapter.py)

#### 新方法 `_entropy_ledger_pre_step(tick, dt)`

```python
def _entropy_ledger_pre_step(self, tick: int, dt: float):
    """Phase 0: 熵账本守卫 — 在所有计算之前运行。
    
    多尺度采样入口：
      每步:   热量累积（Landauer 追踪）
      100步:  Noether 验证 + 权重熵 + TOPRXIN + 递归周期
    
    如果 Noether 发现违规，设置 _structural_freeze = True，
    冻结本步的所有结构操作（sprout/prune/mitosis）。
    """
    # 重置冻结标志（每步重新判断）
    self._structural_freeze = False
    
    # ── 每步: 热量累积 ──
    # 累积的是上一步各神经元产生的热量
    total_heat = sum(n.heat_output for n in self.get_all_neurons())
    self._entropy_probe.accumulate_heat(total_heat)
    
    # ── 100步周期: 守卫级检查 ──
    if tick % 100 == 0 and tick > 0:
        # 1. Noether 验证（上一步结束时的状态）
        violations_before = len(self._noether_probe._violations)
        self._noether_probe.check(self, tick, dt)
        new_violations = len(self._noether_probe._violations) - violations_before
        if new_violations > 0:
            self._structural_freeze = True
        
        # 2. 权重熵快照
        self._entropy_probe.measure(self, tick)
        
        # 3. TOPRXIN + 递归周期
        toprxin_snap = self._toprxin_ledger.measure(self, tick)
        self._recursion_tracker.update_phases(tick, toprxin_snap)
```

#### 新方法 `_entropy_ledger_post_step(tick, dt)`

```python
def _entropy_ledger_post_step(self, tick: int, dt: float):
    """Phase Z: 慢尺度复核 — 在所有计算之后运行。
    
    1000步: 结构熵 + 结构桥（树变化慢，不需要高频采样）
    """
    if tick % 1000 == 0 and tick > 0:
        self._structural_entropy.measure(tick)
        self._structural_bridge.structural_influence(tick)
```

#### step() 主流程修改

```python
def step(self, mechanical_inputs, dt=1.0):
    # ── Phase 0: 熵账本守卫 (BEFORE everything) ──
    tick = getattr(self, '_maturation_tick', 0) + 1
    self._entropy_ledger_pre_step(tick, dt)
    
    # ... 原有 Phase 1-16 不变 ...
    # 但 Phase 17 和 Phase T4 的代码被删除（已移入 Phase 0）
    
    # ── Phase Z: 慢尺度复核 (AFTER everything) ──
    self._entropy_ledger_post_step(self._maturation_tick, dt)
```

### [MODIFY] [hebbian.py](file:///d:/cell-cc/nexus_v1/circuit/hebbian.py)

在 `step()` 的结构操作前加门控：

```python
# ── 7. Structural growth (RULE S2) ──
if self._step_count % self.SPROUT_INTERVAL == 0:
    if not getattr(self, '_structural_freeze', False):
        self._structural_growth(dt)

# ── 9. Mitosis check ──
if self._step_count % self.SPROUT_INTERVAL == 0:
    if not getattr(self, '_structural_freeze', False):
        self._check_mitosis()
```

新属性：
```python
class HebbianCircuit:
    def __init__(self, ...):
        ...
        self._structural_freeze: bool = False
```

---

## 设计决策

> [!IMPORTANT]
> **Pre-step 检查的是上一步的结果**。Phase 0 在本步计算前运行，检查 `t-1` 的状态。违规在 `t-1` 产生，在 `t` 步开始前被发现，阻止 `t` 步的结构修改。

> [!IMPORTANT]
> **Ledger 仍然 read-only**。Phase 0 不修改任何物理状态——只设置 `_structural_freeze` boolean。结构操作自己检查并决定。

> [!NOTE]
> **慢尺度保留在 post-step**。`StructuralEntropy` 和 `StructuralBridge` 需要看到当前步的结构变化结果，所以放在 Phase Z。如果本步有 sprout，Phase Z 的 1000 步检查会记录到它。

## Verification Plan

### Automated Tests
```bash
python test_differentiation.py  # 50k步 Noether ALL PASSED
```
- 验证前置化后 Noether 仍然 0 violations
- 验证 `_structural_freeze` 正常运行时不触发（因为当前系统无违规）

### Manual Verification
- 在 growth_log 中没有 FREEZE 事件
- 热量累积时序正确（Phase 0 读上一步的 heat_output）
