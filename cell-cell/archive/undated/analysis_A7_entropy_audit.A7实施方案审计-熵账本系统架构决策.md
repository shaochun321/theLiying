# A7 实施方案审计 + 熵账本系统架构决策

---

## §1 A7 方案实现状态

[原始方案](file:///d:/cell-cc/history-file/implementation_plan.A7-%E8%BF%90%E5%8A%A8%E5%8A%BF-%E7%86%B5%E8%B4%A6%E6%9C%AC%E7%BB%93%E6%9E%84%E8%BF%BD%E8%B8%AA-%E5%AE%9E%E7%8E%B0%E6%96%B9%E6%A1%88.md) 提出了两大工作：

### 1.1 运动势 ν = dK/dt

| 条目 | 方案要求 | 实现状态 |
|---|---|---|
| `kinetic_energy` 字段 | MotionState 添加 | ✅ 字段已声明 (L89) |
| `motor_potential` 字段 | MotionState 添加 | ✅ 字段已声明 (L90) |
| `motor_potential_xyz` 字段 | 轴分量 ν_x,ν_y,ν_z | ✅ 字段已声明 (L92) |
| `polarization` 字段 | P_ν 偏振度 | ✅ 字段已声明 (L95) |
| **body integration 后计算** | 在 variant_adapter step 中计算 | **❌ 从未实现** |

**结论**: 字段定义了但**没有接线** — 值永远是初始值 0.0。

### 1.2 熵账本结构追踪

| 条目 | 方案要求 | 实现状态 |
|---|---|---|
| H_struct (结构熵) | noether_probe 新增 | ⚠️ 实现在 toprxin_ledger.py `StructuralEntropy` 中（不在 noether_probe） |
| H_flow (流程熵) | noether_probe 新增 | **❌ 从未实现** |
| Ω (规模参数) | noether_probe 新增 | **❌ 从未实现** |
| P_ν × H_flow ≈ const | 数理基因验证 | **❌ 无法验证**（ν 和 H_flow 都未实现） |

---

## §2 当前熵系统全貌

代码中存在 **三个独立的"熵"相关系统**，彼此分离：

```
┌─────────────────────────────────────────────────────────────┐
│                      熵系统全景                              │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  1. EntropyLedger (entropy_ledger.py, 473行)                │
│     ├── 能量收支追踪                                         │
│     ├── ISI 熵 (spike regularity)                           │
│     ├── 层间传递熵 (information transfer)                    │
│     ├── Landauer 约束检查                                   │
│     ├── Registry 整合                                       │
│     └── 状态: ❌ 从未实例化 (仅测试文件使用)                  │
│                                                             │
│  2. WeightEntropyProbe (toprxin_ledger.py, ~100行)          │
│     ├── 权重 Shannon 熵                                     │
│     ├── 热积累 (Landauer)                                   │
│     └── 状态: ✅ 集成到 step loop (每100步)                  │
│                                                             │
│  3. StructuralEntropy (toprxin_ledger.py, ~90行)            │
│     ├── 递归树深度分布熵                                     │
│     ├── 分支因子                                            │
│     ├── 存活率                                              │
│     └── 状态: ✅ 集成到 step loop (每1000步)                 │
│                                                             │
│  未实现:                                                     │
│     ├── H_flow (信号流方向性)                                │
│     ├── Ω (系统规模参数)                                     │
│     ├── P_ν × H_flow ≈ const (运动-信息耦合)                 │
│     ├── 影子层能量账本                                       │
│     └── DA 回路能量账本                                      │
└─────────────────────────────────────────────────────────────┘
```

---

## §3 架构问题分析

你提到的核心问题：**熵账本系统是与主系统并行的大系统，是否需要独立在 nexus_v1 外？**

### 当前问题

1. **职责混乱**: `EntropyLedger` 是 READ-ONLY 观测器，但放在 `components/` 下（与 Neuron, Bundle 同级），暗示它是系统组件
2. **名称冲突**: `_entropy_ledger_pre_step()` 方法名暗示调用 `EntropyLedger`，实际调用的是 `WeightEntropyProbe`
3. **分散实现**: 三个熵系统分散在两个文件中，没有统一接口
4. **覆盖不全**: 只追踪主层权重熵，影子层/DA/Coupler 均不追踪

### 三种架构方案

#### 方案 A: 独立包 (nexus_v1 外)

```
cell-cc/
├── nexus_v1/           # 主系统（被观测对象）
│   ├── components/
│   ├── circuit/
│   └── ...
├── entropy_ledger/     # 独立的观测系统
│   ├── __init__.py
│   ├── core.py         # 统一 Ledger 接口
│   ├── energy.py       # 能量收支追踪
│   ├── information.py  # 信息论指标 (ISI, transfer, H_flow)
│   ├── structural.py   # 结构熵 + Ω
│   ├── thermodynamic.py # Landauer + Noether 约束
│   └── reporter.py     # 输出格式化
└── ...
```

| 优点 | 缺点 |
|---|---|
| 完全解耦：nexus_v1 改代码不影响账本 | 需要稳定的观测接口 (API 契约) |
| 可独立测试 | 跨包引用增加复杂度 |
| 避免循环依赖 | 观测频率难以精确控制 |
| 清晰的"被观测者/观测者"边界 | |

#### 方案 B: 统一到 nexus_v1/ledger/ 子包

```
nexus_v1/
├── components/
├── circuit/
├── ledger/             # 内部子包，仍属于 nexus_v1
│   ├── __init__.py
│   ├── energy_ledger.py
│   ├── information_ledger.py
│   ├── structural_ledger.py
│   ├── toprxin_ledger.py  # 移入
│   └── reporter.py
└── ...
```

| 优点 | 缺点 |
|---|---|
| 与 step loop 紧密集成 | 仍在同一包内，耦合风险 |
| 无跨包引用 | 随 nexus_v1 一起膨胀 |
| 最小迁移成本 | |

#### 方案 C: 保持现状但修复连接

不改架构，只把 `EntropyLedger` 实例化到 `VariantCircuit.__init__()` 并在 step loop 中调用 `.record()`。

| 优点 | 缺点 |
|---|---|
| 最小改动 | 不解决架构混乱 |
| 快速生效 | 随着系统增长会更乱 |

---

## §4 建议

> [!IMPORTANT]
> **方案 B (nexus_v1/ledger/ 子包) 是最务实的选择。**

理由：
1. 熵账本需要在 step loop 中以**精确的步频**采样（每步/每100步/每1000步），独立包无法自然做到这一点
2. 它读取的是 `Neuron.heat_output`, `Bundle.xin_tension`, `MotionState.kinetic_energy` 等内部状态，这些不是公开 API
3. 子包给出清晰的职责边界（`ledger/` 下的所有文件都是 READ-ONLY 观测器），但避免跨包引用的复杂度

### 具体步骤

```
1. 创建 nexus_v1/ledger/ 子包
2. 移入: entropy_ledger.py, toprxin_ledger.py
3. 合并: WeightEntropyProbe + StructuralEntropy + EntropyLedger → 统一 Ledger 接口
4. 新增: H_flow, Ω, ν 计算
5. 扩展覆盖: shadow neurons, DA circuit, coupler
6. 在 variant_adapter 中用统一接口替换散落的调用
```

> [!WARNING]
> 无论选哪个方案，**先实现 A7 的 ν 计算**是前提。
> H_flow 和 P_ν × H_flow 的数理基因验证需要 ν 先有值。
> ν 的计算依赖 body integration（已存在），只需在 step 末尾补上 K = ½mv² 和 dK/dt。
