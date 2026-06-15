# 前神经系统为 HebbianCircuit 提供的 8 个架构指导

## 核心理解

```
前神经系统的价值不在于它的代码要被复用,
而在于它验证了 8 个架构模式,
这些模式应该在 HebbianCircuit 中以"类神经方式"重新实现。
```

---

## 模式 1: 多通道分解 (先分后合)

### 前神经怎么做
```python
# 每个原始事件被分解为 3 个独立通道:
channels = [
    ("bioelectric_proxy", V_mean, V_slope, ...),    # 电信号
    ("kinematic_flow",    speed, phase_vel, ...),     # 运动流
    ("phase_clock",       phase_vel, phase, ...),     # 相位时钟
]
# 3 个通道独立存在, 各有自己的 value/derivative/phase/uncertainty
# 后续通过 cross_modal_binding 用相位一致性绑定
```

### HebbianCircuit 应该学到什么
```
当前: _compute_sensory() 把所有信息压成 7 个标量
应该: 输入保持多通道分离 → 每个通道各自进入独立的元单元组
     → 在后续层通过环流(P/R)的相位一致性实现跨通道绑定
     → 不靠语义标签绑定, 靠结构性相位匹配

这就是"元单元分化"的输入端实现:
  快速型元单元 → 接收 kinematic_flow (变化快)
  慢速型元单元 → 接收 bioelectric_proxy (变化慢)
  时序型元单元 → 接收 phase_clock (周期性)
```

---

## 模式 2: 动态原点 (没有绝对坐标)

### 前神经怎么做
```python
# 每个 tick 计算能量加权质心作为原点:
x = sum(e["x"] * e["energy_proxy"] for e in events) / total_w
y = sum(e["y"] * e["energy_proxy"] for e in events) / total_w
# 所有坐标都是相对于这个动态原点的
# 原点本身也有速度和稳定性分数
```

### HebbianCircuit 应该学到什么
```
当前: 没有"原点"概念, 所有信号都是绝对值
应该: 每个 tick 的环流质心 = 动态参考点
     所有新输入相对于上一个环流质心来度量
     → 这就是"隐式坐标 = 延迟+衰减"的工程实现
     → 原点不是预设的, 是涌现的
```

---

## 模式 3: 数据驱动的分组 (k 由数据决定)

### 前神经怎么做
```python
# 不预设分几组, 用 silhouette score 自动选:
def choose_clusters(features, max_k=6):
    for k in range(2, max_k+1):
        assigns = kmeans(features, k)
        score = silhouette(features, assigns) - penalty
        if score > best_score:
            best_k = k
    return best_k
# 结果: 本次数据选了 k=6
```

### HebbianCircuit 应该学到什么
```
当前: 层结构、通道数、维度数全部硬编码
应该: 系统自己决定"分几组"
     → P/R 的数量不应该预设
     → 环流检测已经有类似机制 (找所有环路, 按流量排序)
     → 但需要加入"多少个环路是有意义的"的判定
     → silhouette 的等价物 = 每个环路的流量占比是否显著
```

---

## 模式 4: 四分数健康指标

### 前神经怎么做
```python
# 每条轨迹有 4 个独立的健康分数:
continuity_score     # 空间连续性 (相邻时间步质心变化是否平滑)
conservation_score   # 能量守恒 (能量标准差 / 能量均值)
phase_coherence      # 相位一致性 (成员节点的相位向量合成长度)
reconstruction_score # 重构质量 (簇内误差 / 全局误差)

# 然后有一个综合残余质量:
residual_mass = 1 - (0.35*cont + 0.25*cons + 0.25*phase + 0.15*recon)
```

### HebbianCircuit 应该学到什么
```
这 4 个分数就是 ρ 测度的原型!

前神经                    HebbianCircuit ρ 测度
──────                    ──────────────────
continuity_score      →   P core 占比 (稳定锚定)
conservation_score    →   P/R 竞争平衡度
phase_coherence       →   跨通道绑定强度
reconstruction_score  →   信息被解释的比例
residual_mass         →   Xin + unresolved 占比

关键: 前神经用浮点数计算这些分数。
     HebbianCircuit 应该用结构性比对 (环流基线)
     涌现出等价的度量。
```

---

## 模式 5: 残余即 Xin (不丢弃)

### 前神经怎么做
```python
# 绑定失败的事件不丢弃, 变成 Xin:
if not accepted or binding_weight < 0.50:
    reason = "weak_binding" if weight < 0.35 else "high_residual_bound"
    xin_candidates.append({
        "mass": 1.0 - binding_weight,
        "reason": reason,
        "continuity": ...,
        "conservation_violation": ...,
        "phase_conflict": ...,
    })

# Xin 有明确的去向政策:
if mass > 0.58:
    policy = "retain_as_unbound_residue_for_next_origin_probe"
else:
    policy = "decay_after_audit_unless_reobserved"
```

