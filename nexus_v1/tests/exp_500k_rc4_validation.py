"""500k long-run validation: RC-4 directional learning persistence.

Checks whether wR > wL (correct: src1 at right) is preserved throughout
the full 500k lifecycle, even as slow_relay charges toward equilibrium.

Key concern: at τ_slow = 300k steps:
  - step 300k: slow_relay ≈ 63% of relay.act  → net DA ∝ 37% of relay
  - step 500k: slow_relay ≈ 81% of relay.act  → net DA ∝ 19% of relay

If DA → tonic again (slow_relay converges), STDP decay dominates and
weights may collapse symmetrically. This experiment tests that concern.

Same setup as Phase 8 (RC-1 layout: src1=[70,50,50] right, src2=[50,50,30] back).
"""
import sys, math, os, time
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from nexus_v1.circuit.variant_adapter import VariantCircuit
from nexus_v1.components.world import HeatSource, Body, World

STEPS = 500_000
DT = 0.001
LOG_INTERVAL = 50_000

# ── Heat sources (RC-1 non-symmetric layout) ──────────────────────────────────
src1 = HeatSource(position=[70.0, 50.0, 50.0], energy=10_000.0,
                  temperature=5.0, radius=30.0)
src2 = HeatSource(position=[50.0, 50.0, 30.0], energy=10_000.0,
                  temperature=5.0, radius=30.0)
src1._drift = [0.0, 0.0, 0.0]
src2._drift = [0.0, 0.0, 0.0]

body = Body(position=[50.0, 50.0, 50.0])
world = World(heat_sources=[src1, src2], body=body)
world.MIN_ALIVE = 0
world.REGEN_PROB = 0.0

c = VariantCircuit()
c.world = world
c.somatosensory.LATERAL_GAIN = 0.3
for m in c.muscle_system.muscles:
    m.gain = 0.3

_stdp_applied = False


def _get_weights(c):
    if not c.bundles_soma_to_da:
        return {}
    b = c.bundles_soma_to_da[0]
    wm = b.weight_matrix()
    return {pid: sum(wm[i]) / max(len(wm[i]), 1)
            for i, pid in enumerate(c.somatosensory.patch_ids)}


def _da_vmem(c):
    if hasattr(c, 'da_neurons') and c.da_neurons:
        vals = [n._membrane.voltage for n in c.da_neurons.values()]
        return sum(vals) / len(vals)
    return 0.0


def _slow_relay_state(c):
    if not hasattr(c, '_slow_relays') or not c._slow_relays:
        return {}
    return {pid: (n._membrane.voltage, n.activation)
            for pid, n in c._slow_relays.items()}


def _relay_state(c):
    if not hasattr(c, 'somatosensory') or not c.somatosensory.relays:
        return {}
    return {pid: (n._membrane.voltage, n.activation)
            for pid, n in c.somatosensory.relays.items()}


print("=" * 76)
print("500k RC-4 Long-run Validation: directional learning persistence")
print("=" * 76)
print(f"src1={src1.position} (RIGHT)  src2={src2.position} (BACK)")
print(f"τ_slow=300k steps; at 500k slow_relay ≈ 81% equilibrium")
print(f"Expected: wR>wL and wB>wF throughout; DA remains phasic or stable")
print()
hdr = (f"{'step':>6}  {'dst1':>6} {'dst2':>6}  {'wL':>6} {'wR':>6} {'wF':>6} {'wB':>6}  "
       f"{'ΔwLR':>7} {'ΔwFB':>7}  {'DA':>6}  "
       f"{'sr_R.v':>7} {'sr_L.v':>7}  {'rl_R.a':>7} {'rl_L.a':>7}")
print(hdr)
print("-" * len(hdr))

