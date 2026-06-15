"""L6 Motor Layer Isolation Analysis (RULES Principle 11).

Isolate motor neurons, feed them fixed contract-compliant input
from the column layer, and measure:
  1. Energy budget: input vs I²R dissipation vs VR recovery
  2. Firing rate at different input levels
  3. adapt_threshold behavior (currently disconnected)
  4. Energy depletion timeline
"""
import sys, math
sys.path.insert(0, '.')

from nexus_v1.components.neuron import Neuron, NeuronConfig, ChannelConfig
from nexus_v1.components.semiconductor import MOSFET

# ── Motor config (exact copy from hebbian.py) ──
def motor_config(name):
    return NeuronConfig(
        neuron_id=f"motor_{name}",
        capacitance=1.0,
        r_leak=5.0,
        inertia=0.5,
        vdd=1.0,
        r_supply=0.1,
        spiking=True,
        v_peak=0.3,
        v_reset=0.077,
        b_adapt=0.02,
        tau_w=50.0,
        use_voltage_regulator=True,
        vr_base_rate=0.1,
        vr_activity_coeff=0.3,
        vr_max_rate=3.0,
    )

dt = 0.001

# ═══════════════════════════════════════════════════════
# Test 1: Energy budget at different input levels
# ═══════════════════════════════════════════════════════
print("=" * 70)
print("TEST 1: Motor energy budget at different input levels")
print("=" * 70)
print(f"\n  {'I_input':>8s}  {'spikes':>8s}  {'rate(Hz)':>8s}  {'E_final':>8s}  {'heat_tot':>10s}  {'VR_eff':>8s}  {'lifetime':>10s}")

for I_in in [0.0, 0.1, 0.5, 1.0, 2.0, 5.0, 10.0]:
    mot = Neuron(motor_config("test"))
    total_heat = 0.0
    total_vr = 0.0
    death_step = None

    for step in range(10000):
        e_before = mot.energy
        mot.step(input_current=I_in, dt=dt)
        e_after = mot.energy
        total_heat += mot.heat_output
        vr_recovery = max(0, e_after - e_before + mot.heat_output)
        total_vr += vr_recovery

        if e_after <= 0.001 and death_step is None:
            death_step = step

    n_spk = len(mot.spike_times)
    rate = n_spk / (10000 * dt) if n_spk > 0 else 0
    lifetime = f"ALIVE" if death_step is None else f"dead@{death_step}"

    print(f"  {I_in:>8.1f}  {n_spk:>8d}  {rate:>8.1f}  {mot.energy:>8.4f}  {total_heat:>10.2f}  {total_vr:>10.4f}  {lifetime:>10s}")

# ═══════════════════════════════════════════════════════
# Test 2: Step-by-step energy trace at typical input
# ═══════════════════════════════════════════════════════
print("\n" + "=" * 70)
print("TEST 2: Energy trace at I=2.0 (typical col->mot current)")
print("=" * 70)
mot = Neuron(motor_config("trace"))
print(f"\n  {'step':>6s}  {'V_mem':>8s}  {'act':>6s}  {'energy':>8s}  {'heat':>10s}  {'spike':>6s}  {'w_adapt':>8s}")

for step in range(500):
    mot.step(input_current=2.0, dt=dt)
    if step % 25 == 0 or step < 10 or mot._spiked_this_step:
        spiked = "YES" if mot._spiked_this_step else ""
        if step < 100 or step % 50 == 0 or mot._spiked_this_step:
            print(f"  {step:>6d}  {mot._membrane.voltage:>+8.4f}  {mot.activation:>6.2f}  {mot.energy:>8.4f}  {mot.heat_output:>10.4f}  {spiked:>6s}  {mot._w_adapt:>8.4f}")

# ═══════════════════════════════════════════════════════
# Test 3: What the col_to_motor bundle actually sends
# ═══════════════════════════════════════════════════════
print("\n" + "=" * 70)
print("TEST 3: Actual col->motor current in live circuit")
print("=" * 70)

