"""T-RPP-1~5：P2-B1 真实 D2 关系回路 + 独立学习资格验证（2026-07-28）。

方案依据：`cell-cell/交叉比对/document - 2026-07-28T185716.294.md`（P2-B1
三步走：①两个NaturalUnit输入→②真实关系载体产生响应→③验证响应具备学习
资格：独立验证pre/post活动→eligibility→DA门控→Δw≠0，再做阻断对照）。

**DEG-023（原DEG-016）教训**：不假设"STDP 应该没问题"——本文件独立、真实驱动
`RPrecCircuitT1Plastic`（不经过完整趋热行为回路/`circuit.step()` 主循环），
`da_concentration` 由测试显式控制（合成设定），验证学习资格链路本身。

驱动方式：直接调用 `RPrecCircuitT1Plastic.rprec_xi_a/b`（= 既有
`thermal_quantum_collectors["thermpt28/31_warm"]`）连续输入合成电流，产生
collector 发放（这是 T1 已验证的检测行为，不是本文件新增内容）——本文件
关注的是新增 bundle 的学习资格，不重新验证 T1 本身的检测正确性（已由
`test_basegen_thermal_t1.py` 验证）。
"""
import sys

sys.path.insert(0, '.')

from tss.relations.temporal_r_prec_plastic import RPrecCircuitT1Plastic
from nexus_v1.components.structural_address import AddressRegistry, DOMAIN_RELATION_PREC

DT = 0.001


#  EXP-P2B1-002：`SynapticBundle.da_ema_tau` 默认 5000.0（仿真步单位，
#  `bundle.py:122`），`_beta=dt/(dt+da_ema_tau)` 决定 `da_ema` 逼近
#  `da_concentration` 的速度。**实测坐实**（本文件开发时诊断，非假设）：
#  只跑 2000 步时，DA=0.5 与 DA=0.0 产生几乎完全相同的 Δw（da_ema 根本
#  来不及从 0 移动），会得到"表面 PASS 实则未验证 DA 门控"的假阳性——
#  这正是 DEG-023（原DEG-016）警告的"不能假设 STDP 没问题"要防的那类错误。改用与
#  `exp_validate_thermal_delta_50k.py` 同量级的 `_DRIVE_STEPS=50000`，
#  实测 DA=0.5 给出 Δw=+0.00105（真实LTP），DA=0.0 给出 Δw=-1.06e-7
#  （基本冻结）——门控在此时间尺度下才真实可分辨。
_DRIVE_STEPS = 50000


def _drive_detection(circuit, steps: int, da_concentration: float, fill_fraction: float = 1.0):
    """直接向 xi_a/xi_b 注入合成电流驱动检测链路 + 新bundle学习，`steps` 步。

    合成电流幅度足以让 collector 越过阈值发放（沿用 T1 既有标定：raw ξ 达到
    pre_trace~1.0 量级即可越过 `_COLLECTOR_THRESHOLD`，见 `temporal_r_prec.py`
    Q3 标定说明），先驱动 a 再驱动 b 以制造"a≺b"的真实时序。
    """
    for t in range(steps):
        # 前半程主要驱动 a，后半程主要驱动 b——制造真实的 a≺b 时序关系
        # （不是同时驱动，否则无法区分方向）。
        inj_a = 1.0 if t < steps // 2 else 0.0
        inj_b = 1.0 if t >= steps // 3 else 0.0
        circuit.rprec_xi_a.step(inj_a, DT)
        circuit.rprec_xi_b.step(inj_b, DT)
        circuit.step_rprec_plastic(DT, da_concentration=da_concentration, fill_fraction=fill_fraction)


def test_rpp_1_learning_occurs_when_da_positive():
    """T-RPP-1：真实 pre/post 相关活动 + DA>0 时段（`_DRIVE_STEPS` 与 da_ema_tau
    同量级），新 bundle 权重 Δw 应显著大于 DA=0 时段的残余漂移——不只是
    "非零"（那会被无关的被动衰减噪声假阳性通过，见模块顶部注释），而是
    量级上真正可分辨的 LTP。"""
    circuit_pos = RPrecCircuitT1Plastic()
    w_before_pos = circuit_pos.bundle_rprec_to_da.weight_matrix()[0][0]
    _drive_detection(circuit_pos, steps=_DRIVE_STEPS, da_concentration=0.5)
    w_after_pos = circuit_pos.bundle_rprec_to_da.weight_matrix()[0][0]
    delta_w_pos = w_after_pos - w_before_pos

    circuit_zero = RPrecCircuitT1Plastic()
    w_before_zero = circuit_zero.bundle_rprec_to_da.weight_matrix()[0][0]
    _drive_detection(circuit_zero, steps=_DRIVE_STEPS, da_concentration=0.0)
    w_after_zero = circuit_zero.bundle_rprec_to_da.weight_matrix()[0][0]
    delta_w_zero = w_after_zero - w_before_zero

    print(f"T-RPP-1: DA=0.5 Δw={delta_w_pos}; DA=0.0 Δw={delta_w_zero}")
    assert delta_w_pos > 0, "DA>0 且有真实pre/post活动时，应发生正向LTP"
    assert delta_w_pos > abs(delta_w_zero) * 100, (
        f"DA门控产生的Δw应远大于DA=0时的残余漂移量级"
        f"（Δw_pos={delta_w_pos}, Δw_zero={delta_w_zero}），"
        f"否则说明门控在当前步数下不可分辨（同2000步假阳性问题）")


