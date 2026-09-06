"""tss.tests.test_tss3a_theta_distance_audit — TSS-3a：Θ 时间关系在更远
物理距离/更弱驱动下的资产审计（纯测量，不新建 collector/bundle）。

方案依据：document - 2026-08-03T212639.904.md（评判三问审计），按我方复核
结论修正其框架——见下"与评判的两处分歧"。

标签说明：评判把本任务命名为 CG-0a，但 204602 已把 CG-0a 定义为"方向耦合
生成元的类型契约与现有资产映射"，同号异义会污染项目标签登记体系。本文件
改用 TSS-3a，CG-0a 留给方向耦合。

═══ 与评判的两处分歧 ═══

1. 评判 Q2 的"实验区分"不成立。Θ_28,X 读的是站点 collector
   （thermal_quantum_collectors），而 N_LOCAL/N_BROAD 是 Λ collector 的
   **输入表**，位于站点 collector 下游。改支撑窗口只改"哪个 Λ collector 把
   站点 X 求进去"，不影响 Θ_28,X 能否形成。要让 X 不活动只能改驱动半径，
   而评判 201310 已裁定 radius=2.0/3.0 是两次不同外部发生。
   → 选点理由换成物理距离与驱动衰减，Λ 完全退出框架。

2. N_LOCAL/N_BROAD 不是几何窗口，与距离不可分。实测（TSS-2b 修正轮）：
       max d within N_LOCAL = 2.9742 (站点24)
       min d within N_DELTA = 1.8222 (站点15)   → 距离重叠
   根因：test_tss2a_scale_audit.py:68-69 的 N_LOCAL = active_r2，是
   radius=2.0 下"响应≥0.01"的实测激活集合，非几何窗口。
   → 评判"12∈N_Δ 更有判别力"方向反了：12(d=2.38) 比 N_LOCAL 内的
     24(d=2.97) 更近。候选按实测距离排布，纳入 24 作为判别力关键点。

═══ 审计三问 + 补的控制变量 ═══

Q1 物理对应物：同一外部发生下，源生成元28先取得活动，远处生成元X随后取得
   活动；trace—collector 结构检测两者活动的有序耦合。不依赖 STDP/DA。
Q2 选点：按实测距离（_CANDIDATES），不按集合成员。
Q3 参数可否复用 T1：实测 t_28/t_X/Δt，判断 W_Θ,T1（50/600 步）是否覆盖
   0<Δt<W。覆盖则复用为来源明确的冻结初值。不做网格搜索。
Q4（我方补，评判缺此项——决定性）：跨 physical_seed 的先后序稳定性。
   variant_adapter.py:1757 的 bundle_id=f"thermq_in_{label}" 走
   bundle.py:194-204 的 bundle_id→crc32→±25% 扰动，即每个站点换能增益按
   名字差异最多 ±25%。谁先越阈部分由名字决定，不只由距离决定
   （temporal_r_prec.py:60 已记录"扰动+饱和会导致假性不对称"；上一轮 Λ 的
   7% 假阳性正是此失效模式）。故须多组种子重建，检查 sign(Δt) 与排序稳定性。

边界：种子扰动只存在于本探针，不改主代码——给 thermq_* 补 physical_seed 会
改掉 T1 的 EXP-T1-01 标定与 21 项回归的全部数值。

停止条件：
  1. 可直接复用            → 进入 28≺X 最小电路
  2. 需一次有根据的窗口调整 → 给出参数来源后再实现
  3. 站点X无稳定后发活动    → 停止，不强造关系
  4. Δt≤0 或先后序跨种子不稳定 → 停止（与3不同：3是强度不稳，本条是顺序
     不稳，而顺序才是 Θ 的全部内容）
"""
import sys
from dataclasses import replace as dc_replace

sys.path.insert(0, '.')

