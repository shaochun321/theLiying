"""
P2-A1b-1：皮肤输出分布测量

背景：评判(`document - 2026-07-21T140903.110.md`"P2-A1b应怎样执行"
P2-A1b-1)指出，选择转导映射`u_i(t)=clip(κ_i·q_i^skin(t)+b_i)`前，必须
先测量三点皮肤自身`q_i^skin(t)`的真实输出分布——不能先选`κ_i`再反过来
设计刺激。

本实验复用现有`build_three_point_skin()`（不涉及生成元，完全遵守P2-A2
"皮肤与生成元解耦"纪律），对皮肤自身做剂量-响应扫描（类比生成元u-scan
方法论，用一组覆盖多个数量级的外部刺激幅度，不参照生成元能消费的范围），
并复用T-STP-6/7/8已验证的六种位置/次序/单点组合场景，测量：
  - 静息范围（零输入基线）；
  - 常见变化范围（典型刺激幅度下各节点温度范围）；
  - 极值（大幅度刺激下的上限）；
  - 上升/下降速率（dq/dt）；
  - 脉冲持续时间（温度回落到基线附近所需步数）；
  - 不同位置/次序下的分布差异。

均使用`TEST_KAPPA_THREE_POINT`（P2-A2独立物理资格验收已用的同一测试
尺度，可观测传播），不新造参数。
"""
import sys

sys.path.insert(0, '.')

from nexus_v1.components.skin_three_point import (
    TEST_KAPPA_THREE_POINT, TEST_R_LEAK_AMBIENT_THREE_POINT,
    build_three_point_skin,
)

DT = 1.0
STEPS = 300  # 与 T-STP-3/6/7/8 已验证的步数量级一致

# 覆盖多个数量级的外部刺激幅度（剂量-响应扫描，不参照生成元范围）。
INJECTION_LEVELS = [0.01, 0.05, 0.1, 0.5, 1.0, 5.0, 10.0, 50.0]


def fresh_skin():
    return build_three_point_skin(
        kappa=TEST_KAPPA_THREE_POINT, r_leak_ambient=TEST_R_LEAK_AMBIENT_THREE_POINT)


def q_vector(graph):
    return [graph.cells[i].temperature for i in range(3)]


# ── 第一部分：剂量-响应扫描（仅刺激s1，测幅度范围/速率/脉冲持续时间）──
def dose_response_scan():
    print("=" * 100)
    print("  第一部分：剂量-响应扫描（仅刺激s1，STEPS=300）")
    print("=" * 100)
    header = (f"{'注入幅度':>10} | {'s1稳态':>10} | {'s2稳态':>10} | {'s3稳态':>10} | "
              f"{'s1上升率(前20步)':>16} | {'脉冲持续步数(回落到10%以内)':>26}")
    print(header)
    print("-" * len(header))

    results = []
    for level in INJECTION_LEVELS:
        graph = fresh_skin()
        trajectory = []
        for t in range(STEPS):
            graph.step(dt=DT, external_injections={0: level})
            trajectory.append(q_vector(graph))

        q_final = trajectory[-1]
        q_at_20 = trajectory[19]
        rise_rate = (q_at_20[0] - trajectory[0][0]) / 20.0

        # 脉冲持续时间：停止注入后，s1回落到峰值10%以内所需步数。
        graph2 = fresh_skin()
        for t in range(STEPS):
            graph2.step(dt=DT, external_injections={0: level})
        peak = graph2.cells[0].temperature
        decay_steps = 0
        for t in range(2000):
            graph2.step(dt=DT, external_injections={})
            decay_steps += 1
            if graph2.cells[0].temperature <= peak * 0.1:
                break
        else:
            decay_steps = -1  # 2000步内未回落到10%以内

        results.append({
            "level": level, "q_final": q_final, "rise_rate": rise_rate,
            "decay_steps": decay_steps,
        })
        print(f"{level:>10.3f} | {q_final[0]:>10.4f} | {q_final[1]:>10.4f} | "
              f"{q_final[2]:>10.4f} | {rise_rate:>16.6f} | {decay_steps:>26}")

    return results


