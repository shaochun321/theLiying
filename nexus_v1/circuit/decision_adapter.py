"""
DecisionCircuit — 运动势垫支决策框架（T-080）

TYPE:BIO — Phase A/B: 置信度积分器 + WTA决策 + FSM前向模型

Phase A（影子模式）：
  - 3个 Capacitor 置信度积分器：监听 yaw_ccw/cw/move_x 马达激活
  - 4束全连接方向涌现 MVE 观察束（§9.3）
  - 所有输出仅报告，不接入马达

Phase B（FSM误差收敛）：
  - 3个 WTA 决策神经元（dec_ccw/cw/fwd）+ 侧向抑制
  - 2个预测神经元（pred_dT, pred_domg）
  - 6束 FSM 束（3马达×2预测，STDP/LMS）
  - 2个误差神经元（err_dT, err_domg）
  - GABA 抑制束（误差→决策）
  - 低通平滑 Capacitor

继承链：DecisionCircuit → VariantCircuit → HebbianCircuit

BIO: 基底节 MSN 积分皮质脉冲序列（Mink 1996 Prog Neurobiol 50:381）
     小脑 Purkinje 前向模型（Wolpert & Kawato 1998 Neural Netw 11:1317）
REF: 《运动势垫支决策框架实施方案》§3.1-3.5（2026-07-07）
"""

from typing import List

from .variant_adapter import VariantCircuit
from ..components.semiconductor import Capacitor
from ..components.neuron import Neuron, NeuronConfig, ChannelConfig
from .bundle import SynapticBundle, BundleConfig


def _frozen_inh(bid: str, w: float = 0.5) -> BundleConfig:
    """Frozen inhibitory bundle config (synapse_gain = -1.0)."""
    return BundleConfig(
        bundle_id=bid, learning_rule='frozen',
        initial_weight=w, weight_max=w, stdp_lr=0.0,
        synapse_gain=-1.0, bundle_role='feedback',
        remodel_cost_kappa=0.0,
    )


def _frozen_exc(bid: str, w: float = 1.0) -> BundleConfig:
    """Frozen excitatory bundle config (synapse_gain = +1.0)."""
    return BundleConfig(
        bundle_id=bid, learning_rule='frozen',
        initial_weight=w, weight_max=w, stdp_lr=0.0,
        synapse_gain=1.0, bundle_role='feedforward',
        remodel_cost_kappa=0.0,
    )


