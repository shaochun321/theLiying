"""tss.tests.test_selection_pool — S0-b：同构候选池验证（不接入竞争）。

方案依据：document - 2026-08-02T211341.334.md（S0-b范围裁定）。

评判裁定S0-b应验证的核心产物：
  候选池本身没有结构和执行顺序偏置，且物理参数差异能产生可测响应差异。
不测试"谁赢"（S0-b不含任何竞争/资源/胜负逻辑）。

五个测试：
  T-S0B-1：构造循环产出结构完全相同的N个候选（只有tau_steps不同，
           bundle权重/collector参数/连接模板逐项相等）
  T-S0B-2：候选ID用selection_contract.make_candidate_id()生成，
           无语义前缀（复用S0-a契约，不重新发明）
  T-S0B-3：完全相同参数的候选，独立驱动后响应轨迹完全一致（运行时
           对称性——不因构造顺序/容器位置产生活动偏差）
  T-S0B-4：tau_steps不同的候选，响应窗口/衰减速度确实不同（验证
           "物理参数差异能产生可测响应差异"，不是死代码）
  T-S0B-5：候选池构造顺序置换后，每个candidate_id对应的响应轨迹不变
           （按candidate_id取值而非按列表下标取值，置换容器顺序不
           改变每个候选自身的物理行为）
"""
import sys

sys.path.insert(0, '.')

from tss.relations.selection_contract import is_valid_candidate_id
from tss.relations.selection_pool import SelectionPoolCircuit

DT = 0.001
_DRIVE_STEPS = 200


def _drive_with_pulse(circuit, pulse_step: int = 20, n_steps: int = _DRIVE_STEPS):
    """给xi_a/xi_b各注入一次脉冲（直接写pre_trace，不经World/HeatSource——
    S0-b只关心候选链本身的响应差异，不需要重演真实感温驱动，同T-R2C系列
    "只切换目标环节，不重新构造外部输入"的省token做法）。"""
    for t in range(n_steps):
        if t == pulse_step:
            circuit.rprec_xi_a.pre_trace = 1.0
        circuit.step_candidates(DT)


def test_s0b_1_identical_structure_across_candidates():
    """T-S0B-1：构造循环产出的候选结构逐项相同，只有tau_steps不同。"""
    taus = (30, 100, 400)
    circuit = SelectionPoolCircuit(taus=taus)

    assert len(circuit.candidates) == 3
    for i, c in enumerate(circuit.candidates):
        assert c.tau_steps == taus[i]
        # 除tau外的所有bundle权重逐项相等（同一构造循环产出，不是手写差异）
        assert c.bundle_xi_to_trace.config.initial_weight == 0.3
        assert c.bundle_trace_to_collector.config.initial_weight == 0.5
        assert c.bundle_raw_xi_to_collector.config.initial_weight == 0.15
        # collector的物理参数（阈值/gm等，位于channels[0]）逐项相等
        ref = circuit.candidates[0].collector.config
        assert c.collector.config.channels[0].v_threshold == ref.channels[0].v_threshold
        assert c.collector.config.channels[0].gm == ref.channels[0].gm
        assert c.collector.config.capacitance == ref.capacitance

    print(f"T-S0B-1: 3个候选tau={[c.tau_steps for c in circuit.candidates]}，"
          f"其余结构参数逐项相等")
    print("✓ T-S0B-1 PASS: 构造循环产出结构完全相同的候选，唯一自由变量是tau_steps")


def test_s0b_2_candidate_id_no_semantics():
    """T-S0B-2：候选ID无语义（复用selection_contract契约）。"""
    circuit = SelectionPoolCircuit()
    for c in circuit.candidates:
        assert is_valid_candidate_id(c.candidate_id)
    ids = [c.candidate_id for c in circuit.candidates]
    assert ids == ["candidate_0", "candidate_1", "candidate_2"]

    print(f"T-S0B-2: candidate_ids={ids}")
    print("✓ T-S0B-2 PASS: 候选ID复用S0-a无语义契约，未重新发明命名规则")


def test_s0b_3_identical_params_identical_response():
    """T-S0B-3：运行时对称性——完全相同tau **且完全相同physical_seed**
    的两个候选，trace层响应完全一致。

    历史修正（S0-bX1，评判document-2026-08-03T125656.528.md）：本测试
    最初只传相同tau、不显式传physical_seed，依赖默认种子分配偶然让两个
    候选的xi_to_trace权重相同——这是脆的：S0-bX1把physical_seed与
    candidate_id解耦后，默认种子改为按候选索引递增（471030/471031/...），
    "只同tau"不再保证"同权重"。真正该验证的运行时对称性必须显式传入
    相同physical_seed才成立——这正是身份-扰动解耦生效的直接证据：
    "参数完全相同"现在唯一且明确地由(tau, physical_seed)两个显式数值
    决定，不再有任何隐式的、依赖bundle_id字符串巧合的对称性。
    """
    same_tau = (100, 100)
    same_seed = (500000, 500000)  # 显式传入相同seed，测真正的对称性
    circuit = SelectionPoolCircuit(taus=same_tau, physical_seeds=same_seed)
    _drive_with_pulse(circuit)

    c0, c1 = circuit.candidates
    # tau相同+physical_seed相同 → 全部bundle权重相同 → trace/collector
    # 响应逐位一致（S0-bX1新增的显式对称性保证，见test_selection_pool_seed.py
    # T-S0BX1-2的更完整版本）。
    assert abs(c0.trace.activation - c1.trace.activation) < 1e-9
    assert abs(c0.collector.pre_trace - c1.collector.pre_trace) < 1e-9

    print(f"T-S0B-3: candidate_0.trace={c0.trace.activation:.6f}, "
          f"candidate_1.trace={c1.trace.activation:.6f}（相同tau+相同seed，完全一致）")
    print(f"  collector.pre_trace: {c0.collector.pre_trace:.6f} vs "
          f"{c1.collector.pre_trace:.6f}（同样一致）")
    print("✓ T-S0B-3 PASS: 显式传入相同(tau, physical_seed)后，"
          "trace/collector运行时对称性完全成立")