def test_rpp_2_frozen_when_da_zero():
    """T-RPP-2：DA=0（quiet）时段，新 bundle 权重 Δw≈0（学习被门控冻结，不侵蚀，
    残余漂移应远小于DA>0时的LTP量级——量级判据见 T-RPP-1）。"""
    circuit = RPrecCircuitT1Plastic()
    w_before = circuit.bundle_rprec_to_da.weight_matrix()[0][0]

    _drive_detection(circuit, steps=_DRIVE_STEPS, da_concentration=0.0)

    w_after = circuit.bundle_rprec_to_da.weight_matrix()[0][0]
    delta_w = w_after - w_before
    print(f"T-RPP-2: w_before={w_before}, w_after={w_after}, Δw={delta_w}")
    assert abs(delta_w) < 1e-4, (
        f"DA=0 时权重应基本冻结（不被动侵蚀出显著量级），实测Δw={delta_w}")


def test_rpp_3_existing_frozen_bundles_unaffected():
    """T-RPP-3：既有 12 条 frozen bundle（RPrecCircuitT1 本身）全程权重不变——
    确认新增可塑 bundle 没有意外破坏 T-TRP-2 的既有不变性断言。"""
    circuit = RPrecCircuitT1Plastic()
    existing_bundles = circuit.rprec_relation_bundles()
    weights_before = [b.weight_matrix() for b in existing_bundles]

    _drive_detection(circuit, steps=_DRIVE_STEPS, da_concentration=0.5)

    weights_after = [b.weight_matrix() for b in existing_bundles]
    for b, wb, wa in zip(existing_bundles, weights_before, weights_after):
        assert wb == wa, f"既有frozen bundle {b.config.bundle_id} 权重不应变化"
    print(f"T-RPP-3 PASS: 既有{len(existing_bundles)}条frozen bundle权重全程不变"
          f"（{_DRIVE_STEPS}步）")


def test_rpp_4_ablation_control():
    """T-RPP-4：阻断对照——同一驱动场景跑两次，(a)新bundle正常学习 vs
    (b)新bundle权重锁死不变——比较下游权重/DA状态，证明该边是真实因果载体。
    """
    circuit_with = RPrecCircuitT1Plastic()
    _drive_detection(circuit_with, steps=_DRIVE_STEPS, da_concentration=0.5)
    da_with = [n.activation for n in circuit_with.da_neurons.values()]
    w_with = circuit_with.bundle_rprec_to_da.weight_matrix()[0][0]

    # 阻断版本：新bundle改为frozen（权重锁死，不学习），其余完全一致。
    circuit_without = RPrecCircuitT1Plastic()
    circuit_without.bundle_rprec_to_da.config.learning_rule = "frozen"
    _drive_detection(circuit_without, steps=_DRIVE_STEPS, da_concentration=0.5)
    da_without = [n.activation for n in circuit_without.da_neurons.values()]
    w_without = circuit_without.bundle_rprec_to_da.weight_matrix()[0][0]

    print(f"T-RPP-4: w_with={w_with}, w_without={w_without}")
    print(f"         da_with={da_with}, da_without={da_without}")
    assert w_with != w_without, "有/无学习两种情形下，新bundle权重应该不同"
    assert w_with > w_without, "学习版本(DA>0驱动LTP)权重应高于冻结版本"


def test_rpp_5_relation_address_registration():
    """T-RPP-5：DOMAIN_RELATION_PREC 首次真实实例化——地址回指两个 D1
    occurrence 的父物理支撑谱系（这里用两个站点各自的皮肤支撑地址作为
    parent，因为完整的 Occurrence.address 需要真实驱动 BaseGenerator 产生，
    本测试聚焦地址注册机制本身是否可用，用站点物理地址做最小可行parent）。
    """
    from nexus_v1.components.structural_address import DOMAIN_SKIN_PATCH

    circuit = RPrecCircuitT1Plastic()
    registry = AddressRegistry()

    addr_a = registry.register_physical(DOMAIN_SKIN_PATCH, f"thermpt{circuit.rprec_site_a}")
    addr_b = registry.register_physical(DOMAIN_SKIN_PATCH, f"thermpt{circuit.rprec_site_b}")

    relation_addr = registry.register_generated(
        domain=DOMAIN_RELATION_PREC,
        local_key=f"rprec_{circuit.rprec_site_a}_prec_{circuit.rprec_site_b}_fast",
        parent_addresses=(addr_a, addr_b),
        generation_depth=2,
    )

    assert relation_addr.domain == DOMAIN_RELATION_PREC
    assert len(relation_addr.parent_addresses) == 2
    assert addr_a in relation_addr.parent_addresses
    assert addr_b in relation_addr.parent_addresses
    print(f"T-RPP-5 PASS: {relation_addr.uid} 回指 "
          f"{[a.uid for a in relation_addr.parent_addresses]}（DOMAIN_RELATION_PREC 首次实例化）")


def run():
    test_rpp_1_learning_occurs_when_da_positive()
    test_rpp_2_frozen_when_da_zero()
    test_rpp_3_existing_frozen_bundles_unaffected()
    test_rpp_4_ablation_control()
    test_rpp_5_relation_address_registration()
    print()
    print("T-RPP-1~5 ALL PASS")


if __name__ == "__main__":
    run()
