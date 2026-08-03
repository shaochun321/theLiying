"""nexus_v1.tests.test_generator_lambda — TSS-2b：同一活动云、双物理窗口、
双独立输出的尺度算子验证。

方案依据：document - 2026-08-03T201310.154.md（TSS-2b裁定）。

评判要求的核心资格测试：
  同一个外部OccurrenceInstanceId驱动local/broad两个独立collector；
  切断N_Δ（广域独有部分）到broad的链路后：
    Y_local^cut == Y_local（不受影响）
    Y_broad^cut ≠ Y_broad（受影响）
  证明两个输出差异来自真实结构支撑范围，不是名称或软件标签。

三个测试：
  T-TSS2B-1：同一次驱动，local/broad两个collector都产生真实非零响应
            （不是软件sum()聚合——两者是独立SynapticBundle+独立collector）
  T-TSS2B-2：切断N_Δ后，local响应不受影响，broad响应确实改变
  T-TSS2B-3：站点集合在构造期冻结，不依赖运行时坐标计算（结构断言，
            非物理仿真）
"""
import sys

sys.path.insert(0, '.')

from nexus_v1.components.world import HeatSource
from nexus_v1.relations.generator_lambda import (
    LambdaScaleCircuit, N_LOCAL, N_BROAD, N_DELTA, SOURCE_SITE,
)

DT = 0.001
N_STEPS = 1600
HEAT_RADIUS = 3.0   # 覆盖N_BROAD全部站点的单次驱动（同一次外部发生）
HEAT_TEMPERATURE = 300.0


def _drive_once(cut_delta: bool = False, random_seed: int = 20260803):
    """构造并驱动一次circuit，返回(circuit, y_local_max, y_broad_max)。

    只驱动一次HeatSource（同一个外部发生ω[W]），local/broad两个
    collector在同一次驱动过程中同时读取活动云——不是分两次驱动后
    对比（评判201310第一点修正的核心要求）。

    real发现（T-TSS2B-2首次运行时定位）：components/langevin_noise.py
    用random.gauss()生成噪声，消耗全局random模块状态——full/cut两次
    独立_drive_once()调用之间的random状态累积不同，导致即使
    bundles_local完全不受cut_delta_bundles()影响，两次运行的Langevin
    噪声轨迹仍会不同，产生~0.6%的Y_local差异（这不是N_Δ切断的真实
    影响，是跨run随机噪声差异——同HeatSource._drift的已知问题同一类）。
    固定random.seed()确保full/cut两次运行除N_Δ切断外，其余随机过程
    完全相同，这是对照实验的正确控制变量，不是回避问题。
    """
    import random
    random.seed(random_seed)

    circuit = LambdaScaleCircuit()
    if cut_delta:
        circuit.cut_delta_bundles()

    patch = circuit._thermal_quantum_patches[SOURCE_SITE]
    heat_pos = patch.world_position(circuit.world.body)
    circuit.world.heat_sources = [HeatSource(
        position=list(heat_pos), energy=100000.0,
        temperature=HEAT_TEMPERATURE, radius=HEAT_RADIUS,
        _drift=[0.0, 0.0, 0.0],
    )]

    y_local_max = 0.0
    y_broad_max = 0.0
    for t in range(N_STEPS):
        circuit.step({}, DT)
        circuit.step_lambda(DT)
        y_local_max = max(y_local_max, circuit.lambda_local_collector.pre_trace)
        y_broad_max = max(y_broad_max, circuit.lambda_broad_collector.pre_trace)

    return circuit, y_local_max, y_broad_max


def test_tss2b_1_same_event_two_independent_outputs():
    """T-TSS2B-1：同一次外部发生（单次HeatSource驱动）产生的活动云，
    local/broad两个独立collector都有真实非零响应。"""
    circuit, y_local, y_broad = _drive_once()

    assert y_local > 0.01, f"Y_local应有真实非零响应，实际={y_local}"
    assert y_broad > 0.01, f"Y_broad应有真实非零响应，实际={y_broad}"
    # local和broad是不同collector对象，物理上独立（不是同一个数值的两次读取）
    assert circuit.lambda_local_collector is not circuit.lambda_broad_collector

    print(f"T-TSS2B-1: Y_local={y_local:.4f}, Y_broad={y_broad:.4f}")
    print("✓ T-TSS2B-1 PASS: 同一次外部发生产生的活动云，"
          "local/broad两个独立collector都有真实响应")


