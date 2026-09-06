"""tss.tests.test_theta_unified — TSS-M2：统一 Θ 九条资格测试(T-TH-1~9)。

TYPE:INFRA

路线依据：08_下一阶段路线图.md §3 T-4（统一 Θ 最低资格 9 条）。
用户裁定 2026-09-06：C-02=比较完全由 MOSFET 承担。

九条资格 → 测试映射：
  T-TH-1：窗口内 i 后接 j → 产生关系（合成链路）        [资格 4]
  T-TH-2：仅 i / 仅 j → 不产生（且为精确零）            [资格 3]
  T-TH-3：交换顺序 / 同步进入 → 不产生                  [资格 5]
  T-TH-4：超窗 → 不产生（且为精确零）                   [资格 6]
  T-TH-5：输出具有可阻断独立作用（下游电容对照实验）    [资格 7]
  T-TH-6：父谱系正确传递，自身对拒绝                    [资格 8]
  T-TH-7：同一类同一参数跑三个站点对，无站点专属字段    [资格 1、9]
  T-TH-8：静态自审计——无软件时钟/禁止读取              [资格 2]
  T-TH-9：真实链路三站点对 28≺15/21/24 正向全部产生、
          镜像对全部为零（TSS-3a 场景单次外部发生）      [资格 4/5 实流验证]

目标站点对来源：TSS-3a 2026-09-06 重跑裁定的全部跨种子稳定对
（28≺31 被停止条件 4 否决；28≺12 超出适用域——见 history_kernel.py Q3）。
"""
import sys
sys.path.insert(0, '.')

import inspect
import math

from nexus_v1.components.semiconductor import Capacitor
from nexus_v1.components.structural_address import (
    AddressRegistry, DOMAIN_SKIN_PATCH, DOMAIN_OCC_THERMAL,
)
from nexus_v1.components.world import HeatSource
from tss.relations.boundary_process import CollectorBoundaryPort
from tss.relations.entry_gate import PhysicalEntryGate, make_entry_gate
from tss.relations.history_kernel import PhysicalHistoryKernel, make_history_kernel
from tss.relations.theta_comparator import (
    PhysicalThetaComparator, make_theta_comparator,
)
from tss.relations.temporal_r_prec import RPrecCircuitT1

DT = 0.001
T_READ = 723             # H_τ 可读窗（test_history_kernel T-R1C-4 实测）
TARGET_SITES = (15, 21, 24)   # TSS-3a 稳定目标站点对（源=28）
SOURCE_SITE = 28
N_STEPS_REAL = 1600      # 同 TSS-3a 场景
HEAT_RADIUS = 3.0        # 同 TSS-3a：单次外部发生覆盖全部目标站点


def _make_address(registry: AddressRegistry, site: int):
    pid = f"thermpt{site}"
    label = f"{pid}_warm"
    parent_addr = registry.register_physical(DOMAIN_SKIN_PATCH, pid)
    return registry.register_generated(DOMAIN_OCC_THERMAL, label, (parent_addr,), 1)


def _synthetic_pair(site_i: int = 28, site_j: int = 15):
    """构造一对合成链路：gate_i→kernel_i 与 gate_j，及其比较器。"""
    registry = AddressRegistry()
    addr_i = _make_address(registry, site_i)
    addr_j = _make_address(registry, site_j)
    gate_i = PhysicalEntryGate(generator_address=addr_i)
    gate_j = PhysicalEntryGate(generator_address=addr_j)
    kernel_i = PhysicalHistoryKernel(generator_address=addr_i)
    comp = make_theta_comparator(kernel_i, gate_j)
    return gate_i, gate_j, kernel_i, comp


def _run_chain(gate_i, gate_j, kernel_i, comp, spikes_i, spikes_j):
    """逐步串联 port→gate→kernel→comparator，返回每步 r 序列。"""
    rs = []
    for s_i, s_j in zip(spikes_i, spikes_j):
        b_i = gate_i.step(s_i, DT)
        h_i = kernel_i.step(b_i, DT)
        b_j = gate_j.step(s_j, DT)
        rs.append(comp.step(h_i, b_j, DT))
    return rs


