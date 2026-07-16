"""nexus_v1.tests._calib_t3_path_ab — T3 路径A(减法抑制)/路径B(分流抑制) 最小判别实验。

方案依据：cell-cell/claudecode方案/基础生成元双轨落地方案_v2_2026-07-16.md
《T3 —— r_part 参与竞争关系》。Gate D 要求：编码前先做路径A/B最小判别
实验，择定路径后再写正式实现——本脚本就是这个"择定"实验，按项目既有
`_diag_*.py`/`_calib_*.py` 一次性诊断脚本惯例编写，不构造完整 r_part
生成元（那是后续独立任务）。

路径A（减法抑制）：ξ_a、ξ_b → 独立兴奋通道 → 共同总量池 → 共享减法抑制
  (synapse_gain=-1.0) → y_a、y_b。

路径B（分流抑制/共享池）：复用既有 `DivisiveNormalizationReceptor`
  （compensation.py:295，Carandini-Heeger 除法归一化，非 Python 除法），
  用**同一个实例**依次对 I_a、I_b 调用 `.normalize()`，使其 `_pool_voltage`
  同时追踪两路输入，得到共享横向池版的分流抑制。

验收标准（方案 T3 段落定义）：
  一级（必须达到）：较大输入→较大输出 / 交换输入则输出交换 /
                    单输入时对应通道占优 / 等强输入输出近似相等 /
                    静默时无虚假占比。
  二级（实验性目标）：共同放大时排序保持 / 输出差异对共同尺度相对稳定 /
                      多通道竞争后近似归一化 / 输出总量变动在有限范围。
"""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from nexus_v1.components.compensation import DivisiveNormalizationReceptor

DT = 0.001
N_STEPS = 2000


def run_path_a(i_a, i_b, r_leak_pool=5.0, pool_capacitance=1.0,
                w_exc=1.0, w_inh=0.5, r_leak_out=5.0, out_capacitance=1.0):
    """路径A：减法抑制。用简化的标量RC模拟(不经过完整Neuron类)，
    因为本脚本是纯诊断性质的最小判别实验，只关心抑制机制本身的
    输入-输出映射关系，不关心尖峰/膜电位等神经元细节。
    """
    pool_v = 0.0
    y_a_v = 0.0
    y_b_v = 0.0
    for _ in range(N_STEPS):
        # pool 累积 (I_a+I_b)
        pool_v += w_exc * (i_a + i_b) * DT / pool_capacitance
        pool_v *= math.exp(-DT / max(r_leak_pool * pool_capacitance, 1e-6))
        # y_a = 兴奋(i_a) - 共享抑制(pool)
        y_a_v += (w_exc * i_a - w_inh * pool_v) * DT / out_capacitance
        y_a_v *= math.exp(-DT / max(r_leak_out * out_capacitance, 1e-6))
        y_b_v += (w_exc * i_b - w_inh * pool_v) * DT / out_capacitance
        y_b_v *= math.exp(-DT / max(r_leak_out * out_capacitance, 1e-6))
    return max(0.0, y_a_v), max(0.0, y_b_v)


def run_path_b(i_a, i_b, sigma=1.0, pool_capacitance=5.0, pool_r_leak=5.0):
    """路径B（顺序调用版）：复用既有 DivisiveNormalizationReceptor，
    用同一实例依次对 i_a/i_b 调用 normalize() 实现共享横向池。

    已知局限（见 T3 报告 §五）：i_a 更新时池尚未包含 i_b 本步贡献，
    i_b 更新时池已包含 i_a 本步贡献——调用顺序造成极小先后不对称。
    """
    dn = DivisiveNormalizationReceptor(
        sigma=sigma, pool_capacitance=pool_capacitance, pool_r_leak=pool_r_leak)
    y_a = 0.0
    y_b = 0.0
    for _ in range(N_STEPS):
        y_a = dn.normalize(i_a, DT)
        y_b = dn.normalize(i_b, DT)
    return max(0.0, y_a), max(0.0, y_b)


