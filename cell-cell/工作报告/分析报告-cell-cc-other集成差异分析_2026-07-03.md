# 分析报告：cell-cc-other 与根目录集成差异分析

**日期**：2026-07-03  
**性质**：代码差异审计，评估 cell-cc-other 是否有需要集成到主仓库的内容  
**结论提前**：无需集成。cell-cc-other 是主仓库的旧版快照，主仓库严格更新。

---

## 一、调查方法

```bash
diff -rq --exclude="*.pyc" --exclude="__pycache__" \
  nexus_v1/ cell-cc-other/nexus_v1/
```

同时比较了：
- 根目录下的 `cell-cc-other/`（gitignored 子目录）
- 父目录下的 `../cell-cc-other/`（J:\cell-cc-other，完全独立目录）

两者内容相同，均为同一个旧版本快照。

---

## 二、差异清单

### 2.1 cell-cc-other 中缺少（仅在 nexus_v1/ 存在）

**代码文件（新功能，主仓库特有）**：

| 文件 | 内容 |
|------|------|
| `components/cpg_neuron.py` | CPGNeuron（2Hz VdP 振荡器，DA STDP 稳态冻结修复，commit 7f6269f）|
| `ledger/nu_probe.py` | NuProbe（ν 探针，commit 从 2026-07 初）|
| `ledger/nu_framework_stub.py` | NuProbe 框架存根 |

**测试/实验脚本（新增，主仓库特有，共 20 个）**：
`exp_500k_rc4_validation.py`, `exp_calibrate_gain.py`, `exp_dual_source_long_run.py`, `exp_fix004_validation.py`, `exp_nu_probe_smoke.py`, `exp_phase5_*.py`, `exp_phase6_*.py`, `exp_phase7_*.py`, `exp_phase8_*.py`, `exp_vest_calibration_scan*.py`, `exp_world2_phase3_tri.py`, `probe_thermal_pathway.py`, `test_phase5_signal_probe.py`, `test_vestibular_v2_phase1.py`

**文档**：`vestibular/DIMENSIONAL_CONTRACT.md`（前庭量纲合同，主仓库特有）

### 2.2 代码内容差异（两个文件有差异）

**`nexus_v1/circuit/variant_adapter.py`**：

主仓库版本多出以下内容：
1. **`_patch_temps` dict**（HC-012 fix 的 DR5 patch 温差指标）
2. **P1-DIFF：lamina I proj 神经元**（`_soma_proj`, `_bundles_relay_to_proj`）
3. **P2-HC002：patch-specific relay_to_da bundles**（`bundles_relay_to_da`）
4. **P2-HC007：relay→enc STDP bundles**（`bundles_relay_to_enc`，替代直接注入）
5. **CPG→DA 振荡器**（`_da_cpg`, `bundles_cpg_to_da`）
6. **relay→enc 传播代码**（HC-007 修复逻辑）
7. **proj→DA 传播代码**（P1-DIFF 完整路径）

`cell-cc-other` 版本的 `variant_adapter.py` 是 P1-DIFF、P2、CPGNeuron 修复之前的状态，功能落后主仓库约 3 个阶段。

**`nexus_v1/ledger/__init__.py`**：

主仓库多出：
```python
from .nu_probe import NuProbe, NuSnapshot, NuReport
# 以及 __all__ 中的对应导出
```

### 2.3 cell-cc-other 中有而主仓库没有的内容

**无**。经过全文件差异比较，cell-cc-other 没有任何代码是主仓库缺失的。所有差异均为"cell-cc-other 落后于主仓库"的方向。

---

## 三、时间线重建

根据代码差异，cell-cc-other 的快照时间点估计为：
- **在 P1-DIFF 之前**（proj 神经元未添加）
- **在 P2 HC-002/HC-007 修复之前**（relay_to_da 和 relay_to_enc bundles 未添加）
- **在 CPGNeuron 添加之前**（commit 7f6269f 之前）
- **在 NuProbe 添加之前**

对应主仓库时间线：commit 1942e6b（P1-DIFF）之前的某个版本，即 2026-06 末期。

---

## 四、判断：是否需要集成？

**结论：不需要集成。**

| 评估项 | 结论 |
|--------|------|
| cell-cc-other 是否有主仓库缺失的功能？ | ❌ 否 |
| cell-cc-other 是否有未被主仓库覆盖的修复？ | ❌ 否 |
| cell-cc-other 是否可以安全丢弃？ | ✅ 是，主仓库严格更新 |
| 是否需要从 cell-cc-other 提取任何代码？ | ❌ 否 |

cell-cc-other 作为历史快照保留即可（gitignored），无需任何集成操作。

---

## 五、建议

cell-cc-other 可以作为：
1. **回退参考点**（出现严重 regression 时对比）
2. **历史文档**（代码演化的参考节点）

但不需要合并或同步。主仓库 main 分支（当前 HEAD：`b2597b3`）是唯一的权威代码库。
