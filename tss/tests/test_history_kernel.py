"""tss.tests.test_history_kernel — TSS-R1c(M1)：PhysicalHistoryKernel 八项资格测试。

TYPE:INFRA

路线依据：08_下一阶段路线图.md §3 T-2（M1 最低结构 7 条 + 停止条件）；
用户裁定 2026-09-06（范围=M1+M2）。参数推导见 history_kernel.py 模块 Q3
（TSS-3a 2026-09-06 重跑实测：稳定站点对 Δt∈[258,364]，τ_h 复用 slow=600 步）。

八项资格（对齐路线图 7 条最低结构，逐条守卫）：
  T-R1C-1：单 b^↑ 单次充电，时程与电容物理解析解吻合；返回值为充电前
           历史（严格先序读出）
  T-R1C-2：门关窗内重复原始 spike 不重复充电（真实 PhysicalEntryGate 集成；
           路线图停止条件"H_τ 被重复 spike 重复充电=绕过 E^↑"的反向守卫）
  T-R1C-3：多站点同参数同输入行为一致，无站点专属字段
  T-R1C-4：窗口内可读（Δt=364 处 h>θ_h）、窗口外自然失效（>t_read 后
           h<θ_h），无软件清零
  T-R1C-5：物理账本局部一致（注入-泄漏=存量，Capacitor 内建 KCL），
           不宣称全局闭合
  T-R1C-6：输入 fail-fast（仅接受 0.0/1.0）+ 最小间隔脉冲序列下电压
           自然有界（无钳位的合法性守卫）
  T-R1C-7：无软件时钟/禁止字段/禁止读取（静态自审计，镜像 T-R1B-1/9）
  T-R1C-8：真实链路集成 port→gate→kernel，charge_count == entry_count
"""
import sys
sys.path.insert(0, '.')

import inspect
import math

from nexus_v1.components.structural_address import (
    AddressRegistry, DOMAIN_SKIN_PATCH, DOMAIN_OCC_THERMAL,
)
from nexus_v1.components.world import HeatSource
from tss.relations.boundary_process import CollectorBoundaryPort
from tss.relations.entry_gate import PhysicalEntryGate, make_entry_gate
from tss.relations.history_kernel import (
    PhysicalHistoryKernel, make_history_kernel,
    _DEFAULT_R_LEAK, _DEFAULT_CAPACITANCE,
)
from tss.relations.temporal_r_prec import RPrecCircuitT1

DT = 0.001
THETA_H = 0.3            # 下游 C_Θ 读取阈值 = MOSFET 默认 v_threshold
                         # （semiconductor.py:130，同 entry_gate θ_g 来源）
TAU_H = _DEFAULT_R_LEAK * _DEFAULT_CAPACITANCE      # 0.6 s = 600 步
MAX_STABLE_DT = 364      # TSS-3a 实测最大稳定 Δt（28≺21 上界）
EXIT_GAP_MIN = 4257      # EXP-R1A-01 真实退出间隔下界（步）
T_OPEN_STEPS = 1204      # entry_gate Q3：b^↑ 最小间隔（E^↑ 物理保证）


def _make_address(registry: AddressRegistry, site: int):
    pid = f"thermpt{site}"
    label = f"{pid}_warm"
    parent_addr = registry.register_physical(DOMAIN_SKIN_PATCH, pid)
    return registry.register_generated(DOMAIN_OCC_THERMAL, label, (parent_addr,), 1)


def _fresh_kernel(site: int = 28) -> PhysicalHistoryKernel:
    """构造一个独立历史核（不需要电路——核只吃 b^↑ 序列）。"""
    registry = AddressRegistry()
    addr = _make_address(registry, site)
    return PhysicalHistoryKernel(generator_address=addr)


def _make_circuit_with_heat(site: int = 28):
    circuit = RPrecCircuitT1()
    patch = circuit._thermal_quantum_patches[site]
    pos = patch.world_position(circuit.world.body)
    circuit.world.heat_sources = [HeatSource(
        position=list(pos), energy=100000.0, temperature=300.0,
        radius=5.0, _drift=[0.0, 0.0, 0.0])]
    return circuit


