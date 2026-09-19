"""tss.adapters.typed_ports — U_T / U_Ṫ typed 端口 canonical 实现（G0-R1 R1-1）。

TYPE:INFRA — 端口层不构造任何新 Neuron/SynapticBundle/电路行为；它把
T1-B 冻结的两个转导口（`T1B_PORT_AND_TIMEBASE_CONTRACT.md` §三）从研究区
局部实现提升为可被 tss 生产侧消费的单一事实来源，并以 typed dataclass
禁止幅值/速率语义混用（G0-R1 方案 R1-1：不得再让裸 `u_i`/`dT_raw`
同时表示幅值与速率）。

RULES.md 强制三问：

  Q1 生物对应物：
    U_Ṫ（速率口，BRIDGE）：Type II AMH（A-δ）温升率信号——消费者
      `ThermalDeltaNeuron` 的既有 BIO 合同（dT/dt 检测器，
      REF: LaMotte & Campbell 1978 J Neurophysiol 41:924）。
    U_T（幅值口，长期 TARGET）：TRPV 家族幅值→受体电流转导
      （REF: Brauchi et al. 2004）；正式接入需 L1 输入语义改造
      （amplitude→receptor-current），属 T1B_FINAL_RULING 登记的
      G0_RECONNECT 升级合同——本轮只建接口存根（R1-3），不改 L1。

  Q2 物理结构：
    本模块零新电路。速率口的消费路径是既有链：
      UdotTSample.value → BaseGeneratorHandle.tick_rate_port()
        → tick() → _propagate()：L1(ThermalDeltaNeuron)
        → bundle_l1_hc → HC → bundle_in → ensemble → bundle_col
        → collector → OccurrenceClosure
    全部经既有 SynapticBundle.propagate()，无直接注入。

  Q3 参数依据（全部 CANONICAL_REFERENCE ≠ OPTIMAL，provenance=
    T1B_PORT_AND_TIMEBASE_CONTRACT §三/§四，held-out 锁定前预承诺）：
      S_CANON = 0.00137531 [u/T]   —— A 口斜率（cal30 稳态标定）
      Y_REF   = 0.0        [T]     —— PHYSICAL（环境参考温）
      G_CANON = 0.275062   [u·s/T] —— B 口增益 = S×τ_field（v1 尺度；
        G0-R0 已实测该量级在真实秒制下致 33.3% 子步 L1 钳位
        （B_BRIDGE_L1_SATURATION），v2 量级重标属 G0-R1
        r1_calibration——重标结果登记于该轮报告，不回写本常量，
        调用方经 `g=` 形参显式传入 v2 值）
      DT_EXT  = 1.0        [s]     —— MAINLINE_TIMEBASE_CONTRACT，
        非可调（锚=SkinPatch τ=5s + τ_env∈[20,2000]s）

调度器策略二分（G0-R1 §5，R-3 裁定 2026-09-19，正式修订
`G0R0_TIMEBASE_CONTRACT.md` §四的适用面）：
  REFERENCE_RECONSTRUCTION_POLICY = "S1"（线性插值——需要下一边界样本，
    只允许 replay/离线重建使用）
  LIVE_CAUSAL_POLICY = "S0"（零阶保持——零未来访问，live production
    唯一合法策略；禁止 live 路径访问未来 Boundary sample）
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import List, Sequence

# ── canonical 常量（provenance 见模块 docstring Q3）──
S_CANON: float = 0.00137531
Y_REF: float = 0.0
G_CANON: float = 0.275062
DT_EXT: float = 1.0

# ── 调度器策略二分（E-5/R-3 合同修订，见模块 docstring）──
REFERENCE_RECONSTRUCTION_POLICY: str = "S1"
LIVE_CAUSAL_POLICY: str = "S0"

_PORT_RATE = "U_dotT"
_PORT_AMPLITUDE = "U_T"


@dataclass(frozen=True)
class UdotTSample:
    """速率口样本（BRIDGE=B，T1B_FINAL_RULING）：u = g·ΔY/Δt_ext，带符号。

    字段：
      value:  u [u]，物理速率×增益（可为负——衰减段符号语义是 B 口
              资格判据之一，见 t1b_common SEMANTIC_FAIL 定义）
      t_phys: 样本物理时刻 [s]（边界帧时间基，Δt_ext 栅格）
      port:   固定 "U_dotT"——typed 标签，消费方必须断言，禁止把
              速率样本喂给幅值口（R1-1 语义混用禁令的机器化形式）
    """
    value: float
    t_phys: float
    port: str = _PORT_RATE


@dataclass(frozen=True)
class UTSample:
    """幅值口样本（长期 TARGET=A）：u = S·(Y−Y_ref)，瞬时幅值无整流无 clip。

    正式消费需 L1 amplitude→receptor-current 改造（G0_RECONNECT 升级
    合同，本轮未实施——见 `amplitude_port_stub()`）。dataclass 本身先冻结
    类型，供 D2/关系层 typed input candidates 引用。
    """
    value: float
    t_phys: float
    port: str = _PORT_AMPLITUDE


def u_t(y: float, s: float = S_CANON, y_ref: float = Y_REF) -> float:
    """A 口标量映射：u_T = S·(Y − Y_ref)（线性，无可违约项）。"""
    return s * (y - y_ref)


def u_dot_t(y_now: float, y_prev: float,
            dt_ext: float = DT_EXT, g: float = G_CANON) -> float:
    """B 口标量映射：u_Ṫ = g·(Y(t) − Y(t−Δt_ext))/Δt_ext（带符号物理差分）。"""
    return g * (y_now - y_prev) / dt_ext


def rate_port_series(y_samples: Sequence[float], t0: float = 0.0,
                     dt_ext: float = DT_EXT,
                     g: float = G_CANON) -> List[UdotTSample]:
    """把 Δt_ext 栅格的边界样本序列映射为速率口样本序列。

    状态初始化合同（T1-B C5）：prev=首样本 ⇒ u(0)=0，replay 逐位可复现
    （与 t1b_common 同一合同，此处是 canonical 实现）。
    """
    out: List[UdotTSample] = []
    prev = y_samples[0] if y_samples else 0.0
    for n, y in enumerate(y_samples):
        out.append(UdotTSample(value=u_dot_t(y, prev, dt_ext, g),
                               t_phys=t0 + n * dt_ext))
        prev = y
    return out


def amplitude_port_stub() -> None:
    """A 长期口 production 接入点存根（G0-R1 R1-3：只建升级接口）。

    正式实现属 G0_RECONNECT 升级合同（T1B_FINAL_RULING：
    FINAL_MAINLINE_TARGET=A，需 L1 输入语义 amplitude→receptor-current
    改造）——不在 G0-R1 顺手重新设计感受神经元（方案 §3-R1-3 明令）。
    """
    raise NotImplementedError(
        "U_T amplitude port requires the L1 amplitude→receptor-current "
        "upgrade (G0_RECONNECT contract, T1B_FINAL_RULING). Registered "
        "interface only in G0-R1 — use the U_dotT rate port (bridge) "
        "via BaseGeneratorHandle.tick_rate_port().")
