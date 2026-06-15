# 建模分析 012 — 变体架构 Phase 1-2

> **日期**: 2026-05-22
> **阶段**: 变体元件构建 + 集成

## Phase 1: 独立构建 (零风险)

### 新增元件清单

| 元件 | 文件 | 电子对应 | 生物对应 | 测试 |
|------|------|---------|---------|------|
| ResonantOscillator | oscillator.py | Van der Pol / LC tank | CPG / θ-γ | 5/5 |
| NDRElement | ndr.py | 隧道二极管 / Chua | Na⁺ 失活 | 7/7 |
| MagnetofluidDamper | damper.py | MR 流体阻尼器 | 髓鞘 / ECM | 5/5 |
| LiquidMetalRouter | router.py | EGaIn 微流控 | 轴突导航 | 6/6 |
| Neuromodulator | modulator.py | DAC / PGA | DA / 5-HT / ACh | 7/7 |

**独立验证: 30/30 PASS, 母本完整性确认。**

## Phase 2: 适配器集成

### 策略: 增益调制 (非直接注入)

```
失败的策略:
  1. 直接注入膜电流 → 热耗散爆炸 (471)
  2. 半波整流注入 → 能量失衡
  3. 大幅度调制 (±35%) → 产生额外 spike, CV 恶化

成功的策略:
  4. 增益调制 ±15%: 振荡器调制膜电压偏差
     → CV: 0.471 → 0.454 (-3.6%)
     → Motor: 36 → 39 (+8.3%)
     → 热: 24.64 → 24.01 (不爆炸)
```

### 关键洞察

直接注入膜电流在 spiking 系统中是**有害的** —— 它添加了非周期
的能量，破坏了 ISI 的时间结构。正确的做法是**调制增益**，让
振荡器通过放大/缩小已有的突触电流来影响 spike 时机。

这与生物学一致: **传出拷贝 (efference copy)** 不直接驱动感觉
神经元放电，而是调节突触效能。

### 验证门控

| Gate | 状态 | 值 |
|------|------|-----|
| G1 母本不退化 | PASS | depth=6, spk=144 |
| G2 变体≥母本 | PASS | mot 39≥36 |
| G3 深度≥6 | PASS | 6/6 |
| G4 无新能量耗尽 | PASS | min 0.001≥0.001 |
| G5 热不爆炸 | PASS | 24.01 < 100 |

## Git 安全网

```
6077050  BASELINE (13/15, depth 6/6)
658ad54  PHASE1: 5 components, 30/30 tests
27fe849  PHASE2: VariantCircuit, 5/5 gates   ← 当前
```

## 下一步

CV 只改善了 3.6%（0.471→0.454），距离契约 ≤0.2 还有很大差距。
需要分析 CV 的根因 — 可能不是缺少振荡器的问题，而是 Ca ramp-up
暂态主导了 ISI 变异。需要分析稳态 vs 暂态 CV。
