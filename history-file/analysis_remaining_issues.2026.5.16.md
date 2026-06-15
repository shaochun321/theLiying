# v40.9 结构审计：剩余改进项

## 已完成（本轮）

| 项 | 状态 |
|---|---|
| LIF 参数注入删除 | ✅ 完成，cos 从注入版 0.333 → 纯物理 0.498 |
| 命名改为物理力场 | ✅ `uniform_oscillation` / `stochastic_impulse` / `structured_compression` |
| 自测修复 | ✅ 两个 self-test 均 PASS |
| 214 粒子扩展 | ✅ 空间网格加速，~3min 完成 |
| CTC 真实数据接入 | ✅ pipeline 通过 |

---

## 剩余问题（按优先级）

### 1. CTC 的伪标签问题（高）

```python
# runner 中的 CTC 处理：
if phase_frac < 0.33:
    stim_label = "growth_early"
elif phase_frac < 0.66:
    stim_label = "growth_mid"
else:
    stim_label = "growth_late"
```

**问题**：这是人为切段，与物理审计中指出的 LIF 注入本质相同 — 把答案塞进数据。

**正确做法**：CTC 是连续过程，不应做"判别"。应该评估的是：
- 轨迹预测误差（前一帧 → 当前帧的位置/面积预测残差）
- 分裂事件检测率（track_id 分支点）
- 群体同步性变化（所有细胞运动方向的一致程度）

这些是物理-结构意义上的指标，不需要人为分段。

### 2. Signal entropy 对物理数据的敏感度（中）

纯物理引擎 `cos=0.498`，好于预期但不如 Allen Brain 的 `0.298`。

当前 signal entropy 的 7 通道（spectral, fano, synchrony, gradient, sparseness, autocorrelation, energy）
是为 Allen Brain 的 ΔF/F 钙成像信号设计的。对于物理粒子系统的 V_mean 分布，
可能需要增加物理相关的 entropy 通道：

| 候选通道 | 物理含义 |
|---|---|
| stress_entropy | 弹簧应力分布的熵 |
| velocity_coherence | 速度场的空间一致性 |
| topology_change | 弹簧连接的动态变化率 |
| displacement_kurtosis | 位移分布的峰度（区分全局/局部运动） |

但这需要在 `pipeline_engine.write_signal_entropy_ledger` 中增加物理通道，
属于架构层面的改动。

### 3. 性能（低-中）

214 粒子 × 100 窗口 × 100 步/窗 = 2,140,000 物理步

当前纯 Python 实现约 3 分钟。如果扩展到 1000+ 粒子或更长仿真，会成为瓶颈。

优化路径：
- **NumPy 矢量化**：力计算从逐粒子循环改为矩阵运算（预计 10-50× 加速）
- **Cython/Numba**：JIT 编译 step() 函数
- 但这会增加外部依赖，违反 "no external dependencies" 原则

### 4. 外部熵账本覆盖（中）

`write_external_ledgers` 应该为物理引擎记录力学特征的熵收支。
当前外部熵审计可能没有充分覆盖物理层的能量守恒和耗散。

需要验证：
- 弹簧势能 + 动能 + 阻尼耗散 = 外力做功？
- 每个窗口的能量收支是否被记入外部熵账本？

### 5. CTC adapter 的 `_BASE` 路径（低）

```python
# ctc_source_adapter.py line 35
_BASE = Path(__file__).resolve().parent  # engines/
```

但 CSV 数据在 `data/` 目录下，需要 `parent.parent`：

```python
csv_path = str(_BASE / "data" / "ctc_centroids_real_v24.csv")
```

如果 adapter 在 engines/ 子目录中，这个路径可能不对。
（实际运行通过了，说明 runner 的 sys.path 修正了这个问题）

---

## 建议执行顺序

1. **CTC 连续评估指标**（最重要 — 与物理审计同一原则）
2. **外部熵账本验证**（维护项目完整性）
3. **物理 entropy 通道**（提升判别力的正确方式）
4. **性能优化**（可延后）
