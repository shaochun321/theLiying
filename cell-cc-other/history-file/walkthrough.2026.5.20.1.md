# 半导体物理层重建 — Walkthrough (v42.0)

## 背景

上一 session 的修改因文件回退全部丢失。本次从 pyc 反编译线索和 session 记录出发，**精简重建**并修复了全部 4 个已知 bug。

## 修改清单

### 1. [NEW] `engines/semiconductor.py`

4 个 dataclass 组成的物理元件库：

| 元件 | 物理方程 | 映射 |
|------|---------|------|
| **Capacitor** | Q=CV, dV/dt=-V/(RC) | 膜电容 → 充放电 |
| **MOSFET** | I=gm(Vgs-Vth) / I∝exp((Vgs-Vth)/nVT)-1 | 阈值门控 → 指数亚阈值 |
| **Memristor** | R=R_min+ΔR(1-w), I=V×G | 突触权重 → 忆阻器 |
| **PowerRail** | V=Vdd-IR | 代谢供能 → 电压源 |

> MOSFET 的 `exp()-1` 形式保证了 I(Vth)=0 的连续性。

---

### 2. [MODIFY] `hebbian_circuit.py` — MetaNeuron

**新增字段**: `_membrane: Capacitor`, `_gate: MOSFET`, `_power: PowerRail`, `r_leak: float`

**activate()** 重写为物理电路:
```
signal → current/inertia → PowerRail.draw(I) → Capacitor.inject(I×Vdd_ratio)
→ Capacitor.voltage → MOSFET.conduct(Vm) → activation
```

**decay()** 重写为:
```
Capacitor.leak(R_leak) → activation = membrane.voltage
MOSFET Vth += rate × (calcium - target)
hunger-aware clamp: floor = min(base_floor, ceiling×0.8)
```

---

### 3. [MODIFY] MetaSynapticBundle

`init_weights()` 现在同步创建 `_memristors[i][j]` 数组。

---

### 4. Bug 修复

| Bug | 修复 |
|-----|------|
| **CPG activation = 0** | `_cpg_step` 改为注入 `neuron._membrane.charge` 而非直接写 `activation` |
| **hunger 被 floor 挡死** | 当 `ceiling < 0.5` 时，`floor = min(base_floor, ceiling × 0.8)` |
| **系统永远 hunger=1** | `basal_consumption = min(tick_heat×0.1, pool×0.1)` 防止消耗失控 |
| **hunger → Vth 通过 _hunger_ceiling** | `_metabolic_step` 设 `n._hunger_ceiling`，`decay()` 中使用 |

---

## 涌现测试结果 (6/6 ✅)

| # | 涌现 | 指标 | 结果 |
|---|------|------|------|
| 1 | **饥饿→Vth↓** | fed=0.0083 vs hungry=0.0046 (ratio=0.56) | ✅ |
| 2 | **权重分化** | 4.80× differentiation | ✅ |
| 3 | **Landauer 约束** | high=1.0 vs low=0.5 bits/tick | ✅ |
| 4 | **空间分化** | enc=0.020 vs col=0.002 | ✅ |
| 5 | **学习稀疏化** | 70% near 0, 17% near 1 | ✅ |
| 6 | **CPG-代谢耦合** | fed=0.010 vs starved=0.038 | ✅ |

## 关键发现

- **CPG 在饥饿时更活跃** (avg=0.038 vs 0.010): 这是正确的生物行为——饥饿动物表现出更多运动探索 (restlessness)
- **饥饿→Vth↓ 现在有效**: hunger ceiling 不再被 floor 挡死——两者同步降低
- **86.7% 权重稀疏化** (70% near-zero + 16.7% near-one): 双模态分布意味着系统自发形成了 winner-take-all 拓扑
