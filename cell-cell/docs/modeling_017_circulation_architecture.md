# Shadow Layer Feedback Design — Modeling Doc 018

> 日期: 2026-05-23
> 状态: DESIGN（待数学建模验证后才可落地）
> 依赖: modeling_016, modeling_017

## 设计意图

将影子层从"纯观察者"升级为"弱反馈源"：
- 运动势 ν = dK/dt → 调制运动层兴奋性
- 跨轴同步性 → 调制 STDP 学习门控

## ⚠️ 安全约束（用户要求）

> "影子层的反馈源先由外部管线来链接，由数学建模分析来测试，
>  免得造成严重的侵蚀后果。"

**Phase 2 不直接修改 variant_adapter.py 或 hebbian.py。**

实施方式：
1. 先写独立的数学建模脚本（scratch/shadow_feedback_sim.py）
2. 模拟 ν 反馈对运动层的影响，扫描耦合增益
3. 确认安全区间后，再将结果写入 RULES.md 的参数范围
4. 最后才修改代码（需用户再次确认）

## 反馈机制

### A: 运动势 ν → 运动阈值

```
影子层:
  K = Σ(xin²)          自由能核
  K_ema = EMA(K, α=0.01)  平滑
  ν = dK_ema/dt         运动势

反馈（外部管线）:
  ν → EMA(ν, α=0.05) → ν_smooth
  Δ_threshold = -ν_smooth × coupling_gain
  effective_threshold = base_threshold + Δ_threshold
```

| coupling_gain | 效果 | 风险 |
|--------------|------|------|
| 0.001 | 几乎无效 | 无 |
| 0.01 | 微弱调制 | 低 |
| 0.1 | 明显调制 | 中（可能振荡） |
| 1.0 | 强耦合 | 高（可能不稳定）|

**建议从 0.01 起步，数学模拟验证。**

### B: 同步性 → 学习门控

```
同步性指标:
  sync = Σ(cross_axis_weight × source_activation)
  归一化: sync_norm = sync / max_possible_sync

学习门控（外部管线）:
  gate_sync = min(1.0, sync_norm / sync_threshold)
  combined_gate = ecm_gate × gate_sync
```

## 数学建模计划

### 实验 1: ν 反馈稳定性

```python
# shadow_feedback_sim.py
# 模拟 50k 步
# 扫描 coupling_gain = [0.001, 0.01, 0.05, 0.1, 0.5]
# 测量:
#   - 运动层放电率变化
#   - 系统能量趋势
#   - 是否出现正反馈振荡
# 合格条件:
#   - 运动层放电率变化 < 20%
#   - 无正反馈振荡（ν 不持续增大）
#   - 能量趋势仍为 PASS
```

### 实验 2: 同步性门控效果

```python
# sync_gate_sim.py
# 模拟学习阶段 + 巩固阶段
# 比较有/无同步门控:
#   - 学习阶段权重变化率
#   - 巩固阶段权重扰动
# 合格条件:
#   - 学习保留 > 90%
#   - 巩固扰动减少 > 50%
```

## 生物学参考

| 机制 | 生物对应 | 耦合强度 |
|------|---------|---------|
| ν → 运动阈值 | 伏隔核多巴胺 → 运动皮层 | 弱（间接通过基底节） |
| 同步 → 学习门 | 小脑 CF 同步 → MLI2 去抑制 | 强但高度选择性 |
| DMN → 行为决策 | 默认网络 → 前额叶 → 运动 | 非常弱（多突触中继） |

## 落地条件

- [ ] 数学建模实验 1 通过
- [ ] 数学建模实验 2 通过
- [ ] 确定 coupling_gain 安全区间
- [ ] 用户确认参数范围
- [ ] 写入 RULES.md 参数约束
- [ ] 才开始修改 variant_adapter.py