def test_th_1_in_window_order_fires():
    """T-TH-1：窗口内 i(t=0) 后接 j(t=300) → 恰在 j 进入步产生关系。"""
    gate_i, gate_j, kernel_i, comp = _synthetic_pair()
    n = 400
    spikes_i = [1.0 if t == 0 else 0.0 for t in range(n)]
    spikes_j = [1.0 if t == 300 else 0.0 for t in range(n)]
    rs = _run_chain(gate_i, gate_j, kernel_i, comp, spikes_i, spikes_j)

    fire_steps = [t for t, r in enumerate(rs) if r > 0.0]
    assert fire_steps == [300], (
        f"T-TH-1: 关系应恰在 j 进入步(300)产生一次，实际 {fire_steps}")
    # r 量级 = 历史新鲜度因子 × 脉冲因子 = (e^{-0.3/0.6}-0.3)·gm × 0.7·gm
    expected = (math.exp(-300 * DT / 0.6) - 0.3) * 1.0 * 0.7 * 1.0
    assert abs(rs[300] - expected) < 1e-6, (
        f"T-TH-1: r={rs[300]:.6f} 与物理预期 {expected:.6f} 不符")
    assert comp.relation_count == 1

    print(f"T-TH-1: i@0, j@300 → r 恰在步300产生，r={rs[300]:.4f}"
          f"（=历史因子×脉冲因子，物理量级吻合）")
    print("✓ T-TH-1 PASS")


def test_th_2_single_input_exact_zero():
    """T-TH-2：仅 i / 仅 j → 不产生关系，且输出为精确零（硬截零负例）。"""
    _, _, _, comp = _synthetic_pair()

    r_only_i = comp.step(0.545, 0.0, DT)   # 历史可读但 j 未进入
    assert r_only_i == 0.0, f"T-TH-2: 仅 i 应为精确零，得 {r_only_i!r}"
    r_only_j = comp.step(0.0, 1.0, DT)     # j 进入但 i 无历史
    assert r_only_j == 0.0, f"T-TH-2: 仅 j 应为精确零，得 {r_only_j!r}"
    r_neither = comp.step(0.0, 0.0, DT)
    assert r_neither == 0.0
    assert comp.relation_count == 0, "T-TH-2: 负例不得计入 relation_count"

    print("T-TH-2: 仅i/仅j/双无 → r 均为精确 0.0（MOSFET 阈下硬截零负例）")
    print("✓ T-TH-2 PASS")


def test_th_3_swap_and_simultaneous_no_fire():
    """T-TH-3：交换顺序（j 先 i 后）与同步进入 → 全程不产生关系。"""
    # 交换顺序：j@100 先，i@500 后 → r_{i≺j} 全程为零
    gate_i, gate_j, kernel_i, comp = _synthetic_pair()
    n = 900
    spikes_i = [1.0 if t == 500 else 0.0 for t in range(n)]
    spikes_j = [1.0 if t == 100 else 0.0 for t in range(n)]
    rs = _run_chain(gate_i, gate_j, kernel_i, comp, spikes_i, spikes_j)
    assert all(r == 0.0 for r in rs), (
        f"T-TH-3: j 先 i 后时 r_{{i≺j}} 应全程为零，"
        f"实际在步 {[t for t, r in enumerate(rs) if r > 0]} 产生")

    # 同步进入：i、j 同一步 → 严格先序（history_kernel 充电前读出）排除
    gate_i2, gate_j2, kernel_i2, comp2 = _synthetic_pair()
    spikes_both = [1.0 if t == 50 else 0.0 for t in range(200)]
    rs2 = _run_chain(gate_i2, gate_j2, kernel_i2, comp2, spikes_both, spikes_both)
    assert all(r == 0.0 for r in rs2), (
        "T-TH-3: 同步进入应不产生关系（i 本步进入不得出现在自己的历史里）")

    print("T-TH-3: 交换顺序(j@100,i@500)与同步进入(@50) → r 全程 0.0")
    print("✓ T-TH-3 PASS")


