"""项目全景扫描 — 给用户的完整报告。"""
import sys
sys.path.insert(0, '.')
from nexus_v1.circuit.hebbian import HebbianCircuit
from nexus_v1.circuit.variant_adapter import VariantCircuit

# ── 1. 规模统计 ──
c = HebbianCircuit()
neurons = c.get_all_neurons()
bundles = c.get_all_bundles()

print("=" * 70)
print("项目全景扫描")
print("=" * 70)

print(f"\n── 1. 规模 ──")
print(f"  总神经元数: {len(neurons)}")
print(f"  总突触束数: {len(bundles)}")

# 按层统计
vest_n = len(c.vestibular.met_neurons) + len(c.vestibular.haircell_neurons) + \
         len(c.vestibular.afferent_regular) + len(c.vestibular.afferent_irregular)
enc_n = len(c.encoding_neurons)
col_n = len(c.column_neurons)
mot_n = len(c.motor_neurons)
print(f"  前庭层: {vest_n} 个神经元 (MET+HC+Aff_r+Aff_i)")
print(f"  编码层: {enc_n} 个神经元")
print(f"  柱状层: {col_n} 个神经元")
print(f"  运动层: {mot_n} 个神经元")
print(f"  轴数:   {len(c.vestibular.axes)}")
print(f"  轴列表: {list(c.vestibular.axes)}")

# 突触连接数 (memristors)
total_memristors = 0
for b in bundles:
    for row in b._memristors:
        total_memristors += len(row)
print(f"  总突触连接 (memristor): {total_memristors}")

# ── 2. STDP 权重演化 ──
print(f"\n── 2. STDP 权重演化 ──")
# Run 5s and track weights
weights_start = {}
for b in bundles:
    weights_start[b.config.bundle_id] = b.mean_weight()

for i in range(5000):
    c.step({'yaw': 0.8}, 0.001)

weights_end = {}
for b in bundles:
    weights_end[b.config.bundle_id] = b.mean_weight()

print(f"  {'Bundle':<30s}  {'初始':>8s}  {'5s后':>8s}  {'变化':>8s}  {'规则'}")
for b in bundles:
    bid = b.config.bundle_id
    w0 = weights_start[bid]
    w1 = weights_end[bid]
    delta = w1 - w0
    marker = "★" if abs(delta) > 0.001 else ""
    print(f"  {bid:<30s}  {w0:>8.4f}  {w1:>8.4f}  {delta:>+8.4f}  {b.config.learning_rule} {marker}")

# ── 3. 链路追踪 ──
print(f"\n── 3. 信号链路 (6 层) ──")
chain = [
    ("L1 MET",     "机械偏转→电导→电流",         "Mechanotransducer"),
    ("L2 HairCell", "突触电流→Ca²⁺→囊泡释放",    "Ribbon Synapse"),
    ("L3 Afferent", "突触输入→膜电位→spike",      "Spiking Neuron"),
    ("L4 Encoding", "spike率→activation (VR)",    "Rate Coding"),
    ("L5 Column",   "多轴整合→空间编码",          "Integration"),
    ("L6 Motor",    "阈值交叉→运动spike",         "Motor Output"),
]
for name, desc, bio in chain:
    print(f"  {name:<15s} │ {desc:<30s} │ {bio}")

# Bundle connections
print(f"\n  连接拓扑:")
for b in bundles:
    src_names = [s.config.neuron_id for s in b.sources]
    tgt_names = [t.config.neuron_id for t in b.targets]
    print(f"    {b.config.bundle_id}: {src_names} → {tgt_names}  (w={b.mean_weight():.3f}, rule={b.config.learning_rule})")

# ── 4. Variant 组件 ──
print(f"\n── 4. 变体组件 (7 个) ──")
v = VariantCircuit()
for i in range(2000):
    v.step({'yaw': 0.8}, 0.001)
state = v.get_variant_state()

print(f"  Oscillators: {len(v.oscillators)} 个")
print(f"  Dampers Enc: {len(v.dampers_enc)} 个")
print(f"  Dampers Col: {len(v.dampers_col)} 个")
print(f"  ECM layers:  3 (vest/enc/col)")
print(f"  Vascular:    1 (global)")
print(f"  NDR gates:   {len(v.ndr_afferent)} 个")
print(f"  Routers:     {len(v.routers_enc_col)} 个")
print(f"  DA modulator: 1")
print(f"  DA conc:     {v.dopamine.concentration:.4f}")

# Traces check
print(f"\n── 5. STDP 机制细节 ──")
aff = c.vestibular.afferent_regular['yaw']
hc = c.vestibular.haircell_neurons['yaw']
print(f"  HC  pre_trace:  {hc.pre_trace:.4f}")
print(f"  HC  post_trace: {hc.post_trace:.4f}")
print(f"  Aff pre_trace:  {aff.pre_trace:.4f}")
print(f"  Aff post_trace: {aff.post_trace:.4f}")
print(f"  STDP 公式: dw = lr × dt × (pre_src × post_tgt - post_src × pre_tgt)")
print(f"  学习率: HC→Aff lr={c.vestibular.bundles_hc_to_aff['yaw'].config.stdp_lr}")
