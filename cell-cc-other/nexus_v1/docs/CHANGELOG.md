# nexus_v1 变更日志

## v1.5.0 — 2026-06-07 (当前)

### 新增
- **C.04** 环流 deviation→Motor 直接激活路径 (variant_adapter.py)
- **S.13** 热源位置漂移 HeatSource.step() (world.py)

### 修复
- **N.03** Encoding bias 0.05→0.02 解决无信号轴 100% 发射 (hebbian.py)
- **P.08** 突触维持税用 apply_dw + 能量耦合替代 magic 0.998 (hebbian.py)
- **A2-fix** 代谢衰减现在走 apply_dw 路径 (Noether 审计合规)

### 重构
- **N.04** Col→Mot 从 7×3 全连接拆为 3×1×1 轴特异 + 1×7×3 弱跨轴 (hebbian.py)

---

## v1.4.0 — 2026-06-07

### 新增
- **E.01-E.04** Noether Conservation Probe 完整实现 (noether_probe.py)
- **S.01** Capacitor KCL 追踪 _q_in/_q_out (semiconductor.py)
- **S.02** Memristor 分项审计 apply_dw + _cum_ltp/_cum_ltd (semiconductor.py)
- **E.03** Landauer Shannon 熵 20-bin 直方图 (noether_probe.py)
- **P.05** ZCR 驻波引导修剪 (bundle.py)

### 修复
- **E.02** Xin conservation 初始化基线同步 (noether_probe.py)
- KCL kcl_imbalance None guard (semiconductor.py)

---

## v1.3.0 — 2026-06-06

### 新增
- CirculationProportionCircuit 结构化环流比例 (circulation_proportion.py)
- EnergyStore 外部能量储库 (energy_store.py)
- DA 神经元池 (3 VTA + D2R + shadow/xin bundles)
- 熵账本 pre-step guard

---

## v1.2.0 — 2026-06-05

### 新增
- Temporal Coupler C-layer + B-layer (temporal_coupler.py)
- LiquidMetalRouter Enc→Col 结构可塑性
- NDR 元件 (afferent 特有)
- Shadow Sandbox + 影子层扩展 7 轴

---

## v1.1.0 — 2026-06-04

### 新增
- BindingLayer 跨模态绑定 (§5)
- 成熟相变逻辑 + PNN gate
- 热感链 therm→Enc→Col→Mot
- G-001/G-002 全局文档

---

## v1.0.0 — 初始

### 基础架构
- HebbianCircuit 前庭→编码→柱→运动
- VestibularSystem 6 轴 + 3 motor
- STDP/BCM/Hebbian 学习
- Fruit 成熟/修剪/萌芽
