"""reconstructor.py — 𝒜⁺ 父层同类重构器（§A.2 的最强攻击）。

TYPE:INFRA（research/ 隔离层）

## 判据（方案修订稿 §A.2）

𝒜⁺ = 对完整 relation current 序列 r(t) 施加「真实父层同型物理栈」可得的
     全部物理量的有限次复合。本模块实现该复合族的**最小二乘最优拟合**：

    Ẑ(t) = argmin_{φ ∈ span(基函数)} ‖ Z_actual(t) − φ(t) ‖

基函数 = 𝒜⁺ 的显式生成元（§A.1 实测构成）：
    1. H_τ 线性指数叠加（history_kernel 行为，τ=600）
    2. 不同 τ 的线性 RC（τ=200/1000）——覆盖"换 τ"的情况 B
    3. 多阶 RC 线性组合——覆盖"两个 H_τ"的情况 A
    4. 上述量的静态非线性（硬截断、平方、乘积、饱和钳位）——覆盖情况 C/E/F

残差：R_Z(t) = Z_actual(t) − Ẑ(t)，报告相对范数与绝对范数。
判定见 §E：R_Z 显著超出 C-null-3 地板 ⟹ A8_CANDIDATE。

## 为什么这是最强攻击（而不是拆台）

重构器拿到的是**完整 r(t)**（原方案 §6 授权），并做最优线性拟合，
比"实例化一个父层物理栈"更强（后者只有一组固定参数）。
若候选仍不可重构，则该结论比原方案要求的更强。
"""

from __future__ import annotations

import math


def _rc_trace(r_series: list[float], tau_steps: float, dt: float,
              q: float = 1.0, cap: float = 1.0) -> list[float]:
    """单极点线性 RC 对 r(t) 的响应（H_τ 行为）。"""
    r_leak = tau_steps * dt / cap
    v = 0.0
    out = []
    for r in r_series:
        v *= math.exp(-dt / max(tau_steps * dt, 1e-9))
        if r > 0.0:
            v += q * r * dt / cap
        out.append(v)
    return out


def _saturate(x: float, lo: float, hi: float) -> float:
    return lo if x < lo else (hi if x > hi else x)


def build_basis(r_series: list[float], dt: float,
                taus: tuple[float, ...] = (200.0, 600.0, 1000.0),
                clamp: float = 1.0) -> list[list[float]]:
    """构造 𝒜⁺ 的显式基函数集（§A.1 的生成元封闭性）。"""
    basis: list[list[float]] = []

    traces = {}
    for tau in taus:
        tr = _rc_trace(r_series, tau, dt)
        traces[tau] = tr
        basis.append(tr)                                   # 线性 RC（含 H_τ）

    tr_h = traces[600.0]
    tr_slow = traces[1000.0]

    basis.append([x * x for x in tr_h])                    # 静态非线性：平方
    basis.append([_saturate(x, 0.0, clamp) for x in tr_h])  # 硬截断/Zener
    basis.append([_saturate(x, 0.0, 0.05) for x in tr_h])   # 更强的截断
    basis.append([a * b for a, b in zip(tr_h, tr_slow)])    # 乘积（NMDA 型）
    basis.append([a + b for a, b in zip(tr_h, tr_slow)])    # 线性叠加（情况 A）

    return basis


def reconstruct(z_actual: list[float], r_series: list[float], dt: float,
                taus: tuple[float, ...] = (200.0, 600.0, 1000.0),
                clamp: float = 1.0) -> dict:
    """最优拟合 Ẑ(t)（最小二乘）并返回残差统计。

    返回 dict：
      z_hat       拟合轨迹
      residual    ‖Z − Ẑ‖₂
      rel         residual / ‖Z‖₂
      abs_max     max|Z − Ẑ|
      scale       ‖Z‖₂（候选自身尺度）
    """
    basis = build_basis(r_series, dt, taus=taus, clamp=clamp)
    n = len(z_actual)
    if n == 0:
        return {"z_hat": [], "residual": 0.0, "rel": 0.0, "abs_max": 0.0,
                "scale": 0.0}

    # 最小二乘：解 (BᵀB) c = Bᵀz，B 为 n×k
    k = len(basis)
    BtB = [[0.0] * k for _ in range(k)]
    Btz = [0.0] * k
    for i in range(n):
        z_i = z_actual[i]
        for a in range(k):
            ba = basis[a][i]
            Btz[a] += ba * z_i
            for b in range(a, k):
                BtB[a][b] += ba * basis[b][i]
    for a in range(k):
        for b in range(a):
            BtB[a][b] = BtB[b][a]

    c = _solve(BtB, Btz)

    z_hat = []
    for i in range(n):
        z_hat.append(sum(c[a] * basis[a][i] for a in range(k)))

    res = [z_actual[i] - z_hat[i] for i in range(n)]
    residual = math.sqrt(sum(x * x for x in res))
    scale = math.sqrt(sum(x * x for x in z_actual))
    abs_max = max((abs(x) for x in res), default=0.0)
    return {
        "z_hat": z_hat,
        "residual": residual,
        "rel": residual / scale if scale > 1e-15 else 0.0,
        "abs_max": abs_max,
        "scale": scale,
    }


def _solve(A: list[list[float]], b: list[float]) -> list[float]:
    """高斯消元（带部分主元），解 A c = b。"""
    n = len(b)
    M = [row[:] + [b[i]] for i, row in enumerate(A)]
    for col in range(n):
        piv = max(range(col, n), key=lambda r: abs(M[r][col]))
        if abs(M[piv][col]) < 1e-18:
            continue
        M[col], M[piv] = M[piv], M[col]
        pv = M[col][col]
        for r in range(col + 1, n):
            f = M[r][col] / pv
            if f == 0.0:
                continue
            for cc in range(col, n + 1):
                M[r][cc] -= f * M[col][cc]
    c = [0.0] * n
    for r in range(n - 1, -1, -1):
        s = M[r][n] - sum(M[r][cc] * c[cc] for cc in range(r + 1, n))
        c[r] = s / M[r][r] if abs(M[r][r]) > 1e-18 else 0.0
    return c
