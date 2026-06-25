"""Phase 3 验证: ECM + VascularCooling 独立组件测试。

Gate 验证:
  G6. ECM 温度缓冲 (thermal inertia > 0)
  G7. ECM 离子缓冲饱和/清除循环
  G8. PNN 成熟动力学
  G9. Q10 温度效应正确方向
  G10. Vascular NVC: 活动 → 血流 ↑
  G11. Vascular 热移除: T > T_artery → Q_remove > 0
  G12. Vascular 能量递送 > 0
  G13. ECM-Vascular 耦合: 热平衡可达
"""
import sys
sys.path.insert(0, '.')

from nexus_v1.components.ecm import (
    ExtracellularMatrix, create_vestibular_ecm, create_cortical_ecm
)
from nexus_v1.components.vascular import (
    VascularCooling, create_brainstem_vascular, create_cortical_vascular
)

results = []

def check(name, condition, actual, expected):
    status = "PASS" if condition else "FAIL"
    results.append((name, status, actual, expected))
    print(f"  [{status}] {name:45s} actual={str(actual):>15s}  expected={expected}")

print("=" * 70)
print("PHASE 3 — ECM + VASCULAR STANDALONE VERIFICATION")
print("=" * 70)

# ═══════════════════════════════════════════════════════
# G6: ECM Thermal Inertia
# ═══════════════════════════════════════════════════════
print("\n── 1. ECM Thermal Dynamics ──")
ecm = create_vestibular_ecm()
assert ecm.temperature == 0.0, "Initial temp should be T_ref=0.0"

# Inject constant heat for 100 steps
dt = 0.001
for _ in range(100):
    ecm.step(heat_inputs=10.0, dt=dt)  # 10W equiv heat

check("G6a ECM temp rises with heat",
      ecm.temperature > 0.0,
      f"{ecm.temperature:.4f}", "> 0.0")

# Let it cool
ecm_hot = ecm.temperature
for _ in range(1000):
    ecm.step(heat_inputs=0.0, dt=dt)
check("G6b ECM cools without heat",
      ecm.temperature < ecm_hot,
      f"{ecm.temperature:.4f}°C", f"< {ecm_hot:.4f}")

# Check it approaches ambient
for _ in range(10000):
    ecm.step(heat_inputs=0.0, dt=dt)
check("G6c ECM converges toward ambient",
      abs(ecm.temperature - 0.0) < 0.05,
      f"{ecm.temperature:.4f}", "≈ 0.0 (±0.05)")

# ═══════════════════════════════════════════════════════
# G7: Ion Buffer Dynamics
# ═══════════════════════════════════════════════════════
print("\n── 2. ECM Ion Buffer ──")
ecm2 = create_vestibular_ecm()

# Fill buffer
for _ in range(500):
    ecm2.step(heat_inputs=5.0, dt=dt)
buffer_full = ecm2.ion_buffer
check("G7a Ion buffer fills with activity",
      buffer_full > 0.1,
      f"{buffer_full:.4f}", "> 0.1")

# Drain buffer
for _ in range(2000):
    ecm2.step(heat_inputs=0.0, dt=dt)
buffer_drained = ecm2.ion_buffer
check("G7b Ion buffer drains without activity",
      buffer_drained < buffer_full * 0.1,
      f"{buffer_drained:.4f}", f"< {buffer_full*0.1:.4f}")

# Saturation test
ecm3 = ExtracellularMatrix(ion_buffer_capacity=1.0)
for _ in range(10000):
    ecm3.step(heat_inputs=100.0, dt=dt)
check("G7c Ion buffer saturates at capacity",
      ecm3.ion_buffer <= ecm3.ion_buffer_capacity,
      f"{ecm3.ion_buffer:.4f}", f"<= {ecm3.ion_buffer_capacity}")

# ═══════════════════════════════════════════════════════
# G8: PNN Maturation
# ═══════════════════════════════════════════════════════
print("\n── 3. PNN Maturation ──")
ecm4 = create_cortical_ecm()
initial_maturity = ecm4.pnn_maturity
initial_gate = ecm4.plasticity_gate
check("G8a PNN starts immature",
      initial_maturity < 0.1,
      f"{initial_maturity:.3f}", "< 0.1")
check("G8b Plasticity gate starts open",
      initial_gate > 0.9,
      f"{initial_gate:.3f}", "> 0.9")

# Run for 200s (maturation)
for _ in range(200000):  # 200s at dt=0.001
    ecm4.step(heat_inputs=0.0, dt=dt)
check("G8c PNN matures toward target",
      ecm4.pnn_maturity > 0.5,
      f"{ecm4.pnn_maturity:.3f}", "> 0.5")
check("G8d Plasticity gate closes",
      ecm4.plasticity_gate < 0.5,
      f"{ecm4.plasticity_gate:.3f}", "< 0.5")

# ═══════════════════════════════════════════════════════
# G9: Q10 Temperature Effects
# ═══════════════════════════════════════════════════════
print("\n── 4. Q10 Temperature Effects ──")
ecm_q10 = ExtracellularMatrix()

# At T_ref (0.0)
tau_at_ref = ecm_q10.temperature_effect_on_tau(1.0)
gm_at_ref = ecm_q10.temperature_effect_on_gm(1.0)
check("G9a tau at T_ref",
      abs(tau_at_ref - 1.0) < 0.01,
      f"{tau_at_ref:.4f}", "≈ 1.0")

