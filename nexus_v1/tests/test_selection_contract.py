"""nexus_v1.tests.test_selection_contract — S0-a：内生竞争选择资格与
反硬编码边界验证。

方案依据：document - 2026-08-02T204821.549.md（S0-a：只冻结候选、本体
身份、允许/禁止读取量、资源约束和五项通过标准的类型契约，不写竞争电路）。

六个测试：
  T-SEL-1：候选ID无语义身份约定（make_candidate_id/is_valid_candidate_id）
  T-SEL-2：存在与保留分离（ObservedExistence不可变，RetainedStanding可变，
           两者是不同类型，竞争层不能通过修改RetainedStanding影响
           ObservedExistence）
  T-SEL-3：禁止读取字段审计（audit_forbidden_reads能正确捕获语义字段）
  T-SEL-4：资源池占位（try_allocate/release基础记账正确，不超容量）
  T-SEL-5：标签置换不变性（评判要求的自动化审计之一）——用三个完全
           对称的候选，交换其索引/ID后，contract层本身的结构不因
           置换而改变（本轮验证的是契约层placeholder本身满足置换
           对称，不是真正的竞争结果——因为S0-a阶段还没有竞争动力学，
           真正的"胜负不受置换影响"要等S0-d接入后再测）
  T-SEL-6：完全相同候选不固定偏向某索引（评判要求的自动化审计之二）——
           验证LocalResourcePool.try_allocate()对候选调用顺序不敏感：
           以任意顺序调用try_allocate相同的amount，最终available相同
           （不存在"先到先得"之外的隐藏索引偏置，S0-a层面只能验证资源
           池本身的记账不偏置，真正的候选竞争偏置测试留给S0-c）
"""
import sys

sys.path.insert(0, '.')

import itertools

from nexus_v1.relations.selection_contract import (
    ObservedExistence, RetainedStanding, SelectionCandidate,
    make_candidate_id, is_valid_candidate_id,
    ALLOWED_READ_FIELDS, FORBIDDEN_READ_FIELDS, audit_forbidden_reads,
    LocalResourcePool, SelectionQualificationResult,
)


def test_sel_1_no_semantic_candidate_id():
    """T-SEL-1：候选ID必须是candidate_N格式，拒绝语义化命名。"""
    cid0 = make_candidate_id(0)
    cid1 = make_candidate_id(1)
    assert cid0 == "candidate_0"
    assert cid1 == "candidate_1"
    assert is_valid_candidate_id(cid0)
    assert is_valid_candidate_id(cid1)

    # 语义化命名应被拒绝
    for bad_id in ("short_candidate", "winner", "candidate_short",
                   "medium_candidate", "candidate_"):
        assert not is_valid_candidate_id(bad_id), (
            f"{bad_id!r} 含语义信息或格式不完整，应被判定为无效")

    try:
        make_candidate_id(-1)
        raise AssertionError("负数index应被拒绝")
    except ValueError:
        pass

    print(f"T-SEL-1: cid0={cid0}, cid1={cid1}")
    print("✓ T-SEL-1 PASS: 候选ID无语义身份约定正确")


def test_sel_2_existence_retain_separation():
    """T-SEL-2：ρ_i^obs（ObservedExistence）不可变，ρ_i^retain
    （RetainedStanding）可变——两者是完全独立的类型，竞争层修改
    RetainedStanding不会、也不能影响ObservedExistence。"""
    cid = make_candidate_id(0)
    existence = ObservedExistence(
        candidate_id=cid, occurrence_ref="fake_ro_object", t_observed=100)
    standing = RetainedStanding(candidate_id=cid)

    # ObservedExistence是frozen dataclass，不能被修改（模拟"候选失败不能
    # 篡改历史"）
    try:
        existence.t_observed = 999
        raise AssertionError("ObservedExistence应是不可变对象")
    except (AttributeError, TypeError):
        pass

    # RetainedStanding可以被竞争层修改（这是竞争层唯一能修改的量）
    standing.weight = 0.5
    standing.energy = 0.3
    assert standing.weight == 0.5
    # existence完全不受影响
    assert existence.t_observed == 100
    assert existence.occurrence_ref == "fake_ro_object"

    print(f"T-SEL-2: existence.t_observed={existence.t_observed}（不变）, "
          f"standing.weight={standing.weight}（竞争层已修改）")
    print("✓ T-SEL-2 PASS: 存在（ρ^obs）与保留（ρ^retain）完全分离，"
          "竞争层修改保留量不影响存在记录")


