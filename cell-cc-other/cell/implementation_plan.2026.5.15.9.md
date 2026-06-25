# v40.6 方案：结构分化 + 阈值多样性 + 时空窗口主动获取

## 当前状态

```
35/35 alive | 22 bundles | 4 zones | cos=0.056 (↓94.3%)
scenes:   [0.000  0.079  0.000  0.002  0.000  0.012  0.000]  (3/7 active)
gratings: [0.058  0.019  0.055  0.071  0.064  0.007  0.041]  (7/7 active)
movie:    [0.000  0.000  0.000  0.000  0.000  0.000  0.000]  (0/7 active)
Xin=1.40 | T=0.079 | μ(G)=0.065 | threshold std=0.000
```

## 3 个剩余 Xin 张力

| 张力 | 根因 | 类型 |
|------|------|------|
| movie 零激活 | 8 窗口不够 STDP 收敛 | 时空窗口不足 |
| 阈值多样性=0 | `calcium_tau=20` 太慢，100 ticks 后所有阈值仍在 floor | 结构参数 |
| masking genuine=34% | 管线层面的结构性强迫 | 不在此阶段解决 |

---

## 方案 A：阈值多样性结构分化

### 问题诊断

当前所有 7 个 z_t 神经元的阈值 = `0.0001`（floor）。原因链：

```
calcium_tau = 20 → calcium 积累极慢
→ calcium ≈ 0.001~0.009（远低于 target_rate=0.03）
→ error = calcium - target = -0.029~-0.021 → 始终为负
→ threshold -= 0.01 × 0.029 = -0.00029/tick → 持续下降
→ 100 ticks 后 → 全部钉在 floor = 0.0001
```

### 修复

不是改参数，而是让 **zone membership 决定阈值**。不同 zone 的中间神经元有不同的 `target_rate`，因为不同熵通道的激活频率不同。

#### 修改 1: [run_v40_integrated.py](file:///d:/cell/Morphosphere_v37_0_native_runtime_prototype_flat_complete.tar/Morphosphere_v37_0_native_runtime_prototype_flat_complete/Morphosphere_v37_0_native_runtime_prototype_flat_complete/morphosphere_v2pp/runners/run_v40_integrated.py)

zone 的 `target_rate` 根据对应熵通道的 **coefficient of variation** 来设置：

```python
zone_target_rates = {
    "spectral": 0.05,    # cv=24.6% → moderate variability → moderate target
    "fano": 0.02,        # cv=56.2% → high variability → low target (sparse responder)
    "synchrony": 0.06,   # cv=29.8% → moderate → slightly higher
    "gradient": 0.08,    # cv=19.3% → low variability → high target (tonic responder)
}
```

- fano zone 的中间神经元 `target_rate=0.02` → 稀疏激活 → 阈值高 → 只对强 fano 信号响应
- gradient zone 的中间神经元 `target_rate=0.08` → 紧张激活 → 阈值低 → 对所有 gradient 信号持续响应

z_t 神经元本身的 `target_rate` 也差异化，基于每个维度被 zone bundle 连接的频次：

```python
z_t_target_rates = {
    "transition": 0.04,     # 被 synchrony + gradient 两个 zone 覆盖
    "drift": 0.03,          # 被 fano 单独覆盖
    "gamma_desync": 0.04,   # 被 synchrony 单独覆盖
    "xin_residual": 0.03,   # 被 gradient 单独覆盖
    "potential_disp": 0.02, # 被 spectral 单独覆盖
    "churn": 0.03,          # 被 fano 单独覆盖
    "magnitude": 0.02,      # 被 spectral 单独覆盖
}
```

#### 修改 2: [hebbian_circuit.py](file:///d:/cell/Morphosphere_v37_0_native_runtime_prototype_flat_complete.tar/Morphosphere_v37_0_native_runtime_prototype_flat_complete/Morphosphere_v37_0_native_runtime_prototype_flat_complete/morphosphere_v2pp/engines/hebbian_circuit.py) L144-149

`calcium_tau` 从固定 20 → 基于 `target_rate` 动态计算：

```python
# calcium_tau 与 target_rate 反比：稀疏响应者需要更长积累周期
self.calcium_tau = max(5.0, min(50.0, 1.0 / max(self.target_rate, 0.001)))
```

`target_rate=0.02` → `calcium_tau=50`（慢积累，允许稀疏激活）
`target_rate=0.08` → `calcium_tau=12.5`（快积累，快速适应）

#### 预期效果

100 ticks 后，各 z_t 阈值因 target_rate 不同而分化到不同水平：
- transition (target=0.04, tau=25): threshold ≈ 0.003
- magnitude (target=0.02, tau=50): threshold ≈ 0.0005
- 阈值 std 从 0 → ~0.001+

---

## 方案 B：Movie 零激活 → 时空窗口主动获取

### 问题诊断

Movie 有 8 个窗口。每个窗口只经历 1 次 circuit tick。STDP 的 conductance 变化量 per tick = `0.01 × w_change ≈ 0.003`。8 ticks 后变化量 = 0.024 — 远不足以让 zone 中间神经元的激活越过 z_t 的阈值。

> [!IMPORTANT]
> 根据你之前的指导：*"这个模块功能应该为内部时空尺度切分与主动获取外部更大时空尺度"*

### 方案：Multi-Resolution Window Amplification

在外部熵账本中增加 `v40_temporal_resolution_ledger`，实现：

1. **自动检测窗口不足**：如果某刺激的窗口数 < 阈值（如 20），标记为 `resolution_starved`
2. **时空尺度插值**：对 starved 刺激，用已有窗口的熵值做 **bootstrap 重采样**，生成合成窗口
3. **渐弱权重**：合成窗口的 STDP 学习率乘以衰减因子 `α = real_windows / total_windows`

