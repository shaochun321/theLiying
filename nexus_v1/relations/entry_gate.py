"""nexus_v1.relations.entry_gate — TSS-R1b：E^↑ 首次进入边界**物理门**。

TYPE:SEMI

方案依据：cell-cell/claudecode方案/TSS-R1b_E上箭头物理载体实现方案_2026-08-05.md（v2）
裁定链：document - 2026-08-05T010306.536.md（R1a 降格为参考检测器）
      → document - 2026-08-05T170306.100.md（否决 v1 的"不刷新"方案）
      → document - 2026-08-05T170642.972.md（确认主线，限定交付边界）
      → document - 2026-08-05T172740.398.md（批准实现，锁定结构与参数）

## 这是什么

E^↑ : p_α(t) ↦ b_α^↑(t) 的**物理载体**——一个可重触发、饱和刷新型 RC 抑制门。

`EntryBoundaryDetector`（TSS-R1a，`entry_boundary.py`）是同一过程的**判定规则**
实现：ARMED/ACTIVE/REFRACTORY 三态枚举 + 整数计步。它已被裁定不是物理生成算子，
保留为历史参考检测器，**不接入生产链，也不要求与本门逐步等价**（三个开门阈值
互不相同：本门 1204 步 / oracle rearm=0 为 501 步 / oracle rearm=500 为 1001 步）。

## 物理过程（每步顺序，不可换序）

    1. _gate_cap.leak(r_leak, dt)                  # 抑制量自然衰减（恢复）
    2. V_g = _gate_cap.voltage                     # 读脉冲到来**前**的门电压
    3. gate_open = (_gate_fet.conduct(V_g) == 0)   # 阈值判定交给 MOSFET
    4. b^↑ = 1.0 if (spike and gate_open) else 0.0
    5. if spike:  充电 + Zener 钳位到 V_H          # ★ 每枚脉冲都刷新
    6. 无脉冲时只泄漏，不做任何软件复位

即：b^↑(t_k) = p(t_k)·1[V_g(t_k⁻) < θ_g]，随后 p(t_k)=1 ⇒ V_g(t_k⁺) = V_H。

顺序 2 必须在 5 之前：若先充电再判定，同一枚 spike 会自己关自己的门。

## 为什么每枚脉冲都必须刷新（v1 的失败反例，勿回退）

v1 方案曾规定"被抑制的重复脉冲不再充电"，本意是防持续驱动下门永久锁死。
那让门测量的是「距**首次**脉冲多久」，而 E^↑ 需要「距**最近一次**脉冲多久」。
持续发生中途门会自行开门 → 同一次发生输出多个 b^↑：

    t=0     首枚通过，V_g ← V_H
    t=200~  重复脉冲被抑制但不刷新 → V_g 继续单调衰减
    t=1204  V_g 跌破 θ_g，门自行打开（此时簇还在继续）
    t=1400  下一枚脉冲再次输出 b^↑   ← 错误：同一次发生输出了 2 次

防锁死的正确解法是**钳位**（V_g 永不超过 V_H，末枚脉冲后恒定从 V_H 起衰减，
恢复时间与簇长/发放率无关），不是拒绝充电。守卫见 T-R1B-4 / T-R1B-5。

## RULES.md 强制三问

Q1 生物对应物：spike-frequency adaptation / 阈值调适，其中"每枚 spike 都刷新
   + 抑制量有饱和上限"对应 Ca²⁺ 依赖 K⁺ 通道的**池饱和**特性——每枚 spike 都
   引起 Ca²⁺ 内流给池充电，池容量有上限（缓冲蛋白饱和 / 泵-漏平衡），Ca²⁺ 被
   泵出后抑制按 τ=C·R 衰减。
   REF（项目内既有引用链，不引入新生物声明）：
     - components/neuron.py:129 FatigueCapacitor
       `BIO: Na+ channel slow inactivation + Ca2+-dependent K+ channels`
     - components/compensation.py:211-247 CalciumRateIntegrator
       `Circuit: Capacitor (Ca²⁺ pool) + MOSFET Zener clamp`
   注意：FatigueCapacitor 不足以单独作先例——它**没有钳位**，持续发放下靠
   充电率/泄漏率达到率依赖稳态，恢复时间随发放率变化。E^↑ 要求恢复时间与
   发放率无关，所以拓扑取自带 Zener 钳位的 CalciumRateIntegrator。

Q2 物理结构：不新建 Neuron，不新建 SynapticBundle——spike-frequency adaptation
   是同一细胞内的通道动力学（Ca²⁺-K⁺ 环），不经过突触，硬接一条 bundle 是错的
   建模。载体 = 既有 collector Neuron（经 CollectorBoundaryPort 读 spike_output）
   + 本门内三个原语对象：
       _gate_cap  : Capacitor  抑制量载体（Ca²⁺ 池）
       _gate_fet  : MOSFET     门阈值判定（v_threshold = θ_g）
       _clamp_fet : MOSFET     Zener 钳位（同 compensation.py:277-285）

Q3 参数依据：t_open = τ·ln(V_H/θ_g)（**不是 τ 单独**——评判 170306.100 纠正）。
   三个值全部取项目既有默认，零自由参数：
     V_H   = 1.0  ← compensation.py:247 CalciumRateIntegrator.v_clamp
     θ_g   = 0.3  ← semiconductor.py:130 MOSFET.v_threshold
     τ     = 1.0s ← collector 既有 AdEx 适应时间常数 tau_w=1.0
                    (variant_adapter.py:386)；同一细胞的两个慢恢复过程都源自
                    Ca²⁺/离子泵动力学，时间尺度相近是生理自洽的
     Q_spike = 1.0 ← 由"单枚 spike 必须直接饱和"反推：需 Q_spike/C ≥ V_H，
                    取等号最简。若 Q_spike/C < V_H，孤立 spike 后
                    t_open=τ·ln(ΔV/θ_g) 短于长簇后的 τ·ln(V_H/θ_g)，恢复时间
                    变成簇历史的函数，破坏位置无关性与跨站点共参。
   代入：t_open = 1.0·ln(1/0.3) = 1.204 s = 1204 步（dt=0.001）
   验证落在 EXP-R1A-01 实测分离带内：
     簇内 ISI 上界 316 步 < 1204 < 真实退出间隔下界 4257 步
     几何中位 √(316×4257) = 1160 步，t_open 与之差 3.8%
   两个资格不等式（评判给出的形式）：
     V_H·exp(-0.316/τ) = 0.729  > 0.3 = θ_g   ✓ 最大簇内间隔后仍关门
     V_H·exp(-4.257/τ) = 0.0142 < 0.3 = θ_g   ✓ 真实静默退出后已重新开门

## 禁止字段（评判 172740.398 明确列出）

  _phase / _silence_count / t_step / gap_steps / rearm_min_steps / site_id

本类不持有其中任何一个。`step()` 签名不含 `t_step` 本身即"无软件时钟"的
结构性证据（T-R1B-1 断言）。全部状态都在 `Capacitor.charge` 里。

亦不读取或修改：Occurrence / OccurrenceClosure / EntryBoundaryDetector 内部
状态 / collector 的 `_w_adapt` / `pre_trace`。

## 已知脆弱点（R5，登记待独立处理）

`MOSFET.conduct()` 阈下分支（semiconductor.py:151-159）注释承诺指数尾流
`|I_sub|`，但实现 `max(0.0, gm·nVT·(exp(x)-1))` 在 x<0 时恒返回 **0.0**。
本门用 `conduct(V_g) == 0.0` 作硬阈值判定，依赖的是**当前实现行为**，不是注释
承诺的语义。若将来有人"修复"这个不一致（让阈下返回微小正值），门会变成永远
微导通、E^↑ 静默失效。T-R1B-3 内有锁定断言 `conduct(θ_g-1e-6) == 0.0`，
届时会立刻报警而不是静默退化。

阈值点约定：V_g 恰好等于 θ_g 时 `conduct` 返回 0.0（MOSFET 原语在阈值点
I=0 连续，见 semiconductor.py:146 注释），本门据此判为"开"。评判定义的严格
不等式 `V_g < θ_g` 在此点判"关"——差一个零测度点，exp 连乘下不可达。

已登记为 DEG-019（cell-cell/docs/degradation_registry.md）。
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field

from ..components.semiconductor import Capacitor, MOSFET
from ..components.structural_address import GeneratedAddress
from .boundary_process import CollectorBoundaryPort

# ─────────────────────────────────────────────────────────────────────
# 物理参数默认值 —— 全部取自项目既有结构，零自由参数（见模块 Q3）
# ─────────────────────────────────────────────────────────────────────

_DEFAULT_CAPACITANCE = 1.0   # C：Ca²⁺ 池电容
_DEFAULT_R_LEAK = 1.0        # R：τ = R·C = 1.0 s，同 collector tau_w
_DEFAULT_V_CLAMP = 1.0       # V_H：compensation.py:247 v_clamp
_DEFAULT_THETA_GATE = 0.3    # θ_g：semiconductor.py:130 MOSFET.v_threshold
_DEFAULT_Q_SPIKE = 1.0       # Q_spike/C ≥ V_H，取等号
_DEFAULT_GM_CLAMP = 10.0     # compensation.py:248 gm_clamp（硬钳位电导）


def open_delay_steps(dt: float = 0.001,
                     r_leak: float = _DEFAULT_R_LEAK,
                     capacitance: float = _DEFAULT_CAPACITANCE,
                     v_clamp: float = _DEFAULT_V_CLAMP,
                     theta_gate: float = _DEFAULT_THETA_GATE) -> int:
    """解析计算 t_open 对应的步数：末枚脉冲后需静默多少步门才重新开放。

    t_open = τ·ln(V_H/θ_g)，τ = R·C。返回满足
    `V_H·exp(-n·dt/τ) < θ_g` 的最小整数 n。

    这是一个**推导工具**，不参与 step() 的任何判定——门的开闭完全由
    Capacitor 电压与 MOSFET 阈值决定，不查这个数字。
    """
    tau = max(r_leak * capacitance, 0.01)
    t_open = tau * math.log(v_clamp / theta_gate)
    n = int(math.ceil(t_open / dt))
    # 边界保护：ceil 落在恰好相等的点上时再进一步（严格小于才算开）
    while v_clamp * math.exp(-n * dt / tau) >= theta_gate:
        n += 1
    return n


@dataclass
class PhysicalEntryGate:
    """TYPE:SEMI — E^↑ 的物理载体：可重触发、饱和刷新型 RC 抑制门。

    p_α(t) ──[本门]──> b_α^↑(t)

    每步 `step(spike_output, dt)`：泄漏 → 读 V_g → MOSFET 阈值判定 → 输出 →
    **每枚脉冲都充电 + Zener 钳位**。返回 b_α^↑（0.0 或 1.0）。

    资格（评判 172740.398 列 9 条，测试 T-R1B-1~9 逐条守卫）：
      1. 首枚脉冲通过           2. 簇内重复脉冲抑制
      3. 每枚输入脉冲刷新抑制    4. 门电压有限饱和，不无限累积
      5. 足够静默后物理恢复      6. 28/31/21/24 同结构同参数
      7. 无 _phase/计步器/站点专属字段
      8. 不修改 occurrence.py    9. 全量回归不退化

    字段说明：
      generator_address：物理谱系定位，只用于追踪，**不参与任何判定**
                        （同 CollectorBoundaryPort 的约定）
      其余全为物理参数，无站点专属值。
    """
    generator_address: GeneratedAddress

    # 物理参数（默认值来源见模块 Q3，四站点共用同一份）
    capacitance: float = _DEFAULT_CAPACITANCE
    r_leak: float = _DEFAULT_R_LEAK
    v_clamp: float = _DEFAULT_V_CLAMP
    theta_gate: float = _DEFAULT_THETA_GATE
    q_spike: float = _DEFAULT_Q_SPIKE
    gm_clamp: float = _DEFAULT_GM_CLAMP

    # 物理载体（init=False：不允许外部注入，避免绕过物理过程直接设定门状态；
    # 同 entry_boundary.py 对 _phase 的封装收窄手法）
    _gate_cap: Capacitor = field(init=False, repr=False, default=None)
    _gate_fet: MOSFET = field(init=False, repr=False, default=None)
    _clamp_fet: MOSFET = field(init=False, repr=False, default=None)

    # 可观测量（只读记账，不参与判定）
    entry_count: int = field(default=0, init=False)
    clamp_heat: float = field(default=0.0, init=False)

    def __post_init__(self):
        if self.capacitance <= 0:
            raise ValueError("PhysicalEntryGate: capacitance must be > 0")
        if self.q_spike / self.capacitance < self.v_clamp:
            # Q3：单枚 spike 必须直接饱和，否则恢复时间成为簇历史的函数
            raise ValueError(
                "PhysicalEntryGate: 需 q_spike/capacitance >= v_clamp"
                f"（当前 {self.q_spike}/{self.capacitance} < {self.v_clamp}）"
                "——否则孤立脉冲与长簇后的 t_open 不同，破坏位置无关性")
        if not (0.0 < self.theta_gate < self.v_clamp):
            raise ValueError(
                "PhysicalEntryGate: 需 0 < theta_gate < v_clamp"
                "（否则门恒开或恒关，t_open 无定义）")

        self._gate_cap = Capacitor(capacitance=self.capacitance, charge=0.0)
        self._gate_fet = MOSFET(v_threshold=self.theta_gate, gm=1.0)
        self._clamp_fet = MOSFET(v_threshold=self.v_clamp, gm=self.gm_clamp)

    # ─────────────────────────────────────────────────────────────
    # 只读观测
    # ─────────────────────────────────────────────────────────────

    @property
    def gate_voltage(self) -> float:
        """当前抑制电压 V_g = Q/C。"""
        return self._gate_cap.voltage

    @property
    def gate_open(self) -> bool:
        """门是否开放：由 MOSFET 阈值判定，不是 Python 比较。

        `conduct(V_g)` 在 V_g < θ_g 时返回 0.0（见模块"已知脆弱点 R5"），
        门开 ⟺ 抑制电流为零。
        """
        return self._gate_fet.conduct(self._gate_cap.voltage) == 0.0

    # ─────────────────────────────────────────────────────────────
    # 物理过程
    # ─────────────────────────────────────────────────────────────

    def step(self, spike_output: float, dt: float) -> float:
        """推进一步物理过程，返回本步 b_α^↑（0.0 或 1.0）。

        签名不含 `t_step`——无软件时钟，状态全在 `_gate_cap.charge` 里。
        """
        # 1. 抑制量自然衰减（RC 恢复）
        self._gate_cap.leak(self.r_leak, dt)

        # 2. 读脉冲到来**前**的门电压（顺序不可与 5 交换）
        v_before = self._gate_cap.voltage

        # 3. 阈值判定交给 MOSFET 原语
        gate_open = self._gate_fet.conduct(v_before) == 0.0

        # 4. 输出：仅当门开放且本步有脉冲
        is_spike = spike_output > 0.5
        b_up = 1.0 if (is_spike and gate_open) else 0.0
        if b_up > 0.0:
            self.entry_count += 1

        # 5. 每枚脉冲都刷新抑制量（无论是否输出）+ Zener 钳位限幅
        if is_spike:
            self._gate_cap.charge += self.q_spike * self.capacitance
            v_after = self._gate_cap.voltage
            if v_after > self.v_clamp:
                # Zener 钳位：同 compensation.py:277-285 的既有做法
                excess = v_after - self.v_clamp
                i_clamp = self._clamp_fet.conduct(v_after)
                self.clamp_heat += i_clamp * excess * dt
                self._gate_cap.discharge_to(self.v_clamp)

        # 6. 无脉冲时只泄漏（步骤 1 已完成），不做任何软件复位
        return b_up


def make_entry_gate(port: CollectorBoundaryPort, **params) -> PhysicalEntryGate:
    """从 CollectorBoundaryPort 构造物理门（只取地址，不持有端口引用）。

    门不保存对 port 的引用——调用方每步显式传入 `port.spike_output` 给
    `step()`，保持"门只吃实时脉冲"的接口纯度（同 `make_entry_detector`
    的既有约定）。
    """
    return PhysicalEntryGate(generator_address=port.generator_address, **params)
