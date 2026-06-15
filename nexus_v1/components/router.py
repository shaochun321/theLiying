"""nexus_v1.components.router — LiquidMetalRouter.

TYPE:HYBRID — Reconfigurable interconnect mapped to both
EGaIn microfluidic circuits and axonal navigation/pruning.

===========================================================
ZERO DEPENDENCY ON EXISTING NEXUS CODE.
===========================================================

Electronic Equivalent:
    Eutectic Gallium-Indium (EGaIn) liquid metal in microchannels:
    - High conductivity (σ ≈ 3.4 × 10⁶ S/m)
    - Reconfigurable: electrowetting moves metal droplets
    - Self-healing: fractures reconnect spontaneously
    - Oxide skin (Ga₂O₃): controllable contact resistance

    REF: Dickey 2017 — "Stretchable and Soft Electronics"
    REF: Palleau et al. 2013 — Self-healing stretchable wires

Biological Equivalent:
    - Axonal growth/retraction (growth cone navigation)
      → REF: Tessier-Lavigne & Goodman 1996 — guidance molecules
    - Synaptic pruning (activity-dependent elimination)
      → REF: Katz & Shatz 1996 — "Synaptic activity and the
        construction of cortical circuits"
    - Structural plasticity (new synapse formation)
      → REF: Holtmaat & Svoboda 2009 — experience-dependent
        structural plasticity

    Key principle: "Neurons that fire together wire together,
    neurons that fire apart wire apart." — Hebb 1949

Mathematical Model:
    Connection state: s(t) ∈ [0, 1]
        s = 0: fully disconnected (liquid metal retracted)
        s = 1: fully connected (liquid metal bridging)

    Dynamics:
        ds/dt = (s_target - s) / τ_reconfig

    s_target determined by correlation rule:
        corr = EMA(pre_activity × post_activity)
        if corr > θ_grow:  s_target = 1  (strengthen)
        if corr < θ_prune: s_target = 0  (eliminate)
        else:              s_target = s   (maintain)

    Effective conductance:
        G = G_metal × s × (1 - oxide_factor × (1-s))
"""

import math
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class LiquidMetalRouter:
    """Reconfigurable connection with activity-dependent topology.

    Models a liquid metal channel that can open, close, or
    partially conduct based on correlated activity between
    source and target neurons.

    Provides:
    1. Structural plasticity: new connections form/dissolve
    2. Self-healing: disrupted connections restore gradually
    3. Activity-dependent pruning: unused paths eliminated
    4. Graded connectivity: partial connections (oxide skin)

    Args:
        g_metal: maximum conductance (fully connected)
        tau_reconfig: reconfiguration time constant (seconds)
        theta_grow: correlation threshold to open connection
        theta_prune: correlation threshold to close connection
        oxide_factor: oxide skin resistance factor [0,1]
        ema_tau: activity correlation EMA time constant
    """

    g_metal: float = 1.0          # max conductance
    tau_reconfig: float = 1.0     # reconfiguration time (seconds)
    theta_grow: float = 0.3       # correlation to grow
    theta_prune: float = 0.05     # correlation to prune
    oxide_factor: float = 0.2     # oxide skin penalty
    ema_tau: float = 0.5          # activity EMA time constant

    # State
    _state: float = field(default=0.0, repr=False)     # s ∈ [0, 1]
    _s_target: float = field(default=0.0, repr=False)
    _correlation_ema: float = field(default=0.0, repr=False)
    _t: float = field(default=0.0, repr=False)

    @property
    def state(self) -> float:
        """Current connection state [0=disconnected, 1=connected]."""
        return self._state

    @property
    def conductance(self) -> float:
        """Current effective conductance."""
        s = self._state
        # Oxide skin adds resistance when partially connected
        oxide_penalty = 1.0 - self.oxide_factor * (1.0 - s)
        return self.g_metal * s * max(oxide_penalty, 0.01)

    @property
    def is_connected(self) -> bool:
        """Whether the connection is functionally active."""
        return self._state > 0.1

    @property
    def is_growing(self) -> bool:
        """Whether the connection is in growth phase."""
        return self._s_target > self._state + 0.05

    @property
    def is_pruning(self) -> bool:
        """Whether the connection is being pruned."""
        return self._s_target < self._state - 0.05

    def update_correlation(self, pre_activity: float,
                           post_activity: float, dt: float):
        """Update activity correlation EMA.

        Args:
            pre_activity: source neuron activity (|activation| or spike)
            post_activity: target neuron activity
            dt: time step
        """
        instant_corr = abs(pre_activity) * abs(post_activity)
        alpha = min(dt / max(self.ema_tau, 0.001), 1.0)
        self._correlation_ema += alpha * (instant_corr - self._correlation_ema)

    def step(self, pre_activity: float, post_activity: float,
             dt: float) -> float:
        """Update router state based on activity.

        Args:
            pre_activity: source neuron activity
            post_activity: target neuron activity
            dt: time step

        Returns:
            Current effective conductance
        """
        self._t += dt

        # Update correlation
        self.update_correlation(pre_activity, post_activity, dt)

        # Determine target state
        if self._correlation_ema > self.theta_grow:
            self._s_target = 1.0
        elif self._correlation_ema < self.theta_prune:
            self._s_target = 0.0
        # else: maintain current target

        # Relax toward target
        if self.tau_reconfig > 0:
            alpha = min(dt / self.tau_reconfig, 1.0)
            self._state += alpha * (self._s_target - self._state)
        else:
            self._state = self._s_target

        # Clamp
        self._state = max(0.0, min(1.0, self._state))

        return self.conductance

    def conduct(self, signal: float) -> float:
        """Pass a signal through the router.

        Args:
            signal: input signal

        Returns:
            Attenuated signal (signal × conductance)
        """
        return signal * self.conductance

    def force_connect(self):
        """Force immediate connection (for initialization)."""
        self._state = 1.0
        self._s_target = 1.0

    def force_disconnect(self):
        """Force immediate disconnection."""
        self._state = 0.0
        self._s_target = 0.0

    def heal(self, rate: float = 0.1):
        """Self-healing: gradually restore partially damaged connections.

        BIO: Schwann cell remyelination after injury
        """
        if self._state > 0.1 and self._state < 0.9:
            self._state = min(1.0, self._state + rate)

    def reset(self):
        """Reset to disconnected state."""
        self._state = 0.0
        self._s_target = 0.0
        self._correlation_ema = 0.0
        self._t = 0.0
