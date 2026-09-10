"""f5_neuron_selfloop_probe.py — F5：Neuron 自激回路 mini 审计（修订稿 §G，PARTIAL）。

TYPE:INFRA（research/ 隔离层）

## 目标（M4 类：极限环/自维持放电）

真实 Neuron（最小 LIF spiking 配置）+ 真实 SynapticBundle 自环
（sources=[n], targets=[n]），检验：
  状态 1：静息（无输入 → 恒静默）
  状态 2：自维持放电（单次 kick 后靠自突触 EPSP 维持周期发放）
两者若在相同外部条件（u=0）下均可持续 ⇒ M4 型双状态（吸引子 vs 极限环）。

生物对应：reverberating persistent activity（工作记忆母题）
REF: Wang 2001 TINS 24:455。

范围声明（PARTIAL）：只做返回映射级检验（可持续性+周期+保持时间），
不做完整分岔分析；Neuron 全配置空间 OUT_OF_SCOPE。

参数 provenance：Neuron/Bundle 全用项目既有构造惯例
  spiking=True, v_peak=0.23 ← T1 collector 惯例（temporal_r_prec.py）
  w=0.3 frozen ← 换能束惯例；synapse_gain 扫 [1,7.5]（da_gate η 上界）
"""
from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from nexus_v1.components.neuron import Neuron, NeuronConfig
from nexus_v1.circuit.bundle import SynapticBundle, BundleConfig

DT = 0.001


def make_loop(gain: float):
    n = Neuron(NeuronConfig(neuron_id="f5_self", capacitance=0.001,
                            r_leak=600.0, spiking=True, v_peak=0.23))
    b = SynapticBundle(
        config=BundleConfig(bundle_id="f5_selfloop", learning_rule="frozen",
                            initial_weight=0.3, weight_max=0.3,
                            synapse_gain=gain, bundle_role="feedforward",
                            physical_seed=91000),
        sources=[n], targets=[n])
    return n, b


def run(gain: float, kick: bool, steps: int = 60000):
    n, b = make_loop(gain)
    spikes = []
    for t in range(steps):
        currents = b.propagate()
        u = 0.4 if (kick and t == 100) else 0.0    # 单次 kick（合法输入幅度域）
        n.step(currents[0] + u, DT)
        if n.activation >= 1.0:
            spikes.append(t)
    return spikes


def main() -> int:
    print("=" * 68)
    print("F5 Neuron 自激回路 mini 审计（PARTIAL：返回映射级）")
    print("=" * 68)
    found = None
    for gain in (1.0, 3.0, 5.0, 7.5):
        s_rest = run(gain, kick=False)
        s_kick = run(gain, kick=True)
        sustained = (len(s_kick) > 20 and s_kick[-1] > 50000)
        rest_quiet = len(s_rest) == 0
        isi = (s_kick[-1] - s_kick[-2]) if len(s_kick) >= 2 else None
        print(f"  gain={gain:4.1f}: 静息 spikes={len(s_rest):4d}  "
              f"kick 后 spikes={len(s_kick):5d}  末次@{s_kick[-1] if s_kick else '—'}"
              f"  ISI={isi}  自维持={sustained}  静息保持={rest_quiet}")
        if sustained and rest_quiet and found is None:
            found = gain
    print()
    if found is not None:
        print(f"  结论: M4 型双状态存在（gain={found}，Domain B）——")
        print(f"        静息吸引子 与 自维持放电极限环 在相同外部条件下并存")
    else:
        print("  结论: 扫描域内未发现自维持放电（M4 未达成，此路线留待后续）")
    return 0


if __name__ == "__main__":
    sys.exit(main())
