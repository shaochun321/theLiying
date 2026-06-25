"""Diagnostic: Itemized energy drain per withdraw source.

Wraps EnergyStore.withdraw() to attribute each call to its caller.
"""
from __future__ import annotations
import sys, io, math, traceback
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

def dist3(a, b, size=100.0):
    total = 0.0
    for x, y in zip(a, b):
        d = abs(x - y)
        if d > size * 0.5:
            d = size - d
        total += d * d
    return math.sqrt(total)

def run():
    from nexus_v1.circuit.variant_adapter import VariantCircuit
    c = VariantCircuit()
    store = c.energy_store

    STEPS = 10_000
    LOG_EVERY = 2000

    # Patch withdraw to track callers
    drain_buckets = {}
    _original_withdraw = store.withdraw.__func__

    def tracked_withdraw(self_store, requested):
        # Identify caller
        frame = traceback.extract_stack(limit=3)
        caller = f"{frame[-2].filename.split('/')[-1].split(chr(92))[-1]}:{frame[-2].lineno}"
        if caller not in drain_buckets:
            drain_buckets[caller] = 0.0
        actual = _original_withdraw(self_store, requested)
        drain_buckets[caller] += actual
        return actual

    import types
    store.withdraw = types.MethodType(tracked_withdraw, store)

    print(f"max_deposit={store.config.max_deposit_per_step}, "
          f"basal={store.config.basal_drain}")
    print()
    print(f"{'Step':>7} | {'fill':>6} {'dist':>6} | "
          f"{'dep_Δ':>8} {'wdr_tot':>8} {'basal':>8} | "
          f"{'net/s':>8}")
    print("-" * 72)

    prev_dep = store._total_deposited
    prev_wdr = store._total_withdrawn
    prev_bas = store._total_basal_drain
    prev_buckets = {}

    for step in range(STEPS):
        c.step({}, 1.0)

        if (step + 1) % LOG_EVERY == 0:
            cur_dep = store._total_deposited
            cur_wdr = store._total_withdrawn
            cur_bas = store._total_basal_drain
            n = LOG_EVERY

            d_dep = (cur_dep - prev_dep) / n
            d_wdr = (cur_wdr - prev_wdr) / n
            d_bas = (cur_bas - prev_bas) / n
            net = d_dep - d_wdr - d_bas

            fill = store.fill_fraction
            pos = c.world.body.position
            dists = [dist3(pos, s.position) for s in c.world.heat_sources if s.alive]
            d_near = min(dists) if dists else float('inf')

            print(f"{step+1:>7} | {fill:>6.4f} {d_near:>6.1f} | "
                  f"{d_dep:>8.5f} {d_wdr:>8.5f} {d_bas:>8.5f} | "
                  f"{net:>+8.5f}")

            # Bucket breakdown
            for caller, total in sorted(drain_buckets.items(),
                                        key=lambda x: -x[1]):
                prev = prev_buckets.get(caller, 0.0)
                delta = (total - prev) / n
                if delta > 1e-7:
                    short = caller.split(':')[0]
                    line = caller.split(':')[1] if ':' in caller else '?'
                    print(f"         -> {short}:{line:>5}  {delta:>8.5f}/step")
                prev_buckets[caller] = total

            prev_dep = cur_dep
            prev_wdr = cur_wdr
            prev_bas = cur_bas

    # Final summary
    print(f"\n=== DRAIN BREAKDOWN (total over {STEPS} steps) ===")
    for caller, total in sorted(drain_buckets.items(), key=lambda x: -x[1]):
        print(f"  {caller:>45}:  {total:.4f}  ({total/STEPS:.5f}/step)")
    print(f"\n  basal_drain:  {store._total_basal_drain:.4f}")
    print(f"  total_deposited: {store._total_deposited:.4f}")
    print(f"  total_withdrawn: {store._total_withdrawn:.4f}")
    print(f"  final_level: {store._level:.4f}")

if __name__ == "__main__":
    run()
