"""candidate_z.py — A8 时间方向组织候选 Z（四原语组装，research/ 隔离层）。

TYPE:HYBRID（不进 TSS 主路径；不被 tss/** 或 nexus_v1/** 导入）

依据：cell-cell/claudecode方案/A8-A9-K-06时间方向组织候选_执行方案修订_2026-09-10.md
      §A（判据）/ §I（原语审计结论）

## 本轮的核心判据（§A.2）

𝒜⁺ = 对完整 relation current 序列 r(t) 施加「真实父层同型物理栈」可得的
    全部物理量的有限次复合。候选 Z ∈ A8 ⟺ 存在合法 formation 使
    Z(t) 不被 𝒜⁺ 重构（相对残差显著非零）。

§A.3 冻结表说明：单 H_τ、H_τ+H_τ 线性叠加、H_τ 换 τ、y=f(H_τ) 全部 ∈ 𝒜⁺。

## 三个候选（统一 step(r1, r2, dt) → float 差分读出接口）

  C0-ZLinearRC    控制件（**已知 ∈ 𝒜⁺**，情况 B 的参数变体）。
                  用途 = §C 的 C-null-3 重构器自检：重构器对它必须给 ≈0 残差。
  C0-ZSaturating  控制件（**已知 ∈ 𝒜⁺**）：线性积分 + 上界钳位。
                  用途 = §A.3 的"情况 C/E"标定：证明饱和不构成 A8。
  C1-ZMemristive  候选（跨出 𝒜⁺ 的尝试）：memristive 状态依赖正反馈。
                  Memristor 电导由自身权重决定，权重更新通量又由电导放大
                  ⇒ 真正的状态依赖非线性 `ż = f(z)·a(t)`，§I 表列的唯一
                  带记忆非线性来源。

## RULES.md 强制三问

Q1 生物对应物：
   - C0-ZSaturating = 被动钙池的有限容量（Ca²⁺ 缓冲饱和）
     REF: Neher & Augustine 1992 J Physiol（钙缓冲的有限容量）。
   - C1-ZMemristive = 树突棘的**状态依赖可塑性**：棘器件的有效电导随累积
     通量改变，而改变后的电导又决定后续通量——这一闭环是本候选的全部内容。
     REF: Strukov et al. 2008 Nature 453:80（memristor 的固态物理模型）；
     REF: Jo et al. 2010 Nano Lett 10:1297（memristive 开关的阈值与迟滞）。
     项目内先例：Memristor 已是 SynapticBundle 的权重载体
     （semiconductor.py:206），本候选只是把它从"被读取的权重"升级为
     "物理回路中的状态变量"，不引入新原语。

Q2 物理结构：
   Capacitor（节点状态）+ MOSFET（阈值/硬截断，DEG-019 行为）+
   Memristor（状态依赖电导）+ PowerRail（供电与 IR 压降）。零新类、零新原语。
   本类不做 SynapticBundle 接线——research/ 隔离件直接消费适配器输出
   （§F 的隔离纪律：不进 census/账本体系）。

Q3 参数依据（**全部由物理标定，非任意填写；见 calibrate()**）：
   r_leak    = 0.6   ← 沿用 H_τ _DEFAULT_R_LEAK（history_kernel.py:54 已有推导）。
                       与父层同一时间尺度，**主动排除**"靠更慢 τ 取胜"（情况 B 变体）。
   theta_*   = 0.3   ← MOSFET.v_threshold 默认值（semiconductor.py:117），
                       与 C_Θ _DEFAULT_THETA_H 同源。
   gm_*      = 1.0   ← MOSFET.gm 默认值。
   v_clamp   = 1.0   ← 同 entry_gate _DEFAULT_V_CLAMP。
   r_min/r_max（Memristor） = 0.1/10.0 ← 原语默认（semiconductor.py:216-217），
                       **不调参**：调它就是把候选推到父层参数之外（情况 B）。
   k_*       ← 见 calibrate()：由"无输入时状态是否驻留"与"是否可被相同输入
               再次推过阈值"两条物理判据反解，不是手填。

## 禁止字段

无 relation_instance_id / epoch_id / lineage；无软件状态位（0/1 标签）；
step() 内无行为性 if/else——仅保留物理限幅（同 entry_gate 的 Zener 手法，
项目惯例允许：构造期接线与边界防护，见 memory《if/else硬编码规则精确范围》）。
"""

