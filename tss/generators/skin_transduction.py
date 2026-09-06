"""tss.generators.skin_transduction — P2-A1b-2：皮肤输出 → 生成元输入的转导映射。

TYPE:INFRA（纯函数映射，不含物理机制，不新建神经元/Bundle）

背景：评判(`document - 2026-07-21T145017.166.md` P2-A1b-2 章节)裁定转导
映射的形式与校准原则：

    u_i(t) = clip[ κ_i · (q_i^skin(t) - q_i0) + b_i ]

目标不是把皮肤输出的全部极值线性塞进 𝒟_disc^G，而是：
    q_reference ↦ u_interior ⊂ 𝒟_disc^G
并与两端保持裕量：
    u_on + Δ_low < u_interior < 0.05 - Δ_high
不能用皮肤输出的最小值/最大值直接反推 κ_i——极端输入允许被 clipping
压缩，原始 q_i^skin(t) 仍完整保存在物理轨迹中（不在本模块，在上游
ThermalFieldGraph/GeneratorTrajectory）。

参考物理过程集合的选择与依据
-----------------------------
采用 P2-A2b/P2-A1b-1 已经测量过的 **T-STP-6/7/8 六场景**（Γ_A~Γ_F，
`nexus_v1/tests/test_skin_three_point.py`，注入幅度统一为1.0）作为
"参考物理过程集合"，而不是 P2-A1b-1 剂量-响应扫描的全部8个数量级：
  1. 这组数据不是本阶段新造的，是既有实验（P2-A2b过程可区分资格验收）
     的直接复用；
  2. 这组场景被设计为"有意义地不同的真实刺激模式"（位置反例/次序反例/
     单点-共同作用反例），代表典型接触事件，不是 dose-response 扫描里
     用来探测极端/钳位鲁棒性的探针幅度（0.01/50.0那种）；
  3. 已有全部6个场景的`[T0,T1,T2]`实测数据（见
     `cell-cell/工作报告/P2-A1b-0边界复核与生成元级可区分度_
     P2-A1b-1皮肤输出分布_2026-07-21.md`第三部分）：
       Γ_A(仅s1)=[61.8260,49.5116,43.6483]
       Γ_B(仅s3)=[43.6483,49.5116,61.8260]
       Γ_C(先s1后s3)=[43.6522,49.5116,61.8221]
       Γ_D(先s3后s1)=[61.8221,49.5116,43.6522]
       Γ_E(仅s2中心)=[49.5116,55.9627,49.5116]
       Γ_F(s1+s3两端)=[52.7371,49.5116,52.7371]
     全部18个数值的范围：[43.6483, 61.8260]。

映射参数推导（EXP-P2A1b2-001）
-------------------------------
- `q_i0 = 0.0`：P2-A1b-1已测得的静息基线（`rest_baseline()`实测
  `[T0,T1,T2]=[0,0,0]`），不是假设值。
- 目标区间 `u_interior = [0.005, 0.03]`：
    下界 0.005 ≈ u_on 的约10倍（P2-A1b-0实测：T_obs=5000时u_on区间
    [0.0005,0.0006]，T_obs=20000时[0.0004,0.0005]），留足够裕量避免
    落入低端启动临界区（该区域触发行为对进程/种子敏感）。
    上界 0.03 比 𝒮_cap 转折点 0.05（P2-A1a-R实测：activation_L1=
    min(200u,10)精确在u=0.05转为常数）留40%裕量（Δ_high=0.02），
    避免参考场景被L1钳位压平。
- 两点线性求解（参考范围[43.6483,61.8260] ↦ 目标范围[0.005,0.03]）：
    κ_i = (0.03-0.005) / (61.8260-43.6483) ≈ 0.0013759
    b_i = 0.005 - κ_i × 43.6483 ≈ -0.0550663
  校验：κ_i×43.6483+b_i = 0.005000；κ_i×61.8260+b_i = 0.030000（两端精确落点）。
- clip 边界（不是校准区间本身，是安全护栏，允许极端输入被压缩）：
    u_clip_min = 0.0（自然地板——ThermalDeltaNeuron内部本身也有
                       max(0,...)，此处冗余但无害，且避免负值u语义不清）。
    u_clip_max = 0.04（𝒮_cap转折0.05以下留裕量，极端dose场景如
                        P2-A1b-1剂量扫描的50.0注入（q≈3091.30）映射后
                        会被clip到0.04，不会把危险数值送进生成元）。

范围声明（本轮不做）
--------------------
本模块只提供经过校准的纯映射函数，**不接入 `BaseGenerator` 的实际驱动
循环**——评判的冻结执行顺序把"驱动权归属守卫（MANUAL_CALIBRATION/
WORLD_COUPLED）"放在下一步 P2-A1b-3，本轮只交付独立可测试的映射本身，
避免在守卫落地前引入 `feed()` 潜在双重驱动的风险窗口。
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class TransductionConfig:
    """转导映射的标定参数（纯数据，不含行为）。"""
    q_i0: float
    kappa_i: float
    b_i: float
    u_clip_min: float
    u_clip_max: float


def transduce(q_skin: float, config: TransductionConfig) -> float:
    """u_i(t) = clip[ κ_i·(q_i^skin(t) - q_i0) + b_i ]，纯函数，无副作用。"""
    u = config.kappa_i * (q_skin - config.q_i0) + config.b_i
    return max(config.u_clip_min, min(config.u_clip_max, u))


# EXP-P2A1b2-001：见模块docstring"映射参数推导"完整推导过程。
# 参考集合：T-STP-6/7/8 六场景（Γ_A~Γ_F，注入幅度1.0）实测温度范围
# [43.6483, 61.8260] ↦ 目标区间 [0.005, 0.03]（𝒟_disc^G内部，两端各留
# 裕量避开u_on临界区与𝒮_cap转折点）。
REFERENCE_TRANSDUCTION_CONFIG = TransductionConfig(
    q_i0=0.0,
    kappa_i=(0.03 - 0.005) / (61.8260 - 43.6483),
    b_i=0.005 - (0.03 - 0.005) / (61.8260 - 43.6483) * 43.6483,
    u_clip_min=0.0,
    u_clip_max=0.04,
)
