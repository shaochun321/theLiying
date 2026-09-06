"""tss.tests.test_c1_coupling — C1：关系次序耦合候选 c_ro 资格测试(T-C1-1~11)。

TYPE:INFRA

路线依据：08_路线图 §10 C1（实现、阻断、不可约与共参验证）+ §9 交付格式
+ §11 最终成功判据。契约与目标对：coupling_contract.py（EXP-C0-02 冻结）。

命名纪律：全程称 **c_ro（关系次序耦合候选）**，不称"方向"；本套测试
通过 ≠ 宣称新生成元（K-05），仅取得"耦合输出/组织候选"资格。

测试映射（§6.2 六项模板 + §9 交付格式）：
  T-C1-1  正例：10 种子真实链路，3 个代表对 c_ro 恰在后继关系产生步输出
  T-C1-2  单输入负例：仅父 A / 仅父 B → 精确零
  T-C1-3  交换负例：B 先 A 后 → 零（§6.2⑤ 绑定）
  T-C1-4  超窗负例：Δt₂=800 → 零；对照 Δt₂=300 窗内产生
  T-C1-5  阻断实验 ×2：阻断父 A / 父 B → c_ro 消失+下游可测差异（§6.2④）
  T-C1-6  不可约实验：记忆无关同类运算 ≡0；序盲对称基线不区分交换序
          而 c_ro 区分（§6.2⑤）
  T-C1-7  共参：level-1/level-2 三件套同类同默认参数；适配器全实例同参
  T-C1-8  阴性对照：排除对 (29,26) 跨 10 种子方向不一致 → 不可取得资格
  T-C1-9  谱系：c_ro 携带深度 2 父谱系；适配器静态审计
  T-C1-10 非学习依赖：全链 frozen，运行前后权重零变化
  T-C1-11 §11 判据核对：真实发生→b^↑→r→c_ro→可阻断下游，单次跑通

真实链路测量（T-C1-1/8/11 共享）：单次外部发生 @site28，10 种子
（同 EXP-C0-02），一次驱动同时测量全部代表对与阴性对——测量一遍，
三个测试消费同一份数据（缓存于模块级，不重复驱动）。
"""
import sys
sys.path.insert(0, '.')

import inspect

from nexus_v1.components.semiconductor import Capacitor
from nexus_v1.components.structural_address import (
    AddressRegistry, DOMAIN_SKIN_PATCH, DOMAIN_OCC_THERMAL,
    DOMAIN_RELATION_PREC,
)
from nexus_v1.components.world import HeatSource
from tss.relations.boundary_process import CollectorBoundaryPort
from tss.relations.entry_gate import PhysicalEntryGate, make_entry_gate
from tss.relations.history_kernel import PhysicalHistoryKernel, make_history_kernel
from tss.relations.theta_comparator import PhysicalThetaComparator, make_theta_comparator
from tss.relations.relation_event_adapter import (
    RelationEventAdapter, RelationInputNeuron,
    _COLLECTOR_CAPACITANCE, _ADAPTER_PHYSICAL_SEED,
)
from tss.relations.coupling_contract import (
    COUPLING_SOURCE_SITE, C1_REPRESENTATIVE_PAIRS, C1_NEGATIVE_CONTROL_PAIR,
    QUALIFIED_LEVEL2_PAIRS,
)
from tss.relations.temporal_r_prec import RPrecCircuitT1
from tss.tests.test_tss3a_theta_distance_audit import _reseed_site

DT = 0.001
N_STEPS = 1600
HEAT_RADIUS = 3.0
SRC = COUPLING_SOURCE_SITE
T_READ = 723
_SEED_VARIANTS = [None, 81000, 82000, 83000, 84000,
                  85000, 86000, 87000, 88000, 89000]

# 真实链路涉及的全部目标站点（3 代表对 ∪ 阴性对）
_REP = C1_REPRESENTATIVE_PAIRS                       # ((24,21),(29,27),(26,17))
_NEG = C1_NEGATIVE_CONTROL_PAIR                      # (29, 26)
_ALL_TARGETS = tuple(sorted({s for p in _REP for s in p} | set(_NEG)))


