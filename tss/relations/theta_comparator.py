"""tss.relations.theta_comparator — TSS-M2：C_Θ 物理比较器与统一 Θ。

TYPE:SEMI

路线依据：08_下一阶段路线图.md §3 T-3（C_Θ 边界裁定）+ T-4（统一 Θ 九条
最低资格）。用户裁定 2026-09-06：C-02 收紧确认——比较**完全由物理结构
（MOSFET）承担**，不允许 Python if 读出物理状态作判定。

## 这是什么

C_Θ : (h_i^(τ)(t), b_j^↑(t)) ↦ r_{i≺j}^(τ)(t) 的**物理载体**——一个无状态
乘法符合检测器：仅当 i 的进入历史仍可读（h_i > θ_h）**且** j 此刻进入
（b_j^↑=1）时输出关系电流脉冲。

## T-3 四问的裁定落地（实现前置裁定，全部有据）

1. 比较由谁完成 → **MOSFET**（用户裁定 2026-09-06）。两个 conduct() 的
   乘积门控，无 Python 阈值比较参与判定。
2. 输出形态 → **实时电流脉冲**（float，b_j^↑ 单步性保证其天然脉冲形）。
   后验关系记录是**消费方的事**（镜像 occurrence_tap 的只读观察者纪律），
   本类不缓存记录列表。
3. 父谱系如何保存而不驱动物理 → address_i / address_j 作为元数据字段，
   step() 的物理路径**从不读取**它们（同 entry_gate.generator_address
   "只用于追踪，不参与任何判定"的约定；T-TH-8 静态守卫）。
4. 负例如何形成 → **由物理形成，不由代码分支形成**：
     仅 i（h_i 可读但 b_j=0）  → conduct(0)=0    → r=0
     仅 j（b_j=1 但 h_i=0）    → conduct(0)=0    → r=0
     同步进入（i、j 同一步）    → h_i 为充电前读出（history_kernel 严格
                                  先序），i 本步进入不在自己历史里 → r=0
     交换顺序（j 先 i 后）      → j 进入时 h_i 不可读；i 进入时 b_j=0 → r=0
     超窗（Δt > t_read）        → h_i 已衰减过 θ_h，conduct 硬截零 → r=0

## RULES.md 强制三问

Q1 生物对应物：NMDA 受体分子符合检测器——通道导通需要**同时**满足
   突触前谷氨酸结合（对应 b_j^↑，j 此刻的进入事件）与突触后足够去极化
   解除 Mg²⁺ 阻断（对应 h_i > θ_h，i 的近期进入历史）。
   REF: Nowak et al. 1984 / Mayer et al. 1984（Mg²⁺ 阻断的电压依赖性）。
   项目内既有结构先例（不引入新原语）：
     - semiconductor.py:123-126 MOSFET 门控自述
       "I_gated = m_gate × I ... equivalent to HH's g_max × m(V) × (V−E)"
       ——乘法门控是原语文档内建的物理语义，非本模块发明。
     - r2_fork.py / T1 collector 的 AND 门效果先例（双输入符合）。

Q2 物理结构：不新建 Neuron，不新建 SynapticBundle——符合检测是单个
   受体/通道的分子动力学，不是新细胞或新突触。载体 = 两个 MOSFET：
       _unblock_fet : MOSFET(v_threshold=θ_h)  Mg²⁺ 阻断解除（读 h_i）
       _entry_fet   : MOSFET(v_threshold=θ_g)  突触前脉冲检测（读 b_j^↑）
   输出 r = conduct(h_i) × conduct(b_j)——两因子任一为零则为零（符合），
   均为正时给出正电流（量级 = 历史新鲜度 × 脉冲通过量）。
   本类**无状态**（无电容、无内部变量随步演化）：符合检测在生物上是
   瞬时的通道开闭，历史保持已由上游 H_τ 承担，此处再引入状态会造成
   双重历史（同 DEG-018 双时钟教训）。

Q3 参数依据（全部取项目既有默认，零自由参数）：
     θ_h = 0.3 ← semiconductor.py:130 MOSFET.v_threshold 默认值，
                 与 entry_gate θ_g 同源。可读性资格不等式已在
                 history_kernel.py Q3 预先推导（722 步可读窗覆盖
                 TSS-3a 全部稳定目标对 Δt≤364，2× 裕量）。
     θ_g = 0.3 ← 同上。b_j^↑∈{0,1}，1.0 > 0.3 导通（0.7·gm），0 截止。
     gm  = 1.0 ← MOSFET 默认跨导，两 FET 同值（统一 Θ"同一类同一参数"）。

## 统一 Θ 九条资格（T-4，test_theta_unified.py T-TH-1~9 逐条守卫）

  1 同一类同一参数跑全部站点对     2 禁止读 pre_trace（静态守卫）
  3 仅 i / 仅 j 不产生关系          4 窗口内 i≺j 产生
  5 交换顺序不产生同一结果          6 超窗不产生
  7 输出具有可阻断独立作用          8 父谱系正确
  9 不复制站点专属电路

## 依赖声明（沿 entry_gate 先例）

本比较器与 entry_gate 一样，刻意依赖 `MOSFET.conduct()` 阈下**硬截零**的
当前实现行为（DEG-019，cell-cell/docs/degradation_registry.md）作硬整流：
h_i ≤ θ_h ⟹ conduct 恰为 0.0 ⟹ r 恰为 0.0（负例是精确零，不是小正值）。
若该实现被"修复"为注释承诺的阈下微导通，超窗/仅 j 负例会变成微弱假阳性。
test_entry_gate.py T-R1B-3 已有锁定断言，届时会先行报警。

## 禁止字段/禁止读取

  _phase / t_step / 计步器 / site_id / 窗口长度字段 / 数组缓存——本类不持有。
  不读取：pre_trace / Occurrence / OccurrenceClosure / collector 内部状态 /
  H_τ 电容内部（只吃 step() 返回值）。（T-TH-8 静态守卫。）
"""

