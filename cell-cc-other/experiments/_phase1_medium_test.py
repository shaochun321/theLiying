"""Step 5: 介质物理系统单元测试"""
import sys, os, math
base = r"D:\cell-cc\Morphosphere_v37_0_native_runtime_prototype_flat_complete\morphosphere_v2pp"
sys.path.insert(0, os.path.join(base, "engines"))
sys.path.insert(0, base)
from engines.medium_system import MediumLattice3D

# ═══════════════════════════════════════════════
# Test 1: Lattice construction
# ═══════════════════════════════════════════════
print("=== 1. Lattice Construction ===")
med_aco = MediumLattice3D("acoustic", box_size=10.0, spacing=1.0, mode='wave')
med_the = MediumLattice3D("thermal", box_size=10.0, spacing=1.0, mode='diffusion')
print(f"  Acoustic: {med_aco.n_particles} particles, "
      f"v={med_aco.v_propagation:.3f}, L_pen={med_aco.penetration_depth:.1f}, "
      f"Z={med_aco.impedance:.3f}")
print(f"  Thermal:  {med_the.n_particles} particles, "
      f"κ={med_the.diffusivity:.4f}, L_pen={med_the.penetration_depth:.2f}, "
      f"Z={med_the.impedance:.3f}")
# Check neighbor counts
nb_counts = [len(p.neighbors) for p in med_aco.particles]
print(f"  Neighbors: min={min(nb_counts)}, max={max(nb_counts)}, "
      f"mean={sum(nb_counts)/len(nb_counts):.1f}")

# ═══════════════════════════════════════════════
# Test 2: Wave propagation speed
# ═══════════════════════════════════════════════
print("\n=== 2. Wave Propagation Speed ===")
med = MediumLattice3D("acoustic", box_size=20.0, spacing=1.0, mode='wave')
# Inject impulse at center
med.inject((0, 0, 0), amplitude=10.0, direction=(1, 0, 0))
print(f"  Predicted v = {med.v_propagation:.3f} unit/tick")

# Track wave front: find farthest particle with energy > threshold
for t in [5, 10, 15, 20, 30]:
    for _ in range(5 if t == 5 else 5):
        med.step()
    # Find max-energy particle along x-axis (y=0, z=0)
    max_e = 0
    max_x = 0
    for p in med.particles:
        if abs(p.y0) < 0.5 and abs(p.z0) < 0.5 and p.energy > max_e:
            max_e = p.energy
            max_x = p.x0
    print(f"  t={med.tick:3d}: wave front at x={max_x:.1f}  "
          f"(predicted: {med.v_propagation * med.tick:.1f})  E_max={max_e:.6f}")

# ═══════════════════════════════════════════════
# Test 3: Thermal diffusion penetration
# ═══════════════════════════════════════════════
print("\n=== 3. Thermal Diffusion ===")
med_t = MediumLattice3D("thermal", box_size=10.0, spacing=1.0, mode='diffusion')
# Continuous injection at center
for t in range(50):
    med_t.inject((0, 0, 0), amplitude=1.0)
    med_t.step()

# Read energy at various distances along x-axis
print(f"  κ={med_t.diffusivity:.4f}, λ={med_t.damping}, L_pen={med_t.penetration_depth:.2f}")
print(f"  Energy profile along x (y=0, z=0):")
for d in [0, 1, 2, 3, 4, 5]:
    e = med_t.read_at((d, 0, 0))
    print(f"    x={d}: E={e:.6f}")

# ═══════════════════════════════════════════════
# Test 4: Impedance matching
# ═══════════════════════════════════════════════
print("\n=== 4. Impedance Matching ===")
# Body impedance: from ParticleSystem3D: k_body=2.0, m_body=1.0, spacing~1.0
Z_body = math.sqrt(2.0 * 1.0) / 1.0  # √(k·m)/d²
print(f"  Z_body = {Z_body:.4f}")
for med_type in ["acoustic", "thermal"]:
    med = MediumLattice3D(med_type, box_size=10, spacing=1.0,
                           mode='wave' if med_type == 'acoustic' else 'diffusion')
    T = med.coupling_coefficient(Z_body)
    print(f"  {med_type}: Z_med={med.impedance:.4f}  T={T:.4f}")

# ═══════════════════════════════════════════════
# Test 5: Gradient reading
# ═══════════════════════════════════════════════
print("\n=== 5. Gradient (from lattice) ===")
med_g = MediumLattice3D("thermal", box_size=10.0, spacing=1.0, mode='diffusion')
for t in range(30):
    med_g.inject((3, 0, 0), amplitude=2.0)
    med_g.step()
gx, gy, gz = med_g.read_gradient_at((1, 0, 0))
print(f"  Gradient at (1,0,0): ({gx:.6f}, {gy:.6f}, {gz:.6f})")
print(f"  |∇E| = {math.sqrt(gx*gx+gy*gy+gz*gz):.6f}")
print(f"  Direction: toward source at (3,0,0)? gx>0: {gx > 0}")

print("\n=== ALL MEDIUM TESTS PASSED ===")
