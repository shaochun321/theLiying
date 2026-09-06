"""T-OID-1：P2-B1X1a D1实例身份唯一性验证（2026-07-30）。

方案依据：`cell-cell/交叉比对/document - 2026-07-30T113327.179.md`
（P2-B1X1a：D1实例身份闭合）。

验证：同一 generator 连续产生两个 occurrence 时，`instance_id` 不同
（`InstanceId_17 != InstanceId_18`），对应 `NaturalUnit` 也不能混同；
`OccurrenceIdentityRegistry` 能正确登记并区分两次发生。
"""
import sys

sys.path.insert(0, '.')

from tss.generators.occurrence import OccurrenceClosure, OccurrenceInstanceId
from tss.generators.natural_unit import naturalize
from tss.generators.occurrence_identity import OccurrenceIdentityRegistry
from nexus_v1.components.structural_address import (
    DOMAIN_OCC_THERMAL, DOMAIN_SKIN_PATCH, GeneratedAddress, StructuralAddress,
)

# 复用 exp_P2A1b_3_closure_calibration.py 的标定常量与驱动范式（不新造）。
CALIBRATED_THETA_DOWN = 0.001
CALIBRATED_REARM_MIN_STEPS = 500
DT = 0.001


class _FakeHandle:
    """T-OID-1 只需要 site_index/polarity/trajectory 三个属性（naturalize()
    的 handle 契约），不需要真实 BaseGenerator，避免驱动真实电路增加测试
    时间（同 `naturalize()` 文档"handle 不做类型注解绑定 BaseGenerator"的
    既定设计——鸭子类型足够）。"""
    site_index = 28
    polarity = "warm"
    trajectory = None


def _make_closure() -> OccurrenceClosure:
    parent = StructuralAddress(domain=DOMAIN_SKIN_PATCH, uid="skin.patch:oid_test")
    address = GeneratedAddress(
        domain=DOMAIN_OCC_THERMAL, uid="occ.thermal:oid_test",
        parent_addresses=(parent,), generation_depth=1,
    )
    return OccurrenceClosure(
        address=address, theta_down=CALIBRATED_THETA_DOWN,
        rearm_min_steps=CALIBRATED_REARM_MIN_STEPS,
    )


def _drive_one_occurrence(closure: OccurrenceClosure, t: int):
    """驱动一次完整触发→跌破→rearm→emit 周期（同
    exp_P2A1b_3_closure_calibration.py 的驱动范式），返回 (occurrence, t)。"""
    ev = closure.update(0.02, t, phys_support=True)
    t += 1
    assert ev is None and closure.is_active
    ev = closure.update(0.0, t, phys_support=True)
    t += 1
    for _ in range(CALIBRATED_REARM_MIN_STEPS):
        ev = closure.update(0.0, t, phys_support=True)
        t += 1
        if ev is not None:
            return ev, t
    raise AssertionError("未能在预算内产生 occurrence")


def test_oid_1_instance_id_unique_across_epochs():
    """T-OID-1：同一 generator 连续产生两次 occurrence，instance_id 不同；
    对应 NaturalUnit 的 source_occurrence_instance_id 也不同。"""
    closure = _make_closure()
    t = 0

    # 第一次发生
    occ_1, t = _drive_one_occurrence(closure, t)
    instance_id_1 = occ_1.instance_id
    print(f"T-OID-1: occ_1.epoch_id={occ_1.epoch_id}, instance_id_1={instance_id_1}")

    # 撤去支撑一步（模拟外周活动退出，允许新 epoch 开启）+ 重整后再来一次
    ev = closure.update(0.0, t, phys_support=False)
    t += 1
    occ_2, t = _drive_one_occurrence(closure, t)
    instance_id_2 = occ_2.instance_id
    print(f"T-OID-1: occ_2.epoch_id={occ_2.epoch_id}, instance_id_2={instance_id_2}")

    # 核心断言：两次发生的 instance_id 不同
    assert instance_id_1 != instance_id_2, (
        f"同一generator连续两次发生的instance_id应不同，"
        f"实际 instance_id_1={instance_id_1}, instance_id_2={instance_id_2}")
    # 但 generator_address 应相同（同一个 closure/生成元）
    assert instance_id_1.generator_address == instance_id_2.generator_address, (
        "同一closure产生的两次occurrence，generator_address应相同")
    assert instance_id_1.epoch_id != instance_id_2.epoch_id, (
        "两次发生的epoch_id应不同")

    # NaturalUnit 层也不能混同
    handle = _FakeHandle()
    nu_1 = naturalize(handle, occ_1, DT)
    nu_2 = naturalize(handle, occ_2, DT)
    assert nu_1.source_occurrence_instance_id == instance_id_1
    assert nu_2.source_occurrence_instance_id == instance_id_2
    assert nu_1.source_occurrence_instance_id != nu_2.source_occurrence_instance_id, (
        "两个NaturalUnit的source_occurrence_instance_id不应相同")

    print("✓ T-OID-1 PASS: instance_id在epoch间唯一，NaturalUnit不混同")


