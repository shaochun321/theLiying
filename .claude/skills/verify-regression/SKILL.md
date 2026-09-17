---
name: verify-regression
description: cell-cc 验证收口流程。任何代码改动后的回归验证、写报告前的"回归状态"行、全量复验收口时调用。含母体回归/contracts/audit/TSS pytest 分层命令序列、标准输出格式、当前已知失败基线。
---

# 验证收口（verify-regression）

**所有命令从 repo 根目录（`j:\cell-cc` 或 worktree 根）执行。** Windows 原生终端必须加 `PYTHONIOENCODING=utf-8` 前缀（GBK 控制台会在打印 ✓/熵/→ 时 `UnicodeEncodeError` 崩溃——崩溃是表面的，测试逻辑已跑完；WSL 下无需前缀）。

## 母体三件套（每次代码改动后必跑）

```bash
# 1. 主回归套件（21 项, ~29s, exit 0 = pass）
PYTHONIOENCODING=utf-8 python -m nexus_v1.tests.test_regression
# pytest 包装也存在: python -m pytest nexus_v1/tests/test_regression.py

# 2. 层契约检查（15 项 C1..C6）
PYTHONIOENCODING=utf-8 python nexus_v1/run_contracts.py
PYTHONIOENCODING=utf-8 python nexus_v1/run_variant_contracts.py

# 3. 熵审计（signal depth / layer activations / weights）——参数改动后强制
PYTHONIOENCODING=utf-8 python nexus_v1/run_audit.py
```

其他诊断入口：`python nexus_v1/run_test.py`（5 项集成测试 static/rotation/path）。

**已知失败基线（2026-09-06 复测）：** contracts 13/15 —— C2 HC output_range `[0.0000, 0.2488]` vs 期望 `[0.001, 0.6]`，C3 Aff frequency 2.0 Hz vs 期望 `[20,100] Hz`，两者均归因 DEG-004（OPEN）。判定标准写法：**失败集合 ⊆ 父提交失败集合** 即为不退化。C6 Motor 三项子检查现全 PASS（旧文档说它失败的信息已过时）。

## TSS 复验序列（2026-09 收口常态）

```bash
PYTHONIOENCODING=utf-8 python -m tss.tests.test_version_pairing   # fail-fast 版本配对，先跑
PYTHONIOENCODING=utf-8 python -m pytest tss/tests -m fast -q         # ~43 项, ~14s
PYTHONIOENCODING=utf-8 python -m pytest tss/tests -m integration -q  # ~45 项
PYTHONIOENCODING=utf-8 python -m pytest tss/tests -m "not longrun" -q  # 日常全量
# 完整套件（含 longrun）约 1:56:05，仅收口时跑
```

- 单个 TSS 测试：`PYTHONIOENCODING=utf-8 python -m tss.tests.test_<name>`（45 个 test_* 均有 pytest + `__main__` 双入口）
- **pytest 全绿 ≠ 全部实验通过**：`exp_*/_diag_*/_probe_*` 不被 pytest 收集（约 20 个），清单与运行方式见 `tss/EXPERIMENT_MANIFEST.md`，收口时逐个确认 exit 0。

## 单测运行注意

- 优先模块形式：`python -m nexus_v1.tests.test_<name>`（repo 根在 path 上）
- 直接跑文件仅对 `sys.path.insert(0,'.')` 或 `__file__` 相对路径的脚本有效；约 8 个旧脚本硬编码 `d:\cell-cc`（陈旧盘符），只能用 `-m` 形式或修正路径
- 批处理入口：根目录 `run_all_tests_capture.py`（4 个入口 + ~30 个 test 模块，输出存 `cell-cell/test_runs/`）
- 无 build 步骤、无 linter。`dt=0.001`（1ms）是仿真步长约定，但部分调用点传 `dt=1.0` —— 看具体测试，别假设

## 标准"回归状态"输出格式（写入报告/commit message）

```
回归状态：test_regression 21/21 PASS；contracts 13/15（失败集合 ⊆ 父提交失败集合，C2/C3 ⊆ DEG-004）；
TSS fast 43 passed / integration 45 passed / version_pairing PASS；非 pytest 实验脚本 N/N exit 0
```

报告中的"复现入口"小节 = 上述实际执行过的命令原样贴成代码块（带 `PYTHONIOENCODING` 前缀）。

## 验收纪律

- 参数改动后必须重跑熵审计：signal depth 不得回退、`|V|<100`、能量 `>0`、无 NaN
- 回归/契约新增失败 → 登记 `cell-cell/docs/degradation_registry.md`（DEG-XXX），修复登记 `fix_registry.md`（FIX-XXX），互相交叉引用
- ⚠️ Registry fork 未解决：`nexus_v1/docs/degradation_registry.md`（16 条）与 `cell-cell/docs/degradation_registry.md`（21 条）DEG-015 编号冲突，引用 DEG-015~019 必须注明出自哪个文件；新条目从 DEG-024 起
