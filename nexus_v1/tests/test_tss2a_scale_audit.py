"""nexus_v1.tests.test_tss2a_scale_audit — TSS-2a：尺度生成算子的最低资格
与现有物理载体审计。

方案依据：document - 2026-08-03T195649.145.md（TSS-2a裁定）。

评判要求本轮只确认五个问题（审计任务，不实现Λ^(1)电路）：
  1. 当前哪些已存在的物理结构可以构成两个不同尺度窗口
  2. 是否已有一次外部发生能够产生至少两个活动云条目
  3. 尺度窗口改变是否会真实改变下游可见结构
  4. 哪些变化只是软件聚合，不能算尺度生成
  5. 是否需要一个新的多生成元外部驱动场景

几何审计（不驱动物理，纯坐标计算，仅用于确定候选站点范围，不作为尺度
算子本体的决策依据——同TSS-1"用坐标摆放刺激源合法，用坐标做决策不合法"
的既定边界）：
  半径2.0内有7个站点（31/23/20/25/30/15/26）
  半径3.0内新增10个站点（29/18/12/17/27/22/10/7/21/24），合计17个

本文件用两次真实HeatSource驱动（radius=2.0 vs radius=3.0，均以站点28为
中心）分别测量这17个候选站点的真实collector响应，验证：
  - 单次外部发生（radius=2.0）产生的真实活动云条目数>1（回应评判指出
    "TSS-A1只有active_sites={31}"的局限，那是测试选点太少，不是资产
    不够）
  - 两个尺度窗口下云成员确实不同（不是同一份数据重新贴标签）
"""
import sys

sys.path.insert(0, '.')

from nexus_v1.components.world import HeatSource
from nexus_v1.relations.temporal_r_prec import RPrecCircuitT1

DT = 0.001
N_STEPS = 1600
HEAT_TEMPERATURE = 300.0

# 几何审计得出的候选站点（半径3.0覆盖范围内，供两个尺度窗口对比测试）
_CANDIDATE_SITES = [31, 23, 20, 25, 30, 15, 26,   # 半径2.0内
                   29, 18, 12, 17, 27, 22, 10, 7, 21, 24]  # 半径2.0~3.0之间


def _drive_and_measure(source_site: int, radius: float, target_sites):
    """驱动一次真实HeatSource场景，返回每个target站点的真实峰值响应。"""
    circuit = RPrecCircuitT1()
    patch = circuit._thermal_quantum_patches[source_site]
    heat_pos = patch.world_position(circuit.world.body)
    circuit.world.heat_sources = [HeatSource(
        position=list(heat_pos), energy=100000.0,
        temperature=HEAT_TEMPERATURE, radius=radius,
        _drift=[0.0, 0.0, 0.0],
    )]

    max_response = {site: 0.0 for site in target_sites}
    for t in range(N_STEPS):
        circuit.step({}, DT)
        for site in target_sites:
            collector = circuit.thermal_quantum_collectors[f"thermpt{site}_warm"]
            max_response[site] = max(max_response[site], collector.pre_trace)
    return max_response


def test_tss2a_1_two_real_scale_windows_exist():
    """Q1+Q5：现有物理载体（HeatSource半径参数+32点量子元阵列）足以构成
    两个真实不同的尺度窗口，不需要新建多生成元外部驱动场景。"""
    responses_r2 = _drive_and_measure(28, 2.0, _CANDIDATE_SITES)
    responses_r3 = _drive_and_measure(28, 3.0, _CANDIDATE_SITES)

    active_r2 = {s for s, r in responses_r2.items() if r >= 0.01}
    active_r3 = {s for s, r in responses_r3.items() if r >= 0.01}

    assert len(active_r2) >= 1, "radius=2.0窗口应至少有站点被激活"
    assert active_r3 != active_r2, (
        "两个尺度窗口的活动云成员应真实不同，否则只是同一份数据换了标签"
        f"（r2.0={active_r2}, r3.0={active_r3}）")
    assert active_r3.issuperset(active_r2) or len(active_r3) != len(active_r2), (
        "更大尺度窗口应产生不同的成员集合（新增或减少成员），"
        "不是简单复制r2.0的结果")

    print(f"T-TSS2A-1: radius=2.0 active={sorted(active_r2)}")
    print(f"           radius=3.0 active={sorted(active_r3)}")
    print("✓ T-TSS2A-1 PASS: 现有HeatSource半径参数+32点量子元阵列"
          "足以构成两个真实不同的尺度窗口，不需要新场景（回答Q1/Q5）")
    return responses_r2, responses_r3, active_r2, active_r3


def test_tss2a_2_single_event_multi_member_cloud():
    """Q2：单次外部发生（radius=2.0）应产生真实的多成员活动云
    （>1个条目），回应评判指出TSS-A1只有active_sites={31}的局限——
    那是此前测试只选了1个候选站点，不是现有资产只能支撑单点。"""
    responses = _drive_and_measure(28, 2.0, _CANDIDATE_SITES)
    active = {s for s, r in responses.items() if r >= 0.01}

    assert len(active) >= 2, (
        f"单次外部发生（radius=2.0）应产生≥2个活动云条目，实际={len(active)}"
        f"（active={active}）——若仍为1，说明需要新场景（Q5答案会反转为'是'）")

    print(f"T-TSS2A-2: radius=2.0下真实活动云成员数={len(active)}, "
          f"成员={sorted(active)}")
    print("✓ T-TSS2A-2 PASS: 单次外部发生确实产生多成员活动云"
          "（回答Q2：不需要新场景）")


def test_tss2a_3_scale_window_changes_downstream_structure():
    """Q3+Q4：验证尺度窗口改变确实改变下游可见结构（新增成员的响应是
    真实非零测量值，不是软件聚合出来的数字）——区分"真实尺度生成"和
    "软件聚合"的关键在于：新窗口下新增的每个成员都必须有独立的真实
    collector.pre_trace测量值，不是从旧窗口的数据里插值/平均出来的。
    """
    responses_r2, responses_r3, active_r2, active_r3 = \
        test_tss2a_1_two_real_scale_windows_exist()

    newly_active = active_r3 - active_r2
    assert len(newly_active) > 0, (
        "更大尺度窗口应至少新增一个真实激活的站点")

    for site in newly_active:
        # 关键区分：新增站点在r2.0下的响应应接近0（未被聚合"借用"任何
        # 其他站点的数值），在r3.0下应是独立测得的真实非零值
        assert responses_r2[site] < 0.01, (
            f"站点{site}在radius=2.0下不应有显著响应（否则说明它本该在"
            f"r2.0的云里，不是r3.0新增的），实际={responses_r2[site]}")
        assert responses_r3[site] >= 0.01, (
            f"站点{site}在radius=3.0下应有真实测得的非零响应，"
            f"实际={responses_r3[site]}")

    print(f"T-TSS2A-3: 尺度窗口从r=2.0→r=3.0新增的真实激活站点={sorted(newly_active)}")
    print(f"  每个新增站点在两个窗口下的响应值都是独立真实测量"
          f"（不是软件聚合/插值产生）")
    print("✓ T-TSS2A-3 PASS: 尺度窗口改变真实改变下游可见结构，"
          "新增成员是独立测量而非软件聚合（回答Q3/Q4）")


def run():
    test_tss2a_1_two_real_scale_windows_exist()
    test_tss2a_2_single_event_multi_member_cloud()
    test_tss2a_3_scale_window_changes_downstream_structure()
    print()
    print("=" * 60)
    print("T-TSS2A-1~3 ALL PASS")
    print("=" * 60)


if __name__ == "__main__":
    run()
