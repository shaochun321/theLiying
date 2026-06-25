"""nexus_v1 — RULE S1: Metric-Mediated Interface Compatibility (度量中介兼容准则)

RULE S1: ALL CROSS-DOMAIN INTERFACES MUST BE MEDIATED BY THE PROJECT'S METRIC SYSTEM
======================================================================================

When components originating from different disciplines (EE, neuroscience,
physics, information theory) connect, the connection must pass through an
explicit compatibility check using the project's own mathematical framework.

PROBLEM STATEMENT:
    nexus_v1 sits at the intersection of:
      - Electrical Engineering (MOSFET, Capacitor, Memristor, PowerRail)
      - Neuroscience (Ca2+, vesicle pools, STDP, DA modulation)
      - Physics (impedance, thermal diffusion, acoustic transmission)
      - Information Theory (entropy, mutual information, free energy)

    Each discipline has its OWN conventions for:
      - Gain/attenuation formulas  (EE: V_out/V_in; Physics: 2Z/(Z+Zm))
      - Time scales               (EE: RC=ms; Bio: DA=seconds)
      - Signal types              (EE: voltage; Bio: concentration; Physics: force)

    When we borrow a formula or component from one discipline and plug it
    into another, COMPATIBILITY IS NOT AUTOMATIC. The physical world handles
    this via "客观实现" (objective realization), but code does not.

SOLUTION:
    The project's mathematical framework (ds2, g_ij, rho, nu, kappa)
    serves as the UNIVERSAL TRANSLATOR between domains.

THE THREE COMPATIBILITY CHECKS:
=================================

CHECK 1: DIMENSIONAL CONSISTENCY (量纲一致性)
    Every signal at every interface has a TYPE:
      - voltage    (V: membrane potential, gate voltage, Ca concentration)
      - current    (I: synaptic current, heat flow, DA release rate)
      - conductance (G: weight, gm, thermal conductivity)
      - time       (t: dt, tau, period)

    RULE: When signal crosses a domain boundary, the TYPE must be
    explicitly preserved or explicitly converted via a component.

    EXAMPLES:
      BAD:  col.activation *= da_gain    # mixing "voltage" with "concentration ratio"
      GOOD: col_membrane.inject(da_mosfet.conduct(da_concentration), dt)
            # da_concentration -> MOSFET -> current -> inject into membrane

CHECK 2: SCALE CONSISTENCY (尺度一致性)
    Every parameter must be consistent with the system's time scale
    and amplitude range. Use the governance modeler to verify:

      - tau_component should be comparable to the dynamics it serves
      - gain × input should produce output in the expected range
      - saturation limits should match downstream thresholds

    VERIFICATION: After setting any parameter, compute:
      V_steady_state = I_input * R_component
      tau_response = C * R
      Verify: V_ss is in [V_threshold, V_saturation] of downstream
      Verify: tau is appropriate for the phenomenon (ms for spikes, s for DA, min for PNN)

CHECK 3: FORMULA CONSISTENCY (公式一致性)
    When borrowing a formula from a discipline, verify that the
    PHYSICAL MEANING is preserved in the component implementation:

      - Acoustic transmission: T = 2Z/(Z+Zm)     (NOT voltage divider Z/(Z+Zm))
      - Thermal diffusion:     dT/dt = kappa*dT   (Ohm's law: I = G*V, consistent)
      - STDP learning:         dw = f(pre, post)  (Memristor update, consistent)

    WHEN IN DOUBT: Write the formula in its original discipline.
    Then map each term to a component. If the mapping requires a
    factor (like the 2 in transmission), that factor must come from
    the STRUCTURE (two symmetric paths) not from a magic constant.

INTERFACE TABLE:
    Source Domain  | Signal       | Component Interface     | Target Domain
    ─────────────────────────────────────────────────────────────────────────
    Vestibular     | deflection   | MET MOSFET conduct()    | Circuit (current)
    Circuit        | activation   | Membrane Capacitor V    | Learning (pre_trace)
    Ca2+ dynamics  | concentration| Ca Capacitor voltage    | Synapse (release_rate)
    Prediction     | xin_tension  | Integrator Capacitor V  | DA (release)
    DA system      | concentration| DA MOSFET conduct()     | Circuit (current inject)
    Temperature    | heat         | Thermal MOSFET conduct()| ECM (temperature)
    Body physics   | impedance    | MOSFET divider ratio    | Circuit (attenuation)
    Binding        | co-activation| Sync MOSFET conduct()   | Learning (gate)

    Every row in this table is a cross-domain interface.
    Every interface uses a COMPONENT (column 3) to translate.

RELATIONSHIP TO S0:
    S0: Structure (WHAT to build with)    — use semiconductor components
    S1: Compatibility (HOW to connect)    — use the metric system to verify

    S0 without S1: components connect but may be physically inconsistent
    S1 without S0: consistency checks on pure math (pointless, no structure)
    S0 + S1: structural computation with verified cross-domain compatibility
"""