def test_oid_2_registry_lookup_roundtrip():
    """T-OID-2（补充）：OccurrenceIdentityRegistry 能正确登记并按
    instance_id 反查到对应的 Occurrence/NaturalUnit，不同实例互不覆盖。"""
    closure = _make_closure()
    t = 0
    occ_1, t = _drive_one_occurrence(closure, t)
    closure.update(0.0, t, phys_support=False)
    t += 1
    occ_2, t = _drive_one_occurrence(closure, t)

    handle = _FakeHandle()
    nu_1 = naturalize(handle, occ_1, DT)
    nu_2 = naturalize(handle, occ_2, DT)

    registry = OccurrenceIdentityRegistry()
    registry.register_occurrence(occ_1)
    registry.register_occurrence(occ_2)
    registry.register_natural_unit(nu_1)
    registry.register_natural_unit(nu_2)

    assert registry.lookup_occurrence(occ_1.instance_id) is occ_1
    assert registry.lookup_occurrence(occ_2.instance_id) is occ_2
    assert registry.lookup_natural_unit(occ_1.instance_id) is nu_1
    assert registry.lookup_natural_unit(occ_2.instance_id) is nu_2
    assert registry.is_resolved(occ_1.instance_id)
    assert registry.is_resolved(occ_2.instance_id)

    # 未登记的instance_id应查不到
    from tss.generators.occurrence import OccurrenceInstanceId
    fake_id = OccurrenceInstanceId(generator_address=occ_1.address, epoch_id=9999)
    assert registry.lookup_occurrence(fake_id) is None
    assert not registry.is_resolved(fake_id)

    print("✓ T-OID-2 PASS: registry往返查找正确，未登记身份查不到")


def test_oid_3_natural_unit_rejects_untraceable_registration():
    """T-OID-3（补充）：手工构造且未传source_occurrence_instance_id的
    NaturalUnit不允许登记进registry（防止无法追溯来源的实例混入查找表）。"""
    from tss.generators.natural_unit import NaturalUnit

    closure = _make_closure()
    occ, _ = _drive_one_occurrence(closure, 0)

    # 手工构造，不传 source_occurrence_instance_id（默认None）
    bare_nu = NaturalUnit(
        address=occ.address, port=(28, "warm"),
        window=(occ.t_up, occ.t_rearm), count_measure=1,
        duration_raw_steps=occ.t_rearm - occ.t_up,
        duration_seconds=(occ.t_rearm - occ.t_up) * DT,
    )
    assert bare_nu.source_occurrence_instance_id is None

    registry = OccurrenceIdentityRegistry()
    try:
        registry.register_natural_unit(bare_nu)
        assert False, "应拒绝登记source_occurrence_instance_id=None的NaturalUnit"
    except ValueError as e:
        print(f"✓ T-OID-3 PASS: 正确拒绝无法追溯来源的NaturalUnit ({e})")


def run():
    test_oid_1_instance_id_unique_across_epochs()
    test_oid_2_registry_lookup_roundtrip()
    test_oid_3_natural_unit_rejects_untraceable_registration()
    print()
    print("T-OID-1~3 ALL PASS")


if __name__ == "__main__":
    run()
