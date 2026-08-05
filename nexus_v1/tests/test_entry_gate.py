"""nexus_v1.tests.test_entry_gate — TSS-R1b：PhysicalEntryGate 九项资格测试。

TYPE:INFRA

方案依据：cell-cell/claudecode方案/TSS-R1b_E上箭头物理载体实现方案_2026-08-05.md（v2）
裁定：document - 2026-08-05T172740.398.md（批准实现，指定四项最重要测试）

九项资格（评判 170642.972 §四 列出）：
  T-R1B-1：无软件时钟（签名无 t_step，无 _phase/计步器/站点专属字段）
  T-R1B-2：参数工作区（2a 解析不等式 + 2b 数值跨阈步数）
  T-R1B-3：首枚脉冲通过 + MOSFET 阈下行为锁定（评判重点 3）
  T-R1B-4：长簇不重复输出——簇长 ≫ t_open 仍只输出 1 次（评判重点 1，直接杀 v1）
  T-R1B-5：饱和不累积——极端持续驱动后恢复步数仍 ≈ t_open（与簇长无关）
  T-R1B-6：静默后物理恢复（无外部 reset）
  T-R1B-7：跨站点 28/31/21/24 同结构同参数
  T-R1B-8：分歧区间显式测试 + 真实流计数旁证（评判重点 2）
  T-R1B-9：occurrence.py 零改动可执行守卫（评判重点 4）

注意 T-R1B-8 的定位：物理门与参考检测器**不要求逐步等价**（三个开门阈值
互不相同：物理门 1204 / oracle rearm=0 为 501 / oracle rearm=500 为 1001 步）。
计数一致只作旁证，且必须显式断言"实测流无 gap 落在分歧区间"——否则会重犯
"在一条实测流上一致 ⇒ 算子相等"的老错（同 TSS-2b 的 Λ 资格）。
"""
import sys
sys.path.insert(0, '.')

import inspect
import math

from nexus_v1.components.structural_address import (
    AddressRegistry, DOMAIN_SKIN_PATCH, DOMAIN_OCC_THERMAL,
)
from nexus_v1.components.world import HeatSource
from nexus_v1.relations.boundary_process import CollectorBoundaryPort
from nexus_v1.relations.entry_boundary import EntryBoundaryDetector, make_entry_detector
from nexus_v1.relations.entry_gate import (
    PhysicalEntryGate, make_entry_gate, open_delay_steps,
)
from nexus_v1.relations.temporal_r_prec import RPrecCircuitT1

DT = 0.001
N_STEPS = 8000
HEAT_RADIUS = 5.0
HEAT_TEMPERATURE = 300.0

# EXP-R1A-01 实测分离带（TSS-R1a 报告记录，非本轮新测）
ISI_MAX_IN_BURST = 316      # 簇内 ISI 上界（步）
EXIT_GAP_MIN = 4257         # 真实退出间隔下界（步）


def _oracle_open_delay(gap_steps: int, rearm_min_steps: int, max_probe: int = 3000) -> int:
    """实测参考检测器的开门静默步数（不手推数字——用构造脉冲序列直接测）。

    对每个候选静默长度 n 独立构造一次"spike, 静默 n 步, spike"序列，
    返回第一个使第二枚 spike 令 update() 返回 True 的 n。

    直接构造 EntryBoundaryDetector（不经 port/电路）——detector 只吃
    spike_output 数值，构造只需一个地址。
    """
    registry = AddressRegistry()
    addr = _make_address(registry, 0)

    for n in range(max_probe):
        det = EntryBoundaryDetector(generator_address=addr,
                                    gap_steps=gap_steps,
                                    rearm_min_steps=rearm_min_steps)
        t = 0
        assert det.update(1.0, t) is True
        for _ in range(n):
            t += 1
            det.update(0.0, t)
        t += 1
        if det.update(1.0, t) is True:
            return n
    raise AssertionError(f"未在 {max_probe} 步内找到开门静默长度")

_TEST_SITES = [28, 31, 21, 24]


