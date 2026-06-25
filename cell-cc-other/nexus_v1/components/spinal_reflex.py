"""nexus_v1.components.spinal_reflex — Nociceptive withdrawal reflex arc.

L2:SELECTION — This is an artificial evolutionary choice.
BIO: Aδ-fiber → spinal interneuron → α-motor neuron (Sherrington 1906).
DESIGN: We hardwire nociceptor spatial contrast → directional motor current.
EMERGE: The withdrawal direction itself is not learned — it is L2 fixed.
        But the GAIN can be modulated by a cortical gate (future L1 override).

Architecture:
    4 skin patches (front, back, left, right) produce nociceptor activations.
    Spatial contrast between opposing patches → signed motor drive.
    A MOSFET gate (default: open) allows future cortical override.

    ┌──────────────────────────────────────────────────┐
    │              SpinalReflexArc                     │
    │                                                  │
    │  noci_front ──┐                                  │
    │  noci_back  ──┼─→ Δ_x = back - front → motor_x  │
    │  noci_left  ──┤                                  │
    │  noci_right ──┘─→ Δ_y = right - left → motor_y   │
    │                                                  │
    │  [MOSFET gate] ← default VDD (open)              │
    │       ↑ future: cortical inhibition injection     │
    │                                                  │
    │  output = Δ × REFLEX_GAIN × gate_conductance     │
    └──────────────────────────────────────────────────┘

Gate Control Theory (Melzack & Wall, 1965):
    Spinal dorsal horn contains gate interneurons that modulate
    nociceptive signal transmission. Descending cortical fibers
    can inhibit (close the gate) or facilitate (open the gate)
    pain signal relay. This is a continuous, analog modulation —
    not a binary switch.

    In our design:
      gate_voltage = 1.0 (VDD)  → gate fully open → reflex executes
      gate_voltage = 0.0        → gate closed → reflex suppressed
      gate_voltage = 0.5        → partial inhibition ("enduring pain")

    The gate_voltage is a MOSFET control voltage. Future cortical
    modules will inject negative current to pull it toward 0.

REF: Sherrington 1906 — "The Integrative Action of the Nervous System"
REF: Melzack & Wall 1965 — "Pain Mechanisms: A New Theory"
REF: Eccles 1964 — spinal reflex arc neurophysiology
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict

from .semiconductor import MOSFET


@dataclass
class SpinalReflexConfig:
    """Configuration for the spinal reflex arc.

    L2:SELECTION — These parameters are artificial evolutionary choices.
    They define the "innate reflexes" of the organism.
    """
    # ── Nociceptive withdrawal (flee from pain) ──
    # Reflex gain: nociceptor contrast → motor current magnitude
    # L2:SELECTION — Calibrated so reflex can save life but not dominate
    # BIO: reflex strength ∝ stimulus intensity (Sherrington's law)
    # DESIGN: 0.5 chosen so reflex is visible but STDP can surpass it
    # EMERGE: System should learn optimal avoidance that improves on reflex
    reflex_gain: float = 0.5

    # MOSFET gate parameters (for cortical override)
    # Default: gate fully open (VDD = 1.0)
    gate_v_threshold: float = 0.1   # below this, gate fully closed
    gate_gm: float = 2.0            # conductance gain

    # Nociceptor activation threshold: only fire reflex if noci > this
    # L2:SELECTION — noise filter. Very low = twitchy. High = sluggish.
    # BIO: Aδ threshold is low but not zero (bare nerve ending)
    noci_threshold: float = 0.01

    # ── Hunger-driven thermotaxis (approach warmth when hungry) ──
    # Same spatial contrast architecture, inverted direction.
    # BIO: hypothalamic hunger signal → lateral hypothalamus →
    #      locomotor drive toward food odor/heat gradient.
    #      (Saper et al. 2002: "The need to feed")
    # Gain is lower than noci: feeding urge is weaker than pain.
    # PHYS: uses thermoreceptor DC channel (not nociceptor AC).
    # CALIBRATION (EXP-018 diag): with gain=0.6, hunger_drive_x steady-state
    # ≈ 0.08 — below motor v_threshold (~0.1-0.2). Motor never fires.
    # Need V_ss = gain × delta_x × da_factor × gate ≈ 0.5 to exceed threshold.
    # At steady-state: delta_x≈0.45, da_factor≈1.0, gate≈0.53
    # → gain=2.0 → drive≈0.48 (above motor threshold)
    hunger_approach_gain: float = 2.0     # calibrated: V_ss > motor v_threshold

    # Hunger gate MOSFET: controlled by (1 - fill_fraction)
    # fill_fraction ≈ 1.0 → hunger_voltage ≈ 0 → gate closed (satiated)
    # fill_fraction ≈ 0.0 → hunger_voltage ≈ 1 → gate open (starving)
    # BIO: leptin/ghrelin modulation of hypothalamic feeding circuits
    hunger_gate_v_threshold: float = 0.15  # gate opens below ~85% fill (was 0.3/~70%)
    hunger_gate_gm: float = 1.5            # moderate gain (gentler than pain)

    # ── DA modulation of hunger approach (basal ganglia motor gating) ──
    # BIO: basal ganglia output (GPi/SNr) gates locomotor drive.
    #      High DA (high prediction error / urgency) → stronger approach.
    #      Low DA (homeostasis) → baseline reflex level (NOT suppressed).
    # PHYS: gain_factor = da_min_gain + DA × (da_max_gain - da_min_gain)
    #   DA=0 → gain × 1.0 (baseline: reflex is innate, not DA-dependent)
    #   DA=0.5 → gain × 1.5 (moderate boost)
    #   DA=1 → gain × 2.0 (double strength)
    # DESIGN: reflexes are L2-hardwired (prior to learning). DA should only
    # AMPLIFY the reflex (positive modulation), never suppress it.
    # REF: Mogenson 1980 — "limbic-motor integration"
    da_min_gain: float = 1.0    # DA=0: full reflex strength (innate baseline)
    da_max_gain: float = 2.0    # DA=1: double reflex strength (DA amplification)



class SpinalReflexArc:
    """Nociceptive withdrawal reflex: noci spatial contrast → directional motor.

    L2:SELECTION — Hardwired at "birth" (init). Not learned.
    BIO: flexion withdrawal reflex (Sherrington 1906).

    The reflex uses spatial nociceptor contrast to compute withdrawal
    direction. This is physically grounded: the patch closer to the
    noxious source fires more → organism flees in the opposite direction.

    The MOSFET gate provides analog cortical override capability.
    Default state: gate_voltage = 1.0 (VDD), reflex fully active.
    """

    def __init__(self, config: SpinalReflexConfig | None = None):
        if config is None:
            config = SpinalReflexConfig()
        self.config = config

        # ── Nociceptive withdrawal gate ──
        # MOSFET gate: controls reflex throughput
        # BIO: spinal gate interneuron (Melzack & Wall 1965)
        # Default: gate_voltage = VDD → fully open
        self._gate = MOSFET(
            v_threshold=config.gate_v_threshold,
            gm=config.gate_gm,
        )

        # L2:SELECTION — Gate voltage. Default 1.0 (fully open).
        # Future cortical module will modulate this.
        # PLACEHOLDER: no cortical input yet.
        self._gate_voltage: float = 1.0

        # ── Hunger approach gate ──
        # MOSFET gate: controlled by hunger signal (1 - fill_fraction).
        # When satiated (fill ≈ 1) → gate_voltage ≈ 0 → closed.
        # When hungry (fill ≈ 0) → gate_voltage ≈ 1 → open.
        # BIO: lateral hypothalamic feeding circuit activation
        #      gated by leptin/ghrelin balance.
        self._hunger_gate = MOSFET(
            v_threshold=config.hunger_gate_v_threshold,
            gm=config.hunger_gate_gm,
        )

    def set_gate_voltage(self, voltage: float):
        """Set gate voltage (for future cortical override).

        Args:
            voltage: 0.0 = gate closed (reflex suppressed)
                     1.0 = gate open (reflex active)
                     Intermediate = partial suppression ("enduring pain")
        """
        self._gate_voltage = max(0.0, voltage)

    def process(self, noci_activations: Dict[str, float],
                dt: float = 1.0) -> Dict[str, float]:
        """Compute directional motor drive from nociceptor spatial contrast.

        Args:
            noci_activations: dict of patch_id → nociceptor activation
                Expected keys: "front", "back", "left", "right"
            dt: time step

        Returns:
            dict of motor_key → signed current to inject
                "move_x": positive = forward, negative = backward
                "move_y": positive = left, negative = right
                "move_z": always 0.0 (no vertical reflex for now)
        """
        # Extract per-patch nociceptor activations (default 0.0)
        front = noci_activations.get("front", 0.0)
        back = noci_activations.get("back", 0.0)
        left = noci_activations.get("left", 0.0)
        right = noci_activations.get("right", 0.0)

        # Check if any nociceptor is above threshold
        max_noci = max(front, back, left, right)
        if max_noci < self.config.noci_threshold:
            return {"move_x": 0.0, "move_y": 0.0, "move_z": 0.0}

        # Spatial contrast → directional drive
        # L2:SELECTION — Flee AWAY from the more stimulated side
        # front > back → heat is in front → flee backward (negative x)
        # left > right → heat is on left → flee right (negative y)
        delta_x = back - front   # positive = flee forward (away from back)
        delta_y = right - left   # positive = flee left (away from right)

        # Apply reflex gain
        raw_x = delta_x * self.config.reflex_gain
        raw_y = delta_y * self.config.reflex_gain

        # Gate modulation via MOSFET
        # MOSFET.conduct(gate_voltage) → conductance factor
        gate_factor = self._gate.conduct(self._gate_voltage)

        return {
            "move_x": raw_x * gate_factor,
            "move_y": raw_y * gate_factor,
            "move_z": 0.0,  # no vertical reflex (2D plane is sufficient)
        }

    def process_hunger(self, thermo_activations: Dict[str, float],
                       fill_fraction: float,
                       da_concentration: float = 0.0,
                       gain_multiplier: float = 1.0,
                       dt: float = 0.001) -> Dict[str, float]:
        """DEPRECATED: Hardcoded thermotaxis reflex removed in STDP cold-start experiment.

        Returns zero drives. Motor is now driven exclusively by Langevin noise
        (AGC-modulated). Thermotaxis must emerge from STDP weight learning.
        See: STDP冷启动实验方案, Phase 1 (裁定文档 D04).
        """
        import warnings
        warnings.warn(
            "process_hunger() is disabled (STDP cold-start experiment Phase 1). "
            "All drives are zero. Remove the call in variant_adapter.py to silence this.",
            DeprecationWarning, stacklevel=2
        )
        return {"move_x": 0.0, "move_y": 0.0, "move_z": 0.0}

    @property
    def gate_voltage(self) -> float:
        """Current noci gate voltage (for monitoring)."""
        return self._gate_voltage

    @property
    def gate_conductance(self) -> float:
        """Current noci gate conductance (for monitoring)."""
        return self._gate.conduct(self._gate_voltage)

    def summary(self) -> dict:
        """State for monitoring."""
        return {
            "noci_gate_voltage": round(self._gate_voltage, 4),
            "noci_gate_conductance": round(self.gate_conductance, 4),
            "reflex_gain": self.config.reflex_gain,
            "hunger_approach_gain": self.config.hunger_approach_gain,
        }
