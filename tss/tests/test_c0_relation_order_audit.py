"""tss.tests.test_c0_relation_order_audit — C0：level-2 关系次序目标对审计。

TYPE:INFRA

路线依据：08_下一阶段路线图.md §10 C0（选择首个不越级的耦合生成元）。
方法论：镜像 TSS-3a（test_tss3a_theta_distance_audit.py）的多种子实测纪律——
不强造关系，判据先于数据声明，停止条件显式。

## 测什么

对三个合格 Θ 目标站点 {15, 21, 24}，在**真实链路**（collector→port→
entry_gate→history_kernel→theta_comparator）上跨 10 个 physical_seed 实测
每条关系 r_{28≺X} 的产生步 t_r[X]，然后对每个 level-2 候选有序对 (X≺Y)
施加 TSS-3a 同款稳定性判据：

  A. 全部种子下两条父关系都产生（无 None）
  B. Δt₂ = t_r[Y] − t_r[X] 全为正（顺序不翻转）
  C. 极差 max(Δt₂)−min(Δt₂) ≤ min(Δt₂)（顺序量级可信）

与 TSS-3a 的差异：TSS-3a 测的是 pre_trace 越阈 onset（Θ 目标选点代理量），
本审计直接测**关系本身的产生步**——这是 level-2 结构真正要消费的事件，
不再用代理。

## 两级判定（EXP-C0-02 扩池版）

首轮（EXP-C0-01，候选={15,21,24}）实测结果：仅 (24≺21) 合格
（Δt₂∈[41,58] 极差17）；(15≺21) 顺序10/10稳但极差57>min29 不合格；
(24,15) 7/10 翻转 → 排除对。合格对<2，触发用户预授权的扩池裁定
（2026-09-06："扩大测量再定"）。

扩池版改为两级：
- **Stage 1（level-1 站点资格）**：候选站点扩至 d(28,X)∈[1.8,3.0] 的全部
  11 个站点。每站点对 Δt₁ = t_r[X] − t_entry[28] 施加 TSS-3a 三判据
  （全产生/全正/极差≤min）。不合格站点的关系不得进入 level-2。
- **Stage 2（level-2 对资格）**：在 Stage 1 合格站点间枚举全部无序对，
  假设方向取跨种子中位 t_r 的先后；对 Δt₂ 施加同三判据。

## 停止条件（镜像 TSS-3a）

  1. 某站点关系在部分种子下不产生 → 该站点 level-1 不合格（不修参数强救）
  2. sign 跨种子翻转 → 该对为名称伪影敏感对，登记为排除对
  3. 扩池后合格对仍 < 2 → exit 2 并打印全部实测数据，停止等待用户裁定
"""
import sys
sys.path.insert(0, '.')

from nexus_v1.components.structural_address import (
    AddressRegistry, DOMAIN_SKIN_PATCH, DOMAIN_OCC_THERMAL,
)
from nexus_v1.components.world import HeatSource
from tss.relations.boundary_process import CollectorBoundaryPort
from tss.relations.entry_gate import make_entry_gate
from tss.relations.history_kernel import make_history_kernel
from tss.relations.theta_comparator import make_theta_comparator
from tss.relations.temporal_r_prec import RPrecCircuitT1
from tss.tests.test_tss3a_theta_distance_audit import _reseed_site

DT = 0.001
N_STEPS = 1600
HEAT_RADIUS = 3.0        # 同 TSS-3a：单次外部发生覆盖全部目标站点
SOURCE_SITE = 28

# EXP-C0-02 扩池候选：d(28,X)∈[1.8,3.0] 的全部站点（实测距离，2026-09-06）
#   原三站点 15/21/24 + 新增 26/29/18/17/27/22/10/7
#   排除 d<1.8 近场站点（31 已被 TSS-3a 停止条件4否决——近场 Δt 被
#   bundle_id ±25% 增益扰动淹没）；12(d=2.38) 首轮 Δt₁∈[673,715] 距可读窗
#   723 仅 ~1% 裕量，按裕量纪律仍列入实测（由判据自然裁决，不预先豁免）
CANDIDATE_TARGETS = (15, 21, 24, 26, 29, 18, 17, 27, 22, 10, 7, 12)

# 10 个种子 = TSS-3a 原 5 个 + 新增 5 个（None=主代码默认 bundle_id 扰动）
_SEED_VARIANTS = [None, 81000, 82000, 83000, 84000,
                  85000, 86000, 87000, 88000, 89000]


def _make_address(registry, site):
    pid = f"thermpt{site}"
    parent = registry.register_physical(DOMAIN_SKIN_PATCH, pid)
    return registry.register_generated(
        DOMAIN_OCC_THERMAL, f"{pid}_warm", (parent,), 1)