def _make_circuit_with_heat(site: int = 28):
    circuit = RPrecCircuitT1()
    patch = circuit._thermal_quantum_patches[site]
    pos = patch.world_position(circuit.world.body)
    circuit.world.heat_sources = [HeatSource(
        position=list(pos), energy=100000.0, temperature=HEAT_TEMPERATURE,
        radius=HEAT_RADIUS, _drift=[0.0, 0.0, 0.0])]
    return circuit


def _make_address(registry: AddressRegistry, site: int):
    pid = f"thermpt{site}"
    label = f"{pid}_warm"
    parent_addr = registry.register_physical(DOMAIN_SKIN_PATCH, pid)
    return registry.register_generated(DOMAIN_OCC_THERMAL, label, (parent_addr,), 1)


def _fresh_gate(site: int = 28) -> PhysicalEntryGate:
    """构造一个独立物理门（不需要电路——门只吃脉冲序列）。"""
    registry = AddressRegistry()
    addr = _make_address(registry, site)
    return PhysicalEntryGate(generator_address=addr)


def _feed(gate: PhysicalEntryGate, spikes) -> list:
    """喂入脉冲序列，返回每步 b^↑。"""
    return [gate.step(s, DT) for s in spikes]


def test_r1b_1_no_software_clock():
    """T-R1B-1：无软件时钟——签名无 t_step，无 _phase/计步器/站点专属字段。"""
    sig = inspect.signature(PhysicalEntryGate.step)
    params = list(sig.parameters.keys())
    assert params == ["self", "spike_output", "dt"], (
        f"T-R1B-1: step() 签名应只有 (self, spike_output, dt)，实际 {params}"
        "——含 t_step 即意味着依赖软件时钟")

    gate = _fresh_gate(28)
    forbidden = ["_phase", "_silence_count", "t_step",
                 "gap_steps", "rearm_min_steps", "site_id"]
    for name in forbidden:
        assert not hasattr(gate, name), (
            f"T-R1B-1: 禁止字段 {name} 出现在 PhysicalEntryGate 上"
            "（评判 172740.398 明确列出）")

    # 状态必须全部在 Capacitor.charge 里：清零电荷等价于完全复位
    gate.step(1.0, DT)
    assert gate.gate_voltage > 0.0, "T-R1B-1: spike 后门电压应 > 0"
    gate._gate_cap.charge = 0.0
    assert gate.gate_open, (
        "T-R1B-1: 清零 Capacitor.charge 后门应立即开放"
        "——若不开则说明还有别的状态载体")

    # 不得读取 collector 的 _w_adapt / pre_trace（门不持有 Neuron 引用）
    for attr in vars(gate):
        val = getattr(gate, attr)
        assert not hasattr(val, "pre_trace"), (
            f"T-R1B-1: 字段 {attr} 指向了带 pre_trace 的对象"
            "——门不应持有 Neuron 引用")

    print(f"T-R1B-1: step 签名={params}，禁止字段 0 个，状态仅在 Capacitor.charge")
    print("✓ T-R1B-1 PASS: 无软件时钟")


def test_r1b_2a_analytic_working_region():
    """T-R1B-2a：解析验证两个资格不等式（评判给出的形式）。"""
    gate = _fresh_gate(28)
    tau = gate.r_leak * gate.capacitance
    v_h, theta = gate.v_clamp, gate.theta_gate

    # 最大簇内间隔后仍关门
    v_at_isi_max = v_h * math.exp(-(ISI_MAX_IN_BURST * DT) / tau)
    assert v_at_isi_max > theta, (
        f"T-R1B-2a: 簇内 ISI 上界 {ISI_MAX_IN_BURST} 步后 V_g={v_at_isi_max:.4f} "
        f"应 > θ_g={theta}（否则簇内会重复输出）")

    # 真实静默退出后已重新开门
    v_at_exit = v_h * math.exp(-(EXIT_GAP_MIN * DT) / tau)
    assert v_at_exit < theta, (
        f"T-R1B-2a: 真实退出间隔下界 {EXIT_GAP_MIN} 步后 V_g={v_at_exit:.4f} "
        f"应 < θ_g={theta}（否则真实退出后无法恢复）")

    t_open = tau * math.log(v_h / theta)
    print(f"T-R1B-2a: t_open=τ·ln(V_H/θ_g)={t_open:.4f}s={t_open/DT:.0f}步; "
          f"V(316步)={v_at_isi_max:.4f}>θ_g; V(4257步)={v_at_exit:.4f}<θ_g")
    print("✓ T-R1B-2a PASS: 解析工作区成立")


