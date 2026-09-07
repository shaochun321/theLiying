"""tss.tests.test_r1_x2c — P2-B1X2c：局部电流不可约与双链路切断测试。

方案依据：
  document - 2026-08-01T051324.332.md（X2c执行指令）
  document - 2026-08-01T213058.303.md（方案2：L1边界回放隔离A/B条件）

切断方法（实测确认）：
  weight_max=0  → 不切断（m.w不受影响，电流不变）
  synapse_gain=0 → 真正切断（propagate()输出全零）

六个条件：
  ∅        : L1_a=0, L1_b=0
  A        : L1_a=dT_A*, L1_b=0
  B        : L1_a=0,    L1_b=dT_B*
  AℓB      : L1_a=dT_A*, L1_b=dT_B*  （保留A≺B时序差异）
  gen-cut  : AℓB输入 + ℓ_gen中raw_xi_b_to_col的synapse_gain=0
  out-cut  : AℓB输入 + ℓ_out的synapse_gain=0

输出：
  K_R1, K_gen, K_out 和各自 epsilon
  T-X2C-CUT-0  : 切断法验证（synapse_gain=0确实使电流为零）
  T-X2C-ISO-1  : A-only隔离验证
  T-X2C-ISO-2  : B-only隔离验证
  T-X2C-1      : K_R1 > ε_int
  T-X2C-2      : K_gen > ε_gen
  T-X2C-3      : K_out > ε_out
"""

import sys
import math

sys.path.insert(0, '.')

from nexus_v1.components.world import HeatSource
from tss.relations.temporal_r_prec_plastic import RPrecCircuitT1Plastic

DT = 0.001
N_RECORD = 1600   # 用足够长的轨迹确保R1事件出现
_XI_THETA = 0.05  # 隔离验证：激活侧xi需超过该值
_XI_THETA0 = 0.1  # 隔离验证：非激活侧xi需低于该值


# ── 工具函数 ──────────────────────────────────────────────────────────────────

def _find_bundle_idx(bundle_list, label_fragment: str) -> int:
    """在bundle列表里按bundle_id子串查找，返回第一个匹配的索引。"""
    for i, b in enumerate(bundle_list):
        if label_fragment in b.config.bundle_id:
            return i
    raise ValueError(f"找不到含'{label_fragment}'的bundle")


def _make_circuit():
    """构造新鲜的RPrecCircuitT1Plastic，热源清空（回放模式不用World热源）。"""
    c = RPrecCircuitT1Plastic()
    c.world.heat_sources = []
    return c


def _bundle_indices(circuit):
    """返回两个目标站点(site_a, site_b) warm通路的三组bundle索引。"""
    sa, sb = circuit.rprec_site_a, circuit.rprec_site_b
    la, lb = f"thermpt{sa}_warm", f"thermpt{sb}_warm"
    ia = _find_bundle_idx(circuit.bundles_thermal_quantum_l1_to_hc, la)
    ib = _find_bundle_idx(circuit.bundles_thermal_quantum_l1_to_hc, lb)
    # l1_to_hc / in / collect 三个列表对同一站点保持相同索引（构造顺序一致）
    return ia, ib


def _step_site(circuit, site_index: int, bundle_idx: int, dT: float):
    """手动驱动单个站点的L1→HC→ensemble→collector链路。

    不调用circuit.step()（那会用HeatSource+全量World物理），
    只驱动目标站点自己的三级bundle，保证其他站点不受影响。
    """
    pid = f"thermpt{site_index}"
    l1 = circuit.thermal_quantum_l1_warm[pid]
    l1.step(dT, DT)

    b_l1hc = circuit.bundles_thermal_quantum_l1_to_hc[bundle_idx]
    b_in   = circuit.bundles_thermal_quantum_in[bundle_idx]
    b_col  = circuit.bundles_thermal_quantum_collect[bundle_idx]

    hc = b_l1hc.targets[0]
    hc.step((b_l1hc.propagate() or [0.0])[0], DT)

    ensemble = b_in.targets
    currents_in = b_in.propagate()
    for k, n in enumerate(ensemble):
        n.step(currents_in[k] if k < len(currents_in) else 0.0, DT)

    collector = b_col.targets[0]
    currents_col = b_col.propagate()
    collector.step((currents_col or [0.0])[0], DT)


