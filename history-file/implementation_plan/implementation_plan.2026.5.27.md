# Phase 4: P→R 闭合 (Xin → DA → α_lr → Δw)

## 问题诊断

### 链路规范 (v2.0 §1E.5)

```
|ξ| → c_DA → α_lr → Δw
```

1. |ξ| = bundle.compute_xin() ✓ （已实现，步骤 13）
2. DA 释放 = xin_integrator → MOSFET gate → dopamine.release() ✓ （步骤 8b）
3. DA → gain_factor() → da_lr_mod ✓ （步骤 12a）
4. Δw = lr × f_STDP × g_ℓ × da_lr_mod × g_sync ← **断裂点在这里**

### 断裂点：Mother 和 Variant 双重 learn()

**Mother** (`hebbian.py` step 5, line 434-442):
```python
for bundle in self.bundles_vest_to_enc:
    bundle.learn(dt)                    # ← plasticity_gate=1.0 (默认)
for bundle in self.bundles_enc_to_col:
    bundle.learn(dt)                    # ← 无 DA，无 PNN
for bundle in self.bundles_col_to_motor:
    bundle.learn(dt)                    # ← 无 DA，无 sync gate
```

**Variant** (`variant_adapter.py` step 12, line 559-573):
```python
for b in self.bundles_vest_to_enc:
    b.learn(dt, plasticity_gate=gate_vest * da_lr_mod)   # ✓ 正确
for b in self.bundles_enc_to_col:
    b.learn(dt, plasticity_gate=gate_enc * da_lr_mod)    # ✓ 正确
for b in self.bundles_col_to_motor:
    b.learn(dt, plasticity_gate=gate_col * da_lr_mod * g_sync)  # ✓ 正确
```

**问题**：`super().step()` 先执行 → Mother 的 learn() 先跑（gate=1.0）→ 然后 Variant 的 learn() 又跑一次（gate=DA×PNN）。

结果：**每步学习两次**——第一次不受 DA/PNN 控制，第二次受控。DA 的调制效果被第一次无门控学习稀释了。

### 验证

这解释了测试中观察到的行为：
- col_to_motor 权重持续增长到 0.5（饱和）→ 因为 Mother 的无门控 learn() 持续推高权重
- DA 有值（xin_V ≈ 2.0）但对学习没有可见效果

## 修复方案

### 核心修改：Mother 不调用 learn()，由 Variant 全权负责

#### [MODIFY] [hebbian.py](file:///d:/cell-cc/nexus_v1/circuit/hebbian.py)

移除 step() 中的 learn() 调用块。但保留一个钩子让子类决定是否学习：

```python
# ── 5. Learn (delegated to subclass if variant overlay active) ──
# Base class calls learn() with default gate=1.0.
# VariantAdapter overrides _do_learning() to add DA/PNN/sync gating.
self._do_learning(dt)
```

新增方法：
```python
def _do_learning(self, dt):
    """Default learning: no gating."""
    for bundle in self.bundles_vest_to_enc:
        bundle.learn(dt)
    for bundle in self.bundles_enc_to_col:
        bundle.learn(dt)
    for bundle in self.bundles_col_to_motor:
        bundle.learn(dt)
    for bundle in self._sprouted_bundles:
        bundle.learn(dt)
```

#### [MODIFY] [variant_adapter.py](file:///d:/cell-cc/nexus_v1/circuit/variant_adapter.py)

1. 在 Variant 的 step() 中**移除**步骤 12 的独立 learn() 调用
2. **Override** `_do_learning()` 方法，加入 DA + PNN + sync gating：

```python
def _do_learning(self, dt):
    """P→R closure: DA + PNN + sync gate all learning."""
    gate_vest = self.ecm_vestibular.plasticity_gate
    gate_enc = self.ecm_encoding.plasticity_gate
    gate_col = self.ecm_column.plasticity_gate
    da_lr_mod = self.dopamine.gain_factor()
    
    # Sync gate from binding layer
    binding_activations = self.binding_layer.compute_all(...)
    total_bind_act = sum(binding_activations.values())
    g_sync = min(1.0, self._sync_gate.conduct(total_bind_act))
    
    for b in self.bundles_vest_to_enc:
        b.learn(dt, plasticity_gate=gate_vest * da_lr_mod)
    for b in self.bundles_enc_to_col:
        b.learn(dt, plasticity_gate=gate_enc * da_lr_mod)
    for b in self.bundles_col_to_motor:
        b.learn(dt, plasticity_gate=gate_col * da_lr_mod * g_sync)
    for b in self._sprouted_bundles:
        # Sprouted bundles: use the gate of their target layer
        b.learn(dt, plasticity_gate=gate_enc * da_lr_mod)
```

> [!IMPORTANT]
> 步骤 12 的 PNN-gated learning 块（line 549-573）和步骤末尾的 PNN 基础 lr 调制块（line 642-667）也需要整合。
> 当前两者独立修改 stdp_lr 和 plasticity_gate → 存在交互问题。
> 修复后统一为：`_do_learning()` 中一次性计算 effective_gate = PNN × DA × sync。

## Open Questions

> [!IMPORTANT]
> **PNN lr 缓存**（line 642-667）直接修改 `bundle.config.stdp_lr`，而 `plasticity_gate` 是乘法参数传给 `learn()`。
> 两者功能重叠：PNN 同时影响了 `stdp_lr`（永久修改）和 `plasticity_gate`（每步传递）。
> 建议：移除 PNN 对 `stdp_lr` 的直接修改，只通过 `plasticity_gate` 传递。这避免了 lr 被永久降低后无法恢复。

## Verification Plan

### Automated Tests
1. `test_governance.py`: 确认不破坏 fuse
2. 对比修复前后 500k 步运行：
   - col_to_motor 权重是否不再饱和到 0.5
   - DA gain_factor 变化是否影响学习速率
   - 总体 motor 行为是否合理

### 预期行为
- DA 高时（xin 大）→ 学习快 → 权重变化大
- DA 低时（系统稳定）→ 学习慢 → 权重稳定
- PNN 成熟时 → 可塑性关闭 → 权重冻结
- col_to_motor 权重应稳定在 <0.5（sync gate 约束）
