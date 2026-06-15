# Walkthrough: S-level 修复 + RULE S2 递归分化沉积

## 完成的工作

### Phase 1: 信号链修复 (S-level)

修复了 6 层信号链中的增益瓶颈：

| 问题 | 根因 | 修复 | 文件 |
|------|------|------|------|
| Motor 不 spike | v_th=0.3 > v_peak=0.2 | 显式 channel v_th=0.15 | [hebbian.py](file:///d:/cell-cc/nexus_v1/circuit/hebbian.py) |
| Motor V_m 上不去 | τ=RC=5s 太慢 | C: 1.0→0.01 (τ=50ms) | [hebbian.py](file:///d:/cell-cc/nexus_v1/circuit/hebbian.py) |
| Motor 常态 spike | bc=0.07 >> v_th | bc: 0.07→0.025 | [hebbian.py](file:///d:/cell-cc/nexus_v1/circuit/hebbian.py) |
| Col→Motor 信号弱 | gain=0.1 | gain=5.0, weight=0.2 | [hebbian.py](file:///d:/cell-cc/nexus_v1/circuit/hebbian.py) |
| 囊泡池不够 | replenish < release | 0.1→0.3 | [neuron.py](file:///d:/cell-cc/nexus_v1/components/neuron.py) |
| DA 永远饱和 | Xin τ=50s | R: 50→0.5 + MOSFET clamp | [variant_adapter.py](file:///d:/cell-cc/nexus_v1/circuit/variant_adapter.py) |

### Phase 2: 对称性打破

| 问题 | 修复 | 效果 |
|------|------|------|
| STDP 不学习 (<0.3%) | 初始权重确定性扰动 ±25% | 权重变化达 24.3% |
| Motor 无分化 | 同上 + rate homeostasis | 分化达 26.5%/32.9%/40.6% |

### Phase 3: RULE S2 — 递归分化沉积

实现了两个结构生长操作：

**Bundle 萌芽 (Sprouting)**:
- 触发: |ξ| > 0.3 (Capacitor 积分器电压)
- 方式: 盲目复制父 bundle 拓扑, 最小权重 1e-4
- 选择: STDP (Memristor) 事后决定哪些存活
- 能量: 消耗源 neuron energy
- 文件: [bundle.py](file:///d:/cell-cc/nexus_v1/circuit/bundle.py) `sprout()`

**Bundle 修剪 (Pruning)**:
- 触发: mean_weight < 0.005 持续 5000 步
- 方式: 移除 bundle, 能量部分返还
- 文件: [bundle.py](file:///d:/cell-cc/nexus_v1/circuit/bundle.py) `should_prune()`

**规则文件**: [RULES_STRUCTURAL_COMPUTATION.py](file:///d:/cell-cc/nexus_v1/RULES_STRUCTURAL_COMPUTATION.py)

## 测试结果

### 100k 步长跑 (100s 仿真)

```
Bundle 动态: 32 → 80 (48 sprouts, 0 pruned)
Motor 分化: move_x=32.9%, move_y=26.5%, move_z=40.6%
Motor 稳定: 2.9-4.5 Hz (homeostasis 有效)
Sprout 成长: 最早的 w 从 1e-4 → 0.001 (STDP 10× 强化)
Enc→Col 分化: 0.130 ~ 0.170 (30% 范围)
能量稳定: avg=0.896, min=0.001
```

### Governance 测试: ALL PASSED

## 已修改的文件

| 文件 | 修改 |
|------|------|
| [hebbian.py](file:///d:/cell-cc/nexus_v1/circuit/hebbian.py) | Motor 参数, S2 常量, 萌芽/修剪逻辑, rate homeostasis |
| [bundle.py](file:///d:/cell-cc/nexus_v1/circuit/bundle.py) | sprout(), should_prune(), 初始权重对称性打破 |
| [neuron.py](file:///d:/cell-cc/nexus_v1/components/neuron.py) | 囊泡池 replenish rate |
| [variant_adapter.py](file:///d:/cell-cc/nexus_v1/circuit/variant_adapter.py) | Xin clamp, leak 修复 |
| [RULES_STRUCTURAL_COMPUTATION.py](file:///d:/cell-cc/nexus_v1/RULES_STRUCTURAL_COMPUTATION.py) | RULE S2 定义 |

## 关键设计决策

1. **盲目萌芽** (非协方差引导) — 符合 RULE S0, 涌现 > 优化
2. **只守恒能量** (非权重) — 电导不是守恒量
3. **PowerRail 自然限制** (非人为权重等分) — 组件特性即约束
4. **Rate homeostasis** — 用 neuron firing_rate() 组件状态触发