def test_r1c_1_single_pulse_physics():
    """T-R1C-1：单 b^↑ 单次充电；时程=电容解析解；返回值为充电前历史。"""
    k = _fresh_kernel()

    # 充电步：返回值必须是充电**前**的历史（此处为 0——严格先序读出）
    h_at_entry = k.step(1.0, DT)
    assert h_at_entry == 0.0, (
        f"T-R1C-1: 充电步返回值应为充电前历史 0.0，得到 {h_at_entry}"
        "——若返回充电后值，同步进入会污染严格先序")
    assert k.charge_count == 1
    v0 = k.history_voltage
    assert abs(v0 - 1.0) < 1e-9, f"T-R1C-1: 单枚 b^↑ 应充至 1.0，得到 {v0}"

    # 衰减时程：h(n) = v0·e^{-n·dt/τ}（leak 逐步复利=精确指数）
    for n in (1, 100, 364, 600):
        kk = _fresh_kernel()
        kk.step(1.0, DT)
        h = None
        for _ in range(n):
            h = kk.step(0.0, DT)
        expected = 1.0 * math.exp(-n * DT / TAU_H)
        assert abs(h - expected) < 1e-6, (
            f"T-R1C-1: n={n} 实测 h={h:.8f} vs 解析 {expected:.8f}")
        assert kk.charge_count == 1, "T-R1C-1: 无 b^↑ 的步不得充电"

    print(f"T-R1C-1: 充电前读出=0.0；n=1/100/364/600 步衰减与 e^(-n·dt/τ) "
          f"吻合(τ={TAU_H}s)，单 b^↑ 恰好一次充电")
    print("✓ T-R1C-1 PASS")


def test_r1c_2_gate_dedup_no_recharge():
    """T-R1C-2：门关窗内重复 spike 不使 H_τ 重复充电（停止条件反向守卫）。

    构造密集 spike 簇（间隔 100 步 < t_open=1204），经真实 PhysicalEntryGate
    过滤后喂核：只有首枚产生 b^↑，核只充电一次，其后电压严格单调衰减。
    """
    registry = AddressRegistry()
    addr = _make_address(registry, 28)
    gate = PhysicalEntryGate(generator_address=addr)
    kernel = PhysicalHistoryKernel(generator_address=addr)

    n_steps = 2000
    spike_every = 100    # 簇内密集重复 spike（≪ t_open）
    voltages = []
    for t in range(n_steps):
        s = 1.0 if t % spike_every == 0 else 0.0
        b_up = gate.step(s, DT)
        kernel.step(b_up, DT)
        voltages.append(kernel.history_voltage)

    assert gate.entry_count == 1, (
        f"T-R1C-2 前提：密集簇应只产生 1 次 b^↑，实际 {gate.entry_count}")
    assert kernel.charge_count == 1, (
        f"T-R1C-2: 核应只充电 1 次，实际 {kernel.charge_count}"
        "——重复充电说明绕过了 E^↑（路线图停止条件）")
    # 充电后电压严格单调不增（重复 spike 不得抬升历史）
    after = voltages[1:]
    assert all(b <= a for a, b in zip(after, after[1:])), (
        "T-R1C-2: 充电后历史电压应单调衰减，出现抬升 ⇒ 有 spike 绕过门充电")

    print(f"T-R1C-2: {n_steps} 步内 {n_steps // spike_every} 枚密集 spike → "
          f"b^↑={gate.entry_count} 次，核充电 {kernel.charge_count} 次，"
          f"其后单调衰减")
    print("✓ T-R1C-2 PASS")


def test_r1c_3_cross_site_same_params():
    """T-R1C-3：多站点同参数同输入 → 行为逐点一致；无站点专属字段。"""
    sites = (28, 15, 21, 24)   # 源 + TSS-3a 三个稳定目标站点
    kernels = [_fresh_kernel(s) for s in sites]

    # 参数一致（同一份模块默认值）
    for k in kernels[1:]:
        assert (k.capacitance, k.r_leak, k.q_pulse) == (
            kernels[0].capacitance, kernels[0].r_leak, kernels[0].q_pulse), (
            "T-R1C-3: 站点间参数不一致——多站点必须共用同一份参数")

    # 同输入序列 → 电压轨迹逐点一致
    seq = [1.0] + [0.0] * 500 + [1.0 if i == 800 else 0.0 for i in range(1300)]
    trajs = []
    for k in kernels:
        traj = [k.step(b, DT) for b in seq]
        trajs.append(traj)
    for traj in trajs[1:]:
        assert traj == trajs[0], (
            "T-R1C-3: 同输入下不同站点轨迹不一致 ⇒ 存在站点专属状态")

    # 字段自审计：无站点专属/增益字段（地址仅谱系用）
    field_names = {f for f in vars(kernels[0])}
    forbidden = {"site_id", "site_gain", "gain", "_site"}
    assert not (field_names & forbidden), (
        f"T-R1C-3: 发现站点专属字段 {field_names & forbidden}")

    print(f"T-R1C-3: 站点 {sites} 同参数，{len(seq)} 步同输入轨迹逐点一致")
    print("✓ T-R1C-3 PASS")


