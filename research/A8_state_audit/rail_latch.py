"""rail_latch.py — F1 canonical RailLatch（唯一权威动力学，P0-4/P0-5/P1）。

TYPE:INFRA（research/ 隔离层，只读导入 nexus_v1）

## 量纲修正（P0-4，本轮必须改）

第二轮形式 `I_fb = k · MOSFET.conduct(V) · V_rail` 中：
  `MOSFET.conduct(V)` 返回**电流**（gm·(V−θ)），再乘 V_rail 得 A·V = W（功率）。
  量纲错误；且 k 无量纲时等于把"功率"当"电流"注入电容。

canonical 修正：
      I_fb = Σ_{n=1}^{N} MOSFET_n.conduct(V_read)      ← N 个同型 FET **并联**
      物理器件完全相同（同 θ、同 gm），N 是**物理支路数**，不是自由增益。
      量纲：每支路 A，N 支路相加仍为 A ✓
      数值：V_rail=1.0 时 N=3 ≡ 旧 k=3 —— 修正零成本，但去掉了无出处的 k。

## PowerRail 的角色（P0-5）

`MOSFET.conduct()` 已直接给出漏极电流（情况 A），因此 **PowerRail 不再乘进
该电流**。PowerRail 的职责严格限定为：
  (1) 作为反馈 FET 的**供电源**（记账其 IR 压降与供出电流）；
  (2) 提供 `v_actual` 供能源账本（P1-6）计算，**不调制**反馈电流。
若将来改用"电导型"建模（I=G(V_g)·V_rail），必须显式构造 G(V_g) 电导，
不得用返回电流的 `conduct()` 冒充——本轮不采用该路线。

## 每步顺序（与第二轮一致，唯一改动是反馈求和）

    1. cap.leak(R, dt)
    2. v_read = cap.voltage
    3. I_fb = Σ_n FET_n.conduct(v_read)          # N 支路并联
    4. cap.inject(I_fb + k_in·u, dt)             # u = 分级 relation current
    5. clamp：hard → discharge_to(v_clamp)；finite → 以 -I_clamp·dt 积分

## 输入换能（P0-6）

输入是 **graded relation current** u（单位 A），直接按 I·dt 注入，**不乘任何
增益**（k_in=1.0 即 fan-in 直接汇聚；候选不引入新的换能增益）。
若将来改为消费 binary event，必须显式插入 RelationEventAdapter 换能步。
"""
from __future__ import annotations

import math
import os
import sys
from dataclasses import dataclass, field

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from nexus_v1.components.semiconductor import Capacitor, MOSFET, PowerRail

DT = 0.001