# ── Phase 0：录制真实dT轨迹 ───────────────────────────────────────────────────

def _record_dt_trajectories():
    """用P2-B1X1d的HeatSource参数（热源放A，T=300）录制真实dT序列。

    返回 (dt_a_traj, dt_b_traj)：与N_RECORD等长的列表，
    每步包含 patch.sample() 在circuit.step() 之前读取的dT值。
    """
    c = _make_circuit()
    c = RPrecCircuitT1Plastic()  # 需要有World，重建
    sa, sb = c.rprec_site_a, c.rprec_site_b
    patch_a = c._thermal_quantum_patches[sa]
    patch_b = c._thermal_quantum_patches[sb]
    heat_pos = patch_a.world_position(c.world.body)
    c.world.heat_sources = [HeatSource(
        position=list(heat_pos), energy=100000.0,
        temperature=300.0, radius=5.0, _drift=[0.0, 0.0, 0.0],
    )]

    dt_a, dt_b = [], []
    for _ in range(N_RECORD):
        _, dT_a = patch_a.sample(c.world, c.world.body, DT)
        _, dT_b = patch_b.sample(c.world, c.world.body, DT)
        dt_a.append(dT_a)
        dt_b.append(dT_b)
        c.step({}, DT)
        c.step_rprec(DT)

    return dt_a, dt_b


# ── Phase 1：运行单个条件 ─────────────────────────────────────────────────────

def _run_condition(dt_a_traj, dt_b_traj,
                   cut_gen_bundle_id: str = None,
                   cut_out: bool = False):
    """用边界回放驱动，返回N_RECORD步的Y轨迹（ℓ_out局部电流，取目标DA节点0的值）。

    dt_a_traj/dt_b_traj: 每步喂给L1_a/L1_b的dT值（某一方可以全零构造隔离）。
    cut_gen_bundle_id:  若非None，切断ℓ_gen内该bundle_id对应bundle的synapse_gain
    cut_out:            若True，切断ℓ_out（bundle_rprec_to_da.config.synapse_gain=0）
    """
    circuit = _make_circuit()
    sa, sb = circuit.rprec_site_a, circuit.rprec_site_b
    ia, ib = _bundle_indices(circuit)
    l1_a = circuit.thermal_quantum_l1_warm[f"thermpt{sa}"]
    l1_b = circuit.thermal_quantum_l1_warm[f"thermpt{sb}"]

    if cut_gen_bundle_id:
        # 在rprec_relation_bundles()里找对应bundle
        for b in circuit.rprec_relation_bundles():
            if b.config.bundle_id == cut_gen_bundle_id:
                b.config.synapse_gain = 0.0
                break

    if cut_out:
        circuit.bundle_rprec_to_da.config.synapse_gain = 0.0

    Y_traj = []
    xi_a_max = 0.0
    xi_b_max = 0.0
    for t in range(N_RECORD):
        dT_a = dt_a_traj[t] if t < len(dt_a_traj) else 0.0
        dT_b = dt_b_traj[t] if t < len(dt_b_traj) else 0.0

        _step_site(circuit, sa, ia, dT_a)
        _step_site(circuit, sb, ib, dT_b)
        circuit.step_rprec(DT)

        xi_a_max = max(xi_a_max, circuit.rprec_xi_a.pre_trace)
        xi_b_max = max(xi_b_max, circuit.rprec_xi_b.pre_trace)

        Y_curr = circuit.bundle_rprec_to_da.propagate()
        Y_traj.append(Y_curr[0] if Y_curr else 0.0)

    circuit._x2c_xi_a_max = xi_a_max
    circuit._x2c_xi_b_max = xi_b_max
    return Y_traj, circuit


