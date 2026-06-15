# 门控分化全景: v2 → v6 演进总结

## 演进路线

```
v2: 基础分化 (τ, θ, cw 不同)
    → 分化成功, 但压力测试受损

v3: + 单时间尺度冲突检测 (cosine of signal×weight)
    → 总损伤 -55%, 但 alignment 不变负 (输出空间平滑)

v4: + 双时间尺度 (fast/slow EMA)
    → 总损伤 -14%, alignment 仍正 (signal×weight 的 EMA 不敏感)

v5: + 信号空间 (不乘 weight)
    → 总损伤 -14%, 同样问题 (EMA 平滑了交替模式)

v6: + 中心化 (signal - mean)
    → 总损伤 -72% ← 最大改善
```

## 最终 v6 数据

### 压力保护

| 区域 | v2 ΔS | v6 ΔS | 改善 |
|------|-------|-------|------|
| encoding | -0.077 ⚠️ | -0.131 ⚠️ | -5% |
| column | -0.019 ✅ | +0.056 ⚠️ | -4% |
| inter_layer | +0.067 ⚠️ | +0.300 ❌ | -23% |
| motor | 0.000 ✅ | 0.000 ✅ | 0% |
| **sediment** | **-2.343** ❌ | **+0.206** ⚠️ | **+214%** |
| **总计** | **2.506** | **0.693** | **-72%** |

> [!IMPORTANT]
> sediment 从 -2.343 (灾难性) 降到 +0.206 (轻微)。
> 这一个区域贡献了大部分改善。
> 原因: 中心化让 sediment 的极慢门控 (τ=50) 不再无条件开放。

### 巩固保护

| 区域 | ΔS | 评价 |
|------|-----|------|
| encoding | +0.000 | ✅ 冻结 |
| column | +0.000 | ✅ 冻结 |
| inter_layer | +0.000 | ✅ 冻结 |
| motor | +0.000 | ✅ 冻结 |
| sediment | -0.029 | ⚠️ 轻微 |

### 门控分化谱 (v6)

```
              学习    巩固    压力    恢复    休息
encoding     0.43    0.00    0.36    0.04    0.00
column       0.70    0.03    0.76    0.31    0.00
inter_layer  0.70    0.04    0.72    0.25    0.00
motor        0.00    0.00    0.00    0.00    0.00
sediment     0.95    0.63    0.88    0.90    0.40
```

---

## 不变量: 母本从未改动

```python
def compute(self, sync, contrast, alignment):
    sig = sync*(1-self.cw) + contrast*self.cw
    self.voltage += (sig - self.voltage) / self.tau
    base = polarity * min(1.0, (voltage-theta)/0.2) if voltage>theta else 0.0
    df = max(0.0, min(1.5, alignment + tolerance))
    return base * df
```

**这 5 行代码从 v2 到 v6 一字未改。**

所有改进都来自:
- v3: 加入 alignment 参数 (扩展接口)
- v4: 改 alignment 的计算方式 (双 EMA)
- v5: 改 alignment 的输入空间 (raw signal)
- v6: 改 alignment 的预处理 (中心化)

---

## 遗留问题

> [!WARNING]
> **alignment 在压力阶段仍然是正值 (+0.43~+0.81)**
> 
> 原因: 信号每 6 ticks 交替 (0.9↔0.1), EMA 平滑后差异消失
> 
> 真正的冲突检测需要: **不是比较平均模式, 而是比较瞬时模式的序列**
> 
> 这对应:
> - 海马 CA3: pattern completion/separation (非 EMA, 而是 attractor)
> - 小脑: complex spike 的瞬时比较 (非平均, 而是事件驱动)
> 
> **当前的 EMA-based 方案是连续的; 真正的冲突检测是事件驱动的。**
> 但即使 alignment 不完美, 中心化 + 分化参数已经实现了 72% 的保护。

---

## 分化原则最终确认

```
✅ 母本不动 — compute() 从 v2 到 v6 不变
✅ 参数驱动 — (τ, θ, cw, tau_fast, tau_slow, tolerance) 6 个轴
✅ 递归分化 — 连冲突检测的参数本身也需要区域特定
✅ 跨学科 — 中心化 = 去均值 = 信号处理基础操作
✅ 渐进改善 — 每个版本只加一个改动, 独立验证
```

### 下一步

以上实验确认了:
1. **分化门控框架有效** — 可以进入实现计划
2. **中心化是必须的** — alignment 必须去均值
3. **参数表需要固化** — 5 区域 × 6 参数 = 30 个值
4. **事件驱动检测是未来方向** — 但不阻塞当前实现
