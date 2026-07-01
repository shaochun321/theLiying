"""Thermal pathway probe — 3 scenarios, 30k steps each.

Measures:
  S1: Single source [70,50,50] — patch gradient, relay signal, DA, weights
  S2: Dual source symmetric ([70,50,50] + [30,50,50]) — symmetry breaking
  S3: Dual source asymmetric ([70,50,50] E=10000 + [30,50,50] E=2000) — selection
"""
import sys, math, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

import time
from nexus_v1.circuit.variant_adapter import VariantCircuit
from nexus_v1.components.world import HeatSource, Body, World

STEPS   = 50_000
DT      = 0.001
LOG_INT = 5_000
BODY_RADIUS = 1.0   # same as variant_adapter.py:658


def _make_circuit(heat_sources):
    body = Body(position=[50.0, 50.0, 50.0])
    world = World(heat_sources=heat_sources, body=body)
    world.MIN_ALIVE = 0
    world.REGEN_PROB = 0.0
    c = VariantCircuit()
    c.world = world
    c.somatosensory.LATERAL_GAIN = 0.3
    for m in c.muscle_system.muscles:
        m.gain = 0.3
    # enable soma STDP from step 1
    _stdp_set = False

    def step_with_stdp(sig, _set=None):
        nonlocal _stdp_set
        c.step(sig, dt=DT)
        if not _stdp_set and c.bundles_soma_to_da:
            for b in c.bundles_soma_to_da:
                b.config.stdp_lr = 0.005
            _stdp_set = True

    c._step_with_stdp = step_with_stdp
    return c, body, world


def _patch_temps(c):
    """Return {pid: (T, dT)} from last step."""
    return {pid: c._patch_temps[pid][:2]
            for pid in c.somatosensory.patch_ids}


def _relay_acts(c):
    """Relay neuron activation per patch."""
    return {pid: c.somatosensory.relays[pid]._activation_ema
            for pid in c.somatosensory.patch_ids}


def _soma_weights(c):
    """soma_to_da weight matrix: {patch_id: mean_weight}."""
    if not c.bundles_soma_to_da:
        return {}
    b = c.bundles_soma_to_da[0]
    wm = b.weight_matrix()
    return {pid: sum(wm[i]) / max(len(wm[i]), 1)
            for i, pid in enumerate(c.somatosensory.patch_ids)}


def _da_vmem(c):
    """Mean DA neuron membrane voltage."""
    if hasattr(c, 'da_neurons') and c.da_neurons:
        vals = [n._membrane.voltage for n in c.da_neurons.values()]
        return sum(vals) / len(vals)
    return 0.0


def _da_init_status(c):
    """Return DA circuit init info string."""
    n_da  = len(getattr(c, 'da_neurons', {}))
    n_bnd = len(getattr(c, 'bundles_soma_to_da', []))
    init  = getattr(c, '_da_circuit_initialized', False)
    return f"da_n={n_da} bnd={n_bnd} init={init}"


def _dist_to(body, src):
    return math.sqrt(sum((p - h)**2 for p, h in zip(body.position, src.position)))


def _header(title, heat_sources):
    print()
    print("=" * 68)
    print(f"  {title}")
    for hs in heat_sources:
        print(f"  src@{hs.position}  E={hs.energy}  T={hs.temperature}  r={hs.radius}")
    print("=" * 68)
    print(f"{'step':>6}  {'dist':>6}  {'T_L':>6} {'T_R':>6} {'ΔT_LR':>7}  "
          f"{'rel_L':>7} {'rel_R':>7}  {'DA_v':>7}  {'fill':>6}  "
          f"{'wL':>6} {'wR':>6} {'wF':>6} {'wB':>6}  DA_status")
    print("-" * 115)