#### 修改 1: [pipeline_engine.py](file:///d:/cell/Morphosphere_v37_0_native_runtime_prototype_flat_complete.tar/Morphosphere_v37_0_native_runtime_prototype_flat_complete/Morphosphere_v37_0_native_runtime_prototype_flat_complete/morphosphere_v2pp/pipeline_engine.py)

新函数 `compute_temporal_resolution_augmentation(conn, run_id)`

```python
def compute_temporal_resolution_augmentation(conn, run_id):
    """检测窗口不足的刺激，生成 bootstrap 合成窗口。

    数理关系：
    对于 N_real 个真实窗口的刺激 S：
    1. 计算 S 的 7-channel entropy 均值 μ_S 和协方差 Σ_S
    2. 从 N(μ_S, Σ_S × shrinkage) 采样 N_aug 个合成窗口
       - shrinkage = N_real / N_target → 窗口越少，合成窗口越接近均值
    3. 合成窗口的 STDP 学习率权重 = N_real / (N_real + N_aug)

    这与 T/O/P/R/Xin 的关系：
    - T: 检测 starved 信号 → temporal resolution 不足
    - O: 计算当前窗口数的统计充分性
    - P: 生成合成窗口扩展环流基线
    - R: shrinkage 因子约束合成窗口不偏离真实分布
    - Xin: 合成权重 < 真实权重 → 保持结构性谦逊
    """
```

#### 修改 2: [run_v40_integrated.py](file:///d:/cell/Morphosphere_v37_0_native_runtime_prototype_flat_complete.tar/Morphosphere_v37_0_native_runtime_prototype_flat_complete/Morphosphere_v37_0_native_runtime_prototype_flat_complete/morphosphere_v2pp/runners/run_v40_integrated.py)

Phase 1.5 后增加 Phase 1.7：时空分辨率审计

```python
# Phase 1.7: 时空分辨率审计
stim_counts = {}  # 统计每个刺激的窗口数
for row in sig_rows:
    stim = get_stimulus_for_window(row[0])
    stim_counts[stim] = stim_counts.get(stim, 0) + 1

MIN_WINDOWS = 20  # 最低统计充分性
for stim, count in stim_counts.items():
    if count < MIN_WINDOWS:
        print(f"  ⚠ {stim}: {count} windows < {MIN_WINDOWS} → augmenting")
        aug_rows = pe.compute_temporal_resolution_augmentation(
            conn, run_id, stim, target_windows=MIN_WINDOWS)
```

#### 预期效果

- movie: 8 → 20 窗口（12 个合成，权重 = 8/20 = 0.4）
- 合成窗口足以让 STDP 产生有意义的 conductance 变化
- movie 的 z_t 从 0/7 → 预计 2-4/7 active

---

## 方案 C：Contrastive Gain → 结构化 STDP 调制

### 问题

当前 contrastive gain modulation 使用**硬编码的均值和标准差**：

```python
ho_means = {"sparseness_H": 0.88, "autocorrelation_H": 0.38, "energy_H": 0.95}
ho_stds = {"sparseness_H": 0.05, "autocorrelation_H": 0.07, "energy_H": 0.03}
```

这是从 `diag_higher_order.py` 的一次运行中提取的。如果换数据集或细胞数量变化，这些值就失效了。

### 修复：从 DB 动态计算

在 Phase 1.5 后，从 `v40_signal_entropy_ledger` 实时计算 7 个通道的均值和标准差，存入 DB。Contrastive gain 从 DB 读取而非硬编码。

#### 修改: [run_v40_integrated.py](file:///d:/cell/Morphosphere_v37_0_native_runtime_prototype_flat_complete.tar/Morphosphere_v37_0_native_runtime_prototype_flat_complete/Morphosphere_v37_0_native_runtime_prototype_flat_complete/morphosphere_v2pp/runners/run_v40_integrated.py)

```python
# 在 Phase 1.5 之后计算
ho_channels = ["population_sparseness", "temporal_autocorrelation", "energy_concentration"]
ho_stats = {}
for col_name in ho_channels:
    vals = conn.execute(
        f"SELECT {col_name} FROM v40_signal_entropy_ledger"
    ).fetchall()
    vals = [v[0] for v in vals]
    mu = sum(vals) / len(vals)
    std = math.sqrt(sum((v - mu)**2 for v in vals) / len(vals))
    ho_stats[col_name] = {"mean": mu, "std": std}
```

---

## 执行顺序

| 步骤 | 改什么 | 预期结果 |
|:---:|--------|---------|
| **C.1** | Contrastive gain 均值/std 从 DB 计算 | 消除硬编码 |
| **A.1** | Zone target_rate 差异化 | 阈值开始分化 |
| **A.2** | calcium_tau 动态化 | 阈值 std > 0.001 |
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

## Open Questions

> [!IMPORTANT]
> **方案 B 的 bootstrap 合成窗口**：合成窗口本质是用已有分布的采样来填充信号缺失。这在统计上是合理的（bootstrap 是标准方法），但在你的项目哲学中，这算不算"伪造信源"？你之前强调"所有对象的表征都是信息的时空轨迹"——合成窗口没有真实的时空轨迹。
>
> 替代方案：不合成窗口，而是**降低 movie 的 STDP 收敛阈值**——让 8 个真实窗口的 STDP 学习率提高 2.5×。这保持了信源的真实性，但可能引入过拟合风险。
>
> 请判断哪种更符合项目底色。
