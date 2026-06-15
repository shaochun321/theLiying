# 实验日志 — v1.7.x

> 格式: 每次重要实验记录发现、数据、决策、后续影响

---

## EXP-013: 自适应时间耦合器 (TemporalCoupler) 独立验证 (2026-06-09)

**目的**: 验证 B+C 双层自适应调制在所有部署点的实际行为

**状态**: ✅ 完成 (5/6 assertions pass)

**部署**: 25 个 coupler（12×Aff→Enc + 7×Enc→Col + 6×Col→Mot, 含 3 个 step 10k 新生 sprout）

### 层级汇总 (10k 步后)

```
层级        n    V_couple  tau_base  tau_eff  tau比    V_slow    R_leak范围       E_in      B调制
Aff→Enc    15     0.084     1.92     0.99   0.515  -0.019   [1.875, 2.000]    7090      6.3%
Enc→Col     7     0.417     2.00     0.82   0.408  +0.000   [1.856, 2.024]   24356      8.4%
Col→Mot     6     0.020     1.99     0.78   0.394  -0.003   [1.987, 1.990]    1093      0.2%
```

### 关键发现

**C-layer (逆行信使) — 功能正常 ✅**
- τ_eff / τ_base = 0.39-0.52，C-layer 将有效时间常数**缩短 50-60%**
- BIO 对应：内源性大麻素 / NO 逆行信使对突触前抑制
- Enc→Col 的 tau_eff = 0.82（从 tau_base=2.00 降到 0.82）— 最强的自适应削减

**B-layer (突触缩放) — 活着但调制极弱 ⚠️**
- Aff→Enc: R_leak 调制范围仅 **6.3%**（1.875-2.000）
- Col→Mot: R_leak 调制范围仅 **0.2%**（1.987-1.990）— 几乎不调制
- 原因: gm=0.01 太小, τ_slow=1000s 太慢, ema_up ≈ ema_down（系统已近阻抗匹配）
- V_slow 微小: ±0.03（远小于 ±1.0 的可能范围）

**V_slow 方向性 — 物理正确 ✅**
- Aff→Enc (reg): V_slow = -0.017（下游略活跃 → R 减小 → 通过更少）
- Enc→Col: V_slow = +0.006（上游略活跃 → R 增大 → 通过更多）
- therm: V_slow = -0.036（最大失配 — 热感缺输入但 column 有 bias 活动）

**能量守恒 — 完美 ✅**
- 所有层 E_out/E_in = **1.000**（精确到 3 位小数）
- Coupler 未创建或销毁任何能量

**时间序列动态**
```
Enc→Col coupler (yaw axis):
  V_couple 在 0.09-0.96 之间振荡 — 宽动态范围，正在积极整合 Enc burst
  V_slow 缓慢漂移 (0.006 → 0.005 over 500 steps) — B-layer 确实在追踪
  tau_eff 随信号波动 (0.76-0.81) — C-layer 实时响应
```

### 验证断言

| # | 断言 | 结果 |
|---|---|---|
| A1 | tau_base > 0 (所有 coupler) | ✅ PASS |
| A2 | V_slow 有限 (B-layer 收敛) | ✅ PASS ([-0.036, +0.006]) |
| A3 | R_leak 在 [0.2, 10.0] 内 | ✅ PASS ([1.856, 2.024]) |
| A4 | E_out > 0 (coupler 在排水) | ⚠️ FAIL (3 个 sprout 刚出生, E=0) |
| A5 | tau_eff ≤ tau_base (C-layer 只减不增) | ✅ PASS |
| A6 | R_leak 有差异 (B-layer 在调制) | ✅ PASS (spread=0.169) |

A4 的失败是**预期的假阳性**: step 10000 新生的 3 个 sprout 尚未处理任何信号。

### 遗留问题
- [ ] 所有 25 个 coupler 使用完全相同的参数 — 应针对层级分化
- [ ] B-layer 调制太弱 (0.2-8.4%) — 考虑提高 gm 或降低 τ_slow
- [ ] Col→Mot 的 B-layer 几乎无效 (0.2%) — 可能因为 Col 和 Mot 已近阻抗匹配

