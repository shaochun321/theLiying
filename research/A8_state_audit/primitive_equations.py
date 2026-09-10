"""primitive_equations.py — 原语动力学方程 + 组合拓扑（§7-§8）。

TYPE:INFRA（research/ 隔离层，只读导入 nexus_v1，不改任何冻结模块）

依据：cell-cell/claudecode方案/A8最小充分状态重定义与多稳态审计_执行方案修订_2026-09-11.md
     （下称"修订稿"）§G F 类清单 / §D Domain B 出处规则

## 原语精确离散映射（与代码逐位一致，main() 自检）

Capacitor.leak:    Q' = Q·e^{−dt/(R·C)}          （精确指数，非 Euler）
Capacitor.inject:  Q' = Q + I·dt
MOSFET.conduct:    I  = gm·max(0, V−θ)            （阈下硬截零，DEG-019）
Memristor:         G(w) = min(1/(r_min+(r_max−r_min)(1−w)), 1/r_min)
                   Δw = clamp(0.5·i·(pre−post))
PowerRail.draw:    V = max(0, vdd − I·R_int)

## F1 单节点正反馈（轨供电闩锁）——本轮主审对象

每步（leak → 读 V → 反馈+输入 → inject → Zener 钳位）：

    V_read = λ·V_n,  λ = e^{−dt/(R·C)}
    I_fb   = k·gm·max(0, V_read − θ)·V_rail      ← MOSFET 栅极=本节点，漏极=供电轨
    V_{n+1} = min(V_clamp, V_read + (I_fb + u_n)·dt/C)

固定点（解析，分段仿射）：
    V*=0                                  （V<θ 区，导数 λ<1，稳定）
    V_u = μθ/(λ(1+μ)−1),  μ = k·gm·V_rail·dt/C   （不稳定，导数 λ(1+μ)>1）
    V*=V_clamp                            （边界固定点/钳位支撑，单侧导数 0，稳定）
    存在条件：λ(1+μ)>1 且 V_u < V_clamp

## 参数 provenance（修订稿 §D，全部 Domain B）

    θ=0.3, gm=1.0        ← MOSFET 默认（semiconductor.py:117,118）
    V_rail=1.0           ← entry_gate _DEFAULT_V_CLAMP
    C：1.0（原语默认）或 0.001（RelationInputNeuron capacitance 先例）
    R：使 τ=R·C=0.6s=600 步 ← H_τ 同尺度（history_kernel.py:54），
       R 取值 0.6~600 均在母体 r_leak 实例化跨度 [1.0*, 5000] 附近
       （*collector 1.5、EnergyStore 5000；R=0.6 即 H_τ 本身的取值）
    k（反馈/输入增益）≤7.5 ← da_gate η=7.5（variant_adapter.py）
    k_in=0.5             ← frozen 换能束权重先例 w=0.3~0.5（transducer/adapter）
"""
from __future__ import annotations

import math
import os
import sys
from dataclasses import dataclass, field

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from nexus_v1.components.semiconductor import Capacitor, MOSFET, Memristor, PowerRail

DT = 0.001


# ─────────────────────────────────────────────────────────────────────
# F1：轨供电单节点闩锁（真实原语组装）
# ─────────────────────────────────────────────────────────────────────

