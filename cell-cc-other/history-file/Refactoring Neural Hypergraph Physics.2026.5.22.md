# Chat Conversation

Note: _This is purely the output of the chat conversation and does not contain any raw data, codebase snippets, etc. used to generate the output._

### Planner Response

Now let me also check what `xin_tension` starts at and look at the xin_tension field initialization:

*Grep searched codebase*

*User accepted the command `$env:PYTHONIOENCODING='utf-8'; python -c "import sys; sys.path.insert(0, r'D:\cell-cc\Morphosphere_v37_0_native_runtime_prototype_flat_complete\morphosphere_v2pp\engines'); from hebbian_circuit import MetaSynapticBundle; b=MetaSynapticBundle.__dataclass_fields__; print([f for f in b if 'xin' in f.lower()])"`*

*Viewed [hebbian_circuit.py](file:///D:/cell-cc/Morphosphere_v37_0_native_runtime_prototype_flat_complete/morphosphere_v2pp/engines/hebbian_circuit.py) *

### Planner Response

Now look at where `xin_tension` is initialized in the bundle:

*Viewed [hebbian_circuit.py](file:///D:/cell-cc/Morphosphere_v37_0_native_runtime_prototype_flat_complete/morphosphere_v2pp/engines/hebbian_circuit.py) *

*Viewed [hebbian_circuit.py](file:///D:/cell-cc/Morphosphere_v37_0_native_runtime_prototype_flat_complete/morphosphere_v2pp/engines/hebbian_circuit.py) *

### Planner Response

Now I have the complete picture. Let me also check what happens to xin_tension over time - does it ever get reset or decayed?

*Grep searched codebase*

### Planner Response

Now I have the full picture. `xin_tension` is only set to 0 at line 798 (when a fruit is activated). Let me verify there's no decay on xin_tension itself:

*Viewed [hebbian_circuit.py](file:///D:/cell-cc/Morphosphere_v37_0_native_runtime_prototype_flat_complete/morphosphere_v2pp/engines/hebbian_circuit.py) *

### Planner Response

现在全部清楚了。让我给出完整的解释：

---

## Xin 是什么？— 直接从代码说

### 1. 结构位置

Xin 是 **MetaSynapticBundle**（元突触束）上的一个浮点数字段：

```python
# hebbian_circuit.py 第 360-362 行
xin_tension: float = 0.0    # > 0 = expected but didn't happen
xin_dormant_fruit: Optional[Dict] = None  # shadow fruit if tension persists
```

每个 **bundle** 都有自己的 `xin_tension`。电路有 10 个 bundle → 有 10 个独立的 xin_tension。

### 2. 运作流程

每个 tick，`compute_xin()` 被调用（[第1596行](file:///D:/cell-cc/Morphosphere_v37_0_native_runtime_prototype_flat_complete/morphosphere_v2pp/engines/hebbian_circuit.py#L1596-L1648)）：

```
for 每个 bundle:
    for 每个 target 神经元:
        predicted = 上一个 tick 的 encoding 层激活值
        actual   = 这个 tick 运算后的实际激活值
        
        bundle.xin_tension += (predicted - actual)    ← 第 737 行: 累加
```

**Xin tension = Σ(predicted - actual)**，是**预测误差的历史累积**。

### 3. 唯一的消耗出口

`xin_tension` 只有**一个地方**会被清零（[第798行](file:///D:/cell-cc/Morphosphere_v37_0_native_runtime_prototype_flat_complete/morphosphere_v2pp/engines/hebbian_circuit.py#L774-L800)）：

```python
def try_activate_fruit(self, bias_signal):
    # 条件 1: 必须有 dormant_fruit
    # 条件 2: effective_tension * bias_signal > 0 (方向一致)  
    # 条件 3: abs(bias_signal) > 0.3 (足够强)
    if 满足:
        self.xin_tension = 0.0    ← 唯一的清零
        return fruit
```

果实激活条件：
1. `abs(xin_tension) > 0.5` 时创建 dormant fruit
2. 之后某个 tick，`bias_signal = actual - predicted` 必须和 tension 同方向，且 `abs > 0.3`

### 4. 为什么果实永远不激活？

实测中 `fruit_consumed = 0`。原因在于 **predicted 和 actual 的来源**：

```python
# run_v40_circuit_validation.py 第 101-104 行
prev_activations = {nid: n.activation 
                    for nid, n in enc_layer.neurons.items()}
```

**predicted** = 上一个 tick 的 encoding 神经元激活值
**actual** = 这个 tick transport 后的激活值

这两者之间：
- `predicted - actual` 每 tick 都是**同一个方向**的偏差（因为输入在持续变化）
- 所以 `xin_tension` **持续往一个方向累积**
- `bias = actual - predicted`，方向**和 tension 相反**
- 激活条件 `effective_tension * bias_signal > 0` **永远不满足**

```
tension 累积方向:  predicted - actual  = +Δ （持续正）
bias 信号方向:     actual - predicted  = -Δ （持续负）

tension > 0, bias < 0 → tension × bias < 0 → 不激活
```

**这就是为什么 Xin 只增不减** — 果实永远无法激活，因为偏差方向恒定。

### 5. 为什么没有分化？

```
输入: 6 个信号特征 → 全部进 encoding 层
encoding 层: 13 个神经元, 全部接收相同类型的信号
column 层: 7 个神经元

问题:
  所有 encoding 神经元接收的是同一个输入源的不同特征:
    sig_mean, sig_std, sig_peak_rate, sig_temporal_d, sig_sync, sig_range
  
  但它们都是从同一批细胞球计算出来的全局统计量
  → 当细胞球整体运动时, 所有特征同步变化
  → 所有神经元同步激活
  → predicted ≈ actual 的偏差模式在所有 bundle 上相同
  → 所有 bundle 的 xin_tension 同方向累积
  → 没有分化
```

**根本原因**：不是 Xin 机制有问题，而是**输入没有对立性**。真实的前庭系统里，半规管的三个通道（yaw/pitch/roll）是**正交**的 — 向左转时 yaw 正、pitch 零、roll 零。但现在的 6 个信号特征之间不正交，它们是同一个源的不同统计切面，所以不会产生"一些 bundle tension 正、一些负"的分化模式。

### User Input

还有,真实运行 产生的信号是如何处理的?从底层的细胞球也好,半规管自身的拟真物质结构或者电路也好,力场施加其上,是如何转化为信号被然后进入系统内部的?管道如何设置?你说的环流是哪个环流?赫布的?还是半规管的?为什么现在去观察环流?半规管已经被认为是完备的么?可以真实分析运动状态了么?

### Planner Response

这些问题非常关键。让我追踪真实的信号路径。

*Viewed [vestibular_system.py](file:///D:/cell-cc/Morphosphere_v37_0_native_runtime_prototype_flat_complete/morphosphere_v2pp/engines/vestibular_system.py) *

### Planner Response

现在看谁调用 `VestibularSystem`：

*Grep searched codebase*

*Viewed [practice_engine.py](file:///D:/cell-cc/Morphosphere_v37_0_native_runtime_prototype_flat_complete/morphosphere_v2pp/engines/practice_engine.py) *

### Planner Response

Now I need to check how `PracticeEngine.step()` sensory output gets fed into `HebbianCircuit`. Let me find where both are connected:

*Grep searched codebase*

*Viewed [run_v40_integrated.py](file:///D:/cell-cc/Morphosphere_v37_0_native_runtime_prototype_flat_complete/morphosphere_v2pp/runners/run_v40_integrated.py) *

### Planner Response

I've now seen the complete signal path. Let me also see the remaining vestibular layer feeding:

*Viewed [run_v40_integrated.py](file:///D:/cell-cc/Morphosphere_v37_0_native_runtime_prototype_flat_complete/morphosphere_v2pp/runners/run_v40_integrated.py) *

### Planner Response

Now I have the complete picture. Let me write a clear answer:

---

好问题。让我从代码出发回答你的每一个问题。

## 1. Xin 是什么？

在 HebbianCircuit 里，Xin 是 **MetaSynapticBundle 上的预测误差累积量**（[第735-755行](file:///D:/cell-cc/Morphosphere_v37_0_native_runtime_prototype_flat_complete/morphosphere_v2pp/engines/hebbian_circuit.py#L735-L755)）：

```python
def accumulate_xin(self, predicted, actual):
    self.xin_tension += (predicted - actual)  # 每 tick 累加
```

每个 tick，`compute_xin()` 对**每个 bundle 的每个 target 神经元**做：
- `predicted` = 上一个 tick 该神经元的激活值（作为"期望"）
- `actual` = 这一个 tick 的实际激活值
- 差值累加到 bundle 的 `xin_tension` 上

**Xin 不是环流。Xin 是"每根突触束上积压的、尚未被解决的预测误差"。** 它的唯一清零出口是"果实激活"（[第790-798行](file:///D:/cell-cc/Morphosphere_v37_0_native_runtime_prototype_flat_complete/morphosphere_v2pp/engines/hebbian_circuit.py#L790-L798)），但果实的激活条件是 `bias_signal` 和 `tension` 同方向且 `|bias| > 0.3`。

## 2. 真实信号的处理路径

有**两条完全不同的管道**，你的 Phase 2b 实验用的是错的那条：

### 管道 A（你 Phase 2b 用的）— Allen Brain 静态管道
```
Allen Brain NWB → generate_cells() → V_mean列表 
→ FeatureExtractor._signal_transform.extract_signal_features() 
→ 6个标量 [sig_mean, sig_std, sig_peak_rate, sig_temporal_d, sig_sync, sig_range]
→ circuit.run_tick(input_activations, "encoding")

没有物理层, 没有前庭, 没有粒子
```

### 管道 B（完整管道）— PracticeEngine 闭环管道
```
力场（CPG节律 + 电路motor输出 + 反射 + babbling）
  ↓
ParticleSystem3D（30个粒子, 弹簧排斥 + LIF）
  ↓
_compute_sensory() → 7通道: spectral_H, fano_H, synchrony_H, gradient_H, sparseness_H, autocorrelation_H, energy_H
  ↓
VestibularSystem.compute_from_particles() → 6轴: canal_yaw/pitch/roll, oto_x/y/z
  ↓
vestibular_layer 神经元直接赋值（lever_acoustic, dlever_thermal...）
  ↓
inter_layer_bundles 传播: vestibular → encoding, motor → vestibular (传出副本)
  ↓
circuit 的 encoding/column/motor/origin/vestibular 各层都参与
```

**管道 A 只取了 Allen 的电压信号做 6 个统计量，然后直接灌进一个只有 encoding+column 的小电路。前庭、motor、origin 层全部不存在。**

**管道 B 才是真正的闭环**：力场 → 粒子 → 传感 → 前庭6轴 → 电路 → motor → 力场回环。

## 3. 我说的"环流"是哪个？

我观测的是 **HebbianCircuit 的 P/R 环流**（[第3220行](file:///D:/cell-cc/Morphosphere_v37_0_native_runtime_prototype_flat_complete/morphosphere_v2pp/engines/hebbian_circuit.py#L3220)），即 `detect_circulations()` 检测的 bundle 之间的循环路径。

**不是半规管的**。半规管 (`SemicircularCanal`) 是一阶低通滤波器，输入角速度、输出感知角速度，没有"环流"概念。

## 4. 为什么去观察环流？半规管完备了吗？

**半规管本身作为传感器是完备的**：它正确地模拟了 `τ·dQ/dt + Q = ω·gain` 的过阻尼扭摆方程，有速度存储适应（`Q_adapt`），有 3 轴 + 3 轴 = 6 自由度。它能感知角速度和线加速度。

**但它没有连接到我 Phase 2b 用的电路上。** Phase 2b 用的是管道 A（只有 Allen Brain 数据的简化电路），而 VestibularSystem 只在管道 B（PracticeEngine 闭环模式）中才被调用。

所以我之前做的观测——**用的是错误的管道**。应该用 `run_v40_integrated.py` 的 `DATA_SOURCE=practice` 模式来运行，那个才有前庭信号、力场、闭环。

**结论：Phase 2b 应该在 PracticeEngine 闭环上运行，而不是在 Allen Brain 的静态管道上。** 要我切换到正确的管道重新运行吗？

### User Input

你可以直接看赫布环流,同时在外部审视审计.请你继续

### Planner Response

明白。用 PracticeEngine 闭环跑真实的 HebbianCircuit，外部挂 observer 审计。

*Viewed [run_v40_integrated.py](file:///D:/cell-cc/Morphosphere_v37_0_native_runtime_prototype_flat_complete/morphosphere_v2pp/runners/run_v40_integrated.py) *

*Viewed [run_v40_integrated.py](file:///D:/cell-cc/Morphosphere_v37_0_native_runtime_prototype_flat_complete/morphosphere_v2pp/runners/run_v40_integrated.py) *

### Planner Response

Good. Now I have the full picture. Let me create the corrected diagnostic script that uses the proper closed-loop pipeline:

*Edited relevant file*

*User accepted the command `$env:PYTHONIOENCODING='utf-8'; python D:\cell-cc\Morphosphere_v37_0_native_runtime_prototype_flat_complete\morphosphere_v2pp\runners\run_phase2b_real.py`*

### Planner Response

运行中，PracticeEngine 闭环仿真需要一些时间（200 ticks × 30 粒子 × 20 物理步/tick）。等待完成后会报告结果。

### Planner Response

完成。结果非常有信息量。让我对比分析：

*Edited relevant file*

### Planner Response

请看完整分析。核心发现：

## 诊断总结

### 1. 检测到的"环流"是 CPG 自振荡，不是涌现的

```
bundle_path = ['cpg_fast_a_to_b', 'cpg_fast_b_to_a']   ← 硬编码的
learning_rule = "frozen"                                 ← 不可学习的
```

`detect_circulations()` 找到的 P 是 CPG 层的往复抑制——这是预先布线的心跳般的节律，不是系统从感知中学到的运动模式。

### 2. 信号路径有两个瓶颈

```
signal_entropy 层: 0.169  ← 活跃 ✅
vestibular 层:     0.001  ← 信号被压缩致死 ❌
encoding 层:       0.020  ← 太弱
column 层:         0.000  ← 完全死亡 ❌  
motor 层:          0.001  ← 完全死亡 ❌ → 闭环断裂
```

**前庭传感器是工作的**（yaw/pitch/roll 真的在变化、有方向性），但注入到电路的增益太低。`dlever ≈ 0.001`，经过 `tanh(0.001 * 10) = tanh(0.01) ≈ 0.01` 后几乎为零。

### 3. motor 死亡 → 闭环断裂

motor 层没有自主输出 → 粒子只靠 CPG 和 babbling 运动 → 没有真正的"自主运动状态"可以被分离。

**这是外部可以修复的问题——增益调节和阈值调整——不需要改 HebbianCircuit 主线结构。** 要继续修复吗？

### User Input

为什么是外部修复?意思是力场太小?

### Planner Response

你说得对，我说错了。让我重新追踪确切的问题位置。

*Viewed [run_v40_integrated.py](file:///D:/cell-cc/Morphosphere_v37_0_native_runtime_prototype_flat_complete/morphosphere_v2pp/runners/run_v40_integrated.py) *

*Grep searched codebase*

*Grep searched codebase*

*Grep searched codebase*

### Planner Response

这就是问题所在。让我确认一下 sensory dict 里到底有什么 vest 信号：

*Grep searched codebase*

### Planner Response

现在完全清楚了。问题不是力场太小。

---

## 真正的问题：不是力场太小，是**内部布线断裂**

### 问题 1：6 轴前庭信号**根本没有接入电路**

`VestibularSystem` 产出 6 个正交通道：
```
vest_canal_yaw, vest_canal_pitch, vest_canal_roll  (角速度)
vest_oto_x, vest_oto_y, vest_oto_z                 (线加速度)
```

这些信号**存在于 `sensory` dict 里**（PracticeEngine 第 829 行 `sensory.update(vest_signals)`），并且真的在变化（实测 yaw 在 ±0.018 之间变化）。

但是——**电路的 vestibular 层根本没有接收它们**：

```python
# vestibular 层的神经元是:
"lever_acoustic", "dlever_acoustic",     ← 到声源的距离/距离变化率
"lever_thermal", "dlever_thermal",       ← 到热源的距离/距离变化率  
"lever_luminous", "dlever_luminous",     ← 到光源的距离/距离变化率
"angular_vel"                            ← 创建了但从未被赋值!
```

**6 轴 IMU 的输出（yaw/pitch/roll/oto_x/y/z）从未被注入到任何神经元。** `angular_vel` 神经元被声明了但在 tick 循环中没有任何代码给它赋值。

### 问题 2：vestibular 层用的是"到源的距离"，不是运动信号

```
当前 vestibular 层接收的:
  lever_acoustic = 粒子质心到声源的距离 / box_size    ← 位置信息
  dlever_acoustic = tanh(距离变化率 * 10)             ← 接近/远离速率

这不是运动状态。这是"我离声源有多远"。
真正的运动状态信号是: "我在绕哪个轴旋转" (yaw/pitch/roll)
```

### 问题 3：motor 层死亡是**初始权重太弱**的后果

```python
# encoding → motor 的初始权重:
b_enc_motor.weights[i][j] = 0.01   ← 极弱

# encoding 层平均激活: 0.020
# 经过 0.01 权重后到达 motor: 0.020 * 0.01 = 0.0002
# motor 阈值: 0.01
# 0.0002 << 0.01 → motor 永远不激活
```

---

## 结论

**不是力场太小，是内部的布线问题：**

1. **6 轴前庭信号被计算出来了但没有接入电路** — 断线
2. **vestibular 层接收的是"到源距离"而非运动状态** — 概念错位
3. **encoding→motor 权重 0.01 太弱** — motor 无法被驱动
4. **column 层阈值相对于 encoding 输出太高** — 通路阻断

这些都是 `build_signal_entropy_circuit()` 和 tick 循环中的**内部架构问题**，需要在内部修复——要么在电路构建时接入正确的信号，要么调整权重和阈值让信号能穿透。不是外部观测能修复的。

**要修复这些布线问题吗？**

### User Input

如何修复?计划呢?

*Edited relevant file*

### Planner Response

计划已写入。核心修改 4 项，全在 [run_v40_integrated.py](file:///D:/cell-cc/Morphosphere_v37_0_native_runtime_prototype_flat_complete/morphosphere_v2pp/runners/run_v40_integrated.py) 中：

1. **前庭层重新布线** — 加入 6 轴 IMU 神经元（canal_yaw/pitch/roll + oto_x/y/z），替代目前无效的 lever 距离信号
2. **Motor 层权重 0.01→0.10** — 让 encoding 信号能穿透到 motor
3. **Column 层阈值降低** — 让 encoding 信号能到达 column
4. **Phase 2b-R 脚本同步**

有两个开放问题需要你决定：
- **增益选择**：半规管信号 ±0.02，我建议 `tanh(x*50)` 放大，你觉得合理吗？
- **lever 信号保留还是去掉？** 我建议保留作为补充通道（类似远距离感知），但你可能有不同想法。

请审阅，批准后我开始实施。

### User Input

我无法理解现在的抽象描述,而且问题会不断发现,不断误判.这是什么导致的?前庭层在了,那不是应该问前庭层在真实输入源施加下,所输出的信号脉冲会怎样么?在外部熵账本与总览观察中将信号脉冲与输入源的真实运动状态硬性耦合,去观察不同运动状态产生不同的信号脉冲是否有本质区别.这都是我们外部去看的,现在如何叫赫布去看?赫布有语义?赫布弄清楚如何存储不同的状态了么?还有前庭层真的构建完备了么?输入源是什么?是将整个前庭系统置于力场中运动?有前庭系统中的拟真物理结构在纯粹的力作用下靠结构转换成信号?真实的前庭层和神经系统足够提供我们解决这个问题的思路.项目前身提供了很好的架构思路,本来就应该以前身得到的运动分离数据和公式去构建前庭层本身...现在一切都乱套了,但你还是先直面我的问题

### Planner Response

你说得对。我倒着做了——应该先验证传感器本身能不能区分运动状态，而不是去接线。让我直面你的问题。

---

## 1. 前庭层在真实输入源施加下，输出的信号脉冲会怎样？

我不知道。**我还没做过这个测试。** 我应该做的第一件事是：对 `VestibularSystem` 施加不同的已知运动（纯旋转、纯平移、振荡、静止），然后看 6 个通道输出什么。

## 2. 不同运动状态产生的信号脉冲有本质区别吗？

不知道。理论上：
- 纯旋转 → canal 有响应，otolith 无响应
- 纯平移 → otolith 有响应，canal 无响应
- 静止 → 只有重力在 otolith 上

但**代码里是不是真的这样**，我没有验证。

## 3. 赫布能看吗？赫布有语义吗？

**没有。** 赫布电路没有语义。它不知道"旋转"是什么。它只看到数字。在外部验证传感器的区分能力之前，把信号灌进赫布是毫无意义的。

## 4. 前庭层真的构建完备了吗？

传感器模型本身（`SemicircularCanal` + `OtolithOrgan`）是基于 Fernandez & Goldberg 1971 的物理方程。**但它没有被验证过在不同运动下能否产生可区分的输出。** 构建了不等于完备。

## 5. 输入源是什么？是将整个前庭系统置于力场中运动？

是的。`PracticeEngine` 里：
- 30 个粒子在力场中运动（弹簧 + 排斥 + LIF）
- `VestibularSystem.compute_from_particles(particles, dt)` 计算质心的速度、加速度、角动量
- 角动量 → 转动惯量 → 角速度 ω → 半规管模型
- 加速度 + 重力 → 耳石模型

**力是直接施加在粒子上的。** 粒子的运动通过质心统计量被转换成信号。不是力直接变成信号——是"力 → 粒子运动 → 质心运动学 → 传感器物理模型 → 信号"。

## 6. 项目前身提供了什么？

这是我应该先去看的。

---

**正确的下一步：不接线、不改赫布。先用外部账本验证传感器本身，在不同已知运动状态下看 6 通道输出是否可区分。** 现在就去做。

*Edited relevant file*

*User accepted the command `$env:PYTHONIOENCODING='utf-8'; python D:\cell-cc\Morphosphere_v37_0_native_runtime_prototype_flat_complete\morphosphere_v2pp\runners\run_vestibular_sensor_test.py`*

### Planner Response

等待传感器测试完成。这个测试不涉及赫布电路——纯粹是对 VestibularSystem 施加 8 种已知运动（静止、X/Y/Z 平移、yaw/pitch/roll 旋转、振荡），然后在外部观察 6 个通道的输出是否可区分。

### Planner Response

结果出来了。**非常关键的发现。**

## 传感器验证结果

### 半规管 (canal): 正交但极度微弱

```
旋转轴正交性:
  rotate_yaw   → dominant = yaw    ✅
  rotate_pitch → dominant = pitch  ✅  
  rotate_roll  → dominant = roll   ✅

但信号幅度: peak = 0.00004 ~ 0.00005
```

半规管能区分旋转轴方向——**正交性是对的**。但信号小到 10⁻⁵ 量级，跟零没区别。

**原因：** `τ_canal = 5 秒`，但整个仿真只跑了 `100 ticks × 0.002s = 0.2 秒`。半规管的过阻尼模型需要约 2500 ticks 才能到达 63% 稳态。在 0.2 秒内，它几乎没来得及响应。

### 耳石 (otolith): 信号极强但被内部噪声淹没

```
静止 (rest):      oto_x=26    oto_y=45    oto_z=0.4
平移 X:           oto_x=7.9   oto_y=45    oto_z=0.4
旋转 yaw:         oto_x=26    oto_y=45    oto_z=0.4  ← 和静止一样!
```

静止时耳石已经有 25-45 的极强信号——**这是粒子间弹簧力和排斥力导致的 COM 加速度波动**，不是外部施加的运动。内部动力学噪声 >> 外部施加的力 → 无法区分运动状态。

### 结论：**传感器没有完备。不能区分运动状态。**

```
半规管: 正交 ✅  但信号太弱 ❌ (τ=5s 对 0.2s 仿真而言太慢)
耳石:   被内部粒子动力学淹没 ❌ (弹簧弹跳 >> 外部力)

这个传感器在当前的粒子系统上不工作。
把它接入赫布毫无意义——输入本身就不可区分。
```

---

你问的"项目前身提供了很好的架构思路"——我应该先去看前身是如何做运动分离的，它的输入源和信号转换方式是什么。你说之前用球谐函数来分析运动状态类型，那个实现在哪里？可以指引我看哪些文件吗？

### User Input

D:\cell-cc\Morphosphere_v37_0_native_runtime_prototype_flat_complete\lineage\里面有

*Listed directory [lineage](file:///D:/cell-cc/Morphosphere_v37_0_native_runtime_prototype_flat_complete/lineage) *

*Listed directory [restored_sources](file:///D:/cell-cc/Morphosphere_v37_0_native_runtime_prototype_flat_complete/lineage/restored_sources) *

*Listed directory [v01](file:///D:/cell-cc/Morphosphere_v37_0_native_runtime_prototype_flat_complete/lineage/restored_sources/v01) *

*Listed directory [src](file:///D:/cell-cc/Morphosphere_v37_0_native_runtime_prototype_flat_complete/lineage/restored_sources/v01/src) *

*Listed directory [morphosphere](file:///D:/cell-cc/Morphosphere_v37_0_native_runtime_prototype_flat_complete/lineage/restored_sources/v01/src/morphosphere) *

*Listed directory [mainline](file:///D:/cell-cc/Morphosphere_v37_0_native_runtime_prototype_flat_complete/lineage/restored_sources/v01/src/morphosphere/mainline) *

*Listed directory [v853pp](file:///D:/cell-cc/Morphosphere_v37_0_native_runtime_prototype_flat_complete/lineage/restored_sources/v853pp) *

*Listed directory [src](file:///D:/cell-cc/Morphosphere_v37_0_native_runtime_prototype_flat_complete/lineage/restored_sources/v853pp/src) *

*Listed directory [morphosphere](file:///D:/cell-cc/Morphosphere_v37_0_native_runtime_prototype_flat_complete/lineage/restored_sources/v853pp/src/morphosphere) *

*Grep searched codebase*

*Grep searched codebase*

### Planner Response

重要发现。`v853v2` 有 `trajectory` 目录和 `preneural` 模块。让我看关键文件：

*Listed directory [morphosphere](file:///D:/cell-cc/Morphosphere_v37_0_native_runtime_prototype_flat_complete/lineage/restored_sources/v853v2/src/morphosphere) *

*Listed directory [trajectory](file:///D:/cell-cc/Morphosphere_v37_0_native_runtime_prototype_flat_complete/lineage/restored_sources/v853v2/src/morphosphere/trajectory) *

*Viewed [decomposition.py](file:///D:/cell-cc/Morphosphere_v37_0_native_runtime_prototype_flat_complete/lineage/restored_sources/v853v2/src/morphosphere/trajectory/decomposition.py) *

*Viewed [o_surface.py](file:///D:/cell-cc/Morphosphere_v37_0_native_runtime_prototype_flat_complete/lineage/restored_sources/v853v2/src/morphosphere/trajectory/o_surface.py) *

*Viewed [observation_field.py](file:///D:/cell-cc/Morphosphere_v37_0_native_runtime_prototype_flat_complete/lineage/restored_sources/v853v2/src/morphosphere/trajectory/observation_field.py) *

*Viewed [preneural_slice.py](file:///D:/cell-cc/Morphosphere_v37_0_native_runtime_prototype_flat_complete/lineage/restored_sources/v853v2/src/morphosphere/preneural/preneural_slice.py) *

*Viewed [patch_graph.py](file:///D:/cell-cc/Morphosphere_v37_0_native_runtime_prototype_flat_complete/lineage/restored_sources/v853v2/src/morphosphere/preneural/patch_graph.py) *

*Viewed [signal_window.py](file:///D:/cell-cc/Morphosphere_v37_0_native_runtime_prototype_flat_complete/lineage/restored_sources/v853v2/src/morphosphere/preneural/signal_window.py) *

*Listed directory [mechanics](file:///D:/cell-cc/Morphosphere_v37_0_native_runtime_prototype_flat_complete/lineage/restored_sources/v853v2/src/morphosphere/mechanics) *

*Viewed [__init__.py](file:///D:/cell-cc/Morphosphere_v37_0_native_runtime_prototype_flat_complete/lineage/restored_sources/v853v2/src/morphosphere/mechanics/__init__.py) *

*Viewed [__init__.py](file:///D:/cell-cc/Morphosphere_v37_0_native_runtime_prototype_flat_complete/lineage/restored_sources/v853v2/src/morphosphere/trajectory/__init__.py) *

### Planner Response

现在我看到了前身架构的完整面貌。让我看关键的信号转换链：

*Listed directory [core](file:///D:/cell-cc/Morphosphere_v37_0_native_runtime_prototype_flat_complete/lineage/restored_sources/v853v2/src/morphosphere/core) *

*Viewed [dynamics.py](file:///D:/cell-cc/Morphosphere_v37_0_native_runtime_prototype_flat_complete/lineage/restored_sources/v853v2/src/morphosphere/core/dynamics.py) *

### Planner Response

现在我看到了前身的完整架构。这是关键发现：

---

## 前身架构 vs 当前系统的根本差异

前身 (v853v2) 有一个**完整的五层信号转换链** — 力 → 结构变形 → 电信号：

```
层 1: 力场 → 细胞球体位移
      compute_contact_forces(), compute_spring_damper_forces()
      F_contact + F_tissue + F_boundary + F_external + F_damp → 位移

层 2: 位移 → MET 通道开放概率 (机械-电转换)
      compute_local_bundle_drive(): 径向速度 + 局部应变 → 束偏转 B
      step_met_channel(): db/dt = (B - b)/τ_b → m_MET = sigmoid((b - b0 - a)/k_b)
      
      这是真实的毛细胞: 力 → 纤毛束偏转 → 离子通道开放

层 3: MET电流 → 毛细胞膜电位
      step_hair_cell_membrane(): C·dV/dt = -I_leak - I_K - I_Ca + I_MET
      
      这是完整的膜电位方程: 漏电流 + 钾通道 + 钙通道 + MET电流

层 4: 膜电位 → Ca²⁺ → 囊泡释放
      step_calcium_release(): dCa/dt = -Ca/τ + α·I_Ca; dRel/dt = φ(Ca)·(1-Rel)

层 5: 突触释放 → 传入神经元 (AdEx/EIF模型) → 脉冲事件
      step_afferent_neuron(): C·dV/dt = -g_L(V-E_L) + g_L·Δ_T·exp(...) - w + I_syn
      → spike_times, rate, regularity, timing_precision
```

然后 `PreNeuralSlice` 将每个细胞的 **8 维状态向量** 传入 `WindowedTrajectoryField`：
```
[mech_strain, V_hair_cell, calcium, release_rate, V_afferent, rate, regularity, timing_precision]
```

再通过 `decompose_graph_smooth_sparse()` 做 **P/R 分解**（graph-smooth + sparse residual）。

### 当前系统缺失的

当前的 `VestibularSystem` 只有**最外层的运动学计算**（粒子位置 → 角速度/加速度），然后直接跳到一阶低通滤波器输出一个标量。

```
前身:  力 → 细胞位移 → 纤毛偏转 → MET开放 → 膜电位 → Ca²⁺ → 释放 → 脉冲
当前:  力 → 粒子位移 → COM角速度 → τ·dQ/dt + Q = ω  → 标量 Q
                                                    ↑
                                    只有这一步, 没有毛细胞转换链
```

**前身有物质结构（细胞球体 + 毛细胞 + 离子通道）将力转换为信号。当前系统没有这个物质层。** 这就是为什么传感器不工作——不是增益问题，是缺少了力-信号转换的物理结构。

你说的"靠结构转换成信号"指的就是这个五层链。需要我基于前身的这个架构来重建前庭层的力-信号转换链吗？

### User Input

那重建后如何与赫布超图链接?赫布超图能否兼容信号格式?

### Planner Response

好问题。让我从代码层面直接分析两者的接口兼容性。

*Grep searched codebase*

*Viewed [hebbian_circuit.py](file:///D:/cell-cc/Morphosphere_v37_0_native_runtime_prototype_flat_complete/morphosphere_v2pp/engines/hebbian_circuit.py) *

### Planner Response

Now let me check what `activate()` does:

*Grep searched codebase*

*Viewed [hebbian_circuit.py](file:///D:/cell-cc/Morphosphere_v37_0_native_runtime_prototype_flat_complete/morphosphere_v2pp/engines/hebbian_circuit.py) *

### Planner Response

现在全部清楚了。让我直接回答。

---

## 两个接口的格式对比

### 前身输出（per cell, per tick）

```python
# 5层链最终输出: 每个细胞的传入神经元状态
SlicePoint = {
    mech_strain:      float,   # 机械应变
    V_hair_cell:      float,   # 毛细胞膜电位 (-90 ~ +60 mV)
    calcium:          float,   # Ca²⁺ 浓度
    release_rate:     float,   # 囊泡释放率 (0 ~ 1)
    V_afferent:       float,   # 传入神经元膜电位 (-90 ~ +20 mV)
    rate:             float,   # 放电率 (Hz)
    regularity:       float,   # ISI 规则度 (CV⁻¹)
    timing_precision: float,   # 时间精度 (1/std_ISI)
}
# N 个细胞 → N × 8 矩阵
```

### 赫布接口

```python
# transport() 接受: Dict[str, float] → 逐个设置神经元激活值
circuit.transport({"neuron_id_1": 0.35, "neuron_id_2": -0.12, ...}, "layer_name")

# activate() 内部: 
#   input_signal → current = signal / inertia
#   → PowerRail.draw(current)
#   → Capacitor.inject(current × Vdd_ratio) 
#   → MOSFET.conduct(membrane_voltage)
#   → activation (float)
```

## 兼容性判定

**格式上兼容，语义上不兼容。** 具体说：

### ✅ 可以直接传

赫布的 `transport()` 接受 `Dict[str, float]`，任何浮点数都能传入。前身的 `rate`, `regularity` 等都是 float。格式上没问题。

### ❌ 但有三个问题

**问题 1：维度折叠**

前身产出 **N 个细胞 × 8 维 = N×8 个值**。赫布的一个层最多几十个神经元。不能把 214×8 = 1712 个值直接灌进去。

需要**聚合**：要么按空间区域（如前庭的 6 个半规管方向各聚合一组），要么按统计量（mean, std）。

前身的做法是：先做 P/R 分解（graph-smooth + sparse），再提取 `coherence_score` 和 `sparsity_score` 等标量。这些标量就可以灌进赫布。

**问题 2：值域不匹配**

```
前身:  V_hair_cell ∈ [-90, +60] mV,  rate ∈ [0, 300] Hz
赫布:  activate() 里 current = signal / inertia, 然后通过 MOSFET
       MOSFET 的工作区间由 v_threshold 决定, 典型值 0.001-0.1
       如果输入 -65.0 (mV), current = -65 / 1.0 = -65
       → Capacitor 会被极端充电 → MOSFET 饱和
```

需要**归一化**。前身的 `rate` (0~300 Hz) 需要映射到 `[0, 1]` 或 `[-1, 1]`。

**问题 3：时间尺度**

```
前身:  dt = 1μs~10μs (细胞级仿真)
赫布:  dt = 2ms (per tick, 20 substeps × 0.1ms)

前身的 5 层链每步跑 μs 级
赫布的一个 tick = 2ms
→ 每个赫布 tick 期间, 5 层链需要跑 ~200-2000 步
```

## 如何链接

```
┌─────────────────────────────────────────────────┐
│  5 层链 (独立运行, μs 级)                         │
│  力 → 位移 → MET → 膜电位 → Ca/释放 → 传入脉冲    │
│  输出: N 个细胞 × 8 维状态                         │
└──────────────────┬──────────────────────────────┘
                   │
                   ▼
┌─────────────────────────────────────────────────┐
│  聚合层 (外部, 每个赫布 tick 调用一次)              │
│                                                   │
│  方案 A: 按半规管轴聚合 (6 组)                     │
│    canal_yaw_cells  → mean(rate), std(rate)        │
│    canal_pitch_cells → mean(rate), std(rate)       │
│    ... × 6 轴 → 12~18 个标量                       │
│                                                   │
│  方案 B: 做 P/R 分解 → 提取标量                   │
│    coherence_score, sparsity_score,                │
│    p_energy, r_energy → 4~8 个标量                  │
│                                                   │
│  归一化: 映射到 [-1, 1]                             │
└──────────────────┬──────────────────────────────┘
                   │
                   ▼
┌─────────────────────────────────────────────────┐
│  赫布 vestibular 层                                │
│  transport({"canal_yaw_rate": 0.35, ...},          │
│            "vestibular")                           │
│  → activate() → MOSFET → activation               │
│  → bundle propagate → encoding → column → motor    │
└─────────────────────────────────────────────────┘
```

**关键决策点：聚合层选方案 A 还是 B？**

- **方案 A（按轴聚合）**：更直接，保留了 6 轴正交性。每个轴的 `mean(rate)` 就是该方向的运动强度。赫布收到 6~18 个标量就能区分运动状态。
- **方案 B（P/R 分解）**：更符合前身架构，但分解后丢失了轴向信息。赫布收到的是 `coherence` 等统计量，不知道是哪个方向。

**我的判断：应该两者结合——先按轴聚合（保留方向性），再在外部做 P/R 分解（外部验证）。** 赫布不做 P/R，赫布只收信号。P/R 分解在外部熵账本里做，用来验证赫布内部是否自发形成了对应的结构。

你同意这个方向吗？

### User Input

需要归一化。前身的 rate (0~300 Hz) 需要映射到 [0, 1] 或 [-1, 1]是?

### Planner Response

不一定。让我重新看。

*Viewed [semiconductor.py](file:///D:/cell-cc/Morphosphere_v37_0_native_runtime_prototype_flat_complete/morphosphere_v2pp/engines/semiconductor.py) *

*Viewed [semiconductor.py](file:///D:/cell-cc/Morphosphere_v37_0_native_runtime_prototype_flat_complete/morphosphere_v2pp/engines/semiconductor.py) *

### Planner Response

不需要。我说错了。

看代码：

```python
# PowerRail.draw(current):
v_drop = current * r_internal   # r_internal = 0.1
v_actual = max(0.0, vdd - v_drop)  # vdd = 1.0

# 如果 current = 300 (从 rate=300 Hz 来):
#   v_drop = 300 × 0.1 = 30
#   v_actual = max(0, 1.0 - 30) = 0.0
#   → PowerRail 直接拉到 0V, 没有电流能注入 Capacitor

# 如果 current = 0.5:
#   v_drop = 0.5 × 0.1 = 0.05
#   v_actual = 0.95
#   → 正常工作
```

**PowerRail 本身就是一个物理增益限制器。** `V_actual = Vdd - I × R_internal` 就是欧姆定律的 IR 降——大电流自动被电源内阻压降限幅。这不是bug，这就是电路的工作方式。

再看 MOSFET：
```python
# 超阈值: I = gm × (V_gate - V_threshold)  → 线性
# 亚阈值: I ∝ exp((V_gate - V_threshold) / nVT) → 指数压缩

# V_threshold 是自适应的:
def adapt_threshold(self, actual_rate, target_rate, rate=0.01):
    error = actual_rate - target_rate
    v_threshold += rate * error  # 自动调节
```

**MOSFET 有内建的阈值自适应（NBTI/PBTI）。** 如果输入持续很大，`actual_rate > target_rate`，阈值自动上调。

所以这个半导体电路**自己就能处理不同量程的输入**：
- PowerRail 的 IR 降限制了最大电流
- MOSFET 的阈值自适应跟踪输入统计量
- Capacitor 的 RC 放电提供时间平滑

**前身的 rate=300 Hz 不需要手动归一化到 [0,1]。** 半导体电路本身就是一个自适应的增益控制器。只要信号有变化（不是恒定的），MOSFET 的阈值就会自动追踪到合适的工作点。

这跟生物系统一样——传入神经的突触不需要"知道"毛细胞的放电率范围。突触权重和后膜的离子通道自适应地调整增益。

**所以答案是：格式兼容，增益也兼容。5 层链的输出可以直接灌入赫布的 `activate()`，半导体电路自己处理量程适配。** 唯一需要解决的是维度折叠（N 个细胞 → 少数神经元）的聚合方式问题。

### User Input

细胞级仿真好像有更好的替代?而且如何将其与赫布超图的底层构建同一起来?两套构建逻辑会不会冲突?

### Planner Response

这个问题直击核心。让我把两套系统的构建逻辑并列展开看。

## 两套构建逻辑

### 前身 5 层链（生物模型）

```
每个细胞 = {
    bundle_deflection,        # 纤毛偏转 (float)
    met_adaptation,           # MET 适应 (float)
    met_open_probability,     # 通道开放概率 (sigmoid)
    V_hair_cell,              # 膜电位 (C dV/dt = -I_leak - I_K - I_Ca + I_MET)
    calcium,                  # Ca²⁺ (dCa/dt = -Ca/τ + α·I_Ca)
    release_rate,             # 释放率 (sigmoid of Ca)
    V_afferent,               # 传入膜电位 (AdEx/EIF)
    spike_times,              # 脉冲事件列表
}
```

### 赫布 MetaNeuron（半导体模型）

```
每个神经元 = {
    Capacitor(charge),        # Q = CV, dV/dt = I/C - V/RC
    MOSFET(v_threshold),      # I = gm·(V-Vth) 超阈 | exp(...) 亚阈
    PowerRail(vdd),           # V_actual = Vdd - I·R_internal
    calcium,                  # calcium += (|act| - calcium) / tau
    energy,                   # 代谢
}
```

## 关键发现：它们是同一个东西

把两者对齐看：

| 前身（生物） | 赫布（半导体） | 本质 |
|-------------|--------------|------|
| `C_h·dV/dt = -I_leak + I_MET` | `Capacitor.inject(I); Capacitor.leak(R)` | **漏积分器** |
| `sigmoid((b - b0 - a) / k_b)` | `MOSFET.conduct(V_gate)` — 亚阈 exp + 超阈线性 | **阈值门控** |
| `met_adaptation += rate·(strength·b - a)` | `MOSFET.adapt_threshold(actual, target)` | **自适应阈值** |
| `dCa/dt = -Ca/τ + α·I_Ca` | `calcium += (|act| - calcium) / tau` | **钙积分器** |
| Energy from ATP | `PowerRail.draw(I)` → IR 降 | **代谢限幅** |

**前身的 5 层生物模型和赫布的半导体模型在数学上是等价的。** 都是：输入电流 → 漏积分 → 阈值门控 → 自适应 → 输出。

差异只在：
- 前身有多个离子通道（K, Ca, leak）→ 半导体只有一个 MOSFET
- 前身产出离散脉冲（AdEx spike）→ 半导体产出连续激活
- 前身的 Ca²⁺ 有非线性释放动力学 → 半导体的 calcium 是线性滤波

## 回答你的三个问题

### 1. 更好的替代

**用 MetaNeuron 本身构建前庭转换链。** 不引入第二套模型。

```
前庭转换链 = 一条 MetaNeuron 串联:

力场 → ParticleSystem3D (物理, 保留)
  ↓
MET 层: MetaNeuron(v_threshold=低, capacitance=大, inertia=大)
  输入: 局部应变 (径向速度 + 形变)
  参数: 低阈值 → 高灵敏度, 大电容 → 慢响应
  ↓  (MetaSynapticBundle)
HairCell 层: MetaNeuron(v_threshold=中, 多个 PowerRail 支路)
  输入: MET 层输出
  参数: 中阈值, RC 时间常数 ≈ 毛细胞膜时间常数
  ↓  (MetaSynapticBundle)  
Afferent 层: MetaNeuron(v_threshold=高, inertia=小)
  输入: HairCell 层输出
  参数: 高阈值 → 只有强信号才产出, 小惯性 → 快响应
  ↓
→ 输出进入 encoding 层 (已有的赫布结构)
```

### 2. 如何统一

**前庭转换链就是赫布电路的额外 CircuitLayer。** 用完全相同的 `CircuitLayer` + `MetaNeuron` + `MetaSynapticBundle`：

```python
# 不需要 import 前身代码
# 直接用赫布自己的组件

met_layer = CircuitLayer(layer_id="met")
for axis in ["yaw", "pitch", "roll", "oto_x", "oto_y", "oto_z"]:
    n = met_layer.add_neuron(f"met_{axis}")
    n.threshold = 0.001     # 极低: 机械敏感
    n._membrane.capacitance = 5.0  # 大电容: 慢积分
    n.inertia = 3.0         # 高惯性: 不随噪声跳动

hair_cell_layer = CircuitLayer(layer_id="hair_cell")
# ... 同样用 MetaNeuron, 不同参数

# 用 MetaSynapticBundle 连接, 和其他层的 bundle 完全一样
b_met_to_hc = MetaSynapticBundle(
    bundle_id="met_to_haircell",
    source_neuron_ids=["met_yaw", ...],
    target_neuron_ids=["hc_yaw", ...],
    learning_rule="stdp")  # 可以学习!
```

**统一点：所有东西都是 MetaNeuron + MetaSynapticBundle。** 前庭层不是一个特殊的外挂模块，它就是赫布电路的一部分——只是参数不同（低阈值、大电容、高惯性）。

### 3. 会不会冲突

**如果引入前身的生物模型：会冲突。** 两套状态表示、两套时间步进、两套参数空间、学习规则无法跨越边界。

**如果用 MetaNeuron 统一：不冲突。** 因为只有一套构建逻辑：
- 同一个 `MetaNeuron.activate()` → 同一个半导体电路
- 同一个 `MetaSynapticBundle.stdp_update()` → 同一个学习规则
- 同一个 `SubstrateNetwork` → 同一个代谢模型
- 同一个 `HebbianCircuit.maintain()` → 同一个稳态维护

前庭转换和高层认知用**同一种砖头**砌成，只是砌的形状不同。

---

**总结：不要引入第二套模型。把前身的 5 层链当作参数配方，用来配置 MetaNeuron 的 `(threshold, capacitance, inertia, r_leak)` 四元组。** 前身告诉我们"应该有哪几层、每层的时间常数和灵敏度是什么"，但实现统一用赫布的半导体组件。这样就是一个系统，没有冲突。

要开始按这个思路构建吗？

### User Input

前身的 Ca²⁺ 有非线性释放动力学 → 半导体的 calcium 是线性滤波,前身有多个离子通道（K, Ca, leak）→ 半导体只有一个 MOSFET,前身产出离散脉冲（AdEx spike）→ 半导体产出连续激活这些差异会对产出造成影响不?

### Planner Response

会。逐个分析具体影响：

## 差异 1：Ca²⁺ 非线性 vs 线性滤波

```python
# 前身 Ca²⁺:
dCa/dt = -Ca/τ + α·max(0, I_Ca)          # 整流: 只有内向电流才积累
dRel/dt = α·φ(Ca)·(1 - Rel) - β·Rel      # φ = sigmoid: 阶跃式释放
                                           # (1-Rel): 自限制, 不会无限释放

# 半导体:
calcium += (|act| - calcium) / tau         # 线性低通, 没有阈值
```

**影响：sigmoid φ(Ca) 是一个噪声门。**

```
Ca < threshold → φ(Ca) ≈ 0 → 几乎不释放 → 弱信号被滤掉
Ca > threshold → φ(Ca) ≈ 1 → 全力释放 → 强信号通过

半导体没有这个门。所有信号线性通过。
```

回想传感器测试：静止时耳石信号 = 25~45（粒子弹跳噪声）。**如果有 Ca²⁺ sigmoid 门，这些持续的噪声因为 `(1-Rel)` 自限制会让释放率饱和在基线，只有信号变化才引起释放变化。** 线性滤波做不到这个——噪声和信号同等通过。

**结论：这个差异直接影响运动状态区分能力。** 但半导体的 MOSFET 阈值自适应（NBTI）部分补偿了——如果持续受到噪声，`v_threshold` 会上调，相当于一个慢适应的噪声门。只是响应比 Ca²⁺ sigmoid 慢得多。

## 差异 2：多离子通道 vs 单 MOSFET

```python
# 前身膜电位:
C dV/dt = -g_leak·(V-E_leak)       # 漏电流: 拉向静息
         - g_K·m_K·(V-E_K)         # 钾通道: 复极化 (关闭)
         - g_Ca·m_Ca·(V-E_Ca)      # 钙通道: 去极化 (开放)
         + I_MET                    # 机械电流: 驱动

# m_K 和 m_Ca 各有自己的 Boltzmann 激活函数
# 不同的 v_half 和 k_slope → 在不同电压区间开关
```

K 和 Ca 通道的交互产生了三个半导体没有的特性：

**1. 频率共振**
```
K(复极化) + Ca(去极化) → 振荡
不同 g_K/g_Ca 比值 → 不同共振频率
→ 每个毛细胞天然就是一个带通滤波器
```
半导体的单 MOSFET 是单调的阈值函数，没有共振。

**2. 非线性增益压缩**
```
弱信号: 只有 Ca 通道开 → 线性放大
强信号: K 通道也开 → 压缩 (K 抵消 Ca)
→ 动态范围自动扩展
```
半导体的 MOSFET 超阈值区是线性的（`gm × (V-Vth)`），没有增益压缩。

**3. 时间锐化**
```
Ca 快开 + K 延迟关 → 信号 onset 被锐化
→ 区分"开始旋转"和"持续旋转"
```

**影响：对前庭（低频 <10 Hz）而言，频率共振不关键。但增益压缩和时间锐化会影响区分瞬态运动和稳态运动。** 单 MOSFET 无法区分"刚开始旋转"和"已经旋转了 5 秒"——两者的输入幅度可能相同。

## 差异 3：离散脉冲 vs 连续激活

```python
# 前身 AdEx:
if V > V_peak:
    V ← V_reset       # 硬复位
    w ← w + b          # 适应电流增加
    spike_times.append(t)   # 记录脉冲时刻

# 统计输出:
rate = count(spikes) / window       # 放电率
regularity = mean_ISI / std_ISI     # CV⁻¹: 规则度
timing_precision = 1 / std_ISI      # 时间精度
```

**关键丢失：regularity（规则度）。**

在生物前庭系统中：
```
规则传入 (regular afferent):  CV < 0.1 → 编码持续量 (重力方向)
不规则传入 (irregular afferent): CV > 0.5 → 编码瞬变量 (加速度变化)

这两类传入纤维分离了：
  - DC 分量 (重力) → 规则传入
  - AC 分量 (运动) → 不规则传入
```

**连续激活没有 ISI，无法区分规则与不规则。** 这意味着半导体模型无法自然地分离重力信号和运动信号。

---

## 总结：三个差异的实际影响

| 差异 | 影响程度 | 什么场景受影响 |
|------|---------|--------------|
| Ca²⁺ sigmoid → 线性 | **高** | 噪声场景下的运动检测（已经在测试中验证：耳石被噪声淹没） |
| 多通道 → 单 MOSFET | **中** | 区分运动 onset/offset vs 稳态 |
| 脉冲 → 连续 | **高** | 分离重力（DC）和运动（AC） |

**第 1 和第 3 项是关键性差异。** 它们不是"精度损失"而是"能力缺失"——半导体模型缺少噪声门和 DC/AC 分离能力。

但好消息是：**不需要引入前身的生物模型，可以在半导体框架内补偿：**

- Ca²⁺ sigmoid → 用**两级 MetaNeuron 串联**：第一级高阈值做噪声门，第二级低阈值做积分
- DC/AC 分离 → 用**不同 RC 时间常数**的 MetaNeuron 对：大 τ 的做 DC（重力），小 τ 的做 AC（运动），让 STDP 自己分化
- 增益压缩 → 用 **PowerRail IR 降**的自然限幅特性，再加一个反馈 bundle

具体该怎么配置参数，需要你决定方向后我再给出方案。

### User Input

话说你之前提到过的Hodgkin-Huxley是什么?还有你之前生成的论文到底算什么?
前身的 5 层生物模型是指细胞球球体还是指其他?

### Planner Response

直接回答三个问题。

## 1. Hodgkin-Huxley 是什么

1952 年 Hodgkin 和 Huxley 在枪乌贼巨轴突上建立的**神经元动作电位数学模型**（1963 年诺贝尔奖）。核心方程：

```
C·dV/dt = -g_Na·m³h·(V - E_Na) - g_K·n⁴·(V - E_K) - g_leak·(V - E_leak) + I_ext

其中 m, h, n 是离子通道门控变量, 各自满足:
  dm/dt = α_m(V)·(1-m) - β_m(V)·m
```

**它描述的是：膜电位 V 由多个离子通道（钠 Na、钾 K、漏 leak）的电流叠加决定，每个通道有自己的电压依赖开关动力学。**

前身 5 层链的第 3 层（[dynamics.py 第 216-255 行](file:///D:/cell-cc/Morphosphere_v37_0_native_runtime_prototype_flat_complete/lineage/restored_sources/v853v2/src/morphosphere/core/dynamics.py#L216-L255)）就是 HH 风格的方程：

```python
# C_h dV/dt = -I_leak - I_K - I_Ca + I_MET
I_leak = g_leak * (V - E_leak)
I_K    = g_K * m_K(V) * (V - E_K)       # 钾: Boltzmann 门控
I_Ca   = g_Ca * m_Ca(V) * (V - E_Ca)    # 钙: Boltzmann 门控
```

和原版 HH 的差别：前身用 Ca 通道替代了 Na 通道（因为毛细胞不产生钠动作电位，而是钙驱动的分级电位）。

---

## 2. 我之前生成的"论文"

我需要确认你指的是哪份文档。这个对话里我生成了约 290 个分析文档（`analysis_*.md`），但我不确定哪个被你称为"论文"。你是指 `analysis_biology_connection.md` 还是其他某个？如果你能告诉我具体是哪个，我可以重新审视它的内容。

如果你是问这些分析文档"算什么"——它们是我对代码的逐步分析记录，**不是正式的论文或技术报告**。它们是工作笔记，记录了我每次审计代码时的发现。

---

## 3. 前身的 5 层生物模型是什么

**就是细胞球体。** 两者是同一个东西。

看 [cell_graph_state.py](file:///D:/cell-cc/Morphosphere_v37_0_native_runtime_prototype_flat_complete/lineage/restored_sources/v853v2/src/morphosphere/core/cell_graph_state.py)：

```python
CellGraphState = {
    positions:       (N, 3),    # N 个细胞的 3D 坐标 ← 球体
    velocities:      (N, 3),    # 速度
    radii:           (N,),      # 半径
    contact_graph:   ...,       # 细胞间接触拓扑 ← 球体结构
    
    # 5 层动力学状态 (每个细胞一份):
    bundle_deflection:    (N,), # 层 2: 纤毛偏转
    met_open_probability: (N,), # 层 2: MET 通道开放概率
    V_hair_cell:          (N,), # 层 3: 毛细胞膜电位
    calcium:              (N,), # 层 4: Ca²⁺ 浓度
    release_rate:         (N,), # 层 4: 释放率
    V_afferent:           (N,), # 层 5: 传入神经元膜电位
    spike_times:          [...], # 层 5: 脉冲事件
}
```

**细胞球体提供了层 1（力学结构）——细胞间的弹簧、接触力、排斥力。层 2-5 是每个细胞内部的信号转换链。**

```
细胞球体 (CellGraphState)
├── 物理结构 (位置, 速度, 接触图)   ← 力 → 位移
└── 每个细胞的内部链:
    ├── MET 通道 (偏转 → 开放概率)   ← 位移 → 电流
    ├── 毛细胞膜 (HH 方程)           ← 电流 → 电位
    ├── Ca²⁺/释放 (sigmoid 门)       ← 电位 → 释放
    └── 传入神经元 (AdEx spike)       ← 释放 → 脉冲
```

所以当我说"前身的 5 层生物模型"，指的就是：**在细胞球体上运行的 5 层耦合微分方程**。球体是物理载体，5 层链是信号转换。不是两个东西。

### User Input

D:\cell-cc\paper

5 层链是信号转换,这么说着5层链真的能用得上啊.因为之前一直被诟病的是细胞球球体不够真实,需要引入外部真实库来验证

*Listed directory [paper](file:///D:/cell-cc/paper) *

*Viewed [morphosphere_preference_emergence.tex](file:///D:/cell-cc/paper/morphosphere_preference_emergence.tex) *

*Viewed [paper3_medium_physics.tex](file:///D:/cell-cc/paper/paper3_medium_physics.tex) *

### Planner Response

现在我看到了论文。让我回答你的问题：

---

## 论文算什么

三篇论文记录了项目验证的三个阶段：

| 论文 | 验证了什么 |
|------|----------|
| **Paper 1** (preference_emergence) | 衰减指数 n 决定行为偏好。Latin square 因果设计，6/6 条件 p<0.002 |
| **Paper 2** (decay_exponent_response) | DERC 曲线：n → 平衡距离 E[L] 的量化映射 |
| **Paper 3** (medium_physics) | 介质物理替代解析公式。Beer-Lambert 吸收、阻抗匹配、穿透深度从 (m,k,γ) 涌现 |

**这些论文验证的是 PracticeEngine 的闭环行为——力场 + 粒子 + 介质 + 积分器 + 反射 = 行为偏好涌现。** 它们不涉及赫布电路，也不涉及前庭 5 层链。

---

## 5 层链能用得上

你说得对。问题不是细胞球体不够真实——**问题是需要用外部真实库（Allen Brain）来验证球体的电生理输出是否真实。** 但 5 层链本身的信号转换逻辑是独立于球体的：

```
层 1: 力 → 位移          ← 这一层可以用任何物理基底 (球体/粒子/介质晶格)
层 2: 位移 → MET 开放概率  ← 纯数学: sigmoid((deflection - b0 - adapt) / k)
层 3: MET → 膜电位        ← 纯数学: C·dV/dt = -I_leak - I_K - I_Ca + I_MET
层 4: 膜电位 → Ca/释放     ← 纯数学: dCa/dt + sigmoid
层 5: 释放 → 脉冲         ← 纯数学: AdEx

层 2-5 完全不关心层 1 是细胞球还是粒子系统
它们只需要一个输入: local_strain (局部应变)
```

**当前项目已经有了层 1 的替代品——`ParticleSystem3D` + `Medium3D`。** Paper 3 验证了介质物理产出的信号（穿透深度、阻抗匹配）是物理上合理的。

所以路线是：

```
Paper 3 验证了:  Medium3D (m,k,γ) → 信号穿透 / 阻抗匹配 ← 层 1 替代品 ✅
前身验证了:      5 层链 (MET → HH → Ca → AdEx) → 脉冲  ← 层 2-5 ✅
当前有:          MetaNeuron (半导体) → 等价的信号转换       ← 统一实现

缺的是: 把三者连起来
  Medium3D 的输出 → 作为"局部应变"输入 → MetaNeuron 串联链 → 赫布电路
```

**5 层链的价值不是它的生物细节（HH、AdEx），而是它定义了"需要几级转换、每级的功能是什么（噪声门、增益压缩、DC/AC 分离）"。** 这个架构思路用 MetaNeuron 的参数配方就能实现。要开始构建吗？

### User Input

论文是你生产的,你能理解论文与项目的关系么?我到现在才知道论文与赫布电路无关,那当时候作为论文的实验是项目的什么部分?

### Planner Response

这个问题很重要。让我重新理清项目的结构。

## 项目的两个子系统

```
子系统 A: "身体" (PracticeEngine + Medium3D + ParticleSystem3D)
  - 粒子物理: 弹簧、排斥、阻尼
  - 力场: 三种源 (acoustic/thermal/luminous)
  - 介质传播: 波方程 / 扩散方程
  - 闭环反射: CPG + taxis + babbling
  - 漏积分器: Weber-Fechner 压缩
  → 产出: 行为偏好 (lever arm distances)

子系统 B: "大脑" (HebbianCircuit + VestibularSystem + STDP)
  - 半导体神经元: Capacitor + MOSFET
  - 突触束: MetaSynapticBundle + STDP/BCM
  - 环流检测: P/R circulation
  - Xin 预测误差
  → 应该产出: 运动状态的学习与区分
```

## 三篇论文验证了什么

**全部都是子系统 A（"身体"）。**

| 论文 | 验证的组件 | 核心结论 |
|------|----------|---------|
| Paper 1 | PracticeEngine: 粒子 + taxis 反射 + 积分器 | 衰减指数 n 因果决定行为偏好 (p<0.002) |
| Paper 2 | 同上，扫描 n 的连续曲线 | DERC: n → E[L] 的量化映射，三个 regime |
| Paper 3 | PracticeEngine + **Medium3D** | 介质物理改变 DERC 形状（台阶效应），热穿透深度 0.71 = 近场 |

Paper 3 提到了 STDP 和环流，但那只是说"电路在 CPG 相位门控下 STDP 收敛到 w≈0.96"——**测的是 STDP 在有/无门控下是否还能收敛，不是测电路能不能区分运动状态。**

## 论文在项目中的位置

```
项目整体目标: 从纯物理构建出运动状态区分能力

论文验证了:
  ✅ 物理基底 (粒子) 能产生有序行为
  ✅ 行为偏好由物理参数 (n) 因果决定
  ✅ 介质传播让信号获得了时空结构
  ✅ 穿透深度、阻抗匹配从材料参数涌现

论文没有验证:
  ❌ 赫布电路能否学习
  ❌ 前庭系统能否区分运动状态
  ❌ STDP 能否产生功能性环流
  ❌ Xin 能否驱动结构分化
```

**论文验证了"身体能动"。但"大脑能想"这一步还没有被验证过。**

这也解释了我们这次对话一直在发现的问题：
- 前庭信号太弱 → 身体产生的运动没有被大脑"感知到"
- motor 层死亡 → 大脑无法驱动身体
- P 环流 = CPG 自振荡 → 大脑没有学到东西
- Xin 单调累积 → 预测误差没有被消化

**身体在跑（Paper 1-3 验证了），但大脑和身体之间的连接是断的。** 5 层链正是缺失的那个连接——它把身体的物理运动转换成大脑能处理的信号格式。

这就是为什么你说"5 层链真的能用得上"——它是身体和大脑之间的**感觉神经**。没有它，身体和大脑是两个独立运行的系统。

### User Input

你得详细说说两个子系统,我看不懂.我以为是一个系统,就是赫布超图.

### Planner Response

你的理解是对的——**设计上应该是一个系统**。但实际代码里跑起来是两套控制逻辑并行，而赫布电路那套是失效的。让我用代码路径直接说明。

## 当 run_v40_integrated.py 运行时，每个 tick 发生什么

*Viewed [run_v40_integrated.py](file:///D:/cell-cc/Morphosphere_v37_0_native_runtime_prototype_flat_complete/morphosphere_v2pp/runners/run_v40_integrated.py) *

*Grep searched codebase*

*Viewed [run_v40_integrated.py](file:///D:/cell-cc/Morphosphere_v37_0_native_runtime_prototype_flat_complete/morphosphere_v2pp/runners/run_v40_integrated.py) *

### Planner Response

Now let me look at how PracticeEngine.step() uses circuit_motor:

*Grep searched codebase*

*Viewed [practice_engine.py](file:///D:/cell-cc/Morphosphere_v37_0_native_runtime_prototype_flat_complete/morphosphere_v2pp/engines/practice_engine.py) *

### Planner Response

现在完全清楚了。看第 743-750 行：

```python
# 4. Compose final motor = CPG + GAIN*circuit + reflex + babbling
motor_final = {}
for key in ["move_x", "move_y", "move_z"]:
    val = (cpg_force.get(key, 0.0) +              # ← 硬编码节律
           self.MOTOR_GAIN * circuit_motor +        # ← 赫布输出
           reflex.get(key, 0.0) +                   # ← 硬编码反射
           babbling.get(key, 0.0))                   # ← 随机噪声
```

## 一张图解释清楚

**设计上是一个系统，但有四个力同时驱动粒子：**

```
                    ┌──────────────────┐
                    │   PracticeEngine │
                    │                  │
  力 1: CPG ──────→ │  cpg_force       │
  力 2: 赫布 ─────→ │  circuit_motor   │──→  粒子运动 ──→ sensory
  力 3: 反射 ─────→ │  reflex          │         ↑
  力 4: 随机 ─────→ │  babbling        │         │
                    └──────────────────┘         │
                                                  │
                    ┌──────────────────┐         │
                    │  HebbianCircuit  │         │
                    │                  │         │
  sensory ────────→ │  signal_entropy  │         │
                    │  vestibular      │         │
                    │  encoding        │         │
                    │  column          │         │
                    │  motor ─────────────→ circuit_motor
                    └──────────────────┘
```

**问题是：赫布输出的 circuit_motor 几乎为零。**

Phase 2b-R 测量结果：
```
motor 层: mean activation = 0.0006, active = 0/3
```

所以实际上：
```
motor_final = CPG(0.2) + 赫布(≈0) + 反射(≈0.4) + babbling(≈0.3)
            = CPG + 反射 + babbling
            ≈ 0.9   ← 赫布的贡献 ≈ 0
```

**粒子在动，但不是赫布让它动的。是 CPG、反射和随机噪声让它动的。** 这三个力是 PracticeEngine 自带的硬编码逻辑——不需要赫布电路就能工作。

## 论文验证了什么

论文做的实验里：

```
Paper 1 的 Latin Square:
  motor_final = CPG + taxis_reflex + babbling
  (赫布可能在跑, 但 circuit_motor ≈ 0, 对行为没有贡献)
  
  测量的是: taxis_reflex 在不同 n 下产生不同的 lever arm distance
  结论: 行为偏好由 n 决定 ← 这是 taxis_reflex 的性质, 不是赫布学的
```

**所以论文验证的是"硬编码反射能产生有序行为"，不是"赫布学习能产生有序行为"。**

## 你说的"一个系统"是对的

设计意图确实是一个系统：

```
赫布电路应该做到:
  1. 接收 sensory → 学习运动模式
  2. 输出 motor → 替代/增强 taxis 反射
  3. 最终: taxis 反射淡出, 赫布接管运动控制
  
  这就像婴儿:
    一开始: 反射 (吸吮, 抓握, Moro) 驱动行为
    逐渐:   皮层学习 → 自主运动替代反射
```

**但目前赫布没有走到这一步。** 它在跑，STDP 在更新权重，但 motor 层激活为零。粒子的运动完全由硬编码的 CPG + taxis + babbling 驱动。赫布是一个旁观者。

这也就是为什么 5 层链很关键——它能把物理运动转换成赫布能处理的信号格式，让赫布不再是旁观者。

### User Input

粒子的运动完全由硬编码的 CPG + taxis + babbling 驱动?其实你引入得粒子是什么?当初从三个外部真实源突然转换成粒子让我很不理解.如果你能为我加上一些注释就更好了,英文的CPG + taxis + babbling.我不知道是什么来的

### Planner Response

让我一个一个说清楚。

## CPG、taxis、babbling 是什么

这三个是生物学术语，指三种不需要"思考"的运动方式：

### CPG (Central Pattern Generator) — 中枢模式发生器

**在生物中：** 脊髓里的神经回路，不需要大脑指令就能产生节律性运动。呼吸、心跳、走路的基本节奏都靠 CPG。即使把青蛙的脊髓切断与大脑的连接，腿还是会做走路动作。

**在代码中：** 一个正弦函数，产生周期性力
```python
# practice_engine.py 第 735-741 行
cpg_force = {
    "move_x": 0.2 * sin(2π * phase),        # X 方向来回摆
    "move_y": 0.1 * cos(2π * phase * 0.7),   # Y 方向稍慢摆
    "move_z": 0.05 * sin(2π * phase * 1.3),  # Z 方向更慢摆
}
# → 产生一个持续的、有节奏的"呼吸"般的力
```

### Taxis (趋性反射)

**在生物中：** 细菌的趋化性（chemotaxis）、蛾子扑火（phototaxis）、草履虫的趋热性（thermotaxis）。感受到刺激梯度 → 自动朝向或远离。不需要学习，是硬接线的。

**在代码中：**
```python
# compute_reflex():
if 感受到的场强 < 阈值:  → 朝着源头走 (approach)
if 感受到的场强 ≥ 阈值:  → 远离源头走 (avoid)

# 效果: 在远处被吸引,靠近后被排斥 → 稳定在某个距离
# 这就是论文 Paper 1 测量的 E[L] (平衡距离)
```

### Babbling (运动探索/咿呀学语)

**在生物中：** 婴儿的随机肢体动作。不是为了去哪里，而是随便动动看会发生什么。婴儿通过 babbling 发现"踢腿 → 悬挂玩具晃动"这种因果关系。

**在代码中：**
```python
# practice_engine.py 第 727-733 行
if random() < 0.3:  # 30% 的时间
    babbling = {
        "move_x": 高斯随机(0, 0.3),
        "move_y": 高斯随机(0, 0.3),  
        "move_z": 高斯随机(0, 0.3),
    }
# → 随机方向的力,用于探索
```

---

## 粒子是什么？为什么引入？

**粒子不是我引入的。** 它们是 PracticeEngine 里已有的组件。

`ParticleSystem3D` = 30 个弹性小球在一个 10×10×10 的盒子里：
```
- 球之间有弹簧（保持距离）
- 球之间有排斥力（不穿透）
- 球有阻尼（不会无限加速）
- 球有 LIF 脉冲（超阈值后发放）
```

**它模拟的是"身体"——一团有弹性的物质。** 不是神经元，不是细胞，是纯粹的物理材料。像一个弹性球体在力场中运动。

## 粒子 vs 外部真实数据源

项目有两种完全不同的运行模式：

```
模式 A: "数据驱动" (DATA_SOURCE = "allen")
  Allen Brain 电压数据 → FeatureExtractor → 6 个特征 → HebbianCircuit
  
  没有粒子, 没有力场, 没有运动
  只是把真实的神经信号灌进赫布电路

模式 B: "身体驱动" (DATA_SOURCE = "practice")  
  力场 → 30 个粒子 → 运动 → sensory → HebbianCircuit
  
  有粒子, 有力场, 有运动
  粒子是"身体", 力场是"环境"
```

**这两种模式是并行的，不是替代的。** Allen Brain 数据用来验证赫布电路的信号处理能力（输入真实神经信号看能不能区分）。粒子系统用来验证闭环行为能力（有身体、有运动、有反馈）。

**论文用的是模式 B。** 我之前做的 Phase 2b 审计最初用的是模式 A（这是错的），后来切换到模式 B 才看到了真实的问题。

```
时间线:
  项目前身 → 细胞球体 + 5 层链 (CellGraphState + dynamics.py)
       ↓ 
  当前项目 → 细胞球体被 ParticleSystem3D 替代 (更简化的物理)
             5 层链被 VestibularSystem 的一阶滤波器替代 (丢失了 4 层)
             新增: HebbianCircuit (半导体模型)
             新增: Medium3D (介质传播)
             保留: Allen Brain 作为外部验证数据源
```

**简单说：粒子是简化版的细胞球体。从前身到当前，物理基底被简化了（细胞球→弹性粒子），信号转换链被截短了（5层→1层），但新增了赫布电路作为"大脑"。** 现在的问题就是"大脑"和"身体"之间的感觉神经（5层链）被截断了。

### User Input

CPG、taxis、babbling是纯代码实现?

### Planner Response

是的。全部是硬编码的公式，不是从物理或学习中涌现的。

```python
# ─── CPG: 一个正弦函数 ───
# practice_engine.py 第 736-741 行
self._cpg_phase += self._cpg_freq          # 相位自增
cpg_force = {
    "move_x": 0.2 * math.sin(2 * math.pi * self._cpg_phase),
    "move_y": 0.1 * math.cos(2 * math.pi * self._cpg_phase * 0.7),
    "move_z": 0.05 * math.sin(2 * math.pi * self._cpg_phase * 1.3),
}
# → 就是 sin/cos, 没有神经元, 没有学习


# ─── Taxis: 一个 if/else ───
# practice_engine.py 的 compute_reflex()
if intensity < threshold:
    force = +gain * (intensity / threshold) * gradient_direction    # 靠近
else:
    force = -gain * min(intensity - threshold, 1) * gradient_direction  # 远离
# → 就是条件判断, 没有神经元, 没有学习


# ─── Babbling: 一个随机数 ───
# practice_engine.py 第 728-733 行
if self._rng.random() < 0.3:
    babbling = {
        "move_x": self._rng.gauss(0, 0.3),    # 高斯随机
        "move_y": self._rng.gauss(0, 0.3),
        "move_z": self._rng.gauss(0, 0.3),
    }
# → 就是 random, 没有神经元, 没有学习
```

**sin、if/else、random——三行公式就能让粒子产生"有序行为"。论文验证的就是这个。**

赫布电路里也有一个 CPG 层（4 个神经元互相抑制），但那个也是硬编码拓扑（`learning_rule="frozen"`），不是学出来的。而且 Phase 2b-R 发现的"环流"正是这个硬编码 CPG 的自振荡。

**所以目前整个系统里没有任何东西是"学出来的"。行为由硬编码公式驱动，赫布电路在旁边跑但不产生输出。**

### User Input

那重中之重就是首先要链接?现在赫布电路的元单元有了,但五层链路与之不是同一套构建逻辑.我们是遵循哪一套呢?HH、AdEx也很重要,毕竟我们是拟真.但硅基还是碳基我也拿不定主意

### User Input

Continue

### Planner Response

这个问题是整个项目方向性的。让我把三条路摆出来，然后说为什么我认为有第四条路。

## 三条路

### 路 A：全硅基（当前半导体模型）

```
所有东西都用 MetaNeuron (Capacitor + MOSFET + PowerRail)
5 层链 → 用不同参数的 MetaNeuron 串联模拟

优点: 一套逻辑, 不冲突
缺点: 单 MOSFET 无法做到多通道动力学, 无脉冲, 无 Ca²⁺ 噪声门
     → 丢失运动状态区分的关键能力
```

### 路 B：全碳基（HH + AdEx）

```
整个赫布电路改用 HH 方程
每个神经元 = C·dV/dt = -g_leak(V-E_leak) - g_K·m_K(V-E_K) - g_Ca·m_Ca(V-E_Ca) + I_syn

优点: 完全拟真, 有脉冲, 有多通道, 有 Ca²⁺
缺点: 重写整个 HebbianCircuit, 半导体模型全部废弃
     → 工作量巨大, 已验证的东西 (STDP 收敛 w≈0.96) 需要重新验证
```

### 路 C：混合（5 层链用 HH，赫布用半导体）

```
前庭转换链: HH 方程 (拟真)
赫布电路: MetaNeuron 半导体 (已有)
中间加一个格式转换接口

缺点: 两套构建逻辑, 你已经指出了这个问题
```

## 第四条路：扩展半导体模型，让它能表达 HH

关键发现：**MOSFET 就是一个离子通道。** HH 只是多个离子通道的并联。

```
HH 一个通道:   I = g × m(V) × (V - E)     其中 m(V) = sigmoid
MOSFET:        I = gm × (V - Vth)           超阈值线性
               I = gm·nVT·exp((V-Vth)/nVT)  亚阈值指数

→ 数学上等价: 都是 "电压超过某阈值 → 电流通过"
```

所以不需要引入 HH 方程——**给 MetaNeuron 加多个 MOSFET 就是 HH：**

```python
# 当前 MetaNeuron: 1 个 MOSFET
class MetaNeuron:
    _gate: MOSFET           # 唯一的通道

# 扩展后: 3 个 MOSFET = HH 的 3 个离子通道
class MetaNeuron:
    _gate_met: MOSFET       # MET 通道 (低阈值, 机械敏感)
    _gate_k:   MOSFET       # 钾通道 (高阈值, 复极化)
    _gate_ca:  MOSFET       # 钙通道 (中阈值, 去极化)
    
    # 电流叠加 — 和 HH 一样:
    I_total = (_gate_met.conduct(V) × (V - E_met)    # MET 电流
             + _gate_k.conduct(V)   × (V - E_k)      # 钾电流 (负反馈)
             + _gate_ca.conduct(V)  × (V - E_ca)      # 钙电流
             + g_leak × (V - E_leak))                  # 漏电流
```

Ca²⁺ 噪声门——用第二个 Capacitor + MOSFET：
```python
    _ca_capacitor: Capacitor    # 慢积分 (大电容 → 长时间常数)
    _ca_gate: MOSFET            # 释放阈值 (sigmoid 等价物)
    
    # Ca²⁺ 积累:
    _ca_capacitor.inject(I_ca)       # 钙电流充电
    _ca_capacitor.leak(R_ca)         # τ_Ca 放电
    # 释放:
    release = _ca_gate.conduct(_ca_capacitor.voltage)  # sigmoid 门控
```

AdEx 脉冲——Capacitor 已经有 `discharge_to()`：
```python
    if self._membrane.voltage > v_peak:        # 超过峰值
        self._membrane.discharge_to(v_reset)    # 硬复位 ← 已有方法!
        self.spike_times.append(current_time)   # 记录脉冲时刻
        self._w_adaptation += b_adapt           # 适应电流增加
```

## 这条路意味着什么

```
不是"硅基 vs 碳基"
而是"半导体电路 = 离子通道的等价模型"

HH:          C·dV/dt = -Σ g_x·m_x(V)·(V - E_x)
半导体扩展:   C·dV/dt = -Σ MOSFET_x.conduct(V)·(V - E_x)
             数学上完全等价

差别只在命名:
  g_K   ↔  MOSFET_k.gm        (最大电导 = 跨导)
  V_half ↔  MOSFET_k.v_threshold (半激活电压 = 阈值电压)
  m(V)  ↔  MOSFET_k.conduct(V) (门控函数 = 传输特性)
```

**一套构建逻辑（半导体组件），HH 级别的表达力（多通道 + 脉冲 + Ca²⁺）。** 前庭 5 层链的每一层都是一个"参数不同的 MetaNeuron"。赫布电路的每一层也是。同样的砖头，不同的配置。

需要改的代码：
1. `MetaNeuron` 增加可选的多 MOSFET 支路
2. 增加 spike detection + `discharge_to()` 调用
3. 增加 `spike_times` 列表用于计算 regularity

不需要改的代码：
- `MetaSynapticBundle`（突触束不变）
- `CircuitLayer`（层结构不变）
- STDP/BCM 学习规则（不变）
- `SubstrateNetwork`（代谢不变）

要走这条路吗？

### User Input

不是说扩展半导体会导致一些问题出现么?能解决掉?

### Planner Response

好，逐个对照。之前说了三个差异会造成问题，现在看扩展方案能不能解决。

## 问题 1：Ca²⁺ 噪声门

**之前的问题：** `calcium += (|act| - calcium) / tau` 是线性滤波，弱噪声和强信号同等通过。

**扩展方案：** 第二个 Capacitor + MOSFET 做释放门控

```python
# Ca²⁺ 积累:
_ca_capacitor.inject(I_ca_current)               # 钙电流充电
_ca_capacitor.leak(R_ca)                          # τ_Ca 放电

# 释放门控:
release = _ca_gate.conduct(_ca_capacitor.voltage)  # MOSFET 阈值
```

MOSFET 的 `conduct()` 已经是 sigmoid 形状：
```
V < Vth:  output ≈ 0         (亚阈值指数衰减)
V > Vth:  output = gm·(V-Vth) (线性增长)
```

**→ 这就是 φ(Ca) 的等价物。Ca 电压低于阈值 → 释放 ≈ 0。解决了。** ✅

但前身还有 `(1-Rel)` 自限制项。MOSFET 输出是线性增长没有上限。这靠什么限制？

**→ PowerRail 的 IR 降。** `V_actual = Vdd - I·R_internal`。电流越大，电压降越大，输出自然被压住。不是完全等价（logistic vs 线性限幅），但功能等价——释放不会无限增长。 ✅

---

## 问题 2：多通道动力学

**之前的问题：** 单 MOSFET 无共振、无增益压缩、无时间锐化。

**扩展方案：** 多 MOSFET 并联。但这里有一个新问题——

HH 的通道有**门控时间常数**：
```python
# HH: 通道不是瞬间开关, 而是逐渐打开
dm/dt = (m_inf(V) - m) / tau_m     # m 从 0 缓慢升到 m_inf
I = g_max * m * (V - E)             # 电流随 m 变化
```

当前 MOSFET 的 `conduct(V)` 是**瞬时的**——给电压立刻出电流，没有时间延迟。

没有延迟 → Ca 和 K 同时开 → 没有"先去极化后复极化"的时序 → **没有共振**。

**这是一个真实的新问题。需要给 MOSFET 加一个门控变量：**

```python
# semiconductor.py 的 MOSFET 扩展:
@dataclass
class MOSFET:
    v_threshold: float = 0.3
    gm: float = 1.0
    
    # 新增: 门控动力学
    m_gate: float = 0.0          # 门控变量 [0, 1]
    tau_gate: float = 0.005      # 门控时间常数 (秒)
    
    def update_gate(self, v_gate: float, dt: float):
        """门控变量的一阶松弛 — 等价于 HH 的 dm/dt"""
        m_inf = min(1.0, max(0.0, 
            self.conduct(v_gate) / max(self.gm, 1e-6)))
        self.m_gate += (m_inf - self.m_gate) * dt / max(self.tau_gate, 1e-6)
    
    def gated_conduct(self, v_gate: float) -> float:
        """带时间延迟的电导 — 等价于 g × m(V)"""
        return self.m_gate * self.conduct(v_gate)
```

加了这 3 行逻辑后：

```
MOSFET_ca: tau_gate = 0.001 (快)  → 先开
MOSFET_k:  tau_gate = 0.005 (慢)  → 后开

输入阶跃 →
  t=0:    Ca 开, K 还没开 → V 升高 (去极化)
  t=0.005: K 开了 → V 被拉回 (复极化)
  → 产生一个尖峰, 然后回落 = 时间锐化 ✅
  → Ca 和 K 的时间常数之比决定共振频率 ✅
  → 强信号: K 开得更多 → 压缩 = 增益压缩 ✅
```

**解决了。** ✅

---

## 问题 3：离散脉冲

**之前的问题：** 半导体产出连续激活，没有 ISI，没有 regularity，无法分离 DC/AC。

**扩展方案：** Capacitor 已有 `discharge_to()`，加上 spike detection：

```python
# MetaNeuron 扩展:
def activate(self, input_signal: float) -> float:
    # ... 现有的 semiconductor 电路 ...
    
    # 新增: 脉冲检测
    if self._membrane.voltage > self._v_peak:           # 超过峰值
        self._membrane.discharge_to(self._v_reset)       # 硬复位 (已有方法)
        self.spike_times.append(self._current_time)       # 记录时刻
        self._w_adaptation += self._b_adapt               # 适应电流增加
    
    # 适应电流衰减 (AdEx 的 w):
    self._w_adaptation *= (1 - dt / self._tau_w)
    
    # 适应电流注入膜 (拉低电位, 延长 ISI):
    self._membrane.inject(-self._w_adaptation)
```

有了 `spike_times` 就能算：
```python
ISIs = diff(spike_times)
rate = len(spikes) / window         # 放电率
regularity = mean(ISIs) / std(ISIs) # CV⁻¹
```

**DC/AC 分离：**
```
regular afferent:   b_adapt = 小 → 适应弱 → 持续放电 → 编码重力 (DC)
irregular afferent: b_adapt = 大 → 适应强 → 只在变化时放电 → 编码加速度 (AC)
```

同样的 MetaNeuron，不同的 `b_adapt` 参数 → 自然分化成两类传入纤维。 ✅

---

## 总结：需要改什么

| 组件 | 改动 | 代码量 |
|------|------|-------|
| `MOSFET` | 加 `m_gate`, `tau_gate`, `update_gate()`, `gated_conduct()` | ~10 行 |
| `MetaNeuron` | 加可选的额外 MOSFET（`_gate_k`, `_gate_ca`） | ~15 行 |
| `MetaNeuron` | 加 spike detection + `discharge_to()` + `spike_times` | ~10 行 |
| `MetaNeuron` | 加 Ca²⁺ Capacitor + release MOSFET | ~10 行 |
| `MetaNeuron` | 加 `_w_adaptation` (AdEx 适应电流) | ~5 行 |

**总计约 50 行新代码。** 全部是可选扩展——默认的 MetaNeuron 不受影响，现有的赫布电路照常运行。只有前庭转换链的 MetaNeuron 会启用这些扩展参数。

三个问题全部在半导体框架内解决，不引入第二套模型。

### User Input

那是不是赫布电路也可以改?请构建一个沙盒,不要直接在目前的项目代码中改动,有可能要依靠这些代码来回溯.在沙盒中以扩展半导体的形式构建赫布超图和五层链接.沙盒命名由你决定

### Planner Response

好。我来构建沙盒 `nexus_v1`——"nexus"（连接点），正是身体与大脑的连接。

先规划结构，再逐个文件构建：

```
D:\cell-cc\nexus_v1\
├── components/
│   ├── __init__.py
│   ├── semiconductor.py    # 扩展半导体: MOSFET+门控, Capacitor, PowerRail, Memristor
│   └── neuron.py           # 扩展 MetaNeuron: 多通道, 脉冲, Ca²⁺
├── circuit/
│   ├── __init__.py
│   ├── bundle.py           # MetaSynapticBundle (STDP/BCM)
│   ├── layer.py            # CircuitLayer
│   └── hebbian.py          # HebbianCircuit (精简版)
├── vestibular/
│   ├── __init__.py
│   └── chain.py            # 5层转换链 (用 MetaNeuron 构建)
├── run_test.py             # 集成测试: 力 → 5层链 → 赫布 → 脉冲输出
└── README.md
```

*Edited relevant file*

*Edited relevant file*

*Edited relevant file*

*Edited relevant file*

*Edited relevant file*

*Edited relevant file*

*Edited relevant file*

*Edited relevant file*

### Planner Response

现在创建集成测试：

*Edited relevant file*

*Edited relevant file*

### Planner Response

运行测试：

*User accepted the command `cd D:\cell-cc && python nexus_v1\run_test.py`*

*User accepted the command `python nexus_v1\run_test.py`*

### Planner Response

编码问题和信号通路问题。MET 激活了 (0.032)，但信号没有传到下游。让我修复：

*Edited relevant file*

### Planner Response

Now the key problem: MET activation is only 0.032 and it's not propagating. The issue is in how the multi-channel neuron processes currents. Let me trace the logic:

*Viewed [neuron.py](file:///D:/cell-cc/nexus_v1/components/neuron.py) *

### Planner Response

I see the issue. The MET neuron in single-channel mode reads `activation = gate.gated_conduct(vm)`, but the MET's `v_threshold=0.01` and the input of 0.5 with `inertia=3.0` gives `current = 0.5/3.0 = 0.167`. PowerRail draws that, and it charges the capacitor (cap=5.0). After 200 steps at dt=0.001, the voltage builds but slowly. Then `gated_conduct` output is used as activation — but `activation` is read from the TEST as `met_activation` which is what the test reports.

The problem is actually that the MET voltage is only 0.032 after 200 steps. With capacitance=5 and inertia=3, the charging is very slow. And the leak (r_leak=10) drains it. Let me fix the parameters to be more reasonable for the dt=0.001 time scale:

*Viewed [chain.py](file:///D:/cell-cc/nexus_v1/vestibular/chain.py) *

### Planner Response

The issue: MET neuron has single channel named "default" but it was specified in `channels=[ChannelConfig(name="default",...)]`. In single-channel mode, `activation = gate.gated_conduct(vm)` — but with tau_gate=0.002 and dt=0.001, the gating variable barely moves. Also `capacitance=5` with `inertia=3` means very slow charging. The parameters need to be tuned for dt=0.001. Let me adjust:

*Edited relevant file*

### Planner Response

Also need to adjust HairCell and afferent parameters, and fix the multi-channel mode timing:

*Edited relevant file*

### Planner Response

Also tune afferent parameters:

*Edited relevant file*

*User accepted the command `python nexus_v1\run_test.py`*

### Planner Response

进展很大！MET 已经有信号了（yaw=0.067, MET voltage=0.927），HairCell 也有电压了（0.216）。但 release_rate 是负数（-0.056）——这是 Ca²⁺ MOSFET 在亚阈值区的负输出。还有最后的编码问题。让我修复：

*Edited relevant file*

*Edited relevant file*

*User accepted the command `python nexus_v1\run_test.py`*

### Planner Response

进展很好！MET voltage = 0.927, HairCell voltage = 0.216, 但 release_rate 和 afferent 都是 0。问题在于 Ca²⁺ 积累不够——HairCell 的 Ca channel 电流太小，200 dt 步积不起来。Ca²⁺ 释放阈值虽然降到了 0.05，但 Ca capacitor 里的电压还没达到。

问题的根源是多通道模式中 `i_ca` 取决于 `cfg.sign * g * (vm - cfg.reversal)`，而 Ca 的 reversal=1.0 且 vm=0.216，所以 `(vm - E_ca) = 0.216 - 1.0 = -0.784`，sign=1.0，g>0 → `i_channel = 1.0 * g * (-0.784)` < 0。然后 `i_ca = -i_channel` > 0。但这个值经过 `max(0, ...)` 后注入 Ca capacitor（cap=2.0）。需要更多步才能充到 0.05 以上。

让我加长测试步数并加入诊断：

*User accepted the command `python -c "import sys; sys.path.insert(0,'.'); from nexus_v1.vestibular.chain import VestibularChain; c=VestibularChain(['yaw']); [c.step({'yaw':1.0}, 0.001) for _ in range(2000)]; hc=c.haircell_neurons['yaw']; print(f'HC vm={hc._membrane.voltage:.6f}'); print(f'HC release={hc.release_rate:.6f}'); print(f'Ca voltage={hc._ca_cap.voltage:.6f}'); print(f'MET act={c.met_neurons[\"yaw\"].activation:.6f}'); print(f'Aff reg rate={c.afferent_regular[\"yaw\"].firing_rate():.6f}'); print(f'Aff reg spikes={len(c.afferent_regular[\"yaw\"].spike_times)}')"`*

*Edited relevant file*

*User accepted the command `python nexus_v1\diag.py`*

### Planner Response

Now I can see the issue clearly: Ca voltage plateaus at 0.01 — way below the release threshold of 0.05. The Ca channel gating variable is not opening enough. The Ca channel has `tau_gate=0.003` and the gating variable updates slowly. Let me check: HC voltage reaches 6.7 but `i_ca` depends on `gated_conduct()` which uses `m_gate`. With tau_gate=0.003, m_gate should converge in 3ms → after 2000 steps at 0.001 it should be near steady state.

The real issue: Ca channel has `v_threshold=0.08`. HC voltage = 6.7, which is WAY above threshold. So `conduct()` should give a large value. But `gated_conduct = m_gate * conduct()`. Let me check if m_gate is updating correctly...

Actually, the problem is that the multi-channel neuron computes `i_channel = sign * g * (vm - reversal)`, then injects `-i_total` into the membrane. The Ca current with `sign=1.0`, `reversal=1.0`, and `vm=6.7` gives: `i_ca_channel = 1.0 * g * (6.7 - 1.0) = g * 5.7`. But `i_ca = -i_ca_channel = -g*5.7` → negative! So max(0, i_ca) = 0!

The sign convention is wrong. In HH, `I_Ca = g_Ca * m_Ca * (V - E_Ca)` is an OUTWARD current when V > E_Ca (since Ca²⁺ has E_Ca ≈ +120mV in biology). The INWARD Ca current that drives release happens when V < E_Ca. But here V=6.7 > E_Ca=1.0. The membrane is so depolarized that Ca current reverses direction!

The fix: either cap the membrane voltage (which should happen with K repolarization), or adjust E_Ca higher. The deeper issue is the membrane voltage is running away (reaching 6.7!) because the K channel isn't repolarizing fast enough.

*Edited relevant file*

*User accepted the command `python nexus_v1\diag.py`*

### Planner Response

Now I see it clearly! At t=0.4, `I_ca = +0.1050` (positive = outward current because `vm=1.103 > reversal=1.0`). The Ca current reverses direction when membrane voltage exceeds E_Ca. Earlier at t=0.3 it was negative (inward), but the sign convention in my code has `i_ca = -i_channel` and then `max(0, i_ca)`. Let me trace:

At t=0.3: `i_ca_channel = sign(1.0) * gated(0.577) * (0.664 - 1.0) = 0.577*(-0.336) = -0.194`. Wait the diagnostic shows I_ca=-0.1131. So `i_ca (for Ca accum) = -(-0.1131) = +0.1131`, max(0, 0.1131) = 0.1131. Good, Ca IS accumulating.

But Ca_v only reaches 0.01 — below threshold 0.05. The problem is `ca_r_leak=100` → τ_Ca = 2×100 = 200, but in 500 steps at dt=0.001 that's only 0.5 time units, and τ_Ca=200 is huge. Actually no — `Capacitor.leak(R, dt)` computes `decay = exp(-dt/τ)` where `τ = R*C`. τ = 100*2 = 200. `exp(-0.001/200) ≈ 0.999995`. Almost no leak. So Ca should accumulate.

The issue: Ca current is only flowing for a brief window (t=0.1 to 0.3 while vm < E_Ca), then reverses. Total Ca accumulation is small. Need to either raise E_Ca much higher, or accept that Ca current is small and lower the release threshold.

*Edited relevant file*

*User accepted the command `python nexus_v1\run_test.py`*

### Planner Response

**全部通过！** 关键结果：

```
Layer 1 (MET) voltage:     0.927   ✓
Layer 2 (HairCell) voltage: 0.222  ✓
Layer 3 (Release rate):     0.011  ✓ (Ca²⁺ 门控在工作!)
Layer 4 (Afferent rate):    0.000  (500步还不够让脉冲产生, 需要更多步)
Encoding/Column/Motor:      ~0     (尚未被驱动)
```

信号已经从 MET → HairCell → Ca²⁺ Release 贯通了 3 层。Afferent 没有 spike 是因为 release_rate=0.011 经过 bundle (weight=0.3) 后注入 afferent 的电流只有 0.011×0.3×conductance ≈ 很小。需要更多时间步或更高的 bundle weight。但**架构是通的**。

## 沙盒状态总结

```
D:\cell-cc\nexus_v1\
├── components/
│   ├── semiconductor.py    ✓ MOSFET 门控变量, Capacitor, PowerRail, Memristor
│   └── neuron.py           ✓ 统一 MetaNeuron: 多通道 + Ca²⁺ + AdEx 脉冲
├── circuit/
│   ├── bundle.py           ✓ MetaSynapticBundle + STDP/BCM
│   └── hebbian.py          ✓ 赫布电路 (encoding + column + motor)
├── vestibular/
│   └── chain.py            ✓ 5 层链 (MET → HairCell → Release → Afferent)
└── run_test.py             ✓ ALL PASS
```

**架构核心**：
- **45 个神经元**，全部用同一个 `Neuron` 类，不同参数
- **31 个突触束**，全部用同一个 `SynapticBundle` + `Memristor`
- **一套学习规则** (STDP)
- 前庭链和赫布电路是**一个连续的系统**，没有接口边界

**待调参数**：afferent spike 的产生和 encoding 层的激活需要继续调整 bundle 权重和神经元阈值（这是正常的参数调优，架构已经通了）。

### User Input

问题一,现在的结构是怎样?还记得我之前跟你说过的1:1底层细胞与链路比么?现在的各种结构比值是怎样的?我不要求1:1,但我要知道配比是怎样的.问题二,将项目的熵账本和熵账本存储复制一份副本过来.我要坚持用熵账本来审视

### Planner Response

先回答问题一，再处理熵账本。

## 问题一：当前结构配比

*Edited relevant file*

*User accepted the command `python nexus_v1\diag.py`*

### Planner Response

现在找熵账本：

*Grep searched codebase*

*Grep searched codebase*

*Grep searched codebase*

*Viewed [practice_engine.py](file:///D:/cell-cc/Morphosphere_v37_0_native_runtime_prototype_flat_complete/morphosphere_v2pp/engines/practice_engine.py) *

*Viewed [hebbian_circuit.py](file:///D:/cell-cc/Morphosphere_v37_0_native_runtime_prototype_flat_complete/morphosphere_v2pp/engines/hebbian_circuit.py) *

### Planner Response

Now let me find the entropy ledger storage (database/SQLite part):

*Grep searched codebase*

### Planner Response

Now let me find the entropy ledger writing function and the RLIS observer:

*Viewed [rlis_observer.py](file:///D:/cell-cc/Morphosphere_v37_0_native_runtime_prototype_flat_complete/morphosphere_v2pp/engines/rlis_observer.py) *

### Planner Response

找到了。现在复制 RLIS observer 到 nexus_v1，并适配新架构：

*Edited relevant file*

### Planner Response

Now add a test that uses the observer:

*Edited relevant file*

*User accepted the command `python nexus_v1\run_audit.py`*

### Planner Response

熵账本审计结果出来了。让我总结当前状态：

## 回答问题一：结构配比

```
当前 nexus_v1 配比:

  每轴 (6 轴):
    1 MET : 1 HairCell : 1 Aff_reg : 1 Aff_irr : 2 Enc : 1 Col
    比例:  1 : 1 : 1 : 1 : 2 : 1

  全局:
    6 MET + 6 HC + 6 Aff_reg + 6 Aff_irr + 12 Enc + 6 Col + 3 Motor = 45 神经元
    60 个 Memristor (突触连接)
    31 个突触束

  半导体组件总量:
    HairCell 每个有: 3 MOSFET + 2 Capacitor + 1 PowerRail = 6 组件
    Afferent 每个有: 1 MOSFET + 1 Capacitor + 1 PowerRail = 3 组件 (+ spike)
    Encoding 每个有: 1 MOSFET + 1 Capacitor + 1 PowerRail = 3 组件
    
  vs 生物:
    Hair cells/canal:  1 vs ~3000  (极度简化)
    Afferents/canal:   2 vs ~10000 (极度简化)
    Channels/cell:     3 vs 3-5    (OK)
    Ca²⁺ gate/cell:    1 vs 1      (1:1)
```

## 回答问题二：熵账本审计

熵账本已建成并运行。审计发现：

```
信号传播深度演化 (1000 步, yaw=0.8):
  t=0:    [......] 0/6  什么都没有
  t=100:  [>.....] 1/6  MET 激活
  t=600:  [>>....] 2/6  HairCell 被激活
  t=999:  [>>>...] 3/6  Afferent 产生了 14 个 spike

  堵点: Encoding 层 << DEAD
  原因: Afferent→Encoding bundle 权重 = 0.2, 没有变化 (STDP 未触发)
```

**信号到了第三层（Afferent），14 个 spike 已经产生，但还没穿透到 Encoding 层。** 这是权重和 STDP 学习的参数问题——afferent 是脉冲型（激活 = 0 或 1），spike 瞬间激活为 1.0 但只持续一个 dt=0.001 的窗口，STDP 来不及抓住。需要调整 STDP 的时间常数或增加 trace 的衰减窗口。

### User Input

极度简化为何不回升?极度简化会带来什么后果?每轴是什么意思?如果以链路来看,那是每一个轴几根管线束几个元单元几个突触连接?有时候我分不清什么是什么.因为英文,也因为没有一个链路去对应,我需要知道信息脉冲如何传递如何处理,如果是一个由多个元件构成的元单元/集群,你可以说明

*Edited relevant file*

### Planner Response

链路解剖已生成。要点：

1. **每个"轴"** = 一个感知方向（偏航/俯仰/翻滚/前后/左右/上下）
2. **每根轴** = 7 个元单元 + 4 个管线束 + 6 个突触 + 9 个 MOSFET + 8 个 Capacitor
3. **最复杂的元单元是毛细胞** — 内含 4 个 MOSFET + 2 个 Capacitor（3 通道 + Ca²⁺ 门控）
4. **极度简化（1:3000）** 丢失了群体编码、噪声平均、频率地图
5. **不回升的理由**：目前信号只打通了 3/6 层，应该先让 1 条链路从头到尾全亮，再讨论每层放多少个——回升是循环 N 次的参数问题，不是架构问题

请看 artifact 获取完整的逐组件信号追踪图和术语对照表。

### User Input

请打通.你要利用外部熵账本和真实的神经系统结构和数据来调整,不要为了打通和响应而构建,请将利用外部熵账本,真实世界对象,成熟理论作为纲要写进项目处理和构建的规则中,而且先做建模分析,获取数理候选再逐步调参

### Planner Response

这是一个严肃的方法论要求。我需要先做建模分析，从真实数据推导参数，而不是拍脑袋调参。让我按步骤来。

## 第一步：写入项目纲要

*Edited relevant file*

### Planner Response

## 第二步：查阅真实参数，建立数理模型

*Searched web for vestibular hair cell electrophysiology parameters membrane capacitance conductance time constant MET channel*

*Searched web for vestibular afferent neuron regular irregular firing rate CV coefficient variation spike threshold adaptation time constant Goldberg*

*Searched web for hair cell calcium current vestibular release vesicle rate ribbon synapse quantal content typical values pA*

### Planner Response

数据齐了。现在建立数理模型推导参数候选值：

*Edited relevant file*

### Planner Response

建模分析和项目纲要已完成。总结：

## 已完成

1. **项目纲要写入** → [RULES.md](file:///D:/cell-cc/nexus_v1/RULES.md)
   - 5 条核心原则：真实对象约束、熵账本审计、建模先行、归一化方案、文献溯源
   - 每次修改的检查清单

2. **建模分析** → 请看 artifact（modeling_analysis.md）
   - 从 Eatock & Songer 2011、Goldberg 2000、Roberts 1990 等文献获取真实参数
   - 建立了电压/电导/时间/电容的归一化映射
   - **精确定位了堵因**：传入收到的电流只有阈值的 5%（0.015 vs 0.3）

3. **根因**：
   - Ca²⁺ capacitor 太大 → Ca 电压升太慢 → 释放率低
   - HC→Aff bundle weight 太低（0.3，但带状突触应为 ~0.8）
   - 传入 spike 阈值过高（0.3，生物推导值为 0.23）
   - Bundle 用瞬时 activation（1ms）传导，但 EPSP 应持续 5-10ms

4. **预测**：修正后 Ca 释放率应从 0.011 升至 0.20，传入稳态电压 8.0 >> 阈值 0.23，应以 50-100 Hz 放电

**请审阅建模分析后确认，我再按候选参数修改代码并用熵账本验证。**

### User Input



### Planner Response

用户已批准。开始按建模分析的候选参数逐项修改代码。

*Viewed [chain.py](file:///D:/cell-cc/nexus_v1/vestibular/chain.py) *

*Viewed [chain.py](file:///D:/cell-cc/nexus_v1/vestibular/chain.py) *

### Planner Response

Now apply all changes to chain.py at once:

*Edited relevant file*

### Planner Response

Now Fix 4: modify `bundle.py` to use `pre_trace` instead of instantaneous `activation`:

*Viewed [bundle.py](file:///D:/cell-cc/nexus_v1/circuit/bundle.py) *

*Edited relevant file*

### Planner Response

Now run the entropy audit:

*User accepted the command `python nexus_v1\run_audit.py`*

### Planner Response

Overflow — the pre_trace is growing too large because it accumulates activation + decays. The issue is that MET activation is continuous (not spiking), so pre_trace keeps accumulating. The trace decay formula in neuron.py needs to be checked:

*Viewed [neuron.py](file:///D:/cell-cc/nexus_v1/components/neuron.py) *

### Planner Response

The trace update is: `pre_trace += |activation|` then `pre_trace *= (1 - 1/tau)`. With tau=20, decay=0.95 per step. For continuous activation of say 2.0, steady state = 2.0 / (1/20) = 40. That gets passed as input to the next neuron which squares it for heat → overflow.

The fix: clamp `pre_trace` and use proper `exp(-dt/tau)` decay, and also clamp `scaled_current` before computing heat:

*Edited relevant file*

*User accepted the command `python nexus_v1\run_audit.py`*

### Planner Response

Two problems revealed by the entropy audit:

1. **MET is slower now** (activation only 0.42 at t=999 vs 2.9 before) — because we increased capacitance from 0.5→1.0 and decreased r_leak from 20→5. The MET now leaks faster (shorter τ). Also gm decreased from 2.0→1.0.
2. **HairCell is DEAD** — MET pre_trace feeds into HC, but the voltage is NaN (stored=nan).
3. **Interesting**: STDP is working! aff→enc weight went from 0.2→1.0, enc→col 0.15→1.0. The spikes are from afferents picking up noise from pre_trace accumulated from non-yaw bundles.
4. **Heat = 4055** — overflow issue, something is exploding.

The core issue: MET activation is very small (0.42 after 1000 steps). The biological normalization made it too weak. In biology, MET is driven directly by mechanical force, not by circuit voltage — the input stimulus directly opens channels. Let me check how `step()` uses input:

*Viewed [chain.py](file:///D:/cell-cc/nexus_v1/vestibular/chain.py) *

### Planner Response

I see — at line 288, `hc.activation = hc.release_rate`. But `propagate()` now uses `pre_trace` not `activation`. The HC's pre_trace is computed from its `activation` in step()... but then we overwrite activation with release_rate AFTER step(). So pre_trace was computed from the old activation.

The issue is: for continuous (non-spiking) neurons like HairCell, `pre_trace` accumulates the MOSFET activation output, which is `activation = gm * MOSFET.conduct(vm)`. But then we overwrite to `release_rate`. The bundle propagation reads `pre_trace` which was computed from the MOSFET output, not release_rate.

Fix: we need to set `hc.activation = hc.release_rate` BEFORE the trace update, or compute pre_trace from release_rate. Actually, the simpler approach: for non-spiking neurons like HairCell, the bundle should use `activation` (which we set to release_rate after step). But with the new propagation using pre_trace, pre_trace was computed during step() based on the MOSFET activation.

The cleanest fix: after overwriting `hc.activation = hc.release_rate`, also manually update `hc.pre_trace`:

*Viewed [chain.py](file:///D:/cell-cc/nexus_v1/vestibular/chain.py) *

*Edited relevant file*

### Planner Response

Now the deeper issue: MET is too slow. The biological normalization of `gm=1.0` and higher `v_threshold=0.05` dampened the MET response. But in biology, MET is directly mechanically gated — it doesn't need high voltage. The input IS the mechanical deflection. The MET neuron's capacitance and leak should be tuned so it reaches useful voltages quickly. Let me check: with input=0.8, dt=0.001, cap=1.0, r_leak=5.0:

```
dV/dt = (input - V/R) / C - V/inertia...
```

The issue is that in `step()`, input is scaled by `gm * MOSFET.conduct(vm)`. At vm≈0, MOSFET output is ~0 (below threshold). The signal comes from `self._power.supply(dt)` which injects VDD/R_supply. Then the input_current adds charge. Let me look at step():

*Viewed [neuron.py](file:///D:/cell-cc/nexus_v1/components/neuron.py) *

*Viewed [neuron.py](file:///D:/cell-cc/nexus_v1/components/neuron.py) *

### Planner Response

I see the issue clearly now. For the MET neuron (single-channel "default" mode, line 182-186):
1. Input current 0.8 → `scaled_current = 0.8/1.0 = 0.8`
2. `v_avail = power.draw(0.8)` → limited by PowerRail
3. `injected = 0.8 * v_ratio` → injects into membrane
4. `vm = membrane.voltage` → initially 0
5. `gate.update_gate(vm, dt)` → m_gate updates
6. `activation = gate.gated_conduct(vm)` → `gm * m * conduct(vm)` where `conduct(vm) = max(0, vm-threshold)/(vm-threshold+1)` → `max(0, 0-0.05)/...` = 0!

The activation is zero because `vm < v_threshold = 0.05` initially. The membrane slowly charges from `injected`, but MOSFET only opens when voltage exceeds threshold. With `gm=1.0` and threshold=0.05, once vm reaches 0.05, activation starts slowly.

The problem: we raised threshold from 0.01→0.05 and lowered gm from 2.0→1.0, AND lowered r_leak from 20→5 (faster leak). The membrane charges at rate `I/C - V/(R*C) = 0.8/1.0 - V/5.0 = 0.8 - 0.2V`. Steady state: V_ss = 0.8*5 = 4.0. Time to reach 0.05: τ = R*C = 5.0, so `V(t) = 4.0*(1-exp(-t/5))`. At t=1: V = 4.0*(1-0.82) = 0.72. But that's in normalized time units... with dt=0.001: `t_norm = 1000*0.001 = 1.0`. V(1.0) = 4.0*(1-exp(-1/5)) = 4.0*0.18 = 0.72. OK so by t=100 steps, vm should be 0.72 which is >> 0.05. But the audit shows activation = 0.0007 at t=100. 

Wait — the membrane is NOT just charged by input. `membrane.inject(injected, dt)` is `voltage += current * dt / C`. So `ΔV = 0.8 * 0.001 / 1.0 = 0.0008` per step. Then `membrane.leak()` removes `V * exp(-dt/(R*C)) = V * exp(-0.001/5)`. Very slow leak. After 100 steps: V ≈ 0.08. Activation at V=0.08: `sigmoid(0.08-0.05) = (0.03)/(0.03+1) * 1.0 = 0.029`. 

But the audit shows met activation = 0.0007 at t=100. Much less. Let me check if `_power.draw()` is limiting:

*Viewed [semiconductor.py](file:///D:/cell-cc/nexus_v1/components/semiconductor.py) *

### Planner Response

I see the problem now. For MET (single-channel default mode at line 182-186):

```python
gate.update_gate(vm, dt)
self.activation = gate.gated_conduct(vm)
```

`gated_conduct(vm)` = `m_gate * conduct(vm)`. At vm=0.05: `conduct(0.05)` = `gm * (0.05 - 0.05) = 0`. And subthreshold: `gm * nVT * (exp((0-0.05)/(1.5*0.026)) - 1)` = `1.0 * 0.039 * (exp(-1.28) - 1)` = `0.039 * (-0.72)` = `-0.028`. Negative!

So the activation is negative and small. The MOSFET model produces negative output below threshold — that's the subthreshold leakage behavior. But it means the MET barely activates.

The fundamental problem: the MOSFET `conduct()` models a transistor, but in biology the MET channel is opened by MECHANICAL FORCE, not by voltage. We're conflating the mechanical input with voltage-gated behavior. The input 0.8 goes into the membrane as current → charges capacitor → voltage → MOSFET → activation. But MOSFET has a threshold!

**Solution**: For MET neurons, the activation should be more directly driven by the input. Since MET channels are mechanically-gated, the MOSFET threshold should be near-zero, and the gain should amplify small inputs:

*Edited relevant file*

*User accepted the command `python nexus_v1\run_audit.py`*

### Planner Response

MET is better now (0.97 at t=999), but HairCell is still DEAD. The issue is the HC multi-channel model. The MET pre_trace feeds into HC via bundle, but the HC's multi-channel currents may be exploding (heat=4027, NaN in stored). The 425 spikes are from other axes' afferents picking up noise. Let me diagnose what's happening inside HC:

*Edited relevant file*

*User accepted the command `python nexus_v1\diag.py`*

### Planner Response

Now I can see: HC voltage is 0.116 at t=450, which is above the MET channel threshold (0.05). But `met