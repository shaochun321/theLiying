"""nexus_v1.components.calcium_channel — CalciumChannel + CalciumDynamics.

TYPE:SEMI — CaV1.3 voltage-gated Ca²⁺ channel as a MOSFET specialization.

Physical chain implemented here:
    V_m (membrane voltage)
      ↓  [Boltzmann gate — CalciumChannel.conductance()]
    g_Ca(V_m)   — voltage-dependent conductance
      ↓  [Ohm's law — CalciumChannel.current()]
    I_Ca = g_Ca × (E_Ca − V_m)   — inward current, positive convention
      ↓  [RC integrator — CalciumDynamics.step()]
    V_ca   — intracellular Ca²⁺ level (normalized concentration proxy)
      ↓  [quadratic gate — CalciumDynamics.release_rate()]
    release_rate   — neurotransmitter release rate (maps to HC-008 output)

Phase A scope: standalone components, NOT connected to any circuit.
Phase B (future): replace HairCell direct-assign with this chain when
  hc_to_aff bundle is unfrozen and N=1→3 vestibular expansion is ready.

Unit system (locked 2026-07-03):
    All parameters are in simulation dimensionless units.
    Anchor: HC MOSFET v_threshold = 0.308 ↔ biological CaV1.3 V_half = −41 mV
    Scale: ~0.0106 V_sim/mV  (derived from sim=0 ↔ bio=−70 mV resting)
    E_Ca in sim units ≈ 1.27–1.5 (biological +50 mV, well above active range)

Polarity convention (locked 2026-07-03):
    Inward Ca²⁺ current is POSITIVE.
    I_Ca = g(V_m) × (E_Ca − V_m) > 0  for V_m < E_Ca  (always in range).
    This matches the sign convention of downstream CalciumDynamics.step().
"""

import math


# ─────────────────────────────────────────────────────────────────────────────
# CalciumChannel — CaV1.3 voltage-gated Ca²⁺ conductance
# ─────────────────────────────────────────────────────────────────────────────

class CalciumChannel:
    """TYPE:SEMI — CaV1.3 L-type voltage-gated calcium channel.

    BIO: Inner hair cell (IHC) basolateral membrane.  CaV1.3 is the
         dominant L-type channel driving synaptic vesicle release.
    REF: Bao et al. 2003 J Neurophysiol 90:1195 — CaV1.3 half-activation
         voltage −41 mV, slope factor 5 mV (gerbil IHC).
    REF: Platzer et al. 2000 Cell 102:89 — CaV1.3 knockout abolishes
         IHC exocytosis.
    PHYS: Voltage-gated current source — MOSFET specialization.
          Boltzmann steady-state activation (m_∞) without gating kinetics
          (τ_gate = 0: instantaneous, valid for slow drive signals dt=1ms).
    """

    def __init__(self) -> None:
        # BIO: half-activation voltage −41 mV (Bao 2003).
        # Mapped to simulation units anchored at HC MOSFET v_threshold=0.308.
        # Derivation: sim_V_half = 0.308 because HC fires when CaV1.3 opens.
        self.V_half: float = 0.308

        # BIO: Boltzmann slope factor 5 mV (Bao 2003).
        # Mapped: 5 mV × 0.0106 V_sim/mV ≈ 0.053; conservatively 0.030
        # (10% of suprathreshold range 0.2–0.5, avoids overflow at V_m~0.5).
        self.k: float = 0.030

        # BIO: maximum Ca²⁺ conductance — normalized from single-channel
        # conductance ~25 pS × ~80 channels/μm² → 2.0 nS/μm² (order-of-mag).
        # In sim units: 2.0 (dimensionless; downstream RC absorbs scaling).
        # REF: Roberts et al. 1990 Nature 345:255 — IHC Ca channel density.
        self.g_max: float = 2.0

        # BIO: Ca²⁺ reversal potential E_Ca ≈ +50 mV (Nernst, 2 mM [Ca]_o).
        # Sim units: (50 − (−70)) × 0.0106 ≈ 1.27 → use 1.5 (headroom).
        # Must remain > max active V_m (~0.8) so current stays inward.
        self.E_Ca: float = 1.5

    # ── Boltzmann steady-state activation ────────────────────────────────────

    def conductance(self, V_m: float) -> float:
        """Steady-state conductance: g = g_max / (1 + exp(−(V−V_half)/k)).

        Returns g_max/2 at V_m = V_half; approaches 0 for V_m << V_half
        and g_max for V_m >> V_half.
        """
        return self.g_max / (1.0 + math.exp(-(V_m - self.V_half) / self.k))

    # ── Ohm's law — inward-positive convention ───────────────────────────────

    def current(self, V_m: float) -> float:
        """Inward Ca²⁺ current (positive = inward).

        I_Ca = g(V_m) × (E_Ca − V_m)

        Positive for all physiological V_m < E_Ca=1.5.
        PHYS: Goldman–Hodgkin–Katz reduced to Ohm's law at low [Ca]_i.
        """
        return self.conductance(V_m) * (self.E_Ca - V_m)


