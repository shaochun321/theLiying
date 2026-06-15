"""P2: STDP 上游传播诊断 — 为什么 Aff→Enc 权重不变？"""
import sys
sys.path.insert(0, '.')
from nexus_v1.circuit.hebbian import HebbianCircuit

c = HebbianCircuit()

# Run with yaw input
for i in range(5000):
    c.step({'yaw': 0.8}, 0.001)

print("=== STDP Upstream Propagation Diagnosis ===\n")

# Check traces at each layer
aff_r = c.vestibular.afferent_regular['yaw']
aff_i = c.vestibular.afferent_irregular['yaw']
enc_r = c.encoding_neurons['reg_yaw']
enc_i = c.encoding_neurons['irr_yaw']
col = c.column_neurons['yaw']
mot = c.motor_neurons['move_x']

print("── Trace values (5s steady-state) ──")
print(f"{'Neuron':<20s}  {'pre_trace':>10s}  {'post_trace':>10s}  {'activation':>10s}  {'spiking':>8s}")
for name, n in [
    ("Aff_reg_yaw", aff_r), ("Aff_irr_yaw", aff_i),
    ("Enc_reg_yaw", enc_r), ("Enc_irr_yaw", enc_i),
    ("Col_yaw", col), ("Motor_x", mot)]:
    print(f"  {name:<20s}  {n.pre_trace:>10.4f}  {n.post_trace:>10.4f}  {n.activation:>10.4f}  {str(n.config.spiking):>8s}")

# Check bundle details
print("\n── Bundle STDP Analysis ──")
# Aff_reg → Enc_reg bundle
for bname in ['aff_reg_to_enc_yaw', 'enc_to_col_yaw']:
    # Find the bundle
    found = None
    for b in c.get_all_bundles():
        if b.config.bundle_id == bname:
            found = b
            break
    if found:
        b = found
        print(f"\n  {bname}:")
        print(f"    learning_rule: {b.config.learning_rule}")
        print(f"    stdp_lr: {b.config.stdp_lr}")
        print(f"    weight: {b.mean_weight():.6f} (init={b.config.initial_weight})")
        for i, src in enumerate(b.sources):
            for j, tgt in enumerate(b.targets):
                pre_x_post = src.pre_trace * tgt.post_trace
                post_x_pre = src.post_trace * tgt.pre_trace
                dw = b.config.stdp_lr * 0.001 * (pre_x_post - post_x_pre)
                print(f"    [{i},{j}] src.pre={src.pre_trace:.4f} tgt.post={tgt.post_trace:.4f}")
                print(f"           src.post={src.post_trace:.4f} tgt.pre={tgt.pre_trace:.4f}")
                print(f"           LTP={pre_x_post:.6f} LTD={post_x_pre:.6f}")
                print(f"           dw/step = {dw:.8f}")

print("\n── 5s 累积 dw 估算 ──")
print("  如果 dw/step ≈ 0，说明 LTP ≈ LTD（对称取消）")
print("  这是因为 pre_trace ≈ post_trace for each neuron")
print("  → pre.pre × tgt.post ≈ src.post × tgt.pre")
