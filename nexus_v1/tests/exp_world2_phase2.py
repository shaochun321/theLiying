"""nexus_v1.tests.exp_world2_phase2 — World 2.0 Phase 2 STDP learning experiment.

Target: STDP learns thermotaxis in physical 3D environment over 500k steps.

Parameter overrides (all in this script, no mother code changes except _conv_k hook):
  - ThermalMouth.eta: 0.02 → 0.15   (7.5× Phase 1; covers basal metabolism)
  - CylindricalHeatSource.energy: 1000 → 8000  (one-time supply, ~500k budget)
  - circuit._conv_k: 0.5 → 0.15     (reduce physics drive; STDP carries more weight)
  - therm_front/back→move_x: weight_max=0.3, initial_weight reset to 0.01
  - therm_left/right→move_y: frozen at weight=0 (eliminates move_y interference)

DIAG-1 result (2026-06-28): sensory_gain=0.02 adequate; ~5000 step thermal warmup
  needed before enc_therm activation reaches ≥0.05 threshold. OK for 500k run.

Run from repo root:
    PYTHONIOENCODING=utf-8 python -m nexus_v1.tests.exp_world2_phase2
"""
import sys
import os
import math

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from nexus_v1.circuit.variant_adapter import VariantCircuit

STEPS = 500_000
REPORT_INTERVAL = 10_000


def dist_to_cylinder(body, src):
    dx = body.position[0] - src.center[0]
    dy = body.position[1] - src.center[1]
    return math.sqrt(dx * dx + dy * dy)


def find_bundle(all_bundles, keyword):
    return next((b for b in all_bundles if keyword in b.config.bundle_id), None)


