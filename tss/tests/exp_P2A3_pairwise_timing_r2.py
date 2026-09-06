"""tss.tests.exp_P2A3_pairwise_timing_r2 — P2-A3 二轮：消除建立瞬态后的
近零区时序分辨率校正。

评判依据：`cell-cell/交叉比对/document - 2026-07-28T143257.082.md`「P2-A3
二轮只补三个实验」。

**首轮遗留问题的核实结论（本轮据此设计，见对话记录/工作报告）**：
评判指出首轮 `Δt_ext=-5` 处的"反转"可能只是约6步固定通道偏置的产物，不能
证明5步不可分辨。进一步核实发现该偏置模型本身不完整——真正存在两层混淆：

  1. **建立瞬态**（本轮新发现，评判未提及）：单独驱动生成元时，其固有
     启动延迟 L 本身随"驱动前空转时长 idle_steps"单调漂移（idle=0→L=673，
     idle=1000→L=692，idle=3000→L=712），与另一个生成元是否存在无关。
     这条曲线精确预测了首轮17组扫描里全部L_i观测值（零残差）。
  2. **站点固有偏移**（评判提出的部分，已用"两站点各自从idle=0独立测"的
     方式验证坐实）：剔除建立瞬态后，站点31比站点28恒定慢6步，与wrap顺序
     /j是否存在都无关——这才是真正的通道固有延迟差 δ_ij^0。

评判「实验一：零间隔偏置标定」原本要求交换生成元/输入角色来判断偏置来源。
本轮改用更直接的方式验证同一问题（单独测两个站点、比较其独立L值），结论
一致（偏置来自站点身份，非调度artifact），故不重复交换角色实验。

**二轮设计**：让两个生成元先各自独立预热 `PRE_IDLE_STEPS` 步（此时L已进入
稳定平台段，见 `measure_settling_plateau()`），以此预热完成时刻为新零点，
再施加评判要求的近零 `Δt_ext` 扫描集合。此时 L_i/L_j 应接近常数，可以安全
地用常数 δ_ij^0 做偏置校正，避免建立瞬态本身的漂移混入近零区判断。

RULES.md 强制三问：
  Q1/Q2：与 `exp_P2A3_pairwise_timing.py` 同一套 BIO/结构依据（双感受野
     时序分辨率范式，复用 wrap_base_generator + last_transitions，不新建
     Neuron/Bundle）。本文件只是同一实验的二轮迭代，不引入新结构。
  Q3：PRE_IDLE_STEPS=2000 直接复用首轮 idle 扫描已测得的"L进入691~699平台
     段"的经验拐点（见 `exp_P2A3_pairwise_timing.py` 站点单独驱动的idle
     曲线数据，本文件 measure_settling_plateau() 重新测量确认）。η_ij
     不预先指定，由 measure_settling_plateau() 的平台段残余波动实测确定。
"""
import sys

sys.path.insert(0, '.')

from nexus_v1.circuit.variant_adapter import VariantCircuit
from nexus_v1.components.structural_address import AddressRegistry
from nexus_v1.components.skin_three_point import (
    TEST_KAPPA_THREE_POINT, TEST_R_LEAK_AMBIENT_THREE_POINT,
    build_three_point_skin,
)
from tss.generators import wrap_base_generator, REFERENCE_TRANSDUCTION_CONFIG
from tss.relations import FROZEN_THERMAL_SITES

DT = 0.001
CONFIG = REFERENCE_TRANSDUCTION_CONFIG
SITE_I = FROZEN_THERMAL_SITES["t1_pair"]["a"]  # 28
SITE_J = FROZEN_THERMAL_SITES["t1_pair"]["b"]  # 31

DRIVE_STEPS = 900
# 首轮idle扫描显示idle>=1000后L进入691~699平台段（见模块docstring）；
# 2000留出充分余量确认已进入平台。
PRE_IDLE_STEPS = 2000

