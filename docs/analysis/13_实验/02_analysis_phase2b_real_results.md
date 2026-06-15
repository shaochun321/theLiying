# Phase 2b-R 闭环实测结果分析

## 电路结构 (完整闭环 vs 之前的静态管道)

| 指标 | 之前 (Allen 静态) | 现在 (PracticeEngine 闭环) |
|------|------------------|---------------------------|
| 神经元 | 20 | **59** |
| 突触束 | 10 | **38** |
| 层 | 2 (encoding, column) | **8** (encoding, column, signal_entropy, cpg, motor, origin, vestibular, practice_cortex) |
| 前庭 | 无 | **有** (6轴信号真实变化) |
| 闭环 | 无 (纯数据灌入) | **有** (motor → 力场 → 粒子 → 感知 → circuit) |

---

## 关键发现 1: P 环流是 CPG 的硬编码振荡

```
固化模式的 bundle_path = ['cpg_fast_a_to_b', 'cpg_fast_b_to_a']

这是 CPG 层的往复抑制振荡, learning_rule = "frozen"
它是预先布线的, 不是学出来的
100% 存在 ← 因为它是硬编码的

detect_circulations() 检测到的 P 环流 = CPG 自振荡
不是感觉运动回路的涌现环流
```

> [!IMPORTANT]
> **系统目前没有产生真正的感觉运动环流。**
> 被检测到的"环流"是 CPG 层的硬编码往复抑制，不是从输入到输出的闭环自维持模式。

---

## 关键发现 2: Xin 仍然主导，但守恒大幅改善

```
              之前 (静态)          现在 (闭环)
xin 占比:     97.8%               95.4%
守恒误差:     13.566/tick         0.296/tick    ← 大幅改善!
净 Xin 增长:  664.75 (120 tick)   61.58 (200 tick) ← 增长慢了17倍
total_sources: 0.86               33.46   ← 有来源了
total_absorbed: 665.6             30.72   ← 有吸收了

但 fruit_consumed 仍然 = 0 (果实仍未激活)
```

改善原因：闭环模式下，sensory 信号**真的在变化**（不是单调递增），所以 predicted - actual 的方向不再恒定。

---

## 关键发现 3: 前庭层信号真实但近乎死亡

```
前庭 6 轴信号在真实变化:
  tick  20: yaw=+0.004  pitch=-0.010  roll=-0.007
  tick  60: yaw=+0.008  pitch=+0.008  roll=+0.021
  tick 120: yaw=-0.011  pitch=-0.001  roll=-0.017
  
  信号幅度 ≈ 0.001-0.021 (非常微弱)
  符号在翻转 (有方向性分化)

但 vestibular 层神经元:
  mean activation = 0.0014
  active = 3/10 
  → 信号太弱, 无法驱动下游
```

---

## 关键发现 4: 各层活性分析

```
signal_entropy:  mean=0.169  active=6/7   ← 最活跃 (外部驱动)
encoding:        mean=0.020  active=10/23 ← 有响应
cpg:             mean=0.035  active=4/4   ← 自振荡存活
vestibular:      mean=0.001  active=3/10  ← 接近死亡
origin:          mean=0.002  active=3/5   ← 接近死亡
motor:           mean=0.001  active=0/3   ← 死亡
column:          mean=0.000  active=0/9   ← 死亡
```

### 信号流瓶颈诊断

```
信号路径:
  力场 → 粒子 → sensory → signal_entropy (OK, 0.169)
                ↓
          vestibular_system 6轴 (OK, 信号在变)
                ↓
          vestibular 层神经元 (DEAD, 0.001)
                ↓
          encoding (WEAK, 0.020)
                ↓
          column (DEAD, 0.000)
                ↓
          motor (DEAD, 0.001)

瓶颈在两处:
  1. vestibular 层: 6轴信号 ≈ 0.01 → neuron activation ≈ 0.001
     原因: sensory.get("lever_acoustic") / box → 被 box_size=10 除小了
     
  2. encoding → column: column 层 0/9 活跃
     原因: encoding 信号太弱(0.020), 无法超过 column 阈值
     
  3. motor 层死亡 → 没有自主运动 → 闭环断裂
     仅靠 CPG + babbling 在驱动粒子
```

---

## 根本诊断

```
问题不是"没有环流", 而是:

1. 检测到的环流是 CPG 自振荡 (硬编码), 不是涌现的
2. 信号太弱, 无法穿透 vestibular → encoding → column → motor 链
3. motor 层死亡 → 闭环断裂 → 没有自主运动 → 没有真正的运动状态可分离
4. 前庭传感器工作正常但数值被标准化压缩到 < 0.01

修复方向:
  A. 增益修复: vestibular 信号的注入增益太低
     lever/box ≈ 0.8, 但 tanh(dlever*10) 的输入 dlever ≈ 0.001 → tanh(0.01) ≈ 0.01
     需要: 提高增益或降低阈值
     
  B. motor 层不应该死亡: 它有 energy=1000, 但 activation=0.001
     检查: motor 的输入来源 (encoding_to_motor 权重 = 0.01 初始, 太弱)
     
  C. column 层需要更低的阈值或更强的 encoding 驱动
```
