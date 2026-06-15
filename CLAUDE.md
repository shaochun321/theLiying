# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 协作规范

- **语言：** 用户使用中文交流，Claude 应以中文回复。代码注释、报告文件、变量命名等技术内容保持英文。
- **环境：** 已安装 WSL（Windows Subsystem for Linux）。在 WSL 终端下运行时，编码默认为 UTF-8，无需 `PYTHONIOENCODING=utf-8` 前缀；但在 Windows 原生终端（cmd/PowerShell/Git Bash）下仍需加该前缀。
- **Bash 分类器设置：** Claude Code 默认权限模式为 `auto`，每条 bash 命令均需调用 Anthropic 安全分类器服务，服务器故障时命令全部阻断。已将全局设置 `C:\Users\shaoc\.claude\settings.json` 中的 `permissions.defaultMode` 改为 `acceptEdits`——bash 命令直接放行，仅文件写入时弹确认。如需恢复分类器保护，删除该字段即可。
- **知识库搜索：** `cell-cell/00_Dashboard/` 下的文档提供设计决策、分析报告和阶段方案的聚合搜索入口。查找项目背景、规范定义、历史报告时优先查阅该目录。

## What this is

Cell-CC is a **neuromorphic circuit simulator built from four semiconductor primitives** — `Capacitor` (membrane / memory), `MOSFET` (threshold / ion channel), `Memristor` (plastic synapse), `PowerRail` (metabolic energy with internal-resistance gain limiting). It simulates a full sensorimotor chain from mechanical/thermal sensing to motor output, with Hebbian/STDP learning. Every component is required to map to a real biological or physical object (see `nexus_v1/RULES.md`).

Three co-existing top-level systems:
- **`nexus_v1/`** — the organism (physics + learning). The active main system.
- **`governance/`** — a *co-equal parallel* auditor (NOT subordinate): `Fuse` (physics-law circuit breaker), `Adjudicator`, `Validator`, `Modeler`, `MathCandidate`, `GovernanceLedger`. Instantiated inside `VariantCircuit.__init__` and run every step.
- **`experiments/`** — older "Morphosphere" experiment scripts (mostly hardcode `D:\cell-cc\Morphosphere_*` paths; predecessor codebase, not the current system).

`cell-cell/` is an Obsidian knowledge vault (design docs, AI logs, analysis reports — Markdown only, no code). `docs/` is an older Morphosphere version archive. Generated reports go in `cell-cell/报告/`.

## Running tests & entry points

**Run everything from the repo root.** The repo is at `j:\cell-cc`.

```bash
# Primary regression suite (21 checks, ~29s) — run after every change
python -m nexus_v1.tests.test_regression          # custom runner, exit 0 = pass
python -m pytest nexus_v1/tests/test_regression.py # pytest wrappers also exist

# Diagnostic entry points (in nexus_v1/)
python nexus_v1/run_test.py            # 5 integration tests (static/rotation/path)
python nexus_v1/run_audit.py           # entropy audit: signal depth, layer activations, weights
python nexus_v1/run_contracts.py       # 15 layer-contract checks (C1..C6)
python nexus_v1/run_variant_contracts.py

# A single test
python -m nexus_v1.tests.test_<name>   # preferred (module form, repo root on path)
python nexus_v1/tests/test_<name>.py   # also works for tests that use sys.path '.' or __file__
```

### Two environment gotchas that will bite you

1. **Windows console is GBK.** Many tests `print` Unicode (✓ ✗ 熵 →) and crash with `UnicodeEncodeError` *after* producing useful data. Always prefix: `PYTHONIOENCODING=utf-8 python ...`. The crash is cosmetic — the test logic ran.
2. **Hardcoded paths.** Test files are inconsistent: some use `sys.path.insert(0, '.')` (require running from repo root), some use `sys.path.insert(0, "d:\\cell-cc")` (a stale `D:` drive path — these only import correctly via the `-m` module form from repo root, or need the path corrected). The robust ones use `os.path.join(os.path.dirname(__file__), '..', '..')`. Prefer `python -m nexus_v1.tests.<name>`.

There is no build step and no linter configured. `dt=0.001` (1 ms) is the simulation timestep convention, though some call sites pass `dt=1.0` — check the specific test before assuming.

## Architecture (the parts that require reading multiple files)

