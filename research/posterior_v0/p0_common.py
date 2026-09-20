"""p0_common.py — Posterior-0 共享层：预注册常量 + 四臂 harness + 预算账本。

TYPE:INFRA（research/ 层；production/G0/D2-0/D2-1 全部 READ_ONLY）。

依据：外部《MAINLINE V2 — Posterior Construction-0》38 节 + 评判
《Posterior-0方案评判_2026-09-21》ADOPT with amendments + 反馈裁定
《反馈_Posterior-0方案评判_2026-09-21》（E-1~E-7 全 ACCEPTED，
R-1=(a)主+(c)条件后备/(b)拒绝，R-2/R-3 落值，READY_TO_EXECUTE=YES）。

## 预注册块（首次运行前冻结；每项后注出处）

  DELTA_PRIMARY_CHANNEL = "C"    # 反馈 §五（R-only 越 θ₂ +52% 触发新
                                 # occurrence=PARALLEL_NEW_STATE 混淆；
                                 # C-only 阈下 −2.8% 干净入口）
  QUERY_CHANNEL         = "C"    # 反馈 §五
  R_CHANNEL_POSTERIOR   = SECONDARY_ONLY（本轮未启用副实验）
  POSTERIOR_WASHOUT_STEPS = 456  # 反馈 §十（=1×τ₂，第一轮固定，
                                 # 不得看数据后改）
  EPSILON_NUM = 1e-6             # 方案 §29：max(10×ε_replay,1e-6)；
                                 # D2-1 M6 replay_bit_exact ⇒ ε_replay=0
  PL0/PL1/PL2                    # 反馈 §十五改名（避免与项目 P0/P1 撞名）
  Q_WINDOW_LEN = 639             # QUERY_WINDOW_SELECTION（反馈 §十四）：
                                 # Q=标准化相位斜坡探针，窗形取冻结
                                 # s23_ov 窗长（3566-2927=639）；驱动经
                                 # build_phase_drive typed 合同，无幅值 DOF
  W=0 臂定义 = R 通道全零、C 通道保留同一驱动序列
                                 # E3 Y 臂 / hold H6 先例；NF-2 C-only
                                 # 阈下 ⇒ 无关系发生；C 侧剂量逐位匹配

## Z 状态分量三分类（反馈 §十一）

  Z-primary   = RelationCell_2 membrane state（G1 已资格化载体）
  Z-secondary = tin (RelationInputNeuron) state（允许记录，不单独支撑资格）
  RESOURCE_TRACE_ONLY = PowerRail/energy/dissipation（单列；仅 energy 差
                        ⇒ PERSISTENT_POSTERIOR_STATE=NO，不得撑 M3）

## path block 定义（反馈 §八/§九，DIAGNOSTIC_INTERVENTION 登记）

  block 窗内：Δ→tin_c ACTIVE（照常换能）；tin_c→bundle_c BLOCKED
  （不调用 propagate ⇒ transmission=0）；RelationCell Δ dose=0。
  五审计项随臂账本输出。禁止用"移除 Δ 输入"充当 block（评判 E-3）。

## COMPUTE_BUDGET（反馈 §二十一口径，budget_ledger.json 开工登记）

  new_g0_trajectories <= 4 / prior_state_replays <= 12（每次完整 W=1 臂
  =1，不按 set 记）/ posterior_timing_points <= 4 / factorial_sets <= 4 /
  state_interventions <= 4 / path_blocks <= 3 / heldout = 6（hold 臂计入
  heldout 行，口径在账本 counting_rules 声明）。中止/重复/不可达的真实
  执行照记 attempted_run（反馈 §二十二）。
"""
from __future__ import annotations

import csv
import json
import math
import os
import sys
from copy import deepcopy
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Sequence, Tuple

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.abspath(os.path.join(_HERE, '..', '..'))
_D21 = os.path.abspath(os.path.join(_HERE, '..', 'd2_recursive_v1'))
_D20 = os.path.abspath(os.path.join(_HERE, '..', 'd2_relation_v0'))
for _p in (_ROOT, _D20, _D21, _HERE):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from d21_common import (  # noqa: E402
    DATA as D21_DATA, frozen_relation2_params, load_relation_ports,
    load_site23_windows, relation2_address)
from recursive_physical_impl import build_relation2, Relation2Parts  # noqa: E402
from relation_physical_impl import PortWindow  # noqa: E402
from d2_common import DT_G  # noqa: E402
from tss.adapters.relation_replay_adapter import build_phase_drive  # noqa: E402
from tss.generators.occurrence import OccurrenceClosure  # noqa: E402

DATA = os.path.join(_HERE, 'data')
S23_TRACES = os.path.join(DATA, 'site23_traces')

