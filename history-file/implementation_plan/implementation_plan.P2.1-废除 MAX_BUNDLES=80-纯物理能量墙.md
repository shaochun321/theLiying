# P2.1: 废除 MAX_BUNDLES=80 — 纯物理能量墙

> 评审结论: N^1.5 超线性被否决 (违反 S0 局部性)
> 正确方案: 恒定本底漏电 + 固定 P_inflow

---

## 方案核心

```
每步的能量平衡:
  P_inflow (恒定上限)
  - N × P_basal (每束恒定漏电)  
  - P_dynamic (spike + learning)
  = P_net (剩余可用功率)

当 P_net → 0: EnergyStore 干涸 → sprout 被物理冻结
当 P_net < 0: contract 释放 P_basal 额度 → 零和入侵
```

## 具体修改

### Step 1: EnergyStore 添加 P_inflow 上限

```python
# energy_store.py
class EnergyStoreConfig:
    # 新增: 每步最大充能量 (恒定宇宙功率供应)
    max_deposit_per_step: float = 0.05  # 恒定 P_inflow
```

deposit() 中 cap: `stored = min(effective, space, self.config.max_deposit_per_step)`

### Step 2: hebbian.py metabolic_tax 改为从 EnergyStore withdraw

```python
# 当前: TAX_PER_BUNDLE = 5e-5 (从神经元 energy 扣)
# 改为: BUNDLE_BASAL_COST = 0.001 (从 EnergyStore 扣)
# 物理: 每束每步恒定漏电, 不查全局 N

def _apply_metabolic_tax(self, dt):
    BUNDLE_BASAL_COST = 0.001  # 每束每步的物理维持费
    for bundle in self.get_all_bundles():
        # 从 EnergyStore 扣除 (不是从神经元)
        self.energy_store.withdraw(BUNDLE_BASAL_COST)
        # 保留: 低能量时权重衰减 (已有逻辑)
```

### Step 3: 移除硬上限, 改为 EnergyStore 门控

```python
# 删除: if total_bundles >= self.MAX_TOTAL_BUNDLES
# 新增: sprout 条件加入 EnergyStore 检查
can_afford = (
    not self.energy_store.is_starving  # EnergyStore 非饥饿
    and all(s.energy > self.SPROUT_ENERGY_COST for s in bundle.sources)
)
```

## 参数校准

- P_inflow = 0.05/step
- P_basal = 0.001/bundle/step
- N_max 理论值 = P_inflow / P_basal = 50 bundles (+ dynamic margin)
- 当前初始 N = 34, 预计稳态 N ≈ 40-50
- SPROUT_ENERGY_COST = 0.1 (保持)
- T_recovery = E_sprout / P_net = 0.1 / (0.05 - N×0.001 - P_dyn)

## 验证

80k 运行观察:
1. N_bundles 是否自动收敛? (不再触碰硬上限)
2. EnergyStore.level 是否稳定? (非枯竭也非爆满)
3. E1 system-level ratio 是否保持 < 1.05?
4. axis/cross ratio 是否 > 2.0?
5. 回归测试 21/21?