**One neuron model, one bundle model.** All ~45 neurons across all 6 layers are the same `Neuron` class (`components/neuron.py`) configured differently via `NeuronConfig` (modes: simple / hair_cell / afferent / multi). All ~35 connections are the same `SynapticBundle` (`circuit/bundle.py`). Behavior differences come from config + optional "compensation" sub-circuits (VoltageRegulator, BiasCurrent, CalciumRateIntegrator, DivisiveNormalization, D2Autoreceptor, Fatigue/Mitosis/Apoptosis) in `components/compensation.py`, not from subclassing.

**Signal chain (6 layers, 6 axes + thermal):**
```
MET(L1) → HC(L2) → Aff_reg/Aff_irr(L3) → Encoding(L4) → Column(L5) → Motor(L6) → Muscle → Body → World → back
```
Axes: `yaw, pitch, roll` (canals) + `oto_x, oto_y, oto_z` (otoliths) + `therm`. Built in `vestibular/chain.py`; thermal sensing is currently the abstract single `therm` axis via `ThermalMembrane` (note: `SomatosensoryChain` in `somatosensory/chain.py` exists as a class but is **not instantiated** in `VariantCircuit` — there is no `circuit.somatosensory` attribute).

**Class layering (inheritance, not modification):**
- `HebbianCircuit` (`circuit/hebbian.py`) — base: layers, bundles, structural growth (sprout/prune/mitosis).
- `VariantCircuit` (`circuit/variant_adapter.py`) — inherits and overlays 12 variant components (ECM, VascularCooling, NDR, LiquidMetalRouter, Neuromodulator/DA, ShadowSandbox, World+Body, ThermalMembrane, MuscleSystem, …). **This is the class tests use.** It overrides `get_all_neurons()`/`get_all_bundles()` to add DA + Xin-relay (but not somatosensory).
- `get_all_neurons()` / `get_all_bundles()` are the census methods every audit/ledger/vascular system iterates — what's missing from them is invisible to the whole observability stack.

**Shadow layer** (`components/shadow_sandbox.py`) — a read-only structural copy of Enc→Col→Mot, driven by Xin tension from the main system. Computes free energy / contraction; does **not** write back.

**Entropy/Noether ledger** (`nexus_v1/ledger/` subpackage — all READ-ONLY observers): `NoetherProbe` (energy/charge-KCL/Landauer/weight conservation, checked every 100 steps), `EntropyLedger` (per-layer energy/heat/ISI-entropy/transfer, every 1000 steps), `WeightEntropyProbe`, `TOPRXinLedger`, `StructuralEntropy` (H_struct, H_flow, Ω). Old import locations (`components/entropy_ledger.py`, `circuit/toprxin_ledger.py`, `circuit/noether_probe.py`) are deprecated re-export shims — import from `nexus_v1.ledger`.

**T/O/P/R/Xin loop** is the core information-processing concept: `Xin = |ξ|`, the accumulated `|predicted − actual|` prediction residual on each bundle — the only force that drives physical structural growth (sprout/fruit/mitosis).

## Working norms (from RULES.md — the project charter)

`nexus_v1/RULES.md` defines 11 enforced principles. The ones that change how you should work:

- **Don't modify mother code to add features.** New components go in separate files, integrated via inheritance/adapter (this is why `VariantCircuit` exists). The user has repeatedly emphasized minimizing changes to main project code.
- **Model before tune.** Don't change parameters "to see if it passes." Locate the dead layer via the entropy ledger → consult the cited biology → derive the value → implement with a `# REF:`/`# BIO:`/`# NORM:` annotation → re-run the entropy audit.
- **Every component carries a TYPE tag** in its docstring first line: `TYPE:BIO | SEMI | MATH | HYBRID | INFRA`.
- **Track regressions and fixes** in `cell-cell/docs/degradation_registry.md` (`DEG-XXX`) and `fix_registry.md` (`FIX-XXX`), cross-referenced.
- **Run the entropy audit after parameter changes** (signal depth must not regress; `|V|<100`; energy `>0`; no NaN).

## Current state (as of v1.7.2)

Regression 21/21 PASS, signal depth 6/6. Known open issues surfaced by testing: Col→Motor coupling weak (C6 Motor-signal contract fails under some inputs), shadow-layer free energy diverges (`K_ema` grows unbounded), lateral inhibition can drive all Columns to zero under multi-axis input, and thermotaxis behavior has not emerged. See `cell-cell/报告/` for the latest measured analysis reports.
