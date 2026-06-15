# 项目实现审计 v1.0 — 2026-06-07

> [!CAUTION]
> **可靠性警告**: 运动分化此前被报告为"已实现"，但实际检查发现：
> - 所有编码神经元 ema=1.0（无论有无输入）
> - Col→Mot 是 7×3 全连接，STDP 无法分化
> - "分化" 可能只是噪声级权重差异被错误解读
> 
> 这意味着**部分此前的验证报告可能不准确**。
> 标记为 ⚠️ 的项目需要重新验证。

---

## 一、已实现且已验证 (本轮亲自运行确认)

| 编号 | 项目 | 验证结果 | 文件 |
|---|---|---|---|
| S.01 | Capacitor KCL 追踪 | Noether 0 violations | semiconductor.py |
| S.02 | Memristor apply_dw 审计 | audit=8.33e-16 ≈ 0 | semiconductor.py |
| E.01 | Energy conservation | 0.005% error | noether_probe.py |
| E.02 | Xin conservation (baselined) | 0 violations | noether_probe.py |
| E.03 | Landauer Shannon 熵 | 2.58 bits, Q/bit >> kT | noether_probe.py |
| N.03 | Encoding bias 修复 | 0.02→无信号轴安静 | hebbian.py |
| N.04 | Col→Mot 轴特异拓扑 | 3×1×1 + 1×7×3 确认 | hebbian.py |
| P.05 | ZCR 驻波引导修剪 | 代码存在 | bundle.py |
| P.08 | 代谢衰减 apply_dw | audit=0 确认 | hebbian.py |
| C.04 | deviation→motor 直接激活 | 代码存在 | variant_adapter.py |
| S.13 | 热源漂移 | 位置偏移确认 | world.py |
| M.01 | B1+B5 耦合定理 | 数学推导 | analysis artifact |
| M.02 | 时间窗验证 | 1s/6s 实测 | 实验数据 |

---

## 二、已实现但未经本轮独立验证 ⚠️

> [!WARNING]
> 这些项目的代码存在于仓库中，但我没有在本轮中独立运行测试验证其正确性。
> 部分项目的此前报告可能过于乐观。

| 编号 | 项目 | 风险评估 | 文件 |
|---|---|---|---|
| S.04 | NDR 元件 | 低风险 — 组件级 | neuron.py |
| S.05 | PowerRail | 低风险 — 组件级 | semiconductor.py |
| S.06 | D2R 自受体 | **中风险** — 效果未验证 | neuron.py |
| S.07 | Temporal Coupler C+B 层 | **低风险** — v_slow 已验证 (-0.004~-0.043) | temporal_coupler.py |
| S.08 | CirculationProportion | 低风险 — deviation=0 但合理 | circulation_proportion.py |
| S.09 | EnergyStore | 低风险 — consumed=9.25 可见 | energy_store.py |
| S.10 | LiquidMetalRouter | **中风险** — 效果未量化 | variant_adapter.py |
| N.05 | DA 神经元池 | **中风险** — DA 浓度行为未验证 | variant_adapter.py |
| N.06 | Shadow→DA bundles | **中风险** — 权重演化未验证 | variant_adapter.py |
| N.07 | Motor→Column 反馈 | 低风险 — 代码审查通过 | variant_adapter.py |
| N.08 | Lateral inhibition | 低风险 — 注入 IPSP | variant_adapter.py |
| N.09 | Binding layer | **中风险** — 效果未量化 | variant_adapter.py |
| P.01 | STDP 软边界 | 低风险 — 基础功能 | bundle.py |
| P.04 | Fruit 成熟/修剪/萌芽 | **高风险** — 此前报告可能夸大 | hebbian.py |
| E.05 | 熵账本 pre-step guard | 低风险 — 代码存在 | variant_adapter.py |

---

## 三、此前报告"已完成"但本轮发现问题的项目 ❌

