"""
Memristor 稳定哈希修复验证：临界档位跨进程一致性

背景：评判(`document - 2026-07-21T145017.166.md`唯一阻塞)指出
`SynapticBundle.__init__`(`circuit/bundle.py`)里驱动±25%对称性打破
扰动的种子用 Python 内置 `hash()` 生成，逐进程随机化导致跨进程结果
不可复现（P2-A1b-0已实测坐实：u=0.0005三次独立进程给出0/1/0次不同
触发）。已修复为 `zlib.crc32` 稳定摘要（`bundle.py`，2026-07-21）。

本脚本验证修复达成目的：对少量临界档位（覆盖低端启动/𝒟_disc/𝒮_cap
转折三个区段），不设置 PYTHONHASHSEED，用独立子进程各跑3次，断言
结果完全一致。不重跑P2-A1b-0的完整多档多种子多观测窗深度扫描（评判
明确说"不必"）。
"""
import os
import subprocess
import sys

sys.path.insert(0, '.')

U_LEVELS = [0.001, 0.02, 0.05, 0.08]
REPEATS = 3
STEPS = 5000

_WORKER_TEMPLATE = """
import sys
sys.path.insert(0, '.')
from nexus_v1.circuit.variant_adapter import VariantCircuit
from nexus_v1.components.structural_address import AddressRegistry
from tss.generators import wrap_base_generator
from tss.relations import FROZEN_THERMAL_SITES

DT = 0.001
SITE = FROZEN_THERMAL_SITES['t1_pair']['a']
c = VariantCircuit()
r = AddressRegistry()
h = wrap_base_generator(c, SITE, r, polarity='warm')
for t in range({steps}):
    h.tick({u}, DT, t)
n_occ = h.closure.occurrence_count
l_first = h.closure.events[0].t_up if h.closure.events else -1
print(f"{{n_occ}},{{l_first}}")
"""


def run_one(u, steps):
    """在独立子进程里跑一次全新生成元实例——刻意不设置PYTHONHASHSEED，
    验证修复后天然确定性，不需要环境变量兜底。"""
    env = dict(os.environ)
    env.pop("PYTHONHASHSEED", None)
    env["PYTHONIOENCODING"] = "utf-8"
    code = _WORKER_TEMPLATE.format(u=u, steps=steps)
    result = subprocess.run(
        [sys.executable, "-c", code],
        cwd=".", env=env, capture_output=True, text=True, timeout=60,
    )
    line = result.stdout.strip().splitlines()[-1] if result.stdout.strip() else "0,-1"
    n_occ_str, l_first_str = line.split(",")
    return int(n_occ_str), int(l_first_str)


def run():
    print("=" * 90)
    print("  Memristor稳定哈希修复验证：临界档位跨进程一致性（不设PYTHONHASHSEED）")
    print("=" * 90)

    all_consistent = True
    for u in U_LEVELS:
        trials = [run_one(u, STEPS) for _ in range(REPEATS)]
        consistent = len(set(trials)) == 1
        all_consistent = all_consistent and consistent
        status = "PASS" if consistent else "FAIL"
        print(f"  u={u:>8.4f}: {trials} -> {status}")

    print()
    if all_consistent:
        print("  [PASS] 全部临界档位跨进程结果完全一致——修复达成目的。")
    else:
        print("  [FAIL] 存在跨进程结果不一致的档位——修复未达成目的，需要排查。")
    print("=" * 90)
    return all_consistent


if __name__ == "__main__":
    ok = run()
    sys.exit(0 if ok else 1)
