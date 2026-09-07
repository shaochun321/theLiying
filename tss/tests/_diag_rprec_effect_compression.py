"""tss.tests._diag_rprec_effect_compression — LIM-RPREC-READOUT-001 压缩链诊断。

TYPE:INFRA（探索性诊断，非 pass/fail 测试，同 `_diag_*` 惯例）

背景：外部实测反馈（cell-cell/交叉比对/TSS 实测错误与缺陷反馈清单.md §1，
2026-09-06）复现了 `test_r_prec_replay_simple` 效应量层稳定失败：
权重学习 +0.97%（0.108750→0.109802），但下游电流积分仅 +0.0033%，
未达 1% 资格阈值，3 个 hashseed 复现。本诊断**只定位压缩链，不改任何参数**。

假设的压缩链（本脚本逐环节实测验证）：

  环节A（w→G 工作点压缩）：Memristor R(w)=r_min+(r_max−r_min)(1−w)，
    低 w 工作点下 ΔG/G = Δw·(r_max−r_min)/R ≪ Δw/w。
    解析预估：Δw=+0.001052 @ w≈0.109 → ΔG/G ≈ 0.117%（约 8× 压缩）。

  环节B（训练期积分稀释）：效应量测的是**整个训练期**的电流积分，而
    三因子学习的 da_ema_tau=50000 步 ≈ 整个训练窗（P2-B1 校准记录），
    权重增量后置——积分的大部分时段 w≈w₀，稀释掉剩余 ~35×。

运行方式：
    PYTHONIOENCODING=utf-8 PYTHONHASHSEED=0 python -m tss.tests._diag_rprec_effect_compression
"""
import os
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

import numpy as np
from tss.relations.temporal_r_prec_plastic import RPrecCircuitT1Plastic

DT = 0.001
TRAIN_STEPS = 50000
W_SAMPLE_EVERY = 500
TAIL_FRACTION = 0.1      # 环节B隔离：只比最后 10% 窗口的电流


def _train(circuit, da_concentration):
    """训练并记录 w(t) 采样与逐步 bundle 电流。"""
    w_traj, current_trace = [], []
    for t in range(TRAIN_STEPS):
        inj_a = 1.0 if t < TRAIN_STEPS // 2 else 0.0
        inj_b = 1.0 if t >= TRAIN_STEPS // 3 else 0.0
        circuit.rprec_xi_a.step(inj_a, DT)
        circuit.rprec_xi_b.step(inj_b, DT)
        circuit.step_rprec_plastic(DT, da_concentration=da_concentration)
        currents = circuit.bundle_rprec_to_da.propagate()
        current_trace.append(currents[0] if currents else 0.0)
        if t % W_SAMPLE_EVERY == 0:
            w_traj.append((t, circuit.bundle_rprec_to_da.weight_matrix()[0][0]))
    w_traj.append((TRAIN_STEPS, circuit.bundle_rprec_to_da.weight_matrix()[0][0]))
    return w_traj, np.array(current_trace)


def run():
    print("=" * 72)
    print("LIM-RPREC-READOUT-001 压缩链诊断（纯测量，零参数改动）")
    print("=" * 72)

    # ── 训练两组 ──
    print("训练学习组（da=0.5, plastic）...")
    c_learn = RPrecCircuitT1Plastic()
    mem = c_learn.bundle_rprec_to_da._memristors[0][0]
    r_min, r_max = mem.r_min, mem.r_max
    w_traj, cur_learn = _train(c_learn, 0.5)

    print("训练基线组（da=0.5, frozen）...")
    c_base = RPrecCircuitT1Plastic()
    c_base.bundle_rprec_to_da.config.learning_rule = "frozen"
    _, cur_base = _train(c_base, 0.5)

    w0, w1 = w_traj[0][1], w_traj[-1][1]
    dw = w1 - w0

    # ── 环节A：w→G 工作点压缩（解析，用实际 Memristor 常量）──
    def G(w):
        return 1.0 / (r_min + (r_max - r_min) * (1.0 - w))
    dG_rel = (G(w1) - G(w0)) / G(w0)
    print("\n── 环节A：w→G 工作点压缩 ──")
    print(f"  Memristor: r_min={r_min}, r_max={r_max}")
    print(f"  w: {w0:.6f} → {w1:.6f}  (Δw={dw:+.6f}, Δw/w={dw / w0 * 100:.3f}%)")
    print(f"  G: {G(w0):.6f} → {G(w1):.6f}  (ΔG/G={dG_rel * 100:.4f}%)")
    print(f"  ⇒ 环节A压缩比 = (Δw/w)/(ΔG/G) = {dw / w0 / dG_rel:.1f}×")

    # ── 环节B：训练期积分稀释 ──
    sum_l, sum_b = float(np.sum(cur_learn)), float(np.sum(cur_base))
    whole_rel = (sum_l - sum_b) / sum_b
    tail_n = int(TRAIN_STEPS * TAIL_FRACTION)
    tail_l = float(np.sum(cur_learn[-tail_n:]))
    tail_b = float(np.sum(cur_base[-tail_n:]))
    tail_rel = (tail_l - tail_b) / tail_b if tail_b > 0 else float("nan")

    # w(t) 增量到位时刻（后置程度量化）
    milestones = {}
    for frac in (0.25, 0.50, 0.75):
        target = w0 + dw * frac
        t_hit = next((t for t, w in w_traj if w >= target), None)
        milestones[frac] = t_hit
    print("\n── 环节B：训练期积分稀释 ──")
    print(f"  全程电流积分: learned={sum_l:.6f} vs frozen={sum_b:.6f} "
          f"→ 相对差 {whole_rel * 100:.4f}%（反馈实测 ~0.0033% 的复现口径）")
    print(f"  末段 {int(TAIL_FRACTION * 100)}% 窗口: learned={tail_l:.6f} vs "
          f"frozen={tail_b:.6f} → 相对差 {tail_rel * 100:.4f}%")
    print(f"  Δw 到位时刻: 25%@step {milestones[0.25]}, 50%@{milestones[0.50]}, "
          f"75%@{milestones[0.75]}（训练全长 {TRAIN_STEPS}）")
    dilution = dG_rel / whole_rel if whole_rel > 0 else float("inf")
    print(f"  ⇒ 环节B稀释比 = (ΔG/G)/(全程ΔI/I) = {dilution:.1f}×")

    # ── 结论 ──
    print("\n" + "=" * 72)
    print("结论")
    print("=" * 72)
    print(f"  总压缩 = (Δw/w)/(全程ΔI/I) = {dw / w0 / whole_rel:.0f}× "
          f"= 环节A {dw / w0 / dG_rel:.1f}× × 环节B {dilution:.1f}×")
    print(f"  即使消除环节B（末段窗口口径），效应量上限≈ΔG/G="
          f"{dG_rel * 100:.3f}% —— 仍低于 1% 阈值一个数量级。")
    print(f"  ⇒ 1% 资格在当前 Δw≈{dw:.4f} 量级下**结构性不可达**：需要 "
          f"Δw≈{0.01 * (r_min + (r_max - r_min) * (1 - w0)) / (r_max - r_min):.4f}"
          f"（约 {0.01 / dG_rel:.0f}× 现有学习量）或读出结构变更。")
    print("  与 P2-B1R 原结论一致（单束信噪比不足，非参数问题）。")
    print("  本诊断不改动任何参数——效应量修复若立项，须走独立设计轮。")
    return 0


if __name__ == "__main__":
    sys.exit(run())
