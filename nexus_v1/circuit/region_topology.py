"""nexus_v1.circuit.region_topology — Brain-region distance matrix and delay routing.

TYPE:INFRA

Physical distance matrix D_REGION[from_region][to_region] in mm.
Source: 《脑区空间归类与地址系统升级实施方案（整合最终版v2.0）》§1.5
Regions: 0x01=spinal, 0x02=brainstem, 0x03=main, 0x04=hypothalamus, 0x05=shadow

Shadow layer (0x05) is attached to main layer (0x03) at 1 mm distance (microcircuit
adjacency). Distances from shadow to other regions follow main-layer distances + 1mm.
"""

from __future__ import annotations

# ── Region constants ──────────────────────────────────────────────────────────
REGION_UNASSIGNED   = 0x00
REGION_SPINAL       = 0x01   # spinal cord (anterior/posterior horn)
REGION_BRAINSTEM    = 0x02   # medulla / pons / midbrain (vestibular nuclei, CPG)
REGION_MAIN         = 0x03   # cortical analog (encoding, column, motor, DA)
REGION_HYPOTHALAMUS = 0x04   # hypothalamus (ARC, VMH, LH — energy sensing)
REGION_SHADOW       = 0x05   # shadow sandbox (attached to main, 1 mm adjacency)

# Internal hypothalamus sub-layers (stored as metadata, not used in D_REGION)
HYP_LAYER_SENSOR  = 0x00    # L0: ARC — energy_sensor neurons
HYP_LAYER_AVERAGE = 0x01    # L1: VMH — average_energy + CPC
HYP_LAYER_OUTPUT  = 0x02    # L2: LH  — hunger / effort output neurons

# Internal shadow sub-layers (conceptual, not used in D_REGION)
SHADOW_LAYER_ENC = 0x01     # s_enc (shadow encoding)
SHADOW_LAYER_COL = 0x02     # s_col (shadow column)
SHADOW_LAYER_MOT = 0x03     # s_mot (shadow motor)

# ── Physical distance matrix ──────────────────────────────────────────────────
# D_REGION[(from_region, to_region)]: distance between region centers [mm].
# REF: 《脑区空间归类与地址系统升级实施方案（整合最终版v2.0）》§1.5
D_REGION: dict = {
    # Spinal cord (0x01)
    (REGION_SPINAL, REGION_SPINAL):       1,
    (REGION_SPINAL, REGION_BRAINSTEM):    3,
    (REGION_SPINAL, REGION_MAIN):         4,
    (REGION_SPINAL, REGION_HYPOTHALAMUS): 6,
    (REGION_SPINAL, REGION_SHADOW):       5,   # main+1

    # Brainstem (0x02)
    (REGION_BRAINSTEM, REGION_SPINAL):       3,
    (REGION_BRAINSTEM, REGION_BRAINSTEM):    1,
    (REGION_BRAINSTEM, REGION_MAIN):         3,
    (REGION_BRAINSTEM, REGION_HYPOTHALAMUS): 5,
    (REGION_BRAINSTEM, REGION_SHADOW):       4,   # main+1

    # Main layer (0x03)
    (REGION_MAIN, REGION_SPINAL):       4,
    (REGION_MAIN, REGION_BRAINSTEM):    3,
    (REGION_MAIN, REGION_MAIN):         1,
    (REGION_MAIN, REGION_HYPOTHALAMUS): 3,
    (REGION_MAIN, REGION_SHADOW):       1,   # microcircuit adjacency

    # Hypothalamus (0x04)
    (REGION_HYPOTHALAMUS, REGION_SPINAL):       6,
    (REGION_HYPOTHALAMUS, REGION_BRAINSTEM):    5,
    (REGION_HYPOTHALAMUS, REGION_MAIN):         3,
    (REGION_HYPOTHALAMUS, REGION_HYPOTHALAMUS): 1,
    (REGION_HYPOTHALAMUS, REGION_SHADOW):       4,   # main+1

    # Shadow layer (0x05) — attached to main at 1 mm
    (REGION_SHADOW, REGION_SPINAL):       5,
    (REGION_SHADOW, REGION_BRAINSTEM):    4,
    (REGION_SHADOW, REGION_MAIN):         1,
    (REGION_SHADOW, REGION_HYPOTHALAMUS): 4,
    (REGION_SHADOW, REGION_SHADOW):       1,
}

# Valid region codes for bounds-checking
_VALID_REGIONS = {
    REGION_SPINAL, REGION_BRAINSTEM, REGION_MAIN,
    REGION_HYPOTHALAMUS, REGION_SHADOW,
}

# ── Conduction velocities ─────────────────────────────────────────────────────
V_MYELINATED   = 1000.0   # mm/s — high-speed myelinated (reflex / emergency)
V_UNMYELINATED = 1.0      # mm/s — standard unmyelinated (homeostatic modulation)


def synaptic_delay_steps(
    from_region: int,
    to_region: int,
    dt: float = 0.001,
    myelinated: bool = True,
) -> int:
    """Compute synaptic delay in simulation steps.

    τ [steps] = round(d_mm / (v_cond [mm/s] × dt [s]))

    Args:
        from_region: source region code (0x01..0x05)
        to_region:   target region code (0x01..0x05)
        dt:          simulation timestep [s]
        myelinated:  True = 1000 mm/s (reflex); False = 1 mm/s (homeostatic)

    Returns:
        Delay in steps (minimum 1).

    Raises:
        ValueError: if either region code is not in the valid set.
    """
    if from_region not in _VALID_REGIONS:
        raise ValueError(
            f"synaptic_delay_steps: invalid from_region=0x{from_region:02X}. "
            f"Valid codes: {[hex(r) for r in sorted(_VALID_REGIONS)]}"
        )
    if to_region not in _VALID_REGIONS:
        raise ValueError(
            f"synaptic_delay_steps: invalid to_region=0x{to_region:02X}. "
            f"Valid codes: {[hex(r) for r in sorted(_VALID_REGIONS)]}"
        )
    if from_region == to_region:
        return 1   # intra-region: use nearby() instead of explicit cross-region delay

    d_mm = D_REGION[(from_region, to_region)]
    v = V_MYELINATED if myelinated else V_UNMYELINATED
    return max(1, round(d_mm / (v * dt)))
