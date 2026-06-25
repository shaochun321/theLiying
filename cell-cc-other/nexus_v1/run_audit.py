"""Extended entropy audit: 5000 steps."""
import sys
sys.path.insert(0, '.')
from nexus_v1.circuit.hebbian import HebbianCircuit
from nexus_v1.circuit.observer import CircuitObserver

circuit = HebbianCircuit()
observer = CircuitObserver()
dt = 0.001

print("=" * 70)
print("nexus_v1 Extended Entropy Audit (5000 steps)")
print("=" * 70)

for t in range(5000):
    inputs = {axis: 0.0 for axis in circuit.vestibular.axes}
    inputs["yaw"] = 0.8
    circuit.step(inputs, dt)

    if t % 500 == 0 or t == 4999:
        entry = observer.observe(circuit, t)
        eb = entry.entropy
        snap = entry.snapshot
        acts = " | ".join(f"{k}={v:.4f}" for k, v in eb.signal_trace.items())
        print(f"  t={t:4d}  depth={eb.signal_depth}/6  "
              f"active={snap.active_neuron_count}  spikes={snap.total_spikes}  "
              f"heat={snap.total_heat:.2f}")
        print(f"         {acts}")

print("\n")
observer.print_summary()

print("\n--- Signal Depth History ---")
for tick, depth in observer.signal_depth_history():
    bar = ">" * depth + "." * (6 - depth)
    print(f"  t={tick:4d}: [{bar}] {depth}/6")
