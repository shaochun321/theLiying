"""semantic_erasure_audit.py — MFS0-E0 Step B1：语义擦除审计。

TYPE:INFRA（research/ 层；只读扫描 production，不修改任何文件）。

方案 §6：Step B2 开始以前必须输出 SEMANTIC_ERASURE_AUDIT.json，至少检查
并明确拒绝 reward / punishment / RPE / hunger / satiety / warming-good /
intake reward / fill-rate reward / positive-valence clamp / preset DA。

H_τ^Δ 只能代表"later occurrence 留下的局部历史动力学"，不得代表
good/bad outcome / success / failure / reward / error。

## 审计方式

1. **拒绝清单**：逐条列出 production 中带 valence 的 DA 汇入点（坐标由我方
   《MFS0-E0方案评判_2026-09-23》E-9 定位），并用机器检查证明 MFS0 的
   M 链**不 import、不引用**其中任何一个符号。
2. **既有反例认领**（方案 §5）：`tss/relations/temporal_r_prec_plastic.py`
   被常数 `da_concentration` 喂入，登记为
   LEGACY_SEMANTIC / TEST CONVENIENCE PATH，NOT MFS0 INPUT。
3. **正向声明**：M 链实际消费的物理量及其语义清白性论证。

运行：cd research/memory_feedback_substrate_v0 && python semantic_erasure_audit.py
"""
from __future__ import annotations

import os
import re
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)

import mfs0_common as M  # noqa: E402

_ROOT = os.path.abspath(os.path.join(_HERE, '..', '..'))

# 方案 §6 拒绝清单 → production 中的实际坐标（评判 E-9 定位）
REJECTED_PATHS = [
    {"semantic": "intake reward",
     "symbol": "intake_to_da_reward",
     "site": "nexus_v1/circuit/variant_adapter.py:3969-3978",
     "why": "BIO comment cites VTA phasic DA during food intake "
            "(Schultz 1997) — explicit reward semantics; source activation "
            "is also overwritten at :2577 (transduction bypass)"},
    {"semantic": "RPE / reward prediction error",
     "symbol": "da_gate (DADifferentialGate) direct injection",
     "site": "nexus_v1/circuit/variant_adapter.py:2992-2995 + "
             "nexus_v1/components/da_differential_gate.py:63-71",
     "why": "half-wave rectifier hard-codes 'energy going up = reward'; "
            "also bypasses SynapticBundle entirely"},
    {"semantic": "hunger drive",
     "symbol": "hunger_to_da",
     "site": "nexus_v1/circuit/variant_adapter.py:4219-4229 (+ Python ReLU "
             "with hard-wired setpoint 0.5 at :2953)",
     "why": "'energy deficit = drive' is a valence assignment"},
    {"semantic": "satiety suppression",
     "symbol": "satiety_to_da",
     "site": "nexus_v1/circuit/variant_adapter.py:3944-3952 (sign_gate=-1.0)",
     "why": "strong valence: satiety inhibits DA"},
    {"semantic": "satiety aggregation (four hand-set signs)",
     "symbol": "intake/fillrate/dwell/hunger _to_satiety",
     "site": "nexus_v1/circuit/variant_adapter.py:1411-1418",
     "why": "four artificial sign assignments feeding the satiety node"},
    {"semantic": "warming-good",
     "symbol": "thermo_delta_to_da",
     "site": "nexus_v1/somatosensory/transducer_neurons.py:379-391",
     "why": "dT/dt>0 (warming) routed to DA = 'getting warmer is good'"},
    {"semantic": "positive-valence clamp",
     "symbol": "_phasic_pos",
     "site": "nexus_v1/circuit/variant_adapter.py:3363",
     "why": "max(0, ...) keeps only the 'approaching' half — a valence clamp"},
    {"semantic": "fill-rate reward",
     "symbol": "fill_rate_sensor bypass",
     "site": "nexus_v1/circuit/variant_adapter.py:2613-2616",
     "why": "feeds the RPE gate; same reward semantics"},
    {"semantic": "transduction bypass of the intake sensor",
     "symbol": "intake_sensor.activation overwrite",
     "site": "nexus_v1/circuit/variant_adapter.py:2577",
     "why": "activation directly overwritten (HC-008 family) — not a "
            "modulation source at all"},
    {"semantic": "preset DA constant",
     "symbol": "da_concentration=<const>",
     "site": "tss/relations/temporal_r_prec_plastic.py (fed by "
             "tss/tests/test_r_prec_plastic_learning.py:63,69)",
     "why": "this is exactly the 'modulation = preset_number' pattern the "
            "plan §5 forbids — claimed below as a legacy path"},
]

# MFS0 的 M 链实际消费的模块（机器检查这些文件不含拒绝符号）
M_CHAIN_SOURCES = [
    "tss/relations/relation_event_adapter.py",
    "tss/relations/entry_gate.py",
    "tss/relations/history_kernel.py",
    "tss/adapters/relation_replay_adapter.py",
    "research/memory_feedback_substrate_v0/mfs0_common.py",
]

BANNED_SYMBOLS = [
    "da_concentration", "dopamine", "reward", "hunger", "satiety",
    "intake", "rpe", "fill_fraction", "phasic", "valence",
]


