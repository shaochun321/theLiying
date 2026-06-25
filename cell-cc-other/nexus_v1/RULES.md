# nexus_v1 Project Rules (项目纲要)

> **制定日期**: 2026-05-22
> **最后修订**: 2026-05-22 (v2: 增加原则 6-9)
> **目的**: 确保所有参数选择和结构设计有据可查，不为了"让它跑起来"而编造。

---

## 核心原则

### 原则 1: 真实对象约束 (Real-World Object Binding)

每个半导体组件都必须对应一个已知的生物/物理对象。
参数不能凭感觉设，必须从对应的生物测量值推导。

```
MOSFET.v_threshold  ←  离子通道的半激活电压 (V_half)
MOSFET.gm           ←  通道最大电导 (g_max)
MOSFET.tau_gate      ←  通道激活时间常数 (τ_activation)
Capacitor.capacitance ← 膜电容 (C_m ≈ 10 pF for hair cell)
r_leak               ←  膜输入电阻 (R_m, 决定 τ_m = R_m × C_m)
```

**违反此原则**: 如果一个参数没有对应的生物来源，必须在代码注释中标注
`# UNGROUNDED: no biological reference, needs validation`

### 原则 2: 熵账本审计 (Entropy Ledger Audit)

每次参数修改后，必须运行 CircuitObserver 并检查：
1. **信号深度** (signal_depth): 是否改善
2. **能量守恒**: dissipation + stored ≈ input (容差 < 10%)
3. **权重演化**: STDP 是否在合理方向移动
4. **无爆炸/崩塌**: 电压不超过 ±100，激活不全为零

不允许跳过熵审计直接提交参数。

### 原则 3: 建模先行 (Model Before Tune)

修改参数的流程：

```
1. 定位问题层（熵账本显示哪一层 DEAD）
2. 查阅该层对应的生物文献，获取真实参数范围
3. 建立数学模型：写出该层的输入-输出关系
4. 推导参数候选值（维度分析/归一化）
5. 在代码中实施，标注来源
6. 运行熵审计验证
```

**禁止**: 直接修改参数"试试看能不能通"。

### 原则 4: 归一化方案 (Normalization Convention)

所有参数基于以下归一化方案（从生物 mV/nA/pF 到无量纲）：

```
电压归一化:  V_norm = (V_bio - E_K) / (E_Ca - E_K)
  E_K = -80 mV (钾离子反转电位)
  E_Ca = +50 mV (钙离子反转电位)
  范围 = 130 mV
  V_rest = (-65 - (-80)) / 130 = 0.115

时间归一化:  t_norm = t_bio / dt
  dt = 0.001 (= 1 ms)
  τ = 10 ms → τ_norm = 10

电导归一化:  g_norm = g_bio / g_ref
  g_ref = max(g_MET, g_K, g_Ca) per cell type

电容归一化:  C_norm = C_bio / C_ref
  C_ref = 10 pF (typical hair cell)
```

### 原则 5: 文献溯源 (Reference Tracing)

每个参数组必须标注来源。格式：

```python
# REF: Eatock & Songer 2011, Table 1
# BIO: g_K(BK) = 20-40 nS, half-activation = -30 mV
# NORM: g_K_norm = 20/30 = 0.67, v_half_norm = 0.385
v_threshold = 0.385
gm = 0.67
```

如无法找到文献，标注：
```python
# ESTIMATED: interpolated from Goldberg 2000, Fig 3
# CONFIDENCE: medium
```

### 原则 6: 降级追踪 (Degradation Tracking)

任何观测到的信号降级、性能退化、数值异常，必须记录到
`docs/degradation_registry.md`，格式：

```markdown
### DEG-XXX: [简述]
- **发现时间**: YYYY-MM-DD
- **现象**: 描述可观测的降级表现
- **影响层**: 受影响的模块/层
- **根因**: 分析结果（可后续补充）
- **状态**: OPEN / INVESTIGATING / FIXED / WONTFIX
- **修复**: 指向修复记录 FIX-XXX（如已修复）
```

