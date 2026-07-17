"""T-P2A0-1~7：P2-A0 入口契约验收（批判二十八，2026-07-18）。

方案依据：`基础生成元执行总纲_V5_2026-07-17.md`"P2-A0"小节。世界物理资格
审查（审查点1）通过后，P2-A有两个入口契约必须先闭合，不是新阶段，是P2-A
内部第一个子步骤：①轨迹身份核对（`JointThermalTrajectory`/
`record_trajectory_step()`）——轨迹已开始承担发生元标定证据，触发条件
已满足；②皮肤支撑地址接通`StructuralAddress`——P2-A自身定义要求
`α(skin patch)↔α(ξ_i^occ)`稳定地址映射，此前皮肤从未接入地址系统，与
P2-A定义直接冲突。
"""

from __future__ import annotations

import pytest

from nexus_v1.components.dynamic_thermal_field import ThermalCell, ThermalLink, ThermalFieldGraph
from nexus_v1.components.semiconductor import Capacitor
from nexus_v1.components.skin_thermal_contact import SkinThermalState, register_skin_patch
from nexus_v1.components.thermal_source_coupling import DynamicHeatSource, ThermalFieldLocator
from nexus_v1.components.structural_address import (
    AddressRegistry, DOMAIN_WORLD_CELL, DOMAIN_SKIN_PATCH,
)
from nexus_v1.components.joint_thermal_step_plan import (
    JointThermalRuntime, prepare_joint_thermal_step, apply_joint_thermal_step,
    JointThermalTrajectory, record_trajectory_step, JointThermalStepError,
)


def _build_rig():
    cells = [ThermalCell(node_id=i, position=(float(i), 0, 0),
                          capacitor=Capacitor(capacitance=1.0)) for i in range(2)]
    graph = ThermalFieldGraph(cells=cells, links=[ThermalLink(i=0, j=1, kappa=0.01)],
                               r_leak_ambient=None)
    source = DynamicHeatSource(position=(0.0, 0, 0), energy_remaining=1000.0,
                                power=0.0, efficiency=1.0)
    locator = ThermalFieldLocator(k=1)
    reg = AddressRegistry()
    reg.register_physical(DOMAIN_WORLD_CELL, 0)
    reg.register_physical(DOMAIN_WORLD_CELL, 1)
    runtime = JointThermalRuntime(world_graph=graph, registry=reg)
    return runtime, graph, source, locator, reg


# ══════════════════════════════════════════════════════════════════════
# ① 轨迹身份核对
# ══════════════════════════════════════════════════════════════════════

def test_p2a0_1_record_rejects_unapplied_plan():
    """T-P2A0-1: 只`prepare()`未`apply()`的计划不能被记录进轨迹（伪造回执
    也不行——`is_applied()`必须为真）。
    """
    runtime, graph, source, locator, _reg = _build_rig()
    trajectory = JointThermalTrajectory()
    plan = prepare_joint_thermal_step(runtime, [], {}, [], source, locator, dt=0.5)

    class _FakeReceipt:
        plan_id = plan.plan_id

    with pytest.raises(JointThermalStepError, match="未在本runtime上确认提交过"):
        record_trajectory_step(trajectory, 0, runtime, {}, plan, _FakeReceipt())
    assert len(trajectory) == 0


def test_p2a0_2_record_rejects_mismatched_receipt():
    """T-P2A0-2: `receipt.plan_id`与`plan.plan_id`不一致（用另一步的回执
    冒充这一步）应拒绝。
    """
    runtime, graph, source, locator, _reg = _build_rig()
    trajectory = JointThermalTrajectory()
    plan_a = prepare_joint_thermal_step(runtime, [], {}, [], source, locator, dt=0.5)
    receipt_a = apply_joint_thermal_step(runtime, plan_a, {}, source)
    plan_b = prepare_joint_thermal_step(runtime, [], {}, [], source, locator, dt=0.5)
    receipt_b = apply_joint_thermal_step(runtime, plan_b, {}, source)

    with pytest.raises(JointThermalStepError, match="回执与计划不是同一步"):
        record_trajectory_step(trajectory, 0, runtime, {}, plan_a, receipt_b)
    assert len(trajectory) == 0


