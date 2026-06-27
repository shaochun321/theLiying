# STDP冷启动实验 — 实现方案 批次2：补丁C（卵黄囊）+ 补丁D（DA微分锚定）

> 前置：批次1问题清单中，补丁C三问已完整，补丁D仅缺 η_da（ISSUE-03）。
> 本批次给出完整代码规格，η_da 用占位符 `ETA_DA_TBD` 标注。
> 写作日期：2026-06-25

---

## Patch C：YolkSac（卵黄囊）

### 三问核查

**Q1 生物对应物**
> BIO: 卵黄囊（yolk sac / vitellus）——脊椎动物胚胎发育期的唯一能量来源。
> 母体在受精卵中预置固定量的脂质/蛋白质储备，胚胎依靠此储备完成早期发育（运动、神经回路建立）直到外部进食能力建立。
> 关键特性：一次性赋予（创建时），不可从外部补充，耗尽后结构消失。
> REF: Davidson EH (2006) *The Regulatory Genome*, Ch.3. / 标准发育生物学教材。

**Q2 物理结构**
```
YolkSac（TYPE:BIO）
  ├── 原语：Capacitor（初始充能 = yolk_initial_level，自然放电）
  ├── 单向输出端：→ EnergyStore.deposit()
  └── 无输入端（不可补充）

每步：
  YolkSac._level -= λ_yolk × dt        # 线性放电
  if YolkSac._level > 0:
      EnergyStore.deposit(λ_yolk × dt)  # 单向转移
```

**Q3 参数依据**

| 参数 | 值 | 推导来源 |
|------|-----|---------|
| `yolk_initial_level` | 200.0 单位 | 实验文档§8：fill_yolk_equivalent=0.2，EnergyStore.capacity=1000 → 0.2×1000=200 |
| `lambda_yolk` | 0.002 单位/步 | 目标持续时长100k步：200 / 100,000 = 0.002/步（线性放电模型） |
| `dt` 基准 | 0.001s（1ms） | CLAUDE.md 约定 dt=0.001 |

验证：0.002 × 100,000 = 200 ✓ 在100k步时卵黄囊耗尽。

---

### 文件位置

**新建文件**：`cell-cc-other/nexus_v1/components/yolk_sac.py`

不修改任何现有文件。集成点仅在 `VariantCircuit.__init__` 和 `VariantCircuit.step()` 中添加两处调用。

---

### 接口规格

```python
# TYPE:BIO
# Yolk sac: fixed maternal energy reserve for embryonic bootstrap.
# One-way, non-replenishable. Maps to vitellus in vertebrate development.
# REF: Davidson 2006, The Regulatory Genome, Ch.3

from dataclasses import dataclass
from nexus_v1.components.semiconductor import Capacitor

@dataclass
class YolkSacConfig:
    initial_level: float = 200.0   # EXP: 0.2 × EnergyStore.capacity
    lambda_yolk: float = 0.002     # EXP: 200 units / 100k steps target

class YolkSac:
    """TYPE:BIO — Non-replenishable embryonic energy reserve (Capacitor).

    Discharges at constant rate λ_yolk into EnergyStore.
    Once depleted, transfer stops. Cannot be refilled.
    """

    def __init__(self, config: YolkSacConfig | None = None):
        self.config = config or YolkSacConfig()
        self._level: float = self.config.initial_level
        self._depleted: bool = False
        self._total_transferred: float = 0.0

    def step(self, energy_store, dt: float = 0.001) -> float:
        """Transfer λ_yolk × dt to EnergyStore. Returns amount transferred."""
        if self._depleted:
            return 0.0
        transfer = self.config.lambda_yolk  # per-step units, do NOT multiply by dt
        if self._level <= transfer:
            transfer = self._level
            self._depleted = True
        self._level -= transfer
        self._total_transferred += transfer
        energy_store.deposit(transfer)
        return transfer

    @property
    def level(self) -> float:
        return self._level

    @property
    def is_depleted(self) -> bool:
        return self._depleted

    @property
    def fraction_remaining(self) -> float:
        return self._level / self.config.initial_level
```

---

### VariantCircuit 集成点

`circuit/variant_adapter.py` 中添加两处，不修改任何现有逻辑：

