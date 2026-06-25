# Phase 3: 三因子适格迹 — 实施计划

基于 [Phase 3 数理核心与架构理念](file:///D:/cell-cc/cell/other/Phase%203%20%E4%B8%89%E5%9B%A0%E5%AD%90%E9%80%82%E6%A0%BC%E8%BF%B9-%E6%95%B0%E7%90%86%E6%A0%B8%E5%BF%83%E4%B8%8E%E6%9E%B6%E6%9E%84%E7%90%86%E5%BF%B5.md) 的方案文档。

## 核心变更

**LTP 从两因子 STDP 接管为三因子 DA 门控**：

```
之前: dw = η × (pre × post - λ × w)          ← STDP 盲目增长
之后: ltp = η_elig × E(t) × DA(t)             ← 只有 DA 确认才增长
      ltd = pre × post × η_ltd + λ × w        ← LTD + 遗忘保持实时
      dw = energy_scale × (ltp - ltd)
```

## 设计决策

> [!IMPORTANT]
> **适格迹作用范围**：文档指定 `use_eligibility_trace` 为 BundleConfig 开关。
> 当前系统中 STDP 规则用于 `max_maturation == 0`（spine 阶段）的 bundle，
> BCM 用于 `maturation == 1`，cross_axis 用 hebbian_decay。
>
> **计划**：仅对 `effective_rule == "stdp"` 的分支施加三因子改造。
> BCM 和 hebbian_decay 暂不改动（它们的物理定位不同）。
> 这与文档§5.1 一致："learn() 重构 LTP 通路为 η×E×DA"。

> [!WARNING]
> **DA 信号传入路径**：当前 `learn()` 不接收 `da_concentration`。
> 但 `variant_adapter._apply_learning()` 已有 `self.dopamine.concentration` 访问。
> 需要新增 `da_concentration` 参数传入 `learn()`。
>
> **现有 DA 调制不冲突**：当前 DA 通过 `plasticity_gate` 中的 `da_lr_mod` 
> (= `gain_factor()`) 乘性调制学习率。Phase 3 后，STDP 分支的 LTP 将
> 完全由 `E×DA` 控制，`da_lr_mod` 对 STDP 分支不再必要。
> 但对 BCM/hebbian 分支仍保留。

---

## Proposed Changes

### Bundle 核心

#### [MODIFY] [bundle.py](file:///D:/cell-cc/nexus_v1/circuit/bundle.py)

**1. BundleConfig 新增字段** (~L50 区域):

```python
# ── Phase 3: Eligibility trace (three-factor learning) ──
# When enabled, LTP is gated by DA: dw_ltp = η × E(t) × DA(t)
# E(t) = leaky capacitor charged by pre×post co-activation.
# BIO: CaMKII/PKC priming → DA confirmation → AMPA insertion.
# REF: Izhikevich 2007 — "Solving the distal reward problem"
use_eligibility_trace: bool = False
eligibility_tau: float = 300.0    # decay time constant (steps)
eligibility_gain: float = 1.0     # η_elig: E×DA → dw scaling
eligibility_ltd_rate: float = 0.01  # η_ltd: realtime LTD rate
```

**2. SynapticBundle.__init__ 新增状态** (~L130 区域):

```python
# Phase 3: per-synapse eligibility trace (Capacitor dynamics)
# E[i][j] = leaky integrator tracking pre×post co-activation
self._eligibility_traces: List[List[float]] = [
    [0.0] * len(targets) for _ in sources
]
```

**3. learn() 方法修改** — STDP 分支 (~L313-L328):

```python
if effective_rule == "stdp":
    if self.config.use_eligibility_trace:
        # ── Phase 3: Three-factor eligibility trace ──
        # Step 1: Update eligibility trace (Capacitor leak-integrate)
        # E(t+1) = E(t) × (1 - dt/τ) + α × pre_trace × post_act × dt
        post_act = self._get_activity_signal(tgt)
        decay_factor = 1.0 - dt / max(self.config.eligibility_tau, 1.0)
        self._eligibility_traces[i][j] = (
            self._eligibility_traces[i][j] * decay_factor
            + src.pre_trace * post_act * dt
        )
        
        # Step 2: LTP = η_elig × E(t) × DA(t)  (DA-gated)
        ltp = (self.config.eligibility_gain
               * self._eligibility_traces[i][j]
               * da_concentration)
        
        # Step 3: LTD + decay (realtime, no DA gate)
        ltd = (self.config.eligibility_ltd_rate * dt
               * src.pre_trace * post_act)
        decay = self.config.decay_rate_by_stage[0] * m.w * dt
        
        # Step 4: Combine with soft bounds
        dw_raw = ltp - ltd - decay
        if dw_raw > 0:
            dw = dw_raw * (self.config.weight_max - m.w)
        else:
            dw = dw_raw * (m.w - self.config.weight_min)
        
        # Phase 2 + PNN gates (unchanged)
        dw *= plasticity_gate * plasticity * energy_plasticity_scale
        m.apply_dw(dw, self.config.weight_min, self.config.weight_max)
    else:
        # Original two-factor STDP (backward compatible)
        ltp = src.pre_trace * tgt.post_trace
        ...  # existing code unchanged
```

**4. learn() 签名修改**:

```python
def learn(self, dt: float = 1.0, plasticity_gate: float = 1.0,
          fill_fraction: float = 1.0, da_concentration: float = 0.0):
```

`da_concentration` 默认 `0.0` — 未传入时 LTP 完全冻结（安全默认）。

---

### Variant Adapter 集成

#### [MODIFY] [variant_adapter.py](file:///D:/cell-cc/nexus_v1/circuit/variant_adapter.py)

**1. `_apply_learning()` 传入 DA 浓度** (~L1418-1450):

```python
da_conc = self.dopamine.concentration  # 已有的值

# Vestibular → Encoding: PNN × DA (mod) + eligibility DA
for b in self.bundles_vest_to_enc:
    b.learn(dt, plasticity_gate=gate_vest * da_lr_mod,
            fill_fraction=fill, da_concentration=da_conc)

# Encoding → Column: PNN × DA (mod) + eligibility DA  
for b in self.bundles_enc_to_col:
    b.learn(dt, plasticity_gate=gate_enc * da_lr_mod,
            fill_fraction=fill, da_concentration=da_conc)

# Column → Motor: PNN × DA × sync × body + eligibility DA
for b in self.bundles_col_to_motor:
    b.learn(dt, plasticity_gate=gate_col * da_lr_mod * g_sync * body_lr,
            fill_fraction=fill, da_concentration=da_conc)
```

**2. Hebbian Circuit 的 Therm→Motor bundles 启用三因子**:

在 [hebbian.py](file:///D:/cell-cc/nexus_v1/circuit/hebbian.py) (~L542-564) 创建热差分 bundle 时，
新增 `use_eligibility_trace=True`:

```python
b_therm = SynapticBundle(
    config=BundleConfig(
        ...
        use_eligibility_trace=True,   # Phase 3: DA-gated LTP
        eligibility_tau=300.0,
        eligibility_gain=1.0,
        eligibility_ltd_rate=0.01,
    ),
    ...
)
```

> [!IMPORTANT]
> **选择性启用**：只在 `therm→motor` bundle 启用三因子。
> `vest→enc`、`enc→col` 等层间 bundle 保持两因子 STDP。
> 
> **理由**：热差分→电机是"学习趋热性"的关键通路，
> 最需要 DA 门控。其他层的 STDP 是基础特征提取（不需要价值判断）。
> 
> 后续可以逐步扩展到其他 bundle。

---

### 其余 learn() 调用点

#### [MODIFY] [variant_adapter.py](file:///D:/cell-cc/nexus_v1/circuit/variant_adapter.py)

L1078 — DA input bundles:
```python
bundle.learn(dt=dt, fill_fraction=self.energy_store.fill_fraction,
             da_concentration=self.dopamine.concentration)
```

L1450 — Sprouted bundles:
```python
b.learn(dt, plasticity_gate=gate, fill_fraction=fill,
        da_concentration=da_conc)
```

---

## Open Questions

> [!IMPORTANT]
> **Q1：`da_lr_mod` 与 `da_concentration` 的关系**
> 
> 当前 STDP 分支同时受到两个 DA 信号调制：
> - `plasticity_gate` 中包含 `da_lr_mod` = `1 + α_lr × (DA - baseline)` ← 乘性学习率缩放
> - 新增 `da_concentration` 直接作为 `E×DA` 中的 DA ← 门控 LTP
> 
> 这意味着 DA 对 STDP 分支的 LTP 影响变成了 `DA × (1 + 2.0×(DA-0.1))` — 双重调制。
> 
> **建议**：对启用 `use_eligibility_trace` 的 bundle，从 `plasticity_gate` 中
> 移除 `da_lr_mod` 因子（因为 DA 已通过三因子直接门控了 LTP）。
> 但这需要在 `_apply_learning()` 中分支处理。
> 
> **或者**：保持双重调制，视为 "DA 既门控是否学习（三因子），也调制学习速率（调制器）"。
> 这在生物上也合理（DA 浓度既决定学习窗口，也影响学习幅度）。
>
> **我倾向于：先保持双重调制**，在验证实验中观察效果。如果 DA 放大过强
> 导致不稳定，再在 Phase 3.1 中拆分。

---

## Verification Plan

### 验证实验 (EXP-019)

基于文档 §4.1 的三组对比设计，创建 `test_phase3_eligibility.py`:

**实验设计**：
1. 构建最小电路：1 个 source neuron + 1 个 target neuron + 1 个 SynapticBundle（启用三因子）
2. 在 t=20 施加 pre×post 共激活脉冲
3. 三组对比：

| 组 | DA | 预期 Δw |
|----|-----|---------|
| A: 对照 | DA=0 全程 | Δw ≤ 0（仅 LTD+decay） |
| B: 即时 DA | DA=0.5 @ t=20 | Δw > 0（但比 C 弱）|
| C: 延迟 DA | DA=0.5 @ t=220（延迟200步）| Δw > 0（适格迹保留） |

**通过标准**：
- `Δw_A ≤ 0`（无 DA → 无 LTP）
- `Δw_C > Δw_A + 0.02`（延迟 DA 仍有效）
- `Δw_C / Δw_B > 0.3`（200步延迟后仍保留 >30% 效力）

### 回归测试

运行 `test_regression.py` (12 tests) 确认无破坏。

### 集成测试

修改后运行 100k 步完整仿真，监控：
- 热差分 bundle 权重演化（应比 Phase 2 更稳定）
- DA 浓度对权重增长的调制效果
- 能量门控（Phase 2）仍正常工作
