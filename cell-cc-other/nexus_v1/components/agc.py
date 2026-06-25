"""nexus_v1.components.agc — Automatic Gain Control (Phase 4).

行为增益自动调节: 在能量状态和DA浓度共同驱动下,
自动调节行为增益, 以打破静止死锁并优化能量利用效率.

Architecture:
    ┌─────────────────────────────────────────────────┐
    │           AutomaticGainControl                   │
    │                                                  │
    │  fill_fraction → S_energy = max(0, 0.5 - fill)   │
    │  DA_conc      → S_da     = max(0, 0.2 - DA)     │
    │                                                  │
    │  S_drive = α × S_energy + β × S_da               │
    │                                                  │
    │  S_drive → [Capacitor: τ=40k] → G_agc            │
    │                                  │               │
    │                            [MOSFET clamp]        │
    │                                  │               │
    │                             G_clamped ≤ 4.0      │
    │                                  │               │
    │                    g_eff = g_base × (1 + G_clamped) │
    └─────────────────────────────────────────────────┘

时间尺度分离:
    Phase 2 能量冻结:  瞬时     (突触 dw 门控)
    Phase 3 适格迹:    τ≈300步  (LTP 标记)
    Phase 4 AGC:       τ≈40k步  (行为增益缩放)

BIO: Hypothalamic–pituitary–adrenal (HPA) axis. Chronic
     energy deficit → cortisol → glucocorticoid receptor →
     increased locomotor drive (Sapolsky 1992).
     DA deficit → basal ganglia hypokinesia (Parkinson's).
     Both operate on slow hormonal timescales (minutes–hours).

REF: Sapolsky 1992 — "Stress, the Aging Brain, and the
     Mechanisms of Neuron Death"
REF: Mogenson 1980 — "From motivation to action"
"""

from __future__ import annotations

from dataclasses import dataclass

from .semiconductor import Capacitor, MOSFET


@dataclass
class AGCConfig:
    """Configuration for Automatic Gain Control.

    All parameters are physical constants — no semantic labels.
    """
    # ── Drive signal coefficients ──
    # α: weight of energy deficit signal S_energy
    # β: weight of DA deficit signal S_da
    # S_drive = α × max(0, energy_threshold - fill) + β × max(0, da_threshold - DA)
    alpha: float = 1.0
    beta: float = 0.5

    # ── Deficit thresholds ──
    # fill_fraction below this activates energy drive.
    # BIO: hypothalamic feeding circuit activates below ~30% glycogen
    #      (not at 50% startup — that is the normal resting level).
    # FIX-AGC-COLDSTART: lowered from 0.5 → 0.3 so AGC does not fire
    #     during normal operation (fill ≈ 0.5).  AGC now only activates
    #     on genuine hunger (fill < 0.3), matching the HPA cortisol axis.
    energy_threshold: float = 0.3
    # DA concentration below this activates DA drive.
    # BIO: tonic DA in healthy striatum ≈ 0.2 (Dreyer 2010).
    # FIX-AGC-COLDSTART: threshold lowered 0.2 → 0.05 because circuit
    #     DA is in transient (0.01-0.02) for the first ~500 steps, nowhere
    #     near the 0.2 healthy tonic level.  Treating transient-DA as
    #     pathological Parkinson's-level deficit causes false AGC saturation.
    #     At 0.05, AGC only fires on genuine DA collapse (below noise floor).
    da_threshold: float = 0.05

    # ── RC integrator time constant ──
    # τ_agc = C × R (Capacitor leak resistance).
    # 40k steps ≈ 40 seconds at dt=1ms.
    # BIO: cortisol response ~30-60 min; scaled to simulation time.
    tau_agc: float = 40000.0

    # ── Output clamp ──
    # Maximum G_agc before clamping. g_eff = g_base × (1 + G_clamped).
    # At G_max=4.0, maximum 5× gain amplification.
    # BIO: stress-induced locomotor activation has a physiological ceiling.
    g_max: float = 4.0

    # ── Cold-start warmup guard ──
    # Number of steps to suppress AGC integration at circuit start.
    # During warmup DA ≈ 0 (DA neurons need ~200 steps to activate);
    # without this guard the DA-deficit term immediately saturates AGC
    # to g_max, causing excessive random locomotion before any signal.
    # BIO: HPA axis cortisol takes minutes to respond — it does NOT
    #      fire instantaneously at birth.  The warmup models the
    #      glucocorticoid receptor occupancy latency (~200–2000 steps).
    # DESIGN: AGC is still computed (gain=1.0 returned) during warmup
    #         so all downstream reads are valid; only the integrator
    #         injection is suppressed.
    # Extended to 2000 so that stable DA and fill are established before
    # AGC begins integrating genuine deficit signals.
    warmup_steps: int = 2000


