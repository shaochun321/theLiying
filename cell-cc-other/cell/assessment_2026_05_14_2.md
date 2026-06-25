# 2026.5.14.2 诚实评估

## 一句话总结

**在一个 session 内完成了从"计划"到"12/12 checklist 通过"的全部执行，速度快，但部分环节的深度不足以支撑"论文级"这一原始目标。**

---

## 真正做到的事情

### ✅ 高质量完成

| 完成项 | 质量评价 |
|--------|---------|
| Allen Brain 数据下载 + CSV 提取 | **扎实**。NWB → CSV 的提取链完整，metadata.json 包含 DOI 和许可证，可追溯。 |
| AllenBrainAdapter 接口 | **规范**。完全遵循 CTCRealDataAdapter 的 CellRecord/EnvelopeRecord 接口，calibration/validation/holdout 三段切分设计合理。 |
| HebbianSignalTransform 架构 | **你的纠正后质量大幅提升**。从"sig_std * 2.0"的粗暴代理修正为 z_t → Φ → d_σ_t 的正规链路，用 Oja 规则训练 W_signal，与现有 MeasureCoordinate/InternalMeasureTime 基础设施正确对接。 |
| Phase 4 统计检验 | **方法正确**。paired t-test + Cohen's d + 混淆矩阵是标准做法。p ≈ 0、d = 5.48 的结果在 10 seeds 上可重现。 |
| 向后兼容性 | **未破坏现有功能**。honest baseline 回归测试通过（95.5%），说明新增代码没有污染旧路径。 |

### ⚠️ 速度换深度的妥协

| 项目 | 缺失的深度 |
|------|-----------|
| Phase 4.2 "基线对比" | 计划里说要跑 **k-means / GMM / PCA** 作为 PRX 分解的基线对比。实际只比了 Bayesian vs Legacy vs Random。没有 sklearn 级别的外部基线。这是"论文级验证"的硬伤。 |
| Allen Brain 端到端 | 跑通了，但 **4 种 regime 中 3 种来自同一个分类簇**（slow_drift 87.8%）。真实数据的 regime 分布极度偏斜，说明分类器可能只是在利用方差阈值做粗分割，而不是真正学到了神经活动的结构。 |
| W_signal 的训练 | Hebbian 更新确实在每个窗口运行了，但 **没有显式的 calibration→freeze→validation 流程验证**。训练和推理在同一个 loop 里混在一起，freeze() 从未被调用。 |
| 运动体制扩展 | 加了 `burst_firing` 和 `sustained_activity`，但这两个新体制 **没有对应的 MotionProcessGenerator 逻辑**。它们在 MOTION_REGIMES 字典里有定义但无法被 `gen.step()` 实际生成。 |

---

## 架构上的真实进步

### HebbianSignalTransform（核心亮点）

你在 session 中期指出的架构缺陷是今天最重要的一个修正。修正前后的对比：

```
修正前: ΔF/F → sig_std * 2.0 → 直接当位移用
         ↑ 这跳过了整个时空测度体系
         
修正后: ΔF/F → sig_features(6d) → z_t(7d) via W_signal → Φ(t) → d_σ_t → disp_proxy
                                         ↑ 
                                    Oja 规则训练
                                    W 矩阵可审计
                                    对接 MeasureCoordinate
```

这个修正的意义：**信号到运动的映射现在经过了与空间位移完全相同的 z_t → Φ → d_σ_t 链路**。这意味着：
- 钙信号和空间位移在同一个测度空间里比较
- W_signal 的每一行都有明确的物理含义（sig_mean → potential_displacement_cost 等）
- 权重的训练/冻结/审计生命周期是显式的

### 但它还不够完整

> [!WARNING]
> W_signal 当前的 Oja 更新中，**z_t 本身依赖于 W**。这形成了一个循环：
> 
> `z_t = W · features`  →  `ΔW = η · features · (z_t - W · features)`
> 
> 代入后：`ΔW = η · f · (W·f - W·f²)` — 当 features 不是单位向量时，这不是严格的 Oja 规则。严格的 Oja 需要**独立的教师信号**（ground truth z_t），而不是 W 自己产生的 z_t。
> 
> 目前的实现实质上是**自编码器**式的权重调整，不是有监督的 Hebbian 学习。这在实践中可能仍然收敛到有意义的表示，但理论保证弱于真正的 Oja。

