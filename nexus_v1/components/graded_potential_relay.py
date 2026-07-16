"""nexus_v1.components.graded_potential_relay — Non-spiking linear readout relay.

TYPE:HYBRID

方案依据：cell-cell/claudecode方案/基础生成元双轨落地方案_v2_2026-07-16.md
第十九节 19.2（T3-C1R）。第十份交叉比对批判发现：T3-B 的共享分流池
（`DivisiveNormalizationReceptor`）输出比例 `y_a/y_b` 精确线性、稳定，但
一旦注入现有 `Neuron`（`v_threshold=0`/`tau_gate=0` 单通道门控）的公开
`activation`，就会被 `activation=gm×V²` 的二次门控压缩（T1 EXP-T1-02
已证），且在较大输入幅度下还会被 `activation` 的 ±10.0 硬钳位彻底抹平
比例信息（T3-C0 四层信号审计实测确认）。参数重标只能挪动饱和触发点，
不能改变"平方"这个函数阶数——这不是拍脑袋修参数能解决的，是读出机制
本身的传递函数类型不对。本模块是修复这个缺口的新组件。

═══════════════════════════════════════════════════════════════════════
强制三问（每个新组件动手前必须先答，见 RULES.md / 方案约束7 / 第十二节
12.1 机制缺口准入七问）
═══════════════════════════════════════════════════════════════════════

Q1. 生物对应物是什么？
    BIO: 非脉冲、分级电位传输的局部神经元/感受器——不通过全或无尖峰
    编码，而是在有限工作区间内以连续膜电位/连续递质释放表达输入强度。
    经典例子：视网膜光感受器、水平细胞、双极细胞（REF: 视网膜分级电位
    生理学，Fain 2010 "Molecular and Cellular Physiology of Neuronal
    Membranes" 及 Kandel《Principles of Neural Science》视网膜章节）。
    这是本项目已有 `Neuron` 类（全/无尖峰编码或二次门控读出）之外的
    另一类真实、常见的神经元行为模式，不是为了凑数学结论而编造的类比。

Q2. 物理结构是什么？
    Sources → 本中继 → Targets，全部经由已有原语组装，不新造状态类：

      DN 输出电流(y_i) → 中继膜电容状态(Capacitor, 复用) → 线性电导读出(a_i) → Bundle

    动力学（标准 RC 充电，稳态与 T1 EXP-T1-03 已证的 Capacitor 性质
    `V_ss=I×R_leak`（与 C 无关）同构）：
        τ_r · dV_i/dt = -V_i + k_i·y_i     （由 Capacitor.inject()+leak() 实现）
        a_i = clip(g_r·V_i, 0, a_max)       （线性读出 + 软上限，非二次）

    关键不是"绝对无饱和"，而是标定后的工作区间内 `a_i≈g_r·V_i` 保持
    线性（不是二次）。**不修改现有通用 `Neuron.activation` 语义**——
    本组件是独立的新类，不影响项目里任何已使用 `Neuron`/`activation`
    的其他系统（T1 的 trace/collector、Ω 层、DA 电路等全部不受影响）。

Q3. 每个参数的依据是什么？
    - `capacitance=1.0`：沿用 `Capacitor` 类默认约定（项目既有惯例）。
    - `r_leak=2.0`、`g_r=1.0`：根据 T3-C0 已实测的 `y_i` 典型范围反推
      （`_diag_t3_c0_ratio_audit.py` + 共同尺度扫描最大场景实测：
      y_i 范围约 0.03~2.6，见方案第十九节 19.2）。取
      `a_max=10.0`（沿用 `Neuron.activation` 现有硬钳位惯例 `neuron.py:438`
      的同一量级，保证下游 Bundle 读到的数值范围与系统其余部分一致，
      不引入新的尺度不匹配）。工作安全边际 `β≤0.5`（批判十建议值，
      同项目"权重远离饱和"一贯纪律同构）：`g_r·r_leak·y_max/a_max
      = 1.0×2.0×2.6/10.0 ≈ 0.52`，接近但不超过目标边际，为真实输入
      波动留余量。**EXP 首轮起点，非最终标定**——同 T1 report 记录的
      多轮校准史，预期 T3-C1 阶段可能需要根据真实 ξ 输入范围重新标定。
    - `tau_r = r_leak × capacitance = 2.0`（时间单位，非步数）：**已发现
      的真实标定注意事项**——T3-B/T3-C0 测试全部用 `dt=0.001`（同 T1/T0
      既有 DT 约定），200~300 步只推进 0.2~0.3 个时间单位，远不足以
      让 `tau=2.0` 的 RC 中继在测试窗口内达到稳态（这正是 CLAUDE.md
      警告的"dt=1.0 陷阱"的另一种表现——本模块参数最初按 dt=1.0 直觉
      推导，实际驱动用 dt=0.001）。**但这不影响比例保真度**：本中继
      是线性时不变系统（LTI），`V_i(t)∝y_i` 在任意时刻 t 都成立，不
      只是稳态才成立——已实测确认（200 步下 `o_a/o_b` 精确等于
      `y_a/y_b`，见 T3-C1R 测试）。当前实测输出量级偏保守（远低于
      `a_max`，未充分利用动态范围），若后续需要更大输出量级供下游
      Bundle 消费，可在 T3-C1 阶段按需重新标定，不影响本轮比例保真
      的核心验收目标。
"""

from __future__ import annotations

from dataclasses import dataclass, field

from nexus_v1.components.semiconductor import Capacitor

# ── T3-C1R 专属标定常量（EXP 起点，见 Q3）──
DEFAULT_CAPACITANCE: float = 1.0
DEFAULT_R_LEAK: float = 2.0
DEFAULT_G_R: float = 1.0
DEFAULT_A_MAX: float = 10.0  # 同 Neuron.activation 硬钳位惯例（neuron.py:438）


@dataclass
class GradedPotentialRelay:
    """TYPE:HYBRID — non-spiking graded-potential relay with linear readout.

    Q2: 复用 `Capacitor`（SEMI 原语）做膜状态积分，不重新实现 RC 逻辑；
    只在读出这一步做线性映射 + 软上限，替代 `Neuron` 的二次门控读出。
    """
    capacitance: float = DEFAULT_CAPACITANCE
    r_leak: float = DEFAULT_R_LEAK
    g_r: float = DEFAULT_G_R
    a_max: float = DEFAULT_A_MAX
    _capacitor: Capacitor = field(init=False, repr=False)

    def __post_init__(self):
        self._capacitor = Capacitor(capacitance=self.capacitance)

    @property
    def voltage(self) -> float:
        """中继膜电位（未经线性读出/clip）。"""
        return self._capacitor.voltage

    def step(self, input_current: float, dt: float) -> float:
        """驱动一步：注入电流 → RC 漏电 → 线性读出 + 软上限。

        Args:
            input_current: 本步输入（T3-C1R 场景下是 DN 输出 y_i）。
            dt: 时间步长。

        Returns:
            a_i = clip(g_r × V_i, 0, a_max)，工作区间内 ≈ g_r × V_i（线性）。
        """
        self._capacitor.inject(input_current, dt)
        self._capacitor.leak(self.r_leak, dt)
        a = self.g_r * self._capacitor.voltage
        return max(0.0, min(a, self.a_max))