def _l2_norm(traj):
    return math.sqrt(sum(y ** 2 for y in traj))


# ── 测试 ──────────────────────────────────────────────────────────────────────

def test_x2c_cut_0_cut_method():
    """T-X2C-CUT-0：切断方法验证——synapse_gain=0使ℓ_out输出全零。

    直接实测：正常权重有非零电流；设置synapse_gain=0后立即归零。
    """
    c = RPrecCircuitT1Plastic()
    bundle = c.bundle_rprec_to_da
    c.rprec_collector_a_prec_b_fast.pre_trace = 0.5

    currents_before = bundle.propagate()
    assert max(abs(x) for x in currents_before) > 1e-6, (
        "正常权重下应有非零电流（切断验证前提）")

    bundle.config.synapse_gain = 0.0
    currents_after = bundle.propagate()
    assert max(abs(x) for x in currents_after) < 1e-12, (
        f"synapse_gain=0后电流应为0，实际: {currents_after}")

    print(f"T-X2C-CUT-0: before={[round(x,6) for x in currents_before]}, "
          f"after={currents_after}")
    print("✓ T-X2C-CUT-0 PASS: synapse_gain=0真正切断ℓ_out电流")


# FIX(2026-09-06, 外部实测反馈清单 §2): 原名 test_x2c_iso_1/2 带轨迹参数,
# pytest 收集时会把 dt_a_traj/dt_b_traj 误当 fixture 报 ERROR。它们本就由
# run() 驱动(先录制轨迹再传入),按反馈方案 B 改为 _ 前缀 helper——
# 实验逻辑零改动,pytest 收集恢复干净,run() 入口行为不变。
def _x2c_iso_1_a_only(dt_a_traj, dt_b_traj):
    """T-X2C-ISO-1：A-only隔离——只喂dT_A*，L1_b=0。
    验证 max_xi_a > θ, max_xi_b <= θ_0。
    """
    zeros = [0.0] * N_RECORD
    _, circuit = _run_condition(dt_a_traj, zeros)
    xi_a_max = circuit._x2c_xi_a_max
    xi_b_max = circuit._x2c_xi_b_max

    print(f"T-X2C-ISO-1 A-only: xi_a_max={xi_a_max:.4f}, xi_b_max={xi_b_max:.4f}")
    assert xi_a_max > _XI_THETA, (
        f"A-only: κ_A的collector应激活(>{_XI_THETA})，实际xi_a={xi_a_max:.4f}")
    assert xi_b_max < _XI_THETA0, (
        f"A-only: κ_B的collector应接近零(<{_XI_THETA0})，实际xi_b={xi_b_max:.4f}")
    print("✓ T-X2C-ISO-1 PASS: A-only隔离验证通过")


def _x2c_iso_2_b_only(dt_a_traj, dt_b_traj):
    """T-X2C-ISO-2：B-only隔离——只喂dT_B*，L1_a=0。
    验证 max_xi_b > θ, max_xi_a <= θ_0。
    """
    zeros = [0.0] * N_RECORD
    _, circuit = _run_condition(zeros, dt_b_traj)
    xi_a_max = circuit._x2c_xi_a_max
    xi_b_max = circuit._x2c_xi_b_max

    print(f"T-X2C-ISO-2 B-only: xi_a_max={xi_a_max:.4f}, xi_b_max={xi_b_max:.4f}")
    assert xi_b_max > _XI_THETA, (
        f"B-only: κ_B的collector应激活(>{_XI_THETA})，实际xi_b={xi_b_max:.4f}")
    assert xi_a_max < _XI_THETA0, (
        f"B-only: κ_A的collector应接近零(<{_XI_THETA0})，实际xi_a={xi_a_max:.4f}")
    print("✓ T-X2C-ISO-2 PASS: B-only隔离验证通过")