# 评判「实验二：校正后扫描近零区」要求的扫描集合。
DELTA_SWEEP_NEAR_ZERO = [-10, -8, -6, -5, -4, -2, -1, 0, 1, 2, 4, 5, 6, 8, 10]


def fresh_skin():
    return build_three_point_skin(
        kappa=TEST_KAPPA_THREE_POINT, r_leak_ambient=TEST_R_LEAK_AMBIENT_THREE_POINT)


def _find_t_up(handle, graph, start, total):
    t_up = None
    for t in range(total):
        inj = {0: 1.0} if start <= t < start + DRIVE_STEPS else {}
        graph.step(dt=1.0, external_injections=inj)
        q = graph.cells[0].temperature
        handle.tick_from_skin(q, CONFIG, DT, t)
        for ev in handle.closure.last_transitions:
            if ev.kind == "up" and t_up is None:
                t_up = ev.t_step
    return t_up


def measure_settling_plateau(site_index: int, idle_points=None):
    """单独驱动一个生成元，在多个相邻 idle_steps 点测 L=t_up-idle_steps，
    用于①确认已进入平台段（相邻点L差远小于6步站点偏置）②取残余波动幅度
    作为 η_ij 候选来源（评判「实验三」要求 η_ij 从已有合法条件变化中取得，
    不能人为指定）。
    """
    if idle_points is None:
        idle_points = [1800, 1900, 2000, 2100, 2200]
    results = {}
    for idle in idle_points:
        circuit = VariantCircuit()
        registry = AddressRegistry()
        h = wrap_base_generator(circuit, site_index, registry, polarity="warm")
        g = fresh_skin()
        t_up = _find_t_up(h, g, idle, idle + 2000)
        results[idle] = t_up - idle
    return results


def run_trial_r2(delta_t_ext: int):
    """两生成元各自先独立预热 PRE_IDLE_STEPS 步，再以此为新零点施加
    delta_t_ext 偏移驱动 DRIVE_STEPS 步。返回 (t_up_i, t_up_j)（相对
    全局绝对 t，未减去 PRE_IDLE_STEPS）。"""
    circuit = VariantCircuit()
    registry = AddressRegistry()
    hi = wrap_base_generator(circuit, SITE_I, registry, polarity="warm")
    hj = wrap_base_generator(circuit, SITE_J, registry, polarity="warm")
    gi, gj = fresh_skin(), fresh_skin()

    if delta_t_ext >= 0:
        i_start, j_start = PRE_IDLE_STEPS, PRE_IDLE_STEPS + delta_t_ext
    else:
        i_start, j_start = PRE_IDLE_STEPS - delta_t_ext, PRE_IDLE_STEPS
    total = max(i_start, j_start) + DRIVE_STEPS + 4000

    t_up_i, t_up_j = None, None
    for t in range(total):
        inj_i = {0: 1.0} if i_start <= t < i_start + DRIVE_STEPS else {}
        inj_j = {0: 1.0} if j_start <= t < j_start + DRIVE_STEPS else {}
        gi.step(dt=1.0, external_injections=inj_i)
        gj.step(dt=1.0, external_injections=inj_j)
        hi.tick_from_skin(gi.cells[0].temperature, CONFIG, DT, t)
        hj.tick_from_skin(gj.cells[0].temperature, CONFIG, DT, t)
        if t_up_i is None:
            for ev in hi.closure.last_transitions:
                if ev.kind == "up":
                    t_up_i = ev.t_step
        if t_up_j is None:
            for ev in hj.closure.last_transitions:
                if ev.kind == "up":
                    t_up_j = ev.t_step
        if t_up_i is not None and t_up_j is not None:
            break
    return i_start, j_start, t_up_i, t_up_j