from nexus_v1.circuit.bundle import SynapticBundle
from nexus_v1.components.world import HeatSource
from tss.relations.generator_lambda import N_LOCAL, N_DELTA, SOURCE_SITE
from tss.relations.temporal_r_prec import (
    RPrecCircuitT1, _TAU_FAST_STEPS, _TAU_SLOW_STEPS,
)

DT = 0.001
N_STEPS = 1600
HEAT_RADIUS = 3.0        # 同 TSS-2b：覆盖 N_BROAD 全部站点的单次外部发生
HEAT_TEMPERATURE = 300.0
HEAT_ENERGY = 100000.0
ACTIVE_THRESHOLD = 0.01  # 同 TSS-2a:68 的活动判据

# 候选：按 TSS-2b 修正轮实测距离排布（d from 28），不按集合成员
#   31: 1.0916  T1 现有目标，基线对照
#   15: 1.8222  N_DELTA 最近（比 N_LOCAL 的 26/29/27/24 都近）
#   12: 2.3751  评判所选
#   21: 2.8307  N_DELTA 最远
#   24: 2.9742  N_LOCAL 最远，比所有 N_DELTA 站点都远 —— 判别力关键点
_CANDIDATES = [31, 15, 12, 21, 24]

# None = 保留主代码默认（bundle_id 派生扰动）；其余为显式 physical_seed 基址
_SEED_VARIANTS = [None, 81000, 82000, 83000, 84000]


def _reseed_site(circuit, site: int, seed_base):
    """把站点 site 的 warm 三级链路 bundle 用新 physical_seed 重建。

    用 dc_replace 从现有 config 复制，故不需要知道任何工厂函数的 id 格式与
    权重常量。step 端是 zip(三个 list) 遍历，原地替换 list 元素即刻生效。
    索引规则：站点 i 的 warm 在 2i，cool 在 2i+1。
    """
    if seed_base is None:
        return
    idx = 2 * site
    for lst in (circuit.bundles_thermal_quantum_l1_to_hc,
                circuit.bundles_thermal_quantum_in,
                circuit.bundles_thermal_quantum_collect):
        old = lst[idx]
        cfg2 = dc_replace(old.config, physical_seed=seed_base + site)
        lst[idx] = SynapticBundle(cfg2, old.sources, old.targets)


def _drive_and_measure_onsets(seed_base, sites):
    """单次外部发生，返回 {site: 首次 pre_trace>=ACTIVE_THRESHOLD 的步数}。

    未越阈的站点记 None。同一次 HeatSource 驱动（不分多次），所有站点在
    同一次发生中被同时测量。
    """
    circuit = RPrecCircuitT1()
    for s in [SOURCE_SITE] + list(sites):
        _reseed_site(circuit, s, seed_base)

    patch = circuit._thermal_quantum_patches[SOURCE_SITE]
    heat_pos = patch.world_position(circuit.world.body)
    circuit.world.heat_sources = [HeatSource(
        position=list(heat_pos), energy=HEAT_ENERGY,
        temperature=HEAT_TEMPERATURE, radius=HEAT_RADIUS,
        _drift=[0.0, 0.0, 0.0],
    )]

    watch = [SOURCE_SITE] + list(sites)
    onset = {s: None for s in watch}
    peak = {s: 0.0 for s in watch}
    for t in range(N_STEPS):
        circuit.step({}, DT)
        for s in watch:
            v = circuit.thermal_quantum_collectors[f"thermpt{s}_warm"].pre_trace
            if v > peak[s]:
                peak[s] = v
            if onset[s] is None and v >= ACTIVE_THRESHOLD:
                onset[s] = t
    return onset, peak


