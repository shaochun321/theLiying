# Walkthrough: 环流架构 + 影子层激活 + 参数进化

> 日期: 2026-05-23

## 完成的工作

### Phase 1: Bundle 环流角色分化

| 文件 | 改动 |
|------|------|
| [bundle.py](file:///d:/cell-cc/nexus_v1/circuit/bundle.py) | +`delay_steps` (轴突传导延迟) + `bundle_role` (feedforward/feedback/cross_axis/shadow) + FIFO 延迟缓冲区 |
| [hebbian.py](file:///d:/cell-cc/nexus_v1/circuit/hebbian.py) | 4 处 Bundle 标注 `feedforward` |
| [shadow_sandbox.py](file:///d:/cell-cc/nexus_v1/components/shadow_sandbox.py) | 3 处标注 `shadow`/`cross_axis` + 跨轴 `delay_steps=2` |

### Phase 3: 环流测量升级

| 文件 | 改动 |
|------|------|
| [circulation.py](file:///d:/cell-cc/nexus_v1/circuit/circulation.py) | `CirculationDetector` → `CirculationMeter` + `MIN_FLOW=1e-5` + `flow_history` + `p_frequency` + `flow_variance` |
| [variant_adapter.py](file:///d:/cell-cc/nexus_v1/circuit/variant_adapter.py) | 引用更新 |

### 影子层修复（4 个阻塞问题）

| # | 问题 | 根因 | 修复 | 文件 |
|---|------|------|------|------|
| 1 | 影子层神经元 act=0 | 能量耗尽 (I²R 热) | 施工供电 `_construction_power=True` | [shadow_sandbox.py](file:///d:/cell-cc/nexus_v1/components/shadow_sandbox.py) |
| 2 | 影子层 Xin=0 | `compute_xin()` 未被调用 | observe() 中加 Xin 计算 | [shadow_sandbox.py](file:///d:/cell-cc/nexus_v1/components/shadow_sandbox.py) |
| 3 | 跨轴权重不学习 | 非脉冲神经元 STDP trace=0 | `maturation_stage=1` → BCM (基于速率) | [shadow_sandbox.py](file:///d:/cell-cc/nexus_v1/components/shadow_sandbox.py) |
| 4 | 列层 v=0.13 不到阈值 | observe 频率太低 (τ/dt=1500) | 调用间隔 100→10 步 | [variant_adapter.py](file:///d:/cell-cc/nexus_v1/circuit/variant_adapter.py) |

### 参数进化搜索

脚本: [parameter_evolution.py](file:///L:/Users/%E7%BB%8D%E6%98%A5/.gemini/antigravity-ide/brain/b28b1552-1fcc-4344-b53a-904fd4f4bced/scratch/parameter_evolution.py)

---

## 关键发现

### 1. 非脉冲神经元不能用 STDP

```
STDP: dw ∝ pre_trace × post_trace
非脉冲: trace 只在 spike 事件时更新 → 永远为 0

BCM: dw ∝ pre_act × post_act × (post_act - θ)
非脉冲: 直接用 activation → 正常工作
```

设 `maturation_stage=1` 让 `bundle.learn()` 自动选择 BCM。

### 2. 影子层 observe 频率必须匹配 SHADOW_K

```
之前: variant_adapter 每 100 步调用 observe
SHADOW_K = 10, dt = 0.001 × 10 = 0.01
τ = R×C = 5×3 = 15
到达稳态: 1500 次更新 = 150,000 主步

修复后: 每 10 步调用
到达稳态: 1500 次更新 = 15,000 主步
```

### 3. 跨轴初始权重 0.001 是最优的

进化搜索结果：

| cross_w | 学习表现 | 原因 |
|---------|---------|------|
| 0.001~0.03 | **满分** (1.0) | BCM θ 低，任何正信号都增强 |
| 0.05 + gain=15 | **下降** (0.74) | BCM θ 高，部分路径被抑制 |

**BCM 的滑动阈值 θ 自动实现了"从弱生长"的设计意图——不需要人为设定。**

### 4. 影子层成功发现输入相关结构

```
跨轴权重排序（20k 步后）:
  yaw↔pitch:   0.0085  ← 输入最强的两轴
  yaw↔roll:    0.0074
  pitch↔roll:  0.0053
  ...
  oto_y↔oto_z: 0.0017  ← 输入最弱的两轴
```

**权重排序完美反映了输入信号的相关结构。**

---

## 测试验证

- ✅ 端到端导入测试通过
- ✅ 200 步运行无崩溃
- ✅ 20,000 步运行：影子层全链路激活
- ✅ 跨轴 BCM 学习正常
- ✅ 环流测量 60 条路径，P 频率 0.39
- ✅ 参数进化搜索 15 组完成

## 待续

- Phase 2: 影子层 ν 反馈到运动层（施工供电已就绪，可以测试）
- 适应度函数权重微调（noether=0.47 还有提升空间）
- `_construction_power` 最终需要关闭（验证完后）
