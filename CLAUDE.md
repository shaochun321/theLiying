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

## 结构构建原则（Structure-First, No Semantic Hardcoding）

这是本项目最核心的约束，违反会导致行为无法涌现：

**禁止的做法（语义硬编码）：**
- 用 Python 数学直接计算语义结论（如 `sign(∇T · v)` 判断"朝热源"）
- 直接向神经元注入电流而不经过 `SynapticBundle`
- 用 `if`/`sign`/`dot product` 等逻辑替代物理电路
- 把行为目标写进代码（如"朝热源移动时 DA↑"）
- 无来源地填写参数值（如 `initial_weight=0.5`）

**正确的做法：**
- 新信号路径 = 新 `SynapticBundle`（类比 `bundles_shadow_to_da`、`bundles_xin_to_da`）
- 方向性和选择性从**前后/左右补丁的激活差异**中物理涌现，不显式计算
- 每个新组件映射到真实生物/物理对象，使用 `Capacitor / MOSFET / Memristor / PowerRail` 原语
- 行为从结构中涌现（sprout/prune/STDP），不从公式中输出

**判断标准：** 如果你写了一个 `if` 或数学公式来决定 DA 的增减，就是硬编码。应该让 bundle 的 propagate() + STDP 自然完成这件事。

## ⛔ 写代码前的强制三问（违反则停止）

**任何新信号路径或新参数，必须先回答以下三问，答不出来就停下来查文献或问用户，不许动手写代码：**

```
Q1. 生物对应物是什么？
    → 写出 BIO: 注释来源（论文/教材/已有代码注释）
    → 例："BIO: 脊髓 relay → VTA 通路（Bhaskara 2011）"

Q2. 物理结构是什么？
    → 写出 Sources → SynapticBundle → Targets
    → 每一端用已有的 Neuron 对象，不能是 Python 变量

Q3. 每个参数的依据是什么？
    → initial_weight / weight_max / stdp_lr 必须有推导或实验来源
    → 例："initial_weight=5.0 # EXP-012: 0.1 too thin → DA sleeps"
    → 没有依据 = 不能填这个数字
```

如果任何一问答不上来 → **停下来，向用户说明缺少什么信息，等待指示**。

## 🧬 母本分化与元件构建原则

> 权威来源：`cell-cell/专题分析/母本分化与元件构建原则-融合版.md`

### 三层分化物理阶梯

```
Level 1: 工厂分化 (Config)
  工厂函数注入不同物理参数（_column_config / _encoding_config / _motor_config）
  存放：hebbian.py / chain.py

Level 2: 元件分化 (Compensation)  ← 新元件只能在这一层创建
  针对特定物理机制，在 compensation.py 建立独立组件，通过 NeuronConfig flag 挂载
  例：CRI (钙积分 H), DN (除法归一化 I), D2R (自受体 J)

Level 3: 运行时分化 (Homeostasis)
  由底层物理耗散驱动的动态自适应（adapt_threshold、BCM 滑动阈值、突触缩放）
  不新增文件
```

**三层的共同红线**：均不修改母本 `Neuron` / `SynapticBundle` 的核心代码。

### 信号链路按需分配铁律

> **绝对禁令：禁止基于"身份归属"（如"影子层才装 CRI"）分配组件。**

分析单位 = **连接（bundle）**，不是层（layer）。对任意一条 bundle 追问：

```
Q1. 下游 STDP 需要什么物理信号？（spike? 连续? 时变?）
Q2. 上游神经元当前提供的是否满足？
Q3. 如不满足 → 需要哪个补偿组件来桥接？
```

**血的教训（战役二）**：v0.9.0 只给影子层 Col 装了 CRI，主层 Col 遗漏。理由是"主层不需要"——这是身份标签分配。物理后果：主层 Col→Motor 的 pre_trace（τ=20ms）在 spike 间隙衰减至零，STDP 时间求和物理断裂。修复：所有向 Motor 输出的 spiking Col，无论主层/影子层，均必须挂 CRI。

### 新元件构建流程

**Step 0（前置检查）**：`compensation.py` 中是否已有同功能组件？是否有 flag=False 的待激活组件？能复用就不建新类（战役二：CRI 已存在，只需激活 flag）。

**Step 1–5（若确需新建）**：

```
Step 1: 识别信号路径需求（bundle 级，不是 layer 级）
Step 2: 映射生物对应物 → BIO: 注释（论文来源）
Step 3: 用四大原语组装类 → compensation.py
        只允许: Capacitor / MOSFET / Memristor / PowerRail
        禁止: step() 中出现 if value > threshold / clamp() / sign() / dot()
Step 4: NeuronConfig 中添加 use_xxx: bool = False + 参数字段
Step 5: 工厂函数中设 flag=True（不在 neuron.step() 函数体中激活）
```

### 基因隔离红线

任何形态发生学操作（分裂/发芽）必须使用 `deepcopy`，**不得用 `copy`**：

| 文件 | 函数 | 风险 |
|------|------|------|
| `neuron.py` L672 | `Neuron.split()` | `channels` List 共享 → 子代修改阈值污染母本 |
| `bundle.py` L646 | `SynapticBundle.sprout()` | `silent_snapshot` dict 共享 → 活跃写入 |
| `hebbian.py` L988/L1004 | `_rewire_after_split()` | 同上 |

```python
from copy import deepcopy          # ✅
child_config = deepcopy(self.config)
# 不是: from copy import copy; child_config = copy(self.config)  ❌
```