# ── 第二部分：静息基线（零输入）──
def rest_baseline():
    print()
    print("=" * 100)
    print("  第二部分：静息基线（零输入，300步）")
    print("=" * 100)
    graph = fresh_skin()
    for t in range(STEPS):
        graph.step(dt=DT, external_injections={})
    q_rest = q_vector(graph)
    print(f"  静息态 [T0,T1,T2] = {q_rest}")
    return q_rest


# ── 第三部分：位置/次序/组合分布（复用T-STP-6/7/8场景）──
def position_order_distribution():
    print()
    print("=" * 100)
    print("  第三部分：位置/次序/组合分布（复用T-STP-6/7/8的六种场景）")
    print("=" * 100)

    scenarios = {}

    # Γ_A/Γ_B：位置反例
    g_a = fresh_skin()
    for _ in range(STEPS):
        g_a.step(dt=DT, external_injections={0: 1.0})
    scenarios["Γ_A(仅s1)"] = q_vector(g_a)

    g_b = fresh_skin()
    for _ in range(STEPS):
        g_b.step(dt=DT, external_injections={2: 1.0})
    scenarios["Γ_B(仅s3)"] = q_vector(g_b)

    # Γ_C/Γ_D：次序反例
    m = STEPS // 2
    g_c = fresh_skin()
    for _ in range(m):
        g_c.step(dt=DT, external_injections={0: 1.0})
    for _ in range(m):
        g_c.step(dt=DT, external_injections={2: 1.0})
    scenarios["Γ_C(先s1后s3)"] = q_vector(g_c)

    g_d = fresh_skin()
    for _ in range(m):
        g_d.step(dt=DT, external_injections={2: 1.0})
    for _ in range(m):
        g_d.step(dt=DT, external_injections={0: 1.0})
    scenarios["Γ_D(先s3后s1)"] = q_vector(g_d)

    # Γ_E/Γ_F：单点与共同作用
    g_e = fresh_skin()
    for _ in range(STEPS):
        g_e.step(dt=DT, external_injections={1: 1.0})
    scenarios["Γ_E(仅s2中心)"] = q_vector(g_e)

    g_f = fresh_skin()
    for _ in range(STEPS):
        g_f.step(dt=DT, external_injections={0: 0.5, 2: 0.5})
    scenarios["Γ_F(s1+s3两端)"] = q_vector(g_f)

    for name, q in scenarios.items():
        print(f"  {name:>16}: [T0,T1,T2] = [{q[0]:.4f}, {q[1]:.4f}, {q[2]:.4f}]")

    all_q = list(scenarios.values())
    all_values = [v for q in all_q for v in q]
    print()
    print(f"  六种场景下全部节点温度的范围：[{min(all_values):.4f}, {max(all_values):.4f}]")
    return scenarios


def run():
    q_rest = rest_baseline()
    dose_results = dose_response_scan()
    scenarios = position_order_distribution()

    print()
    print("=" * 100)
    print("  汇总：q_i^skin(t) 分布特征（供未来 P2-A1b-2 选择 κ_i/clip 参考）")
    print("=" * 100)
    print(f"  静息范围：{q_rest}")
    all_dose_finals = [v for r in dose_results for v in r["q_final"]]
    print(f"  剂量扫描下全部节点温度范围：[{min(all_dose_finals):.4f}, {max(all_dose_finals):.4f}]")
    print(f"  上升速率范围（s1，前20步）：["
          f"{min(r['rise_rate'] for r in dose_results):.6f}, "
          f"{max(r['rise_rate'] for r in dose_results):.6f}]")
    finite_decay = [r["decay_steps"] for r in dose_results if r["decay_steps"] > 0]
    if finite_decay:
        print(f"  脉冲持续时间范围（回落到峰值10%以内所需步数）：["
              f"{min(finite_decay)}, {max(finite_decay)}]")
    print("=" * 100)

    return q_rest, dose_results, scenarios


if __name__ == "__main__":
    run()
