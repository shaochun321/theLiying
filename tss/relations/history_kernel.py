"""tss.relations.history_kernel — TSS-R1c(M1)：H_τ 物理历史保持核。

TYPE:SEMI

路线依据：cell-cell/理论文本_2026-08-14/理论主线文档集_2026-08-14/
08_下一阶段路线图.md §3 T-2（M1 最低结构 7 条）；用户裁定 2026-09-06
（范围=M1+M2，C-02=全物理比较器）。

## 这是什么

H_τ : b_i^↑(t) ↦ h_i^(τ)(t) 的**物理载体**——一个只被首次进入脉冲充电、
按真实 RC 泄漏的历史电容。

路线图候选公式 h_i^(τ)(t) = Σ_k A·e^{-(t-t_k)/τ}·1[t≥t_k] 由电容状态的
物理叠加**自然产生**（逐步 leak 的复利衰减 ≡ 精确指数；多次注入线性叠加），
不按解析式输出——满足路线图"工程首版必须由电容状态产生"的硬性要求。

## 物理过程（每步顺序，不可换序）

    1. _hist_cap.leak(r_leak, dt)          # 历史自然衰减
    2. h_read = _hist_cap.voltage          # 读本步充电**前**的历史量
    3. if b^↑ == 1: 注入 q_pulse           # 一次 b^↑ 恰好一次充电
    4. 返回 h_read

顺序 2 必须在 3 之前：h_i^(τ)(t) 是"t 时刻**之前**的进入历史"。若先充电
再读出，站点 i 在 t 步的进入会立刻出现在自己的历史里，下游 C_Θ 比较
h_i(t) 与 b_j^↑(t) 时，i、j **同步进入**也会误判为 i≺j——严格先后序
（Θ 的全部内容）被同一步事件污染。镜像 entry_gate.py 步骤 2/5 的既有
手法（"同一枚 spike 不能自己关自己的门"→ 此处"同一枚 b^↑ 不能自己
出现在自己的历史里"）。

## 为什么不需要 Zener 钳位（与 entry_gate 的结构差异，有推导）

entry_gate 需要钳位是因为它吃**原始 spike**（簇内密集，无间隔下界）。
本核只吃 b_i^↑，而 E^↑ 物理保证两枚 b^↑ 间隔 ≥ t_open = 1204 步
（entry_gate.py Q3）。几何级数上界：

    h_max = q_pulse/C · 1/(1 - e^{-t_open/τ_h})
          = 1.0 · 1/(1 - e^{-1204/600}) ≈ 1.155

电压自然有界，无需第二个钳位 FET；且不钳位保持了候选公式的纯叠加形式。
该上界由 T-R1C-6 以最小间隔脉冲序列实测守卫——若将来 E^↑ 的 t_open
缩短使上界失效，测试会报警。

## RULES.md 强制三问

Q1 生物对应物：突触前残余 Ca²⁺ / 短时程易化——每次动作电位后残余钙
   以指数衰减保持"最近发生过活动"的痕迹（REF: Zucker & Regehr 2002,
   Ann Rev Physiol, short-term synaptic plasticity）。
   项目内既有引用链（不引入新生物声明）：
     - circuit/bundle.py 三因子 eligibility trace（资格迹=衰减历史痕）
     - components/compensation.py:211+ CalciumRateIntegrator（Ca²⁺ 池电容）
   与 entry_gate 的 Ca²⁺ 池同源不同用：E^↑ 用它做**抑制**（阻止重复计数），
   H_τ 用它做**记忆**（保持进入历史）——同一钙动力学的两个生理侧面。

Q2 物理结构：不新建 Neuron，不新建 SynapticBundle——历史迹是细胞内
   钙动力学，不经突触。载体 = 一个 Capacitor（历史池），输入为
   PhysicalEntryGate.step() 的返回值 b^↑（调用方显式传入，本核不持有
   gate/port/collector 引用——镜像 make_entry_gate 的接口纯度约定）。

Q3 参数依据（全部取自项目既有结构与实测审计，零自由参数）：
     τ_h  = 0.6 s (600 步) ← EXP-T1-01 slow 窗口（temporal_r_prec.py:83
            _TAU_SLOW_STEPS=600）。TSS-3a 距离-延迟审计（2026-09-06 重跑，
            test_tss3a_theta_distance_audit）对全部跨种子稳定站点对的裁定
            均为"slow 通道覆盖，只复用 slow"：
              28≺15: Δt∈[258,321]  28≺21: Δt∈[331,364]  28≺24: Δt∈[285,320]
            （28≺31 被停止条件4否决：极差24 > minΔt=8，顺序量级不可信；
             28≺12: Δt∈[673,715] 超出适用域，不作 M2 目标对。）
     C_h  = 1.0  ← 同 entry_gate _DEFAULT_CAPACITANCE（同源 Ca²⁺ 池）
     ⇒ r_leak = τ_h/C_h = 0.6
     q_pulse = 1.0 ← 单枚 b^↑ 充至 V=1.0，同 entry_gate Q_spike 的
            "单脉冲直接到位"论证：若 q_pulse/C 因历史残余而使有效幅度
            依赖进入间隔，可读窗口会成为进入历史的函数（此处残余 ≤0.134，
            见上节上界推导，影响有界且被 T-R1C-6 守卫）。
   可读性资格（下游 C_Θ 以 θ_h=0.3=MOSFET 默认阈值读取，推导前置于此）：
     可读窗 t_read = τ_h·ln(1.0/0.3) = 722 步
     722 > 364 = 最大稳定 Δt（28≺21 上界）   ✓ 目标对全覆盖，~2× 裕量
     e^{-4257·0.001/0.6} = 8.3e-4 < 0.3      ✓ 真实退出间隔下界
       （EXP-R1A-01: 4257 步）处历史已不可读——不会桥接两次独立外部发生

## 路线图 7 条最低结构 → 实现映射（T-R1C-1~8 逐条守卫）

  1 输入只来自 PhysicalEntryGate → step(b_up) 仅接受 {0.0,1.0}，fail-fast；
    集成测试走真实 gate 链路
  2 一次 b^↑ 恰好一次充电        → 单步单注入；门关窗内重复 spike 无 b^↑
  3 真实 Capacitor 泄漏          → Capacitor.leak()，无解析式直出
  4 无数组/时间戳/站点专属状态   → 全部状态在 _hist_cap.charge；
    step() 签名不含 t_step
  5 多站点同参数                 → 模块级默认值，无站点专属字段
  6 窗口内可读、窗口外自然失效   → RC 衰减自然过 θ_h，无软件清零
  7 物理账本接口、不预称守恒闭合 → leaked_charge/injected_charge 只读暴露
    （Capacitor 内建 KCL 计数），不宣称全局闭合（D-06 仍开放）

## 禁止字段/禁止读取（沿 entry_gate 纪律）

  _phase / t_step / 计步器 / site_id / 站点专属增益——本类不持有任何一个。
  不读取：pre_trace / Occurrence / OccurrenceClosure / EntryBoundaryDetector /
  collector 内部状态。（T-R1C-7 静态守卫。）
"""