def test_r1c_4_window_readable_then_expires():
    """T-R1C-4：窗口内可读、窗口外自然失效（θ_h=0.3，无软件清零）。

    资格不等式（history_kernel.py Q3）：
      h(MAX_STABLE_DT=364) = e^{-0.364/0.6} ≈ 0.545 > 0.3   目标对可读
      h(EXIT_GAP_MIN=4257) = e^{-4.257/0.6} ≈ 8.3e-4 < 0.3  独立发生不桥接
    """
    k = _fresh_kernel()
    k.step(1.0, DT)

    h = None
    crossed_at = None
    for n in range(1, EXIT_GAP_MIN + 1):
        h = k.step(0.0, DT)
        if crossed_at is None and h < THETA_H:
            crossed_at = n

    # 理论过阈步数 t_read = τ·ln(1/θ_h)
    t_read = int(math.ceil(TAU_H * math.log(1.0 / THETA_H) / DT))
    assert crossed_at is not None, "T-R1C-4: 历史从不失效 ⇒ 泄漏未生效"
    assert abs(crossed_at - t_read) <= 1, (
        f"T-R1C-4: 实测过阈步数 {crossed_at} 与解析 t_read={t_read} 不符")
    assert crossed_at > MAX_STABLE_DT, (
        f"T-R1C-4: 可读窗 {crossed_at} 步未覆盖最大稳定 Δt={MAX_STABLE_DT}"
        "——M2 目标对将不可读")
    assert h < THETA_H, (
        f"T-R1C-4: 真实退出间隔 {EXIT_GAP_MIN} 步处 h={h} 仍可读"
        "——会桥接两次独立外部发生")

    # 无任何清零/复位方法暴露
    resetters = [m for m in dir(k) if "reset" in m.lower() or "clear" in m.lower()]
    assert not resetters, f"T-R1C-4: 发现软件清零接口 {resetters}"

    print(f"T-R1C-4: 可读窗实测 {crossed_at} 步（解析 {t_read}），"
          f"覆盖 Δt=364(h=0.545)，{EXIT_GAP_MIN} 步处 h={h:.2e}<0.3")
    print("✓ T-R1C-4 PASS")


def test_r1c_5_ledger_local_consistency():
    """T-R1C-5：物理账本局部一致——注入-泄漏=存量（Capacitor 内建 KCL）。"""
    k = _fresh_kernel()
    seq = [1.0] + [0.0] * 1500 + [1.0] + [0.0] * 800
    for b in seq:
        k.step(b, DT)

    stored = k.history_voltage * k.capacitance
    balance = k.injected_charge - k.leaked_charge
    assert abs(balance - stored) < 1e-9, (
        f"T-R1C-5: KCL 不闭合——注入{k.injected_charge:.6f} - "
        f"泄漏{k.leaked_charge:.6f} = {balance:.6f} ≠ 存量 {stored:.6f}")
    assert abs(k.injected_charge - 2.0) < 1e-9, (
        f"T-R1C-5: 两枚 b^↑ 应注入 2.0，实际 {k.injected_charge}")

    print(f"T-R1C-5: 注入 {k.injected_charge:.4f} - 泄漏 {k.leaked_charge:.4f} "
          f"= 存量 {stored:.6f}（局部 KCL 闭合；全局守恒 D-06 不在此宣称）")
    print("✓ T-R1C-5 PASS")


def test_r1c_6_failfast_and_natural_bound():
    """T-R1C-6：输入 fail-fast + 最小间隔脉冲下电压自然有界（无钳位合法性）。"""
    k = _fresh_kernel()
    for bad in (0.5, -1.0, 2.0, 0.999, 1e-9):
        try:
            k.step(bad, DT)
            raise AssertionError(
                f"T-R1C-6: b_up={bad!r} 应被拒绝（输入只来自 E^↑ 的 0/1 脉冲）")
        except ValueError:
            pass

    # 自然有界：以 E^↑ 允许的最小间隔 t_open 连续供给 b^↑，
    # 峰值电压收敛于几何级数上界 1/(1-e^{-t_open/τ})，不发散
    bound = 1.0 / (1.0 - math.exp(-T_OPEN_STEPS * DT / TAU_H))
    k2 = _fresh_kernel()
    peak = 0.0
    for pulse in range(12):
        k2.step(1.0, DT)
        peak = max(peak, k2.history_voltage)
        for _ in range(T_OPEN_STEPS - 1):
            k2.step(0.0, DT)
    assert peak <= bound + 1e-9, (
        f"T-R1C-6: 峰值 {peak:.6f} 超出几何级数上界 {bound:.6f}"
        "——无钳位的前提失效（检查 E^↑ 的 t_open 是否被缩短）")

    print(f"T-R1C-6: 5 类非法输入全部 fail-fast；12 枚最小间隔 b^↑ 峰值 "
          f"{peak:.4f} ≤ 上界 {bound:.4f}，自然有界成立")
    print("✓ T-R1C-6 PASS")


