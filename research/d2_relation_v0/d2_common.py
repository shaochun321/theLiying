"""d2_common.py — D2-0/P2-B 共享层：多 site parent 构造、轨迹编排、
RawOccurrenceTrack 录制与读取。

TYPE:INFRA（research/ 层；production READ_ONLY——G0 只运行不修改）。

依据：外部《D2-0/P2-B 方案》44 节 + 《反馈_D2-0-P2-B方案评判》全接受
裁定（E-1~E-7 + R-1~R-3 ACCEPTED，执行序 §26 冻结）。

## 冻结常量（不读取 GBK 历史 JSON，常量+provenance 引用，Step0 决策）

  G_V2 = 2.512531e-2   # G0-R1 R1-2 canonical（research/g0_reconnect/
                       # r1_occ/data/r1_calibration.json；规则
                       # (u_clamp/2)/max|Ẏ|_cal，CANONICAL_REFERENCE）
  DT_G = 0.001         # GENERATOR_DT 物理秒（G0-R0 状态A裁定）
  U_DRIVE = 0.03       # parent 驱动幅值（< L1 钳位起点 0.05，R1-2 合法域
                       # 内；G0-R1 hidden dynamics 同幅值先例）
  parent closure = G0-R1 冻结 canonical（theta_up=0.01/theta_down=0.001/
                   rearm=500）——§22 仅禁止 relation closure 抄用，
                   parent G0 本身沿用其已资格化参数。

## parent 驱动模式

MANUAL rate-port 脉冲编排（T0~T1 既有方法论：绕开 world/body，手动喂
u 序列精确控制时序/延迟/重叠——C0-C5 矩阵需要可控 Δt，World 耦合无法
编排）。每条轨迹一个 fresh VariantCircuit，wrap site28(G_a)/site31(G_b)
（攻击轨迹另 wrap site23(G_c)），各 handle 物理链独立、支撑地址不同、
occurrence 独立（方案 §4 要求逐项满足）。

## RawOccurrenceTrack（E-1 数据合同，反馈 §二）

raw track 是**外部实验记录**（研究观察面），不是新的内部生成元状态；
其唯一目的是给 𝒩 提供可复现输入。D2 运行时禁止伸手进 G0 对象——
消费录制轨迹经显式 𝒩 是唯一合法路径（方案 §3 末段）。
最低字段（反馈 §二清单）：t_phys / site / u(t) / collector 信号 /
phys_support / epoch / energy 快照。
IMMUTABLE_PARENT_TRACE：生成后只读；后续 N0-N3/relation/标定/closure/
负对照全部读同一缓存；禁止换 relation 参数就重跑 World→G0（反馈 §2.1）。
"""
from __future__ import annotations

import csv
import os
import sys
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.abspath(os.path.join(_HERE, '..', '..')))

from nexus_v1.circuit.variant_adapter import VariantCircuit  # noqa: E402
from nexus_v1.components.structural_address import AddressRegistry  # noqa: E402
from tss.generators import wrap_base_generator  # noqa: E402
from tss.relations.site_selection import FROZEN_THERMAL_SITES  # noqa: E402

DATA = os.path.join(_HERE, 'data')
TRACES = os.path.join(DATA, 'parent_traces')

# ── 冻结常量（provenance 见模块 docstring）──
G_V2 = 2.512531e-2
DT_G = 0.001
U_DRIVE = 0.03
PARENT_THETA_DOWN = 0.001
PARENT_REARM = 500

# R-1 裁定的 parent 定点
SITE_A = FROZEN_THERMAL_SITES["t1_pair"]["a"]   # 28 CENTER
SITE_B = FROZEN_THERMAL_SITES["t1_pair"]["b"]   # 31 NB1
SITE_C = 23                                      # NB2（仅攻击实验，R-1）


@dataclass(frozen=True)
class Pulse:
    """一个 rate-port 驱动脉冲：[t_on, t_on+length) 内 u=amp。"""
    t_on: int
    length: int
    amp: float = U_DRIVE


@dataclass(frozen=True)
class TrajSpec:
    """一条 parent 轨迹的完整编排（确定性，无 RNG）。"""
    tid: str
    t_total: int
    pulses: Dict[str, Tuple[Pulse, ...]]   # site 标签("A"/"B"/"C") → 脉冲序列
    note: str = ""


def build_parents(sites: Dict[str, int]):
    """新建 fresh circuit 并按 {标签: site_index} wrap 各 parent handle。"""
    circuit = VariantCircuit()
    registry = AddressRegistry()
    handles = {}
    for label, site in sites.items():
        h = wrap_base_generator(circuit, site, registry,
                                polarity="warm",
                                theta_down=PARENT_THETA_DOWN)
        h.closure.rearm_min_steps = PARENT_REARM
        handles[label] = h
    return circuit, handles


def run_trajectory(spec: TrajSpec):
    """执行编排并逐步录制 RawOccurrenceTrack。

    返回 (rows, occurrences)：rows=逐子步记录 dict 列表；
    occurrences={label: [Occurrence,...]}（完成的闭合）。
    """
    sites = {}
    for label in spec.pulses:
        sites[label] = {"A": SITE_A, "B": SITE_B, "C": SITE_C}[label]
    _circuit, handles = build_parents(sites)
    rows: List[dict] = []
    occs = {label: [] for label in handles}
    for k in range(spec.t_total):
        row = {"k": k, "t_phys": k * DT_G}
        for label, h in handles.items():
            u = 0.0
            for p in spec.pulses[label]:
                if p.t_on <= k < p.t_on + p.length:
                    u = p.amp
                    break
            ev = h.tick(u, DT_G, k)
            if ev is not None:
                occs[label].append(ev)
            row[f"u_{label}"] = u
            row[f"col_{label}"] = h.collector.pre_trace
            row[f"sup_{label}"] = int(h.l1.activation > 0.0)
            row[f"epoch_{label}"] = h.closure.epoch_id
        if k % 100 == 0:   # energy 快照（反馈 §二"where available"）
            for label, h in handles.items():
                row[f"energy_{label}"] = sum(
                    n.energy for n in (h.l1, h.hc, *h.ensemble, h.collector))
        rows.append(row)
    return rows, occs, handles


def write_track(tid: str, rows: List[dict]) -> str:
    """写 IMMUTABLE_PARENT_TRACE（UTF-8）；已存在则拒绝覆盖（不可变缓存）。"""
    os.makedirs(TRACES, exist_ok=True)
    path = os.path.join(TRACES, f"{tid}.csv")
    if os.path.exists(path):
        raise FileExistsError(
            f"IMMUTABLE_PARENT_TRACE 已存在，禁止覆盖：{path}"
            "（如需重生成 parent process 本身，删除旧缓存并在报告登记）")
    fieldnames: List[str] = []
    for r in rows:
        for k in r:
            if k not in fieldnames:
                fieldnames.append(k)
    with open(path, 'w', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        w.writerows(rows)
    return path


def read_track(tid: str) -> List[dict]:
    """只读消费缓存轨迹（数值字段转 float/int）。"""
    path = os.path.join(TRACES, f"{tid}.csv")
    out = []
    with open(path, newline='', encoding='utf-8') as f:
        for r in csv.DictReader(f):
            row = {}
            for k, v in r.items():
                if v is None or v == "":
                    continue
                if k == "k" or k.startswith(("sup_", "epoch_")):
                    row[k] = int(v)
                else:
                    row[k] = float(v)
            out.append(row)
    return out