def _make_l1_address(registry, site):
    pid = f"thermpt{site}"
    parent = registry.register_physical(DOMAIN_SKIN_PATCH, pid)
    return registry.register_generated(
        DOMAIN_OCC_THERMAL, f"{pid}_warm", (parent,), 1)


class _PairStack:
    """一个 (X≺Y) 的 level-2 栈：两适配器共享（外部传入）+ 专属门/核/比较器。"""

    def __init__(self, registry, adapters, x, y, tag=""):
        self.x, self.y = x, y
        self.ad_x, self.ad_y = adapters[x], adapters[y]
        self.gate2_x = make_entry_gate(self.ad_x.port)
        self.kernel2_x = make_history_kernel(self.gate2_x)
        self.gate2_y = make_entry_gate(self.ad_y.port)
        self.comp2 = make_theta_comparator(self.kernel2_x, self.gate2_y)
        self.fire_steps = []
        self.downstream = Capacitor(capacitance=1.0, charge=0.0)

    def step(self, t, dt):
        b2x = self.gate2_x.step(self.ad_x.port.spike_output, dt)
        h2x = self.kernel2_x.step(b2x, dt)
        b2y = self.gate2_y.step(self.ad_y.port.spike_output, dt)
        c = self.comp2.step(h2x, b2y, dt)
        if c > 0.0:
            self.fire_steps.append(t)
        self.downstream.inject(c, 1.0)
        return c


def _drive_full_stack(seed_base):
    """单次外部发生：level-1 全链 + 共享适配器 + 全部 pair 栈 + 阻断孪生。

    返回 dict：t_entry_src / t_r[X] / 各栈 fire_steps / 下游电压。
    """
    circuit = RPrecCircuitT1()
    for s in [SRC] + list(_ALL_TARGETS):
        _reseed_site(circuit, s, seed_base)
    patch = circuit._thermal_quantum_patches[SRC]
    pos = patch.world_position(circuit.world.body)
    circuit.world.heat_sources = [HeatSource(
        position=list(pos), energy=100000.0, temperature=300.0,
        radius=HEAT_RADIUS, _drift=[0.0, 0.0, 0.0])]

    registry = AddressRegistry()
    sites = [SRC] + list(_ALL_TARGETS)
    ports, gates, kernels = {}, {}, {}
    for s in sites:
        addr = _make_l1_address(registry, s)
        coll = circuit.thermal_quantum_collectors[f"thermpt{s}_warm"]
        ports[s] = CollectorBoundaryPort(generator_address=addr, carrier_ref=coll)
        gates[s] = make_entry_gate(ports[s])
        kernels[s] = make_history_kernel(gates[s])
    comps1 = {x: make_theta_comparator(kernels[SRC], gates[x])
              for x in _ALL_TARGETS}

    # 共享适配器：每条 level-1 关系一个（关系→事件流是关系自己的性质）
    adapters = {x: RelationEventAdapter(
        registry, kernels[SRC].generator_address, gates[x].generator_address,
        f"rel{SRC}p{x}") for x in _ALL_TARGETS}
    # 阻断孪生适配器（(24≺21) 的父 A 阻断版：r_24 被切断，永远喂 0）
    blk_a = RelationEventAdapter(
        registry, kernels[SRC].generator_address, gates[24].generator_address,
        f"rel{SRC}p24_blkA")
    adapters_blk = dict(adapters)
    adapters_blk[24] = blk_a

    stacks = {p: _PairStack(registry, adapters, p[0], p[1]) for p in _REP}
    neg_fwd = _PairStack(registry, adapters, _NEG[0], _NEG[1])
    neg_rev = _PairStack(registry, adapters, _NEG[1], _NEG[0])
    blk_stack = _PairStack(registry, adapters_blk, 24, 21)   # 父A阻断孪生

    t_entry_src = None
    t_r = {x: None for x in _ALL_TARGETS}
    for t in range(N_STEPS):
        circuit.step({}, DT)
        b1, h1 = {}, {}
        for s in sites:
            b1[s] = gates[s].step(ports[s].spike_output, DT)
            h1[s] = kernels[s].step(b1[s], DT)
        if b1[SRC] > 0.5 and t_entry_src is None:
            t_entry_src = t
        for x in _ALL_TARGETS:
            r = comps1[x].step(h1[SRC], b1[x], DT)
            if r > 0.0 and t_r[x] is None:
                t_r[x] = t
            adapters[x].step(r, DT)
        blk_a.step(0.0, DT)          # 阻断：父A关系电流被切断
        for st in list(stacks.values()) + [neg_fwd, neg_rev, blk_stack]:
            st.step(t, DT)

    return {
        "t_entry_src": t_entry_src, "t_r": t_r,
        "rep_fires": {p: stacks[p].fire_steps for p in _REP},
        "rep_downstream": {p: stacks[p].downstream.voltage for p in _REP},
        "neg_fwd_fires": neg_fwd.fire_steps, "neg_rev_fires": neg_rev.fire_steps,
        "blk_fires": blk_stack.fire_steps,
        "blk_downstream": blk_stack.downstream.voltage,
    }