def run_path_b_synced(i_a, i_b, sigma=1.0, pool_capacitance=5.0, pool_r_leak=5.0):
    """路径B（同步共享池版，批判三修正点8，实测反驳"实现超出现有组件"）：
    只用 DivisiveNormalizationReceptor 已公开的两个成员——`.normalize()`
    方法和 `.pool_activity` 属性（compensation.py:337-338，非本次新增）：

      1. 调用一次 `dn.normalize(i_a+i_b, dt)`，池按**总电流**更新一次
         （返回值本身丢弃，只用于触发池更新）；
      2. 读公开的 `dn.pool_activity`，手算与 normalize() 内部相同的
         `norm_factor = sigma/(sigma+pool)` 公式；
      3. 把同一个 norm_factor 分别乘到 i_a、i_b 上。

    全程未新增方法、未修改/直接读写内部 `_pool_voltage`，是合法的"只用
    现有组件"实现，两路输出保证用的是同一次池更新后的增益（回应批判
    第9点"必须验证所有通道使用同一次 pool 更新后的 G"）。
    """
    dn = DivisiveNormalizationReceptor(
        sigma=sigma, pool_capacitance=pool_capacitance, pool_r_leak=pool_r_leak)
    y_a = 0.0
    y_b = 0.0
    for _ in range(N_STEPS):
        dn.normalize(i_a + i_b, DT)  # 触发池按总电流更新一次；返回值丢弃
        denom = max(sigma + dn.pool_activity, sigma * 0.01)
        norm_factor = sigma / denom
        y_a = i_a * norm_factor
        y_b = i_b * norm_factor
    return max(0.0, y_a), max(0.0, y_b)


import math

SCENARIOS = [
    ("静默",            0.0, 0.0),
    ("单通道A",          1.0, 0.0),
    ("单通道B(交换)",    0.0, 1.0),
    ("等强",             1.0, 1.0),
    ("A占优2:1",         2.0, 1.0),
    ("A占优2:1(共同放大2x)", 4.0, 2.0),
    ("A占优2:1(共同放大4x)", 8.0, 4.0),
    ("三档竞争(极端3:1)", 3.0, 1.0),
]


