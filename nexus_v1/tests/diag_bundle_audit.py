"""diag_bundle_audit.py — audit key bundle parameters for Class 1 Driver check."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from nexus_v1.circuit.variant_adapter import VariantCircuit

c = VariantCircuit()

def show_bundle(b, label=""):
    cfg = b.config
    bid = cfg.bundle_id
    w = cfg.initial_weight
    wmax = getattr(cfg, "weight_max", "N/A")
    gain = getattr(cfg, "synapse_gain", "N/A")
    lr = getattr(cfg, "stdp_lr", "N/A")
    rule = getattr(cfg, "learning_rule", "N/A")
    print(f"  [{label}] {bid}")
    print(f"      initial_weight={w}  weight_max={wmax}  synapse_gain={gain}")
    print(f"      learning_rule={rule}  stdp_lr={lr}")

print("\n=== bundles_vest_to_enc (vestibular Aff -> Enc) ===")
for b in c.bundles_vest_to_enc:
    show_bundle(b, "vest→enc")

print("\n=== bundles_enc_to_col (sample, first 4) ===")
for b in c.bundles_enc_to_col[:4]:
    show_bundle(b, "enc→col")

print("\n=== bundles_col_to_motor — thermal bundles ===")
found_therm = False
for b in c.bundles_col_to_motor:
    if "therm" in b.config.bundle_id:
        show_bundle(b, "therm→motor")
        found_therm = True
if not found_therm:
    print("  (none found — Phase 3 NOT implemented)")

print("\n=== bundles_col_to_motor — vestibular axis bundles (sample) ===")
for b in c.bundles_col_to_motor[:4]:
    show_bundle(b, "col→motor")

print()