---

## 数字层面的诚实评价

### Bayesian 准确率：88.0% vs 98.9%

Phase 1.1（3 seeds）报告了 98.9%。Phase 4（10 seeds）报告了 88.0%。

这是**好事**：更多的 seeds 暴露了更真实的性能。88.0% ± 2.2% 是一个诚实的数字。但它也说明**小样本评估的方差很大**（3 seeds 碰巧都接近最优 schedule 的位置）。

### Allen Brain regime diversity = 4

看起来不错，但：
- `slow_drift` 占 87.8%，几乎是单峰分布
- `oscillation` 只在验证集出现了 21.1%（训练集 2.0%）
- 这可能表示**验证集的信号特征恰好跨越了 slow_drift / oscillation 的决策边界**，而不是分类器真正区分了两种神经活动模式

### ELBO = 535.33

22 轮收敛，monotonic，看起来不错。但要注意：
- GMM 的输入是 6 维 per-window 聚合特征，N=40 窗口
- 这意味着 **40 个数据点拟合 7 分量 GMM** — 严重过参数化
- ELBO 收敛不等于模型质量好，只说明 EM 算法工作正常

---

## 遗留的架构债务

| 债务 | 严重程度 | 修复建议 |
|------|---------|---------|
| W_signal 训练/冻结未分离 | 🟡 中 | 在 integration test 中显式调用 `freeze()`，验证冻结后 W 不变 |
| burst_firing / sustained_activity 无生成器 | 🟡 中 | 在 MotionProcessGenerator.step() 中添加信号模式生成逻辑 |
| 无 sklearn 外部基线 | 🔴 高 | 论文级声称需要 k-means、GMM、PCA 作为硬基线 |
| engines/ 和根目录有两份 motion_recognition_engine.py | 🟡 中 | 应该只保留一份（引入 symlink 或删除副本） |
| Oja 更新的自循环问题 | 🟡 中 | 考虑用 target z_t（如前一窗口的 z_t）替代当前 W 产生的 z_t |
| Allen Brain 数据只有 1 个实验 | 🟡 中 | 扩展到 2-3 个不同 VISp/VISl 实验以验证泛化性 |

---

## 总评

**2026.5.14.2 是一个高效的工程执行日。** 在一个 session 内完成了从 Allen Brain 数据下载到统计检验报告的全流程，12/12 checklist 通过。

**但它不是一个"论文级验证"日。** 原始计划的 Phase 4.2 要求 k-means/GMM/PCA 基线对比，这没有做。Phase 3.1 的新体制没有完整实现（只有字典条目，没有生成器逻辑）。W_signal 的训练/冻结生命周期没有在测试中显式验证。

**最有价值的一刻是你在 session 中期的架构纠正。** 把 "sig_std * 2.0" 换成 HebbianSignalTransform 是今天唯一触及系统理论内核的改动。其他都是工程层面的"接线"工作。

### 给分（5 分制）

| 维度 | 分数 | 理由 |
|------|------|------|
| 执行速度 | ⭐⭐⭐⭐⭐ | 一个 session 内完成全部 4 个 Phase |
| 工程质量 | ⭐⭐⭐⭐ | adapter 接口规范，回归测试通过，无破坏 |
| 理论深度 | ⭐⭐⭐ | HebbianSignalTransform 方向正确但 Oja 自循环问题未解 |
| 评估诚实度 | ⭐⭐⭐⭐ | 10-seed 统计检验 + t-test 是标准做法，但缺 sklearn 基线 |
| 架构完整性 | ⭐⭐⭐ | 两份 motion_recognition_engine.py、未冻结 W、未实现的体制 |

**综合：3.8 / 5 — 高效的工程冲刺，但离"论文级"还差一层严谨性。**