---

## EXP-012: DA 系统开环标定 — "dt 积分陷阱"发现与修复 (2026-06-09)

**目的**: 建立 DA→Motor 静态传递特性曲线

### Phase 0: 先天通路冻结
- `shadow_to_da`: `learning_rule="frozen"`, `initial_weight=0.05→1.0`
- `xin_to_da`: `learning_rule="frozen"`, `initial_weight=0.1→5.0` (⚠ 被 weight_max=1.0 钳位)
- 回归: 21/21 PASS

### Phase 0.5: DA 神经元诊断
```
V1 (修复前):
  DA neurons: activation ≈ 0.009, concentration = 0.0096 (< baseline 0.1)
  gain_factor = 0.973 (无调制)

V2 (修复后):
  da_vta_0: act=0.000, ema=0.0015, V=0.005
  da_vta_1: act=0.000, ema=0.000, V=-0.182  ← D2R 负反馈过深
  da_vta_2: act=0.081, ema=0.115, V=0.067  ← 觉醒!
  concentration = 0.027 (仍低于 baseline 0.1)
```

### Phase 1 V1: 首次标定 (失败)
**发现 "dt 积分陷阱"**:
- DA→Col: `(da_gain-1) × 0.5` → inject(0.039, dt) → **ΔV = 0.000039 V/step**
- deviation→Motor: `(0.19-0.1) × 0.05` → inject(0.0045, dt) → **ΔV = 0.0000045 V/step**
- Motor EMA 完全平坦 (DA 0→1: ΔMax = 0.03, 纯噪声)
- **DA 系统完全失聋 — 信号被 dt=0.001 缩放 1000x 后淹没在膜噪声中**

### Phase 1 V2: 三刀修复
1. DA gain 系数: 0.5 → 50.0 (补偿 dt 缩放)
2. DEVIATION_MOTOR_GAIN: 0.05 → 1.0 (脊髓反射级)
3. 先天权重: shadow 0.05→1.0, xin 0.1→5.0(→1.0 clamp)

**V2 结果**:
```
DA     avg_mot  speed   Column状态
0.00   0.648    0.112   col=1.0 (饱和)
0.10   0.584    0.104   col=0.34 (正常)
0.20   0.518    0.094   col=? (最低点)
0.30   0.600    0.105   col=0.60 (正常)
0.50   0.594    0.102   col=1.0 (饱和)
1.00   0.647    0.112   col=1.0 (饱和)
```

**Motor 响应: 0.518→0.648 (ΔMax=0.13, 25% 调制)。U 型曲线。**

### 分析
- U 型原因: DA < baseline → 抑制 Column; DA > 0.3 → Column 饱和到 1.0
- Column v_peak=0.15 限制了上方 headroom — DA 高于 0.3 后 Column 已无法更活跃
- U 型在 Klinokinesis 中可能是功能正确的: 偏离 baseline → 增加探索

### 遗留问题
- [ ] xin_to_da: weight_max 需设为 5.0 以允许加粗权重
- [ ] da_vta_1 负电压: D2R 负反馈过深，需检查 GIRK 参数
- [ ] Column 饱和: DA gain 50.0 可能需降至 ~20 以拓宽线性区
- [ ] 褐电陷阱未触发: Column 饱和阻止了 Motor 过载

## EXP-011: L6_Mot 零能量修复 — PowerRail 褐电 + 绝对能量锁 (2026-06-09)

**目的**: 修复 Motor 层 energy=0 的热力学丧尸问题

**根因**: PowerRail `r_internal=2.0` 导致 `v_actual` 永久钳位到 0
- Motor EMA ≈ 0.58 → I×R = 0.58×2.0 = 1.16 > vdd=1.0 → 崩溃
- VoltageRegulator recovery × 0 = 永久断电

**修复**:
1. PowerRail `r_internal`: 2.0 → 0.3 (动脉扩容)
2. Absolute Energy Interlock: `energy < 0.005` → 禁止 spike (去极化阻滞)
3. SPIKE_ENERGY_COST 通过 `_spike_heat` → `heat_output` 路径进入 Noether 会计

