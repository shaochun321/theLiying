# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

> **按需知识已移入项目 skill（`.claude/skills/`），对应场景必须先调用再动手：**
> - 代码改动后回归验证 / 收口复验 → **verify-regression** skill
> - 写工作报告 / 实验分析报告 → **work-report** skill
> - 写或监控长程实验脚本（exp_*.py，>10k 步）→ **exp-script** skill
> - 新增组件 / 新信号路径 / 新参数（写代码前）→ **new-component** skill

## ⚠️ 强制：每次会话开始必须执行

1. **Read `cell-cell/工作追踪/BACKLOG.md`** — 了解当前积压、执行中、暂停任务的状态
2. 告知用户当前看板摘要（一行：执行中X项 / 待执行Y项 / 暂停Z项）
3. 若用户说"继续"或未指定任务，从 BACKLOG.md 的"⚡执行中"或"📋待执行"优先级最高项开始

## 任务追踪系统

**看板文件：** `cell-cell/工作追踪/BACKLOG.md`

**操作规则（不遵守则不得动代码）：**

| 时机 | 必须做的事 |
|:---|:---|
| 决定做某任务前 | 先在 BACKLOG.md 写入"⚡执行中"，记录日期 |
| 任务完成后 | 立即移入"✅已完成"，填 commit hash |
| 发现遗留/新需求 | 加入"📋待执行"，填优先级和依赖 |
| 用户说暂缓 | 移入"⏸暂停"，写恢复条件 |
| 上下文压缩前 | 将"⚡执行中"任务的进展写清楚（到哪步/下一步是什么） |

**禁止行为：**
- 口头提及"我忘了做XX"但不写入 BACKLOG.md
- 完成任务后不更新状态
- 新会话开始时跳过 BACKLOG.md 直接动手

## 协作规范

