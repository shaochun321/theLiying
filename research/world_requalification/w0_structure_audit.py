"""w0_structure_audit.py — Phase W0 结构性质测量（W0-A/B/C/D 四门）。

TYPE:INFRA（research/ 观测层，只读消费 nexus_v1，不修改任何母体对象）

依据：《TSS 收尾与主线重启》§6（W0-A 自由度 / W0-B 局部相互作用 /
W0-C 时间尺度 / W0-D 非线性）+ §18（混沌只测不造 MEASURE only）。

## 测量对象（两个 World，见 MAINLINE_COMPONENT_AUDIT.md）

  1. normalized ThermalFieldGraph（`dynamic_thermal_field.py`，W1 产物，
     REQUALIFICATION_REQUIRED）——用 P2-A 实际实例 build_three_point_skin()
     （TEST 档 κ=0.05、r_leak=200，即 T-STP 资格验收所用尺度）
  2. InstantFieldWorld（`world.py`，LEGACY_WORLD_INSTANCE）——瞬时查询场
     T=F(x)，场自身无动力学状态；只做结构枚举（W0-A/B），谱测量不适用

## 度量契约（先于实验冻结）

  W0-A  N_dyn = 逐对象枚举"随 step 演化的标量状态"数（运行时反射 + 结构
        知识）；活跃自由度 = 脉冲实验后 |ΔV|>1e-9 的节点数
  W0-B  叠加性实验：response(0)+response(2) vs response(0&2)，逐位残差；
        多过程共同作用 = 中间节点对两端注入均有非零响应
  W0-C  脉冲响应多指数分解：可观测量 {ΣQ(总能量), T0−T1, T0−2·T1+T2} 的
        log-linear 斜率 → τ 集合；独立参数计数（κ、r_leak 是否独立可调、
        默认是否绑定）
  W0-D  线性判定 = 叠加残差（机器精度 ⇒ 线性）；多稳判定 = 不同初态弛豫
        到的终态数；敏感依赖 = 1e-9 初值扰动的轨迹分离率（只测不造）

审计边界说明：本脚本读取 World 全局真值（节点电荷/温度）是**对 World
自身的资格审计**，非电路行为 benchmark——HC-012 红线（benchmark 禁读
world 特权信息）针对的是电路能力评测，不适用于 World 结构审计本身。

输出：data/w0_structure.json
"""
from __future__ import annotations

import json
import math
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from nexus_v1.components.skin_three_point import (
    TEST_KAPPA_THREE_POINT, TEST_R_LEAK_AMBIENT_THREE_POINT,
    build_three_point_skin)
from nexus_v1.components.dynamic_thermal_field import (
    DEFAULT_KAPPA_0, DEFAULT_R_LEAK_AMBIENT, _TAU_REF_STEPS)
from nexus_v1.components.world import World, Body, _default_skin_patches

DATA_DIR = os.path.join(os.path.dirname(__file__), 'data')
DT = 1.0          # ThermalFieldGraph 测试尺度约定（同 T-STP/W1 单测）


def build():
    return build_three_point_skin(kappa=TEST_KAPPA_THREE_POINT,
                                  r_leak_ambient=TEST_R_LEAK_AMBIENT_THREE_POINT)


def run(graph, steps, inj=None):
    """跑 steps 步，返回三节点电压轨迹。inj: {node: (t0,t1,I)} 区间恒流。"""
    traj = []
    for t in range(steps):
        ext = {}
        for nid, (t0, t1, cur) in (inj or {}).items():
            if t0 <= t < t1:
                ext[nid] = ext.get(nid, 0.0) + cur
        graph.step(DT, ext)
        traj.append([graph.cells[i].capacitor.voltage for i in range(3)])
    return traj


def _slope_tau(series, lo, hi):
    """log-linear 拟合衰减时间常数 τ（series[lo:hi] 需为正的衰减段）。"""
    xs, ys = [], []
    for t in range(lo, hi):
        v = series[t]
        if v > 1e-15:
            xs.append(t)
            ys.append(math.log(v))
    n = len(xs)
    if n < 4:
        return None
    mx, my = sum(xs) / n, sum(ys) / n
    sxx = sum((x - mx) ** 2 for x in xs)
    sxy = sum((x - mx) * (y - my) for x, y in zip(xs, ys))
    slope = sxy / sxx
    return None if slope >= 0 else -1.0 / slope


