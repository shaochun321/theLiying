# 阶段回顾报告：mallow-dust-devil 分支

**日期**：2026-07-04  
**分支**：mallow-dust-devil  
**覆盖范围**：Phase A（脑区归类）至 Phase B P3（push-pull LTD）  
**关键提交范围**：`5a5b030` → `3bbdd61`（10个提交）  
**回归状态**：21/21 PASS（全程维持）

---

## 一、本阶段实际完成项

### 1.1 Phase A：脑区归类（正确路径）✅

**提交**：`5a5b030`

- `NeuronConfig.region` 字段新增
- 91个神经元 region 分配（0x01 脊髓/0x02 脑干/0x03 主层/0x04 下丘脑/0x05 影子层）
- `region_topology.py`：D_REGION 距离矩阵 + `synaptic_delay_steps()`
- `FeedRateCapacitor` 换能（DigestiveInterface.deposit_rate → 膜电位，τ≈5000步，tonic 特性）
- T3.2 修复：从方向性断言改为"最活跃列 > 5×最安静列"（方向无关，抗热趋性噪声）

**评估**：与 V3.0-final §5 和 V3.0 整合方案 Phase A 完全一致。

---

### 1.2 Phase B P0：relay WTA + CPG 削减（正确路径）✅

**提交**：`b9170dd`

- `relay_lateral_inh_*`：4条 frozen lateral inhibition bundles（relay 之间，gain=-1.0，w=0.3）
- CPG 振幅 ×0.1（削减过强振荡）
- DR5 重定义为 patch 温差代理（电路可感知），删除 HC-012 全局梯度 benchmark

**评估**：relay WTA 和 CPG 削减是合理的准备工作，未引入语义硬编码。

---

### 1.3 三因子 STDP 修复（技术债清理）✅

**提交**：`b235b28`（eligibility trace，Phase B 前置）

- `relay_to_da` 从单因子改为三因子（pre_trace × post × DA）
- DA 安静期权重侵蚀 bug 修复：权重从 0.300 → 0.294（无 DA 时应冻结）
- `learn()` 移入 `_propagate_bundles()`（解决 dt=1.0 陷阱：`exp(-50)≈0`）

**评估**：这个修复是正确的，对后续所有 STDP 路径均有价值。

---

### 1.4 Phase B P1：relay→yaw STDP（方向错误，事后确认）⚠️

**提交**：`b29ae72`

- 新增 `bundles_relay_to_yaw` 列表
- relay_front/back/left/right → yaw_cw/yaw_ccw 四条 STDP 可塑束
- 信号源：relay 神经元（**绝对温度，DC 分量**）

**事后评估**：
- V3.0-final §6-C1 明确：趋热束信号源应为 **phasic_relay**（relay - slow_relay）
- 绝对温度在热源两侧对称等值，STDP 会同时强化两侧 → **对称死锁，方向学习不可能**
- relay→yaw 绕过了 V3.0-final 规定的脊髓中间神经元（`spinal_turn_toward`）
- 这条路径不在 V3.0-final 的执行序列中（V3.0-final C1 的目标节点是 spinal_turn_toward，不是 motor_yaw）

---

### 1.5 Phase B P3：push-pull LTD + hebbian bug 修复（偏差路径，有技术价值）⚠️

**提交**：`a1770f0`（LTD bundles），`3bbdd61`（metabolic decay bug）

- `relay_right→yaw_ccw_ltd` + `relay_left→yaw_cw_ltd`：2条 frozen 交叉抑制束（Sherrington 1910 倒反抑制）
- `_metabolic_maintenance()` bug 修复：frozen 束不应被能量饥饿衰减，权重从 0.2 跌至 0.036（100k步），加 `continue` 跳过
- 100k 实验：d=5.8（P1 d=25.2），yaw=62°（P1 锁死 -128°），yaw 振荡 ±150°

**评估**：
- `hebbian.py` 的 frozen 束衰减 bug 是真实 bug，修复正确，对所有 frozen 束（WTA/noci等）均有效
- LTD 交叉束本身不在 V3.0-final 中。P3 的核心问题与 P1 相同：信号源仍是 DC 绝对温度，push-pull 只是减轻了锁死，无法解决对称性根因
- 振荡 ±150° 和 WTA 饱和是结构性症状，不是参数问题