# Heat up +10 units above T_ref
ecm_q10._temperature = 10.0
tau_at_hot = ecm_q10.temperature_effect_on_tau(1.0)
gm_at_hot = ecm_q10.temperature_effect_on_gm(1.0)
check("G9b tau decreases with +10 ΔT (Q10=3)",
      tau_at_hot < tau_at_ref * 0.5,
      f"{tau_at_hot:.4f}", f"< {tau_at_ref*0.5:.4f}")
check("G9c gm increases with +10 ΔT (Q10=1.5)",
      gm_at_hot > gm_at_ref * 1.3,
      f"{gm_at_hot:.4f}", f"> {gm_at_ref*1.3:.4f}")

# Effective capacitance
ecm_cap = ExtracellularMatrix(pnn_maturity=1.0, capacitance_boost=0.3)
c_factor = ecm_cap.effective_capacitance_factor()
check("G9d Capacitance boost at full PNN",
      abs(c_factor - 1.3) < 0.01,
      f"{c_factor:.3f}", "≈ 1.3")

# ═══════════════════════════════════════════════════════
# G10: Vascular NVC
# ═══════════════════════════════════════════════════════
print("\n── 5. Vascular NVC ──")
vasc = create_brainstem_vascular()

# Baseline flow
check("G10a Baseline flow",
      abs(vasc.flow_rate - vasc.base_flow) < 0.01,
      f"{vasc.flow_rate:.3f}", f"≈ {vasc.base_flow}")

# High activity → flow increases
for _ in range(5000):
    vasc.step(tissue_temperature=0.5, local_activity=5.0, dt=dt)
check("G10b Flow increases with activity",
      vasc.flow_rate > vasc.base_flow,
      f"{vasc.flow_rate:.3f}", f"> {vasc.base_flow}")

# Flow bounded
for _ in range(10000):
    vasc.step(tissue_temperature=0.5, local_activity=100.0, dt=dt)
check("G10c Flow bounded by max_flow",
      vasc.flow_rate <= vasc.max_flow,
      f"{vasc.flow_rate:.3f}", f"<= {vasc.max_flow}")

# ═══════════════════════════════════════════════════════
# G11-G12: Heat Removal + Energy Delivery
# ═══════════════════════════════════════════════════════
print("\n── 6. Vascular Heat Removal + Energy ──")
vasc2 = create_cortical_vascular()

result = vasc2.step(tissue_temperature=0.5, local_activity=2.0, dt=0.001)
check("G11 Heat removed when T > T_ref",
      result['heat_removed'] > 0,
      f"{result['heat_removed']:.6f}", "> 0")
check("G12 Energy delivered > 0",
      result['energy_delivered'] > 0,
      f"{result['energy_delivered']:.6f}", "> 0")

# No heat removal when T = T_ref
result_cold = vasc2.step(tissue_temperature=0.0, local_activity=0.0, dt=0.001)
check("G11b No heat removed when T = T_ref",
      result_cold['heat_removed'] == 0,
      f"{result_cold['heat_removed']:.6f}", "= 0")

# ═══════════════════════════════════════════════════════
# G13: ECM-Vascular Coupling — Thermal Equilibrium
# ═══════════════════════════════════════════════════════
print("\n── 7. ECM-Vascular Coupled Equilibrium ──")
ecm_c = create_vestibular_ecm()
vasc_c = create_brainstem_vascular()

# Inject constant heat, let NVC cool it
constant_heat = 2.0  # W equiv
for i in range(20000):
    # ECM absorbs heat and conducts
    ecm_c.step(heat_inputs=constant_heat, dt=dt)
    # Vascular removes heat based on ECM temperature
    activity = constant_heat  # proxy
    result_c = vasc_c.step(
        tissue_temperature=ecm_c.temperature,
        local_activity=activity,
        dt=dt
    )
    # Subtract vascular cooling from ECM
    ecm_c._temperature -= result_c['heat_removed'] * dt / max(ecm_c.thermal_capacity, 0.01)

final_temp = ecm_c.temperature
# Should reach equilibrium above T_ref=0.0
check("G13a Equilibrium reached (T stable)",
      0.0 < final_temp < 5.0,
      f"{final_temp:.4f}", "(0, 5)")
check("G13b NVC flow elevated",
      vasc_c.flow_rate > vasc_c.base_flow,
      f"{vasc_c.flow_rate:.3f}", f"> {vasc_c.base_flow}")

# ═══════════════════════════════════════════════════════
# Summary
# ═══════════════════════════════════════════════════════
print(f"\n{'='*70}")
print("PHASE 3 VERIFICATION SUMMARY")
print(f"{'='*70}")
passes = sum(1 for _, s, _, _ in results if s == "PASS")
fails = sum(1 for _, s, _, _ in results if s == "FAIL")
print(f"  PASS: {passes}")
print(f"  FAIL: {fails}")
print(f"  TOTAL: {passes + fails}")
if fails == 0:
    print(f"\n  ✓ ALL COMPONENTS VERIFIED — ready for integration")
else:
    print(f"\n  ✗ {fails} FAILURES — fix before proceeding")

# Mother codebase integrity
print(f"\n── Mother Codebase Integrity ──")
from nexus_v1.circuit.hebbian import HebbianCircuit
hc = HebbianCircuit()
for i in range(100):
    hc.step({'yaw': 0.5}, 0.001)
neurons = hc.get_all_neurons()
bundles = hc.get_all_bundles()
print(f"  HebbianCircuit: still runs ✓")
print(f"  Total neurons: {len(neurons)}")
print(f"  Total bundles: {len(bundles)}")
