"""GainModCircuit — 死锁二（反射增益调制）MVE adapter.

继承 VariantCircuit，叠加一个 GatedReflexArc：hunger 上下文经 DA-gated STDP 学到
增益指令，通过 MOSFET 物理乘法调制 thermo→yaw 反射的 synapse_gain。

不改母本：在 super().step() 读取反射束前，把门增益乘到反射束的 synapse_gain
（synapse_gain 在 propagate() 里每步实时读取 → 同一步内完成门控）。

方向 100% 留给 frozen thermo→yaw 反射；门是非方向性(hunger 标量) → 与方向零重叠=非冗余。
详见 死锁二_增益调制_设计方案_2026-07-08.md (v2)。
"""
from __future__ import annotations

from .variant_adapter import VariantCircuit
from ..components.gated_reflex import GatedReflexArc


class GainModCircuit(VariantCircuit):
    """TYPE:HYBRID — VariantCircuit + 上下文门控反射增益调制（死锁二 MVE）。"""

    def __init__(self):
        super().__init__()

        # hunger 上下文源（_init_energy_sensing 已建）
        hunger = getattr(self, "hypothalamus_hunger", None)
        self.gated_arc: GatedReflexArc | None = None
        if hunger is not None:
            self.gated_arc = GatedReflexArc(hunger)

        # 记录反射束基线 synapse_gain（门增益乘在其上）
        self._base_sg_left = (self.bundle_left_to_yaw.config.synapse_gain
                              if self.bundle_left_to_yaw is not None else 1.0)
        self._base_sg_right = (self.bundle_right_to_yaw.config.synapse_gain
                               if self.bundle_right_to_yaw is not None else 1.0)
        self._last_gain = 1.0

    def set_gate_frozen(self, frozen: bool):
        """E2' 差分消融：True → 冻结门学习(权重停初值)，隔离已学增量。"""
        if self.gated_arc is not None:
            self.gated_arc.frozen = frozen

    def step(self, mechanical_inputs=None, dt: float = 1.0):
        # ── 门控：在 super().step() 应用反射前设置反射束增益 ──
        # gate 读取上一步 hunger/DA（均为慢信号，一步延迟可忽略）。
        if self.gated_arc is not None:
            g = self.gated_arc.step(self.dopamine.concentration, dt)
            self._last_gain = g
            if self.bundle_left_to_yaw is not None:
                self.bundle_left_to_yaw.config.synapse_gain = self._base_sg_left * g
            if self.bundle_right_to_yaw is not None:
                self.bundle_right_to_yaw.config.synapse_gain = self._base_sg_right * g

        super().step(mechanical_inputs, dt)

    def gate_state(self) -> dict:
        if self.gated_arc is None:
            return {"gain": 1.0, "gate_act": 0.0, "m_gate": 0.0,
                    "w_hunger_gate": 0.0, "frozen": True}
        return self.gated_arc.state()