**`__init__`（在 EnergyStore 实例化之后）：**
```python
from nexus_v1.components.yolk_sac import YolkSac, YolkSacConfig
self.yolk_sac = YolkSac()
```

**`step()` / `_tick_energy()`（在 EnergyStore.tick() 之前）：**
```python
self.yolk_sac.step(self.energy_store, dt)
```

**监控状态输出（可选，加入 metrics）：**
```python
ms.yolk_level = self.yolk_sac.level
ms.yolk_depleted = self.yolk_sac.is_depleted
```

---

### 边界条件

- `deposit()` 上游已有 `max_deposit_per_step` 限制（EnergyStore:141），λ_yolk×dt=0.002×0.001=0.000002 远低于上限 0.12，不会触发截断。
- EnergyStore 已满时：`deposit()` 内部会截断（capacity 上限），多余能量丢失——这符合生物真实性（卵黄过剩时部分降解）。
- 完全耗尽后 YolkSac 不产生任何输出，EnergyStore 恢复纯靠进食。

---

## Patch D：DADifferentialGate（DA微分锚定）

### 三问核查

**Q1 生物对应物**
> BIO: 腹侧被盖区（VTA）多巴胺神经元的奖励预测误差（RPE）信号。
> Schultz et al. (1997) *Science* 275:1593-1599："A neural substrate of prediction and reward"
> 核心发现：VTA DA神经元对**意外的奖励**（即奖励的正向变化）有爆发式激活，
> 对**持续的奖励**（无变化）无响应，对**预期奖励未到达**（负变化）有抑制。
> 数学形式：DA ∝ max(0, d(reward)/dt)——正向变化率激活，零变化和负变化不激活。
> 本实现：reward = EnergyStore.fill（代谢能量水平 = 生存相关奖励）。

**Q2 物理结构**
```
EnergyStore.fill(t)
    ↓
DADifferentialGate（TYPE:BIO|SEMI）
    ├── Capacitor：保存 fill_{t-1}（一步延迟）
    ├── 减法器：Δfill = fill_t - fill_{t-1}
    └── MOSFET（半波整流）：max(0, Δfill) × η_da
    ↓
DA神经元驱动电流（替换 circulation_proportion 的绝对偏差输出）
```

**Q3 参数依据**

| 参数 | 值 | 推导来源 |
|------|-----|---------|
| `eta_da` | **ETA_DA_TBD** | 需标定（见ISSUE-03）。量级估计：Δfill正常范围≈0.0001/步（基础代谢），进食时≈0.108/步；目标DA激活幅度需对比旧系统基线。 |
| `threshold` | 0.0 | MOSFET 门槛：仅正向变化触发，零变化和负变化截止 |
| `fill_prev` 初始值 | `EnergyStore.initial_fill = 0.5 × capacity / capacity = 0.5` | 以fill_fraction表示 |

**η_da 标定方法**（ISSUE-03解决方案草案）：
1. 在旧DA系统（circulation_proportion）下运行1k步，记录 `dopamine.concentration` 均值 μ_old
2. 在新系统下调整 η_da 使得进食事件后 `dopamine.concentration` 达到同等量级
3. 记录为 `# EXP-CAL-DA: η_da=X.X, target μ=Y.Y`

---

### 文件位置

**新建文件**：`cell-cc-other/nexus_v1/components/da_differential_gate.py`

**现有文件的修改**：`circuit/variant_adapter.py` 中将 DA 驱动调用切换为新组件（约2-3行）。不修改 `circulation_proportion.py` 本身。

---

### 接口规格

