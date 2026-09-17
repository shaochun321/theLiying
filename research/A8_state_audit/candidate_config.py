"""candidate_config.py — F1 canonical 配置 + 同实例参数指纹（P0-2/P0-3）。

TYPE:INFRA（research/ 隔离层）

## 尺度分歧的事实（第三轮核心）

第二轮报告混用了两套 C：
  Scale-A  C=1.0,   R=0.6   ← 原语默认；**恰等于 H_τ 自身的 (C=1.0, R=0.6)**
  Scale-B  C=0.001, R=600   ← C 来自 RelationInputNeuron
两套 τ=R·C=0.6 s（600 步）**相同**；差的是电流→电压增益（ΔV=I·dt/C，差 1000 倍）。

项目内的电容实际跨度（本轮实测）：
  RelationInputNeuron   C=0.001        （level-2 换能神经元）
  adapter collector     C=7.920427e-07 （EXP-C1-01 标定，使 r_min 单脉冲越阈）
  entry_gate / H_τ      C=1.0          （level-1 的"钙池"模块，非神经元）
⇒ 项目自身在层级间就是异质的，不存在唯一"正确"C。**这是本轮最重要的发现**：
  结论对 C 的依赖是 1000 倍量级的，C 的选择必须由理论裁定，不能由 Agent
  为保留/否决结果而选。

## 本轮 canonical 选择与理由（必须与结论一起读）

canonical = **Scale-B（C=0.001, R=600）**，理由：
  候选消费的是**分级 relation current**（level-2 信号），而该信号的设计域
  （EXP-C1-01：r_min=0.0026）只在"小 C 膜"上才有意义；C=0.001 由
  RelationInputNeuron 在这一接口上实例化。

★ 自曝风险：该选择**保留了 M5**。因此本模块同时强制输出 Scale-A 的完整
  对照（`--both` 默认开启），并在报告中明确：**若理论裁定 canonical 应为
  Scale-A，则 F1 结论为 M1-only / F1_REJECTED**——不得为了让结果存活而
  默认 Scale-B。

## canonical 的 DT 限制声明（冻结契约，依据 = clamp_integrity C3 实测）

canonical = 项目 dt=0.001 + hard clamp。hard clamp 是"物理有限钳位
（clamp_gm=10 漏极）在项目 dt 下显式积分数值不稳定"的理想化替身：
有限钳位高支在 dt=0.001 下被数值抹除、在 dt/10 与 dt/100 下恢复并趋近
连续预测 V_high*=1.2988（PHYSICAL_BISTABILITY_DT_LIMITED）。
⇒ Z 高态读数 1.0 = 钳位值，物理高支值 ≈1.299；一切资格结论都必须
  连同这一 DT 依赖一起引用，不得只引"Z=1.0 双稳"。

## fingerprint 守卫（P0-3）

所有实验模块启动时必须调用 `assert_fingerprint(cfg)`；指纹不一致 →
INVALID_EXPERIMENT，不得给资格结论。指纹含：C、R、dt、θ、gm、反馈拓扑(N)、
V_rail、钳位模式、钳位 gm、输入换能、输入增益、供能模型。

## 第四轮变更（依据 F1_FEEDBACK_POWER_CONTRACT.md）

1. **N_feedback: 3 → 1**（最小化）：外部实测 N=1 双稳；第三轮报告 §10 自认
   "N=1 已双稳、N≥1 恒双稳" ⇒ N=3（仅为兼容第二轮无出处 k=3.0）非最小。
   仅当 N=1 失败某资格条件时才允许 N>1。
2. **supply_model 进入指纹**：路径 B（电导×供电负载线闭解）为新 canonical
   供能模型；第三轮旧指纹 LEGACY_FP_ROUND3 退役为历史指纹，不得作为最终
   候选指纹引用。
"""
from __future__ import annotations

import hashlib
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

DT = 0.001