def test_p2a0_3_trajectory_rejects_out_of_order_step_index():
    """T-P2A0-3: 轨迹必须从0开始严格递增，不允许跳步/乱序/重复写入。"""
    runtime, graph, source, locator, _reg = _build_rig()
    trajectory = JointThermalTrajectory()
    plan_0 = prepare_joint_thermal_step(runtime, [], {}, [], source, locator, dt=0.5)
    receipt_0 = apply_joint_thermal_step(runtime, plan_0, {}, source)
    plan_1 = prepare_joint_thermal_step(runtime, [], {}, [], source, locator, dt=0.5)
    receipt_1 = apply_joint_thermal_step(runtime, plan_1, {}, source)

    # 跳步（应该是0，直接给2）。
    with pytest.raises(JointThermalStepError, match="严格递增"):
        record_trajectory_step(trajectory, 2, runtime, {}, plan_1, receipt_1)
    assert len(trajectory) == 0

    # 正确顺序：先0再1。
    record_trajectory_step(trajectory, 0, runtime, {}, plan_0, receipt_0)
    assert len(trajectory) == 1
    # 重复写入0（应该是1）。
    with pytest.raises(JointThermalStepError, match="严格递增"):
        record_trajectory_step(trajectory, 0, runtime, {}, plan_1, receipt_1)
    assert len(trajectory) == 1
    # 正确的下一步。
    record_trajectory_step(trajectory, 1, runtime, {}, plan_1, receipt_1)
    assert len(trajectory) == 2


def test_p2a0_4_valid_sequential_recording_carries_provenance():
    """T-P2A0-4: 正常按序记录时，每条轨迹记录携带`runtime_uid`/`plan_id`
    可供事后审计（不只是写入时检查一次）。
    """
    runtime, graph, source, locator, _reg = _build_rig()
    trajectory = JointThermalTrajectory()
    for i in range(3):
        plan = prepare_joint_thermal_step(runtime, [], {}, [], source, locator, dt=0.5)
        receipt = apply_joint_thermal_step(runtime, plan, {}, source)
        record_trajectory_step(trajectory, i, runtime, {}, plan, receipt)

    assert len(trajectory) == 3
    for i in range(3):
        step = trajectory[i]
        assert step.runtime_uid == runtime.runtime_uid
        assert step.step_index == i


# ══════════════════════════════════════════════════════════════════════
# ② 皮肤支撑地址接通
# ══════════════════════════════════════════════════════════════════════

def test_p2a0_5_skin_patch_gets_stable_address():
    """T-P2A0-5: `register_skin_patch()`给皮肤挂载稳定`StructuralAddress`
    （domain=`DOMAIN_SKIN_PATCH`），默认未注册时`address`为`None`（向后
    兼容既有P0/P1-0/P1-C测试）。
    """
    skin = SkinThermalState(patch_id=7, capacitor=Capacitor(capacitance=1.0))
    assert skin.address is None  # 默认未注册，不强制

    reg = AddressRegistry()
    addr = register_skin_patch(reg, skin)
    assert skin.address is addr
    assert addr.domain == DOMAIN_SKIN_PATCH
    assert addr.uid == "skin.patch:7"


def test_p2a0_6_skin_patch_address_idempotent_and_distinct():
    """T-P2A0-6: 同一`patch_id`重复注册返回同一地址（幂等）；不同
    `patch_id`得到不同的稳定地址（同P1-A对世界节点的既定行为）。
    """
    reg = AddressRegistry()
    skin_a = SkinThermalState(patch_id=1, capacitor=Capacitor(capacitance=1.0))
    skin_b = SkinThermalState(patch_id=2, capacitor=Capacitor(capacitance=1.0))

    addr_a1 = register_skin_patch(reg, skin_a)
    addr_a2 = register_skin_patch(reg, skin_a)  # 重复注册同一皮肤
    addr_b = register_skin_patch(reg, skin_b)

    assert addr_a1.uid == addr_a2.uid
    assert addr_a1.uid != addr_b.uid


def test_p2a0_7_skin_and_world_addresses_coexist_in_same_registry():
    """T-P2A0-7: 皮肤地址与世界节点地址可以在同一个`AddressRegistry`里
    共存（不同domain，互不冲突）——为P2-A的
    `α(skin patch)↔α(ξ_i^occ)`映射提供物理支撑基础。
    """
    reg = AddressRegistry()
    world_addr = reg.register_physical(DOMAIN_WORLD_CELL, 0)
    skin = SkinThermalState(patch_id=0, capacitor=Capacitor(capacitance=1.0))
    skin_addr = register_skin_patch(reg, skin)

    # 相同local_key(0)，不同domain，uid应不同（domain是uid组成部分）。
    assert world_addr.uid != skin_addr.uid
    assert world_addr.domain == DOMAIN_WORLD_CELL
    assert skin_addr.domain == DOMAIN_SKIN_PATCH


if __name__ == "__main__":
    test_p2a0_1_record_rejects_unapplied_plan()
    test_p2a0_2_record_rejects_mismatched_receipt()
    test_p2a0_3_trajectory_rejects_out_of_order_step_index()
    test_p2a0_4_valid_sequential_recording_carries_provenance()
    test_p2a0_5_skin_patch_gets_stable_address()
    test_p2a0_6_skin_patch_address_idempotent_and_distinct()
    test_p2a0_7_skin_and_world_addresses_coexist_in_same_registry()
    print("T-P2A0-1~7 ALL PASS")
