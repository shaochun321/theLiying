# Walkthrough: RULE S2 递归分化沉积 — 实施总结

## 已实现的机制

| 机制 | 文件 | 状态 |
|------|------|------|
| Bundle 萌芽 (sprout) | [bundle.py](file:///d:/cell-cc/nexus_v1/circuit/bundle.py) | ✅ 工作 |
| Bundle 修剪 (prune) | [bundle.py](file:///d:/cell-cc/nexus_v1/circuit/bundle.py) | ✅ 工作 |
| 代谢税 (metabolic tax) | [hebbian.py](file:///d:/cell-cc/nexus_v1/circuit/hebbian.py) | ✅ 工作 |
| 并发限制 (sprout cap) | [hebbian.py](file:///d:/cell-cc/nexus_v1/circuit/hebbian.py) | ✅ 工作 |
| Motor rate homeostasis | [hebbian.py](file:///d:/cell-cc/nexus_v1/circuit/hebbian.py) | ⚠️ 部分 |
| RULE S2 规则文件 | [RULES_STRUCTURAL_COMPUTATION.py](file:///d:/cell-cc/nexus_v1/RULES_STRUCTURAL_COMPUTATION.py) | ✅ 完成 |

## 200k 步 (200s) 测试结果

### ✅ 结构动态平衡达成

```
54 sprouted → 48 pruned → 6 active sprouts
稳态: 38 bundles (32 原始 + 6 活跃新芽)
萌芽速率 ≈ 修剪速率（每 10k 步 ~3 sprout, ~3 prune）
```

### ✅ 代谢税生效

```
Energy: 0.899 → 0.880 (缓慢消耗)
5/48 neurons in low-energy state
```

### ⚠️ Motor rate — 前期稳定、后期加速

| 时间 | Rate | col_to_motor w | 状态 |
|------|------|---------------|------|
| 40s | 0.7 Hz | 0.204 | ✅ 稳定 |
| 80s | 1.7 Hz | 0.204 | ✅ 稳定 |
| 120s | 3.5 Hz | 0.205 | ✅ 稳定 |
| 160s | 22.6 Hz | 0.001 | ⚠️ 开始加速 |
| 200s | 76.7 Hz | 0.001 | ❌ 失控 |

根因：col_therm 无输入但持续放电 (activation=0.037)，随时间累积驱动 motor。
Rate homeostasis 衰减 col_to_motor 权重到 0.001，但 col_therm 通过该微弱路径仍提供足够持续电流。

### ❌ Motor 差异化未出现

33.3/33.4/33.3 — 三个 motor 完全均匀。

### ❌ 新芽全部被修剪

0 个新芽存活（w 从未超过 0.005 阈值）。
根因：新芽复制父 bundle 的**相同拓扑**（相同 source → 相同 target），是纯冗余。STDP 没有理由强化一个冗余路径。

---

## 迭代修复历程

| 轮次 | 问题 | 修复 | 效果 |
|------|------|------|------|
| v1 | ξ 阈值太高(2.0) | 降到 0.3 | ✅ 首次萌芽 |
| v1 | Motor 82Hz 失控 | 添加 rate homeostasis | ✅ 降到 4Hz |
| v2 | 代谢缺失 | 添加 metabolic tax | ✅ 能量消耗 |
| v2 | 修剪不触发(ξ条件) | 移除 ξ 条件 | ✅ 修剪启动 |
| v3 | 修剪计数器bug(500万步) | sustain_steps 500→2 | ✅ 修剪正常 |
| v3 | Motor weight-only衰减 | 添加阈值提升 | ⚠️ 部分有效 |
| v4 | 阈值 section 1/3 冲突 | 添加 rate 检查 | ⚠️ 部分有效 |
| v5 | bc_current 过高(0.025) | 降到 0.01, v_reset→0 | ⚠️ 前期好 |

## 已修改的文件

| 文件 | 关键修改 |
|------|---------|
| [bundle.py](file:///d:/cell-cc/nexus_v1/circuit/bundle.py) | `sprout()` + `should_prune()` with grace period |
| [hebbian.py](file:///d:/cell-cc/nexus_v1/circuit/hebbian.py) | S2 constants, `_apply_metabolic_tax()`, `_structural_growth()`, motor config (bc=0.01, v_reset=0), rate homeostasis (dual threshold+weight) |
| [RULES_STRUCTURAL_COMPUTATION.py](file:///d:/cell-cc/nexus_v1/RULES_STRUCTURAL_COMPUTATION.py) | RULE S2 定义 |

---

## 遗留问题与下一步方向

### 方向 A: 修复 Motor 后期加速

- 根因: col_therm 无输入但自发放电，长期驱动 motor
- 修复: 为不活跃的 column 减少 bc_current，或让 col_therm 在无 thermal 输入时静默

### 方向 B: 让新芽能存活（最重要的结构问题）

- 根因: 新芽复制父 bundle 的完全相同拓扑 = 冗余
- 可能方案:
  1. **跨层萌芽**: 新芽连接到不同的 target（如不同的 column neuron）
  2. **互补权重**: 新芽的初始权重模式与父不同（正交初始化）
  3. **更大电路**: 增加 neuron 数量，让盲目萌芽有未覆盖的路径可探索

### 方向 C: 实现 Phase 3 — Neuron 分裂

- 当 κ_act → 0 时分裂 neuron，创造新的结构维度
- 这可能是解决"新芽冗余"的根本方案——分裂创造新 neuron 后，萌芽才有新 target

> [!IMPORTANT]
> **核心洞察**: 当前电路的 48 neurons × 32 bundles 已经完全连接了所有必要路径。在这个尺度上，盲目萌芽只能创造冗余。结构生长要有意义，需要先有 **Neuron 分裂**来创造新的结构节点。
