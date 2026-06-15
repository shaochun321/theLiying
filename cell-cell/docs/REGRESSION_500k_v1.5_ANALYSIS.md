# 500k 回归分析 — v1.5.0 基线报告

> 数据版本: v1.5.0 | 步数: 500,000 | 耗时: 34.8 min
> 数据文件: [regression_500k_v1.5.json](file:///d:/cell-cc/nexus_v1/docs/regression_500k_v1.5.json)

---

## 1. 守恒验证: 完美通过 ✅

| 指标 | 结果 |
|---|---|
| Noether checks | 4999 checks, **0 violations** |
| Energy error | avg=0.000000, max=0.000000 |
| Q dissipated | 4.38 × 10⁹ |
| Landauer | 11.43 bits erased, Q/bit >> kT·ln(2) |
| Weight drift | avg 0.002/step (稳定收敛) |

> [!NOTE]
> 守恒框架在 500k 尺度上完全可靠。
> 所有基于守恒的数理推导（B1+B5 耦合、Landauer）可信。

---

## 2. 编码层分化: ⚠️ 时间退化

| 时期 | enc_stim (oto_x) | enc_quiet (therm) | 差异 |
|---|---|---|---|
| 0-50k | 0.67 | 0.00-0.25 | **大** ✅ |
| 50k-100k | 0.68 | 0.25-0.67 | **缩小** ⚠️ |
| 100k-200k | 0.67 | 0.62-0.67 | **消失** ❌ |
| 200k-350k (Phase 2) | 0.68 | 0.00-0.67 | **振荡** |
| 350k-500k (Phase 3) | 0.69 | 0.00-0.77 | **振荡** |

**根因**: 随着 sprouted bundles 增加（0→43 个），跨模态连接增多。
Therm 编码虽然没有直接前庭输入，但通过 sprouted bundle 接收到了活跃轴的溢出信号。
这不是 bias 问题（已修复），而是**结构生长导致的选择性丧失**。

> [!WARNING]
> Fruit sprouting 无方向选择性——新 bundle 连接任意两个活跃神经元，
> 不区分"这是有意义的共激活"还是"这是噪声溢出"。
> 长期运行后，sprouted bundles 建立了"信号走廊"，让无信号轴也被激活。

---

## 3. 权重演化: 拓扑优势被侵蚀

```
Phase 1 初始 (10k):
  axis-specific:  0.42  (从 0.30 快速上升)
  cross-axis:     0.12  (从 0.05 缓慢上升)
  优势比:         3.5:1

Phase 1 末 (200k):
  axis-specific:  0.426
  cross-axis:     0.270
  优势比:         1.6:1  ← 优势被削弱!

Phase 3 末 (500k):
  axis-specific:  0.424 (yaw), 0.423 (pitch), 0.436 (roll)
  cross-axis:     0.251
  优势比:         1.7:1

Phase 3 中 roll 权重升高 (0.426→0.437):
  因为只有 oto_x 输入 → body 运动 → 全轴加速度 → roll 编码活跃
  → col_roll_to_move_z 获得更多 STDP 增强
```

> [!IMPORTANT]
> 拓扑优势从初始 3.5:1 退化到 1.6:1。
> STDP 不加区分地增强所有活跃连接——包括由信号泄漏导致的跨轴连接。
> 需要**竞争/抑制机制**来维持拓扑选择性。

---

## 4. 运动分化: 弱但稳定

Motor ema 全程 0.66-0.68，三轴差异 <1%。
**相位切换时无可观测的运动响应变化。**

这意味着：
1. 运动输出被编码层的均匀化掩盖
2. Col→Mot 拓扑优势虽存在，但被 cross-axis 稀释
3. 系统处于"饱和运动"状态——所有 motor 都在持续发射

---

## 5. 结构生长

| 时期 | Sprouted bundles |
|---|---|
| 0-50k | 0 → 15 |
| 50k-150k | 15 → 43 |
| 150k-500k | 43（稳定）|

43 个 sprouted bundles 在 150k 后饱和。
这与 fruit maturation cycle (5000 ticks) 一致：150k / 5000 = 30 个周期足够填满。

---

## 6. 热源生态 ✅

| 指标 | 值 |
|---|---|
| Sources depleted | 16 |
| Sources spawned | 18 |
| Total consumed | 612.18 |
| Currently alive | 5 |
| Total remaining energy | 205.45 |

生态系统健康运转——源被消耗、死亡、新源出生。漂移功能正常。

---

## 7. 结论与下一步

### 可信的
- ✅ 守恒框架 (Noether, KCL, Landauer)
- ✅ B-layer 阻抗匹配 (正常工作)
- ✅ 热源生态
- ✅ 结构生长 (果实萌芽)

### 需要修复的（按优先级）
1. **选择性丧失** — sprouted bundles 需要方向选择性或竞争修剪
2. **运动饱和** — motor ema ~0.67 无论输入如何，缺乏安静基线
3. **跨轴泄漏** — cross-axis 权重追赶 axis-specific，拓扑优势丧失

### 需要重新验证的数理
- TSI 参数方程 → 需在修复选择性后重新拟合
- 影子层分化报告 → 可能受同样的泄漏影响
