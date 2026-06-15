# v40.6: 结构分化 + 阈值多样性 + 时空窗口主动获取

基于 [implementation_plan.2026.5.15.9.md](file:///D:/cell-cc/cell/implementation_plan.2026.5.15.9.md) 的执行计划。

## 当前状态

```
35/35 alive | 22 bundles | 4 zones | cos=0.056 (↓94.3%)
movie:    [0.000  0.000  0.000  0.000  0.000  0.000  0.000]  (0/7 active)
threshold std = 0.000
```

3 个剩余张力：movie 零激活、阈值多样性=0、masking genuine=34%（本阶段不解决）

---

## Proposed Changes

### 方案 C（优先）: Contrastive Gain 动态化

#### [MODIFY] [run_v40_integrated.py](file:///D:/cell-cc/Morphosphere_v37_0_native_runtime_prototype_flat_complete/morphosphere_v2pp/runners/run_v40_integrated.py)

- **L449-450**: 将硬编码的 `ho_means` / `ho_stds` 替换为从 `v40_signal_entropy_ledger` 实时计算的统计量
- 在 Phase 1.5 之后、Phase 2 之前插入计算逻辑
- 从 DB 中 SELECT `population_sparseness`, `temporal_autocorrelation`, `energy_concentration` 并计算 μ 和 σ

---

### 方案 A: 阈值多样性结构分化

#### [MODIFY] [run_v40_integrated.py](file:///D:/cell-cc/Morphosphere_v37_0_native_runtime_prototype_flat_complete/morphosphere_v2pp/runners/run_v40_integrated.py)

- 在 `build_signal_entropy_circuit()` 函数中：
  - zone 中间神经元按 zone 类型设置不同 `target_rate`：
    - spectral: 0.05, fano: 0.02, synchrony: 0.06, gradient: 0.08
  - z_t 目标神经元按维度设置不同 `target_rate`：
    - transition: 0.04, drift: 0.03, gamma_desync: 0.04, xin_residual: 0.03 等

#### [MODIFY] [hebbian_circuit.py](file:///D:/cell-cc/Morphosphere_v37_0_native_runtime_prototype_flat_complete/morphosphere_v2pp/engines/hebbian_circuit.py)

- **L74 区域** `MetaNeuron.__init__`: `calcium_tau` 改为动态计算
  - `calcium_tau = max(5.0, min(50.0, 1.0 / max(target_rate, 0.001)))`
  - 需要在 `__post_init__` 或 `activate()` 中首次调用时计算（因为 dataclass 默认值不能引用 field）

---

### 方案 B: Movie 零激活 → 时空窗口主动获取

#### [MODIFY] [pipeline_engine.py](file:///D:/cell-cc/Morphosphere_v37_0_native_runtime_prototype_flat_complete/morphosphere_v2pp/pipeline_engine.py)

- 新增函数 `compute_temporal_resolution_augmentation(conn, run_id, stim, target_windows)`
  - 从已有窗口的 7-channel entropy 计算 μ 和 Σ
  - 用 shrinkage bootstrap 生成合成窗口
  - 合成窗口的 STDP 学习率权重 = N_real / (N_real + N_aug)
  - 插入 `v40_signal_entropy_ledger` 并标记 `calculation_variant = "v40_bootstrap_augmented"`

#### [MODIFY] [run_v40_integrated.py](file:///D:/cell-cc/Morphosphere_v37_0_native_runtime_prototype_flat_complete/morphosphere_v2pp/runners/run_v40_integrated.py)

- Phase 1.5 后新增 Phase 1.7：时空分辨率审计
  - 统计每个刺激的窗口数
  - 窗口数 < 20 → 调用 augmentation

---

## Open Questions

> [!IMPORTANT]
> **方案 B 的 bootstrap 合成窗口 vs 学习率提升**：计划原文中提出了替代方案——不合成窗口，而是对 movie 的 STDP 学习率提高 2.5×。这保持了信源真实性但可能过拟合。
>
> 原计划的 Open Question 问你判断哪种更符合项目底色。**我建议先实现 bootstrap 合成方案（方案 B 原方案），因为它有更明确的数理基础且可以通过 `calculation_variant` 标记来审计。如果你倾向学习率提升方案，请告知。**

---

## 执行顺序

| 步骤 | 改什么 | 预期结果 |
|:---:|--------|---------|
| **C.1** | Contrastive gain 均值/std 从 DB 计算 | 消除硬编码 |
| **A.1** | Zone target_rate 差异化 | 阈值开始分化 |
| **A.2** | calcium_tau 动态化 | threshold std > 0.001 |
| **B.1** | temporal_resolution_ledger 新表 | 检测 starved 刺激 |
| **B.2** | Bootstrap 合成窗口 | movie 获得 12 个额外窗口 |
| **B.3** | 合成窗口注入 circuit loop | movie z_t 激活 |
| **验证** | run_v40_integrated → diag_rchain | 全面对比 |

## Verification Plan

### 自动测试
```bash
python runners/run_v40_integrated.py    # 主循环
python runners/diag_rchain.py           # 反证链
python runners/run_v40_circuit_validation.py  # 电路验证
```

### 成功标准

| 指标 | 当前 | 目标 |
|------|:---:|:---:|
| threshold std | 0.000 | > 0.001 |
| movie active dims | 0/7 | ≥ 2/7 |
| scenes active dims | 3/7 | ≥ 3/7（保持） |
| cos(scenes, gratings) | 0.169 | < 0.20（保持） |
| avg cos | 0.056 | < 0.10（保持） |
| alive neurons | 35/35 | 35/35（保持） |