def test_th_4_beyond_window_exact_zero():
    """T-TH-4：超窗（Δt=800 > t_read=723）→ 不产生，且为精确零。"""
    gate_i, gate_j, kernel_i, comp = _synthetic_pair()
    n = 900
    spikes_i = [1.0 if t == 0 else 0.0 for t in range(n)]
    spikes_j = [1.0 if t == 800 else 0.0 for t in range(n)]
    rs = _run_chain(gate_i, gate_j, kernel_i, comp, spikes_i, spikes_j)
    assert all(r == 0.0 for r in rs), (
        f"T-TH-4: Δt=800 超窗应不产生关系，"
        f"实际在步 {[t for t, r in enumerate(rs) if r > 0]} 产生")

    # 对照：窗口边界内侧（Δt=700 < 723）应产生——证明零来自窗口而非链路坏死
    gate_i2, gate_j2, kernel_i2, comp2 = _synthetic_pair()
    spikes_i2 = [1.0 if t == 0 else 0.0 for t in range(n)]
    spikes_j2 = [1.0 if t == 700 else 0.0 for t in range(n)]
    rs2 = _run_chain(gate_i2, gate_j2, kernel_i2, comp2, spikes_i2, spikes_j2)
    assert any(r > 0.0 for r in rs2), (
        "T-TH-4 对照失败：Δt=700 窗内应产生关系——链路本身坏死，"
        "超窗零不可作为资格证据")

    print(f"T-TH-4: Δt=800 超窗 r≡0.0；对照 Δt=700 窗内产生 r={max(rs2):.4f}"
          "（零确由窗口边界产生）")
    print("✓ T-TH-4 PASS")


def test_th_5_blockable_independent_effect():
    """T-TH-5：r 具有可阻断独立作用——下游电容充电对照实验。

    同一脉冲场景跑两遍：正常链路 vs 比较器输出被阻断（不注入下游）。
    下游电容电压必须可测差异（正常>0，阻断==0）——证明 r 是独立物理
    输出，不是只存在于测试断言里的数字。
    """
    def _run(block: bool) -> float:
        gate_i, gate_j, kernel_i, comp = _synthetic_pair()
        downstream = Capacitor(capacitance=1.0, charge=0.0)
        n = 400
        for t in range(n):
            b_i = gate_i.step(1.0 if t == 0 else 0.0, DT)
            h_i = kernel_i.step(b_i, DT)
            b_j = gate_j.step(1.0 if t == 300 else 0.0, DT)
            r = comp.step(h_i, b_j, DT)
            if not block:
                downstream.inject(r, 1.0)   # r 电流驱动下游
        return downstream.voltage

    v_normal = _run(block=False)
    v_blocked = _run(block=True)
    assert v_normal > 0.0, (
        f"T-TH-5: 正常链路下游电压应 >0，得 {v_normal}")
    assert v_blocked == 0.0, (
        f"T-TH-5: 阻断后下游电压应为 0，得 {v_blocked}")
    assert v_normal - v_blocked > 1e-6, "T-TH-5: 阻断前后无可测差异"

    print(f"T-TH-5: 下游电容 正常={v_normal:.4f} vs 阻断={v_blocked:.4f}"
          "——r 具有可阻断的独立物理作用")
    print("✓ T-TH-5 PASS")


def test_th_6_lineage_correct():
    """T-TH-6：父谱系正确传递（i=历史方，j=进入方，顺序即语义）；自身对拒绝。"""
    gate_i, gate_j, kernel_i, comp = _synthetic_pair()
    assert comp.address_i is kernel_i.generator_address, (
        "T-TH-6: address_i 未从历史核(先行方)传递")
    assert comp.address_j is gate_j.generator_address, (
        "T-TH-6: address_j 未从进入门(后继方)传递")
    assert comp.address_i is not comp.address_j

    # 自身对（i≡j）必须拒绝
    try:
        PhysicalThetaComparator(
            address_i=comp.address_i, address_j=comp.address_i)
        raise AssertionError("T-TH-6: 自身对 i≡j 应被拒绝")
    except ValueError:
        pass

    print("T-TH-6: 谱系 i←历史核/j←进入门 正确传递；自身对 fail-fast")
    print("✓ T-TH-6 PASS")