def main():
    print(f"{'场景':<24} {'I_a':>5} {'I_b':>5} | "
          f"{'路径A y_a':>10} {'路径A y_b':>10} {'A比值':>8} | "
          f"{'路径B y_a':>10} {'路径B y_b':>10} {'B比值':>8}")
    results = []
    for name, i_a, i_b in SCENARIOS:
        ya_a, yb_a = run_path_a(i_a, i_b)
        ya_b, yb_b = run_path_b(i_a, i_b)
        ratio_a = ya_a / max(yb_a, 1e-9) if (ya_a + yb_a) > 0 else float('nan')
        ratio_b = ya_b / max(yb_b, 1e-9) if (ya_b + yb_b) > 0 else float('nan')
        results.append((name, i_a, i_b, ya_a, yb_a, ratio_a, ya_b, yb_b, ratio_b))
        print(f"{name:<24} {i_a:>5.1f} {i_b:>5.1f} | "
              f"{ya_a:>10.4f} {yb_a:>10.4f} {ratio_a:>8.3f} | "
              f"{ya_b:>10.4f} {yb_b:>10.4f} {ratio_b:>8.3f}")

    print("\n" + "="*100)
    print("一级验收检查：")
    # 1. 静默无虚假占比
    silent = results[0]
    print(f"  静默无虚假占比: A路径 y=({silent[3]:.4f},{silent[4]:.4f}) "
          f"B路径 y=({silent[6]:.4f},{silent[7]:.4f}) "
          f"{'PASS' if silent[3]<1e-6 and silent[4]<1e-6 and silent[6]<1e-6 and silent[7]<1e-6 else 'FAIL'}")
    # 2. 单通道占优 + 交换对称
    single_a, single_b = results[1], results[2]
    print(f"  单通道A占优(A路径): y_a={single_a[3]:.4f} > y_b={single_a[4]:.4f}: "
          f"{'PASS' if single_a[3]>single_a[4] else 'FAIL'}")
    print(f"  交换对称(A路径): 单通道A的y_a({single_a[3]:.4f}) ≈ 单通道B的y_b({single_b[4]:.4f}): "
          f"{'PASS' if abs(single_a[3]-single_b[4])<1e-6 else 'FAIL'}")
    print(f"  单通道A占优(B路径): y_a={single_a[6]:.4f} > y_b={single_a[7]:.4f}: "
          f"{'PASS' if single_a[6]>single_a[7] else 'FAIL'}")
    print(f"  交换对称(B路径): 单通道A的y_a({single_a[6]:.4f}) ≈ 单通道B的y_b({single_b[7]:.4f}): "
          f"{'PASS' if abs(single_a[6]-single_b[7])<1e-6 else 'FAIL'}")
    # 3. 等强输出近似相等
    equal = results[3]
    print(f"  等强输出近似相等(A路径): y_a={equal[3]:.4f} y_b={equal[4]:.4f}: "
          f"{'PASS' if abs(equal[3]-equal[4])<1e-6 else 'FAIL'}")
    print(f"  等强输出近似相等(B路径): y_a={equal[6]:.4f} y_b={equal[7]:.4f}: "
          f"{'PASS' if abs(equal[6]-equal[7])<1e-6 else 'FAIL'}")

    print("\n二级验收检查（共同放大时排序/比例是否保持稳定）：")
    r1, r2, r3 = results[4], results[5], results[6]  # 1x, 2x, 4x scaling of 2:1 ratio
    print(f"  路径A 比值随共同放大变化: 1x={r1[5]:.3f}  2x={r2[5]:.3f}  4x={r3[5]:.3f}  "
          f"(方差={max(r1[5],r2[5],r3[5])-min(r1[5],r2[5],r3[5]):.4f})")
    print(f"  路径B 比值随共同放大变化: 1x={r1[8]:.3f}  2x={r2[8]:.3f}  4x={r3[8]:.3f}  "
          f"(方差={max(r1[8],r2[8],r3[8])-min(r1[8],r2[8],r3[8]):.4f})")
    print(f"  路径A 输出总量(y_a+y_b)随放大变化: 1x={r1[3]+r1[4]:.4f} 2x={r2[3]+r2[4]:.4f} 4x={r3[3]+r3[4]:.4f}")
    print(f"  路径B(顺序调用) 输出总量随放大变化: 1x={r1[6]+r1[7]:.4f} 2x={r2[6]+r2[7]:.4f} 4x={r3[6]+r3[7]:.4f}")

    # 批判三修正点8/9：验证"同步共享池"（只用现有公开接口）与常数增益假设的排除
    print("\n" + "="*100)
    print("批判三修正点8：路径B 同步共享池版（只用现有公开接口 .normalize()+.pool_activity）：")
    print(f"{'场景':<24} {'I_a':>5} {'I_b':>5} {'y_a(同步)':>10} {'y_b(同步)':>10} {'比值':>8}")
    synced_results = []
    for name, i_a, i_b in SCENARIOS:
        ya_s, yb_s = run_path_b_synced(i_a, i_b)
        ratio_s = ya_s / max(yb_s, 1e-9) if (ya_s + yb_s) > 0 else float('nan')
        synced_results.append((name, i_a, i_b, ya_s, yb_s, ratio_s))
        print(f"{name:<24} {i_a:>5.1f} {i_b:>5.1f} {ya_s:>10.4f} {yb_s:>10.4f} {ratio_s:>8.3f}")

    equal_s = synced_results[3]
    print(f"\n  等强输出精确相等(同步版): y_a={equal_s[3]:.6f} y_b={equal_s[4]:.6f} "
          f"差值={abs(equal_s[3]-equal_s[4]):.2e} "
          f"{'PASS(更优于顺序调用版)' if abs(equal_s[3]-equal_s[4])<1e-9 else 'FAIL'}")

    s1, s2, s3 = synced_results[4], synced_results[5], synced_results[6]
    print(f"  同步版比值随共同放大变化: 1x={s1[5]:.4f}  2x={s2[5]:.4f}  4x={s3[5]:.4f}  "
          f"(方差={max(s1[5],s2[5],s3[5])-min(s1[5],s2[5],s3[5]):.6f})")
    total_1x, total_2x, total_4x = s1[3]+s1[4], s2[3]+s2[4], s3[3]+s3[4]
    print(f"  同步版输出总量随放大变化: 1x={total_1x:.4f} 2x={total_2x:.4f} 4x={total_4x:.4f}")

    # 批判三修正点9：排除"常数乘性增益 y=g*I"这个替代假设——
    # 若是常数增益，总量应严格正比于放大倍数（1x/2x/4x 应呈 1:2:4）。
    print("\n批判三修正点9：排除常数乘性增益假设——")
    ratio_2x_to_1x = total_2x / total_1x
    ratio_4x_to_1x = total_4x / total_1x
    print(f"  若为常数增益 y=g*I，总量应严格 1:2:4 (即 2x/1x=2.0, 4x/1x=4.0)")
    print(f"  实测: 2x/1x={ratio_2x_to_1x:.4f}（应=2.0000才符合常数增益）, "
          f"4x/1x={ratio_4x_to_1x:.4f}（应=4.0000才符合常数增益）")
    is_sublinear = ratio_2x_to_1x < 1.9 and ratio_4x_to_1x < 3.8
    print(f"  {'总量增长明显亚线性/饱和，排除常数增益假设，确认为真实分流归一化' if is_sublinear else '总量增长接近线性，需进一步排查'}")


if __name__ == "__main__":
    main()