_MEASURED = None


def _measured():
    """10 种子真实链路测量（惰性，全套测试共享一份）。"""
    global _MEASURED
    if _MEASURED is None:
        _MEASURED = {}
        for sb in _SEED_VARIANTS:
            _MEASURED[sb] = _drive_full_stack(sb)
            tag = "default" if sb is None else f"seed={sb}"
            m = _MEASURED[sb]
            print(f"    [{tag}] t_r={m['t_r']}  rep_fires="
                  f"{ {p: m['rep_fires'][p] for p in _REP} }")
    return _MEASURED


# ─────────────────────────────────────────────────────────────────────
# 合成链路工具（负例/不可约/非学习依赖用）
# ─────────────────────────────────────────────────────────────────────

def _synthetic_stack():
    """无电路合成栈：两个适配器 + 一个 pair 栈，r 脉冲由调用方手工馈入。"""
    registry = AddressRegistry()
    a_i = _make_l1_address(registry, 28)
    a_x = _make_l1_address(registry, 24)
    a_y = _make_l1_address(registry, 21)
    ad_x = RelationEventAdapter(registry, a_i, a_x, "syn_x")
    ad_y = RelationEventAdapter(registry, a_i, a_y, "syn_y")
    st = _PairStack(registry, {24: ad_x, 21: ad_y}, 24, 21)
    return ad_x, ad_y, st


def _run_synthetic(r_a_steps, r_b_steps, n, r_amp=0.17):
    """馈入手工 r 脉冲序列，返回 (fire_steps, downstream_v, ad_x, ad_y, st)。"""
    ad_x, ad_y, st = _synthetic_stack()
    for t in range(n):
        ad_x.step(r_amp if t in r_a_steps else 0.0, DT)
        ad_y.step(r_amp if t in r_b_steps else 0.0, DT)
        st.step(t, DT)
    return st.fire_steps, st.downstream.voltage, ad_x, ad_y, st


# ─────────────────────────────────────────────────────────────────────
# T-C1-1 ~ T-C1-11
# ─────────────────────────────────────────────────────────────────────

def test_c1_1_real_chain_positive():
    """T-C1-1：10 种子真实链路，3 代表对 c_ro 恰在后继关系产生步输出一次。"""
    m = _measured()
    for (x, y) in _REP:
        for sb in _SEED_VARIANTS:
            data = m[sb]
            fires = data["rep_fires"][(x, y)]
            assert data["t_r"][x] is not None and data["t_r"][y] is not None, (
                f"T-C1-1 前提：({x},{y}) 父关系应在全部种子产生（C0 已审计）")
            dt2 = data["t_r"][y] - data["t_r"][x]
            assert fires == [data["t_r"][y]], (
                f"T-C1-1: ({x}≺{y}) seed={sb} c_ro 产生步 {fires} ≠ "
                f"后继关系步 [{data['t_r'][y]}]")
            assert 0 < dt2 < T_READ, (
                f"T-C1-1: ({x}≺{y}) seed={sb} Δt₂={dt2} 不在窗内却产生")
    print(f"T-C1-1: 3 代表对 × 10 种子 = 30 次驱动全部恰在后继关系步"
          f"单次产生 c_ro，Δt₂ 全部窗内")
    print("✓ T-C1-1 PASS")


