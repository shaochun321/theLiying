"""
DecisionCircuit — 运动势垫支决策框架（T-080）

TYPE:BIO — Phase A: 影子模式（置信度积分器 + 方向观察束）

Phase A（影子模式）：
  - 3个 Capacitor 置信度积分器：监听 spinal_ccw/cw/fwd 激活
  - 4束全连接方向涌现 MVE 观察束（phasic → spinal，w=0.001，不影响主回路）
  - 所有输出仅报告，不接入马达

继承链：DecisionCircuit → VariantCircuit → HebbianCircuit

Phase B/C/D 的 FSM/误差积分/马达接入将在此类中叠加（不修改父类）。

BIO: 基底节 MSN 积分皮质脉冲序列（Mink 1996 Prog Neurobiol 50:381）
REF: 置信度积分器设计 ← 《运动势垫支决策框架实施方案》§3.1（2026-07-07）
"""

from typing import List

from .variant_adapter import VariantCircuit
from ..components.semiconductor import Capacitor
from .bundle import SynapticBundle, BundleConfig


class DecisionCircuit(VariantCircuit):
    """Phase A: confidence integrators in shadow mode.

    Motor output unchanged. Reads spinal activations → updates Capacitor
    voltages → reports via summary()['decision']. No current injection.

    Experiment: exp_T080_decision_shadow.py (5-action monitoring).
    """

    def __init__(self):
        super().__init__()

        # ── Phase A: Confidence integrators ────────────────────────────────
        # BIO: striatal MSN integrates cortical spike trains over 5-10s windows
        #      (Mink 1996 Prog Neurobiol; Plenz 2003 TINS).
        # SEMI: large Capacitor (C=5000) as leaky integrator.
        # Q3: τ_conf = C × R_CONF; initial R=5000 → τ=5000 steps.
        #     Must calibrate from single-burst half-life in Phase A experiment.
        self._R_CONF: float = 5000.0
        self._conf_ccw = Capacitor(capacitance=5000.0)
        self._conf_cw  = Capacitor(capacitance=5000.0)
        self._conf_fwd = Capacitor(capacitance=5000.0)

        # ── §9.3: 4-bundle MVE observer bundles ────────────────────────────
        # BIO: bilateral spinal connections during development (Eccles 1965 J Physiol)
        # SEMI: STDP observer (eligibility trace, DA-gated) with near-zero initial weight
        # Q3: w=0.001 → I_obs = act × 0.001 (D1 baseline ≈ 0.050×act → ratio < 2%)
        #     Negligible influence on spinal activation; pure STDP observer.
        # MONITOR: after 200k steps, L2L/R2R weight > L2R/R2L → proper lateralization.
        _obs_cfg = lambda bid: BundleConfig(
            bundle_id=bid, learning_rule='stdp',
            initial_weight=0.001, weight_max=0.1, stdp_lr=0.01,
            synapse_gain=1.0, bundle_role='feedforward',
            remodel_cost_kappa=0.0,
            use_eligibility_trace=True, eligibility_tau=300.0,
            eligibility_gain=1e-5, eligibility_ltd_rate=0.01,
        )
        # Sources write nothing (propagate not called). Only STDP traces are used.
        self._obs_L2L = SynapticBundle(
            _obs_cfg('obs_phasic_left_to_spinal_ccw'),
            [self.phasic_left], [self.spinal_ccw])
        self._obs_L2R = SynapticBundle(
            _obs_cfg('obs_phasic_left_to_spinal_cw'),
            [self.phasic_left], [self.spinal_cw])
        self._obs_R2L = SynapticBundle(
            _obs_cfg('obs_phasic_right_to_spinal_ccw'),
            [self.phasic_right], [self.spinal_ccw])
        self._obs_R2R = SynapticBundle(
            _obs_cfg('obs_phasic_right_to_spinal_cw'),
            [self.phasic_right], [self.spinal_cw])
        self._obs_bundles: List[SynapticBundle] = [
            self._obs_L2L, self._obs_L2R, self._obs_R2L, self._obs_R2R
        ]

    # ── Step override: update confidence after main circuit ─────────────────
    def step(self, mechanical_inputs, dt: float = 1.0):
        """Run main circuit, then update confidence integrators."""
        super().step(mechanical_inputs, dt)

        # Read spinal activations (updated by super().step())
        _act_ccw = max(0.0, self.spinal_ccw.activation)
        _act_cw  = max(0.0, self.spinal_cw.activation)
        _act_fwd = max(0.0, self.spinal_fwd.activation)

        # Charge confidence Capacitors (inject activation, then leak)
        # BIO: MSN charge proportional to firing rate; leak = LTP/LTD balance
        self._conf_ccw.inject(_act_ccw, dt)
        self._conf_ccw.leak(1.0 / self._R_CONF, dt)
        self._conf_cw.inject(_act_cw, dt)
        self._conf_cw.leak(1.0 / self._R_CONF, dt)
        self._conf_fwd.inject(_act_fwd, dt)
        self._conf_fwd.leak(1.0 / self._R_CONF, dt)

    # ── Learning hook: add observer STDP after parent learning ──────────────
    def _do_learning(self, dt: float):
        """Extend parent learning with §9.3 observer bundle STDP."""
        super()._do_learning(dt)

        # Observer bundles: same DA gate as D1 arc (gate_col × da_lr_mod × body_lr)
        # No sync gate (g_sync) — observers not part of motor selection
        da_lr_mod = self.dopamine.gain_factor()
        gate_col  = self.ecm_column.plasticity_gate
        fill      = self.energy_store.fill_fraction
        da_conc   = self.dopamine.concentration
        body_lr   = self.world.body.mass_inertia_factor()
        _gate = gate_col * da_lr_mod * body_lr
        for _b in self._obs_bundles:
            _b.learn(dt, plasticity_gate=_gate,
                     fill_fraction=fill, da_concentration=da_conc)
            _b.compute_xin(dt)

    # ── Census registration ─────────────────────────────────────────────────
    def get_all_bundles(self):
        """Include observer bundles in Noether/Xin census."""
        bundles = super().get_all_bundles()
        # §9.3: observer bundles visible to ledger but NOT propagated
        bundles.extend(self._obs_bundles)
        return bundles

    # ── State reporting ──────────────────────────────────────────────────────
    def summary(self) -> dict:
        d = super().summary()
        d['decision'] = {
            # Phase A: confidence integrator voltages
            'conf_ccw': self._conf_ccw.voltage,
            'conf_cw':  self._conf_cw.voltage,
            'conf_fwd': self._conf_fwd.voltage,
            # §9.3: observer bundle lateralization diagnostic
            'obs_L2L_w': self._obs_L2L.mean_weight(),  # correct lateralization
            'obs_L2R_w': self._obs_L2R.mean_weight(),  # cross connection
            'obs_R2L_w': self._obs_R2L.mean_weight(),  # cross connection
            'obs_R2R_w': self._obs_R2R.mean_weight(),  # correct lateralization
        }
        return d