def test_r1b_2b_numeric_open_delay_in_band():
    """T-R1B-2b：数值验证——实测跨阈步数落在分离带 (316, 4257) 内。"""
    gate = _fresh_gate(28)
    gate.step(1.0, DT)          # 单枚 spike → 饱和到 V_H
    assert not gate.gate_open, "T-R1B-2b: spike 后门应关闭"

    n_open = 0
    while not gate.gate_open:
        gate.step(0.0, DT)      # 只泄漏
        n_open += 1
        assert n_open < 100000, "T-R1B-2b: 门在 10 万步内未恢复——疑似永久锁死"

    assert ISI_MAX_IN_BURST < n_open < EXIT_GAP_MIN, (
        f"T-R1B-2b: 实测跨阈步数 {n_open} 应落在分离带 "
        f"({ISI_MAX_IN_BURST}, {EXIT_GAP_MIN}) 内"
        "——若不在则既有默认参数下不存在工作区，应停止并报告裁定，不得调 τ 硬凑")

    n_analytic = open_delay_steps(dt=DT)
    assert abs(n_open - n_analytic) <= 2, (
        f"T-R1B-2b: 实测 {n_open} 步与解析 {n_analytic} 步应一致（容差 ±2 浮点边界）")

    print(f"T-R1B-2b: 实测跨阈 {n_open} 步（解析 {n_analytic}），"
          f"分离带 ({ISI_MAX_IN_BURST}, {EXIT_GAP_MIN}) 几何中位 "
          f"{math.sqrt(ISI_MAX_IN_BURST * EXIT_GAP_MIN):.0f} 步")
    print("✓ T-R1B-2b PASS: 数值跨阈步数落在分离带内")


def test_r1b_3_first_spike_passes_and_mosfet_subthreshold_locked():
    """T-R1B-3：首枚脉冲通过 + MOSFET 阈下硬阈值行为锁定（评判重点 3）。"""
    gate = _fresh_gate(28)
    assert gate.gate_open, "T-R1B-3: 初始（V_g=0）门应开放"

    b_up = gate.step(1.0, DT)
    assert b_up == 1.0, "T-R1B-3: 门开放时首枚 spike 应输出 b^↑=1.0"
    assert gate.entry_count == 1

    # 锁定 MOSFET 阈下行为：当前实现在 V<Vth 时恒返回 0.0。
    # 若将来 conduct() 的阈下尾流被"修复"成微小正值，本门会永远微导通、
    # E^↑ 静默失效——这条断言必须立刻报警（模块脆弱点 R5）。
    theta = gate.theta_gate
    assert gate._gate_fet.conduct(theta - 1e-6) == 0.0, (
        "T-R1B-3: MOSFET.conduct(θ_g - 1e-6) 必须恒等于 0.0"
        "——本门的硬阈值判定依赖此实现行为（semiconductor.py:151-159 "
        "注释承诺指数尾流但实现被 max(0.0,·) 截零）。此断言失败说明原语"
        "语义已变，PhysicalEntryGate 需重新设计阈值判定方式")
    assert gate._gate_fet.conduct(theta + 1e-6) > 0.0, (
        "T-R1B-3: 阈上应有正电流（否则门永不关闭）")

    print(f"T-R1B-3: 首枚输出 b^↑=1.0；conduct(θ_g-1e-6)=0.0 锁定，"
          f"conduct(θ_g+1e-6)={gate._gate_fet.conduct(theta + 1e-6):.4f}>0")
    print("✓ T-R1B-3 PASS: 首枚通过 + 阈下行为锁定")


