"""nexus_v1.components.physical_constants — Project-wide physical constants.

All values are in SIMULATION UNITS unless explicitly noted otherwise.
Where biological values are referenced, the conversion basis is given.

Usage:
    from nexus_v1.components.physical_constants import (
        RHO_HC, RHO_AFF, RHO_THERMO, SKIN_DEPTH_MM
    )

Convention:
    _BIO suffix: raw biological value (SI or biological units)
    no suffix:  simulation-unit equivalent (or unitless ratio)
"""

# ─────────────────────────────────────────────────────────────────────────────
# Vestibular — anterior/lateral cristae (small mammal, gerbil/chinchilla)
# ─────────────────────────────────────────────────────────────────────────────

# BIO: hair cell packing density at gerbil crista.
# Range 20k–100k/mm²; internal sources inconsistent 3–5× → take lower bound.
# REF: Hasson et al. 1989; Lindeman 1969 (anatomical counts)
RHO_HC: int = 20_000          # cells/mm² (conservative)

# BIO: afferent fiber innervation density at gerbil vestibular nerve.
# REF: Eatock & Songer 2011 "Vestibular hair cells and afferents"
RHO_AFF: int = 30_000         # fibers/mm²

# BIO: hair cell → afferent convergence ratio (many hair cells : one afferent).
# REF: Goldberg et al. 1990 — 2:1 to 3:1 in cat/monkey; 2.5 adopted.
CONVERGENCE_RATIO: float = 2.5   # hair cells per afferent

# Synapse gain at N=1 afferent (engineering compensation for single-fiber mode).
# Derivation: g_bio ≈ 0.48 (Eatock & Songer 2011, normalized).
# At N=1: synapse_gain = g_bio × 33 (inverse √N × N factor) ≈ 33×0.48 ≈ 16.
# EXP: g=16 sustained signal at N=1; calibrated across Phase 2–8.
# REF: g ∝ 1/N^(3/2) for group-coding gain compensation (see V2.0 Phase B plan)
SYNAPSE_GAIN_AFF_N1: float = 16.0   # dimensionless; at N=1 afferent per axis

# ─────────────────────────────────────────────────────────────────────────────
# Skin — thermal receptors
# ─────────────────────────────────────────────────────────────────────────────

# BIO: cutaneous thermoreceptor density (TRPV3, TRPM8 warm/cool fibers).
# Range 1–5/mm²; sparse relative to mechanoreceptors.
# REF: Spray 1986; Hensel 1973 — primate/rodent skin thermoreceptor counts
RHO_THERMO: float = 2.0       # cells/mm²

# BIO: nociceptive free-nerve-ending density.
# UNRESOLVED: 100–200/mm² (total free endings) vs 5–10/mm² (TRPV1-specific).
# Locked pending literature clarification; used only in Phase B scale-up.
# REF: Slugg et al. 2000 (5–10 TRPV1+); McCarthy & Lawson 1989 (100–200 total)
RHO_NOCI_TOTAL: float = 150.0      # /mm² (total free nerve endings — upper estimate)
RHO_NOCI_TRPV1: float = 7.5       # /mm² (TRPV1-specific — lower estimate)
# NOTE: Use RHO_NOCI_TRPV1 for TRPV1-targeted channel models; RHO_NOCI_TOTAL
# only for structural neuron counts that include all pain modalities.

# ─────────────────────────────────────────────────────────────────────────────
# Skin thermal physics
# ─────────────────────────────────────────────────────────────────────────────

SKIN_DEPTH_MM: float = 0.5         # penetration depth in mm

# BIO: skin thermal conductivity κ ≈ 0.3 W/(m·K) in epidermis/dermis.
# REF: Duck 1990 "Physical Properties of Tissue"
SKIN_CONDUCTIVITY_W_PER_MK: float = 0.3   # W/(m·K)

# BIO: skin thermal diffusivity α ≈ 0.14 mm²/s.
# Used to verify SkinPatch τ = depth²/(2α) ≈ 0.25/(0.28) ≈ 0.89s ≈ 1s.
# (SkinPatch uses C/k formulation → τ = 5s; biological range 0.9–5s depending
# on depth; SkinPatch τ=5s corresponds to ~2.5mm effective penetration depth.)
# REF: Elwassif et al. 2006 — thermal diffusivity in brain tissue
SKIN_THERMAL_DIFFUSIVITY_MM2_PER_S: float = 0.14   # mm²/s

# BIO: skin specific heat capacity cp ≈ 3500 J/(kg·K), density ρ ≈ 1000 kg/m³.
# REF: Duck 1990
SKIN_SPECIFIC_HEAT_J_PER_KGK: float = 3500.0
SKIN_DENSITY_KG_PER_M3: float = 1000.0

# ─────────────────────────────────────────────────────────────────────────────
# SkinPatch geometry (current V1.0: 4 patches)
# ─────────────────────────────────────────────────────────────────────────────

# Area per patch at effective_radius=2mm sphere surface, 4 patches.
# A_sphere = 4π r² = 4π × 4 = 50.3 mm²; each patch ≈ 12.6 mm².
PATCH_AREA_MM2: float = 12.6       # mm²/patch (4-patch config, r=2mm body)

# ─────────────────────────────────────────────────────────────────────────────
# Simulation timestep (nominal)
# ─────────────────────────────────────────────────────────────────────────────

DT_NOMINAL_S: float = 0.001        # s/step (1 ms; standard across all tests)
