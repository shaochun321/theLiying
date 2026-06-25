# Morphosphere v39 → v40 改善计划

## 目标

将系统从"内部一致性验证"升级为"外部可检验的科学工具"。

---

## Tier 0: 最高优先级（解决根本性限制）

### 0A. 外部刺激验证 — 用 NWB 刺激时间轴作为 Ground Truth

> **核心问题**：0.849 准确率是在系统自定义标签上测的，不是外部标注。

**方案**：NWB 文件（已在 `data/allen_brain/ophys_experiment_data/500964514.nwb`，414MB）包含刺激时间轴（stimulus epochs）。`three_session_B` 协议包含：

- Natural movie 片段（高动态，预期 → fast_drift/oscillation）
- Drifting gratings（周期性，预期 → oscillation）
- Static gratings（低动态，预期 → stationary/slow_drift）
- Spontaneous activity（无刺激，预期 → stationary）

这些刺激类型构成**外部可验证的 ground truth**。

#### 具体改动

##### [NEW] `runners/run_v39_stimulus_validation.py`
1. 用 `h5py` 或 `pynwb` 从 NWB 读取 stimulus epoch 时间范围
2. 将每个窗口映射到其所在的刺激类型
3. 运行 BayesianMotionRecognizer 分类每个窗口
4. 建立 confusion matrix：检测到的运动模式 vs 实际刺激类型
5. 报告：per-stimulus accuracy、regime-stimulus correspondence

##### [MODIFY] `engines/allen_brain_adapter.py`
添加 `get_stimulus_epoch(window_k)` 方法，从 NWB 读取当前窗口的刺激类型。

##### 预期结果
- 如果 natural_movie 窗口多检测到 fast_drift/oscillation → 映射有物理意义 ✅
- 如果 spontaneous 窗口多检测到 stationary → 映射有物理意义 ✅
- 如果没有对应关系 → 模式可能只是数学聚类，需重新审视

> [!IMPORTANT]
> 这是唯一能将系统从"自洽"升级为"可验证"的改进。建议最高优先执行。

---

### 0B. Pipeline 模块化分解

> **核心问题**：pipeline_engine.py 1900+ 行，所有 T/O/P/R/Xin 逻辑耦合在一起。

#### 具体改动

##### [NEW] `pipeline/` 目录结构
```
pipeline/
├── __init__.py           # 统一导入
├── transport.py          # write_transport, write_cells
├── observation.py        # write_v366_measures, write_legacy_observable_layer
├── p_core.py             # write_hypotheses (P/R candidate lifecycle)
├── r_core.py             # R confirmation graph logic
├── xin.py                # write_xi, write_xi_lifecycle_closure
├── ledger.py             # write_external_ledgers (entropy + anomaly)
├── shadow_bridge.py      # Shadow interment wiring
├── fhpms_bridge.py       # FHPMS fiber transport
└── legacy.py             # write_legacy_recursive/diagnostic_layer
```

##### [MODIFY] `pipeline_engine.py`
保留为 thin facade，import 并转发到新模块：
```python
from pipeline.transport import write_transport
from pipeline.p_core import write_hypotheses
from pipeline.xin import write_xi, write_xi_lifecycle_closure
# ... etc
```

##### 预期收益
- 每个模块可独立测试
- 修改 Xin 不影响 Transport
- 新 runner 只需 import 需要的模块

> [!WARNING]
> 这是纯工程重构，不改变任何行为。需要全部回归测试通过后才算完成。

---

## Tier 1: 高优先级（验证系统声明的能力）

### 1A. 对抗鲁棒性测试

> **核心问题**：拓扑迟滞从未被真正攻击过。

##### [NEW] `runners/run_v39_adversarial_stress.py`
构造 3 类攻击向量：

| 攻击 | 方法 | 预期防御 |
|------|------|---------|
| **Xin 脉冲** | 单窗口注入 mass=0.5 的 Xi | 迟滞积分器过滤（不触发 ΔW） |
| **慢爬攻击** | 连续 20 窗口注入 d_σ_t=0.2 | 积分器累积到 3.0 后触发（正确响应） |
| **交替噪声** | 高-低-高-低交替信号 | 迟滞积分器的 15% 泄漏应抵消 |

验证标准：脉冲攻击不触发、慢爬攻击正确触发、交替噪声不触发。

### 1B. 影子共振语义验证

> **核心问题**：cos=0.99 可能是平凡的数学性质。

##### [NEW] `runners/run_v39_shadow_semantics.py`
设计实验：
1. 从不同刺激类型的窗口各取 5 个 z_t
2. 将 natural_movie 的 z_t inter 到影子层
3. 用 spontaneous 的 z_t 做 check_resonance
4. 如果跨类型共振低、同类型共振高 → 影子层有语义区分力
5. 如果所有类型共振都高 → W_signal 映射区分力不足

---

## Tier 2: 中优先级（扩展能力）

### 2A. 扩展 HebbianHypergraph 的审计深度

##### [MODIFY] `engines/hebbian_hypergraph.py`
添加：
- `query_weight_drift(window_range)` — 查询 W_signal 在训练过程中的漂移轨迹
- `query_shadow_resonance_map()` — 按源类型、按模式汇总共振分布
- `query_entropy_trend()` — 从熵账本聚合趋势数据，支持工程师调参

### 2B. 公式候选竞争的熵驱动调整

##### [MODIFY] `formula_candidate_registry.py`
当前 `FormulaCandidateCompetitionEngine` 的 EM 更新使用固定的 performance metrics。改为：
1. 从 `external_entropy_ledger` 读取最近 N 个窗口的熵趋势
2. 将熵稳定性作为额外 fitness signal 注入 J[ρ] 目标函数
3. 高熵方差 → 降低对应公式候选的权重

> 这不违反铁律，因为是**工程师审视后的手动调整流程**，不是自动反馈。

---

## 决策点

> [!IMPORTANT]
> 请告知优先级选择：
> 1. **只做 0A**（刺激验证）— 最快验证系统的科学价值
> 2. **做 0A + 0B**（验证 + 模块化）— 全面但耗时
> 3. **做 0A + 1A**（验证 + 对抗测试）— 验证系统的两个核心声明
> 4. **全部按顺序执行** — 完整路线图

## 依赖项检查

```
NWB 读取: 需要 h5py（标准库级依赖）或 pynwb
         NWB 文件已在本地: ophys_experiment_data/500964514.nwb (414MB) ✅
模块化:   纯重构，无新依赖
对抗测试: 无新依赖，使用现有 Engine B
```
