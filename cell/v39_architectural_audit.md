# v39 架构底色审计 — 赫布超图是否被坚守？

> 审计日期: 2026-05-15 | 追踪范围: v38→v39 所有改动

## 直接回答

**部分坚守，部分偏离。** 具体来说：

| v39 模块 | 是否经过赫布超图？ | 判定 |
|-----------|---------------------|------|
| Spike Pipeline (Phase A) | **✅ 是** | 完整走 W → z_t → Φ → d_σ_t 链 |
| GMM 组件生命周期 (Phase B) | **❌ 否** | 独立数理模块，输入绕开 z_t |
| Sliced-Wasserstein (Phase D) | **⚠️ 间接** | 输入用的是 cell attributes，非 z_t |
| DuckDB (Phase C) | **N/A** | 存储层，不涉及计算 |

---

## 详细调用链追踪

### ✅ Phase A — Spike Pipeline: **完整经过赫布超图**

```
spike_train_adapter.generate_cells(k)
  └→ CellRecord (V_mean, spike_rate, release_proxy, adaptation_state)
      │
      ▼
run_v39_spike_integration.py:
  signal_values = [c.V_mean for c in cells]
  features = extractor.extract(..., signal_values=signal_values)
      │
      ▼
FeatureExtractor.extract()  [motion_recognition_engine.py:415]
  └→ 检测到 disp_mean < 0.01 AND signal_values 有效
     └→ self._signal_transform.transform(signal_values)
          │
          ▼
HebbianSignalTransform.transform()  [line 302]
  Step 1: extract_signal_features(signal_values) → 6-dim 信号特征
  Step 2: signal_to_z_t(sig_features) → z_t via W_signal (6×7 Hebbian 权重矩阵)
           z_t[j] = Σ_i W[i][j] · signal_feature[i]  ← 这就是赫布超图映射
           └→ MeasureCoordinate (7-dim 测度坐标)
  Step 3: z_t.to_phi()  → Φ(t) 运动势
  Step 4: InternalMeasureTime.compute_from_z(z_t) → d_σ_t 时空测度
  Step 5: disp_proxy = d_σ_t × 0.1,  spread_proxy = Φ × 0.5
      │
      ▼
HebbianSignalTransform.hebbian_update()  [line 332]
  └→ Oja rule: ΔW = η · features · (z_t_prev - W·features)
     └→ 非自环：用前一窗口的 z_t 作为 teacher
      │
      ▼
BayesianMotionRecognizer.classify(features)
  └→ 基于 [disp_proxy, spread_proxy, coherence, periodicity, ...] 的 regime 分类
```

**判定: ✅ Spike Pipeline 完整坚守了项目底色。**

脉冲数据 → 赫布权重矩阵 W → 7-dim 测度坐标 z_t → 运动势 Φ(t) → 时空测度 d_σ_t → regime 分类。**每一步都经过了赫布超图和物理计算链。**

---

### ❌ Phase B — GMM 组件生命周期: **绕开了赫布超图**

```
run_v39_gmm_robustness.py:
  X_allen.append([avg_V, avg_spike, avg_release, avg_adapt, disp, avg_bdist])
      │
      ▼
VariationalGMMEngine.fit(X)
  └→ E-step: γ_ik = π_k · N(x_i|μ_k,Σ_k) / Σ_j ...
  └→ M-step: update μ, Σ, π
  └→ _component_maintenance: prune (π<1%), merge (KL<0.5)
```

> [!WARNING]
> **GMM 的输入是 raw cell attributes (V_mean, spike_rate, ...)，而非经过赫布超图的 z_t。**
>
> `_component_maintenance` 的 merge/prune 决策完全基于 KL 散度和 π 阈值——纯数理判定，没有物理依据。
>
> 在项目的理想架构中，组件合并/剪枝的依据应该是：
> - z_t 空间中组件的距离（而非原始特征空间）
> - d_σ_t 加权的组件寿命
> - Φ(t) 势能面上的鞍点位置

### 如何修正

GMM 的输入应当从 raw cell attributes 改为 **z_t 的 7-dim 测度坐标**：

```python
# 当前 (绕开赫布):
X_allen.append([avg_V, avg_spike, avg_release, ...])  # 6-dim raw

# 应当 (经过赫布):
z_t = signal_transform.signal_to_z_t(sig_features)
X_allen.append(list(z_t.as_tuple()))                   # 7-dim z_t
```

组件 merge 的判定也应考虑 d_σ_t：

```python
# 当前 (纯 KL):
kl_div = self._kl_divergence_diag(mu1, sigma1, mu2, sigma2)

# 应当 (物理加权):
d_sigma_weighted_kl = kl_div * d_sigma_avg  # 时空测度越大的区域，合并阈值越高
```

---

### ⚠️ Phase D — Sliced-Wasserstein: **间接关联**

```
OptimalTransportEngine._cells_to_features(cells):
  features.append([x, y, z, v * 0.3, sr * 0.1, rp * 0.1])
```

> [!NOTE]
> OT 的输入是 cell 的空间+信号特征，经过硬编码缩放（v×0.3, sr×0.1, rp×0.1），**没有经过赫布权重矩阵**。
>
> 这些缩放系数应当来自训练好的 W_signal，而不是手工设定。

### 如何修正

```python
# 当前 (手工缩放):
features.append([x, y, z, v * 0.3, sr * 0.1, rp * 0.1])

# 应当 (赫布权重):
z_t = signal_transform.signal_to_z_t([v, sr, rp, ...])
features.append([x, y, z] + list(z_t.as_tuple()))  # 3 spatial + 7 z_t
```

---

## 总结：项目底色坚守程度

```
 ████████████████████░░░░░░░░  70%  (3/4 模块可修正)
```

### 做对了的

1. **Spike Pipeline 的信号链**: 完整走 signal → W_signal → z_t → Φ → d_σ_t → regime。这是 v38 的核心成果，v39 没有破坏它。
2. **Oja 规则修正**: 打破了 z_t 自环，用 z_t_prev 作为 teacher — 这是对赫布学习理论的正确尊重。
3. **MeasureCoordinate 7-dim 空间**: 保持了非语义的测度坐标设计，z_t 不被赋予人类语义。

### 需要修正的

1. **GMM 应在 z_t 空间运行** — 目前在原始特征空间运行等于绕开了赫布超图
2. **OT 的特征缩放应用 W_signal** — 硬编码权重违反了"一切经过赫布学习"的原则
3. **组件 merge/prune 应考虑 d_σ_t** — 纯数理判定缺少物理时空依据

> [!IMPORTANT]
> **核心问题**: v39 的 Phase B/D 是"在系统外面加了数学工具"而不是"让赫布超图长出新能力"。
>
> 理想做法是：merge/prune 不应是 GMM 引擎的外挂维护，而应是赫布超图中**权重自然衰减到临界值**触发的拓扑重构。

---

## 建议的修正优先级

| 优先级 | 修正 | 难度 | 影响 |
|--------|------|------|------|
| 🔴 高 | GMM 输入改用 z_t 空间 | 中 | 让 GMM 分析的是赫布超图映射后的结构 |
| 🟡 中 | OT 特征缩放改用 W_signal | 低 | 让距离计算反映学到的信号权重 |
| 🟢 低 | merge/prune 触发条件加入 d_σ_t | 中 | 让组件管理有物理时空依据 |
