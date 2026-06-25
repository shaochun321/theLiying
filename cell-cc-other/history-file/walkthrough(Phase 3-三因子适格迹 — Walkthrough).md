# Phase 3: 三因子适格迹 — Walkthrough

## 变更概览

将 STDP 的 LTP 通路从盲目的两因子（pre×post）接管为 DA 门控的三因子机制：

$$dw_{ltp} = \eta_{elig} \times E(t) \times DA(t)$$

其中 $E(t)$ 是漏积分电容器（适格迹），在 pre×post 共激活时充电，以 $\tau_{elig}=300$ 步衰减。

---

## 修改文件

### [bundle.py](file:///D:/cell-cc/nexus_v1/circuit/bundle.py)

**BundleConfig 新增字段** (~L93-108):
- `use_eligibility_trace: bool = False` — 开关
- `eligibility_tau: float = 300.0` — 衰减时间常数
- `eligibility_gain: float = 1.0` — E×DA → dw 缩放
- `eligibility_ltd_rate: float = 0.01` — 实时 LTD 速率

**SynapticBundle.__init__** (~L153-163):
- 条件分配 `_eligibility_traces: List[List[float]]`
- 启用时：`sources × targets` 的二维零矩阵
- 未启用时：`None`（零开销）

**learn() 签名** (~L260):
- 新增 `da_concentration: float = 0.0` — 默认 0.0 = LTP 冻结

**learn() STDP 分支** (~L320-380):
- `use_eligibility_trace=True` 时：
  1. E(t+1) = E(t)×(1-dt/τ) + pre_trace×post_act×dt
  2. ltp = η×E(t)×DA(t)
  3. ltd = η_ltd×dt×pre×post + decay×w×dt
  4. dw = soft_bounds(ltp - ltd - decay) × gates
- `use_eligibility_trace=False` 时：原始两因子 STDP 不变

---

### [variant_adapter.py](file:///D:/cell-cc/nexus_v1/circuit/variant_adapter.py)

**_apply_learning()** (~L1422-1456):
- 新增 `da_conc = self.dopamine.concentration`
- 所有 `learn()` 调用增加 `da_concentration=da_conc`
- 覆盖：vest→enc、enc→col、col→motor、sprouted、DA input bundles

---

### [hebbian.py](file:///D:/cell-cc/nexus_v1/circuit/hebbian.py)

**Therm→Motor bundles** (~L559-567):
- 启用 `use_eligibility_trace=True`
- 设置 τ=300, gain=1.0, ltd_rate=0.01
- 这是趋热性学习的关键通路

---

## 验证结果

### EXP-019: 三组对比实验

| 组 | DA 条件 | Δw | DA 贡献 |
|----|---------|-----|---------|
| A (对照) | DA=0 全程 | -0.013 | 0 (基线) |
| B (即时) | DA=0.5 @ t=20 | +0.041 | +0.054 |
| C (延迟) | DA=0.5 @ t=220 | +0.002 | +0.015 |

**通过标准**:
- C1: Δw_A ≤ 0 → -0.013 ✅
- C2: Δw_C > Δw_A + ε → +0.015 ✅  
- C3: DA_effect_C / DA_effect_B > 0.2 → 0.283 ✅

**物理验证**:
- E(220)/E(25) = 0.5215 ≈ exp(-195/300) = 0.522 ✅ 适格迹衰减符合电容动力学

### 向后兼容

两因子 STDP (`use_eligibility_trace=False`) 不受影响：
- DA=0 下仍产生权重变化 ✅
- `_eligibility_traces` 不分配（None）✅

### 回归测试

11/12 passed。唯一失败 `test_encoding_selectivity` 是 pre-existing 问题
（编码层温度神经元 EMA=1.135 > 0.5），与 Phase 3 无关。

---

## 架构状态

Phase 3 后，权重变化被三层串联门控：

| 层 | 机制 | 门控信号 |
|----|------|---------|
| 外层 | Phase 3 适格迹 | DA（全局价值）|
| 中层 | Phase 1 差分拓扑 | 结构路由 |
| 内层 | Phase 2 能量冻结 | fill（能量状态）|