# ── canonical（Scale-B，见模块 docstring 的裁定要求） ──
CANONICAL = {
    "name": "Scale-B",
    "C": 0.001,
    "R": 600.0,
    "dt": DT,
    "tau_steps": 600.0,
    "theta": 0.3,          # MOSFET.v_threshold 默认（semiconductor.py:117）
    "gm": 1.0,             # MOSFET.gm 默认
    "n_feedback_fets": 1,  # 物理支路数；第四轮最小化 3→1（外部实测 N=1 双稳
                           #   + 第三轮报告 §10 "N≥1 恒双稳" ⇒ N=3 非最小）
    "v_rail": 1.0,         # PowerRail vdd（= entry_gate _DEFAULT_V_CLAMP）
    "rail_r_internal": 0.0,
    "supply_model": "B_conductance_load_line",  # 契约路径 B：
                           #   I_fb = G(Vg)·vdd/(1+G·Rs)，G = Σ (gm/V_REF)(Vg−θ)
    "clamp_mode": "hard",  # "hard" | "finite"
    "clamp_gm": 10.0,      # 同 entry_gate _DEFAULT_GM_CLAMP
    "clamp_threshold": 1.0,
    "input": "graded_relation_current",
    "k_in": 0.5,           # frozen 换能权重（transducer w=0.3 惯例 + DEG-014 家族
                           #   w≤0.5 上限；修正记录：曾误设 1.0，使单枚 c_ro 事件
                           #   ΔV=0.434>V_u 即 OR 型闩锁，破坏等计数双胞胎设计）
}

# ── 诊断对照（报告 §八 要求，必须与 canonical 同码跑） ──
SCALE_A_DIAG = dict(CANONICAL, name="Scale-A", C=1.0, R=0.6)
SCALE_B_DIAG = dict(CANONICAL, name="Scale-B", C=0.001, R=600.0)
# 第三轮 legacy 配置（N=3）：仅供勘误对照实验（clamp_integrity legacy 段、
# 能耗对照），不得作为资格结论输入
LEGACY_N3_DIAG = dict(CANONICAL, name="Legacy-N3", n_feedback_fets=3)
# 第三轮退役指纹（供能因果闭合前生成，方案 §十六：不得再作最终候选指纹）
LEGACY_FP_ROUND3 = "72c828f910f7243b"


def fingerprint(cfg: dict) -> str:
    """同实例参数指纹（P0-3）：C/R/dt/θ/gm/反馈拓扑/Vrail/钳位/输入/供能模型。"""
    keys = ("C", "R", "dt", "theta", "gm", "n_feedback_fets", "v_rail",
            "rail_r_internal", "clamp_mode", "clamp_gm", "clamp_threshold",
            "input", "k_in", "supply_model")
    payload = json.dumps({k: cfg.get(k) for k in keys}, sort_keys=True)
    return hashlib.sha256(payload.encode()).hexdigest()[:16]


def assert_fingerprint(cfg: dict, expected: str | None = None) -> str:
    """守卫：打印并校验指纹；不一致抛 INVALID_EXPERIMENT。"""
    fp = fingerprint(cfg)
    name = cfg.get("name", "?")
    print(f"[fingerprint] {name}: {fp}  "
          f"(C={cfg['C']}, R={cfg['R']}, dt={cfg['dt']}, N={cfg['n_feedback_fets']}, "
          f"clamp={cfg['clamp_mode']}, k_in={cfg['k_in']})")
    if expected is not None and fp != expected:
        raise RuntimeError(
            f"INVALID_EXPERIMENT: fingerprint mismatch "
            f"({fp} != {expected}) —— 各实验未使用同一 candidate 实例")
    return fp


def energy_state() -> str:
    """能源声明（第四轮更新）：供能已因果化（路径 B），局部闭合状态由
    z_block_and_energy 的残差收敛实验裁定，此处不预写结论。"""
    return ("ENERGY_SUPPORT=CAUSAL_RAIL_LOAD_LINE(path-B); "
            "LOCAL_ENERGY_CLOSURE=SEE_RESIDUAL_CONVERGENCE_TEST; "
            "GLOBAL_ENERGY_CLOSURE=NOT_ESTABLISHED")


if __name__ == "__main__":
    print("=" * 68)
    print("canonical 配置与 fingerprint（P0-2/P0-3）")
    print("=" * 68)
    for cfg in (CANONICAL, SCALE_A_DIAG, SCALE_B_DIAG):
        assert_fingerprint(cfg)
    print(f"\n{energy_state()}")
    print("\n注意：CANONICAL 与 SCALE_B_DIAG 指纹相同（同一物理系统）；")
    print("      SCALE_A_DIAG 指纹不同 ⇒ 若混用必须报 INVALID_EXPERIMENT。")
    print("\n★ 自曝：canonical 选择（Scale-B）保留了 M5。Scale-A 对照见")
    print("  f1_revalidation.py —— 若裁定为 Scale-A，F1 = M1 only / REJECTED。")