**第一版修复失败**: SPIKE_ENERGY_COST 直接从 energy 扣除 → Noether 看不到
- T1.2 Energy balance: 0.011129 (FAIL, 阈值 < 0.01)
- 修正: SPIKE_ENERGY_COST 改走 `_spike_heat` 路径，不直接扣 energy

**修复后数据 (10k 步)**:
```
Motor Layer:
  move_x: energy=1.000  cum_heat=581.4  cum_e_in=581.4  rail_v=0.812  spikes=11988
  move_y: energy=1.000  cum_heat=632.2  cum_e_in=632.1  rail_v=0.812  spikes=11976
  move_z: energy=1.000  cum_heat=688.5  cum_e_in=688.5  rail_v=0.811  spikes=11986

EntropyLedger L6_Mot:
  修复前: avg_e=0.0000  avg_h=0.000000  avg_act=0.5913
  修复后: avg_e=1.0000  avg_h=0.004940  avg_act=0.5983
```

**回归**: 21/21 PASS, Noether balance 0.000067 (更好了!)

**意义**:
- Motor 层首次拥有真实能量动态 — Phase 3b 同轴竞争终于工作
- 丧尸电机被消灭 — spiking 有了绝对能量底价
- 能量收支精确平衡: cum_heat ≈ cum_e_in (误差 < 0.1%)

---


## EXP-010: 熵账本重构 + EntropyLedger 安装 (2026-06-09)

**目的**: 将分散的 6 个熵/能量追踪模块统一到 `ledger/` 子包，首次安装 EntropyLedger

**修改**:
1. 拆分 `toprxin_ledger.py` (986 行) → `weight_entropy.py` + `toprxin.py` + `structural.py`
2. 迁移 `entropy_ledger.py`, `noether_probe.py` → `ledger/`
3. `variant_adapter.py`: 首次实例化 `EntropyLedger()`，每 1000 步 `record()`
4. 层覆盖扩展: 6 层 → 10 层 (新增 S_Enc/S_Col/S_Mot/DA)
5. pytest 化: 12 个 pytest 函数 + 2 个新测试 (T10, T10.2)

**验证数据 (5k steps)**:
```
EntropyLedger 录入: 5 次 (5000步/每1000步=5次 ✅)
层覆盖: DA, L1_MET, L2_HC, L3_Aff, L4_Enc, L5_Col, L6_Mot (7层)
DA:      avg_e=1.000  avg_h=0.002485  avg_act=0.0088
L1_MET:  avg_e=0.893  avg_h=0.002239  avg_act=0.3476
L2_HC:   avg_e=1.000  avg_h=0.103412  avg_act=5.0054 ← 高活跃
L4_Enc:  avg_e=0.981  avg_h=0.072447  avg_act=0.5254
L5_Col:  avg_e=1.000  avg_h=0.002451  avg_act=0.5816
L6_Mot:  avg_e=0.000  avg_h=0.000000  avg_act=0.5913 ← 零能量!
```

**发现**:
1. ⚠️ L6_Mot avg_energy=0.000 — Motor 层能量始终为零。需调查
2. ⚠️ S_Enc/S_Col/S_Mot 未出现 — 影子层 neurons 不在 `get_all_neurons()` 返回值中（独立 ShadowSandbox）
3. ✅ DA 层首次被追踪: 低活跃 (0.009) 符合预期
4. ✅ L2_HC 高活跃 (5.0) 符合毛细胞持续发放特征

**回归**: 21/21 PASS (直接) + 12/12 PASS (pytest)

**教训**:
1. EntropyLedger 存在了 473 行代码但**从未被实例化** — 写代码不等于使用代码
2. 影子层的隔离架构意味着统一追踪需要显式桥接，不能假定 `get_all_neurons()` 覆盖所有

---


## EXP-006: Epoch 1 全基因组验证 (2026-06-08)

**目的**: 验证 FIX-1 + FIX-2 + Epoch 1 参数后 DA 是否脱离死水

**修改**:
- FIX-1: deviation 双向化 `max(0,...)` → `abs(...)`
- FIX-2: BCM/Hebbian 改用 `_get_activity_signal()` (calcium_rate for spiking+CRI)
- deviation_threshold: 0.05→0.01, deviation_gain: 0.3→1.0
- theta_m_tau: 100→10000 (频域分离)