@dataclass
class RailLatch:
    """F1 canonical：Capacitor + N×MOSFET(并联反馈) + PowerRail + 钳位。"""
    capacitance: float = 0.001
    r_leak: float = 600.0
    theta: float = 0.3
    gm: float = 1.0
    n_feedback_fets: int = 3
    v_rail: float = 1.0
    rail_r_internal: float = 0.0
    clamp_mode: str = "hard"          # "hard" | "finite" | "none"
    clamp_gm: float = 10.0
    clamp_threshold: float = 1.0
    k_in: float = 1.0
    dt: float = DT

    _cap: Capacitor = field(init=False, repr=False, default=None)
    _fets: list = field(init=False, repr=False, default_factory=list)
    _clamp_fet: MOSFET = field(init=False, repr=False, default=None)
    _rail: PowerRail = field(init=False, repr=False, default=None)
    _e_fb: float = field(init=False, repr=False, default=0.0)
    _e_clamp: float = field(init=False, repr=False, default=0.0)

    def __post_init__(self) -> None:
        if self.capacitance <= 0 or self.r_leak <= 0:
            raise ValueError("RailLatch: capacitance/r_leak must be > 0")
        if self.n_feedback_fets < 0:
            raise ValueError("RailLatch: n_feedback_fets 必须 ≥ 0"
                             "（0 = 反馈支路被物理断开，供 P1-5 阻断实验）")
        if self.clamp_mode not in ("hard", "finite", "none"):
            raise ValueError(f"RailLatch: 未知 clamp_mode {self.clamp_mode!r}")
        self._cap = Capacitor(capacitance=self.capacitance, charge=0.0)
        # N 条**同型**支路（同 θ、同 gm）——物理器件完全相同
        self._fets = [MOSFET(v_threshold=self.theta, gm=self.gm)
                      for _ in range(self.n_feedback_fets)]
        self._clamp_fet = MOSFET(v_threshold=self.clamp_threshold,
                                 gm=self.clamp_gm)
        self._rail = PowerRail(vdd=self.v_rail, r_internal=self.rail_r_internal)

    # ── 物理过程 ──
    def step(self, u: float = 0.0, dt: float | None = None) -> float:
        dt = self.dt if dt is None else dt
        # 1. RC 泄漏
        self._cap.leak(self.r_leak, dt)
        # 2. 读充电前节点电压
        v_read = self._cap.voltage
        # 3. N 支路并联反馈电流（量纲 = A）
        i_fb = sum(fet.conduct(v_read) for fet in self._fets)
        self._rail.draw(i_fb)                      # 记账（不调制电流，P0-5）
        # 4. 注入：反馈 + 输入（graded relation current，无增益）
        self._cap.inject(i_fb + self.k_in * u, dt)
        self._e_fb += i_fb * v_read * dt            # P1-6 能源账本
        # 5. 钳位
        self._apply_clamp(dt)
        return self._cap.voltage

    def _apply_clamp(self, dt: float) -> None:
        if self.clamp_mode == "none":
            return
        v = self._cap.voltage
        if v <= self.clamp_threshold:
            return
        if self.clamp_mode == "hard":
            excess = v - self.clamp_threshold
            i_c = self._clamp_fet.conduct(v)
            self._e_clamp += i_c * excess * dt      # Zener 耗散记账
            self._cap.discharge_to(self.clamp_threshold)
        else:  # finite：真实积分 -I_clamp·dt（不强制复位）
            i_c = self._clamp_fet.conduct(v)
            self._cap.inject(-i_c, dt)
            self._e_clamp += i_c * v * dt

    # ── 只读观测 ──
    @property
    def state(self) -> float:
        return self._cap.voltage

    @property
    def lam(self) -> float:
        return math.exp(-self.dt / (self.r_leak * self.capacitance))

    @property
    def mu(self) -> float:
        """单步反馈增益（反馈电流 → 电压增量的无量纲斜率）。"""
        return self.n_feedback_fets * self.gm * self.dt / self.capacitance

    def energy_ledger(self) -> dict:
        return {"feedback_energy": self._e_fb, "clamp_dissipation": self._e_clamp,
                "stored_energy": 0.5 * self._cap.charge ** 2 / self.capacitance,
                "rail_v_actual": self._rail.v_actual}

    # ── 解析映射（供 P1 的 0 容差比对）──
    def analytic_step(self, v: float, u: float = 0.0, dt: float | None = None) -> float:
        dt = self.dt if dt is None else dt
        lam = math.exp(-dt / (self.r_leak * self.capacitance))
        v_read = lam * v
        i_fb = self.n_feedback_fets * self.gm * max(0.0, v_read - self.theta)
        v_new = v_read + (i_fb + self.k_in * u) * dt / self.capacitance
        if self.clamp_mode == "hard" and v_new > self.clamp_threshold:
            v_new = self.clamp_threshold
        return max(0.0, v_new)

    def fixed_points(self) -> list[dict]:
        """解析固定点（含边界/钳位支，方案 §C 分类）。仅对 hard/none 有效。"""
        lam, N = self.lam, self.n_feedback_fets
        mu = N * self.gm * self.dt / self.capacitance
        fps = [{"v": 0.0, "type": "interior", "deriv": lam,
                "stability": "stable" if lam < 1 else "unstable"}]
        denom = lam * (1 + mu) - 1
        if denom > 0:
            v_u = mu * self.theta / denom
            if self.theta < v_u / lam < self.clamp_threshold:
                fps.append({"v": v_u, "type": "interior", "deriv": lam * (1 + mu),
                            "stability": "unstable"})
            f_top = lam * self.clamp_threshold + mu * max(
                0.0, lam * self.clamp_threshold - self.theta)
            if self.clamp_mode == "hard" and f_top > self.clamp_threshold:
                fps.append({"v": self.clamp_threshold, "type": "boundary(clamp)",
                            "deriv": 0.0, "stability": "stable(one-sided)"})
        return fps

    def finite_clamp_fixed_point(self) -> float | None:
        """finite 钳位的连续高态：λV + μmax(0,λV−θ) − clamp_gm·(V−V_c)·dt/C = V。"""
        lam, mu = self.lam, self.mu
        g = self.clamp_gm * self.dt / self.capacitance
        # 高区（λV>θ 且 V>V_c）：λV + μ(λV−θ) − g(V−V_c) = V
        a = lam * (1 + mu) - 1 - g
        b = -mu * self.theta + g * self.clamp_threshold
        if abs(a) < 1e-18:
            return None
        v = -b / a
        return v if v > max(self.theta / lam, self.clamp_threshold) else None


if __name__ == "__main__":
    print("=" * 68)
    print("RailLatch canonical 自检（P1：解析映射 vs 实际 step，0 容差）")
    print("=" * 68)
    z = RailLatch()
    v_a, ok = 0.0, True
    for n in range(5000):
        u = 0.4 if n < 1000 else 0.0
        v_a = z.analytic_step(v_a, u)
        v_r = z.step(u)
        if v_r != v_a:
            print(f"  MISMATCH @n={n}: real={v_r!r} analytic={v_a!r}")
            ok = False
            break
    print(f"  5000 步逐位一致: {ok}")
    print(f"  λ={z.lam:.9f}  μ(每支路)={z.mu:.6f}  N={z.n_feedback_fets}")
    for fp in z.fixed_points():
        print(f"  FP: V*={fp['v']:.6f} {fp['type']:<16} "
              f"deriv={fp['deriv']:.6f} {fp['stability']}")
    sys.exit(0 if ok else 1)