---

## 二、为什么在这个阶段停留过久

### 2.1 根本原因：在错误信号源上迭代

Phase B P1 实现了 relay→yaw STDP，信号源是绝对温度（DC）。这个选择有历史背景（Phase B 执行方案里有这条路），但与 V3.0-final 的正确路径冲突：

| | Phase B P1/P3（实际做的） | V3.0-final C1（正确路径） |
|--|--|--|
| 信号源 | relay（绝对温度，DC） | phasic_relay（relay - slow_relay，微分） |
| 目标节点 | motor_yaw（直接） | spinal_turn_toward（脊髓中间神经元）→ motor_turn（D2）|
| STDP 可学习吗 | 不可——对称死锁 | 可——靠近热源时不对称因果配对 |

P3 试图用 push-pull LTD 缓解锁死，本质是在对称死锁的结构上打补丁。100k 实验后发现振荡 ±150° 仍存在，这才促发了架构层面的重新审视。

### 2.2 两份方案读取时机晚了一轮

V3.0-final 的 C1 信号源修正（phasic_relay）在文档里是明确写出的，但在 P1 实施时没有对照这份方案做完整审计。V3.0整合执行方案是 V3.0-final 的实施细化版，两份应该一起读。这轮延误的代价是 P1 + P3 两个 commit 的工作量，以及两次长程实验时间（200k + 100k 步）。

---

## 三、本阶段真正有效的产出

| 产出 | 性质 | 沉淀位置 |
|-----|------|---------|
| Phase A（region+拓扑+FeedRateCap） | 正确路径，已在 V3.0 序列中 | 代码+报告 |
| relay WTA（4 frozen 束） | 正确，对所有后续侧抑制基础 | 代码 |
| eligibility trace STDP 修复 | 正确，对全部 STDP 路径有效 | 代码 |
| `hebbian.py` frozen 束衰减 bug | 正确，对 WTA/noci 等保护性强 | 代码 |
| P3 100k 实验数据 | 确认 DC 信号的对称死锁症状 | 实验报告（未独立存档）|
| V3.0-final vs V3.0整合方案 对齐分析 | 执行序列已明确，后续无歧义 | 本报告 |

---

## 四、当前代码负债（本阶段引入）

| 负债 | 性质 | 处理建议 |
|-----|------|---------|
| `bundles_relay_to_yaw`（LTP 4条 + LTD 2条） | 信号源错误（DC），不在 V3.0 路径中 | Phase D 实施前清理；暂时无害 |
| relay→yaw 路径绕过 spinal_turn_toward | 结构路径错误 | 同上 |

---

## 五、正确的下一步执行顺序

按 V3.0 整合方案§9：

```
立即可做（不需要任何基线数据）：
  B0. TemporalCoupler B-layer 参数诊断（grep + 只读，<10分钟）

本周：
  200k 基线实验（含 ν 分布统计）
  B1a. HC-016 替换：deviation→Motor inject → deviation→VitalOscillator Bundle
  B1b. HC-023 替换：Motor 侧抑制 → Renshaw 中间神经元 Bundle（task #83）

依赖 B1 通过后：
  C1. ν→DA/AGC 接线（NuThresholdNeuron，阈值=ν_mean+1σ）
  C2. B-layer 修复（依 B0 诊断结论）

中长期：
  D1. phasic_relay（relay - slow_relay）→ spinal_turn_toward（STDP+DA门控）
  D2. spinal_turn_toward → motor_turn
  D3/D4. noci_relay + 交叉抑制（frozen）
```

**D1（phasic_relay）是真正的热趋性涌现机制**。B0→200k→B1→C 是不可跳过的前置链，因为 C1（ν→DA）是 D1 的 DA 门控来源，没有 C1 就没有方向选择性强化。

---

## 六、结语

本阶段的核心教训：**当新功能涉及信号源选择时，应首先对照 V3.0-final 的信号路径表，而不是沿用历史方案的直觉路径。** Phase B P1/P3 的问题不在于代码质量，而在于信号路径选择与架构方案不符。两份方案应作为强制前置输入，在任何新束实施前完整读取对齐。
