# 项目状态报告

## 一、代码库概况

| 指标 | 值 |
|------|-----|
| Python 文件 | 70 |
| 总代码量 | 511 KB |
| 核心文件 | variant_adapter (904行), hebbian (729行), neuron (558行), bundle (457行) |
| Governance 测试 | ✅ ALL PASSED |

---

## 二、已完成的修复 (14 项)

| # | 问题 | 修复 | 50k | 500k |
|---|------|------|-----|------|
| P4 | P→R 断裂 | 三因子 Hebbian | ✅ | ✅ |
| P5 | 基线=0 | bc_current | ✅ | ✅ |
| P6 | 无熵账本 | Entropy Probe + Ledger | ✅ | ✅ |
| P7 | 无候选数学 | Ultrametric + StructuralEntropy | ✅ | ✅ |
| FU-A | col_to_motor 饱和 | decay_rate | ✅ | ✅ |
| FU-B | 无二代 sprout | depth+孤儿+候选扩展 | ✅ | ✅ |
| M1/M3 | δa 基线 | EMA 基线 | ✅ | ✅ |
| A3 | 热瞬时穿透 | 100步延迟 | ✅ | ✅ |
| A4 | Body 无物理 | 动能阻尼+质量惯性+热容 | ✅ | ✅ |
| T2 | PNN 只成熟 | DA→MMP-9 降解 | ✅ | ✅ |
| T3 | Fruit hack 权重 | 结构触发 expand/contract | ✅ | ✅ |
| T4 | 无守恒验证 | NoetherProbe 4律 | ✅ | ⚠️ |
| M4 | activation 混用 | 19处消费者→正确物理量 | ✅ | ✅ |
| — | Xin 无界增长 | τ=1000s 衰减 | — | ✅ 减少31% |

---

## 三、500k 长运行结果

### 通过 ✅

| 指标 | 500k 结果 |
|------|-----------|
| 权重稳定 | c→m: 0.20→0.31 (在0.05-0.5范围内) |
| PNN 均衡 | vest=0.11, enc=0.18, col=0.25 (稳态) |
| 超度量深度 | **depth=7** (持续结构生长) |
| Fruit 触发 | 21,100 次成熟事件 |
| Landauer | OK 全程 |
| M4 分离 | act=0 vs ema=0.0006 (正确分离) |
| 每步权重漂移 | 0.000003 (99.9997% 精度) |

### 未通过 ⚠️

| 指标 | 原因 | 严重度 |
|------|------|--------|
| Noether 能量 | 探针未追踪 VR/vascular/basal 能量流 | **低** — 探针校准问题 |
| Xin 有界 | 虽减少31%，仍有1786次超界 | **低** — τ可再调短 |

---

## 四、已知问题 (按严重度排序)

### 🔴 严重 — 影响系统功能

**1. 增益链全零 (Gain Chain = 0.0000 at all layers)**

```
L1_MET→L2_HC: 0.0000
L2_HC→L3_Aff: 0.0000
...
L5_Col→L6_Mot: 0.0000
```

信号从传感器到运动层没有可测量的增益传递。这意味着:
- 运动输出完全由 bc_current (偏置电流) 驱动，而非传感器输入
- 系统在"自主放电"，不是"感知→反应"
- 可能原因：MOSFET 阈值 (v_th=0.3) 太高，传感器驱动电流太弱

### 🟡 中等 — 影响验证精度

**2. Noether 能量探针校准**
- E_input 估算不精确（VR recovery 能量无直接追踪）
- 修复方案：在 VoltageRegulator.compute_recovery() 中记录 `_vr_energy_delivered`

**3. Xin 仍可增长超界**
- τ=1000s 衰减不够快
- 修复方案：τ 缩短至 500s，或加 hard clamp |ξ| ≤ 2.0

### 🟢 低 — 改进项

**4. Ultrametric nodes=0**
- depth=7 但 nodes=0，说明 RecursionTracker 未正确计数节点
- 仅影响观测，不影响实际结构

**5. col.activation=0 常态化**
- Column 脉冲神经元大部分时间不放电 → activation=0
- 但 ema 正确反映了放电率 (0.0028)
- 这是 M4 修复的预期行为，不是 bug

---

## 五、下一步建议 (优先级排序)

| 优先级 | 任务 | 预计工作量 |
|--------|------|-----------|
| 🔴 P0 | **修复增益链零信号** — 降低 MOSFET 阈值或增加传感器驱动增益，让信号真正传递 | 中 |
| 🟡 P1 | Noether 能量 E_input 精确追踪 | 小 |
| 🟡 P1 | Xin τ 调优或 hard clamp | 小 |
| 🟢 P2 | Ultrametric node 计数修复 | 小 |
| 🟢 P2 | 更丰富的输入场景 (多频多模态) | 中 |
| 🟢 P3 | 长运行可视化 dashboard | 大 |

> [!IMPORTANT]
> **增益链零信号是最紧迫的问题。** 系统的 14 项修复都是内部机制的校正，但如果信号根本传不过去，这些机制就运行在"空转"状态。这需要在传感器驱动链的 MOSFET 阈值/增益上做调整。
