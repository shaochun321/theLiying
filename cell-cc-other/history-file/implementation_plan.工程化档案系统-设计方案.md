# 工程化档案系统 — 设计方案

## 背景

项目已积累：
- **20 个组件** (`components/`)
- **9 个电路模块** (`circuit/`)
- **39 个文档** (`docs/`) — 但缺乏结构化索引和关联
- **398 个对话制品** (artifacts) — 无法从中快速找到特定信息

当前问题：
1. 没有全局结构图 → 不知道系统长什么样
2. 没有组件档案 → 不知道每个文件为何存在、行使什么功能
3. 没有修改历史 → 不知道哪些修改影响了哪些区域
4. 没有理论索引 → 不知道哪些理论应用在哪里
5. 会话断裂后知识丢失 → 反复踩坑

---

## 提议的档案系统

### 目录结构

```
nexus_v1/docs/
├── REGISTRY.md              ← 主索引（所有档案的入口）
├── atlas/                   ← 架构地图集
│   ├── GLOBAL_ARCH.md       ← 全局结构图
│   ├── LOCAL_vestibular.md  ← 局部：前庭链
│   ├── LOCAL_circuit.md     ← 局部：Hebbian 电路
│   ├── LOCAL_motor.md       ← 局部：运动决策
│   ├── LOCAL_entropy.md     ← 局部：熵账本+Noether
│   └── RELATIONS.md         ← 全局↔局部关系
├── components/              ← 组件档案
│   ├── neuron.md            ← 每个组件一个文件
│   ├── bundle.md
│   ├── memristor.md
│   ├── temporal_coupler.md
│   ├── ...
│   └── INDEX.md             ← 组件索引表
├── theory/                  ← 理论档案
│   ├── T001_noether.md      ← Noether 守恒
│   ├── T002_stdp_bcm.md     ← 学习规则
│   ├── T003_fruit.md        ← Fruit 生命周期
│   ├── T004_circulation.md  ← 环流理论
│   ├── T005_TSI.md          ← T·S·I 框架
│   └── INDEX.md
├── history/                 ← 修改历史
│   ├── FIX_registry.md      ← 修复记录（已有，迁移）
│   ├── CHANGELOG.md         ← 版本变更（已有，迁移）
│   └── DECISIONS.md         ← 关键设计决策记录
└── verification/            ← 验证档案
    ├── REGRESSION.md        ← 回归测试说明+与熵账本关系
    └── EXPERIMENTS.md       ← 实验记录索引
```

---

### 档案 1: 全局结构图 (`atlas/GLOBAL_ARCH.md`)

包含：
- Mermaid 图：信号链全局流向
- 层级表：每层有多少神经元/bundle，行使什么功能
- 数据流表：输入→处理→输出的完整路径
- 尺度表：从 spike (0.001s) 到 maturation (1Ms) 的跨尺度结构

> [!IMPORTANT]
> 这是最核心的文档——新会话第一件事就应该看它。

### 档案 2: 局部结构图 (`atlas/LOCAL_*.md`)

每个局部文档包含：
- 该区域的 Mermaid 内部结构图
- 包含哪些文件/类/函数
- 为何如此分化（历史原因 + 理论依据）
- 与其他区域的接口（输入什么，输出什么）
- 已知问题和待改进点

### 档案 3: 组件档案 (`components/*.md`)

每个组件文件包含：

```markdown
# [组件名] — [一句话描述]

## 物理对应
BIO: [生物对应物]
EE: [电路对应物]

## 所在文件
[file link]

## 功能
[该组件行使什么功能]

## 应用的理论
[哪些理论/公式/原理]

## 参数
| 参数 | 值 | 来源 | 理由 |
|---|---|---|---|

## 与其他组件的关系
[Mermaid 图或列表]

## 修改历史
| 版本 | 日期 | 变更 | 原因 |
|---|---|---|---|
```

### 档案 4: 理论档案 (`theory/*.md`)

每个理论文件包含：
- 理论描述（公式 + 直觉）
- 应用位置（哪些文件、哪些行）
- 实验验证状态
- 与其他理论的关系

### 档案 5: 修改历史 (`history/DECISIONS.md`)

关键设计决策记录：

```markdown
## D-001: 为什么用 EMA 而不是瞬时 activation

**日期**: 2026-05-xx
**影响区域**: neuron.py, bundle.py
**决策**: 所有层间通信使用 _activation_ema
**理由**: 瞬时 activation 在 spiking 模式下大部分时间=0
**替代方案**: 使用 pre_trace（被否决：衰减太快）
```

### 档案 6: 关系地图 (`atlas/RELATIONS.md`)

```markdown
## 组件间依赖关系

Neuron → Memristor (via Bundle)
Memristor → Bundle (权重承载)
Bundle → TemporalCoupler (时间尺度桥接)
TemporalCoupler → NoetheProbe (能量审计)
...

## 理论→代码映射

T001_noether → noether_probe.py (验证)
T001_noether → bundle.py L399 (Xin conservation ledger)
T002_stdp → bundle.py L286 (STDP rule)
T003_fruit → bundle.py L436 (lifecycle)
T005_TSI → variant_adapter.py L533 (A7 motor potential)
```

---

## Open Questions

> [!IMPORTANT]
> 1. **维护成本**：这套系统需要每次代码变更后更新。你希望我在每次修改后自动更新对应档案，还是定期批量更新？
> 2. **粒度**：组件档案是按文件（20个）还是按类（约40个）建立？
> 3. **历史追溯**：修改历史是从现在开始记录，还是需要我回溯既往所有修改？既往修改可以从 git log 和对话记录中提取。
> 4. **存放位置**：放在 `nexus_v1/docs/` 下（随代码提交），还是放在 artifacts 目录下（对话级别）？我建议放 `docs/` 下随代码 Git 管理。

---

## 工作量估算

| 档案 | 文件数 | 工作量 | 优先级 |
|---|---|---|---|
| 全局结构图 | 1 | 30min | P0 |
| 局部结构图 | 5 | 1h | P1 |
| 组件档案 | ~20 | 2h | P2 |
| 理论档案 | ~5 | 1h | P1 |
| 修改历史 | 3 | 30min | P2 |
| 关系地图 | 1 | 30min | P1 |
| **总计** | **~35** | **~5h** | |

## 建议执行顺序

```
1. 全局结构图 (GLOBAL_ARCH.md) — 最核心，一切的起点
2. 关系地图 (RELATIONS.md) — 连接全局和局部
3. 理论档案 (theory/) — 回答"为什么"
4. 局部结构图 (LOCAL_*.md) — 展开每个区域
5. 组件档案 (components/) — 最细粒度
6. 修改历史 — 从现在开始累积
```

## 验证计划

- 新会话启动时读 GLOBAL_ARCH.md → 应能在 2 分钟内理解系统全貌
- 修改任何代码前查 RELATIONS.md → 应能看到影响范围
- 回归测试与档案交叉验证：每个 T*.md 理论文件标注"已验证/未验证"

---

*回归测试应加入 REGISTRY.md 的引用，但不与熵账本合并——它们在不同层面工作。*