def test_r1b_4_long_burst_emits_once():
    """T-R1B-4：长簇不重复输出（评判重点 1，直接杀 v1 方案）。

    构造总长 ≫ t_open 但相邻 ISI ≤ 316 步的脉冲簇 → 只能输出 1 次。
    v1（被抑制的脉冲不刷新电容）在此会输出 ≥4 次。
    """
    gate = _fresh_gate(28)
    n_open = open_delay_steps(dt=DT)
    isi = ISI_MAX_IN_BURST
    burst_len = n_open * 4          # 4 倍 t_open，远超开门时间

    spikes = [1.0 if (t % isi == 0) else 0.0 for t in range(burst_len)]
    outputs = _feed(gate, spikes)
    n_entries = int(sum(outputs))

    assert burst_len > n_open, (
        f"T-R1B-4: 测试设计要求簇长 {burst_len} > t_open {n_open}")
    assert n_entries == 1, (
        f"T-R1B-4: 簇长 {burst_len} 步（{burst_len // isi} 枚脉冲，ISI={isi}）"
        f"应只输出 1 次 b^↑，实际 {n_entries} 次"
        "——>1 说明被抑制的脉冲没有刷新门电压（v1 的失败模式）")
    assert outputs[0] == 1.0, "T-R1B-4: 唯一的输出应发生在首枚脉冲"

    print(f"T-R1B-4: 簇长 {burst_len} 步 = {burst_len / n_open:.1f}×t_open，"
          f"{burst_len // isi} 枚脉冲（ISI={isi}）→ b^↑ 共 {n_entries} 次")
    print("✓ T-R1B-4 PASS: 长簇只输出一次（每枚脉冲确实刷新了门）")


def test_r1b_5_saturation_no_accumulation():
    """T-R1B-5：饱和不累积——极端持续驱动后恢复步数仍 ≈ t_open。"""
    gate = _fresh_gate(28)
    n_open_ref = open_delay_steps(dt=DT)

    # 极端驱动：连续 5000 步每步都 spike（满占空比）
    drive_len = 5000
    v_max_seen = 0.0
    for _ in range(drive_len):
        gate.step(1.0, DT)
        v_max_seen = max(v_max_seen, gate.gate_voltage)

    assert v_max_seen <= gate.v_clamp + 1e-9, (
        f"T-R1B-5: 门电压峰值 {v_max_seen:.6f} 不得超过 V_H={gate.v_clamp}"
        "——超过说明 Zener 钳位失效，会导致永久锁死")

    # 从末枚 spike 起静默，测恢复步数
    n_recover = 0
    while not gate.gate_open:
        gate.step(0.0, DT)
        n_recover += 1
        assert n_recover < 100000, "T-R1B-5: 满占空比驱动后永久锁死"

    assert abs(n_recover - n_open_ref) <= 2, (
        f"T-R1B-5: 满占空比 {drive_len} 步驱动后恢复 {n_recover} 步，"
        f"应与单枚 spike 后的 {n_open_ref} 步一致（容差 ±2）"
        "——不一致说明恢复时间依赖发放率/簇长，破坏位置无关性")

    print(f"T-R1B-5: {drive_len} 步满占空比驱动，V_g 峰值 {v_max_seen:.6f} "
          f"≤ V_H={gate.v_clamp}；恢复 {n_recover} 步 vs 单枚 {n_open_ref} 步")
    print("✓ T-R1B-5 PASS: 饱和不累积，恢复时间与簇长无关")