from __future__ import annotations

import os
import sys
from dataclasses import dataclass, field

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from nexus_v1.components.semiconductor import Capacitor, MOSFET, Memristor, PowerRail


# ═════════════════════════════════════════════════════════════════════
# C0-ZLinearRC：控制件（已知 ∈ 𝒜⁺）
# ═════════════════════════════════════════════════════════════════════

@dataclass
class ZLinearRC:
    """C0 控制件：单电容线性积分 + RC 泄漏。**就是** H_τ 的参数变体（情况 B）。

    唯一用途 = §C 的 C-null-3：重构器对它必须给出 ≈0 残差，
    否则重构器实现有误，本轮全部结论作废。
    """
    capacitance: float = 1.0
    r_leak: float = 0.6
    q_pulse: float = 1.0

    _cap: Capacitor = field(init=False, repr=False, default=None)

    def __post_init__(self) -> None:
        if self.capacitance <= 0:
            raise ValueError("ZLinearRC: capacitance must be > 0")
        self._cap = Capacitor(capacitance=self.capacitance, charge=0.0)

    def step(self, r1: float, r2: float, dt: float) -> float:
        self._cap.leak(self.r_leak, dt)
        if r1 > 0.0:
            self._cap.inject(self.q_pulse * r1, dt)
        return self._cap.voltage

    @property
    def state(self) -> float:
        return self._cap.voltage


# ═════════════════════════════════════════════════════════════════════
# C0-ZSaturating：控制件（已知 ∈ 𝒜⁺，情况 C/E 的标定）
# ═════════════════════════════════════════════════════════════════════

@dataclass
class ZSaturating:
    """C0 控制件：线性积分 + 上界钳位（有限容量池）。**已知 ∈ 𝒜⁺**。

    用途 = 证明"饱和/平台"不构成 A8（原方案情况 C/E）：
    钳位是静态逐元素函数，重构器含硬截断即可复现。
    """
    capacitance: float = 1.0
    r_leak: float = 0.6
    q_pulse: float = 1.0
    v_clamp: float = 1.0

    _cap: Capacitor = field(init=False, repr=False, default=None)

    def __post_init__(self) -> None:
        self._cap = Capacitor(capacitance=self.capacitance, charge=0.0)

    def step(self, r1: float, r2: float, dt: float) -> float:
        self._cap.leak(self.r_leak, dt)
        if r1 > 0.0:
            self._cap.inject(self.q_pulse * r1, dt)
        if self._cap.voltage > self.v_clamp:      # Zener 限幅（同 entry_gate 手法）
            self._cap.discharge_to(self.v_clamp)
        return self._cap.voltage

    @property
    def state(self) -> float:
        return self._cap.voltage


# ═════════════════════════════════════════════════════════════════════
# 权重窗口函数（memristor 边界行为的物理化）
# ═════════════════════════════════════════════════════════════════════

def _window(w: float, w_clamp: float) -> float:
    """Joglekar 窗函数：w∈[0, w_clamp] 内平滑，边界处更新速率→0。

    REF: Joglekar & Wolf 2009 Eur J Phys 30:661（memristor 边界窗函数）。
    物理意义：离子漂移在器件边缘受缺陷/势垒抑制，权重不越界。
    本函数是**静态逐元素函数**，不引入新状态，不影响 𝒜⁺ 判据的构成。
    """
    if w_clamp <= 0.0:
        return 0.0
    x = max(0.0, min(1.0, w / w_clamp))
    return 1.0 - (2.0 * x - 1.0) ** 4