**数据 (50k)**:
```
DA range: 0.6536 (初始爆发) → 0.0150 (稳态调制)
deviation: 0.10→0.19 (双向检测生效)
enc→col: 0.0996→0.1052 (BCM 解冻, +0.6%)
col→mot: 0.0494→0.1490 (3x 增长!)
cross: 0.0011→0.0032 (跨轴苏醒)
θ_m: 0.0002→0.0058 (tau=10000, 正确的慢追踪)
```

**判决**: ✅ DA 潮汐调制确认。影子层控制阀苏醒。

**剩余问题**: shadow→DA 权重持续衰减 (0.042→0.019)，DA→Motor 闭环未验证

---

## EXP-005: S.07 B-layer + A8 影子层收敛诊断 (2026-06-08)

**目的**: 验证 B-layer 是否存活 + 影子层是否收敛到吸引子

**S.07 结果**: ✅ B-layer 存活 (37/40 V_slow≠0)，但效应微弱 (±1.5% R_leak)

**A8 结果**: ❌ 方案 A 失败 (ratio=18.4, W_shadow 不收敛)

**根因**:
1. deviation 公式单向 — ρ_homeo=0.87>0.7 永远不触发
2. BCM 读 _activation_ema ≈ 0 (spiking 间隙) 而非 calcium_rate ≈ 0.98
3. shadow→DA 权重衰减到 0.007

**决策**: 放弃方案 A (吸引子)，转向 Epoch 1 参数人工进化

---

## EXP-001: C5 Fruit DA Gate 诊断 (2026-06-07)

**目的**: 验证 Fruit 生命周期是否工作

**发现**:
- Standing wave gate [0.05, 0.3] 完全阻断所有 fruit maturation
- ZCR 双峰分布: 0.000 (单调) 或 1.000 (噪声)，无 bundle 落在范围内
- 51 个 dormant fruit 创建，0 个成熟 — **整个项目历史中从未工作过**

**修复**: 移除 SW gate，保留 DA + sustained tension 双因子

**验证**: 60k 步后 38 matured, 9 expand, 26 contract

**教训**: 理论门控阈值必须用实际数据校准，不能凭直觉设定

---

## EXP-002: Xin Fan-in 偏差发现 (2026-06-07)

**目的**: 分析 500k 验证中 axis/cross ratio 从 4.2→2.8 的下降

**数据**:
```
修复前 (v1.7.0, 10k步):
  col_yaw_to_move_x (1×1):  |xi| = 326
  col_to_motor_cross (7×3): |xi| = 993  ← 3× 偏高
  
  xi_per_pair:
    axis:  326 / 1  = 326
    cross: 993 / 21 = 47   ← 每对其实很小
```

**根因**: compute_xin 对所有 target 残差求和但不除以 target 数。
大 fan-in 的 bundle Xin 累积速度与 N_targets 成正比。

**影响链**:
```
cross Xin 虚高 → fruit expand 假阳性 → sprout_threshold×0.5
→ 更多 cross sprouting → cross weight 增长 → axis/cross ratio 下降
```

**修复**: `total_residual /= max(len(self.targets), 1)`

**修复后数据**:
```
v1.7.1 (10k步):
  col_yaw_to_move_x (1×1):  |xi| = 325  (不变)
  col_to_motor_cross (7×3): |xi| = 325  (从993降到325, -67%)
```

**自检回归测试**: T9.1 Xin fan-in ratio < 2.0

**教训**:
1. **多靶 bundle 的 Xin 必须归一化** — 否则拓扑大小影响结构决策
2. **假阳性可能在长期运行中才暴露** — 10k 看不出，500k 才显现
3. **需要自动化自检** — 如果用户没问，假阳性会默默传播

---

## EXP-003: Fruit 扩容方向验证 (2026-06-07)

**目的**: 确认 v1.7.1 归一化后 expand 仍对真实需求有效