### 元件创建检查清单

```
□ Level 2 新组件 → compensation.py（不在 neuron.py 中）？
□ 使用四大原语（Capacitor/MOSFET/Memristor/PowerRail）？
□ step() 中无 if/else 硬编码数学公式？
□ NeuronConfig flag 已添加（use_xxx: bool = False）？
□ 工厂函数中激活（不在 neuron.step() 函数体中）？
□ Q1 BIO: 生物对应物已注释？
□ Q2 物理结构: Sources → Bundle → Targets 已定义？
□ Q3 参数: 每个参数有推导或实验来源？
□ 组件分配依据 bundle 功能需求，不是层归属？
□ 分裂/发芽操作使用 deepcopy(config)？
```

## 实验监控规范（长程实验强制执行）

### 账本字段：每个实验脚本必须在日志中暴露

每条 `LOG_INTERVAL` 行必须包含以下字段（新日志头格式参见 `exp_phase3_1M.py`）：

| 字段 | 来源 | 含义 | 告警阈值 |
|------|------|------|----------|
| `Nv`（Noether new） | `len(c._noether_probe._violations) - prev` | 本窗口新增违规数 | **>0 立即打印违规详情** |
| `H_w`（weight entropy） | `c._entropy_probe.summary()['total_entropy']` | 权重分布熵 | <1.0 警告（权重塌缩） |
| `R_su`（efference ratio） | `c._efference_supp_ratio` | Efference 抑制比 | ≥0.9 警告 |

每条 `SNAPSHOT_EVERY` 快照额外输出：
- `[LEDGER] Noether total=X  H_struct=Y  weight_entropy=Z`
- `[LEDGER] L5_Col_activity=A  L6_Mot_activity=B`（检测信号是否到达 Motor 层）

Noether 违规出现时立即打印 `violation_counts` 明细（如 `kcl_charge`、`energy`、`weight`）。

### 实验过程跟进规范

启动长程实验（>100k步）后，Claude 应主动阶段性检查并报告，不能仅"启动然后等结束"：

- **启动后 2-5分钟**：确认日志有输出、格式正常、无立即崩溃
- **每 ~15-20分钟**：`tail -20 <log>` 读取最新进度，报告关键指标变化趋势
- **发现异常时立即报告**：fill 触零、Noether 新增违规、权重熵跌破 1.0、AGC 饱和
- **实验结束时**：生成 Markdown 分析报告（见下节"实验报告生成规范"）

---

## 实验报告生成规范

用户要求生成报告时（或实验阶段性完成后），在 `cell-cell/工作报告/` 创建 Markdown 报告。

**命名格式：** `{主题}_{日期}.md`，例如 `Phase3-STDP冷启动-中期分析_2026-06-25.md`

**标准结构（七节）：**

```
# {标题} — {中期/最终}分析报告

报告日期 / 状态 / 实验脚本 / 日志文件 / 关联提交

## 一、实验背景        — 实验目标、补丁列表、参数配置
## 二、关键指标时间序列 — fill/DA/AGC/dist/motor 按检查点列表
## 三、束权重演化       — Col→Motor 及 Therm→Motor 权重变化表
## 四、验收标准评估     — 逐条 CR1-CR4 当前状态（PASS/FAIL+数值）
## 五、问题诊断         — 每个 FAIL 或异常现象：观察→根本原因→建议
## 六、实验进度         — 当前步数 / 预计完成时间（中期报告）
## 七、结论与下一步     — 一段结论 + 下轮参数调整草案（代码块）
```

**数据来源：**
- 日志文件：`cell-cell/工作报告/*.log`（`grep "SNAP @\|^\s\+[0-9]"` 提取检查点）
- 实验脚本：`cell-cc-other/nexus_v1/tests/exp_*.py`
- 当前状态：`cell-cell/当前状态.md`

**生成步骤：**
1. 读取日志，提取所有 `[SNAP @Xk]` 段落和每行检查点数值
2. 对照实验设计，逐条评估验收标准，给出 PASS/FAIL + 实测值
3. 诊断 FAIL 项：观察 → 根本原因 → 下轮修复建议（含参数草案）
4. 将报告写入 `cell-cell/工作报告/{命名}.md`

---

## Current state (as of 2026-06-25, STDP cold-start experiment Phase 1 complete)

**Active working directory: `cell-cc-other/`** (not the root `nexus_v1/`). Run all tests from there:
```bash
cd /j/cell-cc/cell-cc-other && PYTHONIOENCODING=utf-8 python -m nexus_v1.tests.test_regression
```

**Five patches committed (`92a04d8`) in `cell-cc-other/`, regression 21/21 PASS:**
- Patch A: AGC→Langevin (de-mean → AGC multiply → RMS clamp)
- Patch B: TemporalBindingLayer (`τ_w=30` steps, vestibular axes only) — `self.binding_layer`
- Patch C: YolkSac (`λ=0.002`/step, initial 200 units) — `self.yolk_sac`
- Patch D: DADifferentialGate (`η_da=7.5`, clip=5.0) — `self.da_gate`
- Patch E: Efference suppression ratio monitoring (INFRA) — `self._efference_supp_count/total/ratio`
- Phase 1: `process_hunger()` disabled (returns zero + DeprecationWarning)

**Next step: Phase 3 — 1M step long-run experiment** to verify thermotaxis emergence via STDP.
See `cell-cell/当前状态.md` for full handoff context and TODO list.