class DecisionCircuit(VariantCircuit):
    """Phase A/B: confidence integrators + WTA + FSM forward model.

    Phase A (shadow): confidence Capacitors monitor motor output,
    §9.3 MVE observer bundles track lateralization. No motor injection.

    Phase B (FSM): prediction neurons learn to predict sensory outcomes
    from motor efference copies. Error neurons inhibit decision neurons
    (GABA). WTA competition selects the best action.

    Motor connection added in Phase C (_propagate_bundles override).
    """

    def __init__(self):
        super().__init__()

        # ══════════════════════════════════════════════════════════════════
        # Phase A: Confidence integrators
        # ══════════════════════════════════════════════════════════════════
        # BIO: striatal MSN integrates motor cortex spike trains over 5-10s
        #      windows (Mink 1996; Plenz 2003 TINS).
        # SEMI: large Capacitor as leaky integrator.
        # Q3: Capacitor.leak(R, dt) clamps R≥0.01, τ=R×C.
        #     To get τ=5000: R_leak = τ/C = 5000/5000 = 1.0. Call leak(1.0, dt).
        #     V_ss ≈ motor_activation × 1.0 (>>0.2 threshold). Measured τ≈50 when
        #     calling leak(1/5000): due to R clamp (0.0002<0.01→0.01, τ=50 steps).
        self._R_CONF: float = 1.0   # R for confidence integrators; τ = R × C = 5000
        self._conf_ccw = Capacitor(capacitance=5000.0)
        self._conf_cw  = Capacitor(capacitance=5000.0)
        self._conf_fwd = Capacitor(capacitance=5000.0)

        # ── §9.3: 4-bundle MVE observer bundles ──────────────────────────
        # BIO: bilateral spinal connections during development (Eccles 1965)
        # Q3: w=0.001 → I_obs < 2% of D1 contribution (negligible influence)
        # MONITOR: after 200k steps, L2L/R2R > L2R/R2L → correct lateralization
        _obs_cfg = lambda bid: BundleConfig(
            bundle_id=bid, learning_rule='stdp',
            initial_weight=0.001, weight_max=0.1, stdp_lr=0.01,
            synapse_gain=1.0, bundle_role='feedforward',
            remodel_cost_kappa=0.0,
            use_eligibility_trace=True, eligibility_tau=300.0,
            eligibility_gain=1e-5, eligibility_ltd_rate=0.01,
        )
        self._obs_L2L = SynapticBundle(_obs_cfg('obs_phasic_left_to_spinal_ccw'),  [self.phasic_left],  [self.spinal_ccw])
        self._obs_L2R = SynapticBundle(_obs_cfg('obs_phasic_left_to_spinal_cw'),   [self.phasic_left],  [self.spinal_cw])
        self._obs_R2L = SynapticBundle(_obs_cfg('obs_phasic_right_to_spinal_ccw'), [self.phasic_right], [self.spinal_ccw])
        self._obs_R2R = SynapticBundle(_obs_cfg('obs_phasic_right_to_spinal_cw'),  [self.phasic_right], [self.spinal_cw])
        self._obs_bundles: List[SynapticBundle] = [
            self._obs_L2L, self._obs_L2R, self._obs_R2L, self._obs_R2R
        ]

        # ══════════════════════════════════════════════════════════════════
        # Phase B: WTA Decision neurons
        # ══════════════════════════════════════════════════════════════════
        # BIO: SNr/GPi thalamic gate neurons — disinhibition allows action
        #      (DeLong 1990 Trends Neurosci; Mink 1996).
        # SEMI: Capacitor(C=1) + MOSFET channel (Vth=0.01, gm=1.0)
        # Q3: τ_dec = C × r_leak = 1.0 × 50.0 = 50 steps (sustained burst needed)
        def _dec_cfg(nid: str) -> NeuronConfig:
            return NeuronConfig(
                neuron_id=nid, capacitance=1.0, r_leak=50.0, region=0x01,
                spiking=False,
                channels=[ChannelConfig(name=nid, v_threshold=0.01, gm=1.0)])

        self.dec_ccw = Neuron(_dec_cfg('dec_ccw'))
        self.dec_cw  = Neuron(_dec_cfg('dec_cw'))
        self.dec_fwd = Neuron(_dec_cfg('dec_fwd'))

        # Lateral (WTA) inhibition between decision neurons
        # BIO: Ia reciprocal inhibition — winner suppresses competitors
        #      (Eccles 1965 J Physiol 150:43)
        # Q3: w_lateral=0.5, sg=-1.0 → winner (act≈0.3) inhibits by 0.15 >
        #     loser decay rate (V/r_leak ≈ 0.01) → WTA separation in ~15 steps
        self._b_dec_ccw_to_cw  = SynapticBundle(_frozen_inh('dec_ccw_inh_cw'),  [self.dec_ccw], [self.dec_cw])
        self._b_dec_cw_to_ccw  = SynapticBundle(_frozen_inh('dec_cw_inh_ccw'),  [self.dec_cw],  [self.dec_ccw])
        self._b_dec_fwd_to_ccw = SynapticBundle(_frozen_inh('dec_fwd_inh_ccw'), [self.dec_fwd], [self.dec_ccw])
        self._b_dec_fwd_to_cw  = SynapticBundle(_frozen_inh('dec_fwd_inh_cw'),  [self.dec_fwd], [self.dec_cw])
        self._dec_lateral: List[SynapticBundle] = [
            self._b_dec_ccw_to_cw, self._b_dec_cw_to_ccw,
            self._b_dec_fwd_to_ccw, self._b_dec_fwd_to_cw,
        ]

        # Phase B: FSM prediction neurons
        # BIO: cerebellar granule→Purkinje forward model (Wolpert & Kawato 1998)
        # SEMI: Capacitor leaky integrator (τ=100 steps) for efference copy
        # Q3: C=1.0, r_leak=100.0 → τ=100 steps (≈100ms motor-sensory delay)
        def _pred_cfg(nid: str) -> NeuronConfig:
            return NeuronConfig(
                neuron_id=nid, capacitance=1.0, r_leak=100.0, region=0x01,
                spiking=False,
                channels=[ChannelConfig(name=nid, v_threshold=0.001, gm=1.0)])

        self.pred_dT   = Neuron(_pred_cfg('pred_dT'))    # predicted ΔT from action
        self.pred_domg = Neuron(_pred_cfg('pred_domg'))  # predicted Δω from action

        # 6 FSM bundles: 3 motor efference copies × 2 prediction targets
        # BIO: mossy fiber → parallel fiber → Purkinje cell connections
        #      (Eccles 1967 The Cerebellum as a Neuronal Machine)
        # Q3: w0=0.001 (near-zero start); stdp_lr=1e-5 (slow, converges ~50k steps)
        #     eligibility_tau=500 steps (captures motor-sensory delay)
        _fsm_lr = 1e-5
        def _fsm_cfg(bid: str) -> BundleConfig:
            return BundleConfig(
                bundle_id=bid, learning_rule='stdp',
                initial_weight=0.001, weight_max=1.0, stdp_lr=_fsm_lr,
                # Q3: Memristor r_max=10 → min conductance = 1/10 = 0.1.
                # With 2 yaw neurons at act≈2.5 and sg=1.0: min _i_pred = 0.5,
                # pred_dT ≈ 0.58 > dT_actual ≈ 0.42 → systematic POSITIVE error → B2 FAIL.
                # Fix sg=0.1: min _i_pred = 0.05, pred_dT ≈ 0.22 < 0.42 → err negative.
                # FSM can still learn upward via DA-gated LTP until pred ≈ actual.
                synapse_gain=0.1, bundle_role='feedforward',
                remodel_cost_kappa=0.0,
                use_eligibility_trace=True, eligibility_tau=500.0,
                eligibility_gain=1e-5, eligibility_ltd_rate=0.01,
            )

        _move_x = self.motor_neurons['move_x']
        self._b_fsm_ccw_dT   = SynapticBundle(_fsm_cfg('fsm_yaw_ccw_to_pred_dT'),   [self.yaw_ccw_neuron], [self.pred_dT])
        self._b_fsm_cw_dT    = SynapticBundle(_fsm_cfg('fsm_yaw_cw_to_pred_dT'),    [self.yaw_cw_neuron],  [self.pred_dT])
        self._b_fsm_fwd_dT   = SynapticBundle(_fsm_cfg('fsm_move_x_to_pred_dT'),    [_move_x],             [self.pred_dT])
        self._b_fsm_ccw_domg = SynapticBundle(_fsm_cfg('fsm_yaw_ccw_to_pred_domg'), [self.yaw_ccw_neuron], [self.pred_domg])
        self._b_fsm_cw_domg  = SynapticBundle(_fsm_cfg('fsm_yaw_cw_to_pred_domg'),  [self.yaw_cw_neuron],  [self.pred_domg])
        self._b_fsm_fwd_domg = SynapticBundle(_fsm_cfg('fsm_move_x_to_pred_domg'),  [_move_x],             [self.pred_domg])
        self._fsm_dT_bundles:   List[SynapticBundle] = [self._b_fsm_ccw_dT,   self._b_fsm_cw_dT,   self._b_fsm_fwd_dT]
        self._fsm_domg_bundles: List[SynapticBundle] = [self._b_fsm_ccw_domg, self._b_fsm_cw_domg, self._b_fsm_fwd_domg]
        self._fsm_bundles: List[SynapticBundle] = self._fsm_dT_bundles + self._fsm_domg_bundles

        # Phase B: Error neurons
        # BIO: climbing fiber → Purkinje cell (prediction error; Bhaskara 2011)
        #      Fires when ŷ_pred > y_actual (overestimate → wrong action)
        # SEMI: Capacitor(C=1) + MOSFET(Vth=0.05 = 3σ noise floor)
        # Q3: C=1.0, r_leak=20.0 → τ=20 steps (quick error response)
        #     Vth=0.05 calibrated conservatively; update after Phase A quiet measurement
        def _err_cfg(nid: str) -> NeuronConfig:
            return NeuronConfig(
                neuron_id=nid, capacitance=1.0, r_leak=20.0, region=0x01,
                spiking=False,
                channels=[ChannelConfig(name=nid, v_threshold=0.05, gm=0.5)])

        self.err_dT   = Neuron(_err_cfg('err_dT'))
        self.err_domg = Neuron(_err_cfg('err_domg'))

        # pred → error (excitatory, KCL positive side)
        self._b_pred_dT_to_err   = SynapticBundle(_frozen_exc('pred_dT_to_err_dT'),     [self.pred_dT],   [self.err_dT])
        self._b_pred_domg_to_err = SynapticBundle(_frozen_exc('pred_domg_to_err_domg'), [self.pred_domg], [self.err_domg])

        # GABA inhibition: error → decision (inhibitory)
        # BIO: SNr GABA→thalamus (error suppresses wrong-direction action)
        # Q3: w=1.0, sg=-1.0 → full inhibition when error fires (error act≈0.1 → I_inh=-0.1)
        self._b_gaba_dT_ccw  = SynapticBundle(_frozen_inh('gaba_err_dT_to_dec_ccw',  1.0), [self.err_dT],   [self.dec_ccw])
        self._b_gaba_dT_cw   = SynapticBundle(_frozen_inh('gaba_err_dT_to_dec_cw',   1.0), [self.err_dT],   [self.dec_cw])
        self._b_gaba_dT_fwd  = SynapticBundle(_frozen_inh('gaba_err_dT_to_dec_fwd',  1.0), [self.err_dT],   [self.dec_fwd])
        self._b_gaba_domg_ccw = SynapticBundle(_frozen_inh('gaba_err_domg_to_dec_ccw', 1.0), [self.err_domg], [self.dec_ccw])
        self._b_gaba_domg_cw  = SynapticBundle(_frozen_inh('gaba_err_domg_to_dec_cw',  1.0), [self.err_domg], [self.dec_cw])
        self._b_gaba_domg_fwd = SynapticBundle(_frozen_inh('gaba_err_domg_to_dec_fwd', 1.0), [self.err_domg], [self.dec_fwd])
        self._gaba_bundles: List[SynapticBundle] = [
            self._b_gaba_dT_ccw,  self._b_gaba_dT_cw,  self._b_gaba_dT_fwd,
            self._b_gaba_domg_ccw, self._b_gaba_domg_cw, self._b_gaba_domg_fwd,
        ]

        # Low-pass smooth Capacitors (Phase C output buffer)
        # BIO: deep cerebellar nucleus → brainstem RC filter (Eccles 1967)
        # Q3: τ_smooth = R_SMOOTH / 1 = 500 steps > muscle τ_mech ≈ 100 steps
        self._smooth_ccw = Capacitor(capacitance=500.0)
        self._smooth_cw  = Capacitor(capacitance=500.0)
        self._smooth_fwd = Capacitor(capacitance=500.0)
        self._R_SMOOTH: float = 1.0   # R for smooth Capacitors; τ = R × C = 500

        # Confidence → decision drive gain
        # Q3: conf_cw≈1.1, err_sum≈1.7 (Phase A level), W_GABA=0.005
        #     Need: conf×G - W_GABA×err > Vth/r_leak = 0.01/50 = 0.0002
        #     1.1×0.01 - 0.005×1.7 = 0.011 - 0.0085 = 0.0025 > 0.0002 ✓
        #     → dec_cw active (V_ss=0.125) at Phase A residual error level.
        #     W_GABA=0.005 keeps GABA as soft gate (not hard suppressor).
        self._G_CONF: float = 0.01

    # ── Step override ────────────────────────────────────────────────────────
    def step(self, mechanical_inputs, dt: float = 1.0):
        """Run main circuit, then update all decision sub-circuits."""
        super().step(mechanical_inputs, dt)

        # ── Phase A: Confidence integrators (monitor motor output) ──────────
        # BIO: striatal MSN monitors motor cortex (layer 5) output (Mink 1996)
        _act_ccw = max(0.0, self.yaw_ccw_neuron.activation)
        _act_cw  = max(0.0, self.yaw_cw_neuron.activation)
        _act_fwd = max(0.0, self.motor_neurons['move_x'].activation)

        self._conf_ccw.inject(_act_ccw, dt);  self._conf_ccw.leak(self._R_CONF, dt)
        self._conf_cw.inject(_act_cw, dt);    self._conf_cw.leak(self._R_CONF, dt)
        self._conf_fwd.inject(_act_fwd, dt);  self._conf_fwd.leak(self._R_CONF, dt)

        # ── Phase B: FSM forward model ──────────────────────────────────────
        # Step 1: propagate efference copy into prediction neurons
        _i_pred_dT = sum(
            (b.propagate() or [0.0])[0] for b in self._fsm_dT_bundles)
        _i_pred_domg = sum(
            (b.propagate() or [0.0])[0] for b in self._fsm_domg_bundles)
        self.pred_dT.step(_i_pred_dT, dt)
        self.pred_domg.step(_i_pred_domg, dt)

        # Step 2: compute actual sensory signals (KCL reference)
        # ΔT_actual: ALL thermal column activations (mid + top + bot rings).
        # Using only therm_top_* was wrong: at X-axis approach (source in +X),
        # therm_top_* = 0 (Z-axis sensors) → err = pred - 0 = pred → always fires.
        # Full ring average gives a non-zero reference for any source direction.
        _all_therm_keys = [
            'therm_front', 'therm_back', 'therm_left', 'therm_right',
            'therm_top_front', 'therm_top_back', 'therm_top_left', 'therm_top_right',
            'therm_bot_front', 'therm_bot_back', 'therm_bot_left', 'therm_bot_right',
        ]
        _therm_active = [k for k in _all_therm_keys if k in self.column_neurons]
        _dT_actual = (sum(self.column_neurons[k].activation for k in _therm_active)
                      / max(len(_therm_active), 1))
        # Δω_actual: yaw motor asymmetry (rotation proxy)
        _domg_actual = abs(_act_ccw - _act_cw)

        # Step 3: error = pred_activation - actual (direct, no double-propagate)
        # _b_pred_*_to_err not in get_all_bundles() → no auto-propagation
        _i_err_dT   = self.pred_dT.activation   - _dT_actual
        _i_err_domg = self.pred_domg.activation - _domg_actual
        self.err_dT.step(_i_err_dT, dt)
        self.err_domg.step(_i_err_domg, dt)

        # Step 4: WTA decision neurons
        # GABA/lateral bundles not in get_all_bundles() → compute directly from activations.
        # GABA: w=1.0, sg=-1.0 → I = -err.activation
        _W_GABA = 0.005  # soft gate: GABA suppresses proportionally but doesn't hard-clamp
        _W_LAT  = 0.5   # matches _frozen_inh(w=0.5)
        # BIO: GABA fires only for POSITIVE prediction error (overestimate → wrong action).
        # Negative error (pred < actual, body in good environment) must not excite dec via sign-reversal.
        # err_dT is multi-channel → activation = vm (can be negative); clip before use.
        _err_sum = max(0.0, self.err_dT.activation) + max(0.0, self.err_domg.activation)
        _i_gaba_any = -_W_GABA * _err_sum   # same for all dec neurons
        # Lateral inhibition: only ACTIVE (positive) competitors suppress.
        # BIO: Ia reciprocal inhibition only fires when antagonist is active;
        # a deeply hyperpolarized neuron cannot excite via sign-reversal.
        _i_lat_ccw = -_W_LAT * (max(0.0, self.dec_cw.activation) + max(0.0, self.dec_fwd.activation))
        _i_lat_cw  = -_W_LAT * (max(0.0, self.dec_ccw.activation) + max(0.0, self.dec_fwd.activation))
        _i_exc_ccw = self._conf_ccw.voltage * self._G_CONF
        _i_exc_cw  = self._conf_cw.voltage  * self._G_CONF
        _i_exc_fwd = self._conf_fwd.voltage  * self._G_CONF
        self.dec_ccw.step(_i_exc_ccw + _i_gaba_any + _i_lat_ccw, dt)
        self.dec_cw.step( _i_exc_cw  + _i_gaba_any + _i_lat_cw,  dt)
        self.dec_fwd.step(_i_exc_fwd + _i_gaba_any,               dt)  # no lateral for fwd

        # Step 5: smooth Capacitor output
        self._smooth_ccw.inject(max(0.0, self.dec_ccw.activation), dt)
        self._smooth_ccw.leak(self._R_SMOOTH, dt)
        self._smooth_cw.inject(max(0.0, self.dec_cw.activation), dt)
        self._smooth_cw.leak(self._R_SMOOTH, dt)
        self._smooth_fwd.inject(max(0.0, self.dec_fwd.activation), dt)
        self._smooth_fwd.leak(self._R_SMOOTH, dt)

        # ── Phase C: Motor connection ────────────────────────────────────
        # BIO: BG/SNr disinhibition → thalamus → motor cortex L5 →
        #      spinal pattern generators (Mink 1996 Prog Neurobiol 50:381).
        # SEMI: smooth Capacitor (τ=500 steps) acts as RC filter on dec output.
        #       inject() adds to membrane voltage; activation computed next step.
        # Q3: smooth_ccw ≈ 0.2 at steady WTA, _DECISION_GAIN=0.1 →
        #     I_inject = 0.02 per step. yaw_ccw natural activation ≈ 2.0 →
        #     Phase C contribution ≈ 1% — modulates direction without hijacking.
        #     Too large → motor saturation + loss of thermal feedback; too small → no effect.
        _DECISION_GAIN = 0.1
        self.yaw_ccw_neuron._membrane.inject(self._smooth_ccw.voltage * _DECISION_GAIN, dt)
        self.yaw_cw_neuron._membrane.inject(self._smooth_cw.voltage * _DECISION_GAIN, dt)
        self.motor_neurons['move_x']._membrane.inject(self._smooth_fwd.voltage * _DECISION_GAIN, dt)

    # ── Learning hook ────────────────────────────────────────────────────────
    def _do_learning(self, dt: float):
        """Extend parent learning with §9.3 observer STDP + FSM learning."""
        super()._do_learning(dt)

        da_lr_mod = self.dopamine.gain_factor()
        gate_col  = self.ecm_column.plasticity_gate
        fill      = self.energy_store.fill_fraction
        da_conc   = self.dopamine.concentration
        body_lr   = self.world.body.mass_inertia_factor()
        _gate = gate_col * da_lr_mod * body_lr

        # §9.3 observer bundles (DA-gated STDP)
        for _b in self._obs_bundles:
            _b.learn(dt, plasticity_gate=_gate,
                     fill_fraction=fill, da_concentration=da_conc)
            _b.compute_xin(dt)

        # FSM bundles: eligibility-trace STDP, DA-gated
        # LMS-like: error provides teaching signal via da_concentration
        # Prediction error → lower DA → LTD on active motor-prediction connections
        for _b in self._fsm_bundles:
            _b.learn(dt, plasticity_gate=_gate,
                     fill_fraction=fill, da_concentration=da_conc)
            _b.compute_xin(dt)

    # ── Census registration ──────────────────────────────────────────────────
    def get_all_bundles(self):
        """Include Phase A obs bundles in Noether/Xin census.

        Phase B bundles (FSM, pred→err, GABA, lateral) are NOT included here
        because their targets are Phase B neurons (pred_dT, err_dT, dec_*)
        which are stepped manually in step(). Including them would cause
        double-stepping: apply_to_targets() calls tgt.step() AND our override
        also calls tgt.step(). obs_bundles target spinal_ccw/cw (main circuit
        neurons stepped by the main bundle graph) so they're correctly included.
        """
        bundles = super().get_all_bundles()
        bundles.extend(self._obs_bundles)
        # Phase B bundles excluded from auto-propagation; learning called in _do_learning()
        return bundles

    # ── State reporting ──────────────────────────────────────────────────────
    def summary(self) -> dict:
        d = super().summary()
        d['decision'] = {
            # Phase A: confidence Capacitor voltages
            'conf_ccw': self._conf_ccw.voltage,
            'conf_cw':  self._conf_cw.voltage,
            'conf_fwd': self._conf_fwd.voltage,
            # §9.3: MVE observer lateralization
            'obs_L2L_w': self._obs_L2L.mean_weight(),
            'obs_L2R_w': self._obs_L2R.mean_weight(),
            'obs_R2L_w': self._obs_R2L.mean_weight(),
            'obs_R2R_w': self._obs_R2R.mean_weight(),
            # Phase B: WTA decision activations
            'dec_ccw': self.dec_ccw.activation,
            'dec_cw':  self.dec_cw.activation,
            'dec_fwd': self.dec_fwd.activation,
            'smooth_ccw': self._smooth_ccw.voltage,
            'smooth_cw':  self._smooth_cw.voltage,
            'smooth_fwd': self._smooth_fwd.voltage,
            # Phase B: prediction and error
            'pred_dT':    self.pred_dT.activation,
            'pred_domg':  self.pred_domg.activation,
            'err_dT':     self.err_dT.activation,
            'err_domg':   self.err_domg.activation,
        }
        return d
