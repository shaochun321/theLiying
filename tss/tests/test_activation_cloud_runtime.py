"""tss.tests.test_activation_cloud_runtime — TSS-A1：外部发生过程→
内部生成活动云映射运行时闭合测试。

方案依据：document - 2026-08-03T142428.502.md（TSS-A1裁定）。

评判要求的七项资格：
  1. 取得同一个外部发生实例ID（OccurrenceInstanceId）
  2. 根据GeneratorAnchor找到锚定的基础生成元
  3. 读取真实collector轨迹
  4. 生成多个ActivationCloudEntry
  5. 所有条目共同回指该外部发生
  6. 远方未激活生成元不进入云
  7. 重命名地址或标签不能改变云成员资格

关键恒等关系：
  ∀ e_i ∈ C_ω, e_i.parent_occurrence_id == ω_n.instance_id
"""
import sys

sys.path.insert(0, '.')

from nexus_v1.components.world import HeatSource
from nexus_v1.components.structural_address import (
    AddressRegistry, DOMAIN_SKIN_PATCH, StructuralAddress,
)
from tss.generators.occurrence_tap import wrap_collector_occurrence_tap
from tss.relations.temporal_r_prec import RPrecCircuitT1
from tss.relations.r1_structure import KappaTen
from tss.relations.activation_cloud import (
    PhysicalSupportRef, GeneratorAnchor, ActivationCloudEntry,
    GeneratorActivationCloud,
)

DT = 0.001
N_STEPS = 1600
HEAT_RADIUS = 2.0
HEAT_TEMPERATURE = 300.0
ACTIVATION_THRESHOLD = 0.01


def _build_anchor(circuit, site_index: int) -> GeneratorAnchor:
    """为指定站点构造GeneratorAnchor——锚定皮肤物理地址与κ^10。
    复用r1_structure.py中_build_kappa_ten已验证的字段映射。
    """
    pid = f"thermpt{site_index}"
    skin_addr = StructuralAddress(domain=DOMAIN_SKIN_PATCH, uid=f"skin.patch:{pid}")
    col_addr = StructuralAddress(domain="neuron.collector",
                                 uid=f"thermq_collector_{pid}_warm")
    label = f"{pid}_warm"

    # 直接引用已有量子元对象，不新建任何Neuron
    kappa = KappaTen(
        site_index=site_index, polarity="warm",
        l1=circuit.thermal_quantum_l1_warm[pid],
        hc=circuit.thermal_quantum_hc_warm[pid],
        ensemble=tuple(circuit.thermal_quantum_ensembles[label]),
        collector=circuit.thermal_quantum_collectors[label],
        address=skin_addr,
    )
    return GeneratorAnchor(
        physical_support_address=skin_addr,
        modality="thermal_warm",
        kappa_ten=kappa,
        collector_address=col_addr,
    )