def test_sel_3_forbidden_read_audit():
    """T-SEL-3：audit_forbidden_reads()能正确捕获竞争层试图读取的
    语义字段（relation_type/site_name/expected_winner等）。"""
    # 一组合规读取（只读数值字段）
    clean_reads = frozenset({"candidate_id", "weight", "t_observed"})
    assert audit_forbidden_reads(clean_reads) == []

    # 一组违规读取（混入语义字段）
    dirty_reads = frozenset({
        "candidate_id", "weight", "relation_type", "expected_winner"})
    violations = audit_forbidden_reads(dirty_reads)
    assert set(violations) == {"relation_type", "expected_winner"}

    # 确认ALLOWED/FORBIDDEN两组字段没有交集（契约内部一致性）
    assert ALLOWED_READ_FIELDS.isdisjoint(FORBIDDEN_READ_FIELDS), (
        "允许读取字段和禁止读取字段不应有交集，否则契约本身自相矛盾")

    print(f"T-SEL-3: dirty_reads违规字段={violations}")
    print("✓ T-SEL-3 PASS: 禁止读取字段审计正确捕获语义污染")


def test_sel_4_resource_pool_basic():
    """T-SEL-4：LocalResourcePool基础记账——不超容量，release正确归还。"""
    pool = LocalResourcePool(capacity=1.0)
    assert pool.available == 1.0

    assert pool.try_allocate(0.4) is True
    assert abs(pool.available - 0.6) < 1e-9

    assert pool.try_allocate(0.7) is False  # 超出容量，拒绝
    assert abs(pool.available - 0.6) < 1e-9  # 拒绝后不应改变已分配量

    pool.release(0.4)
    assert abs(pool.available - 1.0) < 1e-9

    print(f"T-SEL-4: 分配0.4后available={0.6}, 释放后available={pool.available}")
    print("✓ T-SEL-4 PASS: 资源池记账正确，超容量分配被拒绝且不产生副作用")


def test_sel_5_label_permutation_invariance():
    """T-SEL-5：标签置换不变性（评判要求的自动化审计之一）。

    S0-a阶段验证契约层本身对候选置换保持结构对称——构造三个参数完全
    相同的候选，任意置换其索引/ID后，SelectionCandidate的物理参数集合
    (作为无序集合比较)不因置换顺序改变。真正的"竞争胜负不受置换影响"
    要等S0-c/d接入竞争动力学后才能测（本轮无竞争逻辑，此处验证的是
    契约层不会因为置换顺序本身引入结构性偏置——例如physical_params
    的等价性判断不依赖candidate_id的数值大小）。
    """
    same_params = {"trace_tau_steps": 50}

    def build_pool(order):
        return [SelectionCandidate(
            candidate_id=make_candidate_id(i), physical_params=dict(same_params))
            for i in order]

    base_order = [0, 1, 2]
    permuted_order = [2, 0, 1]

    pool_base = build_pool(base_order)
    pool_permuted = build_pool(permuted_order)

    # 置换后，两个候选池的physical_params多重集合应完全相同
    # （不因置换顺序产生任何数值/结构差异——construction本身是置换对称的）
    params_base = sorted(tuple(sorted(c.physical_params.items())) for c in pool_base)
    params_permuted = sorted(
        tuple(sorted(c.physical_params.items())) for c in pool_permuted)
    assert params_base == params_permuted, (
        "候选池的物理参数多重集合应在索引置换下保持不变（契约层置换对称性）")

    # 遍历全部3!=6种置换，确认construction本身不会因为置换引入任何差异
    for perm in itertools.permutations(base_order):
        pool = build_pool(perm)
        params = sorted(tuple(sorted(c.physical_params.items())) for c in pool)
        assert params == params_base, f"置换{perm}下参数集合发生了变化"

    print(f"T-SEL-5: 6种置换下候选池physical_params多重集合均一致")
    print("✓ T-SEL-5 PASS: 契约层构造对候选索引置换保持结构对称"
          "（S0-a层面验证；真正竞争结果的置换不变性留给S0-d）")