```python
# TYPE:BIO|SEMI
# VTA dopamine reward prediction error gate.
# DA fires on positive energy rate-of-change, not absolute level.
# BIO: Schultz et al. 1997, Science 275:1593-1599

from dataclasses import dataclass

@dataclass
class DADifferentialConfig:
    eta_da: float = 1.0        # ETA_DA_TBD — requires calibration (ISSUE-03)
    threshold: float = 0.0     # MOSFET cutoff: only positive delta passes
    clip_max: float = 5.0      # prevent runaway on sudden large deposits

class DADifferentialGate:
    """TYPE:BIO|SEMI — Reward prediction error gate for dopamine drive.

    Computes DA signal from positive rate-of-change in energy fill.
    Implements: DA(t) = max(0, eta_da × Δfill / dt)
    where Δfill = fill_fraction(t) - fill_fraction(t-1).

    Replaces absolute-deviation DA trigger in circulation_proportion.py.
    BIO: VTA RPE signal, Schultz et al. 1997.
    """

    def __init__(self, config: DADifferentialConfig | None = None,
                 initial_fill: float = 0.5):
        self.config = config or DADifferentialConfig()
        self._fill_prev: float = initial_fill
        self._da_output: float = 0.0

    def step(self, fill_fraction: float, dt: float = 0.001) -> float:
        """Compute DA drive from energy rate-of-change.

        Returns non-negative DA current proportional to energy improvement.
        """
        delta_fill = fill_fraction - self._fill_prev
        self._fill_prev = fill_fraction

        raw = self.config.eta_da * delta_fill / max(dt, 1e-9)
        # MOSFET half-wave rectification: gate closed on zero/negative delta
        self._da_output = min(max(0.0, raw - self.config.threshold),
                              self.config.clip_max)
        return self._da_output

    @property
    def da_output(self) -> float:
        return self._da_output
```

---

### VariantCircuit 集成点

**`__init__`（在 EnergyStore 实例化之后）：**
```python
from nexus_v1.components.da_differential_gate import DADifferentialGate, DADifferentialConfig
self.da_gate = DADifferentialGate(
    initial_fill=self.energy_store.fill_fraction
)
```

**`step()` 中 DA 驱动段（替换旧的 circulation 调用）：**

旧代码（`variant_adapter.py:836` 附近）：
```python
# 旧：基于绝对偏差的DA驱动（circulation_proportion）
da_drive = self._circulation.step(self.energy_store, ...)
```

新代码（直接替换该调用）：
```python
# NEW Patch D: DA fires on energy improvement rate (RPE signal)
# BIO: Schultz 1997, replaces absolute-deviation trigger
da_drive = self.da_gate.step(self.energy_store.fill_fraction, dt)
```

> **注意**：`circulation_proportion.py` 文件本身**不修改**。
> 仅在 `VariantCircuit.step()` 中切换调用源。
> 若 `_circulation` 对象还有其他输出（非DA部分）需单独核查，避免副作用。

---

### 已知风险

**风险1：冷启动期DA沉默**
- 系统刚启动时 fill 从0.5开始稳定，`Δfill ≈ 0`，DA=0
- 无DA → STDP不工作 → 行为不涌现
- 对策：卵黄囊（Patch C）持续向EnergyStore注入，保证 `Δfill > 0`，触发小量DA
- 卵黄释放量：`λ_yolk × dt = 0.002 × 0.001 = 2e-6/步`（微小但非零）
- 若此量级不足以通过 η_da 放大达到DA阈值，需调整 η_da（ISSUE-03的核心）

**风险2：进食脉冲致DA爆发**
- 单次进食：deposit ≈ 0.12 × 0.9 = 0.108单位，若capacity=1000则 Δfill_fraction ≈ 1.08×10⁻⁴
- 若 η_da 过大，此脉冲致DA过饱和
- `clip_max=5.0` 提供保护，但 η_da 标定时需考虑此场景

**风险3：DA系统旧结构残留**
- `circulation_proportion.py` 若还被其他路径引用（非DA部分），需确认切换后无遗漏
- **实施前操作**：`grep -n "circulation" variant_adapter.py` 列出所有引用点，逐一评估

---

## 两项补丁的组合效应

YolkSac（C）+ DADifferentialGate（D）形成一个自洽的能量-奖励子系统：

```
卵黄囊持续释放 → EnergyStore.fill 缓慢上升 → Δfill > 0
                                                ↓
                                        DADifferentialGate
                                        输出微小但非零DA
                                                ↓
                                        STDP调制开始工作
                                        （学习窗口打开）

进食事件 → EnergyStore.fill 快速上升 → 大 Δfill → DA脉冲
                                                ↓
                                        强化当前行为
                                        （趋热学习强化）
```

这是两项补丁联合设计的核心意图：卵黄囊提供"基础电流"维持STDP活跃，进食事件提供"强化脉冲"巩固有效策略。

---

*下一批次：批次3文档将给出补丁A（AGC→Langevin接入）和补丁B（Binding时间卷积窗口）的完整规格。*
*前提：ISSUE-01（σ₀数值）和ISSUE-05（BindingCell修改策略）需先确认。*