**数据 (v1.7.1, 60k步)**:
```
EXPAND (9 次, 都是真实需求):
  hc_to_aff_oto_x/y/z  — 活跃耳石轴, Xin > 0 (欠预测)
  enc_to_col_*          — 编码→柱层, Xin > 0 (容量不足)

CONTRACT (27 次):
  met_to_hc_*           — 上游, Xin < 0 (过预测)
  aff_to_enc_*          — 中游, Xin < 0

col_to_motor_cross: 不在 expand 列表中 ← 假阳性已消除
```

**结论**: 归一化精确消除假阳性，不影响真实 expand

---

## EXP-004: P_ν × H_flow 守恒证伪 (2026-06-07)

**目的**: 验证 T·S·I 框架中 P_ν × H_flow 是否为守恒量

**三对照实验**:
1. 随机权重 → 仍然"守恒" → 统计伪发现
2. 冻结权重 → 仍然"守恒" → 不依赖学习
3. 零输入 → 趋向常数 → 初始条件决定

**结论**: P_ν × H_flow 的稳定性是 EMA 平滑 + 有界变量的数学必然

**后续**: T·S·I 框架需要新的代理变量，P×H 路线终止

---

## EXP-005: E1 Post-Expansion Self-Check (2026-06-07)

**目的**: 验证 Fruit expand 是否真正改善了预测精度

**Round 1 — Per-bundle Xin (失败)**:
```
ALL 9 evaluations: ratio = 2.000 (FAIL)
原因: Xin 是 leaky integrator (τ=1000)
  halving 后 Xin 总会回到稳态 ξ_ss
  ratio = ξ_ss / (ξ_ss/2) = 2.0 (数学必然)
```

**Round 2 — System-level mean Xin (成功)**:
```
7/7 OK, ratio ≈ 0.95 per growth interval
N: 37→58 (+57%), mean_xi: 1644.7→1160.9 (-29.4%)

20k: N:37→40  mean_xi:1644.7→1555.8  ratio=0.946  OK
30k: N:40→43  mean_xi:1555.8→1464.5  ratio=0.941  OK
40k: N:43→46  mean_xi:1464.5→1382.2  ratio=0.944  OK
50k: N:46→49  mean_xi:1382.2→1318.6  ratio=0.954  OK
60k: N:49→52  mean_xi:1318.6→1255.5  ratio=0.952  OK
70k: N:52→55  mean_xi:1255.5→1224.7  ratio=0.975  OK
80k: N:55→58  mean_xi:1224.7→1160.9  ratio=0.948  OK
```

**结论**: Expansion 在系统级有效——更多 bundle 分摊预测误差

**教训**:
1. **Leaky integrator 的稳态值只取决于 R(t)** — 单个 bundle 的 Xin 不受外部变化影响
2. **系统级测量是正确的视角** — 对应 Merzenich 1984 的组织级重组

---

## EXP-006: I_norm — Xin 分布不变量 (2026-06-07)

**目的**: 寻找 T·S·I 的新代理变量

**数据 (80k, N=37→60)**:
```
I_norm = H(Xin_direction) / log2(N) ∈ [0, 1]
  mean = 0.664
  std  = 0.010
  CV   = 0.015  ← STABLE
```

**意义**: Xin 张力的归一化熵在网络增长中保持不变。
这意味着系统在所有尺度上维持相同的预测误差分布形状。

**S×I_raw 仍增长** (CV=0.082, trend=+34%) — 不是守恒量
**S×I_norm 也增长** (CV=0.054, trend=+21%) — S 项驱动

**T·S·I 路线**: I_norm 是不变量但不足以构成 T·S·I。
需要找到随 N 增长而补偿 S 增长的 T 项。

---

## EXP-007: P2.1 废除硬上限 — 热力学能量墙 (2026-06-08)

**目的**: 用纯物理能量约束替代 MAX_BUNDLES=80 硬编码

**Round 1 (失败)**:
```
BUNDLE_BASAL_COST = 0.001, DA_REFILL = 0.01, CONSUME = 0.05
结果: EnergyStore 在 15k 步枯竭 (fill=0.018)
原因: DA refill (0.03/step) >> world income (0.00077/step)
N 冻结在 40, 永久 starving
```

