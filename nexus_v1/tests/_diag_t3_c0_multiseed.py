"""nexus_v1.tests._diag_t3_c0_multiseed — T3-C0 第3点：多 PYTHONHASHSEED 对照。

方案依据：第十八节 18.4 第3点。批判九指出容差不应是理论猜测，应基于实测
分布。本脚本在至少 2 个固定 `PYTHONHASHSEED` 下（子进程隔离，因为 hash
扰动只在进程启动时固定一次）各跑一遍 `_probe_t3_c0_seed.py` 的核心场景，
汇总 ε_swap/ε_equal/ε_ratio 的实测范围，用于校准 T-RPT-2/T-RPT-4 的容差
（不是拍脑袋，是真实测多次取范围）。
"""

import sys
import os
import json
import subprocess

_SEEDS = ["0", "1", "42"]  # 至少2个固定seed对照（方案18.2已确认，不追求"95%seed覆盖"）


def run_seed_probe(seed: str) -> dict:
    env = dict(os.environ)
    env["PYTHONHASHSEED"] = seed
    env["PYTHONIOENCODING"] = "utf-8"
    repo_root = os.path.join(os.path.dirname(__file__), "..", "..")
    result = subprocess.run(
        [sys.executable, "-m", "nexus_v1.tests._probe_t3_c0_seed"],
        cwd=repo_root, env=env, capture_output=True, text=True, timeout=60,
    )
    if result.returncode != 0:
        raise RuntimeError(f"seed={seed} 子进程失败: {result.stderr}")
    return json.loads(result.stdout.strip())


if __name__ == "__main__":
    print(f"[T3-C0-3] 多 PYTHONHASHSEED 对照（seeds={_SEEDS}）")
    print(f"{'seed':<8}{'eps_equal':>12}{'eps_swap_a':>12}{'eps_swap_b':>12}{'eps_ratio':>12}")

    all_results = []
    for seed in _SEEDS:
        r = run_seed_probe(seed)
        all_results.append(r)
        print(f"{r['pythonhashseed']:<8}{r['eps_equal']:>12.4f}{r['eps_swap_a']:>12.4f}"
              f"{r['eps_swap_b']:>12.4f}{r['eps_ratio']:>12.4f}")

    eps_equal_vals = [r["eps_equal"] for r in all_results]
    eps_swap_vals = [r["eps_swap_a"] for r in all_results] + [r["eps_swap_b"] for r in all_results]
    eps_ratio_vals = [r["eps_ratio"] for r in all_results]

    print(f"\neps_equal  范围: [{min(eps_equal_vals):.4f}, {max(eps_equal_vals):.4f}]")
    print(f"eps_swap   范围: [{min(eps_swap_vals):.4f}, {max(eps_swap_vals):.4f}]")
    print(f"eps_ratio  范围: [{min(eps_ratio_vals):.4f}, {max(eps_ratio_vals):.4f}]")

    max_observed = max(max(eps_equal_vals), max(eps_swap_vals), max(eps_ratio_vals))
    recommended_tol = max_observed * 1.5  # 留50%余量，同T-DTF/T-TSC既有惯例的保守系数
    print(f"\n最大实测偏差: {max_observed:.4f}")
    print(f"建议容差（1.5x余量）: {recommended_tol:.4f}")
