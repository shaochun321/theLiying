"""Task B: PNN Critical Period — verify plasticity gating."""
import sys
sys.path.insert(0, '.')
from nexus_v1.circuit.variant_adapter import VariantCircuit

print("=" * 70)
print("Task B: PNN Critical Period Verification")
print("=" * 70)

c = VariantCircuit()

print(f"\n{'Time(s)':>8s}  {'PNN_vest':>8s}  {'PNN_enc':>8s}  {'PNN_col':>8s}  {'Gate_enc':>8s}  {'Enc→Col_lr':>10s}  {'Enc→Col_w':>10s}")

last_w = 0.15
for step in range(100000):
    c.step({'yaw': 0.8, 'pitch': 0.6}, 0.001)
    t = (step + 1) * 0.001
    
    if (step + 1) % 10000 == 0:
        pnn_v = c.ecm_vestibular.pnn_maturity
        pnn_e = c.ecm_encoding.pnn_maturity
        pnn_c = c.ecm_column.pnn_maturity
        gate = c.ecm_encoding.plasticity_gate
        
        # Find enc_to_col bundle
        for b in c.get_all_bundles():
            if b.config.bundle_id == 'enc_to_col_yaw':
                lr = b.config.stdp_lr
                w = b.mean_weight()
                break
        
        dw = w - last_w
        last_w = w
        print(f"{t:>8.1f}  {pnn_v:>8.4f}  {pnn_e:>8.4f}  {pnn_c:>8.4f}  {gate:>8.4f}  {lr:>10.6f}  {w:>10.4f}  dw={dw:+.4f}")

print(f"\n── Verdict ──")
final_gate = c.ecm_encoding.plasticity_gate
print(f"  Final plasticity gate: {final_gate:.4f}")
print(f"  {'✓' if final_gate < 0.5 else '✗'} Gate closing (< 0.5)")
print(f"  PNN maturity: vest={c.ecm_vestibular.pnn_maturity:.3f} enc={c.ecm_encoding.pnn_maturity:.3f} col={c.ecm_column.pnn_maturity:.3f}")
