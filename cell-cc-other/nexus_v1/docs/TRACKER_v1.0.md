# 项目主追踪表 v1.1

> 编号规则: `领域.序号` | 状态: ✅完成 ⚠️部分 ❌未做 🔬需建模 ❓待确定

---

## S. 结构/组件层

- [x] **S.01** Capacitor KCL 追踪 (`_q_in/_q_out/_q_initial`)
- [x] **S.02** Memristor 分项审计 (`apply_dw` + `_cum_ltp/_cum_ltd`)
- [x] **S.03** MOSFET 亚阈值修复 (`conduct()` 返回 0)
- [x] **S.04** NDR 元件 (Afferent 特有)
- [x] **S.05** PowerRail (Motor 特有)
- [x] **S.06** D2R 自受体 (DA 特有)
- [x] **S.07** Temporal Coupler C-layer + B-layer — **EXP-013 验证 5/6 pass**: C-layer 正常 (τ_eff/τ_base=0.4), B-layer 调制弱 (6-8%)
- [x] **S.08** CirculationProportionCircuit (环流比例结构载体)
- [x] **S.09** EnergyStore (外部能量储库)
- [x] **S.10** LiquidMetalRouter (Enc→Col 结构可塑性)
- [ ] **S.11** Encoding 层特有元组件 — 当前只有通用 VR+bias，缺少分化组件
- [ ] **S.12** Column 层特有元组件 — lateral inhibition 是外部注入，非内置
- [x] **S.13** 热源动态 — **代谢壁修复 2026-06-20**: 8源均匀分布(覆盖率10%→27%) + E_HALF 10→100 + 重生能量200-600 (commit 45780da). 回归 12/12 PASS.
- [ ] **S.14** 世界介质参数 — Z=1.0 默认值，未定义深海/硅基属性
- [x] **S.15** DA 乘法调制 — `_propagate_bundles()` 钩子 + gain_factor 缩放

---

## B. 体表/感受层 — 第二主体：热

> 第一主体（运动）通过前庭链获得完整转导：MET→HC→Aff→Enc→Col→Mot。
> 第二主体（热）已实装 4-patch Fourier 热积分器 + SomatoRelay 拓扑。
> 2026-06-11 三根架构钢钉已全部打入（热容积分器 / 废弃人工比较器 / Shadow 缴税）。

- [x] **B.00** 刚体壳定义 — Body dataclass: position/velocity/mass/radius, effective_radius 自动推导
- [x] **B.01** 外皮 patch 拓扑 — 4 patch（front/back/left/right），Fourier 热容积分器（非理想温度计）
- [x] **B.02** 皮肤感受神经元 (Thermoreceptor + Nociceptor) — τ_thermo=100ms, τ_noci=4ms 频域隔离; Noci 输入源 = damage_integral（组织损伤积分）
- [x] **B.02b** SomatoRelay 体感中继层 — 4 relay 神经元 + 邻接侧抑 bundle（禁止 front↔back 对角线）; **拓扑隐式编码体表 2D 流形**; 输出用 _activation_ema（稳定 [0,1] 范围）
- [x] ~~**B.03** 自身原点模块~~ — **已废弃**（2026-06-11 架构师修正）: 外感受预测由 Shadow 层 STDP 自然学习，禁止人工比较器
- [x] **B.04** 感受→DA 闭环 — Phase 3 Gate 6/6 PASS: shadow col therm calcium_rate 0.47~0.85 (分化), DA mean=0.21, STDP weights 0.30→0.93
- [ ] **B.05** 感受带宽扩展 — patch 数按需增加，皮层体积可调
- [ ] **B.06** 热势 ν_th = dE_thermal/dt — 类比运动势 ν，ν×ΔT 相关性是 STDP 方向信号

> **架构约束** (2026-06-11 修正后):
> - SkinPatch 是 Fourier 热容积分器: `dT_skin = k(T_env - T_skin)/C · dt`，严禁直读环境温度。
> - 预测热觉变化 = Shadow 层 STDP 本职工作，无需人工比较器。
> - Shadow 层每 1000 步向 EnergyStore 缴纳 metabolic tax（per-bundle + per-neuron）。
> - SomatoRelay 连接拓扑 + 时间编码 → 隐式 3D/4D 流形（体表×时间×模态）。
>
> **依赖**: B.00 ✅ → B.01 ✅ → B.02 ✅ → B.02b ✅ → B.04 → B.05。
> **验证方法**: test_skin_patches.py (5/5 pass) + test_smoke_soma.py (全 assertion pass)。

---

## N. 神经/信号链