def run():
    print("#" * 100)
    print("  P2-A3 二轮：消除建立瞬态后的近零区时序分辨率校正")
    print("#" * 100)

    print()
    print("== 第一步：确认预热平台 + 取 η_ij 候选（残余波动幅度） ==")
    plat_i = measure_settling_plateau(SITE_I)
    plat_j = measure_settling_plateau(SITE_J)
    print(f"  站点i={SITE_I} 平台段 L: {plat_i}")
    print(f"  站点j={SITE_J} 平台段 L: {plat_j}")
    li_vals = list(plat_i.values())
    lj_vals = list(plat_j.values())
    eta_i = (max(li_vals) - min(li_vals)) / 2
    eta_j = (max(lj_vals) - min(lj_vals)) / 2
    delta_ij_0 = plat_j[PRE_IDLE_STEPS] - plat_i[PRE_IDLE_STEPS]
    print(f"  残余波动幅度：η_i候选={eta_i}, η_j候选={eta_j}")
    print(f"  预热后站点固有偏移 δ_ij^0 = L_j - L_i = {delta_ij_0}"
          f"（首轮估计约6，本次在PRE_IDLE_STEPS={PRE_IDLE_STEPS}处实测）")
    eta_ij = max(eta_i, eta_j, 1)
    print(f"  采用 η_ij = max(η_i, η_j, 1) = {eta_ij}")

    print()
    print("== 第二步：预热后近零区扫描 ==")
    header = (
        f"{'Δt_ext':>7} | {'i_start':>8} {'j_start':>8} | {'t_up_i':>8} {'t_up_j':>8} | "
        f"{'L_i':>5} {'L_j':>5} | {'Δt(1,↑)':>8} | {'校正Δt̃':>8} | Order(η={eta_ij})"
    )
    print(header)
    print("-" * len(header))

    rows = []
    for dt_ext in DELTA_SWEEP_NEAR_ZERO:
        i_start, j_start, t_up_i, t_up_j = run_trial_r2(dt_ext)
        if t_up_i is None or t_up_j is None:
            print(f"{dt_ext:>7} | 未在预算步数内完成触发，跳过")
            continue
        L_i = t_up_i - i_start
        L_j = t_up_j - j_start
        delta_up = t_up_j - t_up_i
        corrected = delta_up - delta_ij_0

        if corrected > eta_ij:
            order = "i≺j"
        elif corrected < -eta_ij:
            order = "j≺i"
        else:
            order = "i∥j"

        print(f"{dt_ext:>7} | {i_start:>8} {j_start:>8} | {t_up_i:>8} {t_up_j:>8} | "
              f"{L_i:>5} {L_j:>5} | {delta_up:>8} | {corrected:>8} | {order}")
        rows.append({
            "delta_ext": dt_ext, "L_i": L_i, "L_j": L_j,
            "delta_up": delta_up, "corrected": corrected, "order": order,
        })

    print()
    print("#" * 100)
    print("  判定：固定延迟偏置 vs 真正压平区")
    print("#" * 100)
    sign_matches = sum(
        1 for r in rows
        if (r["corrected"] > 0) == (r["delta_ext"] > 0) or r["delta_ext"] == 0
    )
    linear_residual = [abs(r["corrected"] - r["delta_ext"]) for r in rows]
    print(f"  校正后符号与Δt_ext一致：{sign_matches}/{len(rows)}")
    print(f"  校正后 Δt̃ 与 Δt_ext 的残差 |Δt̃-Δt_ext|：{linear_residual}")
    max_residual = max(linear_residual) if linear_residual else None
    print(f"  最大残差={max_residual}，η_ij={eta_ij}")
    if max_residual is not None and max_residual <= eta_ij:
        print("  结论：校正后 Δt̃ ≈ Δt_ext 线性保留（残差不超过η_ij）——"
              "支持'只是固定延迟差，未发现真正压平区'。")
    else:
        print("  结论：校正后仍有超出η_ij的残差——需要进一步检查是否存在"
              "真正的压平区，或η_ij/δ_ij^0取值需要重新核实。")
    print("#" * 100)
    return rows


if __name__ == "__main__":
    run()