def test_th_7_unified_class_and_params():
    """T-TH-7：三站点对同一类同一参数，无站点专属字段/电路复制。"""
    registry = AddressRegistry()
    addr_src = _make_address(registry, SOURCE_SITE)
    comps = []
    for site in TARGET_SITES:
        addr_j = _make_address(registry, site)
        comps.append(PhysicalThetaComparator(address_i=addr_src, address_j=addr_j))

    p0 = (comps[0].theta_h, comps[0].theta_g, comps[0].gm)
    for c in comps[1:]:
        assert type(c) is type(comps[0]), "T-TH-7: 站点对使用了不同类"
        assert (c.theta_h, c.theta_g, c.gm) == p0, (
            "T-TH-7: 站点对参数不一致——统一 Θ 必须共用同一份参数")

    fields = set(vars(comps[0]))
    forbidden = {"site_id", "site_gain", "window_steps", "t_step", "_phase"}
    assert not (fields & forbidden), (
        f"T-TH-7: 发现禁止/站点专属字段 {fields & forbidden}")

    # 同输入 → 同输出（除谱系外无任何站点差异）
    outs = [c.step(0.545, 1.0, DT) for c in comps]
    assert outs[0] == outs[1] == outs[2] > 0.0, (
        f"T-TH-7: 同输入下三站点对输出不一致 {outs}")

    print(f"T-TH-7: 站点对 28≺{TARGET_SITES} 同类同参数(θ_h={p0[0]},"
          f"θ_g={p0[1]},gm={p0[2]})，同输入同输出 {outs[0]:.4f}")
    print("✓ T-TH-7 PASS")


def test_th_8_static_audit():
    """T-TH-8：静态自审计——无软件时钟、无禁止读取（镜像 T-R1C-7）。"""
    sig = inspect.signature(PhysicalThetaComparator.step)
    assert "t_step" not in sig.parameters, (
        "T-TH-8: step() 签名含 t_step ⇒ 引入了软件时钟")

    import tss.relations.theta_comparator as tc_mod
    src = inspect.getsource(tc_mod)
    code_lines = []
    in_doc = False
    for ln in src.splitlines():
        stripped = ln.strip()
        if stripped.startswith('"""') or stripped.endswith('"""'):
            if stripped.count('"""') == 1:
                in_doc = not in_doc
            continue
        if in_doc or stripped.startswith("#"):
            continue
        code_lines.append(ln.split("#")[0])
    code = "\n".join(code_lines)
    for token in ("pre_trace", "Occurrence", "spike_output", "carrier_ref",
                  "_hist_cap", "_gate_cap"):
        assert token not in code, (
            f"T-TH-8: 可执行代码引用禁止对象 {token!r}"
            "——C_Θ 只允许消费 h_i 与 b_j^↑ 两个接口值")

    print("T-TH-8: 签名无 t_step；可执行代码无 pre_trace/Occurrence/"
          "collector/上游内部状态引用")
    print("✓ T-TH-8 PASS")