def test_c1_2_single_parent_zero():
    """T-C1-2：仅父 A / 仅父 B → c_ro 精确零。"""
    fires_a, v_a, *_ = _run_synthetic({100}, set(), 900)
    assert fires_a == [] and v_a == 0.0, (
        f"T-C1-2: 仅父A应零产生，得 fires={fires_a}, v={v_a}")
    fires_b, v_b, *_ = _run_synthetic(set(), {100}, 900)
    assert fires_b == [] and v_b == 0.0, (
        f"T-C1-2: 仅父B应零产生，得 fires={fires_b}, v={v_b}")
    print("T-C1-2: 仅A/仅B → c_ro≡0、下游电压精确 0.0")
    print("✓ T-C1-2 PASS")


def test_c1_3_swap_zero():
    """T-C1-3：交换次序（B@100 先 A@400 后）→ c_ro 精确零。"""
    fires, v, *_ = _run_synthetic({400}, {100}, 900)
    assert fires == [] and v == 0.0, (
        f"T-C1-3: B先A后应零产生，得 fires={fires}, v={v}")
    print("T-C1-3: 交换次序 → c_ro≡0（严格先序由 level-2 H_τ 充电前读出保证）")
    print("✓ T-C1-3 PASS")


def test_c1_4_beyond_window_zero():
    """T-C1-4：Δt₂=800 超窗 → 零；对照 Δt₂=300 窗内产生。"""
    fires, v, *_ = _run_synthetic({0}, {800}, 900)
    assert fires == [] and v == 0.0, (
        f"T-C1-4: Δt₂=800 超窗应零产生，得 {fires}")
    fires2, v2, *_ = _run_synthetic({0}, {300}, 900)
    assert fires2 == [300] and v2 > 0.0, (
        f"T-C1-4 对照失败：Δt₂=300 窗内应产生（得 {fires2}）——"
        "链路坏死，超窗零不可作资格证据")
    print(f"T-C1-4: Δt₂=800 → 0；对照 Δt₂=300 → 产生@300，下游 v={v2:.4f}")
    print("✓ T-C1-4 PASS")


def test_c1_5_blocking_both_parents():
    """T-C1-5：阻断父 A / 父 B → c_ro 消失且下游可测差异（§6.2④）。"""
    # 正常
    fires_n, v_n, *_ = _run_synthetic({0}, {300}, 600)
    assert fires_n and v_n > 0.0
    # 阻断父 A（A 的 r 流被切断）
    fires_ba, v_ba, *_ = _run_synthetic(set(), {300}, 600)
    # 阻断父 B
    fires_bb, v_bb, *_ = _run_synthetic({0}, set(), 600)
    assert fires_ba == [] and v_ba == 0.0, "T-C1-5: 阻断父A后仍产生"
    assert fires_bb == [] and v_bb == 0.0, "T-C1-5: 阻断父B后仍产生"
    assert v_n - v_ba > 1e-6 and v_n - v_bb > 1e-6

    # 真实链路旁证：(24≺21) 阻断孪生（10 种子全部零产生零下游）
    m = _measured()
    for sb in _SEED_VARIANTS:
        assert m[sb]["blk_fires"] == [] and m[sb]["blk_downstream"] == 0.0, (
            f"T-C1-5: seed={sb} 真实链路阻断孪生仍产生")
    print(f"T-C1-5: 合成阻断A/B → 零；正常 v={v_n:.4f}；"
          f"真实链路阻断孪生 10 种子全零")
    print("✓ T-C1-5 PASS")