def test_r1b_6_physical_recovery_after_silence():
    """T-R1B-6：静默后物理恢复，中途无任何外部 reset。"""
    gate = _fresh_gate(28)
    b1 = gate.step(1.0, DT)
    assert b1 == 1.0

    # 静默真实退出间隔下界
    for _ in range(EXIT_GAP_MIN):
        out = gate.step(0.0, DT)
        assert out == 0.0, "T-R1B-6: 静默期不应有输出"

    b2 = gate.step(1.0, DT)
    assert b2 == 1.0, (
        f"T-R1B-6: 静默 {EXIT_GAP_MIN} 步后 spike 应重新输出 b^↑"
        "（且全程未调用任何 reset）")
    assert gate.entry_count == 2

    print(f"T-R1B-6: 静默 {EXIT_GAP_MIN} 步后重新输出，entry_count={gate.entry_count}，"
          f"全程无外部 reset")
    print("✓ T-R1B-6 PASS: 静默后物理恢复")


def test_r1b_7_cross_site_same_structure_and_params():
    """T-R1B-7：28/31/21/24 用同一结构、同一份参数。"""
    n_open_ref = open_delay_steps(dt=DT)
    isi = ISI_MAX_IN_BURST
    burst_len = n_open_ref * 4
    spikes = [1.0 if (t % isi == 0) else 0.0 for t in range(burst_len)]

    results = {}
    param_sets = set()
    for site in _TEST_SITES:
        gate = _fresh_gate(site)
        assert type(gate) is PhysicalEntryGate, (
            f"T-R1B-7: 站点 {site} 出现了专属子类")
        param_sets.add((gate.capacitance, gate.r_leak, gate.v_clamp,
                        gate.theta_gate, gate.q_spike, gate.gm_clamp))

        n_entries = int(sum(_feed(gate, spikes)))
        # 恢复步数须从"最后一枚脉冲"起算，不是从数组末尾起算——
        # burst 末尾到最后一枚脉冲之间已经历的泄漏步数要补上（isi-1 步）
        steps_since_last_spike = (burst_len - 1) % isi
        n_recover = steps_since_last_spike
        while not gate.gate_open:
            gate.step(0.0, DT)
            n_recover += 1
        results[site] = (n_entries, n_recover)

        assert n_entries == 1, (
            f"T-R1B-7: 站点 {site} 长簇输出 {n_entries} 次，应为 1")
        assert abs(n_recover - n_open_ref) <= 2, (
            f"T-R1B-7: 站点 {site} 恢复 {n_recover} 步（从末枚脉冲起算），"
            f"应为 {n_open_ref}±2——若某站点需要不同参数才能通过，"
            "这本身是失败信号，应报告而非分别调参")

    assert len(param_sets) == 1, (
        f"T-R1B-7: 四站点参数不统一，出现 {len(param_sets)} 组：{param_sets}")

    print(f"T-R1B-7: {_TEST_SITES} 共用一组参数 {param_sets.pop()}；"
          f"结果 {results}")
    print("✓ T-R1B-7 PASS: 跨站点同结构同参数")


