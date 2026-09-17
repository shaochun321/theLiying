"""rail_latch.py — F1 canonical RailLatch（第四轮：rail 因果供能，路径 B）。

TYPE:INFRA（research/ 隔离层，只读导入 nexus_v1）

## 第四轮修正（依据 F1_FEEDBACK_POWER_CONTRACT.md，先契约后代码）

第三轮结构 `i_fb = Σ conduct(v_read); rail.draw(i_fb) 返回值丢弃; inject(i_fb)`
中 PowerRail 是纯账本：外部实测 Vrail∈{1,0.5,0.1,0} 全部 Z=1，供能不因果。

契约裁定（Q1）：母体 `MOSFET.conduct()` 是"理想供电假设下的期望漏极电流"，
不得直接注入。本轮采用**路径 B（显式电导）**：

    G(V_g)   = Σ_{n=1}^{N} g_c · max(0, V_g − θ)          [G]  = S
    g_c      = gm / V_REF,  V_REF = 1.0 V                  [g_c]= S/V
    I_fb     = G(V_g) · vdd / (1 + G·R_s)                  [I]  = A（负载线闭解）
    V_supply = vdd / (1 + G·R_s)

物理对应 = MOSFET 线性（triode）区 I_D = k′(V_GS−V_th)·V_DS 的小 V_DS 段；
g_c 是单位换算（额定供电 V_REF=vdd=1.0 V 下输出等于原 transconductance
支路），不是新自由参数。数值：vdd=1.0、R_s=0 时与第三轮逐位一致（修正
零成本，外部 M1–M4 基线保持）。

因果性由结构保证（无 if）：vdd=0 ⇒ I_fb ≡ 0；高态断电后仅剩 RC 泄漏。
`PowerRail.draw(I_fb)` 返回电压作为负载线闭解的一致性自检通道。

## 每步顺序

    1. cap.leak(R, dt)
    2. v_read = cap.voltage
    3. G = Σ g_c·max(0, v_read−θ)；I_fb = G·vdd/(1+G·R_s)   ← 供能因果
    4. cap.inject(I_fb + k_in·u, dt)                          u = relation current
    5. clamp：hard → discharge_to(V_c)；finite → -I_clamp·dt 积分

## 因果能源账本（契约 §四，八字段 + 精确泄漏/钳位/储能）

    E_emf      = Σ vdd·I_fb·dt          rail EMF 做功
    E_rail     = Σ I_fb²·R_s·dt         内阻耗散
    E_chan     = Σ (V_supply−v_read)·I_fb·dt   FET 沟道耗散（一阶）
    E_node_fb  = Σ v_read·I_fb·dt       注入节点（一阶；= 旧 feedback_energy）
    E_input    = Σ v_read·k_in·u·dt
    E_leak / E_clamp_exact / ΔE_stored  由 C/2·ΔV² 精确记账
    闭合残差 = (E_node_fb+E_input) − (ΔE_stored+E_leak+E_clamp_exact)，
    理论上 O(dt)/单位时间——判定见契约（一阶收敛 ⇒ AUDITABLE）。

## 参数单源（P1-4 修正）

默认值直接取自 candidate_config.CANONICAL（旧版 k_in 默认 1.0 ≠ canonical
0.5 的隐式分歧已消除）；实验模块仍应显式传 config。
"""
from __future__ import annotations

import math
import os
import sys
from dataclasses import dataclass, field

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from nexus_v1.components.semiconductor import Capacitor, MOSFET, PowerRail
from research.A8_state_audit.candidate_config import CANONICAL

DT = CANONICAL["dt"]
V_REF = 1.0   # 契约 §二：g_c = gm/V_REF；V_REF = 母体 PowerRail vdd 默认 = 1.0 V


