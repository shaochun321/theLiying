"""探针：不同运动模式在权重空间中留下怎样的印记？"""
import sys, copy
sys.path.insert(0, '.')
from nexus_v1.circuit.hebbian import HebbianCircuit

def get_weight_vector(c):
    """提取全部 memristor 权重为一维向量."""
    weights = []
    for b in c.get_all_bundles():
        for row in b._memristors:
            for m in row:
                weights.append(m.w)
    return weights

def cosine_sim(a, b):
    dot = sum(x*y for x, y in zip(a, b))
    na = sum(x**2 for x in a) ** 0.5
    nb = sum(x**2 for x in b) ** 0.5
    return dot / max(na * nb, 1e-10)

# ── 1. 三种不同运动模式训练 ──
print("=" * 70)
print("运动模式在赫布权重空间中的印记")
print("=" * 70)

# 基线权重
c0 = HebbianCircuit()
w0 = get_weight_vector(c0)

# Pattern A: 纯 yaw 旋转
cA = HebbianCircuit()
for _ in range(10000):
    cA.step({'yaw': 0.8}, 0.001)
wA = get_weight_vector(cA)

# Pattern B: 纯 pitch 旋转
cB = HebbianCircuit()
for _ in range(10000):
    cB.step({'pitch': 0.8}, 0.001)
wB = get_weight_vector(cB)

# Pattern C: yaw + pitch 联合
cC = HebbianCircuit()
for _ in range(10000):
    cC.step({'yaw': 0.8, 'pitch': 0.8}, 0.001)
wC = get_weight_vector(cC)

# Pattern D: 纯 oto_x 平移
cD = HebbianCircuit()
for _ in range(10000):
    cD.step({'oto_x': 0.8}, 0.001)
wD = get_weight_vector(cD)

# ── 2. 权重变化分析 ──
def delta(w, w0):
    return [a - b for a, b in zip(w, w0)]

dA = delta(wA, w0)
dB = delta(wB, w0)
dC = delta(wC, w0)
dD = delta(wD, w0)

print(f"\n── 权重变化幅度 ──")
print(f"  Pattern A (yaw):       Σ|Δw| = {sum(abs(d) for d in dA):.4f},  max|Δw| = {max(abs(d) for d in dA):.4f}")
print(f"  Pattern B (pitch):     Σ|Δw| = {sum(abs(d) for d in dB):.4f},  max|Δw| = {max(abs(d) for d in dB):.4f}")
print(f"  Pattern C (yaw+pitch): Σ|Δw| = {sum(abs(d) for d in dC):.4f},  max|Δw| = {max(abs(d) for d in dC):.4f}")
print(f"  Pattern D (oto_x):     Σ|Δw| = {sum(abs(d) for d in dD):.4f},  max|Δw| = {max(abs(d) for d in dD):.4f}")

print(f"\n── 权重变化向量的余弦相似度 ──")
print(f"  A(yaw) vs B(pitch):     {cosine_sim(dA, dB):.4f}")
print(f"  A(yaw) vs C(yaw+pitch): {cosine_sim(dA, dC):.4f}")
print(f"  B(pitch) vs C(yaw+pitch): {cosine_sim(dB, dC):.4f}")
print(f"  A(yaw) vs D(oto_x):     {cosine_sim(dA, dD):.4f}")

# ── 3. 哪些权重变了？逐 bundle 分析 ──
print(f"\n── 逐 Bundle 权重变化 (10s 后) ──")
print(f"  {'Bundle':<30s}  {'A(yaw)':>8s}  {'B(pitch)':>8s}  {'C(y+p)':>8s}  {'D(oto)':>8s}  {'init':>6s}")
bundles_A = cA.get_all_bundles()
bundles_B = cB.get_all_bundles()
bundles_C = cC.get_all_bundles()
bundles_D = cD.get_all_bundles()
bundles_0 = c0.get_all_bundles()

for i, b0 in enumerate(bundles_0):
    bA = bundles_A[i]
    bB = bundles_B[i]
    bC = bundles_C[i]
    bD = bundles_D[i]
    wA_b = bA.mean_weight()
    wB_b = bB.mean_weight()
    wC_b = bC.mean_weight()
    wD_b = bD.mean_weight()
    w0_b = b0.mean_weight()
    # Only show bundles that changed
    if max(abs(wA_b-w0_b), abs(wB_b-w0_b), abs(wC_b-w0_b), abs(wD_b-w0_b)) > 0.001:
        print(f"  {b0.config.bundle_id:<30s}  {wA_b:>8.4f}  {wB_b:>8.4f}  {wC_b:>8.4f}  {wD_b:>8.4f}  {w0_b:>6.3f}")

# ── 4. 独立性检验：A 训练后能否识别 B？ ──
print(f"\n── 模式独立性检验 ──")
# 用 A-trained 电路处理 pitch 输入
cA2 = HebbianCircuit()
for _ in range(10000):
    cA2.step({'yaw': 0.8}, 0.001)
# 现在给它 pitch 输入
for _ in range(1000):
    cA2.step({'pitch': 0.8}, 0.001)

# 对比：未训练电路处理 pitch
cU = HebbianCircuit()
for _ in range(1000):
    cU.step({'pitch': 0.8}, 0.001)

aff_A2 = cA2.vestibular.afferent_regular['pitch']
aff_U = cU.vestibular.afferent_regular['pitch']
print(f"  Pitch response after yaw-training:  {len(aff_A2.spike_times)} spikes")
print(f"  Pitch response (untrained):         {len(aff_U.spike_times)} spikes")
print(f"  → {'独立' if abs(len(aff_A2.spike_times) - len(aff_U.spike_times)) < 5 else '交叉影响'}:  yaw训练{'不' if abs(len(aff_A2.spike_times) - len(aff_U.spike_times)) < 5 else ''}影响 pitch 响应")