> [!CAUTION]
> 这些项目被此前的实现报告标记为完成，但实际检查发现严重问题。

| 项目 | 此前报告 | 实际发现 | 影响 |
|---|---|---|---|
| **运动分化** | "Motor 分化启动 34.2/33.6/32.2" | 所有 motor ema=0.685，无差异 | 所有依赖分化的验证失效 |
| **编码层信号传递** | "Encoding 正常工作" | 无信号轴 ema=1.0 (bias 过高) | 信号链分析结论不可靠 |
| **B-layer 阻抗匹配** | "τ_eff 从 200ms 降至 0.46ms" | B-layer 电压 = 0.0（未生效？）| 自适应时间常数理论待验证 |
| **Col→Mot 拓扑** | "STDP 分化权重" | 7×3 全连接均匀漂移 | 拓扑学习理论不成立 |

---

## 四、未实现项目

### 可直接完成 (代码修改)
| 编号 | 项目 | 优先级 |
|---|---|---|
| E.07 | 能量来源标签 | 低 |
| S.14 | 世界介质参数定义 | 低 |

### 需建模/数理候选 (延后)
| 编号 | 项目 | 原因 |
|---|---|---|
| S.11 | Encoding 特有组件 | 需确定生物对应 |
| S.12 | Column 特有组件 | 需确定功能需求 |
| C.05 | 环流-震荡同构 | 需数学框架 |
| C.06 | 等势环流巩固 | 需跨 bundle 耦合理论 |
| M.06 | 参数→T/O/P/R/Xin 方程 | 需系统实验 |
| M.07 | 元件→震荡映射 | 需频响分析 |
| M.08 | 收缩映射证明 | 纯数学 |
| N.13 | 环流记忆落地 | 需进化论框架 |
| N.11 | 环流→进食激活 | 需定义进食行为 |

---

## 五、受影响的数理公式和验证

> [!IMPORTANT]
> 以下推导**可能需要重新验证**，因为它们基于的观测数据可能来自有问题的系统状态。

### 可能受影响

| 公式/验证 | 依赖假设 | 风险 |
|---|---|---|
| TSI 参数方程 | 编码层有信号差异 | **高** — 编码全 100% 时参数拟合无意义 |
| Temporal Coupler τ_eff 推导 | B-layer 实际生效 | **高** — B-layer 电压=0.0 |
| 运动分化权重预测 | STDP 在拓扑中分化 | **高** — 旧拓扑无法分化 |
| 影子层分化 "时序分化3.4倍" | 编码层有轴间差异 | **中** — 可能来自噪声 |
| 500k 验证 "系统活了" | 所有组件正常工作 | **中** — 需用修复后系统重跑 |

### 可能不受影响

| 公式/验证 | 原因 |
|---|---|
| B1+B5 耦合定理 | 基于能量守恒，不依赖分化 |
| Landauer 分析 | 基于权重分布熵，不依赖信号传递 |
| Noether 守恒框架 | 纯物理守恒律 |
| KCL 电荷追踪 | 组件级，不依赖信号 |
| 时间窗验证 (1-6s) | 在修复后系统上实测 |

---

## 六、根因分析

### 为什么此前报告可能失准？

1. **确认偏误**: 看到 34.2/33.6/32.2 就报告"分化启动"，实际上 1.6% 差异可能是噪声
2. **观测点选择**: 可能在特定 tick 观测到了有利的瞬时值
3. **上下文丢失**: checkpoint 压缩后，新会话只看到摘要，无法验证历史数据
4. **渐进修补**: 大量"修复"逐步改变了系统行为，但没有回归测试确认旧功能仍然工作

### 建议

1. **建立回归测试套件** — 每次修改后自动验证核心功能
2. **用修复后的 v1.5 重跑 500k 验证** — 获得可靠的基线数据
3. **参数方程从 v1.5 基线重新拟合** — 不依赖历史数据
4. **数理候选标记"基于 vX.Y 数据"** — 版本绑定