@dataclass
class RailLatch:
    """F1 canonical：Capacitor + N×电导支路(rail 因果供电) + PowerRail + 钳位。"""
    capacitance: float = CANONICAL["C"]
    r_leak: float = CANONICAL["R"]
    theta: float = CANONICAL["theta"]
    gm: float = CANONICAL["gm"]
    n_feedback_fets: int = CANONICAL["n_feedback_fets"]
    v_rail: float = CANONICAL["v_rail"]
    rail_r_internal: float = CANONICAL["rail_r_internal"]
    clamp_mode: str = CANONICAL["clamp_mode"]   # "hard" | "finite" | "none"
    clamp_gm: float = CANONICAL["clamp_gm"]
    clamp_threshold: float = CANONICAL["clamp_threshold"]
    k_in: float = CANONICAL["k_in"]
    dt: float = DT

    _cap: Capacitor = field(init=False, repr=False, default=None)
    _fets: list = field(init=False, repr=False, default_factory=list)
    _clamp_fet: MOSFET = field(init=False, repr=False, default=None)
    _rail: PowerRail = field(init=False, repr=False, default=None)
    # ── 因果能源账本（契约 §四）──
    _e_emf: float = field(init=False, repr=False, default=0.0)
    _e_rail_loss: float = field(init=False, repr=False, default=0.0)
    _e_channel: float = field(init=False, repr=False, default=0.0)
    _e_node_fb: float = field(init=False, repr=False, default=0.0)
    _e_input: float = field(init=False, repr=False, default=0.0)
    _e_leak: float = field(init=False, repr=False, default=0.0)
    _e_clamp_exact: float = field(init=False, repr=False, default=0.0)
    _e_clamp_legacy: float = field(init=False, repr=False, default=0.0)
    _e_stored_0: float = field(init=False, repr=False, default=0.0)
    # 最近一步诊断（供 rail causality 实验读取）
    last_i_fb: float = field(init=False, repr=False, default=0.0)
    last_i_requested: float = field(init=False, repr=False, default=0.0)
    last_v_supply: float = field(init=False, repr=False, default=0.0)

    def __post_init__(self) -> None:
        if self.capacitance <= 0 or self.r_leak <= 0:
            raise ValueError("RailLatch: capacitance/r_leak must be > 0")
        if self.n_feedback_fets < 0:
            raise ValueError("RailLatch: n_feedback_fets 必须 ≥ 0"
                             "（0 = 反馈支路被物理断开，供阻断实验）")
        if self.clamp_mode not in ("hard", "finite", "none"):
            raise ValueError(f"RailLatch: 未知 clamp_mode {self.clamp_mode!r}")
        if self.v_rail < 0 or self.rail_r_internal < 0:
            raise ValueError("RailLatch: v_rail/rail_r_internal 必须 ≥ 0")
        self._cap = Capacitor(capacitance=self.capacitance, charge=0.0)
        # N 条**同型**电导支路（同 θ、同 g_c）——物理器件完全相同
        self._fets = [MOSFET(v_threshold=self.theta, gm=self.gm)
                      for _ in range(self.n_feedback_fets)]
        self._clamp_fet = MOSFET(v_threshold=self.clamp_threshold,
                                 gm=self.clamp_gm)
        self._rail = PowerRail(vdd=self.v_rail, r_internal=self.rail_r_internal)
        self._e_stored_0 = self._stored_energy()

    # ── 电导（契约 §二，路径 B）──
    def conductance(self, v_gate: float) -> float:
        """G(V_g) = Σ_n (gm/V_REF)·max(0, V_g−θ)，单位 S。

        器件参数取自支路 FET 实例（θ、gm），电导语义在 research 层构造，
        不调用返回 A 的母体 conduct() 冒充（契约红线）。"""
        g = 0.0
        for fet in self._fets:
            g += (fet.gm / V_REF) * max(0.0, v_gate - fet.v_threshold)
        return g

    def _feedback_current(self, v_read: float) -> tuple[float, float, float]:
        """负载线闭解（契约 Q4）：返回 (I_fb, V_supply, I_requested)。"""
        g = self.conductance(v_read)
        denom = 1.0 + g * self.rail_r_internal
        i_fb = g * self.v_rail / denom
        v_supply = self.v_rail / denom
        return i_fb, v_supply, g * self.v_rail

    def _stored_energy(self) -> float:
        return 0.5 * self._cap.charge ** 2 / self.capacitance

    # ── 物理过程 ──
    def step(self, u: float = 0.0, dt: float | None = None) -> float:
        dt = self.dt if dt is None else dt
        # 1. RC 泄漏（精确能量记账）
        e_pre = self._stored_energy()
        self._cap.leak(self.r_leak, dt)
        self._e_leak += e_pre - self._stored_energy()
        # 2. 读节点电压
        v_read = self._cap.voltage
        # 3. 反馈电流 = 电导 × 供电（负载线闭解；vdd=0 ⇒ I_fb=0 由结构保证）
        i_fb, v_supply, i_req = self._feedback_current(v_read)
        v_drawn = self._rail.draw(i_fb)             # 一致性自检通道
        if abs(v_drawn - v_supply) > 1e-12:
            raise RuntimeError(
                f"RailLatch: 负载线闭解 {v_supply!r} 与 PowerRail.draw 返回 "
                f"{v_drawn!r} 不一致 —— 供电模型被破坏")
        self.last_i_fb, self.last_v_supply = i_fb, v_supply
        self.last_i_requested = i_req
        # 4. 注入：反馈 + 输入（graded relation current）
        self._cap.inject(i_fb + self.k_in * u, dt)
        # 因果账本（契约 §四）
        self._e_emf += self.v_rail * i_fb * dt
        self._e_rail_loss += i_fb * i_fb * self.rail_r_internal * dt
        self._e_channel += (v_supply - v_read) * i_fb * dt
        self._e_node_fb += v_read * i_fb * dt
        self._e_input += v_read * self.k_in * u * dt
        # 5. 钳位（精确能量记账）
        self._apply_clamp(dt)
        return self._cap.voltage

    def _apply_clamp(self, dt: float) -> None:
        if self.clamp_mode == "none":
            return
        v = self._cap.voltage
        if v <= self.clamp_threshold:
            return
        e_pre = self._stored_energy()
        if self.clamp_mode == "hard":
            excess = v - self.clamp_threshold
            i_c = self._clamp_fet.conduct(v)
            self._e_clamp_legacy += i_c * excess * dt   # 旧 Zener 记账（对照用）
            self._cap.discharge_to(self.clamp_threshold)
        else:  # finite：真实积分 -I_clamp·dt（不强制复位）
            i_c = self._clamp_fet.conduct(v)
            self._cap.inject(-i_c, dt)
            self._e_clamp_legacy += i_c * v * dt
        self._e_clamp_exact += e_pre - self._stored_energy()

    # ── 只读观测 ──
    @property
    def state(self) -> float:
        return self._cap.voltage

    @property
    def lam(self) -> float:
        return math.exp(-self.dt / (self.r_leak * self.capacitance))

    @property
    def mu(self) -> float:
        """单步反馈增益（R_s=0 线性区）：N·gm·(vdd/V_REF)·dt/C，无量纲。

        vdd=1 时与第三轮数值一致；vdd=0 时 μ=0（断电即无反馈）。"""
        return (self.n_feedback_fets * self.gm * (self.v_rail / V_REF)
                * self.dt / self.capacitance)

    def energy_ledger(self) -> dict:
        """契约 §四 八字段 + 精确项 + 闭合残差。"""
        d_stored = self._stored_energy() - self._e_stored_0
        residual = ((self._e_node_fb + self._e_input)
                    - (d_stored + self._e_leak + self._e_clamp_exact))
        return {
            # 八字段（契约表）
            "requested_feedback_current": self.last_i_requested,
            "delivered_feedback_current": self.last_i_fb,
            "supply_voltage": self.last_v_supply,
            "supply_current": self.last_i_fb,
            "supply_energy": self._e_emf,
            "stored_capacitor_energy": self._stored_energy(),
            "clamp_dissipation": self._e_clamp_exact,
            "rail_internal_dissipation": self._e_rail_loss,
            # 附加精确项与对照项
            "channel_dissipation": self._e_channel,
            "feedback_energy": self._e_node_fb,       # = 旧公式 Σ v_read·i_fb·dt
            "input_energy": self._e_input,
            "leak_dissipation": self._e_leak,
            "clamp_dissipation_legacy": self._e_clamp_legacy,
            "delta_stored": d_stored,
            "closure_residual": residual,
            "rail_v_actual": self._rail.v_actual,
        }

    # ── 解析映射 ──
    def analytic_charge_step(self, q: float, u: float = 0.0,
                             dt: float | None = None) -> float:
        """电荷域解析映射：与 step() 的浮点运算顺序**逐位对齐**（0 容差比对）。

        第三轮教训：电压域解析（v*=λ）与实际（charge*=decay; v=charge/C）的
        舍入顺序不同，逐位一致只是轨迹运气。比对必须在电荷域做。"""
        dt = self.dt if dt is None else dt
        c_eff = max(self.capacitance, 1e-6)          # 同 Capacitor.voltage
        tau = self.r_leak * self.capacitance          # 同 Capacitor.leak
        q = q * math.exp(-dt / max(tau, 0.01))
        v_read = q / c_eff
        i_fb, _, _ = self._feedback_current(v_read)
        q = q + (i_fb + self.k_in * u) * dt
        if self.clamp_mode != "none":
            v = q / c_eff
            if v > self.clamp_threshold:
                if self.clamp_mode == "hard":
                    q = self.clamp_threshold * self.capacitance  # 同 discharge_to
                else:
                    i_c = self._clamp_fet.conduct(v)             # conduct 无状态
                    q = q + (-i_c) * dt
        return q

    def analytic_step(self, v: float, u: float = 0.0, dt: float | None = None) -> float:
        """电压域解析映射（数学等价，**不承诺逐位一致**——逐位比对用
        analytic_charge_step）。"""
        dt = self.dt if dt is None else dt
        lam = math.exp(-dt / (self.r_leak * self.capacitance))
        v_read = lam * v
        g = (self.n_feedback_fets * self.gm / V_REF) * max(0.0, v_read - self.theta)
        i_fb = g * self.v_rail / (1.0 + g * self.rail_r_internal)
        v_new = v_read + (i_fb + self.k_in * u) * dt / self.capacitance
        if self.clamp_mode == "hard" and v_new > self.clamp_threshold:
            v_new = self.clamp_threshold
        return max(0.0, v_new)

    def _require_zero_rs(self, fn: str) -> None:
        if self.rail_r_internal != 0.0:
            raise NotImplementedError(
                f"{fn}: 解析固定点公式仅覆盖 R_s=0 线性区；R_s>0 请用数值扫描")

    def fixed_points(self) -> list[dict]:
        """解析固定点（含边界/钳位支）。仅对 hard/none、R_s=0 有效。"""
        self._require_zero_rs("fixed_points")
        lam, mu = self.lam, self.mu
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

    # ── finite 钳位固定点：三函数拆分（第四轮 §十一，替代旧混名函数）──
    def finite_discrete_map(self, v: float, dt: float | None = None) -> float:
        """一次离散 map（finite 钳位、u=0）：leak → 反馈注入 → 钳位电流注入。"""
        dt = self.dt if dt is None else dt
        lam = math.exp(-dt / (self.r_leak * self.capacitance))
        v_read = lam * v
        g = (self.n_feedback_fets * self.gm / V_REF) * max(0.0, v_read - self.theta)
        i_fb = g * self.v_rail / (1.0 + g * self.rail_r_internal)
        v_new = v_read + i_fb * dt / self.capacitance
        if v_new > self.clamp_threshold:
            i_c = self.clamp_gm * (v_new - self.clamp_threshold)
            v_new -= i_c * dt / self.capacitance
        return max(0.0, v_new)

    def finite_discrete_fixed_point(self, dt: float | None = None) -> dict | None:
        """离散 map 高区固定点（依赖 dt）：λV + μ(λV−θ) − g(V−V_c) = V。

        返回 {v, map_deriv, stable}；这是**离散**量，不得再标注"连续"。"""
        self._require_zero_rs("finite_discrete_fixed_point")
        dt = self.dt if dt is None else dt
        lam = math.exp(-dt / (self.r_leak * self.capacitance))
        mu = (self.n_feedback_fets * self.gm * (self.v_rail / V_REF)
              * dt / self.capacitance)
        g = self.clamp_gm * dt / self.capacitance
        a = lam * (1 + mu) - 1 - g
        b = -mu * self.theta + g * self.clamp_threshold
        if abs(a) < 1e-18:
            return None
        v = -b / a
        if v <= max(self.theta / lam, self.clamp_threshold):
            return None
        deriv = lam * (1 + mu) - g          # 高区 map 斜率
        return {"v": v, "map_deriv": deriv, "stable": abs(deriv) < 1.0}

    def continuous_limit_fixed_point(self) -> float | None:
        """连续极限（dt→0，ODE dV/dt=0）高区固定点：

            −V/R + N·gm·(vdd/V_REF)·(V−θ) − clamp_gm·(V−V_c) = 0
        """
        self._require_zero_rs("continuous_limit_fixed_point")
        n_eff = self.n_feedback_fets * self.gm * (self.v_rail / V_REF)
        a = n_eff - self.clamp_gm - 1.0 / self.r_leak
        b = -n_eff * self.theta + self.clamp_gm * self.clamp_threshold
        if abs(a) < 1e-18:
            return None
        v = b / -a
        return v if v > max(self.theta, self.clamp_threshold) else None


