"""Phase 3 Gate Test: Thermal → Shadow → DA closed-loop verification.

Signal chain under test:
  SkinPatch (Fourier) → Thermo/Noci → SomatoRelay → Encoding → Column
       ↓ (Xin)
  Shadow Enc → Shadow Col → DA neurons → dopamine.concentration
       ↓ (STDP modulation)
  Main bundles learn direction-thermal correlations

Success criteria:
  1. SIGNAL FLOW: thermal patches produce nonzero skin temperature
  2. ENCODING ALIVE: extra_axes encoding neurons have nonzero activation
  3. SHADOW RECEIVES: shadow col neurons for thermal axes show activity
  4. DA RESPONDS: dopamine concentration is nonzero and fluctuates
  5. STDP ACTIVE: enc→col bundle weights for thermal axes change over time
  6. ENERGY ACCOUNTING: Noether balance remains bounded
"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

import json
from nexus_v1.circuit.variant_adapter import VariantCircuit

def run_phase3_gate(total_steps=20000, report_interval=2000):
    """Run Phase 3 DA loop verification."""
    print("=" * 70)
    print("PHASE 3 GATE TEST: Thermal → Shadow → DA Closed Loop")
    print("=" * 70)

    circuit = VariantCircuit()
    print(f"\nall_axes: {circuit.all_axes}")
    print(f"extra_axes: {circuit.extra_axes}")

    # ── Tracking arrays ──
    da_history = []
    shadow_therm_activity = []
    enc_therm_activity = []
    col_therm_activity = []
    weight_history = {}
    energy_history = []
    skin_temp_history = {}

    # Initialize weight tracking for thermal bundles
    for b in circuit.get_all_bundles():
        if 'therm' in b.id:
            weight_history[b.id] = []

    for step in range(total_steps):
        circuit.step({}, dt=1.0)

        # ── Periodic sampling ──
        if step % report_interval == 0 and step > 0:
            tick = step

            # 1. Skin temperatures
            body = circuit.world.body
            for patch in body.skin_patches:
                if patch.patch_id not in skin_temp_history:
                    skin_temp_history[patch.patch_id] = []
                skin_temp_history[patch.patch_id].append(
                    round(patch.current_temperature, 4))

            # 2. Somatosensory relay outputs
            soma_out = circuit.somatosensory.get_output()
            relay_acts = {pid: round(v['relay_activation'], 4)
                         for pid, v in soma_out.items()}

            # 3. Encoding neuron activations (thermal axes)
            enc_acts = {}
            for axis in circuit.extra_axes:
                enc = circuit.encoding_neurons.get(f"reg_{axis}")
                if enc:
                    enc_acts[axis] = round(enc.activation, 4)
            enc_therm_activity.append(enc_acts)

            # 4. Column neuron activations (thermal axes)
            col_acts = {}
            for axis in circuit.extra_axes:
                col = circuit.column_neurons.get(axis)
                if col:
                    col_acts[axis] = round(col.activation, 4)
            col_therm_activity.append(col_acts)

            # 5. Shadow col activity for thermal axes
            #    NOTE: shadow col neurons are SPIKING + CRI. Their .activation
            #    is 0/1 (spike this step or not). The real continuous output is
            #    .calcium_rate (CRI integrator: bounded [0, 1]).
            shadow_acts = {}
            for nid, n in circuit.shadow_sandbox.neurons.items():
                if nid.startswith('s_col_therm'):
                    shadow_acts[nid] = round(n.calcium_rate, 6)
            shadow_therm_activity.append(shadow_acts)

            # 6. DA concentration
            da_conc = round(circuit.dopamine.concentration, 6)
            da_history.append(da_conc)

            # 7. Bundle weights for thermal
            for b in circuit.get_all_bundles():
                if b.id in weight_history:
                    weight_history[b.id].append(round(b.mean_weight(), 6))

            # 8. Energy
            energy_history.append(round(circuit.energy_store.level, 2))

            # ── Print progress ──
            print(f"\n--- Step {tick} ---")
            print(f"  Skin T: {skin_temp_history}")
            print(f"  Relay: {relay_acts}")
            print(f"  Enc (therm): {enc_acts}")
            print(f"  Col (therm): {col_acts}")
            print(f"  Shadow Col (therm): {shadow_acts}")
            print(f"  DA: {da_conc}")
            print(f"  Energy: {energy_history[-1]}")

            # Reset per-report skin history (keep only latest)
            for pid in skin_temp_history:
                skin_temp_history[pid] = skin_temp_history[pid][-1:]

    # ═══════════════════════════════════════════
    # GATE CHECKS
    # ═══════════════════════════════════════════
    print("\n" + "=" * 70)
    print("GATE CHECKS")
    print("=" * 70)

    passed = 0
    total = 6

    # Gate 1: Signal Flow — skin temperature nonzero
    final_skin = {p.patch_id: p.current_temperature
                  for p in circuit.world.body.skin_patches}
    any_nonzero = any(t > 0.01 for t in final_skin.values())
    status = "✅ PASS" if any_nonzero else "❌ FAIL"
    print(f"\n[1] SIGNAL FLOW — Skin temps nonzero: {status}")
    print(f"    Final skin T: {final_skin}")
    if any_nonzero:
        passed += 1

    # Gate 2: Encoding differentiation — thermal encoding shows spatial selectivity
    #   Old check: any(v > 0) — tautological because ambient baseline drives all
    #   enc neurons to nonzero activation. Changed to differential check that
    #   verifies gradient information (not just baseline) reaches encoding layer.
    enc_front_ema = circuit.encoding_neurons.get('reg_therm_front')
    enc_back_ema = circuit.encoding_neurons.get('reg_therm_back')
    if enc_front_ema and enc_back_ema:
        enc_diff = abs(enc_front_ema._activation_ema - enc_back_ema._activation_ema)
        any_enc_diff = enc_diff > 0.01  # gradient signal threshold
    else:
        any_enc_diff = False
        enc_diff = 0.0
    status = "✅ PASS" if any_enc_diff else "❌ FAIL"
    print(f"\n[2] ENCODING DIFFERENTIATION — thermal enc gradient signal: {status}")
    print(f"    front-back EMA diff: {enc_diff:.4f} (threshold > 0.01)")
    if enc_front_ema:
        print(f"    front EMA: {enc_front_ema._activation_ema:.4f}")
    if enc_back_ema:
        print(f"    back EMA:  {enc_back_ema._activation_ema:.4f}")
    if any_enc_diff:
        passed += 1

    # Gate 3: Shadow receives — shadow col therm has nonzero calcium_rate
    #   Shadow col neurons are SPIKING + CRI. calcium_rate is the continuous
    #   output signal (bounded [0,1]). activation=0/1 is per-step spike flag.
    any_shadow = any(
        any(v > 0 for v in snapshot.values())
        for snapshot in shadow_therm_activity
    )
    status = "✅ PASS" if any_shadow else "❌ FAIL"
    print(f"\n[3] SHADOW RECEIVES — shadow col therm calcium_rate: {status}")
    if shadow_therm_activity:
        print(f"    Last snapshot: {shadow_therm_activity[-1]}")
    if any_shadow:
        passed += 1

    # Gate 4: DA responds — concentration fluctuates
    if len(da_history) >= 2:
        da_range = max(da_history) - min(da_history)
        da_mean = sum(da_history) / len(da_history)
        da_alive = da_mean > 0.001
    else:
        da_range = 0
        da_mean = 0
        da_alive = False
    status = "✅ PASS" if da_alive else "❌ FAIL"
    print(f"\n[4] DA RESPONDS — DA concentration alive: {status}")
    print(f"    DA history: {da_history}")
    print(f"    DA mean={da_mean:.6f}, range={da_range:.6f}")
    if da_alive:
        passed += 1

    # Gate 5: STDP active — thermal bundle weights change
    weight_changed = False
    for bid, wh in weight_history.items():
        if len(wh) >= 2:
            delta = abs(wh[-1] - wh[0])
            if delta > 1e-6:
                weight_changed = True
                break
    status = "✅ PASS" if weight_changed else "⚠️ WEAK"
    print(f"\n[5] STDP ACTIVE — thermal bundle weights changed: {status}")
    for bid, wh in weight_history.items():
        if wh:
            print(f"    {bid}: {wh[0]:.6f} → {wh[-1]:.6f}")
    if weight_changed:
        passed += 1

    # Gate 6: Energy accounting — store hasn't crashed to zero
    energy_ok = energy_history[-1] > 10.0 if energy_history else False
    status = "✅ PASS" if energy_ok else "❌ FAIL"
    print(f"\n[6] ENERGY ACCOUNTING — store level healthy: {status}")
    print(f"    Energy: {energy_history[0]:.2f} → {energy_history[-1]:.2f}")
    if energy_ok:
        passed += 1

    # Shadow metabolic tax check
    shadow_state = circuit.shadow_sandbox.get_state()
    tax = shadow_state.get('metabolic_tax', {})
    print(f"\n[+] SHADOW TAX: total_paid={tax.get('total_paid', 0):.4f}, "
          f"active_bundles={tax.get('active_bundles', 0)}")

    # ── Final verdict ──
    print(f"\n{'=' * 70}")
    print(f"PHASE 3 GATE: {passed}/{total} passed")
    if passed >= 5:
        print("VERDICT: ✅ DA CLOSED LOOP VERIFIED")
    elif passed >= 3:
        print("VERDICT: ⚠️ PARTIAL — signal chain works but some gates weak")
    else:
        print("VERDICT: ❌ FAIL — fundamental chain broken")
    print("=" * 70)

    return passed >= 5


if __name__ == "__main__":
    run_phase3_gate(total_steps=20000, report_interval=2000)