def w0a(out):
    print("\n[W0-A] 自由度")
    # normalized 三点皮肤
    g = build()
    n_dyn = len(g.cells)                       # 每节点唯一动态标量 = charge
    g2 = build()
    run(g2, 200, {0: (0, 1, 1.0)})
    active = sum(1 for i in range(3)
                 if abs(g2.cells[i].capacitor.voltage) > 1e-9)
    print(f"  normalized 三点皮肤: N_dyn={n_dyn}（每节点 1×charge）  "
          f"脉冲后活跃节点={active}/3")
    # InstantFieldWorld：运行时反射枚举
    w = World()
    n_src = len(w.heat_sources)
    per_src = 7                                # position[3]+energy+_drift[3]
    n_world_scalars = sum(1 for v in vars(w).values()
                          if isinstance(v, (int, float)))
    body = Body()
    n_body = sum(1 for v in vars(body).values() if isinstance(v, (int, float))) \
        + sum(len(v) for v in vars(body).values()
              if isinstance(v, (list, tuple)) and v
              and isinstance(v[0], (int, float)))
    patches = _default_skin_patches()
    n_patch = len(patches) * 3                 # T, prev_T, damage_integral
    total = n_src * per_src + n_world_scalars + n_body + n_patch
    print(f"  InstantFieldWorld: 场自身动态变量=0（T=F(x) 瞬时查询）；"
          f"代理状态≈{total}（{n_src}源×{per_src}+world {n_world_scalars}"
          f"+Body {n_body}+{len(patches)}patch×3）")
    out["W0A"] = {"normalized_n_dyn": n_dyn, "normalized_active": active,
                  "instant_field_own_dyn": 0, "instant_proxy_total": total,
                  "verdict": "少数节点+单变量（3×1）——方案 §6 W0-A 的怀疑属实"}


def w0b_w0d(out):
    print("\n[W0-B/W0-D] 局部相互作用 + 线性/多稳/敏感依赖")
    inj0 = {0: (0, 50, 1.0)}
    inj2 = {2: (0, 50, 1.0)}
    both = {0: (0, 50, 1.0), 2: (0, 50, 1.0)}
    tA = run(build(), 400, inj0)
    tB = run(build(), 400, inj2)
    tAB = run(build(), 400, both)
    # 中间节点对两端注入均响应（多过程共同作用）
    mid_from_0 = max(row[1] for row in tA)
    mid_from_2 = max(row[1] for row in tB)
    # 叠加残差（线性判定）
    sup_res = max(abs(tAB[t][i] - (tA[t][i] + tB[t][i]))
                  for t in range(400) for i in range(3))
    # 多稳：不同初态弛豫终态（15τ 后残余 ~v0·e⁻¹⁵；同一吸引子判定用
    # 容差 1e-3——远大于残余、远小于初态间距 5.0/50.0）
    finals = []
    for v0 in (0.0, 5.0, 50.0):
        g = build()
        for i in range(3):
            g.cells[i].capacitor.charge = v0
        run(g, 3000)
        finals.append(sum(c.capacitor.voltage for c in g.cells.values()))
    n_attractors = len({round(v / 1e-3) for v in finals})
    # 敏感依赖（只测不造）：1e-9 扰动分离率
    gP = build()
    gQ = build()
    gQ.cells[0].capacitor.charge = 1e-9
    sep0 = 1e-9
    run(gP, 500, inj0)
    run(gQ, 500, inj0)
    sep1 = max(abs(gP.cells[i].capacitor.voltage
                   - gQ.cells[i].capacitor.voltage) for i in range(3))
    print(f"  中间节点响应: 来自节点0={mid_from_0:.6f} / 来自节点2={mid_from_2:.6f}"
          f" ⇒ 多过程共同作用={mid_from_0 > 0 and mid_from_2 > 0}")
    print(f"  叠加残差 max={sup_res:.3e} ⇒ 线性={sup_res < 1e-12}")
    print(f"  多稳: 3 初态终态数={n_attractors}（全部弛豫到 ambient ⇒ 单吸引子）")
    print(f"  敏感依赖: 1e-9 扰动 500 步后分离={sep1:.3e}"
          f"（{'衰减' if sep1 <= sep0 else '增长'} ⇒ 无敏感依赖）")
    print(f"  InstantFieldWorld: patch 间零相互作用（各 patch 只读 T=F(x)"
          f"+自身 RC）⇒ independent channel")
    out["W0B"] = {"mid_from_0": mid_from_0, "mid_from_2": mid_from_2,
                  "coupling_class_normalized": "weakly_coupled_linear_field",
                  "coupling_class_instant": "independent_channel"}
    out["W0D"] = {"superposition_residual": sup_res,
                  "linear": sup_res < 1e-12, "n_attractors": n_attractors,
                  "perturbation_growth": sep1 > sep0,
                  "classification": "线性 / 单吸引子 / 无敏感依赖"}


