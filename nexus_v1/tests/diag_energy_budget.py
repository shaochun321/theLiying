"""Diagnostic: True energy budget over 20k steps.

Tracks ACTUAL deposit/withdraw/basal per step (not the proxy).
Goal: Determine exact P_in and P_out breakdown to guide parameter tuning.
"""
from __future__ import annotations
import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

import math

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

    STEPS = 20_000
    LOG_EVERY = 2000

    print(f"max_deposit_per_step = {store.config.max_deposit_per_step}")
    print(f"basal_drain = {store.config.basal_drain}")
    print(f"capacity = {store.config.capacity}")
    print(f"deposit_efficiency = {store.config.deposit_efficiency}")
    print()
    print(f"{'Step':>7} | {'fill':>6} {'dist':>6} | "
          f"{'dep_Δ':>8} {'wdraw_Δ':>8} {'basal_Δ':>8} | "
          f"{'net/s':>8} {'dep_util':>8}")
    print("-" * 80)

    prev_dep = store._total_deposited
    prev_wdr = store._total_withdrawn
    prev_bas = store._total_basal_drain

    for step in range(STEPS):
        c.step({}, 1.0)

        if (step + 1) % LOG_EVERY == 0:
            cur_dep = store._total_deposited
            cur_wdr = store._total_withdrawn
            cur_bas = store._total_basal_drain

            d_dep = cur_dep - prev_dep
            d_wdr = cur_wdr - prev_wdr
            d_bas = cur_bas - prev_bas
            net = d_dep - d_wdr - d_bas

            prev_dep = cur_dep
            prev_wdr = cur_wdr
            prev_bas = cur_bas

            # Per step averages
            n = LOG_EVERY
            fill = store.fill_fraction
            pos = c.world.body.position
            dists = [dist3(pos, s.position) for s in c.world.heat_sources if s.alive]
            d_near = min(dists) if dists else float('inf')

            dep_util = (d_dep / n) / store.config.max_deposit_per_step * 100

            print(f"{step+1:>7} | {fill:>6.4f} {d_near:>6.1f} | "
                  f"{d_dep/n:>8.5f} {d_wdr/n:>8.5f} {d_bas/n:>8.5f} | "
                  f"{net/n:>+8.5f} {dep_util:>7.1f}%")

    print()
    print("=== TOTALS ===")
    print(f"  total_deposited:   {store._total_deposited:.4f}")
    print(f"  total_withdrawn:   {store._total_withdrawn:.4f}")
    print(f"  total_basal_drain: {store._total_basal_drain:.4f}")
    print(f"  final_level:       {store._level:.4f}")
    print(f"  avg dep/step:      {store._total_deposited/STEPS:.6f}")
    print(f"  avg wdr/step:      {store._total_withdrawn/STEPS:.6f}")
    print(f"  avg bas/step:      {store._total_basal_drain/STEPS:.6f}")
    print(f"  avg net/step:      {(store._total_deposited - store._total_withdrawn - store._total_basal_drain)/STEPS:+.6f}")
    print(f"  dep_utilization:   {store._total_deposited/STEPS / store.config.max_deposit_per_step * 100:.1f}%")

if __name__ == "__main__":
    run()
