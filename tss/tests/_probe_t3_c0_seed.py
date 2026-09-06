"""tss.tests._probe_t3_c0_seed — 单 PYTHONHASHSEED 下的 T-RPT 核心场景探针。

方案依据：第十八节 18.4 第3点。独立可执行脚本，被 `_diag_t3_c0_multiseed.py`
以不同 `PYTHONHASHSEED` 环境变量启动子进程调用（Bundle 级 hash 扰动只在
进程启动时按 PYTHONHASHSEED 固定一次，同一进程内多次实例化电路仍会得到
同一扰动幅度——这也是为什么 T-RPT-2/T-RPT-4 的偏差在单次运行内是稳定的
~8%，但跨会话/跨进程运行会不同，同 T1 已记录的机制）。

以 JSON 单行打印结果到 stdout，供父进程解析。
"""

import sys
import os
import json

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from tss.relations.ratio_r_part import RPartCircuitT3

DT = 0.001
_N_STEPS = 200


def _drive(i_a, i_b, n_steps=_N_STEPS):
    c = RPartCircuitT3()
    r = {}
    for _ in range(n_steps):
        c.rpart_xi_a.pre_trace = i_a
        c.rpart_xi_b.pre_trace = i_b
        r = c.step_rpart(dt=DT)
    return r


if __name__ == "__main__":
    equal = _drive(1.0, 1.0)
    unequal_1 = _drive(1.0, 0.3)
    unequal_2 = _drive(0.3, 1.0)

    result = {
        "pythonhashseed": os.environ.get("PYTHONHASHSEED", "<unset>"),
        # ε_equal: 等强输入下 i_a_raw/i_b_raw 偏离 1.0 的相对幅度
        "eps_equal": abs(equal["i_a_raw"] - equal["i_b_raw"]) / max(equal["i_a_raw"], equal["i_b_raw"]),
        # ε_swap: 交换输入后 y_a(before)/y_b(after) 与 y_b(before)/y_a(after) 的相对偏差
        "eps_swap_a": abs(unequal_1["y_a"] - unequal_2["y_b"]) / max(unequal_1["y_a"], unequal_2["y_b"]),
        "eps_swap_b": abs(unequal_1["y_b"] - unequal_2["y_a"]) / max(unequal_1["y_b"], unequal_2["y_a"]),
        # ε_ratio: Bundle 有效电流比（i_a_raw/i_b_raw）在等强输入下应为1.0，偏离即扰动幅度
        "eps_ratio": abs(equal["i_a_raw"] / equal["i_b_raw"] - 1.0) if equal["i_b_raw"] != 0 else None,
    }
    print(json.dumps(result))
