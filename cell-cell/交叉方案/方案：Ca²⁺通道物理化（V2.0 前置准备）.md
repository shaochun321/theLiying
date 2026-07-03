# 方案：Ca²⁺通道物理化（V2.0 前置准备）

**日期**：2026-07-03
**性质**：组件级方案，非主线重构
**关联**：HC-008 兼容性验证（Phase 5）、体感重构（V2.0）、规模泛化 Phase B
**状态**：待执行（体感重构间隙启动）


## 一、核心理念动机

### 1.1 为什么要物理化 Ca²⁺ 通道

HC-008 修复将前庭毛细胞的 `pre_trace` 改为 Ca²⁺ 释放率信号，验证了生物学机制的兼容性。但它当前以“生化黑盒”形式存在于神经元内部——直接在 Python 层赋值，不经过物理原语，不被 Noether 探针审计，无法追溯能量消耗。

物理化的本质是：**将电压门控离子通道（CaV1.3）从 Python 赋值升级为可审计的物理组件——与 MOSFET、Capacitor、PowerRail、Memristor 同级。**

| 当前状态 | 物理化后 |
| :--- | :--- |
| `hc.activation = release_rate`（直接赋值）| `I_Ca = g_Ca(V_m) × (V_m - E_Ca)`（欧姆定律）|
| Ca²⁺ 信号不可追踪 | 全链路可审计（I_Ca, V_ca, release_rate）|
| 参数无物理来源 | 文献锚定（V_half, P_open, τ）|
| 能量消耗不可见 | I²R 焦耳热计入 P_T |

### 1.2 为什么现在准备

- **不紧急**：Phase 5 已验证 HC-008 与多源导航兼容，热趋性由体感驱动，前庭 Ca²⁺ 细节不影响当前行为
- **正确**：这是项目从“黑箱生物化学”走向“可审计物理组件”的自然步骤
- **时机合适**：体感重构和规模泛化之间有间隙，Phase A 可在此时段启动而不阻塞主线


## 二、问题背景

### 2.1 HC-008 的当前状态

`hc.activation = hc.release_rate`，其中 `release_rate` 由 Ca²⁺ 浓度驱动。在正常输入下，Ca²⁺ 通道的二次方响应使 `release_rate≈0`。Phase 5 已确认此状态与系统行为兼容。

### 2.2 但这不是可审计的状态

| 问题 | 表现 |
| :--- | :--- |
| 直接赋值绕过物理原语 | `activation` 不经过 MOSFET 通道 |
| 能量不可追踪 | Noether 探针看不到 Ca²⁺ 电流的能量消耗 |
| 参数无锚点 | `release_gain`、`ca_release_threshold` 无文献来源 |
| 不可扩展 | N=3 时每个毛细胞实例的 Ca²⁺ 状态无法独立审计 |


## 三、方案设计

### 3.1 核心设计：Ca²⁺ 通道作为 MOSFET 特化

CaV1.3 通道本质上是**电压门控电流源**，是 MOSFET 原语的自然特化。

**转换链**：
```
膜电位 V_m
    ↓（电压门控）
CaV1.3 电导 g_Ca(V_m)
    ↓（欧姆定律）
Ca²⁺ 电流 I_Ca = g_Ca × (V_m - E_Ca)
    ↓（RC 积分）
钙缓冲 V_ca（电容 + 漏电）
    ↓（单调映射）
release_rate
```

### 3.2 参数来源

| 参数 | 值 | 来源 | 置信度 |
| :--- | :--- | :--- | :--- |
| V_half（激活半程电压）| -41 mV | Bao et al. 2003 | 高 |
| k（斜率因子）| 5 mV | 玻尔兹曼拟合 | 高 |
| E_Ca（反转电位）| 50 mV | 物理常数 | 极高 |
| g_max（最大电导）| 2.0 nS | 单通道电导×通道密度 | 中等 |
| τ_ca（钙清除时间常数）| 50 ms | 钙缓冲动力学 | 中等 |
| release_gain | 1.0 | 归一化映射 | 校准值 |
| release_threshold | 0.01 | 当前值保留 | 校准值 |

### 3.3 新组件规格

**CalciumChannel（电压门控 Ca²⁺ 通道）**：