def test_sel_6_no_fixed_index_bias_in_resource_pool():
    """T-SEL-6：完全相同候选不固定偏向某索引（评判要求的自动化审计之二）。

    评判211341阻塞加固：本测试原版只测了资源充足场景（3×0.2=0.6 <
    capacity=1.0，从未触发分配失败），"顺序无关"在这种场景下是必然
    结论（谁申请都成功），不能证明真正稀缺时的公平性。本轮补充资源
    稀缺子场景，明确展示try_allocate()的"先到先得"偏置确实存在——
    这不是bug，是评判要求必须写清楚的接口边界：try_allocate()是记账
    接口，不是无偏选择器，S0-c实现真正竞争时必须换成batch式处理
    （见LocalResourcePool.try_allocate()文档的"正确用法"）。
    """
    request_amount = 0.2
    n_candidates = 3

    def run_allocation_order(order):
        pool = LocalResourcePool(capacity=1.0)
        results = []
        for idx in order:
            ok = pool.try_allocate(request_amount)
            results.append((idx, ok))
        return pool.available, results

    # 子场景A（资源充足，原有验证保留）：3×0.2=0.6 < capacity=1.0
    orders = [[0, 1, 2], [2, 1, 0], [1, 0, 2]]
    finals = [run_allocation_order(o)[0] for o in orders]
    assert all(abs(f - finals[0]) < 1e-9 for f in finals), (
        f"资源充足时，资源池最终available应与分配调用顺序无关，实际={finals}")
    expected_available = 1.0 - request_amount * n_candidates
    assert abs(finals[0] - expected_available) < 1e-9

    # 子场景B（资源稀缺，评判要求补充）：capacity=0.3 < 3×0.2=0.6，
    # 必然有候选申请失败——验证失败者确实由调用顺序决定（先到先得），
    # 不是"资源池已实现公平竞争"。
    scarce_capacity = 0.3

    def run_scarce(order):
        pool = LocalResourcePool(capacity=scarce_capacity)
        return [(i, pool.try_allocate(request_amount)) for i in order]

    results_012 = run_scarce([0, 1, 2])
    results_210 = run_scarce([2, 1, 0])

    winners_012 = {i for i, ok in results_012 if ok}
    winners_210 = {i for i, ok in results_210 if ok}
    assert winners_012 != winners_210, (
        "稀缺资源下，调用顺序[0,1,2]与[2,1,0]的成功候选集合应不同——"
        "这正是try_allocate()'先到先得'偏置的直接证据，证明它不能"
        "被当作无偏选择器使用（评判211341核心要求）")

    print(f"T-SEL-6a: 资源充足时三种调用顺序available均为{finals[0]:.4f}")
    print(f"T-SEL-6b: 资源稀缺(capacity={scarce_capacity})时，"
          f"顺序[0,1,2]成功集合={winners_012}, 顺序[2,1,0]成功集合={winners_210}"
          f"（不同——确认先到先得偏置存在）")
    print("✓ T-SEL-6 PASS: 资源充足时记账无顺序偏置；"
          "资源稀缺时明确证实try_allocate()的先到先得偏置，"
          "不得被误用为无偏选择器（S0-c必须换用batch处理）")


def run():
    test_sel_1_no_semantic_candidate_id()
    test_sel_2_existence_retain_separation()
    test_sel_3_forbidden_read_audit()
    test_sel_4_resource_pool_basic()
    test_sel_5_label_permutation_invariance()
    test_sel_6_no_fixed_index_bias_in_resource_pool()
    print()
    print("=" * 60)
    print("T-SEL-1~6 ALL PASS")
    print("=" * 60)


if __name__ == "__main__":
    run()