def test_c1_6_irreducibility():
    """T-C1-6：不可约（§6.2⑤）——两条同类简单运算基线都无法重构 c_ro。

    基线1（记忆无关）：min(r_A(t), r_B(t)) 逐步同类运算——父脉冲不同步，
      全程恒零，连共现都测不到 ⇒ 次序信息必须有历史载体（H_τ）。
    基线2（序盲对称）：正反两方向栈输出之和（同类部件的对称组合）——
      A→B 与 B→A 两种次序下都产生 ⇒ 无法区分交换序；c_ro 只在 A→B 产生。
    """
    n, r_amp = 900, 0.17

    # ── 基线1：记忆无关 min(r_A, r_B) ──
    memoryless_sum = 0.0
    for t in range(n):
        r_a = r_amp if t == 0 else 0.0
        r_b = r_amp if t == 300 else 0.0
        memoryless_sum += min(r_a, r_b)
    assert memoryless_sum == 0.0, "T-C1-6: 父脉冲不同步，记忆无关基线应恒零"

    # ── 场景 A→B ──
    fires_fwd_ab, _, ad_x, ad_y, _ = _run_synthetic({0}, {300}, n)
    # 序盲基线需要反向栈：同一场景下 B≺A 方向
    registry = AddressRegistry()
    a_i = _make_l1_address(registry, 28)
    a_x = _make_l1_address(registry, 24)
    a_y = _make_l1_address(registry, 21)
    def _both_directions(steps_a, steps_b):
        adx = RelationEventAdapter(registry, a_i, a_x,
                                   f"irr_x_{len(steps_a)}_{min(steps_a | steps_b)}")
        ady = RelationEventAdapter(registry, a_i, a_y,
                                   f"irr_y_{len(steps_b)}_{max(steps_a | steps_b)}")
        fwd = _PairStack(registry, {24: adx, 21: ady}, 24, 21)
        rev = _PairStack(registry, {24: adx, 21: ady}, 21, 24)
        for t in range(n):
            adx.step(r_amp if t in steps_a else 0.0, DT)
            ady.step(r_amp if t in steps_b else 0.0, DT)
            fwd.step(t, DT)
            rev.step(t, DT)
        return len(fwd.fire_steps), len(rev.fire_steps)

    fwd_ab, rev_ab = _both_directions({0}, {300})     # A→B
    fwd_ba, rev_ba = _both_directions({300}, {0})     # B→A
    sym_ab, sym_ba = fwd_ab + rev_ab, fwd_ba + rev_ba
    assert sym_ab == sym_ba == 1, (
        f"T-C1-6: 序盲对称基线两次序下应同为1，得 {sym_ab}/{sym_ba}")
    assert (fwd_ab, fwd_ba) == (1, 0), (
        f"T-C1-6: c_ro 应仅在 A→B 产生，得 A→B:{fwd_ab} B→A:{fwd_ba}")

    print("T-C1-6: 记忆无关基线恒零（脉冲不同步）；序盲对称基线 A→B/B→A "
          "均=1 不可区分；c_ro=(1,0) 区分次序——两条同类简单运算均无法重构")
    print("✓ T-C1-6 PASS")


