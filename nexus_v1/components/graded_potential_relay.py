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
        a_i = clip(g_r·V_i, 0, a_max)       （线性工作区 + 硬安全钳位，非二次；
                                               "clip"是分段截断，非连续压缩函数，
                                               订正见文件末尾"T3-C1订正"一节）

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
      推导，实际驱动用 dt=0.001）。当前实测输出量级偏保守（远低于
      `a_max`，未充分利用动态范围），若后续需要更大输出量级供下游
      Bundle 消费，可在 T3-C1 阶段按需重新标定。

═══════════════════════════════════════════════════════════════════════
T3-C1 订正（第二十节，批判十一，2026-07-17）
═══════════════════════════════════════════════════════════════════════

**表述订正**：T3-C1R 报告曾称"线性时不变系统在任意时刻 t 都满足
`V_a(t)/V_b(t)=y_a(t)/y_b(t)`"——**此表述过强，已被批判十一指出且用代码
实测复现证伪**。中继实际输出是卷积 `V_i(t)=∫h(t-s)y_i(s)ds`，只有当驱动
历史全程满足 `y_a(s)=c·y_b(s)`（同一常数 c）时才有 `V_a(t)=c·V_b(t)`——
这正是 T3-C1R 的 24 组固定比例测试场景，`eps_ratio=0` 是"固定历史比例"
这一特例下的正确结果，不能推广为"任意动态输入下瞬时比例保真"。实测
（`test_t3_c1_dynamic_ratio.py`）：分段驱动 1:1→2:1→1:3→1:1，切换到 2:1
后 150 步中继输出比仍停留在 1.519（未达 2.0）；比例交叉测试显示新占优
通道需要约 260/300 步窗口才能反超，且有 ~6.45% 过冲。

**正式定义 r_ρ^τ（窗口化射影关系，批判十一②，采纳）**：
```
z_i^τ(t) = (h_τ * y_i)(t)                      # 中继自身已有的 RC 核卷积
r_ρ^τ(t) = [z_1^τ(t) : z_2^τ(t) : ... : z_n^τ(t)]   # 射影等价类
```
其中 `y_i` 是共享分流池输出，`h_τ` 是本中继的公共 RC 核，`τ` 是关系的
时间支撑尺度。这不是新增计算逻辑，只是给中继已经存在的卷积行为一个正式
数学名称——与项目"关系是有自身时间尺度的过程状态，不是外部瞬时计算出的
数"的一贯哲学一致。固定历史比例输入下精确退化为 `[y_1:y_2]`（已证）；
动态输入下表示"最近一个由中继动力学决定的历史窗口内，各通道以什么相对
份额参与了共同过程"，平滑过渡而非瞬时跳变。

**"软上限"措辞订正为"硬钳位"**：`a_i=clip(g_r·V_i,0,a_max)` 是分段函数
意义上的硬钳位（`clip()` 在 `[0,a_max]` 区间外直接截断，非连续可导的
压缩函数），不应称"软上限"——一旦触及 `a_max`，比例信息会和旧 Neuron
读出层一样被破坏（触发 `N_clip>0`，见下方 T3-C1 独立账本，`n_clip=0`
是 r_ρ 资格的硬门槛）。

═══════════════════════════════════════════════════════════════════════
T3-C1 新增①：Bundle-source 契约点（强制三问，方案第二十节 20.2 第2点）
═══════════════════════════════════════════════════════════════════════