# ─────────────────────────────────────────────────────────────────────────────
# CalciumDynamics — intracellular Ca²⁺ RC integrator
# ─────────────────────────────────────────────────────────────────────────────

class CalciumDynamics:
    """TYPE:SEMI — Intracellular Ca²⁺ buffering and extrusion (RC integrator).

    BIO: PMCA (plasma-membrane Ca²⁺-ATPase) pump provides Ca²⁺ extrusion
         (models R_ca, the clearance "resistance").  Endogenous buffer
         proteins (calbindin-D28k, calretinin) provide Ca²⁺ buffering
         (models C_ca, the "capacitance").
    REF: Burrone & Lagnado 2000 J Physiol 524:821 — IHC Ca²⁺ dynamics,
         clearance time constant ~50 ms.
    PHYS: C_ca × dV_ca/dt = I_Ca − V_ca / R_ca
          At steady state: V_ca_ss = I_Ca × R_ca
          Time constant: τ [seconds] = R_ca × C_ca = 5.0 × 0.010 = 0.050 s = 50 ms
          In steps at dt=0.001 s: τ_steps = τ / dt = 50 steps.
    """

    def __init__(self) -> None:
        # BIO: Ca²⁺ extrusion resistance (PMCA pump, endogenous buffers).
        # REF: Burrone & Lagnado 2000 — τ ≈ 50 ms (gerbil IHC).
        self.R_ca: float = 5.0

        # BIO: Ca²⁺ buffering capacitance (calbindin-D28k, calretinin).
        # τ [seconds] = R_ca × C_ca = 5.0 × 0.010 = 0.050 s = 50 ms.
        # Note: the × dt in step() means R×C must be in seconds, not steps.
        self.C_ca: float = 0.010

        # Current normalized Ca²⁺ level (proxy for [Ca²⁺]_i).
        self.V_ca: float = 0.0

    # ── Discrete RC integration ───────────────────────────────────────────────

    def step(self, I_Ca: float, dt: float) -> float:
        """Integrate one timestep: C × dV/dt = I_Ca − V_ca/R.

        Args:
            I_Ca: inward Ca²⁺ current (positive = inward, from CalciumChannel).
            dt:   timestep in seconds (typically 0.001).

        Returns:
            Updated V_ca (normalized Ca²⁺ level).
        """
        dV = (I_Ca - self.V_ca / self.R_ca) / self.C_ca * dt
        self.V_ca += dV
        return self.V_ca

    # ── Neurotransmitter release rate ─────────────────────────────────────────

    def release_rate(self, threshold: float = 0.01, gain: float = 1.0) -> float:
        """Map V_ca to synaptic vesicle release rate (quadratic above threshold).

        BIO: Ca²⁺-triggered exocytosis follows a power-law (≥2) dependence
             on [Ca²⁺]_i near the active zone.
        REF: Beutner et al. 2001 Neuron 29:681 — fourth-power Ca²⁺ cooperativity
             at IHC ribbon synapse (simplified to quadratic for Phase A).
        NORM: Matches HC-008 gated_conduct quadratic — release_rate ≈ 0
              for normal drive signals, preserving Phase 5 compatibility.

        Args:
            threshold: minimum V_ca for release (default 0.01, Ca²⁺ dead band).
            gain:      output scaling factor.

        Returns:
            Non-negative release rate.
        """
        x = max(0.0, self.V_ca - threshold)
        return gain * x * x

    # ── Convenience ──────────────────────────────────────────────────────────

    def reset(self) -> None:
        """Reset Ca²⁺ level to zero (for test isolation)."""
        self.V_ca = 0.0

    @property
    def tau_steps(self) -> float:
        """Time constant in simulation steps at dt=0.001 s (= R_ca × C_ca / dt)."""
        return self.R_ca * self.C_ca / 0.001   # 5.0 × 0.010 / 0.001 = 50 steps