```python
class CalciumChannel:
    """CaV1.3 voltage-gated calcium channel (physical component)."""
    def __init__(self):
        self.g_max = 2.0  # nS
        self.E_Ca = 50.0  # mV
        self.V_half = -41.0  # mV
        self.k = 5.0  # mV
        
    def conductance(self, V_m):
        return self.g_max / (1 + exp(-(V_m - self.V_half) / self.k))
    
    def current(self, V_m):
        return self.conductance(V_m) * (V_m - self.E_Ca)
```

**CalciumDynamics（Ca²⁺ 缓冲 RC 积分器）**：

```python
class CalciumDynamics:
    """Ca²⁺ accumulation and clearance (RC integrator)."""
    def __init__(self):
        self.C_ca = 10.0  # 钙缓冲电容
        self.R_ca = 100.0  # 钙清除电阻
        self.V_ca = 0.0
        
    def step(self, I_Ca, dt):
        dV = (I_Ca - self.V_ca / self.R_ca) / self.C_ca * dt
        self.V_ca += dV
        return self.V_ca
```


## 四、实施路径

### Phase A（立即，在体感重构间隙执行）

**目标**：新增 Ca²⁺ 通道组件，不接入电路，独立验证。

| 步骤 | 任务 | 工作量 | 验收 |
| :--- | :--- | :--- | :--- |
| A1 | 新增 `CalciumChannel` 类 | 1h | 单元测试通过 |
| A2 | 新增 `CalciumDynamics` 类 | 1h | 单元测试通过 |
| A3 | 文献参数注释注入 | 1h | 包含 BIO/REF 来源 |
| A4 | 单元测试（恒定 V_m 下的 I_Ca、RC 响应）| 1h | 数值与预期一致 |
| A5 | 回归测试 | 0.5h | 21/21 PASS |

**总工作量**：4-6 小时，可在体感重构的测试/等待间隙完成。

### Phase B（远期，hc_to_aff 解冻时）

**目标**：将 HairCell 中的 Ca²⁺ 机制替换为独立组件。

| 步骤 | 任务 | 前提 |
| :--- | :--- | :--- |
| B1 | 将 HairCell 中的 release_rate 改为 CalciumDynamics 输出 | hc_to_aff 解冻决策 |
| B2 | 从 HairCell 移除直接赋值 | 步骤 B1 完成 |
| B3 | 验证前庭 STDP 行为 | 回归测试通过 |

**Phase B 不进入当前 Sprint**，仅在以下条件下启动：
- 需要 `hc_to_aff` 解冻（HC-driven STDP）
- 规模泛化 Phase B 完成且行为稳定


## 五、与现有架构的衔接

| 维度 | 关系 |
| :--- | :--- |
| 与体感重构 | **正交**——在体感重构间隙启动 Phase A，不阻塞主线 |
| 与 V2.0 规模泛化 | **准备性工作**——Phase B 在 N=1→3 扩展时完成接入 |
| 与现有神经原语 | **兼容**——CalciumChannel 复用 ChannelConfig 接口模式 |
| 与 TSI/Noether | **增强**——Ca²⁺ 电流的 I²R 耗散可被审计 |
| 与 HC-008 | **保留**——Phase 5 已验证兼容，物理化后行为应保持一致 |


## 六、验收标准

| 阶段 | 标准 | 说明 |
| :--- | :--- | :--- |
| Phase A | 单元测试全部通过 | CalciumChannel 正确输出 I-V 曲线 |
| Phase A | 21/21 回归 PASS | 新组件不影响现有行为（未接入电路）|
| Phase B | hc.activation 由物理组件驱动 | 直接赋值被移除 |
| Phase B | 前庭行为与 Phase 5 一致 | 回归测试及短程验证 |


## 七、总结

| 问题 | 回答 |
| :--- | :--- |
| 何时执行？ | **Phase A**：体感重构间隙立即启动（4-6 小时）；**Phase B**：hc_to_aff 解冻时 |
| 是否阻塞体感重构？ | ❌ 不阻塞——Phase A 正交，可并行 |
| 是否阻塞 V2.0？ | ❌ 不阻塞——Phase B 在规模泛化时完成接入 |
| 风险是什么？ | 低——Phase A 新增组件不接入电路，回归测试可验证 |