降级不会自动消失。每个 OPEN 状态的降级必须有对应的分析计划。

### 原则 7: 组件类型分类 (Component Type Classification)

每个模块/结构/元件必须标注其设计风格类别，以便快速定位和修复：

| 类型标签 | 含义 | 示例 |
|---------|------|------|
| `TYPE:BIO` | 拟真生物结构，参数来自文献 | HairCell 3-channel HH |
| `TYPE:SEMI` | 半导体等效件，用电路类比实现 | MOSFET, Memristor, PowerRail |
| `TYPE:MATH` | 纯数学硬编码，公式直接给出 | activation clamp, normalization |
| `TYPE:HYBRID` | 生物+半导体混合 | Ca²⁺ subsystem (bio decay + capacitor) |
| `TYPE:INFRA` | 基础设施/工具代码 | Observer, Audit, Logging |

标注位置：每个模块/类/函数的 docstring 首行：
```python
class SynapticBundle:
    """TYPE:SEMI — Synaptic connection modeled as memristor array."""
```

配置函数：
```python
def _haircell_config(axis):
    """TYPE:BIO — HairCell with 3 HH-equivalent ion channels.
    REF: Eatock & Songer 2011
    """
```

### 原则 8: 修复记录 (Fix Record Tracing)

每次修复必须记录到 `docs/fix_registry.md`，格式：

```markdown
### FIX-XXX: [简述]
- **日期**: YYYY-MM-DD
- **关联降级**: DEG-XXX
- **修改文件**: 列出变更的文件
- **修改内容**: 具体的参数/逻辑变更
- **推导依据**: 引用建模分析或文献
- **验证**: 熵审计结果摘要
- **副作用**: 是否引入新的降级
```

修复记录与降级记录交叉引用。可通过 DEG-XXX 追踪到 FIX-XXX，反之亦然。

### 原则 9: 完备性优先 (Completeness Before Tuning)

新构建模块的工作流程：

```
1. 建模分析：明确该模块的数学模型和预期行为
2. 构建实现：编写代码，标注 TYPE 和 REF
3. 完备性审查：
   a. 所有输入/输出端口是否连接？
   b. 能量收支是否闭合？(input ≥ dissipation + stored)
   c. 时间常数匹配？(τ_upstream ↔ τ_downstream)
   d. 边界条件处理？(NaN, Inf, 负值)
4. 记录到降级/修复注册表
5. 仅在完备性确认后，才进入测试和调参
```

**禁止**: 新模块未做完备性分析就深入测试调参。

**数学工具清单**（按需使用，不限于以下）：
- 傅里叶变换 (频域分析)
- 拉普拉斯变换 (传递函数/稳定性)
- 相平面分析 (非线性系统)
- 线性稳定性分析 (雅可比矩阵特征值)
- 蒙特卡罗模拟 (参数敏感度)
- 信息论 (互信息/传递熵)

### 原则 10: 层接口契约 (Layer Interface Contract)

逐块调整的级联问题：改上游 → 下游全要重调 → O(N²) 工作量。

**解法：接口契约**。每层定义输入输出的合格范围。
改内部参数时，只要输出仍满足契约 → 下游不需要调。

契约定义在 `docs/layer_contracts.md`，格式：

```markdown
### [层名]
- **输出类型**: continuous / spiking
- **输出范围**: [min, max]
- **动态范围**: ≥ N:1 (max/min 的倍数)
- **频率范围**: [f_min, f_max] Hz (spiking 层)
- **能量**: > E_min
- **互信息**: MI(input, output) ≥ X bits
```

**契约破坏 = 降级**：当某层输出超出契约范围，自动登记 DEG-XXX。

**契约合规 = 不级联**：内部参数变更只要不破坏契约，下游层无需修改。