# ── 预注册冻结常量（provenance 见模块 docstring）──
DELTA_PRIMARY_CHANNEL = "C"
QUERY_CHANNEL = "C"
R_CHANNEL_POSTERIOR = "SECONDARY_ONLY"
POSTERIOR_WASHOUT_STEPS = 456
EPSILON_NUM = 1e-6
Q_WINDOW_LEN = 639
T_TOTAL_MAIN = 8000          # 主四臂时间轴（rc_main 同款）
T_TOTAL_AUDIT = 12000        # Step A1 残余观测（零驱动垫尾）

# W 组合 = rc_main（D2-1 E1 预注册组合；candidates.csv 运行时读边界）
RHO_W_TRAJ = "cal_C3_m"
S23_W_TID = "s23_ov"

# Step A2 探边（首次运行前冻结；latency 外推见 substrate_audit docstring）
PROBE1 = {"tid": "p0_probe_near", "t_on": 4780, "length": 600,
          "amp": 0.03, "t_total": 10000}
PROBE2_R1C = {"tid": "p0_probe_near_r1c", "t_on": 4780, "length": 900,
              "amp": 0.03, "t_total": 10000}   # R-1(c) 条件后备：仅延长
                                               # physical support duration；
                                               # probe1=同 t_on paired control

BUDGET_CAPS = {"new_g0_trajectories": 4, "prior_state_replays": 12,
               "posterior_timing_points": 4, "factorial_sets": 4,
               "state_interventions": 4, "path_blocks": 3, "heldout": 6}
LEDGER_PATH = os.path.join(DATA, 'budget_ledger.json')


# ── 冻结产物只读加载 ──

def rc_main_boundaries() -> Tuple[int, int, int]:
    """rc_main χ_ρ₂ 冻结边界 (t_up, t_down, t_rearm)——运行时读，不硬编码。"""
    with open(os.path.join(D21_DATA, 'relation2_occurrence_candidates.csv'),
              newline='', encoding='utf-8') as f:
        for r in csv.DictReader(f):
            if r["run"] == "rc_main":
                return int(r["t_up"]), int(r["t_down"]), int(r["t_rearm"])
    raise KeyError("rc_main not found in relation2_occurrence_candidates.csv")


def w_composition():
    """W=1 臂驱动素材：([ρ_a port], [s23_ov 窗])——rc_main 同款。"""
    rho = load_relation_ports()[RHO_W_TRAJ]
    cwins = list(load_site23_windows()[S23_W_TID])
    return [rho], cwins


def q_window(t_q_up: int) -> PortWindow:
    """标准化 query 探针窗（QUERY_WINDOW_SELECTION：仅放置，无幅值 DOF）。"""
    return PortWindow(t_q_up, t_q_up + Q_WINDOW_LEN,
                      "probe.Q:standardized_ramp")


# ── 四臂 harness ──

@dataclass
class ArmResult:
    name: str
    xs: List[float]                    # activation（typed 读出面）
    vs: List[float]                    # cell 膜电压（Z-primary 载体面，
                                       # DIAGNOSTIC_READ：只读观察，不写；
                                       # 反馈 §十一 Z-primary=membrane state；
                                       # G0-R1 hidden dynamics 先例）
    events: list                       # OccurrenceClosure 完成事件
    snapshots: Dict[int, dict] = field(default_factory=dict)
    audit: Dict[str, float] = field(default_factory=dict)
    ledger: Dict[str, float] = field(default_factory=dict)