def test_c1_7_shared_params_across_levels():
    """T-C1-7：level-1/level-2 三件套同类同默认参数；适配器全实例同参。"""
    ad_x, ad_y, st = _synthetic_stack()
    registry = AddressRegistry()
    a1 = _make_l1_address(registry, 28)
    a2 = _make_l1_address(registry, 21)
    g1 = PhysicalEntryGate(generator_address=a1)
    k1 = PhysicalHistoryKernel(generator_address=a1)
    c1 = PhysicalThetaComparator(address_i=a1, address_j=a2)

    assert type(st.gate2_x) is type(g1) and type(st.kernel2_x) is type(k1) \
        and type(st.comp2) is type(c1), "T-C1-7: level-2 使用了不同类"
    assert (st.gate2_x.capacitance, st.gate2_x.r_leak, st.gate2_x.v_clamp,
            st.gate2_x.theta_gate, st.gate2_x.q_spike) == (
        g1.capacitance, g1.r_leak, g1.v_clamp, g1.theta_gate, g1.q_spike), (
        "T-C1-7: level-2 gate 参数偏离默认")
    assert (st.kernel2_x.capacitance, st.kernel2_x.r_leak,
            st.kernel2_x.q_pulse) == (
        k1.capacitance, k1.r_leak, k1.q_pulse), "T-C1-7: level-2 kernel 参数偏离"
    assert (st.comp2.theta_h, st.comp2.theta_g, st.comp2.gm) == (
        c1.theta_h, c1.theta_g, c1.gm), "T-C1-7: level-2 comparator 参数偏离"

    # 适配器同参（同电容/同权重/同 physical_seed ⇒ 同扰动）
    assert ad_x.collector.config.capacitance == ad_y.collector.config.capacitance \
        == _COLLECTOR_CAPACITANCE
    assert ad_x.bundle.config.physical_seed == ad_y.bundle.config.physical_seed \
        == _ADAPTER_PHYSICAL_SEED
    assert ad_x.bundle.config.initial_weight == ad_y.bundle.config.initial_weight

    print("T-C1-7: 门/核/比较器 level-1↔level-2 同类同参；适配器同电容"
          f"({_COLLECTOR_CAPACITANCE:.3e})同种子({_ADAPTER_PHYSICAL_SEED})")
    print("✓ T-C1-7 PASS")


def test_c1_8_negative_control_pair():
    """T-C1-8：排除对 (29,26) 跨 10 种子方向不一致 → 不可取得资格。

    EXP-C0-02 判定该对 5/10 种子顺序翻转。此处在完整 level-2 栈上验证：
    正/反方向 c_ro 的产生模式跨种子不一致（存在两方向都产生过、或产生
    方向翻转）——一致性是资格前提，不一致即不可入合格对集合。
    """
    m = _measured()
    fwd_fired = [sb for sb in _SEED_VARIANTS if m[sb]["neg_fwd_fires"]]
    rev_fired = [sb for sb in _SEED_VARIANTS if m[sb]["neg_rev_fires"]]
    n_fwd, n_rev = len(fwd_fired), len(rev_fired)
    consistent = (n_fwd == len(_SEED_VARIANTS) and n_rev == 0) or \
                 (n_rev == len(_SEED_VARIANTS) and n_fwd == 0)
    assert not consistent, (
        f"T-C1-8: 排除对在 10 种子上方向完全一致(fwd={n_fwd},rev={n_rev})"
        "——与 EXP-C0-02 审计矛盾，须重查")
    assert ( _NEG[0], _NEG[1]) not in [(p[0], p[1]) for p in QUALIFIED_LEVEL2_PAIRS], (
        "T-C1-8: 阴性对照对不应出现在合格对清单")
    print(f"T-C1-8: (29≺26) 10 种子产生分布 fwd={n_fwd}/10, rev={n_rev}/10 "
          "——方向不一致，确认不可取得资格（与 EXP-C0-02 一致）")
    print("✓ T-C1-8 PASS")


def test_c1_9_lineage_and_static_audit():
    """T-C1-9：深度 2 父谱系正确；适配器静态审计（无软件时钟/禁止引用）。"""
    ad_x, ad_y, st = _synthetic_stack()
    addr = ad_x.generator_address
    assert addr.domain == DOMAIN_RELATION_PREC
    assert addr.generation_depth == 2
    assert len(addr.parent_addresses) == 2, "T-C1-9: 关系地址应有两个父端"
    # c_ro 比较器的谱系两端 = 两条父关系的地址
    assert st.comp2.address_i is ad_x.generator_address
    assert st.comp2.address_j is ad_y.generator_address

    sig = inspect.signature(RelationEventAdapter.step)
    assert "t_step" not in sig.parameters, "T-C1-9: adapter.step 含软件时钟"
    import tss.relations.relation_event_adapter as mod
    src = inspect.getsource(mod)
    code_lines, in_doc = [], False
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
    # 换能先例允许写 pre_trace（bundle 兼容），故只审计 Occurrence/相位字段
    for token in ("Occurrence", "_phase", "rearm_min_steps"):
        assert token not in code, (
            f"T-C1-9: 适配器可执行代码含禁止对象 {token!r}")

    print("T-C1-9: 地址域=relation.r_prec，深度=2，父=关系两端；"
          "step 无 t_step；无 Occurrence/相位字段引用")
    print("✓ T-C1-9 PASS")


