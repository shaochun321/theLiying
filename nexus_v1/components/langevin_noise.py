"""nexus_v1.components.langevin_noise — LangevinNoise (Ornstein-Uhlenbeck thermal noise).

TYPE:HYBRID — Physical thermal fluctuation as a first-class component.
Parallel to VitalOscillator: VitalOscillator injects into Motor (efferent),
LangevinNoise injects into Otolith afferent path (afferent).

Design Derivation:
    BIO: Thermal fluctuations of endolymph → vestibular hair cell membrane
         displacement. Johnson-Nyquist thermal noise (kT ≈ 4.1 pN·nm at 37°C).
         Hair cells are immersed in ECM (extracellular matrix / endolymph).
         Therefore T_bath = ECM.temperature — not external air temperature.
    PHYS: Ornstein-Uhlenbeck (OU) process — colored noise (finite bandwidth).
          White noise (infinite bandwidth) is unphysical for a biological sensor.
          OU provides the correct finite-correlation-time approximation.
    REF: Johnson 1928 / Nyquist 1928 — thermal noise in resistors
    REF: Uhlenbeck & Ornstein 1930 — theory of Brownian motion
    REF: Berg & Brown 1972 — klinokinesis in chemotaxis
    REF: 步骤2统一物理架构方案 §二 ECM热浴; §三 涨落耗散定理

Noise Calibration (Stochastic Resonance):
    From Kramers escape rate theory, optimal SNR occurs at:
        σ* ≈ θ_sys / sqrt(2)
    With vestibular afferent threshold θ_sys ≈ 0.1:
        σ* ≈ 0.07
    Anchored by Fluctuation-Dissipation Theorem:
        σ_target = σ₀ × sqrt(T_bath)
    At T_bath ≈ 0.01 (ECM temperature normalized units):
        σ₀ = 0.07 / sqrt(0.01) = 0.70
    REF: 皮层除颤与热力学大一统方案 §2.1-§2.2

Energy Accounting:
    Langevin noise is powered by the ECM thermal bath — NOT EnergyStore (ATP).
    The noise is the ambient thermal background, free to the organism.
    Mechanical transduction cost is already included in `basal_drain`.
    This component does NOT call EnergyStore.withdraw().

OU Exact Discretization (variance-preserving):
    η(t+Δt) = η(t) × exp(-Δt/τ) + N(0, σ₀² × T_bath × (1 - exp(-2Δt/τ)))
    This guarantees exact variance preservation regardless of Δt.
    REF: 皮层除颤与热力学大一统方案 §2.3
"""

from __future__ import annotations

import math
import random
from dataclasses import dataclass
from typing import List, TYPE_CHECKING

if TYPE_CHECKING:
    from .ecm import ExtracellularMatrix


@dataclass
class LangevinConfig:
    """Configuration for the Langevin thermal noise source.

    σ₀ and τ are physically grounded — not free parameters.
    """
    # Base noise amplitude: σ_target = σ₀ × sqrt(T_bath)
    # Anchored by: σ* ≈ θ_sys/sqrt(2) ≈ 0.07 at T_bath=0.01
    # CALIBRATE: σ₀=0.70 derived from FDT + stochastic resonance optimum.
    #            Pending EXP-langevin validation of exact σ* for this system.
    sigma0: float = 0.70

    # OU correlation time (s) — finite bandwidth, avoids white noise pathology.
    # BIO: hair cell membrane time constant τ_hair ≈ 0.1-1.0 s
    # Chosen as 0.5 s to sit within the hair cell integration window.
    tau: float = 0.5

    # Number of noise axes (one per otolith axis: x, y, z)
    n_axes: int = 3


class LangevinNoise:
    """Ornstein-Uhlenbeck thermal noise source for vestibular afferent path.

    Provides physical thermal fluctuations driven by ECM temperature.
    Injected at the sensor (afferent) side — not at Motor (efferent).

    The brain cannot distinguish this thermal noise from real body motion.
    Macro and micro signals are absolutely isomorphic at the synapse:
        O_k = a_k_body + η_k

    Shadow predictor learns the low-frequency macro component but cannot
    predict high-frequency noise → persistent residual → basal Xin tension.

    Usage:
        noise = LangevinNoise()
        eta = noise.step(ecm_vestibular, dt)
        # eta = [η_x, η_y, η_z] in acceleration units
        # Add to mechanical_inputs before OTOLITH_GAIN scaling
    """

    def __init__(self, config: LangevinConfig | None = None):
        if config is None:
            config = LangevinConfig()
        self.config = config
        # OU state: η_k for each axis
        self._eta: List[float] = [0.0] * config.n_axes
        self._step_count: int = 0

    def step(self, ecm_vestibular: 'ExtracellularMatrix', dt: float = 0.001) -> List[float]:
        """Advance OU process by one time step.

        Uses exact variance-preserving discretization:
            η(t+Δt) = η(t) × exp(-Δt/τ) + N(0, σ₀² × T_bath × (1 - exp(-2Δt/τ)))

        Args:
            ecm_vestibular: vestibular ECM — provides T_bath (endolymph temperature)
            dt: time step (seconds)

        Returns:
            List of [η_x, η_y, η_z] noise values in acceleration units.
            Add directly to body acceleration before otolith gain scaling.
        """
        self._step_count += 1
        T_bath = max(ecm_vestibular.temperature, 1e-6)

        # Exact OU discretization (Itô calculus, variance-preserving)
        decay = math.exp(-dt / self.config.tau)
        # Noise variance: σ₀² × T_bath × (1 - e^(-2Δt/τ))
        noise_var = self.config.sigma0 ** 2 * T_bath * (1.0 - math.exp(-2.0 * dt / self.config.tau))
        noise_std = math.sqrt(max(noise_var, 0.0))

        for k in range(self.config.n_axes):
            self._eta[k] = decay * self._eta[k] + noise_std * random.gauss(0.0, 1.0)

        return list(self._eta)

    @property
    def eta(self) -> List[float]:
        """Current noise state without advancing time."""
        return list(self._eta)

    def summary(self) -> dict:
        """State for monitoring and diagnostics."""
        return {
            "eta": [round(e, 6) for e in self._eta],
            "sigma0": self.config.sigma0,
            "tau": self.config.tau,
            "step_count": self._step_count,
        }