**背景**：批判十一指出 T3-C1R 从未验证"中继输出经真实下游 Bundle 读取后
是否仍保持比例"。核实 `SynapticBundle.propagate()`（`bundle.py:244/251/
253/256`）要求 source 满足 `is_alive()`/`config.spiking`/`.activation`
三个契约点，本组件此前不满足。若改用给中继接一个标准 `Neuron` 做"输出
适配器"（把 `a_i` 喂给 `Neuron.step()` 再读 `.activation`），会重新触发
`gm×V²` 二次门控——**正是 T3-C1R 刚解决掉的问题会被重新引入**，不可取。

Q1. 生物对应物是什么？
    与本组件（`GradedPotentialRelay`）本身相同——分级电位神经元对外的
    突触前信号。不需要新的 BIO 依据，只是把细胞已有的内部状态（`step()`
    已经算好的 `a_i`）暴露给下游读取接口，不是新细胞类型。

Q2. 物理结构是什么？
    `Sources(GradedPotentialRelay_a, GradedPotentialRelay_b) →
    SynapticBundle(frozen) → Targets(observer_a, observer_b)`，Bundle
    走既有 `propagate()`/`apply_to_targets()` 路径，不改 `bundle.py`。
    本组件新增三个 duck-typing 契约点（不继承 `Neuron`，不改
    `neuron.py`）：
      - `is_alive() -> bool`：本轮恒真（见 Q3）；
      - `.config`：新增极简 `RelayConfig`（只含 `spiking: bool = False`
        一个字段——不复用完整 `NeuronConfig`，那会带入 `channels`/
        `v_threshold` 等与本组件语义无关的字段）；
      - `.activation`：只读属性，返回最近一次 `step()` 的返回值本身，
        **不重新计算**——Bundle 读到的就是中继自己的线性输出，不会像
        接 `Neuron` 适配器那样被二次门控污染。

Q3. 每个参数的依据是什么？
    三个新契约点均不引入新参数：`is_alive()`恒真无参数（EXP 起点——
    中继是否需要真实"死亡"判据留待后续，本轮不涉及，不影响 T3-C1 四项
    验收范围）；`RelayConfig.spiking=False` 是布尔常量，非物理量；
    `.activation` 直接复用已标定的 `a_max`/`g_r`/`r_leak`，不新增标定。

═══════════════════════════════════════════════════════════════════════
T3-C1 新增②：独立账本（方案第二十节 20.2 第4点）
═══════════════════════════════════════════════════════════════════════

`GradedPotentialRelay` 是有真实内部状态的物理组件（Capacitor/电荷/leak/
输出钳位/step 次数），满足机制缺口准入七问，但此前未暴露关系层账本读数。
新增 `relay_ledger_stats() -> Dict`，返回 `{n_step, n_clip, v_max, q_max,
e_leak}`：
    - `n_step`：`step()` 调用次数（同 `RPartCircuitT3._rpart_pool_step_
      count` 的外部计数模式，本组件不同于 `DivisiveNormalizationReceptor`
      ——计数持有在组件自身而非外部电路，因为每个中继实例独立自计数，
      不像共享池需要电路代持）。
    - `n_clip`：`step()` 内 `g_r·V_i` 超出 `[0,a_max]` 区间（触发硬钳位）
      的次数。**`n_clip=0` 是 r_ρ 资格的硬门槛**——一旦任何参与通道
      触及 `a_max`，该时段 `r_ρ^τ` 视为失格（射影关系可能被压平）。
    - `v_max`/`q_max`：中继膜电位/电荷绝对值的历史峰值。
    - `e_leak`：leak 阶段累计耗散能量，仿照 `TemporalCoupler.
      stored_energy` 的 `E=½CV²` 差分模式（`temporal_coupler.py:
      171-175`）——`Capacitor` 本身只追踪累积电荷（`_q_out`），不追踪
      能量，本组件自行在每步 inject/leak 前后计算 `½CV²` 差值累加。
    `N_relay`（中继实例数）不在本方法返回值里——同 `rpart_relation_
    pool_stats()` 的 `pool_instance_count` 模式，由持有中继的电路自行
    统计，不是中继自身的状态。
"""

from __future__ import annotations

from typing import Dict

from dataclasses import dataclass, field

from nexus_v1.components.semiconductor import Capacitor

# ── T3-C1R 专属标定常量（EXP 起点，见 Q3）──
DEFAULT_CAPACITANCE: float = 1.0
DEFAULT_R_LEAK: float = 2.0
DEFAULT_G_R: float = 1.0
DEFAULT_A_MAX: float = 10.0  # 同 Neuron.activation 硬钳位惯例（neuron.py:438）


@dataclass
class RelayConfig:
    """T3-C1 Bundle-source 契约点：`SynapticBundle.propagate()` 只需要
    `config.spiking` 这一个字段（`bundle.py:251/253`），不需要完整
    `NeuronConfig` 的其余字段（`channels`/`v_threshold` 等与本组件语义
    无关）。见 `graded_potential_relay.py` 模块 docstring"T3-C1 新增①"。
    """
    spiking: bool = False


@dataclass
class GradedPotentialRelay:
    """TYPE:HYBRID — non-spiking graded-potential relay with linear readout.

    Q2: 复用 `Capacitor`（SEMI 原语）做膜状态积分，不重新实现 RC 逻辑；
    只在读出这一步做线性映射 + 硬安全钳位，替代 `Neuron` 的二次门控读出。

    T3-C1 起同时满足 `SynapticBundle` 的 source 契约（`is_alive()`/
    `config.spiking`/`.activation`，见模块 docstring"T3-C1 新增①"），
    可直接作为 Bundle 的 source 使用，不需要额外的 Neuron 适配器
    （那会重新触发二次门控，见 docstring 说明）。
    """
    capacitance: float = DEFAULT_CAPACITANCE
    r_leak: float = DEFAULT_R_LEAK
    g_r: float = DEFAULT_G_R
    a_max: float = DEFAULT_A_MAX
    _capacitor: Capacitor = field(init=False, repr=False)
    config: RelayConfig = field(init=False, repr=False)

    # ── T3-C1 独立账本状态（见模块 docstring"T3-C1 新增②"）──
    _last_activation: float = field(default=0.0, init=False, repr=False)
    _step_count: int = field(default=0, init=False, repr=False)
    _clip_count: int = field(default=0, init=False, repr=False)
    _v_max: float = field(default=0.0, init=False, repr=False)
    _q_max: float = field(default=0.0, init=False, repr=False)
    _cumulative_energy_in: float = field(default=0.0, init=False, repr=False)
    _cumulative_energy_out: float = field(default=0.0, init=False, repr=False)  # E_leak

    def __post_init__(self):
        self._capacitor = Capacitor(capacitance=self.capacitance)
        self.config = RelayConfig(spiking=False)

    @property
    def voltage(self) -> float:
        """中继膜电位（未经线性读出/clip）。"""
        return self._capacitor.voltage

    @property
    def activation(self) -> float:
        """T3-C1 Bundle-source 契约点：最近一次 `step()` 的返回值本身，
        只读，不重新计算——Bundle 读到的是中继自己的线性输出。
        """
        return self._last_activation

    def is_alive(self) -> bool:
        """T3-C1 Bundle-source 契约点：本轮恒真（EXP 起点，见模块
        docstring"T3-C1 新增①"Q3 说明）。
        """
        return True

    def _stored_energy(self) -> float:
        """E = ½CV²，仿照 `TemporalCoupler.stored_energy` 同款公式
        （`temporal_coupler.py:179-183`）。"""
        v = self._capacitor.voltage
        return 0.5 * self.capacitance * v * v

    def step(self, input_current: float, dt: float) -> float:
        """驱动一步：注入电流 → RC 漏电 → 线性读出 + 硬安全钳位。

        Args:
            input_current: 本步输入（T3-C1R 场景下是 DN 输出 y_i）。
            dt: 时间步长。

        Returns:
            a_i = clip(g_r × V_i, 0, a_max)，工作区间内 ≈ g_r × V_i（线性）。
        """
        e_before = self._stored_energy()
        self._capacitor.inject(input_current, dt)
        e_after_inject = self._stored_energy()
        self._cumulative_energy_in += max(0.0, e_after_inject - e_before)

        self._capacitor.leak(self.r_leak, dt)
        e_after_leak = self._stored_energy()
        self._cumulative_energy_out += max(0.0, e_after_inject - e_after_leak)

        v = self._capacitor.voltage
        a_raw = self.g_r * v
        clipped = max(0.0, min(a_raw, self.a_max))

        self._step_count += 1
        if a_raw < 0.0 or a_raw > self.a_max:
            self._clip_count += 1
        self._v_max = max(self._v_max, abs(v))
        self._q_max = max(self._q_max, abs(self._capacitor.charge))
        self._last_activation = clipped

        return clipped

    def relay_ledger_stats(self) -> Dict[str, float]:
        """T3-C1 独立账本读数（方案第二十节 20.2 第4点）。`n_clip=0` 是
        r_ρ 资格的硬门槛——一旦任何参与通道触及 `a_max`，该时段 `r_ρ^τ`
        视为失格。`N_relay`（实例数）不在此返回值里，由持有中继的电路
        自行统计（同 `rpart_relation_pool_stats()` 的 `pool_instance_
        count` 模式）。
        """
        return {
            "n_step": self._step_count,
            "n_clip": self._clip_count,
            "v_max": self._v_max,
            "q_max": self._q_max,
            "e_leak": self._cumulative_energy_out,
        }
