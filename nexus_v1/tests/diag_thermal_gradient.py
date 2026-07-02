"""Phase 1 Validation: Thermal gradient weight divergence (staged).

Stage 3a: 20k steps — fast confirmation of w_front / w_back divergence.
Stage 3b: 50k steps — full validation with weight trajectory logging.

Scenario: Heat source at [70,50,50], body starts at [50,50,50].
The front patch faces +x → closer to heat → higher thermal input.
STDP should drive w_front > w_back (excitatory front → forward motion).

Usage:
    python -m nexus_v1.tests.diag_thermal_gradient
"""
from __future__ import annotations

import sys
import io
import math
import time

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

from nexus_v1.circuit.variant_adapter import VariantCircuit


def find_bundle(circuit, bundle_id_substr):
    """Find a bundle by substring match in its ID."""
    for b in circuit.bundles_col_to_motor:
        if bundle_id_substr in b.id:
            return b
    return None


def get_weight(bundle):
    """Get the first memristor weight from a bundle."""
    if bundle is None:
        return float('nan')
    return bundle._memristors[0][0].w


def run_thermal_gradient(total_steps=20000, log_interval=2000):
    """Run thermal gradient scenario and track weight divergence."""
    print("=" * 70)
    print(f"  THERMAL GRADIENT VALIDATION — {total_steps // 1000}k steps")
    print("=" * 70)

    start = time.time()
    c = VariantCircuit()

    # ── Identify differential pair bundles ──
    b_front_x = find_bundle(c, "therm_front_to_move_x")
    b_back_x  = find_bundle(c, "therm_back_to_move_x")
    b_left_y  = find_bundle(c, "therm_left_to_move_y")
    b_right_y = find_bundle(c, "therm_right_to_move_y")

    if b_front_x is None or b_back_x is None:
        print("ERROR: Differential pair bundles not found!")
        print("Available bundles:")
        for b in c.bundles_col_to_motor:
            print(f"  {b.id}")
        return

    print(f"\nBundle IDs:")
    print(f"  front→move_x: {b_front_x.id} (gain={b_front_x.config.synapse_gain})")
    print(f"  back→move_x:  {b_back_x.id}  (gain={b_back_x.config.synapse_gain})")
    print(f"  left→move_y:  {b_left_y.id if b_left_y else 'N/A'}")
    print(f"  right→move_y: {b_right_y.id if b_right_y else 'N/A'}")

    print(f"\nInitial state:")
    print(f"  Body position: {c.world.body.position}")
    print(f"  Heat sources: {[(s.position, s.effective_temperature()) for s in c.world.heat_sources[:3]]}")
    print(f"  w_front={get_weight(b_front_x):.4f}  w_back={get_weight(b_back_x):.4f}")

    # ── Column header ──
    print(f"\n{'Step':>7} | {'w_front':>8} {'w_back':>8} {'Δw':>8} | "
          f"{'col_f':>6} {'col_b':>6} | "
          f"{'enc_f':>6} {'enc_b':>6} | "
          f"{'pos_x':>7} {'Δx':>6} | "
          f"{'DA':>5} {'fill':>5}")
    print("-" * 105)

    x_start = c.world.body.position[0]

    # ── Main simulation loop ──
    for step in range(total_steps):
        # No explicit oto_x input — thermal gradient scenario only.
        # Body is driven by vital oscillator + hunger approach + spinal reflex.
        c.step({}, 1.0)

        if (step + 1) % log_interval == 0:
            w_f = get_weight(b_front_x)
            w_b = get_weight(b_back_x)
            dw = w_f - w_b

            col_f = c.column_neurons.get('therm_front')
            col_b = c.column_neurons.get('therm_back')
            col_f_ema = col_f._activation_ema if col_f else 0
            col_b_ema = col_b._activation_ema if col_b else 0

            enc_f = c.encoding_neurons.get('reg_therm_front')
            enc_b = c.encoding_neurons.get('reg_therm_back')
            enc_f_ema = enc_f._activation_ema if enc_f else 0
            enc_b_ema = enc_b._activation_ema if enc_b else 0

            pos_x = c.world.body.position[0]
            dx = pos_x - x_start

            da = c.dopamine.concentration
            fill = c.energy_store.fill_fraction

            print(f"{step+1:>7} | {w_f:>8.4f} {w_b:>8.4f} {dw:>+8.4f} | "
                  f"{col_f_ema:>6.3f} {col_b_ema:>6.3f} | "
                  f"{enc_f_ema:>6.3f} {enc_b_ema:>6.3f} | "
                  f"{pos_x:>7.2f} {dx:>+6.2f} | "
                  f"{da:>5.3f} {fill:>5.3f}")

    elapsed = time.time() - start

    # ── Final analysis ──
    w_f_final = get_weight(b_front_x)
    w_b_final = get_weight(b_back_x)
    dw_final = w_f_final - w_b_final

    w_l = get_weight(b_left_y) if b_left_y else float('nan')
    w_r = get_weight(b_right_y) if b_right_y else float('nan')

    pos_final = c.world.body.position
    dx_total = pos_final[0] - x_start

    print(f"\n{'=' * 70}")
    print(f"  FINAL RESULTS — {total_steps // 1000}k steps, {elapsed:.1f}s")
    print(f"{'=' * 70}")

    print(f"\n  Move-X differential pair:")
    print(f"    w_front = {w_f_final:.6f}  (initial 0.1)")
    print(f"    w_back  = {w_b_final:.6f}  (initial 0.1)")
    print(f"    Δw      = {dw_final:+.6f}")

    print(f"\n  Move-Y differential pair:")
    print(f"    w_left  = {w_l:.6f}")
    print(f"    w_right = {w_r:.6f}")
    print(f"    Δw      = {w_l - w_r:+.6f}")

    print(f"\n  Body displacement:")
    print(f"    Δx = {dx_total:+.4f}")
    print(f"    Final position: {[f'{p:.2f}' for p in pos_final]}")

    # ── Pass/fail thresholds ──
    print(f"\n  === STAGE 3a THRESHOLDS ===")
    tests = [
        ("w_front > 0.10",  w_f_final > 0.10,  f"{w_f_final:.4f}"),
        ("w_back  < 0.10",  w_b_final < 0.10,  f"{w_b_final:.4f}"),  
        ("Δw > 0.01",       dw_final > 0.01,   f"{dw_final:+.4f}"),
        ("Δw > 0.03 (3b)",  dw_final > 0.03,   f"{dw_final:+.4f}"),
    ]
    for name, passed, val in tests:
        status = "PASS" if passed else "FAIL"
        print(f"    [{status}] {name}: {val}")

    # ── Encoding/column signal check ──
    col_f = c.column_neurons.get('therm_front')
    col_b = c.column_neurons.get('therm_back')
    enc_f = c.encoding_neurons.get('reg_therm_front')
    enc_b = c.encoding_neurons.get('reg_therm_back')

    print(f"\n  === SIGNAL CHAIN CHECK ===")
    if enc_f and enc_b:
        print(f"    Encoding front: {enc_f._activation_ema:.4f}")
        print(f"    Encoding back:  {enc_b._activation_ema:.4f}")
        print(f"    Enc difference: {enc_f._activation_ema - enc_b._activation_ema:+.4f}")
    if col_f and col_b:
        print(f"    Column front:   {col_f._activation_ema:.4f}")
        print(f"    Column back:    {col_b._activation_ema:.4f}")
        print(f"    Col difference: {col_f._activation_ema - col_b._activation_ema:+.4f}")

    # ── Thermoreceptor check ──
    print(f"\n  === THERMORECEPTOR CHECK ===")
    soma_out = c.somatosensory.get_mechanical_inputs()
    for k in ['therm_front', 'therm_back', 'therm_left', 'therm_right']:
        print(f"    {k}: relay_ema = {soma_out.get(k, 0.0):.4f}")

    print(f"{'=' * 70}")

    return dw_final


if __name__ == "__main__":
    # 对照实验: 100k steps — per 统一执行方案 Section II
    # 不修改模拟代码，仅延伸观测窗口
    dw = run_thermal_gradient(total_steps=100000, log_interval=10000)

    print("\n  === 对照实验判决 (100k) ===")
    if dw > 0.02:
        print(f"  ✅ Δw={dw:+.4f} > 0.02 — 物理系统自稳定，Phase 2 不必要")
        print(f"     → 直接进入 Phase 3（三因子适格迹）")
    elif dw > 0.01:
        print(f"  ⚠️  Δw={dw:+.4f} — 临界状态 (0.01 < Δw < 0.02)")
        print(f"     → 需延长至 150k 步继续观察")
    else:
        print(f"  ❌ Δw={dw:+.4f} < 0.01 — 经典STDP盲目性导致系统失效")
        print(f"     → 执行 Phase 2（异突触竞争）")