from __future__ import annotations

from dataclasses import dataclass, field

from nexus_v1.components.semiconductor import Capacitor
from nexus_v1.components.structural_address import GeneratedAddress

# ─────────────────────────────────────────────────────────────────────
# 物理参数默认值 —— 来源见模块 Q3，多站点共用同一份，零自由参数
# ─────────────────────────────────────────────────────────────────────

_DEFAULT_CAPACITANCE = 1.0   # C_h：同 entry_gate Ca²⁺ 池电容
_DEFAULT_R_LEAK = 0.6        # R_h：τ_h = R·C = 0.6 s = 600 步
                             #      ← EXP-T1-01 slow / TSS-3a 裁定复用
_DEFAULT_Q_PULSE = 1.0       # 单枚 b^↑ 注入电荷（充至 V=1.0）


@dataclass
class PhysicalHistoryKernel:
    """TYPE:SEMI — H_τ 的物理载体：进入历史 RC 保持电容。

    b_i^↑(t) ──[本核]──> h_i^(τ)(t)

    每步 `step(b_up, dt)`：泄漏 → 读充电前历史 → （若 b^↑）单次注入 →
    返回 h_i^(τ)(t)。签名不含 t_step——无软件时钟，状态全在
    `_hist_cap.charge` 里。

    字段说明：
      generator_address：物理谱系定位，只用于追踪，**不参与任何判定**
                        （同 PhysicalEntryGate / CollectorBoundaryPort 约定）
    """
    generator_address: GeneratedAddress

    # 物理参数（默认值来源见模块 Q3，全站点共用同一份）
    capacitance: float = _DEFAULT_CAPACITANCE
    r_leak: float = _DEFAULT_R_LEAK
    q_pulse: float = _DEFAULT_Q_PULSE

    # 物理载体（init=False：不允许外部注入历史状态，同 entry_gate 封装手法）
    _hist_cap: Capacitor = field(init=False, repr=False, default=None)

    # 可观测量（只读记账，不参与判定）
    charge_count: int = field(default=0, init=False)

    def __post_init__(self):
        if self.capacitance <= 0:
            raise ValueError("PhysicalHistoryKernel: capacitance must be > 0")
        if self.r_leak <= 0:
            raise ValueError("PhysicalHistoryKernel: r_leak must be > 0")
        if self.q_pulse <= 0:
            raise ValueError("PhysicalHistoryKernel: q_pulse must be > 0")
        self._hist_cap = Capacitor(capacitance=self.capacitance, charge=0.0)

    # ─────────────────────────────────────────────────────────────
    # 只读观测
    # ─────────────────────────────────────────────────────────────

    @property
    def history_voltage(self) -> float:
        """当前历史电压 h = Q/C（含本步已注入的电荷；下游 C_Θ 应消费
        step() 返回值而非本属性——返回值才是"充电前"的严格先序历史）。"""
        return self._hist_cap.voltage

    @property
    def injected_charge(self) -> float:
        """账本：累计注入电荷（Capacitor 内建 KCL 计数，见路线图第 7 条）。"""
        return self._hist_cap._q_in

    @property
    def leaked_charge(self) -> float:
        """账本：累计泄漏电荷。只暴露不宣称全局守恒闭合（D-06 仍开放）。"""
        return self._hist_cap._q_out

    # ─────────────────────────────────────────────────────────────
    # 物理过程
    # ─────────────────────────────────────────────────────────────

    def step(self, b_up: float, dt: float) -> float:
        """推进一步物理过程，返回本步 h_i^(τ)(t)（充电前读出，严格先序）。

        b_up 必须是 PhysicalEntryGate.step() 的返回值（0.0 或 1.0）——
        其他任何值 fail-fast 拒绝（路线图第 1 条"输入只来自 E^↑"的
        接口层守卫；结构层守卫见集成测试 T-R1C-8）。
        """
        if b_up not in (0.0, 1.0):
            raise ValueError(
                "PhysicalHistoryKernel: b_up 必须是 PhysicalEntryGate 输出的"
                f" 0.0/1.0 脉冲，收到 {b_up!r}——不接受迹变量、原始 spike"
                " 或任何连续量（路线图 M1 第 1 条）")

        # 1. 历史自然衰减（真实 RC，无解析式直出）
        self._hist_cap.leak(self.r_leak, dt)

        # 2. 读本步充电**前**的历史（顺序不可与 3 交换，见模块级说明）
        h_read = self._hist_cap.voltage

        # 3. 一次 b^↑ 恰好一次充电（q_pulse 为电荷量，直接入池；
        #    b^↑ 间隔 ≥ t_open 由 E^↑ 物理保证，故无需钳位，见模块级推导）
        if b_up == 1.0:
            self._hist_cap.inject(self.q_pulse, 1.0)
            self.charge_count += 1

        return h_read


def make_history_kernel(gate, **params) -> PhysicalHistoryKernel:
    """从 PhysicalEntryGate 构造历史核（只取地址，不持有 gate 引用）。

    调用方每步显式串联：`h = kernel.step(gate.step(port.spike_output, dt), dt)`
    ——保持"核只吃 b^↑ 实时脉冲"的接口纯度（同 make_entry_gate 约定）。
    """
    return PhysicalHistoryKernel(
        generator_address=gate.generator_address, **params)
