"""relation_reference.py — D2-0 Step3：关系动力学纯数学参考模型。

TYPE:MATH — **REFERENCE 身份（反馈 §十二）**：只用于量纲检查/预期响应
形状/数值稳定性/与物理实现对照；不能也不会取得 PHYSICAL_RELATION_PROCESS
资格（若物理实现不成立而 reference 工作 ⇒ 终态 D，不降门）。

参考方程（方案 §8）：
  τ_ρ · ẋ_ρ = −x_ρ + w_a·ϑ_a(t) + w_b·ϑ_b(t)，x 截断于 [0, x_max]
"""
from __future__ import annotations

from typing import List, Sequence


def reference_trajectory(ya: Sequence[float], yb: Sequence[float],
                         dt: float, tau: float = 0.5,
                         w_a: float = 1.0, w_b: float = 1.0,
                         x_max: float = 10.0) -> List[float]:
    """欧拉积分参考轨迹（REFERENCE，非物理资格对象）。"""
    x, out = 0.0, []
    for a, b in zip(ya, yb):
        x += (-x + w_a * a + w_b * b) * dt / tau
        x = min(max(x, 0.0), x_max)
        out.append(x)
    return out