def test_th_9_real_chain_three_pairs():
    """T-TH-9：真实链路（TSS-3a 场景）——三对正向全产生、镜像全为零。

    单次外部发生 @site28（radius=3.0 覆盖全部目标站点），每对建
    正向比较器 r_{28≺X}（kernel_28 + gate_X）与镜像比较器 r_{X≺28}
    （kernel_X + gate_28）。预期：正向恰在 X 进入步产生（Δt∈窗内），
    镜像全程为零（28 先进入时 X 无历史）。
    """
    circuit = RPrecCircuitT1()
    patch = circuit._thermal_quantum_patches[SOURCE_SITE]
    pos = patch.world_position(circuit.world.body)
    circuit.world.heat_sources = [HeatSource(
        position=list(pos), energy=100000.0, temperature=300.0,
        radius=HEAT_RADIUS, _drift=[0.0, 0.0, 0.0])]

    registry = AddressRegistry()
    sites = [SOURCE_SITE] + list(TARGET_SITES)
    ports, gates, kernels = {}, {}, {}
    for s in sites:
        addr = _make_address(registry, s)
        collector = circuit.thermal_quantum_collectors[f"thermpt{s}_warm"]
        ports[s] = CollectorBoundaryPort(
            generator_address=addr, carrier_ref=collector)
        gates[s] = make_entry_gate(ports[s])
        kernels[s] = make_history_kernel(gates[s])

    fwd = {x: make_theta_comparator(kernels[SOURCE_SITE], gates[x])
           for x in TARGET_SITES}
    mir = {x: make_theta_comparator(kernels[x], gates[SOURCE_SITE])
           for x in TARGET_SITES}

    entry_step = {s: None for s in sites}
    fwd_fire = {x: [] for x in TARGET_SITES}
    for t in range(N_STEPS_REAL):
        circuit.step({}, DT)
        b, h = {}, {}
        for s in sites:
            b[s] = gates[s].step(ports[s].spike_output, DT)
            h[s] = kernels[s].step(b[s], DT)
            if b[s] > 0.5 and entry_step[s] is None:
                entry_step[s] = t
        for x in TARGET_SITES:
            if fwd[x].step(h[SOURCE_SITE], b[x], DT) > 0.0:
                fwd_fire[x].append(t)
            mir[x].step(h[x], b[SOURCE_SITE], DT)

    assert entry_step[SOURCE_SITE] is not None, "T-TH-9 前提：源站点应进入"
    for x in TARGET_SITES:
        assert entry_step[x] is not None, f"T-TH-9 前提：site{x} 应进入"
        dt_x = entry_step[x] - entry_step[SOURCE_SITE]
        assert fwd_fire[x], (
            f"T-TH-9: r_{{28≺{x}}} 未产生（Δt={dt_x}，窗={T_READ}）")
        assert fwd_fire[x][0] == entry_step[x], (
            f"T-TH-9: r_{{28≺{x}}} 首次产生步 {fwd_fire[x][0]} ≠ "
            f"site{x} 进入步 {entry_step[x]}")
        assert 0 < dt_x < T_READ, (
            f"T-TH-9: Δt={dt_x} 不在 (0, {T_READ}) 窗内却产生了关系")
        assert mir[x].relation_count == 0, (
            f"T-TH-9: 镜像 r_{{{x}≺28}} 产生了 {mir[x].relation_count} 次"
            "——28 先进入时 X 不应有历史")

    dts = {x: entry_step[x] - entry_step[SOURCE_SITE] for x in TARGET_SITES}
    print(f"T-TH-9: 源@{entry_step[SOURCE_SITE]}，目标进入 Δt={dts}；"
          f"三对正向恰在进入步产生、三对镜像全零")
    print("✓ T-TH-9 PASS")


def main():
    tests = [
        test_th_1_in_window_order_fires,
        test_th_2_single_input_exact_zero,
        test_th_3_swap_and_simultaneous_no_fire,
        test_th_4_beyond_window_exact_zero,
        test_th_5_blockable_independent_effect,
        test_th_6_lineage_correct,
        test_th_7_unified_class_and_params,
        test_th_8_static_audit,
        test_th_9_real_chain_three_pairs,
    ]
    passed = 0
    for fn in tests:
        print(f"\n{'=' * 68}\n{fn.__name__}\n{'=' * 68}")
        fn()
        passed += 1
    print(f"\n{'=' * 68}\nTSS-M2 统一Θ: {passed}/{len(tests)} PASS\n{'=' * 68}")
    return 0 if passed == len(tests) else 1


if __name__ == "__main__":
    sys.exit(main())