def _drive_and_measure_relation_steps(seed_base):
    """单次外部发生，返回 (t_entry_28, {X: t_r or None}, {X: r 幅度})。"""
    circuit = RPrecCircuitT1()
    for s in [SOURCE_SITE] + list(CANDIDATE_TARGETS):
        _reseed_site(circuit, s, seed_base)

    patch = circuit._thermal_quantum_patches[SOURCE_SITE]
    pos = patch.world_position(circuit.world.body)
    circuit.world.heat_sources = [HeatSource(
        position=list(pos), energy=100000.0, temperature=300.0,
        radius=HEAT_RADIUS, _drift=[0.0, 0.0, 0.0])]

    registry = AddressRegistry()
    sites = [SOURCE_SITE] + list(CANDIDATE_TARGETS)
    ports, gates, kernels = {}, {}, {}
    for s in sites:
        addr = _make_address(registry, s)
        coll = circuit.thermal_quantum_collectors[f"thermpt{s}_warm"]
        ports[s] = CollectorBoundaryPort(generator_address=addr, carrier_ref=coll)
        gates[s] = make_entry_gate(ports[s])
        kernels[s] = make_history_kernel(gates[s])

    comps = {x: make_theta_comparator(kernels[SOURCE_SITE], gates[x])
             for x in CANDIDATE_TARGETS}

    t_entry_src = None
    t_r = {x: None for x in CANDIDATE_TARGETS}
    r_amp = {x: None for x in CANDIDATE_TARGETS}
    for t in range(N_STEPS):
        circuit.step({}, DT)
        b, h = {}, {}
        for s in sites:
            b[s] = gates[s].step(ports[s].spike_output, DT)
            h[s] = kernels[s].step(b[s], DT)
        if b[SOURCE_SITE] > 0.5 and t_entry_src is None:
            t_entry_src = t
        for x in CANDIDATE_TARGETS:
            r = comps[x].step(h[SOURCE_SITE], b[x], DT)
            if r > 0.0 and t_r[x] is None:
                t_r[x] = t
                r_amp[x] = r
    return t_entry_src, t_r, r_amp


def _judge(deltas, label):
    """TSS-3a 三判据。返回 (verdict, reason)：'ok'/'missing'/'sign_flip'/'spread'。"""
    if any(d is None for d in deltas):
        return "missing", f"{label}: 部分种子下不产生"
    if any(d <= 0 for d in deltas):
        n_flip = sum(1 for d in deltas if d <= 0)
        return "sign_flip", f"{label}: {n_flip}/{len(deltas)} 种子顺序翻转"
    spread = max(deltas) - min(deltas)
    if spread > min(deltas):
        return "spread", (f"{label}: 极差 {spread} > min {min(deltas)}"
                          "（顺序稳但量级不可信）")
    return "ok", (f"{label}: Δt∈[{min(deltas)},{max(deltas)}]，极差 {spread}")


def run():
    print("=" * 72)
    print("C0(EXP-C0-02 扩池)：level-1 站点资格 + level-2 关系次序对审计")
    print(f"场景：单次 HeatSource @site{SOURCE_SITE}, radius={HEAT_RADIUS}, "
          f"{N_STEPS}步, {len(_SEED_VARIANTS)}种子")
    print(f"候选站点：{CANDIDATE_TARGETS}")
    print("=" * 72)

    t_src, results, amps_all = {}, {}, []
    for sb in _SEED_VARIANTS:
        tag = "default" if sb is None else f"seed={sb}"
        te, t_r, r_amp = _drive_and_measure_relation_steps(sb)
        t_src[sb] = te
        results[sb] = t_r
        amps_all.extend(v for v in r_amp.values() if v is not None)
        print(f"  {tag:<14s} entry28={te}  t_r={t_r}")

    # ── Stage 1：level-1 站点资格（Δt₁ = t_r[X] − t_entry[28]）──
    print("\n" + "=" * 72)
    print("Stage 1：level-1 站点资格（TSS-3a 三判据施加于 Δt₁）")
    print("=" * 72)
    l1_ok = []
    for x in CANDIDATE_TARGETS:
        deltas = [None if (results[sb][x] is None or t_src[sb] is None)
                  else results[sb][x] - t_src[sb]
                  for sb in _SEED_VARIANTS]
        verdict, msg = _judge(deltas, f"site{x} Δt₁")
        mark = "✓" if verdict == "ok" else "✗"
        print(f"  {mark} {msg}")
        if verdict == "ok":
            l1_ok.append(x)
    print(f"\n  level-1 合格站点：{l1_ok}")

    # ── Stage 2：level-2 对资格（合格站点间全枚举，方向取中位次序）──
    print("\n" + "=" * 72)
    print("Stage 2：level-2 关系次序对资格")
    print("=" * 72)
    qualified, excluded = [], []
    for i in range(len(l1_ok)):
        for j in range(i + 1, len(l1_ok)):
            a, b_site = l1_ok[i], l1_ok[j]
            med = sorted(results[sb][a] - results[sb][b_site]
                         for sb in _SEED_VARIANTS)[len(_SEED_VARIANTS) // 2]
            x, y = (a, b_site) if med < 0 else (b_site, a)   # 假设方向=中位次序
            deltas = [results[sb][y] - results[sb][x] for sb in _SEED_VARIANTS]
            verdict, msg = _judge(deltas, f"({x}≺{y}) Δt₂")
            mark = "✓" if verdict == "ok" else "✗"
            print(f"  {mark} {msg}")
            if verdict == "ok":
                qualified.append((x, y, min(deltas), max(deltas)))
            else:
                excluded.append((x, y, verdict))

    print("\n" + "=" * 72)
    print(f"合格对：{[(q[0], q[1], f'[{q[2]},{q[3]}]') for q in qualified]}")
    print(f"排除对：{excluded}")
    if amps_all:
        print(f"r 幅度实测范围：[{min(amps_all):.4f}, {max(amps_all):.4f}]"
              f"（n={len(amps_all)}，供 C1-1 标定交叉核对）")
    print("=" * 72)

    if len(qualified) < 2:
        print("→ 停止条件3：扩池后合格对仍 < 2。停止，等待用户裁定。")
        return 2
    print("→ C0 PASS：合格对 ≥2，冻结进 coupling_contract.py 进入 C1。")
    return 0


if __name__ == "__main__":
    sys.exit(run())
