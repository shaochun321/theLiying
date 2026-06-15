"""nexus_v1 — Structural Computation Rules (结构计算准则)

RULE S0: ALL SIGNAL-PATH COMPUTATION MUST USE SEMICONDUCTOR COMPONENTS
=========================================================================

Any computation that participates in signal flow, gating, clamping,
filtering, or attenuation MUST be implemented using the semiconductor
component library (Capacitor, MOSFET, Memristor, PowerRail) or
compositions thereof.

RATIONALE:
    The core thesis of nexus_v1 is that biological neural computation
    emerges from the STRUCTURE of semiconductor-equivalent components.
    If we bypass components with pure mathematical formulas:
    - Structure-dynamics correspondence breaks (the theory cannot be tested)
    - Components become decorative (violating Occam's razor)
    - Emergent behaviors from component interactions are lost
    - The system degrades to a conventional ANN with extra steps

ALLOWED pure math:
    - Read-only OBSERVATION tools (shadow sandbox, circulation meter, ledger)
    - Parameter CONFIGURATION (setting thresholds, gains, time constants)
    - Test scripts and diagnostics

FORBIDDEN pure math in signal path:
    - Direct arithmetic on activations (e.g., `min(x, cap)`, `x * gain`)
    - Inline formulas replacing component behavior (e.g., `2*Z/(Z+Zm)`)
    - PDE/ODE discretizations not routed through components

HOW TO IMPLEMENT instead:
    - Voltage clamp      → MOSFET (high gm, threshold at clamp voltage)
    - Current limit      → Capacitor pool (finite charge → finite output)
    - Signal gate        → MOSFET (control signal as gate voltage)
    - Signal integration → Capacitor (inject + leak = temporal filter)
    - Signal attenuation → PowerRail (IR drop = natural limiter)
    - Adaptive weight    → Memristor (conductance tracks state)
    - Thermal coupling   → Capacitor (thermal mass) + MOSFET (conductance)
    - Impedance match    → MOSFET divider (two MOSFETs, ratio = impedance)

COMPONENT PRIMITIVES:
    Capacitor   — charge storage, temporal integration, RC filtering
    MOSFET      — threshold gate, conductance, voltage-current conversion
    Memristor   — adaptive weight, plastic conductance
    PowerRail   — energy supply, IR-drop natural saturation

DIFFERENTIATION (母本分化):
    New functional elements MUST be composed from these 4 primitives.
    If a genuinely new primitive is needed, it must be proposed to the
    user with full physical/biological justification before implementation.

RULE S2: RECURSIVE DIFFERENTIATION AND SEDIMENTATION (递归分化沉积)
=========================================================================

Structural growth operations (sprouting, pruning, splitting) are
governed by COMPONENT STATE, not by external optimization algorithms.

TRIGGERS (from component state, not from an optimizer):
    - Sprouting:  |ξ| > threshold    (Capacitor integrator voltage)
    - Pruning:    w → 0 sustained    (Memristor conductance)
    - Splitting:  κ_act → 0          (activation diversity collapse)

CONSTRAINTS:
    - Energy conservation: growth operations consume neuron energy
    - PowerRail limitation: new connections are naturally limited by IR drop
    - Blind topology: sprouts do NOT use gradient/covariance guidance
      STDP (Memristor adaptation) decides post-hoc what survives

FORBIDDEN:
    - Covariance-guided target selection (violates S0: pure math in path)
    - Weight redistribution / "vampire" rules (conductance is not conserved)
    - Human-imposed weight splitting (PowerRail handles current limiting)

THE CYCLE:
    Differentiation (STDP + sprouting + splitting)
      → Sedimentation (maturation + pruning)
        → Recursion (each round's output is next round's input)
"""