def test_c1_10_no_learning_dependency():
    """T-C1-10：全链 frozen，运行前后权重零变化（F-10/CG-0a 条 3）。"""
    ad_x, ad_y, st = _synthetic_stack()
    assert ad_x.bundle.config.learning_rule == "frozen"
    w_before = [m.w for row in ad_x.bundle._memristors for m in row]
    for t in range(600):
        ad_x.step(0.17 if t == 0 else 0.0, DT)
        ad_y.step(0.17 if t == 300 else 0.0, DT)
        st.step(t, DT)
    w_after = [m.w for row in ad_x.bundle._memristors for m in row]
    assert st.fire_steps, "T-C1-10 前提：正常场景应产生 c_ro"
    assert w_before == w_after, (
        f"T-C1-10: frozen 束权重发生变化 {w_before} → {w_after}")
    print(f"T-C1-10: c_ro 在零学习(全frozen)下产生；权重前后一致 {w_before}")
    print("✓ T-C1-10 PASS")


def test_c1_11_final_criterion_chain():
    """T-C1-11：§11 最终成功判据单次跑通——
    多个真实基础发生 → 合格关系 → 非学习依赖耦合 → 可阻断独立输出。"""
    m = _measured()
    d = m[None]   # default 种子的真实链路
    # ① 真实基础发生（源+两目标站点全部进入）
    assert d["t_entry_src"] is not None
    assert d["t_r"][24] is not None and d["t_r"][21] is not None
    # ② 合格基础生成算子关系（r_{28≺24}, r_{28≺21} 产生）
    # （t_r 非 None 即关系产生——比较器只在关系成立时输出）
    # ③ 非学习依赖的耦合输出（c_ro 产生；无 STDP/DA 参与，见 T-C1-10）
    assert d["rep_fires"][(24, 21)], "T-C1-11: c_ro 未产生"
    # ④ 可阻断的独立输出作用（下游电容：正常>0，阻断孪生==0）
    v_n = d["rep_downstream"][(24, 21)]
    v_b = d["blk_downstream"]
    assert v_n > 0.0 and v_b == 0.0 and v_n - v_b > 1e-6, (
        f"T-C1-11: 下游差异不成立 normal={v_n} blocked={v_b}")
    print(f"T-C1-11: 真实发生@{d['t_entry_src']} → r@{d['t_r'][24]}/"
          f"{d['t_r'][21]} → c_ro@{d['rep_fires'][(24, 21)]} → "
          f"下游 {v_n:.4f} vs 阻断 {v_b:.4f}——§11 链条单次跑通")
    print("✓ T-C1-11 PASS")


def main():
    tests = [
        test_c1_1_real_chain_positive,
        test_c1_2_single_parent_zero,
        test_c1_3_swap_zero,
        test_c1_4_beyond_window_zero,
        test_c1_5_blocking_both_parents,
        test_c1_6_irreducibility,
        test_c1_7_shared_params_across_levels,
        test_c1_8_negative_control_pair,
        test_c1_9_lineage_and_static_audit,
        test_c1_10_no_learning_dependency,
        test_c1_11_final_criterion_chain,
    ]
    passed = 0
    for fn in tests:
        print(f"\n{'=' * 68}\n{fn.__name__}\n{'=' * 68}")
        fn()
        passed += 1
    print(f"\n{'=' * 68}\nC1 关系次序耦合候选 c_ro: {passed}/{len(tests)} PASS"
          f"\n{'=' * 68}")
    return 0 if passed == len(tests) else 1


if __name__ == "__main__":
    sys.exit(main())