def test_r1b_8_divergence_band_explicit_and_count_corroboration():
    """T-R1B-8：分歧区间显式测试（评判重点 2）+ 真实流计数旁证。

    物理门与参考检测器**不要求逐步等价**——三个开门阈值互不相同。
    真实数据流恰好跳过了分歧区间，所以必须用构造间隔显式测试。
    """
    n_open = open_delay_steps(dt=DT)
    # oracle 阈值实测得到，不手推数字
    oracle_rearm0_open = _oracle_open_delay(gap_steps=500, rearm_min_steps=0)
    oracle_rearm500_open = _oracle_open_delay(gap_steps=500, rearm_min_steps=500)

    # ── 第一部分：分歧区间显式测试（评判指定 600/1000/1203/1205）──
    # 查询在"静默 gap 步（纯 leak，无脉冲）"之后门是否开放，直接用
    # gate_open 属性——不再喂一枚探测脉冲，避免探测脉冲自身的 leak
    # 引入额外一步造成 off-by-one（T-R1B-2b 的 n_open 也是用同样方式测的）。
    probe_gaps = [600, 1000, n_open - 1, n_open + 1]
    observed = {}
    for gap in probe_gaps:
        gate = _fresh_gate(28)
        assert gate.step(1.0, DT) == 1.0
        for _ in range(gap):
            gate.step(0.0, DT)
        observed[gap] = gate.gate_open

    assert observed[600] is False, (
        f"T-R1B-8: 静默 600 步（< t_open={n_open}）后应仍关门，"
        f"实际 gate_open={observed[600]}")
    assert observed[1000] is False, (
        f"T-R1B-8: 静默 1000 步（< t_open={n_open}）后应仍关门，"
        f"实际 gate_open={observed[1000]}")
    assert observed[n_open - 1] is False, (
        f"T-R1B-8: 静默 {n_open - 1} 步（= t_open-1）后应仍关门，"
        f"实际 gate_open={observed[n_open - 1]}")
    assert observed[n_open + 1] is True, (
        f"T-R1B-8: 静默 {n_open + 1} 步（= t_open+1）后应重新开门，"
        f"实际 gate_open={observed[n_open + 1]}")

    # 这四个点里 600/1000 应落在物理门与 oracle 的分歧区间内——
    # 断言的是**物理门的定义**，不是 oracle 的，用实测的 oracle 阈值核对。
    assert oracle_rearm0_open <= 600 < n_open, (
        f"T-R1B-8: 600 步应落在 vs rearm=0 oracle 的分歧区间 "
        f"[{oracle_rearm0_open}, {n_open})")
    assert oracle_rearm500_open <= 1000 < n_open, (
        f"T-R1B-8: 1000 步应落在 vs rearm=500 oracle 的分歧区间 "
        f"[{oracle_rearm500_open}, {n_open})")

    print(f"T-R1B-8 分歧区间：t_open={n_open}, oracle(rearm=0)={oracle_rearm0_open}, "
          f"oracle(rearm=500)={oracle_rearm500_open}；"
          f"gap=600→{observed[600]}, 1000→{observed[1000]}, "
          f"{n_open-1}→{observed[n_open-1]}, {n_open+1}→{observed[n_open+1]}")

    # ── 第二部分：真实流计数旁证（非资格判据）──
    circuit = _make_circuit_with_heat(28)
    registry = AddressRegistry()
    addr = _make_address(registry, 28)
    collector = circuit.thermal_quantum_collectors["thermpt28_warm"]
    port = CollectorBoundaryPort(generator_address=addr, carrier_ref=collector)

    gate = make_entry_gate(port)
    det0 = make_entry_detector(port, gap_steps=500, rearm_min_steps=0)
    det500 = make_entry_detector(port, gap_steps=500, rearm_min_steps=500)

    spike_steps = []
    n_gate = n_det0 = n_det500 = 0
    for t in range(N_STEPS):
        circuit.step({}, DT)
        s = port.spike_output
        if s > 0.5:
            spike_steps.append(t)
        n_gate += int(gate.step(s, DT) > 0.5)
        n_det0 += int(det0.update(s, t))
        n_det500 += int(det500.update(s, t))

    # 旁证成立的前提必须可验证：实测流不得有 gap 落在分歧区间
    # （区间下界取两个 oracle 阈值的较小者——只要 gap 落在其中任一
    #  分歧区间内，计数一致就不再是有效旁证）
    band_lo = min(oracle_rearm0_open, oracle_rearm500_open)
    gaps = [b - a for a, b in zip(spike_steps, spike_steps[1:])]
    in_band = [g for g in gaps if band_lo <= g < n_open]
    assert not in_band, (
        f"T-R1B-8: 实测流出现 {len(in_band)} 个 gap 落在分歧区间 "
        f"[{band_lo}, {n_open})：{in_band[:5]}"
        "——此时计数一致不再是有效旁证（物理门与 oracle 定义不同），"
        "必须改用构造序列判定，不得据此宣称等价")

    assert n_gate == n_det0 == n_det500, (
        f"T-R1B-8: 实测流事件计数应一致（旁证）——"
        f"物理门 {n_gate} / oracle(rearm=0) {n_det0} / oracle(rearm=500) {n_det500}")

    print(f"T-R1B-8 计数旁证：{len(spike_steps)} 枚 spike，gap 范围 "
          f"[{min(gaps) if gaps else 0}, {max(gaps) if gaps else 0}]，"
          f"分歧区间 [{band_lo}, {n_open}) 内 0 个；"
          f"计数 门={n_gate} oracle0={n_det0} oracle500={n_det500}")
    print("✓ T-R1B-8 PASS: 分歧区间显式验证 + 计数旁证（前提已断言）")


