# 版本迭代记录 — nexus_v1

> 每次版本号变更时更新。记录架构变更、关键参数调整、回归测试状态。
> 格式: `vX.Y.Z` — X=架构, Y=功能, Z=修复

---

## v1.7.2 (2026-06-08, commit 63995a0)

**主题**: P2.1 — 废除硬上限, 热力学能量墙

**架构变更**:
- 移除 `MAX_TOTAL_BUNDLES = 80` (硬编码上限)
- 添加 `EnergyStore.max_deposit_per_step = 0.05` (恒定 P_inflow)
- metabolic_tax 改为从 EnergyStore 扣除 (`BUNDLE_BASAL_COST = 0.0005`)
- Sprout 门控改为 `!energy_store.is_starving`
- E1 系统级评估 (mean_xi per growth interval)
- expand_boost: sprout 继承 30% 父本权重

**参数变更**: 见 [PARAM_CHANGELOG.md](PARAM_CHANGELOG.md)

**验证**:
- 回归: 21/21 ✅
- 80k: N=37→61, ES fill 50%→21%, E1 7/7 OK
- 500k: 🔄 运行中

**新增文档**: T006_theoretical_anchors.md

---

## v1.7.1 (2026-06-07, commit 497ef27)

**主题**: Xin fan-in 归一化 + Fruit SW gate 修复

**架构变更**:
- `compute_xin()` 添加 `/= N_targets` 归一化
- Fruit standing_wave_gate 移除 (ZCR 双峰阻断)
- T9 回归测试 (fan-in ratio < 2.0)

**参数变更**: 见 [PARAM_CHANGELOG.md](PARAM_CHANGELOG.md)

**验证**:
- 回归: 21/21 ✅
- 60k: expand 方向正确, cross 假阳性消除
- 500k: axis/cross ratio 2.3→2.8 (恢复)

---

## v1.7.0 (2026-06-07, commit 7a8833e)

**主题**: ν EMA 平滑 + C5 Fruit gate 修复 + 回归套件

**架构变更**:
- Motor potential ν 改为 EMA (α=0.01) 而非 raw Δ
- 自动化回归套件 (20 tests → 21 tests)
- Fruit DA gate 校准

**验证**:
- 回归: 20/20 ✅ (初始版本)
- 500k: Xin 周期性确认 (FFT 验证)

---

## v1.6.0 (2026-06-06, commit cbea5d5)

**主题**: A7 运动势 + 结构熵追踪

**架构变更**:
- `MotionState.motor_potential` = dK/dt
- `StructuralEntropy` 追踪 H_struct, H_flow
- P_ν × H_flow 准守恒发现 (后证伪)

**验证**: 500k 回归通过

---

## v1.5.0 (2026-06-05, commit ac64dba)

**主题**: C2 运动分化 + Noether probe

**架构变更**:
- Col→Mot 轴特异拓扑 (3×1×1 + 1×7×3)
- NoetherProbe 全面审计
- cross_weight_ceiling 硬编码

**验证**: 10k 运动分化确认

---

## v0.10.3 (2026-06-03, commit 4d88780)

**主题**: 信号链完成 (body moves)

- spike-before-leak 修复
- TemporalCoupler 就位
- 身体首次真正运动

---

## v0.10.2 (2026-06-02, commit ab10433)

**主题**: 环流结构载体

- CirculationProportionCircuit (Capacitor+MOSFET)
- EnergyStore 初版
- Fruit DA gate 初版

---

## v0.10.1 (2026-06-01, commit 0d5de37)

**主题**: C3' 环流耦合初版

- World + Body + Thermal + Muscle
- EnergyStore
- Fruit 生命周期初版
