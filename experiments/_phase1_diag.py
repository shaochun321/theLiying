"""诊断: acoustic 介质信号传播"""
import sys, os, math
base = r"D:\cell-cc\Morphosphere_v37_0_native_runtime_prototype_flat_complete\morphosphere_v2pp"
sys.path.insert(0, os.path.join(base, "engines"))
sys.path.insert(0, base)
from engines.medium_system import MediumLattice3D

# 模拟 PracticeEngine 的 acoustic 介质
med = MediumLattice3D("acoustic", box_size=10.0, spacing=2.0, mode='wave')
print(f"Acoustic: {med.n_particles} particles, v={med.v_propagation:.3f}")
print(f"CFL: dt = 1/ceil(1/sqrt(6*k/m)) = 1/ceil(1/sqrt(6*0.5/1))")
print(f"  = 1/ceil(1/{math.sqrt(3):.3f}) = 1/{int(math.ceil(1/math.sqrt(3)))+0}")

# Source at (7.5, 0, 0)
src_pos = (7.5, 0, 0)
print(f"\nInjecting at {src_pos}")

for t in range(100):
    med.inject(src_pos, amplitude=5.0 * 0.05)
    med.step()
    if t in [0, 4, 9, 19, 49, 99]:
        stats = med.get_stats()
        e_origin = med.read_at((0, 0, 0))
        e_source = med.read_at(src_pos)
        e_mid = med.read_at((4, 0, 0))
        print(f"  t={t+1:3d}: total_E={stats['total_energy']:.6f} "
              f"E(source)={e_source:.6f} E(mid)={e_mid:.6f} "
              f"E(origin)={e_origin:.6f}")

# Also check: what does the gradient look like?
gx, gy, gz = med.read_gradient_at((0, 0, 0))
print(f"\nGradient at origin: ({gx:.8f}, {gy:.8f}, {gz:.8f})")
print(f"|∇E| = {math.sqrt(gx*gx+gy*gy+gz*gz):.8f}")
