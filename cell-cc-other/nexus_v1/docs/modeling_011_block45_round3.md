# 建模分析 011 — Block 4/5 Round 3 + FIX-009/010/011

> **日期**: 2026-05-22
> **阶段**: dt Bug 修复 + 全链重校准

## FIX-009: dt 未传播 (严重 Bug)

**问题**: `bundle.apply_to_targets(currents)` 中 `tgt.step(current)` 
没传 dt → dt 默认 1.0 而非 0.001 → 所有下游层时间常数错 1000x。

**影响**: Enc/Col/Motor 的 inject 和 leak 都是 1000x → 行为异常但部分抵消。

**修复文件**: 
- `circuit/bundle.py` — apply_to_targets 加 dt 参数
- `circuit/hebbian.py` — 所有调用传 dt

**效果**:
- Motor silence: 124 → 0 噪声脉冲 ✓
- Motor energy: 0.001 → 1.0 ✓
- 热耗散: 567 → 18 (-97%) ✓

## FIX-010: AGC 移除

**问题**: dt 修复后 AGC×5 使 scaled_current=50 → PowerRail v_ratio=0 → 阻断。

**修复**: 移除 Enc/Col AGC，调整 synapse_gain。

## FIX-011: Aff VR + HC→Aff gain 重校准

**问题**: 
1. Aff 没有 VR → energy 耗尽
2. HC→Aff gain=80 太大（release 从 0.015 → 0.48）
3. VR compute_recovery 对 spiking 应用 EMA

**修复**:
- Aff VR 加入 + VR 改用 _activation_ema
- HC→Aff gain: 80 → 20
- Ca_R: 500 → 6 (active zone clearance)
- ca_release_gm: 0.07 → 0.20

## 当前契约状态

| 契约 | 状态 | 值 |
|------|------|-----|
| C1 MET range | PASS | [1.98, 4.85] |
| C1 MET energy | PASS | 1.0 |
| C2 HC range | PASS | [0.011, 0.483] |
| C2 HC DR | PASS | 43.6:1 |
| C2 HC energy | PASS | 0.921 |
| C3 Aff freq | **PASS** | **41.1 Hz** |
| C3 Aff CV | FAIL | 0.471 |
| C4 Enc energy | FAIL | 0.001 |
| C6 Motor signal | FAIL | 0 |

**Signal depth**: 4/6 (Enc/Col 太弱)

## 下一步

Enc activation=0.0014 在 5000 步后。需要等 30k 步结果确认是否
是充电时间问题还是增益根本不够。