def test_r1c_7_no_clock_no_forbidden():
    """T-R1C-7：无软件时钟 + 禁止字段/禁止读取的静态自审计（镜像 T-R1B-1/9）。"""
    sig = inspect.signature(PhysicalHistoryKernel.step)
    assert "t_step" not in sig.parameters, (
        "T-R1C-7: step() 签名含 t_step ⇒ 引入了软件时钟")

    k = _fresh_kernel()
    fields = set(vars(k))
    forbidden_fields = {"_phase", "_silence_count", "t_step", "gap_steps",
                        "rearm_min_steps", "site_id"}
    assert not (fields & forbidden_fields), (
        f"T-R1C-7: 发现禁止字段 {fields & forbidden_fields}")

    import tss.relations.history_kernel as hk_mod
    src = inspect.getsource(hk_mod)
    code_lines = []
    in_doc = False
    for ln in src.splitlines():
        stripped = ln.strip()
        if stripped.startswith('"""') or stripped.endswith('"""'):
            n_quotes = stripped.count('"""')
            if n_quotes == 1:
                in_doc = not in_doc
            continue
        if in_doc or stripped.startswith("#"):
            continue
        code_lines.append(ln.split("#")[0])
    code = "\n".join(code_lines)
    for token in ("pre_trace", "Occurrence", "EntryBoundaryDetector",
                  "_w_adapt", "spike_output"):
        assert token not in code, (
            f"T-R1C-7: 可执行代码引用禁止对象 {token!r}"
            "——H_τ 只允许消费 b^↑")

    print("T-R1C-7: 签名无 t_step；无禁止字段；可执行代码无 pre_trace/"
          "Occurrence/spike_output 等禁止引用")
    print("✓ T-R1C-7 PASS")


def test_r1c_8_real_chain_integration():
    """T-R1C-8：真实链路 collector→port→gate→kernel，充电与进入一一对应。"""
    circuit = _make_circuit_with_heat(28)
    registry = AddressRegistry()
    addr = _make_address(registry, 28)
    collector = circuit.thermal_quantum_collectors["thermpt28_warm"]
    port = CollectorBoundaryPort(generator_address=addr, carrier_ref=collector)
    gate = make_entry_gate(port)
    kernel = make_history_kernel(gate)

    n_steps = 8000
    charge_steps = []
    for t in range(n_steps):
        circuit.step({}, DT)
        b_up = gate.step(port.spike_output, DT)
        kernel.step(b_up, DT)
        if b_up > 0.5:
            charge_steps.append(t)

    assert gate.entry_count >= 1, (
        "T-R1C-8 前提：真实驱动下应至少发生一次进入（检查热源/电路）")
    assert kernel.charge_count == gate.entry_count, (
        f"T-R1C-8: 核充电 {kernel.charge_count} 次 ≠ 门进入 {gate.entry_count} 次"
        "——存在绕过 b^↑ 的充电或丢失的进入")
    # 谱系一致：核地址来自门地址（make_history_kernel 只取地址）
    assert kernel.generator_address is gate.generator_address, (
        "T-R1C-8: 谱系地址未从门传递")

    print(f"T-R1C-8: 真实链路 {n_steps} 步，进入 {gate.entry_count} 次"
          f"（步 {charge_steps}），核充电 {kernel.charge_count} 次，一一对应")
    print("✓ T-R1C-8 PASS")


def main():
    tests = [
        test_r1c_1_single_pulse_physics,
        test_r1c_2_gate_dedup_no_recharge,
        test_r1c_3_cross_site_same_params,
        test_r1c_4_window_readable_then_expires,
        test_r1c_5_ledger_local_consistency,
        test_r1c_6_failfast_and_natural_bound,
        test_r1c_7_no_clock_no_forbidden,
        test_r1c_8_real_chain_integration,
    ]
    passed = 0
    for fn in tests:
        print(f"\n{'=' * 68}\n{fn.__name__}\n{'=' * 68}")
        fn()
        passed += 1
    print(f"\n{'=' * 68}\nTSS-R1c(M1): {passed}/{len(tests)} PASS\n{'=' * 68}")
    return 0 if passed == len(tests) else 1


if __name__ == "__main__":
    sys.exit(main())