def _row(step, c, body, heat_sources):
    pt   = _patch_temps(c)
    ra   = _relay_acts(c)
    ws   = _soma_weights(c)
    da_v = _da_vmem(c)
    fill = c.energy_store.fill_fraction
    dist = _dist_to(body, heat_sources[0])

    T_L   = pt.get("left",  (0.0,0.0))[0]
    T_R   = pt.get("right", (0.0,0.0))[0]
    dT_LR = T_R - T_L
    rel_L = ra.get("left",  0.0)
    rel_R = ra.get("right", 0.0)
    wL = ws.get("left",  0.0)
    wR = ws.get("right", 0.0)
    wF = ws.get("front", 0.0)
    wB = ws.get("back",  0.0)
    da_info = _da_init_status(c)

    print(f"{step:>6}  {dist:>6.2f}  {T_L:>6.4f} {T_R:>6.4f} {dT_LR:>+7.4f}  "
          f"{rel_L:>7.5f} {rel_R:>7.5f}  {da_v:>7.4f}  {fill:>6.4f}  "
          f"{wL:>6.4f} {wR:>6.4f} {wF:>6.4f} {wB:>6.4f}  {da_info}")


def run_scenario(title, heat_sources, steps=STEPS):
    c, body, world = _make_circuit(heat_sources)
    _header(title, heat_sources)

    signal_base = {
        'yaw':   0.0, 'pitch': 0.0, 'roll': 0.0,
        'oto_x': 0.0, 'oto_y': 0.0, 'oto_z': 0.0,
    }

    for step in range(steps):
        t = step * DT
        sig = {
            'yaw':   2.0 * math.sin(1.5 * t),
            'pitch': 1.5 * math.sin(1.0 * t),
            'roll':  1.0 * math.sin(0.7 * t),
            'oto_x': 6.0 * math.sin(2.0 * t),
            'oto_y': 6.0 * math.sin(2.5 * t + 0.3),
            'oto_z': 6.0 * math.sin(3.0 * t + 0.7),
        }
        c._step_with_stdp(sig)

        if step % LOG_INT == 0:
            _row(step, c, body, heat_sources)

    # final row
    _row(steps, c, body, heat_sources)

    # weight summary
    ws = _soma_weights(c)
    print(f"\n  Final weights: L={ws.get('left',0):.4f} R={ws.get('right',0):.4f} "
          f"F={ws.get('front',0):.4f} B={ws.get('back',0):.4f}")
    dom = max(ws, key=ws.get) if ws else "?"
    print(f"  Dominant patch: {dom}  (max_w={max(ws.values(),default=0):.4f})")

    # gradient detectability at body center at start
    pos0 = [50.0, 50.0, 50.0]
    T_R0 = world.temperature_at([pos0[0]+BODY_RADIUS, pos0[1], pos0[2]])
    T_L0 = world.temperature_at([pos0[0]-BODY_RADIUS, pos0[1], pos0[2]])
    print(f"  T_right@init={T_R0:.4f}  T_left@init={T_L0:.4f}  "
          f"ΔT_init={T_R0-T_L0:+.4f}")


# ─── Scenario 1: Single source ────────────────────────────────────────────────
src1 = HeatSource(position=[70.0, 50.0, 50.0], energy=10_000.0,
                  temperature=5.0, radius=30.0)
src1._drift = [0.0, 0.0, 0.0]
run_scenario("S1: Single source [70,50,50]  E=10000", [src1])

# ─── Scenario 2: Dual source, symmetric ───────────────────────────────────────
src2a = HeatSource(position=[70.0, 50.0, 50.0], energy=10_000.0,
                   temperature=5.0, radius=30.0)
src2b = HeatSource(position=[30.0, 50.0, 50.0], energy=10_000.0,
                   temperature=5.0, radius=30.0)
src2a._drift = [0.0, 0.0, 0.0]
src2b._drift = [0.0, 0.0, 0.0]
run_scenario("S2: Dual symmetric  [70,50,50]+[30,50,50]  E=10000+10000",
             [src2a, src2b])

# ─── Scenario 3: Dual source, asymmetric ──────────────────────────────────────
src3a = HeatSource(position=[70.0, 50.0, 50.0], energy=10_000.0,
                   temperature=5.0, radius=30.0)
src3b = HeatSource(position=[30.0, 50.0, 50.0], energy=2_000.0,
                   temperature=5.0, radius=30.0)
src3a._drift = [0.0, 0.0, 0.0]
src3b._drift = [0.0, 0.0, 0.0]
run_scenario("S3: Dual asymmetric [70,50,50]+[30,50,50]  E=10000+2000",
             [src3a, src3b])