def run_x2c(dt_a_traj, dt_b_traj):
    """T-X2C-1/2/3：六条件K_R1/K_gen/K_out不可约与切断测试。"""
    zeros = [0.0] * N_RECORD

    print("运行六条件（每条件约1600步）...")
    Y_empty, _ = _run_condition(zeros, zeros)
    Y_a, _     = _run_condition(dt_a_traj, zeros)
    Y_b, _     = _run_condition(zeros, dt_b_traj)
    Y_alb, _   = _run_condition(dt_a_traj, dt_b_traj)
    Y_gen_cut, _ = _run_condition(dt_a_traj, dt_b_traj,
                                   cut_gen_bundle_id="rprec_raw_xi_b_to_col_fast")
    Y_out_cut, _ = _run_condition(dt_a_traj, dt_b_traj, cut_out=True)

    # K_R1 = ||Y_AℓB - Y_A - Y_B + Y_∅||_2
    kappa = [Y_alb[t] - Y_a[t] - Y_b[t] + Y_empty[t] for t in range(N_RECORD)]
    K_R1 = _l2_norm(kappa)

    K_gen = _l2_norm([Y_alb[t] - Y_gen_cut[t] for t in range(N_RECORD)])
    K_out = _l2_norm([Y_alb[t] - Y_out_cut[t] for t in range(N_RECORD)])

    # ε由空条件自然波动估计
    eps_int = _l2_norm(Y_empty) * 3 + 1e-10
    eps_gen = eps_int
    eps_out = eps_int

    print(f"\n  Y_∅  norm = {_l2_norm(Y_empty):.6f}")
    print(f"  Y_A  norm = {_l2_norm(Y_a):.6f}")
    print(f"  Y_B  norm = {_l2_norm(Y_b):.6f}")
    print(f"  Y_AℓB norm = {_l2_norm(Y_alb):.6f}")
    print(f"\n  K_R1 = {K_R1:.6f}  (ε_int={eps_int:.6f}) → {'PASS' if K_R1 > eps_int else 'FAIL'}")
    print(f"  K_gen = {K_gen:.6f} (ε_gen={eps_gen:.6f}) → {'PASS' if K_gen > eps_gen else 'FAIL'}")
    print(f"  K_out = {K_out:.6f} (ε_out={eps_out:.6f}) → {'PASS' if K_out > eps_out else 'FAIL'}")

    assert K_R1 > eps_int, f"T-X2C-1 FAIL: K_R1={K_R1:.6f} <= eps_int={eps_int:.6f}"
    print("✓ T-X2C-1 PASS: K_R1 > ε_int（组合产生不可加和的额外作用）")

    assert K_gen > eps_gen, f"T-X2C-2 FAIL: K_gen={K_gen:.6f} <= eps_gen={eps_gen:.6f}"
    print("✓ T-X2C-2 PASS: K_gen > ε_gen（作用依赖关系生成链路）")

    assert K_out > eps_out, f"T-X2C-3 FAIL: K_out={K_out:.6f} <= eps_out={eps_out:.6f}"
    print("✓ T-X2C-3 PASS: K_out > ε_out（出口链路确实传递作用）")

    return K_R1, K_gen, K_out, eps_int


def run():
    test_x2c_cut_0_cut_method()

    print("\n录制真实dT轨迹...")
    dt_a_traj, dt_b_traj = _record_dt_trajectories()
    print(f"  max(dT_A*)={max(dt_a_traj):.4f}, max(dT_B*)={max(dt_b_traj):.4f}")

    print("\n隔离验证...")
    _x2c_iso_1_a_only(dt_a_traj, dt_b_traj)
    _x2c_iso_2_b_only(dt_a_traj, dt_b_traj)

    print("\nX2c六条件实验...")
    K_R1, K_gen, K_out, eps = run_x2c(dt_a_traj, dt_b_traj)

    print()
    print("=" * 60)
    print("T-X2C ALL PASS")
    print(f"  K_R1={K_R1:.4f}, K_gen={K_gen:.4f}, K_out={K_out:.4f}, ε={eps:.4f}")
    print("=" * 60)


if __name__ == "__main__":
    run()