- **语言：** 用户使用中文交流，Claude 应以中文回复。代码注释、报告文件、变量命名等技术内容保持英文。
- **环境：** 已安装 WSL（Windows Subsystem for Linux）。在 WSL 终端下运行时，编码默认为 UTF-8，无需 `PYTHONIOENCODING=utf-8` 前缀；但在 Windows 原生终端（cmd/PowerShell/Git Bash）下仍需加该前缀。
- **Bash 分类器设置：** Claude Code 默认权限模式为 `auto`，每条 bash 命令均需调用 Anthropic 安全分类器服务，服务器故障时命令全部阻断。已将全局设置 `C:\Users\shaoc\.claude\settings.json` 中的 `permissions.defaultMode` 改为 `acceptEdits`——bash 命令直接放行，仅文件写入时弹确认。如需恢复分类器保护，删除该字段即可。
- **知识库搜索：** `cell-cell/00_Dashboard/` 下的文档提供设计决策、分析报告和阶段方案的聚合搜索入口。查找项目背景、规范定义、历史报告时优先查阅该目录。TSS 理论轨的权威理论文本在 `cell-cell/理论文本_2026-08-14/`（四卷：理论主线文档集×2、理念原典审计、双聊天对照；入口先读 `理论主线文档集_2026-08-14/06_当前冻结状态与未决问题.md`）。
- **报告写法：** 存档位置 `cell-cell/工作报告/`；实施方案存档 `J:\cell-cc\cell-cell\claudecode方案\`，命名 `{主题}_{日期}.md`。模板/结构/拆分规则见 **work-report** skill。

## What this is

Cell-CC is a **neuromorphic circuit simulator built from four semiconductor primitives** — `Capacitor` (membrane / memory), `MOSFET` (threshold / ion channel), `Memristor` (plastic synapse), `PowerRail` (metabolic energy with internal-resistance gain limiting). It simulates a full sensorimotor chain from mechanical/thermal sensing to motor output, with Hebbian/STDP learning. Every component is required to map to a real biological or physical object (see `nexus_v1/RULES.md`).

Four co-existing top-level systems:
- **`nexus_v1/`** — the organism (physics + learning). The active main system.
- **`tss/`** — the TSS/基础生成元 theory track (temporal/spatial/scale generating-operator research), migrated out of `nexus_v1/{generators,relations,events}` on 2026-09-06 (pure move, zero renames — see `tss/README.md` for the old→new mapping and resume guide). **Strictly one-way dependency**: `tss/*` may import `nexus_v1/*`; the organism has zero imports of `tss/*`. It is an offline analysis/theory-validation layer wrapping live circuit objects, NOT part of the physics loop. Tests: `python -m tss.tests.test_<name>`. The theory corpus lives at `cell-cell/理论文本_2026-08-14/` (authoritative copy also at `J:/文本`, two independent sets, never overwrite each other).
- **`governance/`** — a *co-equal parallel* auditor (NOT subordinate). Runtime components (instantiated inside `VariantCircuit.__init__`, run every step): `Fuse` (physics-law circuit breaker — note: trips raise `FuseTrippedError` that nothing catches in production), `GovernanceLedger`, `Adjudicator` (J2 wired 2026-09-06). On-demand design-time tools (manual invocation only, never auto-run): `Validator`, `Modeler`, `MathCandidate`.
- **`experiments/`** — older "Morphosphere" experiment scripts (mostly hardcode `D:\cell-cc\Morphosphere_*` paths; predecessor codebase, not the current system).

`cell-cell/` is an Obsidian knowledge vault (design docs, AI logs, analysis reports — Markdown only, no code). `docs/` is an older Morphosphere version archive. Generated reports go in `cell-cell/工作报告/`. (`cell-cell/报告/` is legacy archive — do not use for new reports.)

⚠️ **Registry fork (2026-09-06, unresolved)**: `nexus_v1/docs/degradation_registry.md` (16 entries) and `cell-cell/docs/degradation_registry.md` (21 entries) have diverged with **conflicting DEG-015 numbering**. Always state which file a DEG-015~019 reference comes from. Merging needs user adjudication.

## Running tests（核心命令；全套序列与失败基线见 verify-regression skill）

**Run everything from the repo root.** The repo is at `j:\cell-cc`.

```bash
# Primary regression suite (21 checks, ~29s) — run after every change
PYTHONIOENCODING=utf-8 python -m nexus_v1.tests.test_regression   # exit 0 = pass

# A single test — prefer module form (repo root on path)
PYTHONIOENCODING=utf-8 python -m nexus_v1.tests.test_<name>
PYTHONIOENCODING=utf-8 python -m tss.tests.test_<name>
```

两个环境坑：
1. **Windows console is GBK** — 测试打印 ✓/熵/→ 会 `UnicodeEncodeError` 崩溃，崩溃是表面的（逻辑已跑完），加 `PYTHONIOENCODING=utf-8` 前缀。
2. **Hardcoded paths** — 部分旧测试硬编码 `d:\cell-cc`，只能用 `-m` 模块形式跑。

No build step, no linter. `dt=0.001` (1 ms) is the simulation timestep convention, though some call sites pass `dt=1.0` — check the specific test before assuming.

## Architecture (the parts that require reading multiple files)

**One neuron model, one bundle model.** All ~45 neurons across all 6 layers are the same `Neuron` class (`components/neuron.py`) configured differently via `NeuronConfig` (modes: simple / hair_cell / afferent / multi). All ~35 connections are the same `SynapticBundle` (`circuit/bundle.py`). Behavior differences come from config + optional "compensation" sub-circuits (VoltageRegulator, BiasCurrent, CalciumRateIntegrator, DivisiveNormalization, D2Autoreceptor, Fatigue/Mitosis/Apoptosis) in `components/compensation.py`, not from subclassing.

**Signal chain (6 layers, 6 axes + thermal):**
```
MET(L1) → HC(L2) → Aff_reg/Aff_irr(L3) → Encoding(L4) → Column(L5) → Motor(L6) → Muscle → Body → World → back
```
Axes: `yaw, pitch, roll` (canals) + `oto_x, oto_y, oto_z` (otoliths) + `therm`. Built in `vestibular/chain.py`; thermal sensing uses two parallel pathways: (1) `ThermalMembrane` scalar sensor → `mechanical_inputs['therm']` → enc/col_therm → motor (temporal/klinokinesis pathway), and (2) `SomatosensoryChain` (`somatosensory/chain.py`) — 4 directional skin patches (front/back/left/right) with nociceptors and relay neurons. **Both are instantiated**: `self.somatosensory = SomatosensoryChain()` at `variant_adapter.py:320`, `circuit.somatosensory` IS a valid attribute, relays connect to DA via `bundles_soma_to_da`. `get_all_neurons()` and `get_all_bundles()` include SomatosensoryChain components for observability.

**Class layering (inheritance, not modification):**
- `HebbianCircuit` (`circuit/hebbian.py`) — base: layers, bundles, structural growth (sprout/prune/mitosis).
- `VariantCircuit` (`circuit/variant_adapter.py`) — inherits and overlays 12 variant components (ECM, VascularCooling, NDR, LiquidMetalRouter, Neuromodulator/DA, ShadowSandbox, World+Body, ThermalMembrane, MuscleSystem, …). **This is the class tests use.** It overrides `get_all_neurons()`/`get_all_bundles()` to add DA + Xin-relay (but not somatosensory).
- `get_all_neurons()` / `get_all_bundles()` are the census methods every audit/ledger/vascular system iterates — what's missing from them is invisible to the whole observability stack.

**Shadow layer** (`components/shadow_sandbox.py`) — a read-only structural copy of Enc→Col→Mot, driven by Xin tension from the main system. Computes free energy / contraction; does **not** write back.

**Entropy/Noether ledger** (`nexus_v1/ledger/` subpackage — all READ-ONLY observers): `NoetherProbe` (energy/charge-KCL/Landauer/weight conservation, checked every 100 steps), `EntropyLedger` (per-layer energy/heat/ISI-entropy/transfer, every 1000 steps), `WeightEntropyProbe`, `TOPRXinLedger`, `StructuralEntropy` (H_struct, H_flow, Ω). Old import locations (`components/entropy_ledger.py`, `circuit/toprxin_ledger.py`, `circuit/noether_probe.py`) are deprecated re-export shims — import from `nexus_v1.ledger`.

**T/O/P/R/Xin loop** is the core information-processing concept: `Xin = |ξ|`, the accumulated `|predicted − actual|` prediction residual on each bundle — the only force that drives physical structural growth (sprout/fruit/mitosis).

**VestibularChain signal path (critical — proposals often get this wrong):** `VestibularChain.step()` returns `None`. Neurons fire inside the chain; signals propagate via `SynapticBundle.propagate()` in `HebbianCircuit.step()` through the full Enc→Col→Motor cascade — there is no direct "motor output" from the vestibular chain. Tests access motor activity by reading `Motor` neuron states after `circuit.step()`.

**Phase 4 components** (all instantiated in `VariantCircuit.__init__`, accessible as attributes): `self.agc` (AutoGainControl), `self.binding_layer` (TemporalBindingLayer, τ_w=30 steps, vestibular axes only), `self.yolk_sac` (YolkSac, λ=0.002/step, initial 200 units), `self.da_gate` (DADifferentialGate, η_da=7.5, clip=5.0), `self._efference_supp_count/total/ratio` (INFRA monitoring).

## Working norms (from RULES.md — the project charter)

`nexus_v1/RULES.md` defines 11 enforced principles. The ones that change how you should work:

- **Don't modify mother code to add features.** New components go in separate files, integrated via inheritance/adapter (this is why `VariantCircuit` exists). The user has repeatedly emphasized minimizing changes to main project code.
- **Model before tune.** Don't change parameters "to see if it passes." Locate the dead layer via the entropy ledger → consult the cited biology → derive the value → implement with a `# REF:`/`# BIO:`/`# NORM:` annotation → re-run the entropy audit.
- **Every component carries a TYPE tag** in its docstring first line: `TYPE:BIO | SEMI | MATH | HYBRID | INFRA`.
- **Track regressions and fixes** in `cell-cell/docs/degradation_registry.md` (`DEG-XXX`) and `fix_registry.md` (`FIX-XXX`), cross-referenced.
- **Run the entropy audit after parameter changes** (signal depth must not regress; `|V|<100`; energy `>0`; no NaN).

## 结构构建原则（Structure-First, No Semantic Hardcoding）

这是本项目最核心的约束，违反会导致行为无法涌现：

**禁止（语义硬编码）：** 用 Python 数学直接算语义结论（`sign(∇T·v)` 判断"朝热源"）；绕过 `SynapticBundle` 直接注入电流；用 `if`/`sign`/`dot` 替代物理电路；把行为目标写进代码；无来源填参数值。

**正确：** 新信号路径 = 新 `SynapticBundle`；方向性从前后/左右补丁的激活差异中物理涌现；每个组件映射真实生物/物理对象，用 `Capacitor / MOSFET / Memristor / PowerRail` 原语；行为从结构涌现（sprout/prune/STDP）。

**判断标准：** 如果你写了一个 `if` 或数学公式来决定 DA 的增减，就是硬编码——应该让 bundle 的 propagate() + STDP 自然完成。

**核心红旗**（写代码时自检，命中即停）：`_membrane.inject()` / `.charge =` / `.energy -=` 出现在 `step()` 循环；`dot(` / `sign(` / `if ... > ...: reward/turn/move`；`math.sin/cos` 用于运动输出；benchmark 读 `world.` 全局真值。完整反面案例表（HC-005/006/012/007/016/022/008）与元件构建流程见 **new-component** skill；完整清单 `docs/technical_debt_hardcoding.md`（HC-001～HC-060）。

## ⛔ 写代码前的强制三问（违反则停止）

**任何新信号路径或新参数，必须先回答以下三问，答不出来就停下来查文献或问用户，不许动手写代码：**

```
Q1. 生物对应物是什么？   → 写出 BIO: 注释来源（论文/教材/已有代码注释）
Q2. 物理结构是什么？     → Sources → SynapticBundle → Targets，每一端是已有 Neuron 对象，不能是 Python 变量
Q3. 每个参数的依据是什么？ → initial_weight / weight_max / stdp_lr 必须有推导或实验来源；没有依据 = 不能填
```

如果任何一问答不上来 → **停下来，向用户说明缺少什么信息，等待指示**。动手前先调用 **new-component** skill 过一遍三层阶梯、bundle 级分配铁律、deepcopy 红线和检查清单。

## 🔴 遇到问题时的处理流程

**遇到任何技术阻塞（三问无法回答、参数推导缺依据、代码行为超出预期）时：**

1. **查清根因** — 定位到具体代码行/参数/数学关系，写清楚"什么坏了、为什么坏"
2. **提交分析报告** — 写入 `cell-cell/工作报告/`，包含：根因、受影响路径、已知约束、待决策项
3. **将被阻塞任务标记为 ⏸暂停** — 在 BACKLOG.md 注明"需方案更新"
4. **继续执行其他无阻塞任务** — 不要因一个任务卡死而全停
5. **等待用户提供方案文档** — 方案文档下发后，照方案执行，不自行补全缺失信息

**禁止行为：** 没有三问支撑就"先试一个值看看"；自行猜测生物依据或参数值写入代码；把阻塞当成无限等待——继续做其他任务，并在回复末尾说明阻塞状态。

## 实验监控与报告（详规范见 skill）

- 编写/启动/监控长程实验脚本（>10k 步）前，**必须先调用 exp-script skill**：账本字段（Nv/H_w/R_su）、ν探针强制规则、定时采样节奏、早停判据、脚手架样板都在那里。
- 写报告前**调用 work-report skill**：六段式模板、命名、存档位置、极简默认原则。

## Current state

**项目整体暂停（2026-09-06，用户决定）。** 权威状态入口：`cell-cell/工作追踪/暂停快照_2026-09-06.md`（项目全景、分支状态、阅读顺序）+ `cell-cell/工作追踪/BACKLOG.md`。2026-07~08 的实际工作重心是 TSS 理论轨（见 `tss/README.md`），BACKLOG 旧条目落后于 git 实际进度。

回归基线：test_regression 21/21 PASS；contracts 13/15（C2/C3 失败 ⊆ DEG-004，OPEN）。历史实验时间线（Phase 3~8）与 P0 硬编码审计结论已沉淀在 memory 与 `docs/technical_debt_hardcoding.md`，不在此重复。

See `cell-cell/00_Dashboard/` for design decisions and `cell-cell/当前状态.md` for handoff context.
