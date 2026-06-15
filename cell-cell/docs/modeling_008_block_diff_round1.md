# 建模分析 008 — Block 分化后契约验证

> **日期**: 2026-05-22
> **阶段**: Block 1/2/3 修复后

## 变更

| Block | 修改 | 目标 DEG |
|-------|------|---------|
| 1. HC Ca²⁺ | i_ca = g (gate activation, 非 driving force) | DEG-004 |
| 2. Col VR | 保持 (已在 FIX-006 修复) | DEG-002 |
| 3. MET/HC VR | 加 VoltageRegulator | DEG-011, DEG-012 |

## 契约验证结果对比

| 契约 | 之前 | 之后 | 改善 |
|------|------|------|------|
| C1 MET energy | 0.001 FAIL | **1.000 PASS** | VR 修复 |
| C2 HC dynamic_range | 1.2:1 FAIL | **101.6:1 PASS** | Ca 修复! |
| C2 HC energy | 0.001 FAIL | **0.921 PASS** | VR 修复 |
| C2 HC output_range | [0.014, 0.016] OK | **[0.315, 32.0] FAIL** | 过大! |
| C3 Aff frequency | 12.6 Hz FAIL | **0.0 Hz FAIL** | 退化! |
| C5 Col energy | 0.001 FAIL | **1.000 PASS** | VR 修复 |

## 新问题

**PASS 增加**: 6 → 9 (+3)
**FAIL 减少**: 9 → 6 (-3)

但出现了**新退化**:

1. **C2 HC release 范围 [0.315, 32.0] 超出契约 [0.001, 0.5]**
   - Ca²⁺ 修复后 Ca 积累太快 → release_rate 爆到 32
   - 需要调整 ca_release_gm 或 Ca 衰减参数

2. **C3 Aff frequency 从 12.6 Hz → 0 Hz**
   - release_rate 太大 → HC→Aff 电流过强 → Aff 膜电压爆炸 → 可能卡在 v_peak
   - 或者 release_rate 信号性质改变导致 propagation 失效

## 分析

Ca 修复方向正确（动态范围从 1.2:1 → 101.6:1），但幅度失控。
需要在 Ca 路径上增加增益控制或调低 ca_release_gm。