def _code_lines(lines):
    """产出 (行号, 代码文本)，跳过注释与 docstring/字符串块。

    必须跟踪三引号的开合状态：拒绝符号会合法地出现在**否定性说明**里
    （例如 build_modulation 的 "无 valence——不表示 reward/punishment"），
    那是文档而不是引用。只按行首 `\"\"\"` 判断会漏掉块内部的行。
    """
    in_block = False
    delim = ''
    for i, line in enumerate(lines, 1):
        s = line.strip()
        if in_block:
            if delim in s:
                in_block = False
            continue
        if s.startswith('#'):
            continue
        for d in ('"""', "'''"):
            if s.startswith(d):
                # 单行 docstring（开合同行）不进入块状态
                if not (len(s) > len(d) and s.endswith(d)):
                    in_block, delim = True, d
                break
        else:
            yield i, s
            continue
        # 行首即 docstring 起始 —— 整行都是文档
        continue


def scan_chain() -> dict:
    """机器检查：M 链源码不得出现拒绝符号（大小写不敏感，整词匹配）。"""
    findings = {}
    for rel in M_CHAIN_SOURCES:
        path = os.path.join(_ROOT, rel)
        with open(path, encoding='utf-8') as f:
            lines = f.readlines()
        hits = []
        for i, s in _code_lines(lines):
            for sym in BANNED_SYMBOLS:
                if re.search(rf'\b{re.escape(sym)}\b', s, re.IGNORECASE):
                    hits.append({"line": i, "symbol": sym,
                                 "text": s[:120]})
        findings[rel] = hits
    return findings


def main() -> int:
    M.assert_no_step_era_import()
    findings = scan_chain()
    # docstring 行已被跳过；剩余命中即真实代码引用
    total_hits = sum(len(v) for v in findings.values())

    modu = M.build_modulation()
    elig = M.build_eligibility()
    M.assert_paths_independent(elig, modu)

    out = {
        "step": "B1",
        "audit": "SEMANTIC_ERASURE_AUDIT",
        "plan_section": "§6",
        "rejected_paths": REJECTED_PATHS,
        "rejected_count": len(REJECTED_PATHS),
        "legacy_claim": {
            "path": "tss/relations/temporal_r_prec_plastic.py",
            "fed_by": "tss/tests/test_r_prec_plastic_learning.py:63,69 "
                      "(da_concentration=0.5 / 0.0, constants)",
            "registration": "LEGACY_SEMANTIC / TEST CONVENIENCE PATH — "
                            "NOT MFS0 INPUT",
            "note": "This is the concrete instance of the "
                    "'modulation = preset_number' pattern plan §5 forbids. "
                    "MFS0 replaces exactly this position with a physical "
                    "H_tau^Delta state. The legacy path is left untouched "
                    "(production READ_ONLY) and claimed here so it cannot be "
                    "mistaken for an MFS0 input.",
        },
        "m_chain_scan": {
            "sources": M_CHAIN_SOURCES,
            "banned_symbols": BANNED_SYMBOLS,
            "hits": findings,
            "total_hits": total_hits,
            "clean": total_hits == 0,
        },
        "m_source_positive_declaration": {
            "source": M.M_SOURCE,
            "physical_quantity": "h^Delta(t) = V of the H_tau^Delta history "
                                 "capacitor, charged once per b^up pulse from "
                                 "the later occurrence and decaying with "
                                 "tau_h = 0.600 s",
            "what_it_means": "a later occurrence happened recently, and its "
                             "entry history is still physically present",
            "what_it_does_NOT_mean": ["good outcome", "bad outcome", "success",
                                      "failure", "reward", "error", "value"],
            "no_valence_argument":
                "The quantity is the voltage of an RC pool driven by an "
                "entry-gate pulse. It carries no sign asymmetry between "
                "'desirable' and 'undesirable' events: every legal later "
                "occurrence charges it identically, regardless of what the "
                "organism's energy / temperature / intake state is. There is "
                "no term anywhere in the chain that reads an outcome variable.",
            "dopamine_primitives_not_used": {
                "Neuromodulator": "in production this is a DEAD ODE — "
                                  "variant_adapter.py:3023-3025 assigns "
                                  "_concentration directly and comments "
                                  "\"Don't call dopamine.step()\"; it has "
                                  "degenerated into a stateless gain "
                                  "converter. NOT used by MFS0.",
                "DADifferentialGate": "despite the 'Capacitor' comment it is a "
                                      "one-step delay register plus Python "
                                      "max/min rectification, with no tau, no "
                                      "decay and no energy ledger. NOT used "
                                      "by MFS0.",
            },
        },
        "path_independence_R1": {
            "checked": "assert_paths_independent (object identity)",
            "result": "PASS — Past->e and Later->M share no object",
            "why_it_matters": "if W fed H_tau^Delta, M would merely be a "
                              "second encoding of e (plan §3 R-1)",
        },
        "SEMANTIC_ERASURE_AUDIT": "PASS" if total_hits == 0 else "FAIL",
    }
    M.write_json('semantic_erasure_audit.json', out)

    print("MFS0-E0 Step B1 — Semantic Erasure Audit")
    print(f"  rejected valence paths : {len(REJECTED_PATHS)} "
          "(coordinates in JSON)")
    print("  legacy claim           : temporal_r_prec_plastic "
          "da_concentration=const -> LEGACY_SEMANTIC, NOT MFS0 INPUT")
    print(f"  M-chain symbol scan    : {total_hits} hit(s) across "
          f"{len(M_CHAIN_SOURCES)} sources")
    for rel, hits in findings.items():
        if hits:
            for h in hits:
                print(f"      {rel}:{h['line']}  [{h['symbol']}]  "
                      f"{h['text'][:70]}")
    print("  path independence (R-1): PASS")
    print(f"\n  SEMANTIC_ERASURE_AUDIT = {out['SEMANTIC_ERASURE_AUDIT']}")
    return 0 if total_hits == 0 else 1


if __name__ == '__main__':
    raise SystemExit(main())