def test_r1b_9_occurrence_py_untouched():
    """T-R1B-9：occurrence.py 零改动可执行守卫（评判重点 4）。"""
    from nexus_v1.generators import occurrence as occ

    assert occ._DEFAULT_REARM_MIN_STEPS == 500, (
        f"T-R1B-9: occurrence.py 的 _DEFAULT_REARM_MIN_STEPS 应仍为 500，"
        f"实际 {occ._DEFAULT_REARM_MIN_STEPS}"
        "——本轮不得顺手处理双时钟债务（评判 170642.972 §风险1）")
    assert hasattr(occ, "_ClosurePhase"), (
        "T-R1B-9: occurrence.py 的 _ClosurePhase 三态机应仍存在（未被合并）")
    phases = {p.name for p in occ._ClosurePhase}
    assert phases == {"ARMED", "ACTIVE", "REFRACTORY"}, (
        f"T-R1B-9: _ClosurePhase 应仍是三态，实际 {phases}")

    # 物理门不得引用 occurrence 相关符号。
    # 只检查**可执行代码行**（剔除 docstring 与注释）——模块文档里说明
    # "不得读取 OccurrenceClosure / pre_trace / _w_adapt" 这类句子是合规
    # 声明，不是引用；对整份源码做子串匹配会把说明文字本身判成违规。
    import ast
    import nexus_v1.relations.entry_gate as eg
    src = inspect.getsource(eg)
    tree = ast.parse(src)
    code_lines = set()
    for node in ast.walk(tree):
        # 收集所有标识符与属性名（不含字符串字面量与注释）
        if isinstance(node, ast.Name):
            code_lines.add(node.id)
        elif isinstance(node, ast.Attribute):
            code_lines.add(node.attr)
        elif isinstance(node, ast.alias):
            code_lines.add(node.name.split(".")[-1])
            if node.asname:
                code_lines.add(node.asname)
        elif isinstance(node, ast.ImportFrom) and node.module:
            code_lines.add(node.module.split(".")[-1])

    for forbidden in ["OccurrenceClosure", "_ClosurePhase", "occurrence_tap",
                      "occurrence", "pre_trace", "_w_adapt"]:
        assert forbidden not in code_lines, (
            f"T-R1B-9: entry_gate.py 的可执行代码不得引用 {forbidden}")

    print(f"T-R1B-9: occurrence.py rearm={occ._DEFAULT_REARM_MIN_STEPS}, "
          f"三态 {sorted(phases)} 均未改动；entry_gate.py 可执行代码无禁止引用")
    print("✓ T-R1B-9 PASS: 旧母本零改动")


def main():
    tests = [
        test_r1b_1_no_software_clock,
        test_r1b_2a_analytic_working_region,
        test_r1b_2b_numeric_open_delay_in_band,
        test_r1b_3_first_spike_passes_and_mosfet_subthreshold_locked,
        test_r1b_4_long_burst_emits_once,
        test_r1b_5_saturation_no_accumulation,
        test_r1b_6_physical_recovery_after_silence,
        test_r1b_7_cross_site_same_structure_and_params,
        test_r1b_8_divergence_band_explicit_and_count_corroboration,
        test_r1b_9_occurrence_py_untouched,
    ]
    passed = 0
    for fn in tests:
        print(f"\n{'=' * 68}\n{fn.__name__}\n{'=' * 68}")
        fn()
        passed += 1
    print(f"\n{'=' * 68}\nTSS-R1b: {passed}/{len(tests)} PASS\n{'=' * 68}")
    return 0 if passed == len(tests) else 1


if __name__ == "__main__":
    sys.exit(main())