### HebbianCircuit 应该学到什么
```
当前: xin_tension 只是一个标量, 没有 reason, 没有 decay policy
应该:
  1. Xin 有 mass (不只是 tension)
  2. Xin 有 reason (为什么绑定失败: 连续性断裂? 守恒违反? 相位冲突?)
  3. Xin 有 policy (大残余保留做新原点探测, 小残余衰减除非被再次观察)
  4. 所有 Xin 流动记入外部账本 (RLIS)
```

---

## 模式 6: 屏蔽层 = 噪声扰动重跑

### 前神经怎么做
```python
# 给特征向量加高斯噪声, 重新聚类, 比较结果:
for level in [0.05, 0.10, 0.20, 0.30]:
    noisy = [x + gauss(0, level) for x in features]
    new_assigns = kmeans(noisy, k)
    stability = coassignment_similarity(base_assigns, new_assigns)
    # 如果 stability 高 → 分离是稳健的
    # 如果 stability 低 → 分离不可靠
```

### HebbianCircuit 应该学到什么
```
这就是固化验证的工程实现:
  1. 正常运行 → 得到环流模式 (P/R)
  2. 部分遮蔽输入 → 重新运行
  3. 比较: 环流模式是否保持不变?
     → 保持 → 固化通过 → 运动状态可以结晶
     → 不保持 → 固化失败 → 继续学习

HebbianCircuit 中的实现:
  → 不需要外部噪声注入
  → 可以用"能量下降"或"信号衰减"模拟遮蔽
  → calcium 下降时, 环流是否还在?
  → 这就是成熟阈值的验证标准
```

---

## 模式 7: 回投 = 反向验证

### 前神经怎么做
```python
# 用分离出的轨迹质心回投到源 3D 坐标:
# 计算误差: 轨迹质心 vs 全局质心
# 如果 trajectory_error < baseline_error → 分离有信息增量
improvement = (baseline_error - trajectory_error) / baseline_error
# 改善 > 10% 才算通过
```

### HebbianCircuit 应该学到什么
```
这就是"反向映射"的最小实现:
  正向: 底层信号 → 环流模式
  反向: 环流模式 → 预测底层信号的分布
  如果预测比"全局平均"好 → 环流模式捕获了真实结构

在 HebbianCircuit 中:
  → 已有雏形: xin_tension = predicted - actual
  → 但只用于单条管道, 没有全局比对
  → 需要: 用环流模式(P路径)预测"下一个tick各元单元的状态"
  → 如果 P 预测比"全局基线"好 → P 环流被确认
  → 这就是运动状态固化的判定标准
```

---

## 模式 8: 跨模态相位绑定

### 前神经怎么做
```python
# 不同通道的相位差决定绑定:
phase_gap = abs(wrap_angle_delta(phase_a, phase_b))
coherence = exp(-phase_gap)
accepted = coherence >= 0.12
# 相位一致 → 绑定; 相位不一致 → 不绑定
# 没有使用语义标签
```

### HebbianCircuit 应该学到什么
```
当前: HebbianCircuit 没有显式的相位概念
但实际上已有隐含相位:
  → 时空环流中各神经元的 activation 峰值时间 = 相位
  → _st_circ_history 已在记录 (L1468-1470)
  → 但没有用于绑定判定

应该:
  不同通道(分化后的元单元组)的环流
  通过 activation 峰值时序的对齐 来绑定
  → 峰值时序一致 → 同一运动事件
  → 峰值时序不一致 → 不同运动事件 / Xin
```

---

## 总结: 架构转译路线

```
前神经验证了什么                   HebbianCircuit 怎么实现
───────────────                   ──────────────────────
多通道分解                        → 元单元分化 (不同类型接收不同通道)
动态原点                          → 环流质心作为参考点
数据驱动分组                      → 环流数量由流量显著性决定
四分数健康                        → ρ 7分量从环流健康指标涌现
残余即 Xin                        → Xin 有 mass + reason + policy
屏蔽层验证                        → 衰减时环流保持 = 固化通过
回投反验                          → P 预测优于全局基线 = 确认
相位绑定                          → activation 峰值时序对齐 = 跨通道绑定

前神经用: 浮点数 + 外部算法 (kmeans, silhouette)
HebbianCircuit 用: 结构性环流 + 内部涌现

同一个思想, 不同的实现层级。
```
