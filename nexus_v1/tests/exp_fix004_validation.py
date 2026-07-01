"""FIX-004 验证实验 — slow_relay τ 生物锚定后的 DA 动力学确认

实验目标（单变量控制：仅 τ 改变，环境同 exp_dual_source_long_run.py）：
  1. slow_relay 超调恢复：slow_relay.vmem / relay.act ≤ 3× at 100k步
  2. 方向学习保持：wR-wL > 0.005 at 50k步后
  3. DA 波形质量：DA phasic（非 tonic 饱和）

设计：
  - 200k 步（旧双热源环境，src1 右，src2 背）
  - 每 10k 步记录 slow_relay.vmem / relay.act 比值
  - 验收在 100k 步时完成（可提前停止）

BIO REF: Duclaux & Kenshalo 1980 — SA-II τ_bio=15s → capacitance=15.0
"""
import sys, math, os, time
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from nexus_v1.circuit.variant_adapter import VariantCircuit
from nexus_v1.components.world import HeatSource, Body, World

STEPS = 200_000
DT = 0.001
LOG_INTERVAL = 10_000
ACCEPT_STEP = 100_000   # acceptance check at this step

# Identical to exp_dual_source_long_run.py — single-variable control
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


def _relay_slow_ratio(c):
    """Returns dict pid → (relay.act, slow_relay.vmem, ratio).
    Iterates over _slow_relays.keys() to avoid KeyError on patches without slow relay.
    """
    if not hasattr(c, '_slow_relays'):
        return {}
    result = {}
    for pid, sr in c._slow_relays.items():
        rl = c.somatosensory.relays.get(pid)
        if rl is None:
            continue
        relay_act = rl.activation
        sr_vmem = sr._membrane.voltage
        ratio = abs(sr_vmem) / max(abs(relay_act), 1e-9)
        result[pid] = (relay_act, sr_vmem, ratio)
    return result


print("=" * 72)
print("FIX-004 验证：slow_relay τ=15k (bio) vs τ=300k (old)")
print(f"单变量控制：仅 capacitance 改变，环境同双热源实验")
print(f"BIO: SA-II τ_bio=15s → capacitance=15.0 (Duclaux & Kenshalo 1980)")
print("=" * 72)
print(f"src1={src1.position} (RIGHT)  src2={src2.position} (BACK)")
print()

hdr = (f"{'step':>6}  {'wL':>6} {'wR':>6}  {'wR-wL':>7}  {'DA':>6}  "
       f"{'sr_R/rl_R':>10} {'sr_L/rl_L':>10}  {'max_ratio':>9}  OK?")
print(hdr)
print("-" * len(hdr))

ratio_history = []
accept_100k = None
t0 = time.time()

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
        ws = _get_weights(c)
        da_v = _da_vmem(c)
        ratios = _relay_slow_ratio(c)

        wdiff = ws.get('right', 0) - ws.get('left', 0)
        sr_r, rl_r, ratio_r = ratios.get('right', (0, 0, 0))
        sr_l, rl_l, ratio_l = ratios.get('left', (0, 0, 0))
        max_ratio = max(r[2] for r in ratios.values()) if ratios else 0

        ratio_ok = max_ratio <= 3.0
        wdir_ok = wdiff > 0.005 if step >= 50_000 else True  # N/A before 50k

        elapsed = time.time() - t0
        row = (f"{step:>6}  {ws.get('left',0):>6.4f} {ws.get('right',0):>6.4f}  "
               f"{wdiff:>+7.4f}  {da_v:>6.4f}  "
               f"{ratio_r:>10.3f} {ratio_l:>10.3f}  "
               f"{max_ratio:>9.3f}  "
               f"{'✓' if ratio_ok else '✗'}  ({elapsed:.0f}s)")
        print(row)
        ratio_history.append({'step': step, 'max_ratio': max_ratio,
                               'wdiff': wdiff, 'da': da_v})

        # Acceptance check at 100k
        if step == ACCEPT_STEP:
            ratio_pass = max_ratio <= 3.0
            wdir_pass = wdiff > 0.005
            accept_100k = {
                'ratio_pass': ratio_pass,
                'ratio_value': max_ratio,
                'wdir_pass': wdir_pass,
                'wdir_value': wdiff,
                'da': da_v,
            }

elapsed_total = time.time() - t0
print(f"\nDone: {STEPS:,} steps in {elapsed_total:.1f}s")

# ── 验收判定 ──────────────────────────────────────────────────────────────────
print("\n" + "=" * 72)
print("FIX-004 验收判定")
print("=" * 72)

ws_f = _get_weights(c)
ratios_f = _relay_slow_ratio(c)
wdiff_f = ws_f.get('right', 0) - ws_f.get('left', 0)
max_ratio_f = max(r[2] for r in ratios_f.values()) if ratios_f else 0
da_f = _da_vmem(c)

print(f"\n最终状态（step {STEPS:,}）：")
for pid in sorted(ratios_f.keys()):
    rl_a, sr_v, ratio = ratios_f[pid]
    print(f"  {pid:8s}: relay.act={rl_a:.5f}  slow_relay.vmem={sr_v:.4f}  ratio={ratio:.2f}×")

print(f"\n验收标准（100k 步时）：")
if accept_100k:
    c1 = accept_100k['ratio_pass']
    c2 = accept_100k['wdir_pass']
    print(f"  [{'PASS' if c1 else 'FAIL'}] ① slow_relay/relay.act ≤ 3×  "
          f"(实测 {accept_100k['ratio_value']:.2f}×)")
    print(f"  [{'PASS' if c2 else 'FAIL'}] ② wR-wL > 0.005  "
          f"(实测 {accept_100k['wdir_value']:+.4f})")
    passed_100k = c1 and c2
else:
    passed_100k = False
    print("  [FAIL] 100k 步检查点未到达")

c3 = max_ratio_f <= 3.0
c4 = wdiff_f > 0.005
print(f"\n最终状态（step {STEPS:,}）：")
print(f"  [{'PASS' if c3 else 'FAIL'}] ① slow_relay/relay.act ≤ 3×  (实测 {max_ratio_f:.2f}×)")
print(f"  [{'PASS' if c4 else 'FAIL'}] ② wR-wL > 0.005  (实测 {wdiff_f:+.4f})")
print(f"  DA 最终值 = {da_f:.4f}")

# Ratio trajectory summary
print("\n超调比率轨迹（max across patches）：")
for r in ratio_history:
    bar_len = int(min(r['max_ratio'] * 4, 20))
    bar = '▓' * bar_len
    ok = '✓' if r['max_ratio'] <= 3.0 else '✗'
    print(f"  step {r['step']:>6d}: ratio={r['max_ratio']:>5.2f}×  wR-wL={r['wdiff']:>+.4f}  {ok}{bar}")

final_pass = passed_100k and c3 and c4
print(f"\n{'='*72}")
print(f"VERDICT: {'FIX-004 PASS — DA 超调消除，方向学习保持' if final_pass else 'FIX-004 FAIL — 见上述指标'}")
print("=" * 72)
sys.exit(0 if final_pass else 1)