def run():
    print("=" * 100)
    print("  World 2.0 Phase 2 — STDP Thermotaxis Learning (W10/W11/W12)")
    print(f"  {STEPS:,} steps, reporting every {REPORT_INTERVAL:,} steps")
    print("=" * 100)

    circuit = VariantCircuit()

    # ── Phase 2 parameter overrides ──
    # P2-01: ThermalMouth efficiency 7.5×
    # BIO: eta=0.02 in Phase 1 gave mouth_intake/step ~= 0.0001; basal drain ~0.001/step.
    # Raising to 0.15 brings mouth_intake near metabolic drain at dist_surface=10.
    circuit.thermal_mouth.eta = 0.15

    # P2-02: Heat source energy 8×
    # BUDGET: eta=0.15, 500k steps at ~50% proximity → ~6000-8000 units drain.
    # 8000 one-time supply (regen=0.002 → ~1 unit total, negligible).
    circuit._cylindrical_source.energy = 8000.0

    # P2-03: Convective drift = Phase 1 value (STDP supplements physics)
    # EXP-W2-005: k_conv=0.15 → drifted away (dist 22→34 in 140k steps).
    # EXP-W2-006: k_conv=0.40 → still drifted (dist 22→31 in 100k steps).
    # Root cause: Langevin motor noise ~0.054 units/step outward; threshold is
    # k_conv >= 0.47 to overcome noise (k_conv × |∇T| / μ ≥ motor_noise).
    # k_conv=0.5 (Phase 1 value): body approaches, STDP learns during approach.
    # Chicken-and-egg: body must get close FIRST before STDP can learn direction.
    # EXP-W2-004 updated: _conv_k attribute checked by step() via getattr.
    circuit._conv_k = 0.5

    # ── Body initial position (off-axis, same as Phase 1) ──
    circuit.world.body.position = [75.0, 35.0, 25.0]
    circuit.world.body.velocity = [0.0, 0.0, 0.0]
    circuit.world.body.yaw = 0.0
    # Clear legacy 8-point sources for clean cylindrical gradient
    circuit.world.heat_sources = []

    # ── Bundle overrides: post-init, no hebbian.py modification ──
    all_bundles = circuit.get_all_bundles()

    b_front = find_bundle(all_bundles, 'therm_therm_front_to_move_x')
    b_brake = find_bundle(all_bundles, 'therm_therm_back_to_move_x')
    b_left  = find_bundle(all_bundles, 'therm_therm_left_to_move_y')
    b_right = find_bundle(all_bundles, 'therm_therm_right_to_move_y')

    # Disable lateral bundles: weight=0, weight_max=0 (STDP cannot restore)
    for b in [b_left, b_right]:
        if b is not None:
            b.config.weight_max = 0.0
            for row in b._memristors:
                for m in row:
                    m.w = 0.0

    # Reset approach/brake bundles: from-zero learning, reduced saturation
    # initial_weight=0.01: EXP-W2-005 calibrated from Phase 5 Round 4
    # (0.1 → too fast, DA saturated; 0.01 → gradient visible at 100k mark)
    for b in [b_front, b_brake]:
        if b is not None:
            b.config.weight_max = 0.3
            for row in b._memristors:
                for m in row:
                    m.w = 0.01

    # ── Print bundle override summary ──
    print()
    print("Bundle override summary:")
    print(f"  therm_front→move_x: w_max={b_front.config.weight_max if b_front else 'N/A'}, "
          f"mean_w={b_front.mean_weight():.4f}" if b_front else "  therm_front→move_x: NOT FOUND")
    print(f"  therm_back →move_x: w_max={b_brake.config.weight_max if b_brake else 'N/A'}, "
          f"mean_w={b_brake.mean_weight():.4f}" if b_brake else "  therm_back →move_x: NOT FOUND")
    print(f"  therm_left →move_y: disabled (w={b_left.mean_weight():.4f})" if b_left else "  therm_left →move_y: NOT FOUND")
    print(f"  therm_right→move_y: disabled (w={b_right.mean_weight():.4f})" if b_right else "  therm_right→move_y: NOT FOUND")
    print(f"  k_conv: {circuit._conv_k} (Phase 1: 0.5; 0.15/0.40 both failed: Langevin overwhelms weak drift)")
    print(f"  eta: {circuit.thermal_mouth.eta} (Phase 1: 0.02)")
    print(f"  source energy: {circuit._cylindrical_source.energy:.0f} (Phase 1: 1000)")
    print()

    # ── Column header ──
    print(f"{'step':>8} | {'dist_c':>7} | {'d_surf':>6} | {'yaw°':>7} | "
          f"{'fill':>6} | {'intake/s':>9} | {'src_E':>7} | "
          f"{'w_front':>7} | {'w_brake':>7} | {'damage':>7} | {'repair/s':>8}")
    print("-" * 100)

    # Monitoring accumulators
    repair_cost_acc = 0.0
    step_acc = 0
    prev_damage = [p.damage_integral for p in circuit.world.body.skin_patches]

    for step in range(1, STEPS + 1):
        # Langevin noise is applied inside circuit.step() via _langevin.step()
        circuit.step({}, dt=0.001)

        # Track repair cost: sum(damage_integral) × repair_energy_rate × dt
        curr_damage = [p.damage_integral for p in circuit.world.body.skin_patches]
        total_damage = sum(curr_damage)
        repair_cost_acc += total_damage * circuit.repair_energy_rate * 0.001
        step_acc += 1

        if step % REPORT_INTERVAL == 0:
            body = circuit.world.body
            src = circuit._cylindrical_source

            dist_c = dist_to_cylinder(body, src)
            dist_surf = dist_c - src.radius
            yaw_deg = math.degrees(body.yaw)
            fill = circuit.energy_store.fill_fraction
            intake = circuit.thermal_mouth.energy_intake

            w_front = b_front.mean_weight() if b_front else 0.0
            w_brake = b_brake.mean_weight() if b_brake else 0.0

            avg_repair = repair_cost_acc / step_acc if step_acc > 0 else 0.0

            print(f"{step:>8,} | {dist_c:>7.2f} | {dist_surf:>6.2f} | {yaw_deg:>7.1f} | "
                  f"{fill:>6.4f} | {intake:>9.6f} | {src.energy:>7.1f} | "
                  f"{w_front:>7.4f} | {w_brake:>7.4f} | {total_damage:>7.4f} | {avg_repair:>8.6f}")

            repair_cost_acc = 0.0
            step_acc = 0

    # ── Final assessment ──
    fill_final = circuit.energy_store.fill_fraction
    src_final = circuit._cylindrical_source.energy
    w_front_f = b_front.mean_weight() if b_front else 0.0
    w_brake_f = b_brake.mean_weight() if b_brake else 0.0
    dist_final = dist_to_cylinder(circuit.world.body, circuit._cylindrical_source)

    print("\n" + "=" * 100)
    print("  FINAL ASSESSMENT")
    print(f"  fill_fraction: {fill_final:.4f}  (W12 target: >0.05)")
    print(f"  source energy: {src_final:.1f} / 8000.0")
    print(f"  dist_surface:  {dist_final - circuit._cylindrical_source.radius:.2f} units")
    print(f"  w_front:       {w_front_f:.4f}")
    print(f"  w_brake:       {w_brake_f:.4f}")
    if w_brake_f > 1e-6:
        print(f"  w_front/w_brake ratio: {w_front_f/w_brake_f:.3f}  (W11 target: >2.0)")
    else:
        print(f"  w_front/w_brake ratio: N/A (w_brake~0)")

    # W10: dist_surface decreased >5 units from initial 23
    initial_dist_surface = 29.2 - 6  # from Phase 1 report: sqrt(850)≈29.2, r=6
    dist_surf_final = dist_final - circuit._cylindrical_source.radius
    w10 = (initial_dist_surface - dist_surf_final) > 5.0
    w11 = (w_front_f / w_brake_f > 2.0) if w_brake_f > 1e-6 else (w_front_f > 0.05)
    w12 = fill_final > 0.05

    print()
    print(f"  {'[PASS]' if w10 else '[FAIL]'} W10: dist_surface decrease > 5 units "
          f"(actual: {initial_dist_surface - dist_surf_final:.1f})")
    print(f"  {'[PASS]' if w11 else '[FAIL]'} W11: STDP directional weight ratio "
          f"w_front/w_brake > 2.0 (actual: {w_front_f/w_brake_f:.3f})" if w_brake_f > 1e-6 else
          f"  {'[PASS]' if w11 else '[FAIL]'} W11: w_front > 0.05 (actual: {w_front_f:.4f})")
    print(f"  {'[PASS]' if w12 else '[FAIL]'} W12: fill > 0.05 full-run (actual: {fill_final:.4f})")
    print("=" * 100)

    return w10, w11, w12


if __name__ == "__main__":
    results = run()
    ok = all(results)
    sys.exit(0 if ok else 1)
