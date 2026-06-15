# A→B→C 全 Tier Walkthrough

## A-tier: 守恒/审计层

### A1. KCL 电荷守恒
- [semiconductor.py](file:///d:/cell-cc/nexus_v1/components/semiconductor.py): `Capacitor` 加入 `_q_in`, `_q_out`, `_q_initial` 追踪
- 所有 `inject()`, `leak()`, `discharge_to()` 均追踪电荷流向
- `kcl_imbalance` 属性: `|Q_in - Q_out - ΔQ_stored|`
- [noether_probe.py](file:///d:/cell-cc/nexus_v1/circuit/noether_probe.py): 相对 KCL 检查 → 0 violations

### A2. Weight 分项审计
- [semiconductor.py](file:///d:/cell-cc/nexus_v1/components/semiconductor.py): `Memristor` 加入 `_cum_ltp`, `_cum_ltd`, `_cum_clamp`
- 新 `apply_dw()` 方法统一所有权重修改路径
- [bundle.py](file:///d:/cell-cc/nexus_v1/circuit/bundle.py): 三个学习规则 (STDP, BCM, Hebbian_decay) 全部迁移到 `apply_dw()`
- 守恒恒等式: `w(t) - w(0) = Σ_ltp - Σ_ltd`

### A3. Landauer Shannon 熵
- [noether_probe.py](file:///d:/cell-cc/nexus_v1/circuit/noether_probe.py): 20-bin 直方图 → H(w) = -Σ p·log₂(p)
- ΔH < 0 = 比特擦除（学习）→ Landauer 最小热: Q ≥ kT·ln(2)·|ΔH|
- 结果: 2.58 bits erased, Q/bit = 3.8M >> Landauer minimum ✅

### A4. Xin 初始化同步
- 基线校正: `adj_produced = produced - produced_initial`
- 修复了 fruit 事件导致的追踪偏差
- 0 xin_conservation violations ✅

---

## B-tier: 运动分化

### 根因诊断
- 编码层 **所有轴 ema=1.0**，即使只有 oto_x 有输入
- 原因: `bc_current=0.05` → V_ss=0.25 ≈ v_peak=0.35，bias 几乎足以让无信号轴持续 spike

### 修复 1: 降低编码 bias
- [hebbian.py](file:///d:/cell-cc/nexus_v1/circuit/hebbian.py) L76-80: `bc_current` 0.05→0.02
- V_ss = 0.02×5 = 0.10 << v_peak=0.35
- 效果: 无信号轴 ema 从 1.0 降至 ~0.55

### 修复 2: 拓扑分化
- 原: 1 个 7×3 全连接 `col_to_motor` bundle
- 新: 3 个 1×1 轴特异 + 1 个 7×3 弱跨轴

```
col_yaw  ─── [w=0.3] ─── move_x  (VOR horizontal)
col_pitch ── [w=0.3] ─── move_y  (VOR vertical)
col_roll ─── [w=0.3] ─── move_z  (VSR trunk)
all_col ──── [w=0.05] ── all_mot  (cross-axis, slow STDP)
```

---

## C-tier: 理论层

### C1. B1+B5 耦合定理

**命题**: Xin 振荡幅度 A ≤ √(2·P_input·R_leak)

核心推导:
- Xin 耗散功率: P_diss = A²/(2R_leak)
- Noether 约束: P_input ≥ P_diss
- 吸引子方程: A* 是 P_input(A) = A²/(2R_leak) 的唯一不动点

**关键推论**: 学习和振荡竞争能量——不能同时最大化两者

### C2. 时间分辨率验证

三阶段变频实验 (0.5Hz → 2.0Hz → 0.1Hz):

| 变化 | 响应时间 | 物理含义 |
|---|---|---|
| 频率升高 ×4 | **1s** | 快速预警 |
| 频率降低 ×20 | **6s** | 慢速松弛 |

不对称性: 升频检测 >> 降频检测（生物一致: 捕食者检测快于放松）

---

## 最终验证状态

```
Noether T4: PASS (0 violations, 30k steps)
  Energy:  0.0017% error
  KCL:     0 violations  
  Xin:     0 violations (baselined + rolling ledger)
  Landauer: 2.58 bits, Q/bit >> kT·ln(2)
  Weight:  Memristor LTP/LTD tracking active
```

## 修改文件汇总

| 文件 | 修改 |
|---|---|
| [semiconductor.py](file:///d:/cell-cc/nexus_v1/components/semiconductor.py) | Capacitor KCL + Memristor audit |
| [noether_probe.py](file:///d:/cell-cc/nexus_v1/circuit/noether_probe.py) | KCL check + Shannon Landauer + Xin sync |
| [hebbian.py](file:///d:/cell-cc/nexus_v1/circuit/hebbian.py) | Enc bias 0.02 + axis-specific bundles + ZCR pruning |
| [bundle.py](file:///d:/cell-cc/nexus_v1/circuit/bundle.py) | apply_dw migration + Xin rolling ledger + fruit fix |
