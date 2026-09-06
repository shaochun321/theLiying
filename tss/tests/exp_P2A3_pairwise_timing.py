"""tss.tests.exp_P2A3_pairwise_timing — P2-A3：成对 D1 occurrence 时序分辨率

评判依据：`cell-cell/交叉比对/document - 2026-07-28T120854.728.md`
「P2-A3 应严格做什么」§1~4 +「P2-A3 的停止标准」。

范围边界（评判明确）：P2-A3 只研究两个**已经取得物理确认资格**的发生
χ_i^(1)/χ_j^(1) 之间系统能分辨的时序关系，不构造 D2 时间关系算子/生成元
本身；输入对象是 χ_i^(1)/χ_j^(1)，不是 collector 原始峰值。

三种时间定义（评判§3，不能默认相等）：
  Δt_ij^(-1,ext)：外部物理刺激起始时间差（实验设定的 ground truth，本
                  脚本里是 j 相对 i 的驱动起始偏移，可正可负）。
  Δt_ij^(1,↑)  = t_up_j - t_up_i（D1 发生启动间隔，来自 ξ↑，即
                 OccurrenceClosure.last_transitions 的 "up" 事件）。
  Δt_ij^(1,χ)  = t_rearm_j - t_rearm_i（D1 完整闭合间隔，来自 ξ_rearm）。

站点选择：复用 T0 冻结集合 `FROZEN_THERMAL_SITES["t1_pair"]`（点28↔31，
真实球面几何最近邻对，不新选点，见 `relations/site_selection.py`）。

驱动方式：两个生成元各自独立驱动（各自一份 `build_three_point_skin()`
皮肤图），互不耦合扩散——这样 Δt_ij^ext 完全由实验直接控制，不与皮肤自身
扩散延迟混淆（若要研究"同一皮肤区域两点"的耦合时序，是另一个独立问题，
不在本轮范围）。驱动幅度/时长沿用 P2-A1b-3R 已验证的代表性预算（900步
持续注入 level=1.0），不新造数值。

RULES.md 强制三问：
  Q1 生物对应物：两个独立空间位置的热感受野各自完成一次外周—中枢换能，
     中枢读出系统（本脚本扮演 P2-B 前置的"比较器"角色）比较两次独立传入
     事件的时序——标准的双感受野时序分辨率范式（如双点辨别阈测量），
     不引入新生物机制，只是读出层面的比较。
  Q2 物理结构：不新建 Neuron/Bundle。复用已有 `wrap_base_generator`（两次
     调用，site_index=28/31）+ 已有 `OccurrenceClosure.last_transitions`
     （P2-A3 本轮为在线转换流新增的暴露接口，见 occurrence.py）。
  Q3 参数依据：DRIVE_STEPS=900、注入幅度=1.0 直接复用
     `exp_P2A1b_3_closure_calibration.py` 已验证的代表性预算，不新造。
     Δt_ext 扫描点集合覆盖从"远大于单侧闭合窗口"到"接近0"的量级，用于
     经验性确定分辨阈值 b_ij，不预设该阈值本身。
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

# 复用 P2-A1b-3R 已验证的代表性驱动预算（exp_P2A1b_3_closure_calibration.py）。
DRIVE_STEPS = 900
# 足够覆盖：max(|Δt_ext|) + 900 步驱动 + 单侧完整闭合(~3300步实测) + 余量。
TOTAL_STEPS = 8000

# 扫描点：覆盖 i≺j / j≺i / i∥j 三种名义关系，量级从远大于单侧闭合窗口
# （2000步，此前实测单侧 t_rearm~3300 步）到接近0（同时驱动）。
DELTA_SWEEP = [-2000, -1000, -500, -200, -100, -50, -20, -5, 0, 5, 20, 50, 100, 200, 500, 1000, 2000]


def fresh_skin():
    return build_three_point_skin(
        kappa=TEST_KAPPA_THREE_POINT, r_leak_ambient=TEST_R_LEAK_AMBIENT_THREE_POINT)


def make_pair():
    circuit = VariantCircuit()
    registry = AddressRegistry()
    hi = wrap_base_generator(circuit, SITE_I, registry, polarity="warm")
    hj = wrap_base_generator(circuit, SITE_J, registry, polarity="warm")
    return hi, hj


def run_trial(delta_t_ext: int):
    """i、j 各自独立驱动 DRIVE_STEPS 步（level=1.0），j 相对 i 的起始偏移
    为 delta_t_ext（可负）。两侧驱动窗口都平移到 >=0（不改变相对间隔），
    避免负索引。返回 (events_i, events_j, trans_i, trans_j)。"""
    hi, hj = make_pair()
    gi, gj = fresh_skin(), fresh_skin()

    if delta_t_ext >= 0:
        i_start, j_start = 0, delta_t_ext
    else:
        i_start, j_start = -delta_t_ext, 0
    i_end, j_end = i_start + DRIVE_STEPS, j_start + DRIVE_STEPS

    trans_i, trans_j = [], []
    for t in range(TOTAL_STEPS):
        inj_i = {0: 1.0} if i_start <= t < i_end else {}
        inj_j = {0: 1.0} if j_start <= t < j_end else {}
        gi.step(dt=1.0, external_injections=inj_i)
        gj.step(dt=1.0, external_injections=inj_j)
        qi = gi.cells[0].temperature
        qj = gj.cells[0].temperature
        hi.tick_from_skin(qi, CONFIG, DT, t)
        hj.tick_from_skin(qj, CONFIG, DT, t)
        if hi.closure.last_transitions:
            trans_i.extend(hi.closure.last_transitions)
        if hj.closure.last_transitions:
            trans_j.extend(hj.closure.last_transitions)
    return hi.closure.events, hj.closure.events, trans_i, trans_j


def _get_transition(trans, kind):
    """从 last_transitions 累积列表里取第一个匹配 kind 的 t_step（None 表示未发生）。

    审查点2升级（`document - 2026-07-28T170247.680.md`）：`trans` 里的元素从
    裸元组 `(kind, t_step)` 升级为 `TransitionEvent`（`.kind`/`.t_step` 属性），
    此处同步改用属性访问。"""
    for ev in trans:
        if ev.kind == kind:
            return ev.t_step
    return None


def run():
    print("#" * 100)
    print("  P2-A3：成对 D1 occurrence 时序分辨率标定")
    print(f"  站点对：i={SITE_I}（t1_pair.a）, j={SITE_J}（t1_pair.b）"
          f"（T0冻结集合最近邻对，见site_selection.py）")
    print("#" * 100)

    header = (
        f"{'Δt_ext':>8} | {'N_i':>3} {'N_j':>3} | {'t_up_i':>7} {'t_up_j':>7} | "
        f"{'Δt(1,↑)':>8} | {'t_rearm_i':>9} {'t_rearm_j':>9} | {'Δt(1,χ)':>8} | "
        f"{'ε_ij':>6} | {'overlap':>7} | Order"
    )
    print(header)
    print("-" * len(header))

    rows = []
    for dt_ext in DELTA_SWEEP:
        events_i, events_j, trans_i, trans_j = run_trial(dt_ext)
        n_i, n_j = len(events_i), len(events_j)

        t_up_i = _get_transition(trans_i, "up")
        t_up_j = _get_transition(trans_j, "up")
        t_rearm_i = _get_transition(trans_i, "rearm")
        t_rearm_j = _get_transition(trans_j, "rearm")

        if None in (t_up_i, t_up_j, t_rearm_i, t_rearm_j) or n_i != 1 or n_j != 1:
            print(f"{dt_ext:>8} | {n_i:>3} {n_j:>3} | 未各自恰好闭合一次，跳过时序计算"
                  f"（N_i={n_i}, N_j={n_j} 应均为1；若否说明该Δt_ext下二者相互干扰产生"
                  f"额外/缺失occurrence，是本身值得记录的发现）")
            rows.append({
                "delta_ext": dt_ext, "n_i": n_i, "n_j": n_j,
                "delta_up": None, "delta_chi": None, "epsilon": None,
                "overlap": None, "order": "N_i或N_j≠1",
            })
            continue

        delta_up = t_up_j - t_up_i
        delta_chi = t_rearm_j - t_rearm_i
        epsilon = delta_up - dt_ext
        overlap = max(0, min(t_rearm_i, t_rearm_j) - max(t_up_i, t_up_j))

        if delta_up > 0:
            order = "i≺j"
        elif delta_up < 0:
            order = "j≺i"
        else:
            order = "i∥j"

        print(f"{dt_ext:>8} | {n_i:>3} {n_j:>3} | {t_up_i:>7} {t_up_j:>7} | "
              f"{delta_up:>8} | {t_rearm_i:>9} {t_rearm_j:>9} | {delta_chi:>8} | "
              f"{epsilon:>6} | {overlap:>7} | {order}")
        rows.append({
            "delta_ext": dt_ext, "n_i": n_i, "n_j": n_j,
            "delta_up": delta_up, "delta_chi": delta_chi, "epsilon": epsilon,
            "overlap": overlap, "order": order,
        })

    print()
    print("#" * 100)
    print("  停止标准五问（评判§「P2-A3 的停止标准」）——本次扫描直接回答的部分")
    print("#" * 100)

    clean_rows = [r for r in rows if r["order"] not in ("N_i或N_j≠1",)]
    interference_rows = [r for r in rows if r["order"] == "N_i或N_j≠1"]

    print(f"  1. 两个真实 occurrence 是否可独立形成：扫描的 {len(DELTA_SWEEP)} 个 "
          f"Δt_ext 中，{len(clean_rows)} 个各自恰好 N=1（独立形成），"
          f"{len(interference_rows)} 个出现相互干扰（N≠1）。")
    if interference_rows:
        print(f"     干扰发生在 Δt_ext ∈ {[r['delta_ext'] for r in interference_rows]}")

    sign_matches = [r for r in clean_rows
                    if r["delta_up"] is not None and
                    ((r["delta_up"] > 0) == (r["delta_ext"] > 0) or r["delta_ext"] == 0)]
    print(f"  2/3. 顺序符号一致性（sign(Δt^(1,↑)) 与 sign(Δt_ext) 相符的比例）："
          f"{len(sign_matches)}/{len(clean_rows)}")

    print("  4. HC 慢态是否造成时序偏移/漏计/次序反转：见 ε_ij 列——若 ε_ij 在小 "
          "|Δt_ext| 处显著偏离0或符号与Δt_ext不一致，即为HC慢态（D0债务）造成的"
          "时序偏移证据。")
    print("  5. 在线状态流能否供P2-B使用：last_transitions 已能实时暴露ξ↑/ξ↓/ξ_rearm，"
          "本脚本的读取方式（累积trans列表+按kind取值）即可直接复用于P2-B。")

    print()
    print("  【未测量项，如实登记，非本轮伪造】：C_ij（多次重复下的顺序一致率）"
          "需要有物理依据的trial-to-trial噪声源（如输入幅度的真实生理变异范围），"
          "本轮未引入任何未经推导的随机噪声源（避免RULES.md禁止的'无来源填参数'），"
          "故C_ij留空，留待有依据的噪声模型确定后再测。")
    print("#" * 100)
    return rows


if __name__ == "__main__":
    run()
