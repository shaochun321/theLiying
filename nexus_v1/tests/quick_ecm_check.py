"""快速检查 VariantCircuit 的 ECM/Vascular 状态。"""
import sys, json
sys.path.insert(0, '.')
from nexus_v1.circuit.variant_adapter import VariantCircuit

v = VariantCircuit()
for i in range(5000):
    v.step({'yaw': 0.8}, 0.001)

state = v.get_variant_state()
print("=== ECM State ===")
for layer, data in state['ecm'].items():
    print(f"  {layer}: {data}")
print(f"\n=== Vascular State ===")
print(f"  {state['vascular']}")
