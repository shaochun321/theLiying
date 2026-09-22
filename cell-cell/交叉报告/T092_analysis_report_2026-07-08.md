# T-092 分析报告：DA-Gating 失效根因分析

**日期**: 2026-07-08
**状态**: 分析完成，根因确认

---

## 1. 执行摘要

T-092 随机 DA 拷打实验**确认诈胡**：用 `random.uniform(0,1)` 替换真实 DA 信号后，学习不仅没有崩溃，反而**更快饱和**。DA-gating 机制无法阻止无关 DA 信号驱动学习，gate 退化为一个"学习速率旋钮"而非真正的开关。

## 2. Bug 修复

### 诊断脚本字符串比较 Bug（已修复）

`diag_T092_rootcause.py:54`:
```python
# Bug: trace_da("RANDOM-DA") 传入大写，但比较的是小写
if da_mode == "random":  # "RANDOM-DA" != "random" → 永不为真！
    c.dopamine._concentration = random.uniform(0.0, 1.0)
```

**结果**: 两个条件都运行了 REAL-DA，产生完全相同的输出。这是之前看到"identical"的原因，不是 DA-gating 的固有属性。

**修复**: 改为 `if da_mode in ("random", "RANDOM-DA"):`

## 3. 修复后实测数据

### 诊断 (`diag_T092_rootcause.py`)：

| 指标 | REAL-DA | RANDOM-DA | 差异 |
|------|---------|-----------|------|
| DA_ema (40k步) | 0.1769 | 0.5085 | **2.87×** |
| w (2k步) | 0.0003 | 0.0052 | **17×** |
| w (20k步) | 0.0090 | 0.0382 | **4.2×** |
| w (30k步) | 0.4784 | **1.0000** | 随机先饱和 |
| w (40k步) | 1.0000 | 1.0000 | 都饱和 |

### T-092 实验 (`exp_T092_da_decorrelation.py`)：

| 指标 | REAL-DA | RANDOM-DA |
|------|---------|-----------|
| w_learned | 1.0000 | 1.0000 |
| gain(hungry) | 2.000 | 2.000 |
| gain(full) | 1.702 | 1.702 |
| E1 调制 | 0.298 | 0.298 |

**判定**:
- J1 (w < 0.5): **FAIL** — 随机DA下权重饱和到 1.0
- J2 (E1差 > 0.1): **FAIL** — 两种条件增益调制完全相同

## 4. 根因分析

### 4.1 直接原因：DA 始终为正 → LTP gate 永远部分开启

`bundle.py:405-411`:
```python
ltp = eligibility_gain × E(t) × DA_ema
```

关键事实：
- DA 基线 = 0.1（`create_dopamine()` 设定）
- Hunger 通路 → fill < 1.0 时持续向 DA 神经元输入正电流
- DA 神经元有 `bc_current=0.1`，即使无其他输入也产生 ~0.09 的 baseline activation
- D2 自受体有抑制作用但不足以将 DA 压到 0
- **DA 的实际范围 ≈ [0.02, 0.30]**，始终 > 0

### 4.2 结构性问题：DA_ema 是学习速率旋钮，不是开关

```
LTP = η × E(t) × DA_ema
```

- DA_ema 只能将 LTP 缩放为原来的 0%~100%，不能将其关断（因为 DA_ema > 0）
- REAL-DA: DA_ema → 0.18 → 学习慢一些
- RANDOM-DA: DA_ema → 0.50 → 学习快 3 倍
- **两者在 40k 步内都饱和** — 真实 DA 只是"减速"了饱和，没有阻止它

### 4.3 反直觉现象：随机 DA 加速学习

这是关键发现：**真实 DA 通路实际上在抑制学习**（DA_ema ≈ 0.18），而随机均匀噪声（均值 0.5）产生了 3 倍更强的 LTP 驱动。

真实 DA 通路包含多个负反馈：
- D2 自受体 → 抑制 DA 神经元
- Satiety → DA（抑制性输入）
- Energy fill 上升 → hunger 下降 → DA 下降

这些机制让 DA 保持在较低水平，客观上**减慢了**学习，但无法**阻止**学习。

### 4.4 时间尺度失配

| 组件 | τ | 功能 |
|------|-----|------|
| Eligibility trace E(t) | 500 steps | 记住 pre-post 共现 |
| DA_ema | **5000 steps** | 平滑 DA 信号 |
| 行为周期 | 20000 steps | ON/OFF 热源交替 |

DA_ema 比 eligibility trace 慢 10 倍，无法将具体行为与具体奖励时刻联系起来。

## 5. 结论

**DA-gating 证实为诈胡**，原因不是 DA_ema 把所有信号平滑到相同常数（这是原假说，已证伪），而是：

1. **DA 从不归零** — LTP gate 永远部分开启，只有速率差异
2. **无基线减法** — LTP ∝ DA_ema，而非 LTP ∝ (DA_ema − baseline)
3. **时间尺度失配** — DA_ema (τ=5000) 太慢，无法进行时间信用分配
4. **权重单调增长** — 无有效 LTD 机制对抗 LTP，饱和不可避免

## 6. 建议修复方向

1. **基线减法**: `LTP = η × E × max(0, DA_ema − DA_baseline)`，使 DA 在基线时 LTP = 0
2. **缩短 DA_ema τ**: 从 5000 降至 200-500，匹配 eligibility trace 时间尺度
3. **或使用 dDA/dt**: 用 DA 变化率（RPE），而非绝对值，门控学习
4. **增强 LTD**: 当 DA < baseline 时，LTD 应占主导