def test_s0b_4_different_tau_different_response():
    """T-S0B-4：tau不同的候选确实产生可测的响应差异（验证候选池不是
    死代码——物理参数差异必须体现为真实响应差异，否则S0-c/d的竞争
    将无实际内容可比较）。"""
    circuit = SelectionPoolCircuit(taus=(30, 400))
    _drive_with_pulse(circuit)

    c_fast, c_slow = circuit.candidates
    # 短tau候选衰减快，长tau候选衰减慢——脉冲后200步时trace幅值应有明显差异
    assert c_fast.trace.activation != c_slow.trace.activation
    diff_ratio = abs(c_fast.trace.activation - c_slow.trace.activation) / \
        max(abs(c_slow.trace.activation), 1e-9)
    assert diff_ratio > 0.01, (
        f"tau=30与tau=400的候选响应差异应显著，实际相对差异={diff_ratio:.4f}")

    print(f"T-S0B-4: tau=30候选trace={c_fast.trace.activation:.6f}, "
          f"tau=400候选trace={c_slow.trace.activation:.6f}, "
          f"相对差异={diff_ratio:.4f}")
    print("✓ T-S0B-4 PASS: tau_steps差异产生可测的响应窗口差异，候选池非死代码")


def test_s0b_5_container_order_permutation_invariance():
    """T-S0B-5：候选池**容器存储顺序**置换后，每个候选自身的响应不变。

    诊断修正（实测发现）：最初版本改用"交换taus元组顺序"来测试置换，
    但construction loop按位置把candidate_id分配给taus[i]（见
    SelectionPoolCircuit.__init__的enumerate(taus)），所以交换taus顺序
    实际上是把tau值绑定到了**不同的candidate_id**上——而bundle哈希扰动
    （circuit/bundle.py按bundle_id计算±25%扰动，含candidate_id）会因此
    给同一个tau值产生不同的扰动结果。这比较的是"不同身份"，不是
    "同一身份、不同容器位置"，会错误地把"扰动机制的正常特性"误判为
    "候选池存在顺序偏置"。

    正确测法：构造后**只打乱circuit.candidates列表本身的存储顺序**
    （不改变每个候选的candidate_id/tau_steps/trace/collector对象引用），
    验证被打乱顺序遍历（`step_candidates`按`for c in self.candidates`
    遍历）不影响每个候选的最终响应——因为每个候选的trace/collector都是
    独立对象，互不共享状态，遍历顺序在S0-b阶段（无共享资源池）不应
    产生任何交叉影响。
    """
    import random

    circuit = SelectionPoolCircuit(taus=(30, 100, 400))
    original_order = list(circuit.candidates)

    # 只打乱列表存储顺序，不改变任何候选对象本身
    shuffled_order = list(original_order)
    random.Random(42).shuffle(shuffled_order)
    circuit.candidates = shuffled_order

    _drive_with_pulse(circuit)

    responses_by_id = {c.candidate_id: c.trace.activation for c in circuit.candidates}

    # 用相同taus、相同（未打乱）顺序跑一次对照组
    circuit_control = SelectionPoolCircuit(taus=(30, 100, 400))
    _drive_with_pulse(circuit_control)
    responses_control = {c.candidate_id: c.trace.activation
                         for c in circuit_control.candidates}

    for cid in responses_by_id:
        assert abs(responses_by_id[cid] - responses_control[cid]) < 1e-12, (
            f"{cid}的响应不应因candidates列表存储顺序被打乱而改变，"
            f"实际shuffled={responses_by_id[cid]}, control={responses_control[cid]}")

    print(f"T-S0B-5: 存储顺序打乱前后，每个candidate_id的响应逐一致："
          f"{responses_by_id}")
    print("✓ T-S0B-5 PASS: 候选响应只由候选自身身份/参数决定，"
          "与candidates列表的存储/遍历顺序无关")


def run():
    test_s0b_1_identical_structure_across_candidates()
    test_s0b_2_candidate_id_no_semantics()
    test_s0b_3_identical_params_identical_response()
    test_s0b_4_different_tau_different_response()
    test_s0b_5_container_order_permutation_invariance()
    print()
    print("=" * 60)
    print("T-S0B-1~5 ALL PASS")
    print("=" * 60)


if __name__ == "__main__":
    run()
