"""Run all nexus_v1 tests and capture stdout/stderr to files."""
import subprocess
import sys
import os
from pathlib import Path

OUT_DIR = Path("j:/cell-cc/cell-cell/test_runs/run_v1.7.2_2026-06-15/raw")
OUT_DIR.mkdir(parents=True, exist_ok=True)

TESTS = [
    # entry points
    ("run_audit",              ["python", "nexus_v1/run_audit.py"]),
    ("run_test",               ["python", "nexus_v1/run_test.py"]),
    ("run_contracts",          ["python", "nexus_v1/run_contracts.py"]),
    ("run_variant_contracts",  ["python", "nexus_v1/run_variant_contracts.py"]),
    # module tests
    ("test_governance",          [sys.executable, "-m", "nexus_v1.tests.test_governance"]),
    ("test_multiaxis",           [sys.executable, "-m", "nexus_v1.tests.test_multiaxis"]),
    ("test_entropy_ledger",      [sys.executable, "-m", "nexus_v1.tests.test_entropy_ledger"]),
    ("test_ecm_vascular",        [sys.executable, "-m", "nexus_v1.tests.test_ecm_vascular"]),
    ("test_new_systems",         [sys.executable, "-m", "nexus_v1.tests.test_new_systems"]),
    ("test_shadow_sandbox",      [sys.executable, "-m", "nexus_v1.tests.test_shadow_sandbox"]),
    ("test_shadow_stress",       [sys.executable, "-m", "nexus_v1.tests.test_shadow_stress"]),
    ("test_shadow_trace",        [sys.executable, "-m", "nexus_v1.tests.test_shadow_trace"]),
    ("test_shadow_expansion",    [sys.executable, "-m", "nexus_v1.tests.test_shadow_expansion"]),
    ("test_shadow_coupling",     [sys.executable, "-m", "nexus_v1.tests.test_shadow_coupling"]),
    ("test_variant_components",  [sys.executable, "-m", "nexus_v1.tests.test_variant_components"]),
    ("test_stdp_diagnosis",      [sys.executable, "-m", "nexus_v1.tests.test_stdp_diagnosis"]),
    ("test_stdp_evolution",      [sys.executable, "-m", "nexus_v1.tests.test_stdp_evolution"]),
    ("test_stdp_upstream",       [sys.executable, "-m", "nexus_v1.tests.test_stdp_upstream"]),
    ("test_stdp_vs_frozen",      [sys.executable, "-m", "nexus_v1.tests.test_stdp_vs_frozen"]),
    ("test_met_range",           [sys.executable, "-m", "nexus_v1.tests.test_met_range"]),
    ("test_cv_rootcause",        [sys.executable, "-m", "nexus_v1.tests.test_cv_rootcause"]),
    ("test_pnn_critical",        [sys.executable, "-m", "nexus_v1.tests.test_pnn_critical"]),
    ("test_motion_imprint",      [sys.executable, "-m", "nexus_v1.tests.test_motion_imprint"]),
    ("test_rc_charging",         [sys.executable, "-m", "nexus_v1.tests.test_rc_charging"]),
    ("test_motor_isolation",     [sys.executable, "-m", "nexus_v1.tests.test_motor_isolation"]),
    ("test_motor_fix",           [sys.executable, "-m", "nexus_v1.tests.test_motor_fix"]),
    ("test_binding_trace",       [sys.executable, "-m", "nexus_v1.tests.test_binding_trace"]),
    ("test_heat_trace",          [sys.executable, "-m", "nexus_v1.tests.test_heat_trace"]),
    ("test_wadapt_trace",        [sys.executable, "-m", "nexus_v1.tests.test_wadapt_trace"]),
    ("test_phase3_da_loop",      [sys.executable, "-m", "nexus_v1.tests.test_phase3_da_loop"]),
    ("test_directional_learning",[sys.executable, "-m", "nexus_v1.tests.test_directional_learning"]),
    ("test_chain_diagnostic",    [sys.executable, "-m", "nexus_v1.tests.test_chain_diagnostic"]),
    ("test_scalar_thermal",      [sys.executable, "-m", "nexus_v1.tests.test_scalar_thermal"]),
    ("test_thermal_smoke",       [sys.executable, "-m", "nexus_v1.tests.test_thermal_smoke"]),
    ("test_thermal_timing",      [sys.executable, "-m", "nexus_v1.tests.test_thermal_timing"]),
    ("test_thermal_differentiation", [sys.executable, "-m", "nexus_v1.tests.test_thermal_differentiation"]),
    ("test_thermotaxis",         [sys.executable, "-m", "nexus_v1.tests.test_thermotaxis"]),
    ("test_thermotaxis_v2",      [sys.executable, "-m", "nexus_v1.tests.test_thermotaxis_v2"]),
    ("test_exp016_vital_thermotaxis", [sys.executable, "-m", "nexus_v1.tests.test_exp016_vital_thermotaxis"]),
    ("test_smoke_soma",          [sys.executable, "-m", "nexus_v1.tests.test_smoke_soma"]),
    ("test_skin_patches",        [sys.executable, "-m", "nexus_v1.tests.test_skin_patches"]),
]

results = {}
total = len(TESTS)

for i, (name, cmd) in enumerate(TESTS, 1):
    outfile = OUT_DIR / f"{name}.txt"
    if outfile.exists():
        print(f"[{i}/{total}] SKIP (exists): {name}")
        results[name] = "skipped"
        continue
    print(f"[{i}/{total}] Running: {name} ... ", end="", flush=True)
    try:
        proc = subprocess.run(
            cmd, capture_output=True, text=True,
            encoding="utf-8", errors="replace",
            timeout=300, cwd="j:/cell-cc"
        )
        output = proc.stdout + proc.stderr
        outfile.write_text(output, encoding="utf-8")
        status = "PASS" if proc.returncode == 0 else f"FAIL(rc={proc.returncode})"
        print(status)
        results[name] = status
    except subprocess.TimeoutExpired:
        print("TIMEOUT")
        results[name] = "TIMEOUT"
    except Exception as e:
        print(f"ERROR: {e}")
        results[name] = f"ERROR: {e}"

print("\n=== CAPTURE SUMMARY ===")
for name, status in results.items():
    print(f"  {status:20s} {name}")
print(f"\nFiles in: {OUT_DIR}")