### 原则 11: 母本分化 (Block Differentiation)

从母本（当前主线代码）出发，逐块查看、建模、调整。

**工作流程**：
```
1. 选择目标块（从互信息瓶颈图中选最低效率的块）
2. 单层隔离分析：
   a. 固定输入（用契约中的标准输入）
   b. 分析该层的 phase plane / 传递函数 / 能量
   c. 推导修正参数（数学推导，非试错）
3. 验证契约合规：
   a. 该层输出是否仍在契约范围内？
   b. 下游层的输入是否在契约范围内？
4. 如果契约被破坏 → 标记受影响的下游层
5. 只调整契约被破坏的层（而非全部）
```

**防止级联爆炸的三道防线**：

| 防线 | 机制 | 效果 |
|------|------|------|
| **契约隔离** | 每层有 I/O 契约，内部变更不传播 | O(N) → O(1) |
| **灵敏度矩阵** | 雅可比 ∂output_j / ∂param_i | 提前知道哪些下游受影响 |
| **自动化回归** | `run_contracts.py` 一键验证全链 | 秒级发现契约破坏 |

**灵敏度矩阵计算方法**：
```python
# 对每个参数 p_i，微扰 δ 并测量各层输出变化
for param in target_params:
    baseline = run_simulation()
    param += delta
    perturbed = run_simulation()
    sensitivity[param] = (perturbed - baseline) / delta
```

当 sensitivity 小 → 该参数对下游影响小 → 可自由调整
当 sensitivity 大 → 该参数是关键耦合点 → 需谨慎，可能需要级联调整

---

## 生物文献参考清单

| 文献 | 提供什么 | 用于哪层 |
|------|---------|---------| 
| Eatock & Songer 2011 | 前庭毛细胞电生理参数 | MET, HairCell |
| Goldberg 2000 | 传入神经 CV, 放电率 | Afferent |
| Hudspeth 2014 | MET通道动力学 | MET |
| Fettiplace & Kim 2014 | MET通道电导 | MET |
| Hodgkin & Huxley 1952 | 离子通道门控模型 | 所有通道 |
| Destexhe et al. 1994 | AdEx 脉冲模型参数 | Afferent |
| Roberts et al. 1990 | 毛细胞Ca²⁺动力学 | HairCell Ca²⁺ |
| Bao et al. 2003 | 前庭突触传递 | Bundle weights |

---

## 检查清单

每次修改后执行:

**参数合规**
- [ ] 参数有生物来源？(原则 1)
- [ ] 使用了归一化方案？(原则 4)
- [ ] 标注了文献来源？(原则 5)
- [ ] 标注了组件 TYPE？(原则 7)

**熵审计**
- [ ] 运行了 `run_audit.py`？(原则 2)
- [ ] signal_depth 改善或不退化？
- [ ] 无电压爆炸 (|V| < 100)？
- [ ] 无能量崩塌 (energy > 0)？

**追踪**
- [ ] 降级记录到 `degradation_registry.md`？(原则 6)
- [ ] 修复记录到 `fix_registry.md`？(原则 8)
- [ ] 写了数学推导 / 建模分析？(原则 3)

**新模块**
- [ ] 完备性分析完成？(原则 9)
- [ ] 端口连接验证？
- [ ] 能量收支闭合？
- [ ] 时间常数匹配？

**分化调整**
- [ ] 层契约定义或更新？(原则 10)
- [ ] 契约自动验证通过？(`run_contracts.py`)
- [ ] 灵敏度分析？(如涉及关键耦合点)
- [ ] 只调整了契约破坏的层？(原则 11)

**变体元件 (原则 12)**
- [ ] 新元件放在独立文件？(不修改现有文件)
- [ ] 集成用适配器/继承？(不修改母本代码)
- [ ] 验证门控全部通过？(G1-G5)
- [ ] git tag 已创建？
