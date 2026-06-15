"""Task E: Entropy Ledger — full audit run."""
import sys
sys.path.insert(0, '.')
from nexus_v1.circuit.variant_adapter import VariantCircuit
from nexus_v1.components.entropy_ledger import EntropyLedger

c = VariantCircuit()
ledger = EntropyLedger()

# Run 10s with multi-axis input
for step in range(10000):
    c.step({'yaw': 0.8, 'pitch': 0.6, 'oto_x': 0.4}, 0.001)
    ledger.record(c, 0.001)

# Print full report
ledger.print_report()

# Energy balance check
ok, msg = ledger.energy_balance_check()
print(f"\n  Energy Balance: {'✓' if ok else '✗'} {msg}")