- [x] **N.01** 前庭链 Met→HC→Aff(reg/irr)→Enc→Col→Mot
- [x] **N.02** 热感链 therm→Enc→Col→Mot
- [x] **N.03** Encoding bias 修复 (0.05→0.02)
- [x] **N.04** Col→Mot 轴特异拓扑 (3×1×1 + 1×7×3) — **战役四补全 2026-06-20**: vestibular 轴束 stdp_lr 0.005→0.05, synapse_gain 5.0→10.0 (commit e8ad17e). 回归 12/12 PASS.
- [x] **N.05** DA 神经元池 (3 个 VTA DA)
- [x] **N.06** Shadow→DA + Xin→DA bundles
- [x] **N.07** Motor→Column 反馈 (efference copy)
- [x] **N.08** Lateral inhibition (Column 间)
- [x] **N.09** Binding layer (跨模态)
- [x] **N.10** Spike-before-leak 顺序确认
- [x] **N.11** DA→Motor 乘法调制 — `_propagate_bundles()` 覆写，gain = 1+α·DA
- [ ] **N.12** 环流→进食激活路径 — 偏激反向传播未实现
- [ ] **N.13** 环流记忆 / 长期 EMA 落地 — 进化尺度存储无结构
- [ ] ❓**N.14** 外皮感受→Encoding 传入链 — 依赖 B.02

---

## P. 可塑性/学习

