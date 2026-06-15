"""Deep signal trace: track Xin -> enc -> col propagation in shadow."""
import sys, os
sys.path.insert(0, '.')
os.environ['PYTHONIOENCODING'] = 'utf-8'

from nexus_v1.circuit.variant_adapter import VariantCircuit

circuit = VariantCircuit()

# Run 20000 steps with strong differentiated input
print("Running 20000 steps with strong input...")
for t in range(20000):
    if (t // 500) % 2 == 0:
        inputs = {'yaw': 0.5, 'pitch': 0.05, 'roll': 0.02}
    else:
        inputs = {'yaw': 0.05, 'pitch': 0.5, 'roll': 0.02}
    circuit.step(inputs, dt=0.001)

    # Print every 2000 steps
    if t % 2000 == 0 and t > 0:
        sb = circuit.shadow_sandbox
        print(f"\n--- tick={t} ---")

        # Xin values from main bundles
        print("  Main bundle Xin tensions:")
        for b in circuit.get_all_bundles():
            if sb._xin_routing.get(b.id):
                print(f"    {b.id:<25s}: xin={b.config.xin_tension:>+10.6f}")

        # Accumulated currents for key neurons
        print("  Shadow encoding activations (8 decimal places):")
        for nid in sorted(sb.neurons):
            if nid.startswith("s_enc_"):
                n = sb.neurons[nid]
                print(f"    {nid:<25s}: act={n.activation:>+14.8f}  E={n.energy:.6f}  pre_tr={n.pre_trace:.8f}")

        print("  Shadow column activations:")
        for nid in sorted(sb.neurons):
            if nid.startswith("s_col_"):
                n = sb.neurons[nid]
                print(f"    {nid:<25s}: act={n.activation:>+14.8f}  E={n.energy:.6f}  V_mem={n._membrane.voltage:.10f}")

        # Bundle propagation check
        print("  Bundle propagation test:")
        for bid in ['s_enc_to_col_yaw', 's_enc_to_col_pitch', 's_enc_to_col_roll']:
            bundle = sb.bundles.get(bid)
            if bundle:
                currents = bundle.propagate()
                src_acts = [s.activation for s in bundle.sources]
                print(f"    {bid}: src_acts={[f'{a:.8f}' for a in src_acts]}, propagated={[f'{c:.10f}' for c in currents]}, w={bundle.mean_weight():.6f}")

        # Cross bundle check
        print("  Cross-axis bundle weights:")
        for bid in sorted(sb.bundles):
            if bid.startswith("s_cross_yaw") or bid.startswith("s_cross_pitch"):
                b = sb.bundles[bid]
                print(f"    {bid:<30s}: w={b.mean_weight():.8f}  silent={b.config.is_silent}")

print("\n[DONE]")