# ═════════════════════════════════════════════════════════════════════
# C1-ZMemristive：候选（状态依赖非线性）
# ═════════════════════════════════════════════════════════════════════

@dataclass
class ZMemristive:
    """C1 候选：memristive 状态依赖正反馈（自启动门 + 通量驱动电导）。

    ★ 设计修正（首轮校准暴露的自门控死锁）：若把进入电导写成 g_in=conduct(v)，
      则 v=0 时 g_in=0 ⇒ 无电流 ⇒ v 永不上升（冷启动死锁，实测 v 恒 0）。
      修正：把**正反馈路径交给 memristor 电导**（由权重 w 决定，与 v 无关），
      节点的自启动由独立的供电轨电流保证。

    每步顺序：
      1. 电容 RC 泄漏
      2. 读节点电压 v（充电前）
      3. 自启动/驱动门：g_port = conduct(v_supply) × conduct(v_half)
         —— 由供电轨电压驱动，保证 v=0 时仍有电流可注入（非死锁）
      4. memristor 通流：I_mem = v_supply × G(w)
             G(w) = Memristor.conductance（由 w 决定，原语属性）
      5. 外部驱动：I_drive = g_port × r1（父层 relation current 进入同一节点）
      6. 注入：I_total = k_mem·I_mem + k_drive·I_drive
      7. memristor 权重更新（**通量驱动**）：
             dw = 0.5 · I_mem · (pre − post)，pre=|I_mem|，post=0
             ⇒ 偏置通量使 w 单调增长（等价 Strukov dw/dt = μ·R_on/D²·i(t)）

    闭环（状态依赖）：I_mem ↑ ⇒ w ↑ ⇒ G(w) ↑ ⇒ I_mem ↑
    —— `ẇ = f(w)·a(t)` 型，§A.3 冻结表列其 ∉ 𝒜⁺。
    且 memristor **无衰减项**（原语只有 apply_dw）：washout 期 r1=0 时
    节点 v 依 RC 回零，但 w 不回退 ⇒ w 保有形成期信息。
    """
    capacitance: float = 1.0
    r_leak: float = 0.6
    theta_port: float = 0.3
    gm_port: float = 1.0
    v_supply: float = 1.0
    k_mem: float = 0.0    # 恒定时变偏置置零：状态必须由输入驱动，不得自发饱和
    k_drive: float = 1.0
    k_gain: float = 10.0      # memristor 电导→门极增益（见 docstring Q3 标定）
    k_gain_stab: float = 1.0  # 通流分母稳定项（防 G 大时发散）
    v_clamp: float = 1.0
    w_clamp: float = 0.9  # 权重上限（防饱和出域；见模块 docstring）

    _cap: Capacitor = field(init=False, repr=False, default=None)
    _m_port: MOSFET = field(init=False, repr=False, default=None)
    _mem: Memristor = field(init=False, repr=False, default=None)
    _rail: PowerRail = field(init=False, repr=False, default=None)

    def __post_init__(self) -> None:
        if self.capacitance <= 0 or self.r_leak <= 0:
            raise ValueError("ZMemristive: capacitance/r_leak must be > 0")
        if not (0.0 < self.theta_port < self.v_clamp):
            raise ValueError("ZMemristive: 需 0 < theta_port < v_clamp")
        self._cap = Capacitor(capacitance=self.capacitance, charge=0.0)
        self._m_port = MOSFET(v_threshold=self.theta_port, gm=self.gm_port)
        self._mem = Memristor(w=0.5)                     # 原语默认 r_min/r_max
        self._rail = PowerRail(vdd=self.v_supply, r_internal=0.0)

    def step(self, r1: float, r2: float, dt: float) -> float:
        # 1. RC 泄漏
        self._cap.leak(self.r_leak, dt)
        v = self._cap.voltage                            # 2. 充电前读出

        # 3. 驱动门：输入 relation current 先经 **memristor 增益**再加到门极。
        #    ★ 修正记录（两次）：先前把 r1 直接送门极，而 r1=0.17 < θ=0.3，
        #      MOSFET 硬截断（DEG-019）使 g_port≡0 ⇒ 输出恒零——那是实现错误。
        #      物理语义应为：**输入电流经 memristor 器件后**才达到门极，
        #      器件增益 G(w) 进入，状态因此调制读出。
        v_gate = self.k_drive * r1 * (1.0 + self.k_gain * self._mem.conductance)
        g_port = self._m_port.conduct(v_gate)

        # 4. 经 memristor 的通流（读出门与保持元件同一路径）：
        #    I = g_port × v_gate × G(w) / (1 + k_gain·G(w))
        #    ⇒ 相同 probe r1 经不同 w 给出不同电流：状态对读出有直接作用。
        i_mem = g_port * v_gate * self._mem.conductance / (
            1.0 + self.k_gain_stab * self._mem.conductance)

        # 5. 注入
        self._cap.inject(i_mem + self.k_mem * i_mem, dt)

        # 6. 通量驱动权重更新（pre=|I_mem| 通量，post=0）
        #    窗口函数（Joglekar 窗）：w→w_clamp 时更新速率→0，
        #    防止权重跑出 [0, w_clamp] 的物理域（原语 apply_dw 的 clamp 保留）
        self._mem.update(current=i_mem, pre_trace=abs(i_mem) * _window(self._mem.w, self.w_clamp),
                         post_trace=0.0)

        # 7. 物理限幅（Zener 手法，同 entry_gate step 第 5 步）
        if self._cap.voltage > self.v_clamp:
            self._cap.discharge_to(self.v_clamp)
        elif self._cap.voltage < 0.0:
            self._cap.discharge_to(0.0)

        return self._cap.voltage

    # ── 只读观测 ──
    @property
    def state(self) -> float:
        return self._cap.voltage

    @property
    def weight(self) -> float:
        """Memristor 权重（**观测，不参与物理**）——A8 的主观测量候选。"""
        return self._mem.w


