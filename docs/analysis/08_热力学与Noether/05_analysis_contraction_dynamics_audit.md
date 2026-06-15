# 收缩动力学 + 元件库审计

## 1. 收缩的动力学机制

### 核心链路

```
主系统 Xin 张力 ξ_k (每个 bundle 的预测残差)
       │
       ▼
影子神经元 shadow_i 接收 ξ_k 作为外部电流
       │
       ▼
影子神经元通过 RC 电路产生 activation
       │
       ▼
影子 STDP 更新影子 bundle 权重
       │
       ▼
相关 Xin → 相关 activation → STDP 增强跨轴连接
                                STDP 弱化冗余连接
       │
       ▼
"收缩" = 跨轴 bundle 增强 + 轴内冗余 bundle 弱化
```

### 具体机制：为什么 STDP 就是收缩

影子神经元 shadow_yaw_enc 和 shadow_pitch_enc 分别接收 ξ_yaw 和 ξ_pitch 作为输入。

**当头同时转和倾时**：ξ_yaw 和 ξ_pitch 同时非零（都有预测误差），shadow_yaw 和 shadow_pitch 同时激活。

它们之间有一个 shadow bundle（初始权重 0.001）。STDP 检测到**同时激活**：
```
pre_trace(shadow_yaw)  > 0
post_trace(shadow_pitch) > 0
→ STDP LTP: Δw = lr × pre × post × (w_max - w) > 0
→ 权重增加
```

重复多次后，shadow_yaw → shadow_pitch 的权重显著增强。这就是**结构化的收缩**——不是浮点距离变小，而是两个神经元之间的突触链路**真正变强**了。

**同时**，如果 shadow_pitch_enc 和 shadow_pitch_col 之间的 Xin 不相关（pitch encoding 的预测误差模式和 pitch column 的预测误差模式不同步）：
```
pre_trace(shadow_pitch_enc) > 0 但 post_trace(shadow_pitch_col) ≈ 0
→ STDP: 无增强
→ decay 项: Δw = -lr × decay_rate × w < 0
→ 权重衰减
```

**活跃度迁移** = shadow_yaw_enc 通过增强的跨轴 bundle 注入电流到 shadow_pitch_enc，使后者的激活变成"yaw + pitch 混合模式"。原来只代表 pitch 的神经元现在也承载了部分 yaw 信息。

**链路重塑** = 跨轴权重增强 + 冗余轴内权重衰减。环流路径改变。

**能量消耗** = 每次 STDP 权重变化消耗 E_remodel。影子神经元的 energy 在重塑过程中下降。当 energy → 0 时，STDP 停止 → 收缩自然停止。

### 收缩不能无限的三重保障

| 机制 | 限制什么 | 已有？ |
|------|---------|--------|
| **能量耗尽** | energy = 0 → STDP 停止 | ✅ Neuron.energy 已有 |
| **权重饱和** | w → w_max → 乘法软边界使 Δw → 0 | ✅ Bundle.learn() 已有 |
| **PNN 门控** | PNN 成熟 → plasticity_gate → 0 → 学习冻结 | ✅ ECM.pnn_maturity 已有 |

---

## 2. 元件库审计

### 已有元件 vs 影子层需求

| 元件 | 主系统用法 | 影子层需求 | 满足？ |
|------|-----------|-----------|--------|
| `Neuron` | RC电路+MOSFET+能量+trace | 完全相同，只是参数不同（τ 慢 10×） | ✅ 配置即可 |
| `SynapticBundle` | STDP 学习 + memristor 权重 | 完全相同，Xin 驱动而非感觉驱动 | ✅ 直接用 |
| `Memristor` | 连接权重 | 完全相同 | ✅ |
| `Capacitor` | 膜电容 | 完全相同（更大的 C = 更慢的τ） | ✅ |
| `MOSFET` | 通道门控 | 完全相同 | ✅ |
| `PowerRail` | 供电 | 影子层需要独立的供电轨（能量预算更低） | ✅ 配置 vdd |
| `ECM` | 温度+PNN | 影子层需要自己的 ECM（独立温度场） | ✅ create_vestibular_ecm 可复用 |
| `VascularCooling` | 散热+能量递送 | 影子层需要自己的 Vascular（更低的流量） | ✅ 配置即可 |
| `VoltageRegulator` | 代谢恢复 | 影子层需要更低的恢复率 | ✅ 配置 vr_base_rate |
| `Oscillator` | 节律耦合 | 影子层可选（影子有自己的慢节律？） | ✅ 可选 |
| `BindingLayer` | 超边 AND 门 | 影子层不需要独立的 binding（它看的是主系统的 Xin） | N/A |
| `CirculationDetector` | P/R 环流 | 影子层需要自己的环流检测 | ✅ 复用 |

### 缺失的 3 个小件

| 缺失 | 说明 | 添加方式 | 大小 |
|------|------|---------|------|
| **E_remodel** | STDP 权重变化需要消耗神经元能量 | 在 `bundle.learn()` 末尾加 `src.energy -= κ × \|Δw\|` | ~10 行 |
| **Silent Synapse** | 被弱化到 w < w_silence 的 bundle 不删除，标记为 silent + 存权重快照 | BundleConfig 加 `is_silent` flag + snapshot | ~30 行 |
| **Shadow NeuronConfig 预设** | 慢 τ、低能量、低 VR 的影子神经元配置 | 一个工厂函数 `create_shadow_config()` | ~20 行 |

**合计新增 ~60 行，无需修改现有元件接口。**

### 特别注意

`Neuron.step(I_ext, dt)` 已经接受外部电流 `I_ext`。影子层的输入（Xin 张力）直接作为 `I_ext` 注入影子神经元——**不需要任何新的输入接口**。

```python
# 影子层 step 中:
for i, shadow_neuron in enumerate(self.shadow_neurons):
    xin_input = main_bundles[i].config.xin_tension  # 从主系统读取 Xin
    shadow_neuron.step(I_ext=xin_input, dt=dt)       # 直接注入
```

---

## 3. 收缩路径记录

用 Silent Synapse 机制：

```python
# 在 bundle.learn() 中:
if m.w < w_silence and not self.config.is_silent:
    # 进入静默状态
    self.config.is_silent = True
    self.config.silent_snapshot = {
        'w': m.w,
        'tick': current_tick,
        'xin': self.config.xin_tension,
    }
    # 权重归零但 bundle 不销毁
    m.w = 0.0

# 在后续 step 中检查重新激活:
if self.config.is_silent:
    # 如果新 Xin 模式与快照相关 → 唤醒
    if cosine_sim(current_xin_pattern, self.config.silent_snapshot['xin']) > 0.8:
        m.w = self.config.silent_snapshot['w']  # 恢复权重
        self.config.is_silent = False
```

这就是你说的"记录收缩路径"——弃置的链路变成 silent synapse，保留快照，在条件合适时可被唤醒。

---

## 4. 结论

| 问题 | 答案 |
|------|------|
| 收缩的动力学机制 | Xin 驱动 → 影子 STDP → 跨轴增强/冗余衰减 |
| 为什么不能无限收缩 | 能量耗尽 + 权重饱和 + PNN 冻结 |
| 元件母本库是否满足 | **满足 95%**，缺 3 个小件（~60 行） |
| 收缩路径记录 | Silent Synapse（不删除，标记+快照+条件唤醒） |
