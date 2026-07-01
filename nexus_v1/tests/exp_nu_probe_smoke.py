"""ν probe smoke test — 5k steps, verifies NuProbe computes ν for all bundles.

Checks:
  1. NuProbe imports cleanly from nexus_v1.ledger
  2. update() runs without error each step
  3. At least N_BUNDLES_MIN bundles tracked
  4. system_nu is finite (no NaN/Inf)
  5. charging_fraction ∈ [0, 1]
  6. format_report() produces non-empty string
  7. Per-bundle ν EMA stabilizes (last 1k vs first 1k not all-zero)
"""
import sys, math, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from nexus_v1.circuit.variant_adapter import VariantCircuit
from nexus_v1.components.world import HeatSource, Body, World
from nexus_v1.ledger import NuProbe

STEPS = 5_000
DT = 0.001
REPORT_EVERY = 1_000
N_BUNDLES_MIN = 10

# ── Minimal heat source setup ────────────────────────────────────────────────
src = HeatSource(position=[70.0, 50.0, 50.0], energy=10_000.0,
                 temperature=5.0, radius=30.0)
src._drift = [0.0, 0.0, 0.0]
body = Body(position=[50.0, 50.0, 50.0])
world = World(heat_sources=[src], body=body)
world.MIN_ALIVE = 0
world.REGEN_PROB = 0.0

c = VariantCircuit()
c.world = world
c.somatosensory.LATERAL_GAIN = 0.3

probe = NuProbe(ema_alpha=0.001)

print("=" * 60)
print("NuProbe smoke test — 5k steps")
print("=" * 60)

for step in range(STEPS):
    t = step * DT
    signal = {
        'yaw':   2.0 * math.sin(1.5 * t),
        'pitch': 1.5 * math.sin(1.0 * t),
        'roll':  1.0 * math.sin(0.7 * t),
        'oto_x': 6.0 * math.sin(2.0 * t),
        'oto_y': 6.0 * math.sin(2.5 * t + 0.3),
        'oto_z': 6.0 * math.sin(3.0 * t + 0.7),
    }
    c.step(signal, dt=DT)
    probe.update(c, step, dt=DT)

    if step > 0 and step % REPORT_EVERY == 0:
        r = probe.report(step)
        print(f"\n[step {step}]")
        print(probe.format_report(r, top_n=5))
        print(f"  system_nu_ema={probe.system_nu_ema:+.5f}  "
              f"charging_fraction={probe.charging_fraction:.2%}")

# ── Final checks ────────────────────────────────────────────────────────────
print("\n" + "=" * 60)
print("CHECKS")
print("=" * 60)

n_bundles = len(probe._nu_ema)
sys_nu = probe.system_nu_ema
cf = probe.charging_fraction

checks = {
    f"bundles tracked ≥ {N_BUNDLES_MIN}": n_bundles >= N_BUNDLES_MIN,
    "system_nu finite":                   math.isfinite(sys_nu),
    "no NaN in ν EMA":                    all(math.isfinite(v) for v in probe._nu_ema.values()),
    "charging_fraction ∈ [0,1]":          0.0 <= cf <= 1.0,
    "format_report non-empty":            len(probe.format_report(probe.report(STEPS))) > 20,
    "any non-zero ν EMA":                 any(abs(v) > 1e-12 for v in probe._nu_ema.values()),
}

all_pass = True
for desc, result in checks.items():
    mark = "PASS" if result else "FAIL"
    print(f"  [{mark}] {desc}")
    if not result:
        all_pass = False

print(f"\n  n_bundles={n_bundles}  system_nu={sys_nu:+.5f}  charging={cf:.2%}")
print(f"\n{'PASS — NuProbe operational' if all_pass else 'FAIL — see above'}")
sys.exit(0 if all_pass else 1)