- [x] **P.01** STDP 软边界 (乘法)
- [x] **P.02** BCM 滑动阈值
- [x] **P.03** Hebbian decay
- [x] **P.04** Fruit 成熟/修剪/萌芽
- [x] **P.05** ZCR 驻波引导修剪 (#5)
- [x] **P.06** PNN gate 传递到 learn()
- [x] **P.07** 三因子学习 (DA × pre × post)
- [x] **P.08** 突触维持税结构化 — P2.1: 常数基底漏电从 EnergyStore 扣除
- [x] **P.09** 先天通路冻结 — shadow→DA + xin→DA 设为 `learning_rule="frozen"`

---

## E. 能量/守恒

- [x] **E.01** Noether energy conservation
- [x] **E.02** Xin conservation (baselined)
- [x] **E.03** Landauer Shannon entropy
- [x] **E.04** Weight stability check
- [x] **E.05** 熵账本 pre-step guard → `_ledger_pre_step` (v1.7.2 重命名)
- [x] **E.06** ECM 负温度修复
- [ ] **E.07** 能量来源标签 — 追踪 E_in 来自哪个 source
- [x] **E.08** P2.1: 废除 MAX_BUNDLES=80 硬上限 — 热力学能量墙替代
- [x] **E.09** EnergyStore P_inflow 恒定上限 (max_deposit_per_step=0.05)
- [x] **E.10** 系统级 E1 评估 (mean_xi per growth interval)
- [x] **E.11** `nexus_v1/ledger/` 子包重构 — 统一 6 个观测模块
- [x] **E.12** EntropyLedger 安装 — 首次接入 step loop (每 1000 步)
- [x] **E.13** EntropyLedger 层覆盖扩展 — Shadow + DA 层
- [x] **E.14** PowerRail R_internal 2.0→0.3 — 修复 Motor 层褒电崩溃
- [x] **E.15** 绝对能量锁 (SPIKE_ENERGY_COST=0.005) — 消灭热力学丧尸
- [x] **E.16** 代谢壁修复 — **2026-06-20** Body 初始位置 [50,50,50]→[63,25,25] (dist=12, T=2.0 < damage_threshold), 热源三联修复. P_net: -0.0083→+0.00134/步. (commit 45780da)

---

## C. 环流/耦合

- [x] **C.01** CirculationMeter (rho 测量)
- [x] **C.02** CirculationProportionCircuit (rho→deviation→DA)
- [x] **C.03** 进食-运动-体征三路耦合概念
- [ ] **C.04** 环流偏激反向传播 — deviation→DA 有，但无直接 motor/feed 激活
- [ ] **C.05** 环流与震荡同构关系 — 概念讨论过，未建模
- [ ] **C.06** 等势环流巩固 — fruit 间耦合协同成熟未实现

---

## M. 数理/理论

- [x] **M.01** B1+B5 耦合定理 (能量钳制振荡)
- [x] **M.02** 时间窗验证 (1-6s 不对称)
- [x] **M.03** TSI 参数方程 (候选)
- [x] **M.04** TSI metric unification (候选)
- [x] **M.05** Adaptive coupler 数学分析
- [ ] **M.06** 参数→T/O/P/R/Xin 关系方程 — 系统化工具未实现
- [ ] **M.07** 元件参数→震荡频率/幅度映射 — 未建模
- [ ] **M.08** 收缩映射证明 (STDP Jacobian 谱半径) — 数学难题

---

## D. 文档/工具

- [x] **D.01** G-001 全局数学公式
- [x] **D.02** G-002 全局架构图
- [x] **D.03** 版本号迭代记录系统 → [VERSION_LOG.md](history/VERSION_LOG.md)
- [x] **D.04** 参数变更日志 → [PARAM_CHANGELOG.md](history/PARAM_CHANGELOG.md)
- [x] **D.05** 本追踪表
- [x] **D.06** 回归测试 pytest 化 — 12 个 pytest 函数 + 直接运行 21 项
- [x] **D.07** ledger/ re-export shims — 旧路径向后兼容

---

## 优先执行分类

### 🔧 可直接完成 (代码修改)

| 编号 | 项目 | 预估 |
|---|---|---|
| C.04 | 环流 deviation→motor 直接激活 | 15min |
| P.08 | 突触维持税用能量-电导耦合替代 magic 0.999 | 10min |
| N.11 | 环流→Motor 直接路径 | 同 C.04 |
| E.07 | 能量来源标签 | 15min |
| D.03 | 版本号 + 变更日志框架 | 5min |

### 🔬 需建模/数理候选 (延后)

| 编号 | 项目 | 原因 |
|---|---|---|
| S.11 | Encoding 特有组件 | 需确定生物对应 |
| S.12 | Column 特有组件 | 需确定功能需求 |
| C.05 | 环流-震荡同构 | 需数学框架 |
| C.06 | 等势环流巩固 | 需跨 bundle 耦合理论 |
| M.06 | 参数关系方程 | 需系统实验 |
| M.07 | 元件→震荡映射 | 需频响分析 |
| M.08 | 收缩映射证明 | 纯数学 |
| N.13 | 环流记忆落地 | 需进化论框架 |

### ❓ 待确定 (需架构决策)

| 编号 | 项目 | 前置依赖 |
|---|---|---|
| B.00 | 刚体壳定义 | S.14 世界介质 |
| B.01 | 外皮 patch 拓扑 | B.00 |
| B.02 | 皮肤感受→Encoding | B.01, N.02 |
| B.03 | 自身原点坐标 | B.01, A7 |
| B.04 | 感受→DA 闭环 | B.02, N.06 |
| B.05 | 感受带宽扩展 | B.02 验证后 |

### 🚫 显式延后 (2026-06-11 决策记录)

> 以下为第二主体构建期间**显式决定不做**的事项。每项记录原因和未来触发条件。

| 编号 | 项目 | 延后原因 | 未来触发条件 |
|---|---|---|---|
| D.10 | 修剪虚位重整化塔 | 熵账本有赫布超边保存虚位，但目前不需过度发展此机制 | 当 sprout/prune 频率 >10/1k步 且虚位回收率 <20% 时 |
| D.11 | Shadow sprout/prune/mitosis | Shadow 保持 plastic weights + growing topology；结构可塑性只在主系统 | 当 shadow 预测误差在新模态上 >100k 步不收敛时 |
| D.12 | Binding 扩展验证 | 平行测试方向，不在关键路径；metabolic_tax 自然修剪 C(N,2) | B.02 完成后，作为独立实验 |
| D.13 | P_ν × P_th 交叉守恒验证 | 需要第二主体建成后的实验数据；可能是 Lyapunov 追踪而非守恒 | Phase 3 100k 验证完成后 |
| D.14 | thermal_membrane.py 改动 | 保留单点标量传感器作为 legacy；新 patch 系统独立构建 | 新系统验证通过后，评估是否废弃 legacy |

---

## L2. 人工进化选择层 (L2:SELECTION) — Operation Trauma Genesis

> **本体论**：L0（物理规律）→ L1（涌现行为）→ L2（人工进化选择）。
> L2 层注入的是**物理后果**，不是**行为规则**。等价于自然选择将TRPV1→脊髓→运动的反射弧焊死在基因组中。
> 方法论详见: [METHODOLOGY_biological_screening.md](METHODOLOGY_biological_screening.md)
> 代码标注: `# L2:SELECTION — [简述] / BIO: / DESIGN: / EMERGE:`

- [x] **L2.01** 反馈环 A: damage → VitalOscillator 幅度衰减 — 心源性休克 `vital_damage_factor = 1/(1 + D×0.5)`
- [x] **L2.02** 反馈环 B: damage → EnergyStore 代谢税 — 组织修复消耗 `REPAIR_ENERGY_RATE = 0.005`
- [x] **L2.03** 反馈环 C: Nociceptor → Motor 脊髓反射弧 — `SpinalReflexArc` + MOSFET 闸门 (REFLEX_GAIN=0.5, gate=VDD)
- [x] **L2.04** 反馈环 D: damage → ECM 热突破 — Michaelis-Menten 屏障穿透 `K_BARRIER=2.0`
- [x] **L2.05** SpinalReflexArc 组件 — `components/spinal_reflex.py`，空间对比 noci 差值 → 定向运动电流
- [x] **L2.06** 皮层抑制占位链路 — MOSFET gate (default VDD=1.0), 未来皮层模块注入负电流关闭反射
- [x] **L2.07** L0/L1/L2 染色标注体系 — 代码级 + 文档级双层审计
- [x] **L2.08** 长步骤生物筛选 (≥100k) — **FULL PASS 4/4**: 存活 ✓ 心跳 ✓ 受损 ✓ 回避涌现(step 7k) ✓
- [ ] **L2.09** 参数联调实验 — REFLEX_GAIN / REPAIR_RATE / K_BARRIER 联合扫描

> **依赖**: B.01 ✅ → B.02 ✅ → L2.01~04 ✅ → L2.08 ✅ → L2.09 (待实验)
> **验证**: 长步骤运行后观察：① 系统存活 ✅ ② 出现回避行为 ✅ (step 7000) ③ 行为出现步数 = 7k