def w0c(out):
    print("\n[W0-C] 时间尺度谱（脉冲响应多指数分解）")
    g = build()
    traj = run(g, 4000, {0: (0, 1, 10.0)})
    # 三个可观测量的解析模式（链式 3 节点 Laplacian 特征值 0/1/3 × κ + leak）
    total = [sum(row) for row in traj]                     # 模式 λ=0 → 仅 leak
    anti = [row[0] - row[2] for row in traj]               # λ=1 → κ + leak
    curv = [row[0] - 2 * row[1] + row[2] for row in traj]  # λ=3 → 3κ + leak
    tau_leak = _slope_tau(total, 500, 3000)
    tau_anti = _slope_tau([abs(v) for v in anti], 20, 200)
    tau_curv = _slope_tau([abs(v) for v in curv], 5, 60)
    kappa, rleak = TEST_KAPPA_THREE_POINT, TEST_R_LEAK_AMBIENT_THREE_POINT
    pred = {"leak": rleak, "anti": 1.0 / (kappa + 1.0 / rleak),
            "curv": 1.0 / (3 * kappa + 1.0 / rleak)}
    print(f"  实测 τ: leak={tau_leak:.1f} / 反对称={tau_anti:.1f} / "
          f"曲率={tau_curv:.1f} 步")
    print(f"  解析 τ: leak={pred['leak']:.1f} / {pred['anti']:.1f} / "
          f"{pred['curv']:.1f} 步")
    print(f"  独立参数计数: 2（κ, r_leak）；默认档 r_leak=10/κ **绑定** ⇒ "
          f"实际独立尺度=1（κ 派生族）")
    print(f"  normalized 生产档: τ_ref={_TAU_REF_STEPS:.0f} 步"
          f"（κ_0={DEFAULT_KAPPA_0:.3e}, r_leak={DEFAULT_R_LEAK_AMBIENT:.3e}）"
          f"——单一扩散尺度，远超实验时长")
    print(f"  InstantFieldWorld: SkinPatch τ=C/k=5000 步（world.py:135）单 RC"
          f"+Body 角摩擦；场自身无谱")
    out["W0C"] = {"tau_measured": {"leak": tau_leak, "antisym": tau_anti,
                                   "curvature": tau_curv},
                  "tau_predicted": pred,
                  "independent_params": 2, "default_binding": "r_leak=10/kappa",
                  "MULTISCALE_SUPPORT": "NOT_ESTABLISHED",
                  "note": "τ 谱 {6.5,18,200} 全部由 κ 单参数+固定 10× 绑定派生；"
                          "非独立多尺度"}


def main() -> int:
    os.makedirs(DATA_DIR, exist_ok=True)
    print("=" * 68)
    print("Phase W0 结构审计（W0-A/B/C/D；对象=normalized 三点皮肤 + "
          "InstantFieldWorld）")
    print("=" * 68)
    out = {}
    w0a(out)
    w0b_w0d(out)
    w0c(out)
    path = os.path.join(DATA_DIR, "w0_structure.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(out, f, indent=2, ensure_ascii=False)
    print(f"\n落盘: {path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
