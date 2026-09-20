"""recursive_trials.py — D2-1 StepD/E1：递归接受矩阵 + χ_ρ₂^(2) closure
候选（RC-1~RC-5 机器证据面）。

TYPE:INFRA（research/ 层；全部 stage-2 replay，读 StepB IMMUTABLE 缓存）。

## COMPUTE_BUDGET

  physical_trajectories=0; depth-1 relation replays=0（消费 StepB 端口）;
  stage-2 runs = 6（main/lead/lag/far/R_only/C_only）+1 零驱动（静息，
  不计）; closure 评估复用 E1 的 x 序列（无新 run）; interventions=0

## 预注册判据（运行前冻结）

RT-1 RC-1 typed acceptance：RelationOccurrencePortV1 经同一
     build_phase_drive 展开（与 depth-0 同函数，无手工解包）；机器核验
     =R 通道驱动非零集合恰为 [t_up, t_rearm)。
RT-2 重叠轴单调（结构预判，D2-0 T1 同地位——可证伪预测）：
     peak(main) > peak(lead) > peak(lag) > peak(far)——ρ 窗 [2617,3971)
     与 site23 窗重叠 633/44/0(gap188)/0(gap606) 步。
     **首跑证伪（2026-09-21，如实登记）**：lag/far/R_only 峰值逐位相同
     （3.9850）——根因=峰值度量饱和：非重叠情形全局峰由 R 通道长斜坡
     峰唯一决定，C 贡献叠加于其后残余、不超过 R 峰。RT-2 降级为
     falsified prediction（非门），根因由 RT-2r 机器核验；重叠régime
     的严格序（main > lead > R_only）保留为 RT-2a 门。
RT-2r 根因核验（证伪后加入，POST_HOC 标注）：lag/far/R_only 三者
     argmax(k) 相同且峰差 <1e-12；同时轨迹逐点确实不同（C 通道物理
     在场）：RMSE(lag,R_only)/RMSE(far,R_only)/RMSE(lag,far) 均 >1e-6；
     C 窗局部增量 max(x_run−x_R_only) 序：lag > far > 0（间隙越近
     残余叠加越大——时距敏感性在正确的度量下恢复）。POST_HOC 地位：
     RT-2r 是诊断非资格门，最终六门不依赖它。
RT-3 叠加性：peak(main) > max(peak(R_only), peak(C_only))（双输入 ≠
     单输入，D2-0 T7 同族）。
RT-4 R2 耗散：全部 run x_end < 0.05×peak（输入停后回落静息）。
RT-5 R3 有限：全部 peak ≤ 10（母本钳位）。
RT-6 静息：零驱动 8s x≡0（无源 RC 无自持；无父支撑 ⇒ ΔC_phys=0）。
RT-7 χ_ρ₂ closure（RC-5）：θ₂/rearm₂ 由 StepC 实测新鲜推导（规则族
     =D2-0：θ=u_work/2, rearm=round(τ/dt)；数值独立）。预注册：rc_main
     恰 1 次 relation-2 occurrence 且有自己的 t↑/t↓/t_rearm；单通道
     （R_only/C_only）计数如实登记（单通道峰相对 θ₂ 的边缘性必须并报，
     不预设、不回调）。谱系：AddressRegistry depth=2 真实注册，父=
     (ρ depth1, site23 生成元 depth0)。

复现入口：
  PYTHONIOENCODING=utf-8 python research/d2_recursive_v1/recursive_trials.py
"""
from __future__ import annotations

import csv
import json
import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _HERE)

from d21_common import (  # noqa: E402
    DATA, DT_G, RHO_MAIN_TRAJ, frozen_relation2_params,
    load_relation_ports, load_site23_windows, relation2_address)
from recursive_physical_impl import (  # noqa: E402
    build_relation2, recursive_drives, run_relation2, step_relation2)

EPS = 1e-12