@dataclass
class RailLatch:
    """F1 候选：Capacitor + MOSFET(反馈门) + PowerRail + Zener 钳位。

    与上轮 ZBistableLatch 的关键差异（修订稿 §I 勘误的核心）：
    反馈电流 = k·g(V)·V_rail（轨供电，washout 期自持），
    而非上轮误写的 k·g(V)·r1（输入门控，washout 期归零）。
    """
    capacitance: float = 1.0
    r_leak: float = 0.6          # τ = R·C = 600 步（H_τ 同尺度）
    theta: float = 0.3
    gm: float = 1.0
    v_rail: float = 1.0
    k: float = 3.0
    k_in: float = 1.0
    v_clamp: float = 1.0

    _cap: Capacitor = field(init=False, repr=False, default=None)
    _fet: MOSFET = field(init=False, repr=False, default=None)
    _rail: PowerRail = field(init=False, repr=False, default=None)

    def __post_init__(self) -> None:
        self._cap = Capacitor(capacitance=self.capacitance, charge=0.0)
        self._fet = MOSFET(v_threshold=self.theta, gm=self.gm)
        self._rail = PowerRail(vdd=self.v_rail, r_internal=0.0)

    def step(self, u: float, dt: float = DT) -> float:
        self._cap.leak(self.r_leak, dt)
        v = self._cap.voltage
        i_fb = self.k * self._fet.conduct(v) * self._rail.draw(0.0)
        self._cap.inject(i_fb + self.k_in * u, dt)
        if self._cap.voltage > self.v_clamp:
            self._cap.discharge_to(self.v_clamp)
        elif self._cap.voltage < 0.0:
            self._cap.discharge_to(0.0)
        return self._cap.voltage

    @property
    def state(self) -> float:
        return self._cap.voltage

    # ── 解析量（审计用，不参与物理） ──
    @property
    def lam(self) -> float:
        return math.exp(-DT / (self.r_leak * self.capacitance))

    @property
    def mu(self) -> float:
        return self.k * self.gm * self.v_rail * DT / self.capacitance

    def fixed_points(self) -> list[dict]:
        """解析固定点（修订稿 §C 含边界固定点分类）。"""
        lam, mu = self.lam, self.mu
        fps = [{"v": 0.0, "type": "interior", "deriv": lam,
                "stability": "stable" if lam < 1 else "unstable"}]
        denom = lam * (1 + mu) - 1
        if denom > 0:
            v_u = mu * self.theta / denom
            if self.theta < v_u / lam < self.v_clamp:   # 读出点 λV>θ 的区域一致性
                fps.append({"v": v_u, "type": "interior",
                            "deriv": lam * (1 + mu), "stability": "unstable"})
            # 钳位支：F(V_clamp) 是否仍越上界
            f_top = lam * self.v_clamp + mu * max(0.0, lam * self.v_clamp - self.theta)
            if f_top > self.v_clamp:
                fps.append({"v": self.v_clamp, "type": "boundary(clamp)",
                            "deriv": 0.0, "stability": "stable(one-sided)"})
        return fps


# ─────────────────────────────────────────────────────────────────────
# F2：两节点互激（活动闩锁）
# ─────────────────────────────────────────────────────────────────────

@dataclass
class MutualExcitation:
    """F2：x 由 g(y) 供流、y 由 g(x) 供流（轨供电）。"""
    capacitance: float = 1.0
    r_leak: float = 0.6
    theta: float = 0.3
    gm: float = 1.0
    v_rail: float = 1.0
    k: float = 3.0
    v_clamp: float = 1.0

    def __post_init__(self) -> None:
        self._cx = Capacitor(capacitance=self.capacitance, charge=0.0)
        self._cy = Capacitor(capacitance=self.capacitance, charge=0.0)
        self._fx = MOSFET(v_threshold=self.theta, gm=self.gm)
        self._fy = MOSFET(v_threshold=self.theta, gm=self.gm)
        self._rail = PowerRail(vdd=self.v_rail, r_internal=0.0)

    def step(self, ux: float, uy: float, dt: float = DT):
        self._cx.leak(self.r_leak, dt)
        self._cy.leak(self.r_leak, dt)
        x, y = self._cx.voltage, self._cy.voltage
        vr = self._rail.draw(0.0)
        ix = self.k * self._fx.conduct(y) * vr + ux     # 交叉：y 供 x
        iy = self.k * self._fy.conduct(x) * vr + uy
        self._cx.inject(ix, dt)
        self._cy.inject(iy, dt)
        for c in (self._cx, self._cy):
            if c.voltage > self.v_clamp:
                c.discharge_to(self.v_clamp)
            elif c.voltage < 0.0:
                c.discharge_to(0.0)
        return self._cx.voltage, self._cy.voltage


# ─────────────────────────────────────────────────────────────────────
# F3：两节点互抑（WTA 选择闩锁）——背景驱动用 vdd+r_supply 既有模式
# ─────────────────────────────────────────────────────────────────────