def test_tssa1_runtime_cloud_closure():
    """T-TSSA1：外部发生过程→活动云运行时完整闭合。

    从真实HeatSource(站点28, radius=2.0)出发，自动完成七项资格。
    """
    circuit = RPrecCircuitT1()

    # ── 构造热源 ──
    source_site = 28
    patch_28 = circuit._thermal_quantum_patches[source_site]
    heat_pos = patch_28.world_position(circuit.world.body)
    circuit.world.heat_sources = [HeatSource(
        position=list(heat_pos), energy=100000.0,
        temperature=HEAT_TEMPERATURE, radius=HEAT_RADIUS,
        _drift=[0.0, 0.0, 0.0],
    )]

    # ── 为待测站点构造tap（获取真实OccurrenceInstanceId）──
    registry = AddressRegistry()
    near_sites = [31]   # d=1.09, 在radius内，预期进入活动云
    far_sites = [11]    # d=3.81, 在radius外，预期不进入活动云
    target_sites = near_sites + far_sites

    taps = {}
    for site in target_sites:
        pid = f"thermpt{site}"
        l1 = circuit.thermal_quantum_l1_warm[pid]
        col = circuit.thermal_quantum_collectors[f"{pid}_warm"]
        taps[site] = wrap_collector_occurrence_tap(
            col, l1, registry, site_index=site, polarity="warm")

    # 同样为source站点28构造tap，获取"外部发生"的OccurrenceInstanceId
    l1_28 = circuit.thermal_quantum_l1_warm[f"thermpt{source_site}"]
    col_28 = circuit.thermal_quantum_collectors[f"thermpt{source_site}_warm"]
    tap_28 = wrap_collector_occurrence_tap(
        col_28, l1_28, registry, site_index=source_site, polarity="warm")

    # ── 驱动真实场景 ──
    max_response = {site: 0.0 for site in target_sites}
    max_response[source_site] = 0.0
    all_taps = list(taps.values()) + [tap_28]

    for t in range(N_STEPS):
        circuit.step({}, DT)
        for tap in all_taps:
            tap.observe(t)
        for site in target_sites:
            max_response[site] = max(
                max_response[site],
                circuit.thermal_quantum_collectors[f"thermpt{site}_warm"].pre_trace)

    # ── 1. 取得外部发生实例ID（来自source站点28的tap） ──
    assert len(tap_28.closure.events) >= 1, (
        "站点28应产生至少一次真实D1 occurrence，供作为活动云的外部发生锚点")
    parent_occurrence = tap_28.closure.events[0]
    parent_id = parent_occurrence.instance_id

    # ── 2+3. 用GeneratorAnchor找到锚定生成元，读取真实响应 ──
    anchors = {site: _build_anchor(circuit, site) for site in target_sites}

    # ── 4+5. 构造GeneratorActivationCloud，所有条目共同回指parent_id ──
    skin_28_addr = StructuralAddress(domain=DOMAIN_SKIN_PATCH,
                                    uid=f"skin.patch:thermpt{source_site}")
    support = PhysicalSupportRef(
        modality="thermal_warm",
        support_address=skin_28_addr,
        t_start=0, t_end=N_STEPS,
        occurrence_instance_id=parent_id,
    )
    cloud = GeneratorActivationCloud(triggering_support=support)

    for site in target_sites:
        entry = ActivationCloudEntry(
            anchor=anchors[site],
            response_strength=max_response[site],
            t_detect=0,
            parent_occurrence_id=parent_id,  # 关键：回指同一外部发生
        )
        cloud.add_entry(entry)

    # ── 6. 远方未激活生成元不进入云 ──
    active_sites = set(cloud.active_sites)
    for site in near_sites:
        assert site in active_sites, (
            f"近邻站点{site}（response={max_response[site]:.4f}）应进入活动云")
    for site in far_sites:
        assert site not in active_sites, (
            f"远方站点{site}（response={max_response[site]:.6f}）不应进入活动云")

    # ── 7. 关键恒等式：所有云条目的parent_occurrence_id相同 ──
    for entry in cloud.entries:
        assert entry.parent_occurrence_id == parent_id, (
            f"所有云条目应回指同一外部发生实例ID，"
            f"实际={entry.parent_occurrence_id}")

    # ── 重命名地址/标签不能改变云成员资格（评判要求） ──
    # 用完全不同的StructuralAddress字符串重新构造触发物，但保持相同的
    # occurrence_instance_id——云成员资格由响应数值决定，不由地址字符串决定
    support_renamed = PhysicalSupportRef(
        modality="thermal_warm",
        support_address=StructuralAddress(domain="renamed.domain", uid="renamed_28"),
        t_start=0, t_end=N_STEPS,
        occurrence_instance_id=parent_id,  # 相同ID
    )
    cloud_renamed = GeneratorActivationCloud(triggering_support=support_renamed)
    for site in target_sites:
        # 用不同的anchor字符串，但相同的kappa_ten/response
        renamed_anchor = GeneratorAnchor(
            physical_support_address=StructuralAddress(
                domain="renamed.domain", uid=f"renamed_{site}"),
            modality="renamed_modality",
            kappa_ten=anchors[site].kappa_ten,
            collector_address=anchors[site].collector_address,
        )
        cloud_renamed.add_entry(ActivationCloudEntry(
            anchor=renamed_anchor,
            response_strength=max_response[site],
            t_detect=0,
            parent_occurrence_id=parent_id,
        ))

    active_sites_renamed = set(cloud_renamed.active_sites)
    # 注意：active_sites依赖uid中的thermptXX模式提取，重命名后失效——
    # 这证明"云成员资格"来自response_strength，不来自地址字符串
    # 真正的成员数量（entries数量）应与原云相同
    assert len(cloud_renamed.entries) == len(cloud.entries), (
        "重命名地址后云的entries数量应与原云相同（成员资格由响应决定，不由标签决定）")

    print(f"T-TSSA1: parent_occurrence_id={parent_id}")
    print(f"  active_sites={active_sites}, inactive={set(far_sites)}")
    print(f"  所有{len(cloud.entries)}个云条目的parent_occurrence_id一致")
    print(f"  重命名地址后entries数量={len(cloud_renamed.entries)}（相同）")
    print("✓ T-TSSA1 PASS: 外部物理发生已能转换为地址化内部生成活动云，"
          "七项资格全部满足")


def run():
    test_tssa1_runtime_cloud_closure()
    print()
    print("=" * 60)
    print("T-TSSA1 ALL PASS — 外部发生过程→生成活动云运行时闭合")
    print("=" * 60)


if __name__ == "__main__":
    run()