from __future__ import annotations

from dataclasses import dataclass, field

from nexus_v1.components.semiconductor import MOSFET
from nexus_v1.components.structural_address import GeneratedAddress

# ─────────────────────────────────────────────────────────────────────
# 物理参数默认值 —— 全部取项目既有默认，零自由参数（见模块 Q3）
# 全站点对共用同一份（统一 Θ 资格第 1 条）
# ─────────────────────────────────────────────────────────────────────

_DEFAULT_THETA_H = 0.3    # 历史可读阈值 ← MOSFET.v_threshold 默认
_DEFAULT_THETA_G = 0.3    # 脉冲检测阈值 ← 同上
_DEFAULT_GM = 1.0         # 跨导 ← MOSFET.gm 默认


@dataclass
class PhysicalThetaComparator:
    """TYPE:SEMI — C_Θ 的物理载体：无状态 NMDA 型乘法符合检测器。

    (h_i^(τ)(t), b_j^↑(t)) ──[本器]──> r_{i≺j}^(τ)(t)

    每步 `step(h_i, b_j_up, dt)`：两 MOSFET conduct 乘积 → 关系电流。
    签名不含 t_step；类内无任何随步演化状态——历史在 H_τ，符合在此刻。

    字段说明：
      address_i / address_j：父发生谱系（i 为先行方，j 为后继方——
        **顺序即语义**，r_{i≺j} 与 r_{j≺i} 是两个不同的比较器实例）。
        只用于追踪，step() 不读取（T-3 裁定 3）。
    """
    address_i: GeneratedAddress
    address_j: GeneratedAddress

    # 物理参数（默认值来源见模块 Q3，全站点对共用同一份）
    theta_h: float = _DEFAULT_THETA_H
    theta_g: float = _DEFAULT_THETA_G
    gm: float = _DEFAULT_GM

    # 物理载体（init=False：不允许外部注入，同 entry_gate 封装手法）
    _unblock_fet: MOSFET = field(init=False, repr=False, default=None)
    _entry_fet: MOSFET = field(init=False, repr=False, default=None)

    # 可观测量（只读记账，不参与判定）
    relation_count: int = field(default=0, init=False)

    def __post_init__(self):
        if self.address_i is self.address_j:
            raise ValueError(
                "PhysicalThetaComparator: i、j 必须是不同的父发生谱系"
                "（自身与自身不构成先后关系）")
        if not (0.0 < self.theta_h):
            raise ValueError("PhysicalThetaComparator: theta_h must be > 0")
        if not (0.0 < self.theta_g < 1.0):
            raise ValueError(
                "PhysicalThetaComparator: 需 0 < theta_g < 1"
                "（否则 b^↑=1 不导通或 b^↑=0 也导通，符合检测失效）")
        self._unblock_fet = MOSFET(v_threshold=self.theta_h, gm=self.gm)
        self._entry_fet = MOSFET(v_threshold=self.theta_g, gm=self.gm)

    # ─────────────────────────────────────────────────────────────
    # 物理过程
    # ─────────────────────────────────────────────────────────────

    def step(self, h_i: float, b_j_up: float, dt: float) -> float:
        """推进一步符合检测，返回本步 r_{i≺j}^(τ)(t)（关系电流，≥0）。

        h_i    必须是 PhysicalHistoryKernel.step() 的返回值（充电前
               严格先序历史）；
        b_j_up 必须是 PhysicalEntryGate.step() 的返回值（0.0/1.0 脉冲），
               其他值 fail-fast 拒绝。

        比较完全由两个 MOSFET 的导通乘积完成——本方法内没有任何
        Python 阈值比较参与判定（C-02 收紧，用户裁定 2026-09-06）。
        """
        if b_j_up not in (0.0, 1.0):
            raise ValueError(
                "PhysicalThetaComparator: b_j_up 必须是 PhysicalEntryGate"
                f" 输出的 0.0/1.0 脉冲，收到 {b_j_up!r}")
        if h_i < 0.0:
            raise ValueError(
                f"PhysicalThetaComparator: h_i 必须非负，收到 {h_i!r}"
                "——历史电压不可能为负，负值说明上游不是 H_τ")

        # NMDA 乘法门控：Mg²⁺ 解除因子 × 突触前脉冲因子
        # （任一因子阈下硬截零 ⇒ 负例是精确零，见模块"依赖声明"）
        r = self._unblock_fet.conduct(h_i) * self._entry_fet.conduct(b_j_up)

        if r > 0.0:
            self.relation_count += 1
        return r


def make_theta_comparator(kernel_i, gate_j, **params) -> PhysicalThetaComparator:
    """从先行方历史核与后继方进入门构造比较器（只取地址，不持有引用）。

    调用方每步显式串联（保持接口纯度，同 make_entry_gate /
    make_history_kernel 约定）：

        h_i = kernel_i.step(gate_i.step(port_i.spike_output, dt), dt)
        b_j = gate_j.step(port_j.spike_output, dt)
        r   = comparator.step(h_i, b_j, dt)
    """
    return PhysicalThetaComparator(
        address_i=kernel_i.generator_address,
        address_j=gate_j.generator_address, **params)