@dataclass
class MutualInhibition:
    """F3：背景供流 I=(vdd−V)/r_supply（Neuron config 的既有模式），
    互抑 −k_inh·g(V_other)。编码"哪一侧赢"而非"是否激活"。
    """
    capacitance: float = 1.0
    r_leak: float = 0.6
    theta: float = 0.3
    gm: float = 1.0
    vdd: float = 1.0             # ← Neuron config vdd 先例（默认 2.0/此处 1.0=V_clamp）
    r_supply: float = 1.2        # 使基线 V* = vdd·R/(R+Rs) = 0.6/1.8·1.2… 见 main
    k_inh: float = 3.0
    v_clamp: float = 1.0

    def __post_init__(self) -> None:
        self._cx = Capacitor(capacitance=self.capacitance, charge=0.0)
        self._cy = Capacitor(capacitance=self.capacitance, charge=0.0)
        self._fx = MOSFET(v_threshold=self.theta, gm=self.gm)
        self._fy = MOSFET(v_threshold=self.theta, gm=self.gm)

    def step(self, ux: float, uy: float, dt: float = DT):
        self._cx.leak(self.r_leak, dt)
        self._cy.leak(self.r_leak, dt)
        x, y = self._cx.voltage, self._cy.voltage
        ix = (self.vdd - x) / self.r_supply - self.k_inh * self._fx.conduct(y) + ux
        iy = (self.vdd - y) / self.r_supply - self.k_inh * self._fy.conduct(x) + uy
        self._cx.inject(ix, dt)
        self._cy.inject(iy, dt)
        for c in (self._cx, self._cy):
            if c.voltage > self.v_clamp:
                c.discharge_to(self.v_clamp)
            elif c.voltage < 0.0:
                c.discharge_to(0.0)
        return self._cx.voltage, self._cy.voltage


# ─────────────────────────────────────────────────────────────────────
# F4：Memristor 闭环（上轮拓扑的 w 流函数）
# ─────────────────────────────────────────────────────────────────────

def memristor_flow(w: float, u: float, w_clamp: float = 0.9) -> float:
    """上轮 ZMemristive 拓扑在给定 (w, u) 下的单步 Δw（w 流函数）。

    i_mem = g_port(u)·u_eff·G(w)/(1+G(w))；Δw = 0.5·i·|i|·window(w)。
    u=0 时 i=0 ⇒ Δw=0 对所有 w —— 整个 [0,1] 是边际固定点连续统。
    """
    mem = Memristor(w=w)
    fet = MOSFET(v_threshold=0.3, gm=1.0)
    v_gate = u * (1.0 + 10.0 * mem.conductance)
    g_port = fet.conduct(v_gate)
    i = g_port * v_gate * mem.conductance / (1.0 + mem.conductance)
    x = max(0.0, min(1.0, w / w_clamp))
    window = 1.0 - (2.0 * x - 1.0) ** 4
    return 0.5 * i * abs(i) * window


# ─────────────────────────────────────────────────────────────────────
# 自检：解析映射与真实原语逐位一致
# ─────────────────────────────────────────────────────────────────────

def verify_exact_maps() -> bool:
    """F1 的解析每步映射与真实原语组合逐位一致（0 容差）。"""
    z = RailLatch(k=3.0)
    lam, mu = z.lam, z.mu
    v_analytic = 0.0
    ok = True
    for n in range(5000):
        u = 0.4 if n < 1000 else 0.0
        v_read = lam * v_analytic
        i_fb = z.k * z.gm * max(0.0, v_read - z.theta) * z.v_rail
        v_analytic = v_read + (i_fb + z.k_in * u) * DT / z.capacitance
        v_analytic = min(z.v_clamp, max(0.0, v_analytic))
        v_real = z.step(u)
        if v_real != v_analytic:
            print(f"  MISMATCH @n={n}: real={v_real!r} analytic={v_analytic!r}")
            ok = False
            break
    return ok


if __name__ == "__main__":
    print("=" * 68)
    print("primitive_equations 自检：解析映射 vs 真实原语（0 容差）")
    print("=" * 68)
    ok = verify_exact_maps()
    print(f"  F1 RailLatch 5000 步逐位一致: {ok}")
    z = RailLatch(k=3.0)
    print(f"  λ={z.lam:.6f}  μ={z.mu:.6f}")
    for fp in z.fixed_points():
        print(f"  FP: V*={fp['v']:.6f}  {fp['type']:<16} deriv={fp['deriv']:.6f}  {fp['stability']}")
    sys.exit(0 if ok else 1)