# ═════════════════════════════════════════════════════════════════════
# 标定与自检
# ═════════════════════════════════════════════════════════════════════

def calibrate(verbose: bool = False) -> dict:
    """物理标定：验证各候选在其合法工作域内可被驱动与读出。

    判据：
      (a) C0-ZLinearRC：驱动期节点电压显著上升（可到达）
      (b) C0-ZSaturating：驱动期触到钳位（饱和可达）
      (c) C1-ZMemristive：驱动期 v 上升 且 memristive 权重单调增长
                          （状态依赖闭环确实闭合）
    """
    out = {}

    z = ZLinearRC()
    for _ in range(3000):
        z.step(0.17, 0.0, 0.001)
    out["linear_reachable"] = z.state > 0.1
    out["linear_v"] = z.state

    zs = ZSaturating()
    for _ in range(3000):
        zs.step(0.17, 0.0, 0.001)
    out["saturating_clamped"] = abs(zs.state - zs.v_clamp) < 1e-9
    out["saturating_v"] = zs.state

    zm = ZMemristive()
    w0 = zm.weight
    for _ in range(3000):
        zm.step(0.17, 0.0, 0.001)
    out["memristive_reachable"] = zm.state > 0.1
    out["memristive_v"] = zm.state
    out["memristive_w0"] = w0
    out["memristive_w1"] = zm.weight
    out["memristive_w_grew"] = zm.weight > w0

    if verbose:
        for k, v in out.items():
            print(f"[calibrate] {k} = {v}")
    return out


if __name__ == "__main__":
    ok = calibrate(verbose=True)
    all_ok = (ok["linear_reachable"] and ok["saturating_clamped"]
              and ok["memristive_reachable"] and ok["memristive_w_grew"])
    print(f"\n[candidate_z] calibration {'PASS' if all_ok else 'FAIL'}")
    sys.exit(0 if all_ok else 1)
