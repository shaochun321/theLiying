"""tss.tests conftest — pytest markers 分层（2026-09-06，外部实测反馈清单 §4/§5）。

背景：外部评判指出 `pytest tss/tests` 收集的 200+ 项中混有大量分钟级真实
母体电路实验，无法用于快速回归判断。按反馈建议引入 markers 分层；**不搬
目录**（目录拆分会打断全部 `python -m tss.tests.*` 入口约定与 git 历史，
markers 语义等价）。

用法：
    pytest tss/tests -m "not longrun"      # 快速回归层（分钟内）
    pytest tss/tests -m longrun            # 完整物理资格实验层
    pytest tss/tests -m fast               # 仅纯组件单测

分类依据：参考机实测时长（tss/EXPERIMENT_MANIFEST.md 记录），可修订：
    fast        纯组件/契约测试，无真实电路驱动，秒级
    integration 驱动真实电路但短程（≲60s）
    longrun     完整母体电路多驱动/万步级训练（分钟级，含全部资格套件）

注意：exp_*/_diag_*/_probe_* 脚本**不被 pytest 收集**（非 test_ 前缀），
它们的清单与入口见 tss/EXPERIMENT_MANIFEST.md——"pytest 全绿"≠"全部
实验体系通过"（反馈 §5 的边界声明）。
"""

# 按模块名显式分层（不含 test_ 前缀与 .py 后缀）
_FAST = {
    "test_event_support_binding", "test_generator_contract",
    "test_generator_lambda", "test_generator_sigma", "test_natural_unit",
    "test_occurrence_identity", "test_occurrence_tap",
    "test_selection_contract", "test_selection_pool",
    "test_selection_pool_seed", "test_skin_transduction",
    "test_e0_kernel_ledger",
}
_INTEGRATION = {
    "test_basegen_thermal_t0", "test_basegen_thermal_t1",
    "test_basegen_thermal_t3_ratio", "test_r1_structure", "test_r2_fork",
    "test_tss2a_scale_audit", "test_e0_event_type_audit",
    "test_deg021_dual_drive_interlock",
}
# 其余全部视为 longrun（完整母体电路/万步级训练/多种子驱动）


def pytest_configure(config):
    config.addinivalue_line("markers", "fast: 纯组件单测，秒级")
    config.addinivalue_line("markers", "integration: 短程真实电路测试（≲60s）")
    config.addinivalue_line(
        "markers", "longrun: 分钟级完整物理资格实验（真实母体电路/万步训练）")


def pytest_collection_modifyitems(config, items):
    import pytest
    for item in items:
        mod = item.module.__name__.rsplit(".", 1)[-1]
        if mod in _FAST:
            item.add_marker(pytest.mark.fast)
        elif mod in _INTEGRATION:
            item.add_marker(pytest.mark.integration)
        else:
            item.add_marker(pytest.mark.longrun)