if __name__ == "__main__":
    from research.A8_state_audit.candidate_config import assert_fingerprint
    print("=" * 68)
    print("RailLatch canonical 自检（解析 vs step 0 容差 + 供能因果冒烟）")
    print("=" * 68)
    assert_fingerprint(CANONICAL)          # P1-4：独立自检也打印 fingerprint
    z = RailLatch()
    q_a, ok = 0.0, True
    c_eff = max(z.capacitance, 1e-6)
    for n in range(5000):
        u = 0.4 if n < 1000 else 0.0
        q_a = z.analytic_charge_step(q_a, u)
        v_r = z.step(u)
        if v_r != q_a / c_eff:
            print(f"  MISMATCH @n={n}: real={v_r!r} analytic={q_a / c_eff!r}")
            ok = False
            break
    print(f"  5000 步逐位一致(电荷域): {ok}")
    print(f"  λ={z.lam:.9f}  μ={z.mu:.6f}  N={z.n_feedback_fets}")
    for fp in z.fixed_points():
        print(f"  FP: V*={fp['v']:.6f} {fp['type']:<16} "
              f"deriv={fp['deriv']:.6f} {fp['stability']}")
    fd = RailLatch(clamp_mode="finite")
    d = fd.finite_discrete_fixed_point()
    if d is None:
        print(f"  finite discrete FP(dt={fd.dt}): None")
    else:
        print(f"  finite discrete FP(dt={fd.dt}): v={d['v']:.9f} "
              f"map_deriv={d['map_deriv']:.4f} stable={d['stable']}")
    print(f"  continuous limit FP:          {fd.continuous_limit_fixed_point()}")
    # 供能因果冒烟：断电 ⇒ i_fb=0（结构保证）
    zc = RailLatch(v_rail=0.0)
    zc._cap.charge = 0.9 * zc.capacitance
    zc.step(0.0)
    print(f"  power-cut 冒烟: vdd=0, V=0.9 → i_fb={zc.last_i_fb!r} "
          f"(要求恒 0.0)  supply_energy={zc.energy_ledger()['supply_energy']!r}")
    ok = ok and zc.last_i_fb == 0.0
    sys.exit(0 if ok else 1)
