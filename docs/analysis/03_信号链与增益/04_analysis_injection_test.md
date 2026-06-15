# 赫布超图结构审计：运动-环流闭环

## 一、当前拓扑

### Motor 层完整连接图

```
Motor 输入 (5条束):
  transition,drift,gamma_desync → motor   w=0.01 (STDP) — 编码→运动
  integ_acoustic/thermal/luminous → motor w=0.08 (STDP) — 积分器→运动
  grad_acoustic/thermal/luminous → motor  w=0.05 (STDP) — 梯度→运动
  cpg_fast_a/fast_b → motor               w=0.15 (NONE) — CPG→运动 (固定!)
  proprio_spindle/golgi → motor            w=0.02 (STDP) — 本体感觉→运动

Motor 输出 (2条束):
  motor → transition, magnitude            w=0.10 (STDP) — 运动→编码 ✅
  motor → origin_x/y/z                    w=0.10 (STDP) — 运动→原点
```

### 闭环路径

```
motor → transition/magnitude (motor_to_enc, w=0.10, STDP)
              ↓
       transition (encoding 层的中枢节点)
              ↓
       enc_to_motor (w=0.01→0.76 after 2000t, STDP)
              ↓
       motor
```

> [!IMPORTANT]
> **闭环已经存在！** motor_to_enc + enc_to_motor 构成了一个双向 STDP 闭环。
> 但第三跳 (到 column) 后没有返回路径——column 是单向的。

---

## 二、2000 tick 后的权重演化

| 束 | 初始 | 终态 | 方向 | 含义 |
|----|------|------|------|------|
| **transition→move_x** | 0.01 | **0.76** | ↑↑↑ | 编码层学会了驱动运动 |
| **grad→move_x** | 0.05 | **0.81** | ↑↑↑ | 梯度信号学会了驱动运动 |
| cpg_fast→visc_rhythm | 0.10 | 0.17 | ↑ | CPG→内脏耦合增强 |
| visc→transition | 0.05 | 0.67 | ↑↑ | 内脏节律进入编码 |
| fano_H→transition | 0.12 | 1.00 | ↑↑↑ | 信号统计进入编码 (架构偏好) |
| motor→transition | 0.10 | **0.10** | — | **未变化!** |
| integ→move_x | 0.08 | 0.04 | ↓ | 积分器→运动被修剪 |
| proprio→move_x | 0.02 | 0.001 | ↓↓ | 本体感觉→运动被修剪 |
| proprio→churn | 0.03 | 0.001 | ↓↓ | 本体感觉→环流被修剪 |

---

## 三、关键观察

### 3.1 motor_to_enc 没有增长

**motor→transition 束的权重停留在 0.10。** 这是最重要的发现。

STDP 要求 pre(motor) 先于 post(transition) 激活。
但 transition 的激活来自 fano_H(1.0)、synchrony_H(1.0)、visc_rhythm(0.67)——
这些信号的强度远大于 motor(0.03) 对 transition 的贡献。

所以 transition 的激活**不依赖于 motor 的 pre_trace**，
STDP 检测不到 motor→transition 的因果关系。

### 3.2 proprio 被完全修剪

本体感觉(proprio_spindle_Ia, proprio_golgi)→motor 和 →encoding 都被修剪到 0.001。

STDP 的判决：**本体感觉与运动之间没有因果关系。**

这是因为本体感觉信号（disp×10, motor_mag/3）来自**物理引擎的运动结果**，
而 motor 层的激活来自**赫布回路的 CPG**——两者有时间延迟但没有因果。
物理 CPG 的运动结果不经过赫布回路的 motor 层。

### 3.3 integ→motor 减半

integrator→motor 从 0.08 降到 0.04。
integrator 是"某方向 received 信号的时间积分"——
它与 motor 之间的因果关系是弱的。

### 3.4 唯一强化的返回路径

能从外部信号到达 motor 的路径中，STDP 强化了两条：
- **grad→motor: 0.05→0.81** — 梯度方向→运动
- **transition→motor: 0.01→0.76** — 环流节点→运动

transition→motor 的增长(0.01→0.76)意味着：
**编码层的环流节点已经学会了驱动运动。**
这正是你说的"加力到肌肉的结构"——它已经存在于赫布超图中。

---

## 四、超图能否自组织出闭环？

### 已有的半环

```
梯度/环流 → motor (已学到, w=0.76-0.81)
                ↓
         motor 输出 (circuit_motor)
                ↓
         物理引擎 motor_final (但被物理CPG淹没)
                ↓
         粒子运动 → observer 位移 → received 变化 → gradient 变化
                ↓
         梯度信号 → 赫布回路 → encoding → transition
```

### 断裂点

```
motor → transition 束 (w=0.10, 未增长)
```

这是返回路径。STDP 没有增长它，因为
**motor 的 pre_trace 不与 transition 的激活有因果**——
transition 被 fano_H(1.0) 和 synchrony_H(1.0) 主导。

### 超图需要什么才能自组织闭环？

**条件 1**: motor 输出必须能改变 transition 的激活
  → 需要 motor_to_enc 的信号能**竞争过** fano_H/synchrony_H
  → 当前不可能 (0.10 vs 1.0)

**条件 2**: 或者 motor 需要一条更独特的返回路径
  → 不经过 transition（已被占满），而是到 encoding 的其他节点
  → 当前 motor_to_enc 只连 transition 和 magnitude

**条件 3**: 或者 motor 通过**物理反馈**间接影响 encoding
  → motor→粒子运动→received变化→gradient→grad→motor/encoding
  → 当前这条链路存在但 motor 的贡献被物理 CPG 淹没

### 结论

> **赫布超图有半个闭环的基础设施（编码→运动），
> 但返回路径（运动→编码）被信号饱和阻塞了。**
> 
> 不需要新层。需要的是：
> 1. motor_to_enc 的目标不应是已饱和的 transition
> 2. 或者 transition 需要一种机制不被 entropy 通道完全占据
> 3. 或者 motor 需要一条通过物理世界的间接反馈路径
> 
> 这三个方向都有可能让超图自己"长出"闭环。
> 具体哪个方向最可行，需要建模分析。
