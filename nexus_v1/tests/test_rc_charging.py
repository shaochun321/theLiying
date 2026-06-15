"""Minimal RC charging test: single enc -> col bundle."""
import sys
sys.path.insert(0, '.')

from nexus_v1.components.neuron import Neuron, NeuronConfig
from nexus_v1.circuit.bundle import SynapticBundle, BundleConfig
from nexus_v1.components.semiconductor import Memristor

# Create two shadow-like neurons
enc_cfg = NeuronConfig(
    neuron_id="enc",
    capacitance=3.0,
    r_leak=5.0,
    v_rest=0.0,
    energy=10.0,  # plenty
    spiking=False,
)
col_cfg = NeuronConfig(
    neuron_id="col",
    capacitance=3.0,
    r_leak=5.0,
    v_rest=0.0,
    energy=10.0,
    spiking=False,
)

enc = Neuron(enc_cfg)
col = Neuron(col_cfg)

# Create bundle
bundle_cfg = BundleConfig(
    bundle_id="enc_to_col",
    initial_weight=0.1,
    stdp_lr=0.01,
)
bundle = SynapticBundle(bundle_cfg, [enc], [col])

dt = 0.01  # shadow dt
input_current = 2.0 * 3.0  # abs(xin) * gain = 2.0 * 3.0 = 6.0

print("Step-by-step RC charging:")
print(f"  enc C={enc_cfg.capacitance}, R_leak={enc_cfg.r_leak}")
print(f"  col C={col_cfg.capacitance}, R_leak={col_cfg.r_leak}")
print(f"  bundle w=0.1 (memristor R={bundle._memristors[0][0].resistance:.2f})")
print(f"  input_current = {input_current}")
print(f"  dt = {dt}")
print()
print(f"  {'Step':>6s}  {'enc.V_mem':>10s}  {'enc.act':>10s}  {'enc.pre_tr':>10s}  {'prop_curr':>10s}  {'col.V_mem':>10s}  {'col.act':>10s}")

for step in range(200):
    # Phase 1: Accumulate
    acc_enc = input_current
    prop = bundle.propagate()  # reads enc activation from PREVIOUS step
    acc_col = prop[0] if prop else 0.0

    # Phase 2: Step neurons
    enc.step(input_current=acc_enc, dt=dt)
    col.step(input_current=acc_col, dt=dt)

    if step % 10 == 0 or step < 5:
        print(f"  {step:>6d}  {enc._membrane.voltage:>+10.6f}  {enc.activation:>+10.6f}  {enc.pre_trace:>10.6f}  {acc_col:>10.6f}  {col._membrane.voltage:>+10.6f}  {col.activation:>+10.6f}")

print(f"\n  Theoretical enc V_ss = I * R = {input_current} * {enc_cfg.r_leak} = {input_current * enc_cfg.r_leak}")
print(f"  Theoretical col V_ss depends on propagated current reaching threshold")
