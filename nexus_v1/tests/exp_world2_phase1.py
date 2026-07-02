"""nexus_v1.tests.exp_world2_phase1 — World 2.0 Phase 1 探测实验。

验收标准 W9: 100k 步后 fill_fraction > 0（口器供能接替 YolkSac）。

Run from repo root:
    PYTHONIOENCODING=utf-8 python -m nexus_v1.tests.exp_world2_phase1
"""
import sys
import os
import math

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from nexus_v1.circuit.variant_adapter import VariantCircuit
from nexus_v1.components.heat_source import CylindricalHeatSource
from nexus_v1.components.world import Body


STEPS = 100_000
REPORT_INTERVAL = 1_000


def dist_to_cylinder(body, src):
    dx = body.position[0] - src.center[0]
    dy = body.position[1] - src.center[1]
    return math.sqrt(dx * dx + dy * dy)


def run():
    print("=" * 72)
    print("  World 2.0 Phase 1 — Probe Experiment (W9)")
    print(f"  {STEPS:,} steps, reporting every {REPORT_INTERVAL:,} steps")
    print("=" * 72)
    print(f"{'step':>8} | {'fill':>6} | {'yolk':>6} | "
          f"{'m_intake':>9} | {'dist_cyl':>8} | {'yaw':>7} | "
          f"{'T_front':>7} | {'T_left':>7} | {'T_right':>7}")
    print("-" * 72)

    circuit = VariantCircuit()
    # Phase 1a: off-axis start — body NOT aligned with cylinder axis.
    # [75,35,25] vs cylinder [50,50,25]: dist_xy≈32, d_surface≈26, ΔT_lr≠0.
    # On-axis [82,50,25] had T_left≈T_right (symmetric) → yaw torque=0.
    circuit.world.body.position = [75.0, 35.0, 25.0]
    circuit.world.body.velocity = [0.0, 0.0, 0.0]
    circuit.world.body.yaw = 0.0
    # Phase 1a: disable legacy 8-point sources for clean cylindrical gradient.
    # Legacy sources (octant pos, radius=30) created y-direction asymmetry
    # that dominated the yaw signal and pushed body away from cylinder.
    circuit.world.heat_sources = []

    # Zero-input mechanical signal (thermal + structural only)
    inputs = {ax: 0.0 for ax in ['yaw', 'pitch', 'roll', 'oto_x', 'oto_y', 'oto_z', 'therm']}

    for step in range(1, STEPS + 1):
        circuit.step(inputs, dt=0.001)

        if step % REPORT_INTERVAL == 0:
            body = circuit.world.body
            src = circuit._cylindrical_source
            fill = circuit.energy_store.fill_fraction
            yolk = circuit.yolk_sac.level
            mouth_in = circuit.thermal_mouth.energy_intake
            dist_c = dist_to_cylinder(body, src)
            yaw_deg = math.degrees(body.yaw)

            # Read last patch_temps from somatosensory
            patch_temps = circuit.world.body.sample_skin(circuit.world, 0.001)
            T_f = patch_temps.get("front", (0.15, 0, 0))[0]
            T_l = patch_temps.get("left",  (0.15, 0, 0))[0]
            T_r = patch_temps.get("right", (0.15, 0, 0))[0]

            print(f"{step:>8,} | {fill:>6.3f} | {yolk:>6.1f} | "
                  f"{mouth_in:>9.6f} | {dist_c:>8.2f} | {yaw_deg:>6.1f}d | "
                  f"{T_f:>7.3f} | {T_l:>7.3f} | {T_r:>7.3f}")

    # W9 verification
    fill_final = circuit.energy_store.fill_fraction
    yolk_depleted = circuit.yolk_sac.is_depleted
    mouth_total = circuit.thermal_mouth.energy_intake  # last step's rate
    src_energy_remaining = circuit._cylindrical_source.energy

    print("\n" + "=" * 72)
    print(f"  Final fill_fraction: {fill_final:.4f}")
    print(f"  YolkSac depleted:    {yolk_depleted}")
    print(f"  Last mouth_intake:   {mouth_total:.8f}")
    print(f"  Source energy left:  {src_energy_remaining:.2f}")

    w9_pass = fill_final > 0
    status = "[PASS]" if w9_pass else "[FAIL]"
    print(f"\n  {status} W9: fill_fraction > 0 (={fill_final:.4f})")
    print("=" * 72)
    return w9_pass


if __name__ == "__main__":
    ok = run()
    sys.exit(0 if ok else 1)
