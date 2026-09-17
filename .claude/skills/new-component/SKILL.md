---
name: new-component
description: cell-cc 元件构建与母本分化原则。新增组件、新信号路径、新参数之前（动手写代码前）必须调用。含三层分化物理阶梯、bundle 级三问、新元件构建流程 Step 0-5、deepcopy 基因隔离红线、创建检查清单、HC 硬编码反面案例表。
---

# 元件构建与母本分化（new-component）

> 权威来源：`cell-cell/专题分析/母本分化与元件构建原则-融合版.md`；完整违规清单：`docs/technical_debt_hardcoding.md`（HC-001～HC-060）

## 三层分化物理阶梯

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

## 信号链路按需分配铁律

> **绝对禁令：禁止基于"身份归属"（如"影子层才装 CRI"）分配组件。**

分析单位 = **连接（bundle）**，不是层（layer）。对任意一条 bundle 追问：

```
Q1. 下游 STDP 需要什么物理信号？（spike? 连续? 时变?）
Q2. 上游神经元当前提供的是否满足？
Q3. 如不满足 → 需要哪个补偿组件来桥接？
```

**血的教训（战役二）**：v0.9.0 只给影子层 Col 装了 CRI，主层 Col 遗漏，理由是"主层不需要"——身份标签分配。物理后果：主层 Col→Motor 的 pre_trace（τ=20ms）在 spike 间隙衰减至零，STDP 时间求和物理断裂。修复：所有向 Motor 输出的 spiking Col，无论主层/影子层，均必须挂 CRI。

## 新元件构建流程

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

## 基因隔离红线

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

## 元件创建检查清单

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
□ TYPE 标签在 docstring 首行（TYPE:BIO | SEMI | MATH | HYBRID | INFRA）？
```

## ❌ 硬编码反面案例（2026-07-02 审计教训）

以下模式在历史代码中造成实验结论全部失效，严禁再次出现：

| 反面案例 | HC | 为何是硬编码 | 正确做法 |
|---------|-----|------------|---------|
| `mechanical_inputs['yaw'] += (T_right-T_left) * G_ORIENT` | HC-005 | Python 减法直接算"右侧热→右转"，跳过全部 Bundle/STDP | patch→relay→motor SynapticBundle |
| `feed_alignment = max(0, dot(heat_dir, vel_dir))` | HC-006 | 点积直接判断"朝热源移动"，Python 变量而非 Neuron | front/back patch 差异→feed relay Bundle |
| `DR5 = dot(world.gradient_at(pos), velocity)` | HC-012 | benchmark 用电路无法访问的全局梯度特权信息 | 只用 patch 温差（电路可感知的信号）|
| `enc.step(tonic_val * 5.0, dt)` 绕过 Bundle | HC-007 | 直接注入热觉编码，STDP 第一跳无法学习 | bundles_extra_to_enc SynapticBundle |
| `neuron._membrane.inject(drive, dt)` 在 `step()` 中 | HC-016/017/023/024 | 绕过 Bundle，Noether/census/STDP 全部失效 | 建 SynapticBundle，让 propagate() 流经 |
| `if birth > 0: expand; else: contract` | HC-022 | if/sign 替代物理比较器 | MOSFET 比较器电路 |
| `self.activation = release_rate`（覆盖 MOSFET 输出）| HC-008 | 丢弃半导体物理结果，用 Python 变量代替 | 独立 ReleaseNeuron + Bundle |

**if/else 精确范围（用户 2026-07-09 确认）**：`step()` 内算行为数值禁止；构造期接线/边界防护允许。

**已知物理陷阱**：Memristor `weight_max=1.0` 会卡电导上限 + 对称性打破扰动 → PowerRail 饱和 → 假性不对称，建议 `weight_max ≤ 0.5`。