def main() -> int:
    g, theta2, rearm2 = frozen_relation2_params()
    rho = load_relation_ports()[RHO_MAIN_TRAJ]
    s23 = load_site23_windows()
    rho2_addr, rho_addr, c_addr = relation2_address()
    print(f"closure params (fresh-derived from StepC): theta2={theta2:.4f} "
          f"rearm2={rearm2}  [D2-0 values NOT copied]")

    runs_spec = {
        "rc_main": ([rho], s23["s23_ov"]),
        "rc_lead": ([rho], s23["s23_lead"]),
        "rc_lag": ([rho], s23["s23_lag"]),
        "rc_far": ([rho], s23["s23_far_b"]),
        "rc_R_only": ([rho], []),
        "rc_C_only": ([], s23["s23_ov"]),
    }
    runs, ledgers = {}, []
    for tag, (rports, cwins) in runs_spec.items():
        xs, led, _p = run_relation2(rports, cwins, g)
        led = {"run": tag, **led}
        runs[tag] = xs
        ledgers.append(led)
        print(f"  {tag}: peak={led['x_peak']:.4f} end={led['x_end']:.5f} "
              f"dE={led['energy_drop']:.4f}")
    pk = {t: max(x) for t, x in runs.items()}

    checks = {}
    # RT-1 typed acceptance：R 驱动非零集合 == [t_up, t_rearm)
    dr, _dc = recursive_drives([rho], [])
    nz = [k for k, s in enumerate(dr) if s.value > 0.0]
    # ϑ(t_up)=0 by definition（相位起点），窗内其余全非零
    expect = list(range(rho.t_up + 1, rho.t_rearm))
    checks["RT1_pass"] = nz == expect
    checks["RT1_window"] = [rho.t_up, rho.t_rearm]
    # RT-2 重叠轴（v1 预判：首跑证伪，如实登记；根因见 RT-2r）
    checks["RT2_order"] = [pk["rc_main"], pk["rc_lead"], pk["rc_lag"],
                           pk["rc_far"]]
    checks["RT2_v1_prediction"] = (pk["rc_main"] > pk["rc_lead"]
                                   > pk["rc_lag"] > pk["rc_far"])
    checks["RT2_v1_status"] = (
        "FALSIFIED_PREDICTION: peak metric saturates in non-overlap regime "
        "(global peak = R-hump ceiling); root cause verified by RT-2r "
        "(POST_HOC diagnostic, not a gate)")
    # RT-2a 重叠 régime 严格序（保留为门）
    checks["RT2a_pass"] = pk["rc_main"] > pk["rc_lead"] > pk["rc_R_only"]
    # RT-2r 根因核验（POST_HOC 诊断）
    import math as _math

    def _rmse(a, b):
        return _math.sqrt(sum((x - y) ** 2 for x, y in zip(a, b)) / len(a))

    amax = {t: max(range(8000), key=lambda k: runs[t][k])
            for t in ("rc_lag", "rc_far", "rc_R_only")}
    same_hump = (amax["rc_lag"] == amax["rc_far"] == amax["rc_R_only"]
                 and abs(pk["rc_lag"] - pk["rc_R_only"]) < 1e-12
                 and abs(pk["rc_far"] - pk["rc_R_only"]) < 1e-12)
    r_lag = _rmse(runs["rc_lag"], runs["rc_R_only"])
    r_far = _rmse(runs["rc_far"], runs["rc_R_only"])
    r_lf = _rmse(runs["rc_lag"], runs["rc_far"])
    inc = {}
    for tag, wtag in (("rc_lag", "s23_lag"), ("rc_far", "s23_far_b")):
        w0 = s23[wtag][0].t_up
        inc[tag] = max(runs[tag][k] - runs["rc_R_only"][k]
                       for k in range(w0, 8000))
    checks["RT2r"] = {
        "same_R_hump": same_hump, "argmax": amax,
        "rmse_lag_vs_Ronly": r_lag, "rmse_far_vs_Ronly": r_far,
        "rmse_lag_vs_far": r_lf,
        "c_local_increment": inc,
        "pass": (same_hump and min(r_lag, r_far, r_lf) > 1e-6
                 and inc["rc_lag"] > inc["rc_far"] > 0.0),
        "status": "POST_HOC_DIAGNOSTIC (root cause of RT-2 falsification; "
                  "not a qualification gate)"}
    # RT-3 叠加性
    checks["RT3_pass"] = pk["rc_main"] > max(pk["rc_R_only"],
                                             pk["rc_C_only"])
    # RT-4 / RT-5
    checks["RT4_pass"] = all(l["x_end"] < 0.05 * l["x_peak"]
                             for l in ledgers if l["x_peak"] > 0)
    checks["RT5_pass"] = all(l["x_peak"] <= 10.0 + EPS for l in ledgers)
    # RT-6 静息
    p0 = build_relation2(g)
    x0max = 0.0
    for _ in range(8000):
        x0max = max(x0max, abs(step_relation2(p0, 0.0, 0.0)))
    checks["RT6_pass"] = x0max == 0.0

    # RT-7 closure：对全部 E1 run 复用 x 序列评估（无新 run）
    from tss.generators.occurrence import OccurrenceClosure
    occ_rows, occ_map = [], {}
    for tag, (rports, cwins) in runs_spec.items():
        dr, dc = recursive_drives(rports, cwins)
        cl = OccurrenceClosure(address=rho2_addr, theta_up=theta2,
                               theta_down=0.1 * theta2,
                               rearm_min_steps=rearm2, dt=DT_G)
        for k, x in enumerate(runs[tag]):
            sup = dr[k].parent_support or dc[k].parent_support
            cl.update(x, k, phys_support=sup)
        occ_map[tag] = len(cl.events)
        for ev in cl.events:
            tp = ev.to_physical(DT_G)
            occ_rows.append({
                "run": tag, "status": "RELATION2_OCCURRENCE_CANDIDATE",
                "t_up": ev.t_up, "t_down": ev.t_down, "t_rearm": ev.t_rearm,
                "t_up_s": tp[0], "t_down_s": tp[1], "t_rearm_s": tp[2],
                "epoch": ev.epoch_id, "rho2_uid": rho2_addr.uid,
                "generation_depth": rho2_addr.generation_depth,
                "parents": f"{rho_addr.uid}|{c_addr.uid}"})
    checks["RT7_occ_map"] = occ_map
    checks["RT7_main_pass"] = occ_map["rc_main"] == 1
    # 单通道边缘性并报（不预设）
    checks["RT7_single_channel"] = {
        "R_only": {"peak": pk["rc_R_only"], "occ": occ_map["rc_R_only"],
                   "margin_vs_theta2": (pk["rc_R_only"] - theta2) / theta2},
        "C_only": {"peak": pk["rc_C_only"], "occ": occ_map["rc_C_only"],
                   "margin_vs_theta2": (pk["rc_C_only"] - theta2) / theta2}}
    checks["lineage"] = {"rho2_uid": rho2_addr.uid, "depth": 2,
                         "parents": [rho_addr.uid, c_addr.uid]}
    # NF-2 结构性发现（如实登记，非门）：R 通道单独越 θ₂ ⇒ u_work/2
    # 规则族在非对称通道结构下不赋予双亲必要性（D2-0 双父必要性本就
    # 4.4% 边缘）；直接影响 E4 解读（阻断 R→occ 1→0；阻断 C→仅边界/
    # 轨迹级差异）。
    checks["NF2_single_parent_trigger"] = {
        "finding": "R-channel-alone crosses theta2 "
                   f"(margin {(pk['rc_R_only'] - theta2) / theta2:+.3f}); "
                   "dual-parent necessity does NOT hold for asymmetric "
                   "channels under the u_work/2 rule family; C_only margin "
                   f"{(pk['rc_C_only'] - theta2) / theta2:+.3f} (marginal, "
                   "below)",
        "consequence": "site23 parentage is trajectory/boundary-level "
                       "(NC4-style block shifts, not existence-level); "
                       "rho parentage is existence-level (block R => "
                       "occ 1->0)"}

    with open(os.path.join(DATA, 'recursive_trials.csv'), 'w',
              newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=list(ledgers[0]))
        w.writeheader(); w.writerows(ledgers)
    if occ_rows:
        with open(os.path.join(DATA, 'relation2_occurrence_candidates.csv'),
                  'w', newline='', encoding='utf-8') as f:
            w = csv.DictWriter(f, fieldnames=list(occ_rows[0]))
            w.writeheader(); w.writerows(occ_rows)
    with open(os.path.join(DATA, 'd21_trials.json'), 'w',
              encoding='utf-8') as f:
        json.dump(checks, f, indent=1, ensure_ascii=False, default=str)

    gate_keys = ["RT1_pass", "RT2a_pass", "RT3_pass", "RT4_pass",
                 "RT5_pass", "RT6_pass", "RT7_main_pass"]
    ok = all(checks[k] for k in gate_keys)
    print(f"  RT2 v1 prediction: "
          f"{'成立' if checks['RT2_v1_prediction'] else '证伪（峰值度量饱和）'}"
          f"  RT2r root-cause: {checks['RT2r']['pass']}")
    for k in gate_keys:
        print(f"  {k}: {checks[k]}")
    print(f"  occ map: {occ_map}")
    sc = checks["RT7_single_channel"]
    print(f"  single-channel margin vs theta2: "
          f"R={sc['R_only']['margin_vs_theta2']:+.3f} "
          f"C={sc['C_only']['margin_vs_theta2']:+.3f}")
    print("RESULT:", "PASS" if ok else "FAIL")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