def test_tss2b_2_cut_delta_affects_only_broad():
    """T-TSS2B-2（关键资格测试）：切断N_Δ到broad的链路后，
    Y_local不受影响，Y_broad确实改变——证明差异来自真实结构支撑范围。
    """
    _, y_local_full, y_broad_full = _drive_once(cut_delta=False)
    _, y_local_cut, y_broad_cut = _drive_once(cut_delta=True)

    assert abs(y_local_full - y_local_cut) < 1e-9, (
        f"切断N_Δ(广域独有部分)不应影响Y_local（local bundles是独立对象，"
        f"不含N_Δ站点），实际: full={y_local_full}, cut={y_local_cut}")

    assert abs(y_broad_full - y_broad_cut) > 1e-6, (
        f"切断N_Δ应真实改变Y_broad（broad bundles包含N_Δ站点的输入），"
        f"实际: full={y_broad_full}, cut={y_broad_cut}")

    # ── 资格边界（TSS-2b修正新增）：broad限制到local支撑集后必须逐位等于
    # local。这不是"通过"标志，恰恰是**降格依据**——它证明local/broad是
    # 同一个求和算子作用在两张输入表上，不是两个不同的尺度算子。初版此处
    # 有7%差（2.4918 vs 2.3280）被误读为结构效应，实为bundle_id哈希扰动
    # 污染（见generator_lambda._PHYS_SEED_BASE）。断言恒等，以后任何"尺度
    # 专属变换"的宣称必须先让这条断言失败。 ──
    assert abs(y_broad_cut - y_local_full) < 1e-9, (
        f"physical_seed对齐后，broad限制到N_LOCAL应与local逐位相同"
        f"（同一算子同一支撑集）。实际: Y_broad^cut={y_broad_cut}, "
        f"Y_local={y_local_full} —— 若此处出现差异，说明仍有身份信息泄漏"
        f"进物理权重（S0-bX1门），或引入了未记录的尺度专属变换")

    print(f"T-TSS2B-2: Y_local(full={y_local_full:.4f}, cut={y_local_cut:.4f}) "
          f"— 不变（构造保证：bundles_local不含N_Δ，非资格证据）")
    print(f"           Y_broad(full={y_broad_full:.4f}, cut={y_broad_cut:.4f}) "
          f"— 改变")
    print(f"           Y_broad^cut == Y_local: {y_broad_cut:.6f} == "
          f"{y_local_full:.6f} — 同一算子，两张输入表")
    print("✓ T-TSS2B-2 PASS: 切断N_Δ真实改变broad；同时确认local/broad是"
          "同一求和算子的两个支撑范围（嵌套支撑，非独立尺度算子）")


def test_tss2b_3_membership_frozen_at_construction():
    """T-TSS2B-3：站点集合在构造期字面冻结，不依赖运行时坐标计算——
    结构断言（检查代码常量，不跑物理仿真）。"""
    assert N_LOCAL.issubset(N_BROAD), "N_local应是N_broad的子集"
    assert N_DELTA == N_BROAD - N_LOCAL
    assert len(N_DELTA) > 0, "N_Δ应非空，否则切断实验无意义"

    circuit = LambdaScaleCircuit()
    local_sites_in_bundles = {
        int(b.config.bundle_id.split("site")[1].split("_")[0])
        for b in circuit.bundles_local
    }
    broad_sites_in_bundles = {
        int(b.config.bundle_id.split("site")[1].split("_")[0])
        for b in circuit.bundles_broad
    }
    assert local_sites_in_bundles == N_LOCAL
    assert broad_sites_in_bundles == N_BROAD

    print(f"T-TSS2B-3: N_local={sorted(N_LOCAL)}")
    print(f"           N_broad={sorted(N_BROAD)}")
    print(f"           N_delta={sorted(N_DELTA)}")
    print("✓ T-TSS2B-3 PASS: 站点集合在构造期字面冻结，"
          "bundle实际连接的站点与冻结常量完全一致")


def run():
    test_tss2b_1_same_event_two_independent_outputs()
    test_tss2b_2_cut_delta_affects_only_broad()
    test_tss2b_3_membership_frozen_at_construction()
    print()
    print("=" * 60)
    print("T-TSS2B-1~3 ALL PASS")
    print("=" * 60)


if __name__ == "__main__":
    run()
