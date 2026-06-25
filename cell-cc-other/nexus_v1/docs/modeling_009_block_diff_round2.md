# 建模分析 009 — Block 分化 Round 2 (Ca 修复 + VR 扩展)

> **日期**: 2026-05-22
> **阶段**: C2 Ca²⁺ 修复 + C1/C2 VR + ca_release_gm 调校

## 修改汇总

| Block | 修改 | 文件 | 推导 |
|-------|------|------|------|
| 1a | i_ca = g (gate activation) | neuron.py L278 | 归一化坐标系下 E_Ca 反转 |
| 1b | ca_release_gm: 5.0 → 0.07 | chain.py | gm = 0.5/(Ca_ss - 0.01) |
| 3 | MET/HC 加 VR | chain.py | DEG-011/012 |

## 关键指标对比

| 指标 | 之前(无Ca修复) | Round 1(Ca修复) | Round 2(+gm修正) |
|------|----------------|-----------------|-------------------|
| HC release range | [0.014, 0.016] | [0.315, 32.0] | **[0.004, 0.448]** |
| HC dynamic range | 1.2:1 | 101:1 | **101:1** |
| Aff frequency | 12.6 Hz | 0 Hz | **24.3 Hz** |
| Aff spikes | 44 | — | **85** |
| MET energy | 0.001 | 0.001 | **6.0** |
| HC energy | 0.001 | 0.921 | **5.9** |
| Col energy | 0.001 | 1.0 | **6.0** |
| Total heat | 1180 | — | **567** (52% reduction) |
| Signal depth | 6/6 | 6/6 | **6/6** |

## 契约验证结果

```
PASS: 10/15 (+4 from round 1)
FAIL: 5/15  (-3 from round 1)
Critical: 4 (-4 from start)

进展: 8 critical → 5 critical → 4 critical
```

## 剩余违约

| 契约 | 实测 | 目标 | 分析 |
|------|------|------|------|
| C3 Aff CV | 0.509 | ≤ 0.2 | Ca ramp-up 造成 ISI 不规则 |
| C6 Motor silence | 124 pre-signal | 0 | Enc/Col bias 传到 Motor |
| C6 Motor signal | 0 post-signal | >0 | Col→Motor 增益不足 |
| C6 Motor energy | 0.001 | >0.1 | 仍然耗尽 |

## HC release 动态验证

```
t=1500: release=0.004  (刚开始)
t=2000: release=0.035  (上升中)
t=2500: release=0.085  (继续上升)
t=3000: release=0.148  (加速)
t=3500: release=0.218  
t=4000: release=0.292
t=4500: release=0.369
t=4999: release=0.448  (接近稳态)
```

**Ca 动态响应恢复** — release 不再是常数，而是随时间逐渐上升
（反映了 Ca²⁺ 的缓慢积累，tau_Ca=100ms）。