def run_arm(name: str, rports: Sequence, cwins: Sequence,
            t_total: int = T_TOTAL_MAIN,
            block_window: Optional[Tuple[int, int]] = None,
            transplant_state: Optional[dict] = None,
            transplant_at: Optional[int] = None,
            snapshot_at: Sequence[int] = ()) -> ArmResult:
    """一臂完整 replay（物理链与 step_relation2 同构 + block/移植选项）。

    block_window=[a,b)：窗内 tin_c 照常 step、bundle_c 不 propagate
    （transmission=0，反馈 §八）；五审计项入 audit。
    transplant_at=k：第 k 步 step 前 cell.__dict__ ← deepcopy(移植态)
    （a8v2 tier1 先例，DIAGNOSTIC_INTERVENTION）。
    """
    g, theta2, rearm2 = frozen_relation2_params()
    rho2_addr, _, _ = relation2_address()
    dr = build_phase_drive(t_total, DT_G, rports)
    dc = build_phase_drive(t_total, DT_G, cwins)
    p = build_relation2(g)
    cl = OccurrenceClosure(address=rho2_addr, theta_up=theta2,
                           theta_down=0.1 * theta2,
                           rearm_min_steps=rearm2, dt=DT_G)
    neurons = (p.tin_r, p.tin_c, p.cell)
    e0 = sum(n.energy for n in neurons)
    audit = {"blocked_steps": 0, "tin_c_drive_sum_block": 0.0,
             "tin_c_act_peak_block": 0.0, "tin_c_energy_block_start": None,
             "tin_c_energy_block_end": None, "cell_dose_block": 0.0}
    xs: List[float] = []
    vs: List[float] = []
    snapshots: Dict[int, dict] = {}
    snapset = set(snapshot_at)
    for k in range(t_total):
        if transplant_at is not None and k == transplant_at:
            p.cell.__dict__.update(deepcopy(transplant_state))
        yr, yc = dr[k].value, dc[k].value
        blocked = (block_window is not None
                   and block_window[0] <= k < block_window[1])
        p.tin_r.step(yr, DT_G)
        p.tin_c.step(yc, DT_G)
        cr = p.bundle_r.propagate()
        if blocked:
            cc_val = 0.0                        # transmission = ZERO
            audit["blocked_steps"] += 1
            audit["tin_c_drive_sum_block"] += yc
            audit["tin_c_act_peak_block"] = max(
                audit["tin_c_act_peak_block"], abs(p.tin_c.activation))
            if audit["tin_c_energy_block_start"] is None:
                audit["tin_c_energy_block_start"] = p.tin_c.energy
            audit["tin_c_energy_block_end"] = p.tin_c.energy
        else:
            cc = p.bundle_c.propagate()
            cc_val = cc[0] if cc else 0.0
        p.cell.step((cr[0] if cr else 0.0) + cc_val, DT_G)
        x = p.cell.activation
        sup = dr[k].parent_support or dc[k].parent_support
        cl.update(x, k, phys_support=sup)
        xs.append(x)
        vs.append(p.cell._membrane.voltage)   # DIAGNOSTIC_READ（只读）
        if k in snapset:
            snapshots[k] = {"x": x,
                            "cell_state": deepcopy(p.cell.__dict__),
                            "energy_total": sum(n.energy for n in neurons)}
    e1 = sum(n.energy for n in neurons)
    ledger = {"x_peak": max(xs), "x_end": xs[-1], "e_start": e0,
              "e_end": e1, "energy_drop": e0 - e1,
              "transport_cost": p.bundle_r.transport_cost
              + p.bundle_c.transport_cost}
    return ArmResult(name, xs, vs, cl.events, snapshots, audit, ledger)


# ── 分析原语 ──

def rms(seq: Sequence[float]) -> float:
    return math.sqrt(sum(v * v for v in seq) / len(seq)) if seq else 0.0


def interaction_traj(x11, x10, x01, x00, w: Tuple[int, int]) -> float:
    """I_W^traj = RMS_t[(x11−x10)−(x01−x00)]，窗 [a,b)（反馈 §十六）。"""
    a, b = w
    return rms([(x11[k] - x10[k]) - (x01[k] - x00[k]) for k in range(a, b)])


def events_in(events, a: int, b: int):
    return [e for e in events if a <= e.t_up < b]


def peak_in(xs, a: int, b: int) -> float:
    return max(xs[a:b]) if b > a else 0.0


# ── 预算账本（反馈 §二十一/§二十二）──

def ledger_init() -> dict:
    os.makedirs(DATA, exist_ok=True)
    if os.path.exists(LEDGER_PATH):
        with open(LEDGER_PATH, encoding='utf-8') as f:
            return json.load(f)
    led = {"caps": BUDGET_CAPS,
           "counting_rules": {
               "prior_state_replays": "each full run of a W=1 history arm "
                                      "counts 1 (per-arm, NOT per 2x2 set)",
               "heldout": "hold6 runs (incl. their W arms) counted here, "
                          "not under prior_state_replays (declared up "
                          "front, feedback §21)",
               "attempted_run": "aborted/duplicate/unreachable executions "
                                "are still logged (feedback §22)"},
           "entries": []}
    _ledger_write(led)
    return led


def _ledger_write(led: dict) -> None:
    with open(LEDGER_PATH, 'w', encoding='utf-8', newline='\n') as f:
        json.dump(led, f, indent=1, ensure_ascii=False)


def ledger_add(category: str, item: str, note: str = "",
               attempted: bool = False) -> dict:
    """登记一笔预算消费。幂等：同 (category,item) 已登记则跳过
    （确定性重放同一评估不重复计费，D2-1 标定去重先例）。"""
    led = ledger_init()
    if any(e["category"] == category and e["item"] == item
           for e in led["entries"]):
        return led
    led["entries"].append({"category": category, "item": item,
                           "note": note, "attempted_only": attempted})
    used = sum(1 for e in led["entries"]
               if e["category"] == category and not e["attempted_only"])
    cap = led["caps"].get(category)
    if cap is not None and used > cap:
        raise RuntimeError(
            f"COMPUTE_BUDGET 超限：{category} used={used} > cap={cap}"
            "（EXPECTED_NEW_INFORMATION 未登记则停止，方案 §30）")
    _ledger_write(led)
    return led


def ledger_count(category: str) -> int:
    led = ledger_init()
    return sum(1 for e in led["entries"]
               if e["category"] == category and not e["attempted_only"])