from nexus_v1.circuit.variant_adapter import VariantCircuit

circuit = VariantCircuit()
# Run 5000 steps, sample motor input
motor_currents = {m: [] for m in circuit.motor_neurons}
motor_heats = {m: [] for m in circuit.motor_neurons}

for t in range(5000):
    inputs = {'yaw': 0.3, 'pitch': 0.3, 'roll': 0.02}
    circuit.step(inputs, dt=0.001)

    if t % 100 == 0:
        for key, mot in circuit.motor_neurons.items():
            motor_currents[key].append(mot.activation)
            motor_heats[key].append(mot.heat_output)

print(f"\n  {'Motor':>12s}  {'E':>8s}  {'spikes':>8s}  {'avg_heat':>10s}  {'max_heat':>10s}  {'avg_act':>8s}")
for key, mot in circuit.motor_neurons.items():
    avg_h = sum(motor_heats[key]) / max(len(motor_heats[key]), 1)
    max_h = max(motor_heats[key]) if motor_heats[key] else 0
    avg_a = sum(motor_currents[key]) / max(len(motor_currents[key]), 1)
    print(f"  {key:>12s}  {mot.energy:>8.4f}  {len(mot.spike_times):>8d}  {avg_h:>10.2f}  {max_h:>10.2f}  {avg_a:>8.4f}")

# ═══════════════════════════════════════════════════════
# Test 4: What input current does col_to_motor propagate?
# ═══════════════════════════════════════════════════════
print("\n" + "=" * 70)
print("TEST 4: col_to_motor bundle propagation analysis")
print("=" * 70)
for b in circuit.bundles_col_to_motor:
    print(f"\n  Bundle: {b.id}")
    print(f"  synapse_gain = {b.config.synapse_gain}")
    print(f"  n_sources = {b.n_sources}, n_targets = {b.n_targets}")
    currents = b.propagate()
    print(f"  Propagated currents: {[f'{c:.4f}' for c in currents]}")
    print(f"  Source activations:")
    for s in b.sources:
        print(f"    {s.id}: act={s.activation:.6f}, pre_tr={s.pre_trace:.6f}")
    print(f"  Memristor weights (sample):")
    for i in range(min(3, len(b._memristors))):
        for j in range(min(3, len(b._memristors[i]))):
            m = b._memristors[i][j]
            print(f"    [{i}][{j}]: w={m.w:.6f}, R={m.resistance:.2f}, G={m.conductance:.4f}")

# ═══════════════════════════════════════════════════════
# Test 5: PowerRail analysis at motor currents
# ═══════════════════════════════════════════════════════
print("\n" + "=" * 70)
print("TEST 5: PowerRail I²R at different scaled_current levels")
print("=" * 70)
print(f"\n  Motor config: vdd={1.0}, r_supply={0.1}, inertia={0.5}")
print(f"  heat = (I/inertia)² × r_supply")
print(f"\n  {'I_raw':>8s}  {'I_scaled':>10s}  {'V_avail':>8s}  {'V_ratio':>8s}  {'I_inject':>10s}  {'heat(I²R)':>10s}")
for I_raw in [0.1, 0.5, 1.0, 2.0, 5.0, 10.0, 50.0, 100.0]:
    I_scaled = I_raw / 0.5  # inertia=0.5
    v_avail = max(0, 1.0 - abs(I_scaled) * 0.1)
    v_ratio = v_avail / 1.0
    I_inj = I_scaled * v_ratio
    heat = min(100.0, I_scaled) ** 2 * 0.1
    print(f"  {I_raw:>8.1f}  {I_scaled:>10.2f}  {v_avail:>8.4f}  {v_ratio:>8.4f}  {I_inj:>+10.4f}  {heat:>10.2f}")

print(f"\n{'='*70}")
print("[DONE] L6 Motor isolation analysis complete.")
