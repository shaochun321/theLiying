"""
P2-A1b-0：低端启动边界复核（多种子 + 多观测窗）

背景：评判(`document - 2026-07-21T140903.110.md`唯一阻塞)指出P2-A1a-R
报告"u<=0.0005全部不触发（真正静默）"与更早的P2-A1a粗扫描（u=0.0005在
第4451步触发过一次）矛盾。已用命令行独立进程实测坐实：

    不固定 PYTHONHASHSEED: 3次独立进程 u=0.0005 → 0/1/0 次触发
    固定 PYTHONHASHSEED=0:  3次独立进程 u=0.0005 → 全部第4449步触发

机制：Memristor ±25%对称性打破扰动依赖 `hash((bundle_id,i_s,i_t))`，
Python字符串hash()默认逐进程随机化（`relations/site_selection.py`
docstring已警告过这个机制）。u=0.0005恰好卡在触发临界点，扰动幅度决定
触发与否。

本实验：对每个候选u，用`subprocess`以不同`PYTHONHASHSEED`（0~9共10个
种子）各跑一次全新生成元实例，两种观测窗（T_obs=5000/20000），产出
`u_on(T_obs) = inf{u: N_occ(u;T_obs)>0}`的经验分布（触发比例），不冻结
单一数值。
"""
import subprocess
import sys

sys.path.insert(0, '.')

U_LEVELS = [0.0004, 0.0005, 0.0006, 0.0007, 0.0008]
SEEDS = list(range(10))
OBS_WINDOWS = [5000, 20000]

_WORKER_TEMPLATE = """
import sys
sys.path.insert(0, '.')
from nexus_v1.circuit.variant_adapter import VariantCircuit
from nexus_v1.components.structural_address import AddressRegistry
from tss.generators import wrap_base_generator
from tss.relations import FROZEN_THERMAL_SITES

DT = 0.001
SITE = FROZEN_THERMAL_SITES['t1_pair']['a']
c = VariantCircuit()
r = AddressRegistry()
h = wrap_base_generator(c, SITE, r, polarity='warm')
for t in range({steps}):
    h.tick({u}, DT, t)
n_occ = h.closure.occurrence_count
l_first = h.closure.events[0].t_up if h.closure.events else -1
print(f"{{n_occ}},{{l_first}}")
"""


def run_one(u, steps, seed):
    """在独立子进程里以指定 PYTHONHASHSEED 跑一次全新生成元实例。"""
    import os
    env = dict(os.environ)
    env["PYTHONHASHSEED"] = str(seed)
    env["PYTHONIOENCODING"] = "utf-8"
    code = _WORKER_TEMPLATE.format(u=u, steps=steps)
    result = subprocess.run(
        [sys.executable, "-c", code],
        cwd=".", env=env, capture_output=True, text=True, timeout=60,
    )
    line = result.stdout.strip().splitlines()[-1] if result.stdout.strip() else "0,-1"
    n_occ_str, l_first_str = line.split(",")
    return int(n_occ_str), int(l_first_str)


def run():
    print("=" * 90)
    print("  P2-A1b-0：低端启动边界复核（多PYTHONHASHSEED种子 x 多观测窗）")
    print("=" * 90)

    results = {}  # (u, T_obs) -> [(seed, n_occ, l_first), ...]
    for T_obs in OBS_WINDOWS:
        for u in U_LEVELS:
            trials = []
            for seed in SEEDS:
                n_occ, l_first = run_one(u, T_obs, seed)
                trials.append((seed, n_occ, l_first))
            results[(u, T_obs)] = trials

    for T_obs in OBS_WINDOWS:
        print()
        print(f"--- 观测窗 T_obs={T_obs} ---")
        header = f"{'u':>10} | {'触发种子数/总数':>16} | {'触发比例':>10} | {'l_first(触发种子)':>30}"
        print(header)
        print("-" * len(header))
        for u in U_LEVELS:
            trials = results[(u, T_obs)]
            n_triggered = sum(1 for _, n_occ, _ in trials if n_occ > 0)
            ratio = n_triggered / len(trials)
            l_firsts = [l_first for _, n_occ, l_first in trials if n_occ > 0]
            print(f"{u:>10.4f} | {n_triggered:>7}/{len(trials):<7} | {ratio:>10.2%} | "
                  f"{str(l_firsts):>30}")

    # ── 确定性核实：固定同一种子多次独立进程，结果应完全一致 ──
    print()
    print("=" * 90)
    print("  确定性核实：固定 PYTHONHASHSEED=0，同一 u 独立跑 3 次")
    print("=" * 90)
    check_u = 0.0005
    for trial_idx in range(3):
        n_occ, l_first = run_one(check_u, 5000, seed=0)
        print(f"  第{trial_idx+1}次: n_occ={n_occ}, l_first={l_first}")

    # ── u_on(T_obs) 经验定义 ──
    print()
    print("=" * 90)
    print("  u_on(T_obs) = inf{u: N_occ(u;T_obs)>0} 的经验分布（不冻结单一数值）")
    print("=" * 90)
    for T_obs in OBS_WINDOWS:
        # 找到"至少有一个种子触发"的最低u
        candidates = [u for u in U_LEVELS
                      if any(n_occ > 0 for _, n_occ, _ in results[(u, T_obs)])]
        u_on_lower_bound = min(candidates) if candidates else None
        # 找到"全部种子都触发"的最低u（更保守的上界）
        all_triggered = [u for u in U_LEVELS
                         if all(n_occ > 0 for _, n_occ, _ in results[(u, T_obs)])]
        u_on_upper_bound = min(all_triggered) if all_triggered else None
        print(f"  T_obs={T_obs}: 至少1个种子触发的最低u = {u_on_lower_bound}, "
              f"全部种子都触发的最低u = {u_on_upper_bound}")
        print(f"    → u_on(T_obs={T_obs}) 应表述为区间/分布，"
              f"不是单一数值：介于 [{u_on_lower_bound}, {u_on_upper_bound}]")

    print("=" * 90)
    return results


if __name__ == "__main__":
    run()
