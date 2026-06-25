
**文档性质**：架构方案，侧重数理推导与理念阐释，代码仅作示意


## 一、从 Phase 1+2 到 Phase 3 的逻辑递进

### 1.1 已完成的物理基底

| 阶段 | 核心机制 | 解决的物理问题 |
|------|----------|---------------|
| Phase 1 | 差分拓扑（±增益）+ 分级编码 + 阻抗匹配 | 热梯度信号能到达 Motor，方向选择性可被 STDP 学习 |
| Phase 2 | 能量门控对称冻结（`dw *= min(1.0, fill/0.10)`）| 能量枯竭时，已学记忆不被 LTD 风化，也不被盲目 LTP 追尾 |

**Phase 1+2 之后的系统状态**：
- 权重已分化（`w_front > w_back`），能量充足时剪刀差可达 +0.289
- 能量枯竭时权重被冻结，剪刀差锁定在 +0.065
- **但**：权重的固化时机由 STDP 的局部时序决定（pre×post），与全局价值信号（DA）解耦

### 1.2 Phase 3 的定位

**问题**：STDP 是“盲目的”——只要 pre 和 post 共激活，权重就变化。它不区分“这个共激活导致了好的结果”还是“它只是随机噪音”。

**Phase 3 的作用**：引入适格迹（Eligibility Trace）作为**临时标记**，将 LTP 的“写入权限”从局部 STDP 移交给全局 DA 信号。只有 DA 确认的标记才被固化为永久权重变化。

**在积体影子层中的定位**：
- Phase 2 = **突触沉积层**（能量门控，保护已沉积结构）
- Phase 3 = **拓扑门控层**（DA 门控，决定什么被沉积）


## 二、数理核心

### 2.1 适格迹的动力学

**物理载体**：Capacitor（漏积分器）

**数学形式**：
$$E(t+1) = E(t) \cdot \left(1 - \frac{dt}{\tau_{elig}}\right) + \alpha \cdot (pre_trace \cdot post_{act}) \cdot dt$$

**物理含义**：
- pre 和 post 共激活时，`pre_trace × post_act` 产生充电电流，使电容电压 $E(t)$ 上升
- 无共激活时，电容通过 $\tau_{elig}$ 指数放电
- $\tau_{elig} = 300$ 步（≈0.3秒），对应体感信号→DA 释放的传导延迟

**关键性质**：$E(t)$ 不是权重，它只是一个**临时标记**——记录“不久前发生了什么共激活事件”。

### 2.2 三因子更新方程（修正版）

**修正后的完整形式**：

$$ltp = \eta_{elig} \cdot E(t) \cdot DA(t)$$
$$ltd = pre_{trace} \cdot post_{act} \cdot \eta_{ltd}$$
$$decay = \lambda \cdot w$$
$$dw = energy\_scale \times (ltp - ltd - decay)$$

**与未修正版本的区别**：

| | 未修正（加法） | 修正后（接管） |
|---|---|---|
| LTP 来源 | `stdp_update + η×E×DA` | `η×E×DA`（完全由 DA 门控）|
| DA=0 时 | 仍有 stdp_update 在盲目更新 | LTP 完全冻结，只有 LTD+decay |
| 物理意义 | 适格迹是“补丁”| 适格迹是“唯一的 LTP 通道”|

**为什么修正**：如果保留 `stdp_update` 作为加法项，DA=0 时权重仍会被局部 STDP 盲目更新——Phase 1 中的“无主突触癫痫”没有被根治。修正后，LTP 完全由 DA 门控，DA=0 时系统进入“只遗忘不生长”的绝对冷静状态。

### 2.3 双重门控的数学表达

权重变化被两道物理闸门串联控制：

$$dw = \underbrace{\min(1.0, \frac{fill}{0.10})}_{\text{Phase 2: 能量门控}} \times \underbrace{(\eta \cdot E(t) \cdot DA(t) - ltd - decay)}_{\text{Phase 3: DA 门控 LTP}}$$

| 门控 | 信号 | 作用 |
|------|------|------|
| 能量门控（Phase 2）| `fill_fraction` | 能量不足时冻结全部可塑性 |
| 价值门控（Phase 3）| `DA(t)` | DA=0 时 LTP 被冻结，DA>0 时 LTP 被激活 |

**两门串联的物理意义**：能量是“能不能学习”的前提，DA 是“学什么”的指令。两者缺一不可。


## 三、物理理念

### 3.1 为什么 LTP 必须完全由 DA 门控？

在真实神经系统中，多巴胺是“学习信号”而非“执行信号”：

- 突触前和突触后共激活是**局部事件**（毫秒级），它标记“有事情发生了”
- 多巴胺释放是**全局事件**（百毫秒级），它标记“这件事有价值”

适格迹作为中间状态，弥合了这两个时间尺度：
1. 局部事件（pre×post）→ 电容充电（$E(t)$ 上升）
2. 全局价值（DA）→ 门控 LTP（$dw = \eta \times E \times DA$）

**这意味着**：共激活不直接改变权重，它只是在突触上留下一个“等待确认”的标记。

### 3.2 为什么 $\tau_{elig}=300$ 步？

从体感信号（皮肤温度变化）到 DA 释放的传导路径：
- 皮肤热感受器 → 脊髓 relay → 脑干 → VTA（DA 神经元）
- 在生物系统中约 100-500ms
- 本项目 dt=0.001，对应 100-500 步