class AutomaticGainControl:
    """Phase 4: Automatic Gain Control — behavior-energy coupling.

    物理原语: Capacitor (RC leaky integrator) + MOSFET (clamp).
    Satisfies RULE S0: all computation via semiconductor primitives.

    Signal flow:
        S_drive → Capacitor.inject() → leak(R) → voltage = G_agc
        G_agc → MOSFET clamp → G_clamped = min(G_agc, g_max)
        Output: gain = 1.0 + G_clamped

    The integrator is a first-order RC lowpass:
        G_agc(t+dt) = G_agc(t) × exp(-dt/τ) + S_drive × (1 - exp(-dt/τ))

    This is mathematically equivalent to:
        Capacitor.inject(S_drive, dt) + Capacitor.leak(R, dt)
    where τ = C × R.
    """

    def __init__(self, config: AGCConfig | None = None):
        if config is None:
            config = AGCConfig()
        self.config = config

        # ── RC leaky integrator ──
        # τ = C × R. We set C=1.0, R=τ_agc so τ = 1.0 × τ_agc.
        # This gives the correct exponential decay time constant.
        self._integrator = Capacitor(capacitance=1.0)

        # ── Output clamp MOSFET ──
        # Zener-style clamp: when V > g_max, MOSFET drains excess charge.
        # BIO: physiological ceiling on stress-induced hyperactivity.
        self._clamp = MOSFET(v_threshold=config.g_max, gm=10.0)

        # ── Diagnostic state ──
        self._s_drive: float = 0.0
        self._s_energy: float = 0.0
        self._s_da: float = 0.0

    def step(self, fill_fraction: float, da_concentration: float,
             dt: float = 1.0) -> float:
        """Update AGC integrator and return effective gain.

        Args:
            fill_fraction: EnergyStore fill level [0, 1].
                1.0 = full → S_energy = 0 (no drive).
                0.0 = empty → S_energy = energy_threshold (maximum drive).
            da_concentration: Dopamine concentration [0, 1].
                ≥0.2 → S_da = 0 (no drive).
                0.0 → S_da = da_threshold (maximum DA drive).
            dt: time step.

        Returns:
            Effective gain = 1.0 + G_clamped.
        """
        cfg = self.config

        # ── Warmup guard: suppress integration during cold-start ──
        # During the first warmup_steps ticks, DA ≈ 0 (neurons not yet
        # activated).  Integrating immediately would saturate AGC to g_max
        # before any real signal exists, causing spurious hyperlocomotion.
        # We increment the tick counter and skip integration if still in
        # warmup.  The gain property returns 1.0 during this period.
        if not hasattr(self, '_tick'):
            self._tick = 0
        self._tick += 1

        # ── Compute drive signals ──
        self._s_energy = max(0.0, cfg.energy_threshold - fill_fraction)
        self._s_da = max(0.0, cfg.da_threshold - da_concentration)
        self._s_drive = cfg.alpha * self._s_energy + cfg.beta * self._s_da

        # ── RC integration (gated by warmup) ──
        # Inject drive signal as current.
        # The Capacitor accumulates charge: ΔQ = I × dt.
        # Leak with R = τ_agc gives exponential decay: τ = C × R = τ_agc.
        if self._tick > cfg.warmup_steps:
            self._integrator.inject(self._s_drive, dt)
        self._integrator.leak(cfg.tau_agc, dt)

        # ── Clamp: prevent integrator runaway ──
        # Zener clamp via Capacitor.discharge_to() — instantaneous.
        # BIO: physiological ceiling = hard saturation, not feedback loop.
        # DESIGN: The MOSFET feedback-inject pattern (gm × overshoot × dt)
        #         over-corrects at large gm, causing bang-bang oscillation.
        #         discharge_to() is the Capacitor's native reset primitive,
        #         equivalent to an ideal Zener diode (S0-compliant).
        if self._integrator.voltage > cfg.g_max:
            self._integrator.discharge_to(cfg.g_max)

        # ── Ensure non-negative ──
        # S_drive is always ≥ 0, so G_agc should never go negative,
        # but clamp for safety (numerical edge cases).
        if self._integrator.voltage < 0:
            self._integrator.discharge_to(0.0)

        return self.gain

    @property
    def g_raw(self) -> float:
        """Raw integrator voltage (before clamp)."""
        return max(0.0, self._integrator.voltage)

    @property
    def g_clamped(self) -> float:
        """Clamped gain value: min(G_agc, g_max)."""
        return min(self.g_raw, self.config.g_max)

    @property
    def gain(self) -> float:
        """Effective gain multiplier: 1.0 + G_clamped.

        Range: [1.0, 1.0 + g_max] = [1.0, 5.0].
        At 1.0: no gain boost (energy/DA sufficient).
        At 5.0: maximum gain (severe deficit).
        """
        return 1.0 + self.g_clamped

    @property
    def s_drive(self) -> float:
        """Current drive signal (diagnostic)."""
        return self._s_drive

    def summary(self) -> dict:
        """State for monitoring."""
        return {
            "g_raw": round(self.g_raw, 6),
            "g_clamped": round(self.g_clamped, 6),
            "gain": round(self.gain, 6),
            "s_drive": round(self._s_drive, 6),
            "s_energy": round(self._s_energy, 6),
            "s_da": round(self._s_da, 6),
            "tau": self.config.tau_agc,
        }