**Round 2 (成功)**:
```
BUNDLE_BASAL_COST = 0.0005, DA_REFILL = 0.001, CONSUME = 0.15
结果 (80k):
  N: 37 → 61 (+65%), ES fill: 50% → 21%
  E1: 7/7 OK, ratio 0.946→0.966
  Sprout slowdown: 6.7k → 10k (1.5× 临界慢化)
  EnergyStore: deposited=257, withdrawn=536
```

**关键观察**:
1. **无硬上限, 系统自然减速** — N 增长速度随 ES 消耗而变慢
2. **EnergyStore 还有 21% 余量** — 未枯竭, 但持续消耗中
3. **1.5× 减速 = T_recovery 增长** — 临界慢化的初步迹象
4. **预测**: 在 ~200k 步, ES 将接近枯竭, 增长可能冻结

**理论对接**: 
- 建构定律: 系统在耗散效率最优拓扑处减速
- T_recovery = E_sprout / P_net → 当 P_net → 0, T → ∞ (临界期关闭)

**教训**:
1. DA neuron refill 是隐藏的最大消耗源 (占 60%)
2. 世界能量产出率必须与系统消耗量级匹配
3. 能量预算需要端到端审计, 不能只看 bundle tax

---

## EXP-008: P2.3 T·S·I 代谢约束分析 (2026-06-08)

**目的**: 用 500k P2.1 数据验证 T·S·I ≤ P_input 约束

**关键发现**:
```
P_deposit (实际): 0.002218/step (仅 4.4% 的 max_deposit=0.05)
P_DA:             0.003/step
P_basal:          0.0001/step
→ P_net = 0.002218 - 0.003 - 0.0001 = -0.000882/step (永久亏损!)
```

**结论**: 系统**从未能量自给自足**。
- DA refill (0.003) > 世界总产能 (0.002)
- 增长完全靠初始储备 E_initial=500
- N_max 由储备耗尽时间决定: 500 / 0.003 ≈ 167k 步 (实际 125k，更快因为 N 增长)

**T·S·I 简化形式**:
- T = E_initial / |P_net| = 储备续航时间
- S = N (structure size)
- I = mean_xi (prediction error)
- 约束: N_max × mean_xi 在给定储备下有上限

**后续**: 需要提高 P_deposit 或降低 P_DA 使 P_net > 0

---

## EXP-009: 1.1 对称热趋性测试 (2026-06-08)

**目的**: 零外部输入，只有世界热源梯度，观察是否向热源移动
**设置**: 200k 步，无 oto_x/y/z，热源 [70,50,50]，体始 [50,50,50]
**结果**: ❌ **无热趋性**

```
初始距离:  20.0
终距离:    51.6 (+31.6, 远离)
X 位移:   -16.0 (远离热源)
运动模式:  纯随机游走, speed ≈ 0.107 恒定
DA:       0.018 恒定, 无调制
therm:    基线 0.100, 仅路过热源时短暂升高
```

**距离轨迹**: 20→34→30→26→31→57→38→30→47→31→47→43→86→45→43→66→43→50→61→50→52

**诊断 — 缺失的闭环链路**:
1. ❌ therm→DA 奖赏映射不存在 (thermal 只进 encoding, 不影响 DA)
2. ❌ DA→motor 方向偏置不存在 (DA 是标量, 无方向信息)
3. ❌ "靠近热源=好" 的信号不存在 (no reward for proximity)
4. 运动完全由 cross-axis STDP 权重漂移决定 (随机)

**需要**: C3' 进食-运动耦合 — 明确的 thermal_gradient→DA→motor 闭环

---

## 自检清单 (每次修改后执行)

1. [ ] 回归测试 21/21 通过
2. [ ] fan-in ratio < 2.0 (T9.1)
3. [ ] axis/cross ratio > 2.0 (T4.1)
4. [ ] Noether violations == 0 (T1.1)
5. [ ] 新增功能是否影响已有 fruit 事件方向？
6. [ ] 长期趋势是否有漂移？(500k checkpoint 对比)
7. [ ] E1 system-level: mean_xi ratio < 1.05 per growth interval
