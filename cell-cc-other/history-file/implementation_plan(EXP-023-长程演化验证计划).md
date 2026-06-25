# EXP-023: 长程演化验证计划

> 触发: /goal 长程演化验证  
> 时间: 2026-06-21  
> 前置: 战役四补全 (e8ad17e) + 代谢壁修复 (45780da)

---

## 背景

两项关键修复已完成：
1. **战役四**: vestibular Col→Mot 轴束 stdp_lr 0.005→0.05, synapse_gain 5→10
2. **代谢壁**: 世界生态三联修复 (8源均匀分布 + E_HALF×10 + Body 起点修正)

EXP-023 目标：在修复后的生态中运行 500k 步，验证系统能否实现：
- 能量自持（fill 全程 > 0）
- 热趋性学习成熟（STDP 建立方向性权重）
- 行为涌现（运动趋近热源）
- 神经健康（DA、AGC、权重不退化）

---

## 验证阶段

### 阶段 0: 回归基线确认 (5 min)
- 运行 `pytest test_regression.py`
- 目标: 12/12 PASS
- 失败则停止，报告回归

### 阶段 1: 代谢稳定性验证 (10 min)
- 运行 5000 步代谢诊断
- 目标: P_net > 0, fill @5000步 > 0.49

### 阶段 2: 500k 步长程演化 (主体, 估计 2-4h)
- 新建 `exp_023_500k.py`，使用真实 8 源世界
- 每 10k 步记录: fill, DA, AGC, motor_ema, body_pos, dist_nearest_src, w_front, w_back
- 每 50k 步打印完整快照
- 运行时间预估: ~2-3 小时

### 阶段 3: 结果分析与判定 (30 min)
- 统计热趋性指标: Δx + dist_trajectory
- 统计能量指标: fill_min, fill_mean, P_net_mean
- 统计学习指标: Δw_max (权重分化)
- 对比 EXP-022 基线

---

## 通过标准

| 编号 | 标准 | 目标值 | 备注 |
|------|------|--------|------|
| C1 | fill 全程 > 0 | fill_min > 0 | 代谢壁修复成效 |
| C2 | fill @500k > 0.3 | fill > 0.3 | 长期可持续 |
| C3 | 回归 12/12 PASS | 全通 | 基线不退化 |
| C4 | DA 浓度健康 | DA_mean ∈ [0.05, 0.8] | 神经调节正常 |
| C5 | 权重出现分化 | max(Δw) > 0.05 | STDP 有效 |
| C6 | 行为不退化 | AGC_peak > 1.0 | 内稳态干预正常 |
| C7 | 运动持续存在 | motor_ema_mean > 0.01 | 生物体活着 |

---

## 关键监控信号

```
热趋性: body.position vs nearest_src.position → dist 变化趋势
能量:   energy_store.fill_fraction + P_in/P_out 分解
学习:   bundles_col_to_motor 权重 + shadow 权重演化
神经:   DA 浓度 + AGC gain + VitalOscillator amplitude
```

---

## 执行记录 (实时填写)

- [ ] 阶段 0: 回归基线
- [ ] 阶段 1: 代谢稳定性
- [ ] 阶段 2: 500k 长程运行
- [ ] 阶段 3: 结果分析
- [ ] 最终结论