def run():
    print("=" * 72)
    print("TSS-3a：Θ 时间关系的距离审计 + 跨种子先后序稳定性")
    print(f"场景：单次 HeatSource @site{SOURCE_SITE}, radius={HEAT_RADIUS}, "
          f"T={HEAT_TEMPERATURE}, {N_STEPS}步, DT={DT}")
    print(f"W_Θ,T1: fast={_TAU_FAST_STEPS}步  slow={_TAU_SLOW_STEPS}步")
    print("=" * 72)

    dists = {31: 1.0916, 15: 1.8222, 12: 2.3751, 21: 2.8307, 24: 2.9742}
    results = {}   # seed_base -> (onset, peak)

    for sb in _SEED_VARIANTS:
        tag = "default(bundle_id)" if sb is None else f"seed_base={sb}"
        print(f"\n--- 驱动 {tag} ---")
        onset, peak = _drive_and_measure_onsets(sb, _CANDIDATES)
        results[sb] = (onset, peak)
        t0 = onset[SOURCE_SITE]
        print(f"  site{SOURCE_SITE} (源) onset={t0}  peak={peak[SOURCE_SITE]:.4f}")
        for s in _CANDIDATES:
            grp = "LOCAL" if s in N_LOCAL else ("DELTA" if s in N_DELTA else "?")
            dt_s = (None if (onset[s] is None or t0 is None)
                    else onset[s] - t0)
            print(f"  site{s:2d} d={dists[s]:.4f} [{grp:5s}] "
                  f"onset={onset[s]}  Δt={dt_s}  peak={peak[s]:.4f}")

    # ── 判定 ──
    print("\n" + "=" * 72)
    print("判定")
    print("=" * 72)
    for s in _CANDIDATES:
        deltas = []
        for sb in _SEED_VARIANTS:
            onset, _ = results[sb]
            t0, tx = onset[SOURCE_SITE], onset[s]
            deltas.append(None if (t0 is None or tx is None) else tx - t0)

        grp = "LOCAL" if s in N_LOCAL else "DELTA"
        print(f"\nsite{s} (d={dists[s]:.4f}, {grp})  Δt across seeds = {deltas}")

        if all(d is None for d in deltas):
            print("  → 停止条件3：该站点在任何种子下都无活动，不强造关系")
            continue
        if any(d is None for d in deltas):
            print("  → 停止条件3：活动不稳定（部分种子下不越阈）")
            continue
        if any(d <= 0 for d in deltas):
            print("  → 停止条件4：Δt≤0（与源同时或先于源活动），顺序不成立")
            continue
        signs = {d > 0 for d in deltas}
        if len(signs) > 1:
            print("  → 停止条件4：sign(Δt) 跨种子翻转 ⇒ 先后序是名称伪影")
            continue
        spread = max(deltas) - min(deltas)
        print(f"  Δt 全为正，跨种子极差={spread}步 "
              f"(min={min(deltas)}, max={max(deltas)})")
        if spread > min(deltas):
            print("  → 停止条件4：极差超过 Δt 本身，顺序量级不可信")
            continue
        if max(deltas) < _TAU_FAST_STEPS:
            print(f"  → 停止条件1：0<Δt<{_TAU_FAST_STEPS}(fast) 全覆盖，"
                  f"T1 参数可直接复用为冻结初值")
        elif max(deltas) < _TAU_SLOW_STEPS:
            print(f"  → 停止条件1：{_TAU_FAST_STEPS}≤Δt<{_TAU_SLOW_STEPS}，"
                  f"slow 通道覆盖，fast 通道不覆盖（只复用 slow）")
        else:
            print(f"  → 停止条件2：Δt≥{_TAU_SLOW_STEPS}，超出 T1 适用域，"
                  f"需先说明物理时间差再按推理调整窗口（不做网格搜索）")

    print("\n" + "=" * 72)
    print("附：集合成员 vs 距离（评判 Q2 的判别力检查）")
    print("  site24 ∈ N_LOCAL 但 d=2.9742，比所有 N_DELTA 站点都远")
    print("  site15 ∈ N_DELTA 但 d=1.8222，在几何半径2.0以内")
    print("  ⇒ 若 site24 与 site12 的 Δt 表现无系统差异，则集合成员对 Θ")
    print("     不承重，评判 Q2 的'不同支撑范围下获得/失去资格'不成立")
    print("=" * 72)


if __name__ == "__main__":
    run()