trajectory = []
t0 = time.time()
dist_s1_init = math.sqrt(sum((p-h)**2 for p,h in zip(body.position, src1.position)))
dist_s2_init = math.sqrt(sum((p-h)**2 for p,h in zip(body.position, src2.position)))

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

    if not _stdp_applied and step >= 1 and c.bundles_soma_to_da:
        for b in c.bundles_soma_to_da:
            b.config.stdp_lr = 0.005
        _stdp_applied = True

    if step % LOG_INTERVAL == 0:
        pos = list(c.world.body.position)
        d1 = math.sqrt(sum((p-h)**2 for p,h in zip(pos, src1.position)))
        d2 = math.sqrt(sum((p-h)**2 for p,h in zip(pos, src2.position)))
        ws = _get_weights(c)
        da_v = _da_vmem(c)
        sr = _slow_relay_state(c)
        rl = _relay_state(c)

        wdiff_lr = ws.get('right', 0) - ws.get('left', 0)
        wdiff_fb = ws.get('back', 0) - ws.get('front', 0)

        sr_r_v = sr.get('right', (0, 0))[0]
        sr_l_v = sr.get('left',  (0, 0))[0]
        rl_r_a = rl.get('right', (0, 0))[1]
        rl_l_a = rl.get('left',  (0, 0))[1]

        elapsed = time.time() - t0
        row = (f"{step:>6}  {d1:>6.3f} {d2:>6.3f}  "
               f"{ws.get('left',0):>6.4f} {ws.get('right',0):>6.4f} "
               f"{ws.get('front',0):>6.4f} {ws.get('back',0):>6.4f}  "
               f"{wdiff_lr:>+7.4f} {wdiff_fb:>+7.4f}  "
               f"{da_v:>6.4f}  "
               f"{sr_r_v:>7.4f} {sr_l_v:>7.4f}  "
               f"{rl_r_a:>7.5f} {rl_l_a:>7.5f}  ({elapsed:.0f}s)")
        print(row)
        trajectory.append({
            'step': step, 'd1': d1, 'd2': d2,
            'wL': ws.get('left', 0), 'wR': ws.get('right', 0),
            'wF': ws.get('front', 0), 'wB': ws.get('back', 0),
            'wdiff_lr': wdiff_lr, 'wdiff_fb': wdiff_fb,
            'da_v': da_v,
            'sr_right_v': sr_r_v, 'sr_left_v': sr_l_v,
            'relay_right_a': rl_r_a, 'relay_left_a': rl_l_a,
        })

elapsed_total = time.time() - t0
print(f"\nDone: {STEPS:,} steps in {elapsed_total:.1f}s ({STEPS/elapsed_total:.0f} steps/s)")

# ── Final analysis ─────────────────────────────────────────────────────────────
ws_f = _get_weights(c)
wdiff_lr_f = ws_f.get('right', 0) - ws_f.get('left', 0)
wdiff_fb_f = ws_f.get('back', 0) - ws_f.get('front', 0)

sr_f = _slow_relay_state(c)
rl_f = _relay_state(c)

print("\n" + "=" * 76)
print("VALIDATION RESULTS")
print("=" * 76)
print(f"\nFinal weights (step {STEPS:,}):")
for pid in c.somatosensory.patch_ids:
    sr_v = sr_f.get(pid, (0, 0))[0]
    rl_a = rl_f.get(pid, (0, 0))[1]
    print(f"  {pid:8s}: w={ws_f.get(pid,0):.4f}  relay.act={rl_a:.5f}  slow_relay.vmem={sr_v:.4f}  "
          f"ratio={sr_v/max(rl_a,1e-9):.2f}×")

print(f"\nDirection asymmetry:")
dir_ok_lr = wdiff_lr_f > 0.005
dir_ok_fb = wdiff_fb_f > 0.005
print(f"  wR-wL = {wdiff_lr_f:+.4f}  {'CORRECT (wR>wL, src1 right)' if wdiff_lr_f > 0 else 'WRONG'} "
      f"  {'PASS' if dir_ok_lr else 'FAIL'} (>0.005 threshold)")
print(f"  wB-wF = {wdiff_fb_f:+.4f}  {'CORRECT (wB>wF, src2 back)' if wdiff_fb_f > 0 else 'WRONG'} "
      f"  {'PASS' if dir_ok_fb else 'FAIL'} (>0.005 threshold)")

# slow_relay saturation check
print(f"\nSlow relay saturation at {STEPS:,} steps:")
print(f"  theoretical: 1 - exp(-{STEPS}/{300_000}) = {1 - math.exp(-STEPS/300_000):.3f}× equilibrium")
for pid in c.somatosensory.patch_ids:
    sr_v = sr_f.get(pid, (0, 0))[0]
    rl_a = rl_f.get(pid, (0, 0))[1]
    expected_v_ss = rl_a  # V_ss = relay.act × r_leak=1.0
    saturation = sr_v / max(expected_v_ss, 1e-9)
    print(f"  {pid:8s}: slow_relay.vmem={sr_v:.4f}  V_ss_expected≈{expected_v_ss:.4f}  sat={saturation:.2%}")

# direction persistence trajectory
print(f"\nDirection persistence (wR-wL across all checkpoints):")
for r in trajectory:
    sign = '+' if r['wdiff_lr'] > 0 else '-'
    bar = '▓' * int(abs(r['wdiff_lr']) * 200)
    print(f"  step {r['step']:>6d}: wR-wL={r['wdiff_lr']:+.4f} {sign}{bar}")

passed = dir_ok_lr and dir_ok_fb
print(f"\n{'='*76}")
print(f"VERDICT: {'PASS — directional learning persists to 500k' if passed else 'FAIL — direction lost'}")
print('='*76)

sys.exit(0 if passed else 1)