$\tau_{elig}=300$ 步是这一延迟的物理估计。它使适格迹标记能“等待”DA 信号到达。


## 四、验证理念（三组对比实验）

### 4.1 实验设计的逻辑结构

| 实验组 | pre×post | DA | 预期 |
|--------|----------|-----|------|
| 对照组 | ✅ | ❌ 全程无 | 权重下降（LTD+decay 主导，LTP 冻结）|
| 实验组 A | ✅ | ❌ 全程无 | 同对照组（验证重复性）|
| 实验组 B | ✅ | ✅ 延迟 200 步到达 | 权重显著增长（适格迹标记保留，DA 到达时固化）|

**关键对比**：实验组 B 与 A 的权重差异，就是适格迹 + DA 门控的净效果。

**时间延迟的物理意义**：pre×post 在 $t=20$ 发生，DA 在 $t=220$ 到达。如果适格迹工作正常，$E(220)$ 仍有残余电荷，DA 将其转化为 LTP。这证明系统能“记住”200 步前发生的共激活事件，并将其与延迟到达的 DA 信号绑定。

### 4.2 通过标准

**数学表达**：

$$w_B - w_A > \epsilon$$

其中 $\epsilon$ 由系统初始权重和 STDP 参数决定，通常是初始权重的 2-3 倍。

**物理含义**：DA 延迟到达时权重显著增长，而 DA=0 时权重不增长，证明：
1. 适格迹产生并保留（有因果关系痕迹）
2. DA 门控生效（无 DA 时不固化）
3. 时间延迟被弥合（200 步前的共激活仍被“记住”）

### 4.3 通过后的系统能力提升

| 能力 | 修复前（Phase 2）| 修复后（Phase 3）|
|------|-----------------|-----------------|
| 共激活→立即 LTP | 有（STDP 盲目生长）| 无（需要 DA 确认）|
| 共激活→延迟 LTP | 无（STDP 不跨时间窗口）| 有（适格迹保留标记）|
| DA=0 时的权重稳定性 | 冻结（Phase 2）| 冻结 + LTP 不会盲目增长 |


## 五、轻量代码示意

### 5.1 修改点

| 文件 | 修改 | 行数 |
|------|------|------|
| `bundle.py` | `BundleConfig` 新增 `use_eligibility_trace`, `eligibility_tau`, `eligibility_gain` | ~5 |
| `bundle.py` | `SynapticBundle.__init__` 新增 `self.eligibility_trace = 0.0` | ~3 |
| `bundle.py` | `learn()` 重构 LTP 通路为 `η×E×DA` | ~30 |
| `variant_adapter.py` | 向 `learn()` 传入 `da_concentration` | ~5 |

### 5.2 核心逻辑示意

```python
# 适格迹更新（Capacitor 动力学）
self.eligibility_trace = (
    self.eligibility_trace * (1.0 - dt / eligibility_tau)
    + (pre_trace * post_act) * dt
)

# LTP 完全由 DA 门控
ltp = eligibility_gain * self.eligibility_trace * da_concentration

# LTD + 遗忘（实时，无 DA 门控）
ltd = pre_trace * post_act + decay_rate * weights

# 双重门控会师（Phase 2 + Phase 3）
dw = energy_scale * (ltp - ltd)
weights += stdp_lr * dw * dt
```


## 六、Phase 3 完成后的整体架构状态

### 6.1 三层保护

| 层级 | 机制 | 保护对象 | 门控信号 |
|------|------|----------|---------|
| 外层 | Phase 3 适格迹 | 不确认就不固化 | DA（全局价值信号）|
| 中层 | Phase 1 差分拓扑 | 方向选择性 | 结构路由（无门控）|
| 内层 | Phase 2 能量冻结 | 所有已沉积结构 | fill（能量状态）|

### 6.2 与积体影子层的连接（已确认）

| 沉积子层 | 物理载体 | 门控 |
|----------|---------|------|
| 突触沉积层（Phase 2）| `w_front - w_back` 剪刀差 | 能量冻结 |
| 拓扑门控层（Phase 3）| `eligibility_trace` 标记 → DA 确认 | DA 门控 LTP |

**两者构成了一个完整的沉积逻辑**：
1. 局部 STDP 发现因果关系 → 适格迹标记（Phase 3 前提）
2. DA 确认该标记 → LTP 固化（Phase 3 执行）
3. 能量充足时固化正常进行，能量枯竭时全部冻结（Phase 2 保护）


## 七、三问

**Q1：Phase 3 是新构建还是母本分化？**

新构建。它引入了一个新的物理状态变量（`eligibility_trace`），且 LTP 通路被从两因子 STDP **接管**为三因子 DA 门控。这与 CRI、D2R 同属 L2 补偿组件层，只是实现方式更轻量（状态内嵌于 `SynapticBundle`，而非独立组件类）。

**Q2：它使用什么物理原语？**

Capacitor（漏积分器 `dE/dt = -E/τ + pre×post`）+ 乘法器（`ltp = η×E×DA`）+ Phase 2 能量冻结（`dw *= energy_scale`）。无新原语需要实现。

**Q3：如何证明它有效？**

三组对比实验：实验组 A（DA=0）权重不增长，实验组 B（DA 延迟 200 步到达）权重显著增长。通过标准：`Δw_B - Δw_A` 显著为正（≥ 初始权重的 20%）。