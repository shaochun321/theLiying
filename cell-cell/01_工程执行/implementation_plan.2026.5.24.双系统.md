# 熵账本系统升级为并行治理系统

## 目标

将 EntropyLedger 从"只读被动观测器"升级为与项目并行运行的**治理系统**,
具备: 熔断、裁决、批准、建模分析、数理候选 五大职能。

> [!IMPORTANT]
> 核心原则: 每次构建/修改项目时, 治理系统必须被同等对待。
> 不允许"先改代码再补审计"——治理系统与代码修改同步运行。

---

## 双系统架构

```
┌─────────────────────────────────┐  ┌─────────────────────────────────┐
│     nexus_v1 (生物体)            │  │   Entropy Governance (治理)      │
│                                 │  │                                 │
│  客观层: 物质结构 + 物理         │  │  1. 熔断: 违反物理定律 → 停机    │
│  主观层: ds²/ν/Xin 构建         │  │  2. 裁决: 新模块是否合规         │
│                                 │  │  3. 批准: 参数修改的物理合理性   │
│  运行时:                        │  │  4. 建模: 独立数学模拟验证       │
│    circuit.step() 每步运行      │←→│  5. 候选: 数理公式的提案/评审    │
│                                 │  │                                 │
│  代码位置:                      │  │  代码位置:                      │
│    components/                  │  │    governance/                   │
│    circuit/                     │  │    governance/fuse.py           │
│    vestibular/                  │  │    governance/adjudicator.py    │
│    docs/                        │  │    governance/validator.py      │
│                                 │  │    governance/modeler.py        │
│                                 │  │    governance/math_candidate.py │
│                                 │  │    governance/ledger.py (迁移)  │
└─────────────────────────────────┘  └─────────────────────────────────┘
```

---

## Proposed Changes

### governance 模块 (全部 [NEW])

#### [NEW] `governance/__init__.py`
模块初始化, 导出 GovernanceSystem 主类。

#### [NEW] `governance/ledger.py`
从 `components/entropy_ledger.py` 迁移并扩展。
保留全部现有功能 + 添加阈值检查接口。

#### [NEW] `governance/fuse.py` — 熔断器

```
职能: 运行时物理定律违反检测 → 立即停机

检测项:
  F1. 能量守恒: E_total(t) > E_total(0) + Σ E_input (热一)
  F2. 熵单调: dS/dt < 0 持续 > 100步 (热二)
  F3. 权重边界: w ∉ [0, 1] (忆阻器物理)
  F4. 膜电位发散: |V| > V_max (数值不稳定)
  F5. 能量耗尽: E_neuron < 0 (物理不可能)

触发: 打印诊断 + 抛出 FuseTrippedError
可配置: 严格模式 (立即停) / 警告模式 (记录但继续)
```

#### [NEW] `governance/adjudicator.py` — 裁决器

```
职能: 新模块/修改是否符合项目公理

裁决规则 (基于 §0 公理):
  J1. 主观层是否访问了客观层变量? (Ω-1 违反)
  J2. 新组件是否修改了只读观测器的读写约束? (Ψ-1 O相违反)
  J3. 学习规则是否绕过了 plasticity_gate? (客观层完整性)
  J4. 新参数是否有物理来源/文献支持?
  J5. 新公式是否与 G-001 v2.0 一致?

输出: APPROVED / REJECTED / CONDITIONAL (附条件)
```

#### [NEW] `governance/validator.py` — 批准器

```
职能: 参数修改的物理合理性检查

验证规则:
  V1. 尺度一致性: 新参数的量纲是否匹配
  V2. 边界合理性: 参数是否在物理可能的范围内
  V3. 稳定性: 参数修改是否导致 τ < dt (数值不稳定)
  V4. 对称性: 对称化操作的来源是物理还是人工?
  V5. 基线影响: 参数修改是否破坏基线活动?

输出: 通过/不通过 + 影响评估
```

#### [NEW] `governance/modeler.py` — 建模分析器

```
职能: 独立数学模拟, 在修改代码前验证假设

功能:
  M1. 单步扫描: 扫描参数空间, 预测行为
  M2. 稳定性分析: 线性化 + 特征值检查
  M3. 增益链追踪: 从输入到输出的信号增益链
  M4. 耦合增益验证: Paper 3 §4.4 的 coupling_gain 安全区间
  M5. 基线计算: 给定 (bc_current, R, C, V_th) → 预测基线活动

使用场景:
  修改参数前 → modeler.predict(param_changes) → 预测结果
  如果预测不合理 → 不执行修改
```

#### [NEW] `governance/math_candidate.py` — 数理候选

```
职能: 数学公式的提案、评审、追踪

功能:
  C1. 提案: 新公式 + 物理来源 + 预期效果
  C2. 评审: 与 G-001 v2.0 的一致性检查
  C3. 追踪: 公式从提案→验证→采纳→撤回的生命周期
  C4. 存档: 被拒绝的公式也保留记录 (避免重复提案)

格式:
  每个候选是一个结构体:
    id, formula, source, expected_effect, status
    status ∈ {proposed, testing, adopted, rejected, withdrawn}
```

---

### 与 variant_adapter 的集成

#### [MODIFY] `circuit/variant_adapter.py`

在 `step()` 的开头和结尾添加 governance 钩子:

```python
def step(self, ...):
    # ── 0. Governance pre-check ──
    self.governance.pre_step_check(self)
    
    # ... 现有 step 逻辑 ...
    
    # ── N+1. Governance post-check ──
    self.governance.post_step_check(self)
```

pre_step_check: 熔断检查 (F1~F5)
post_step_check: 熵记录 + 增量异常检测

---

## Open Questions

> [!IMPORTANT]
> 1. governance/ 目录放在 nexus_v1/ 下还是与 nexus_v1/ 平级?
>    - 放在下面: 方便导入, 但概念上它不是项目的一部分
>    - 放在平级: 体现"并行", 但需要处理导入路径

> [!IMPORTANT]
> 2. 熔断器应该在生产运行中总是开启, 还是可以关闭?
>    - 用户立场可能是: 始终开启, 因为物理定律不可违反

> [!IMPORTANT]
> 3. 裁决器是运行时检查还是代码审查工具?
>    - 运行时: 自动但有性能成本
>    - 代码审查: 手动但零运行时成本
>    - 建议: 关键规则 (J1, J2) 运行时, 其余代码审查

---

## Verification Plan

### Automated Tests
- 熔断器: 注入违规条件 → 验证触发
- 裁决器: 构造违规模块 → 验证拒绝
- 建模器: 对已知参数 → 验证预测匹配实际

### Integration Test
- 运行 20k 步完整模拟 → governance 全程参与
- 确认无性能退化 (governance 应 < 5% 开销)
