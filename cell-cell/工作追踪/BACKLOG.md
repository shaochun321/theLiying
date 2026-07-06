# 工作追踪看板 (Task Board)

<!-- Claude 必须在每次会话开始时读取本文件，执行任务前先登记，完成后立即更新 -->
<!-- 格式：每行一个任务，状态必须是：⚡执行中 | 📋待执行 | ⏸暂停 | ✅已完成 | ❌取消 -->

---

## ⚡ 当前执行中

| ID | 任务描述 | 开始日期 | 备注 |
|:---|:---|:---|:---|
| — | — | — | — |

---

## 📋 待执行

| ID | 任务描述 | 优先级 | 依赖 | 来源文档 |
|:---|:---|:---|:---|:---|
| T-053 | nu_neuron 校准修复：_NU_SCALE=1/176 vs 当前xin_max≈8470（差4个量级），τ=0.1/dt=1.0导致exp(-10)衰减，nu_neuron.activation≈0，shadow→DA通路实质失效；需方案更新 ⏸ | P3 | T-047 ✅ | T-050诊断发现 |

---

## ⏸ 暂停（有明确恢复条件）

| ID | 任务描述 | 暂停原因 | 恢复条件 |
|:---|:---|:---|:---|
| T-013 | HC-015（待定） | 用户明确暂缓 | 用户指示 |

---

## ✅ 已完成（最近20条）

| ID | 任务描述 | 完成日期 | Commit |
|:---|:---|:---|:---|
| T-050 | P2-H shadow_nu验证：ν实测值在百万级（>0.01 ✅），shadow输入激活s_enc_therm_front=1.23；nu_neuron.activation=0（_NU_SCALE校准问题，登记T-053）| 2026-07-06 | — |
| T-047 | P0-B：shadow层输入增强（16条frozen束：3 Motor+12 relay+1 energy），H_struct 7.03→7.14，21/21 PASS | 2026-07-06 | 85274e9 |
| T-048 | P1-G 饥饿r_leak调制（EMA τ=1000，_hunger_ema，gain≤1.5×），21/21 PASS，T4.1=4.04x | 2026-07-06 | bafeae4 |
| T-051 | P0-A relay侧向抑制：已存在（bundles_relay_lateral_inh 4条，sg=-1.0/w=0.3，已注册 get_all_bundles）| 2026-07-06 | — |
| T-044 | 50k 验证：4/4 PASS（DR5%=76.5%/|Δw|=0.110/无死锁2.2%/T4.1=3.30x）| 2026-07-06 | — |
| T-043 | yaw层交叉抑制束实装（spinal_ccw→yaw_cw + spinal_cw→yaw_ccw，W=0.020/sg=-1.0，frozen，get_all_bundles注册），21/21 PASS | 2026-07-06 | 4ac8d98 |
| T-042 | F-I曲线诊断：phasic钳位(-0.1V)是根本原因，Ia压制比1.09×（峰值），T-045取消，T-043参数W=0.020/sg=-1.0 | 2026-07-06 | — |
| T-046 | P1-F：前庭N=3激活（VestibularChain(n_hair_cells=3)，21/21 PASS，variant_adapter.py+1行import） | 2026-07-06 | — |
| T-041 | 200k步长程复测：T4.1全程3.65x→5.56x（PASS），P8-3/P8-4 FAIL（时间点问题）| 2026-07-05-06 | 08e4c76 |
| T-040 | 热源侧向反转：G1 PASS(w_ccw=0.2994>w_cw=0.0058)，G2 FAIL(CPG随机性50k不足) | 2026-07-05 | — |
| T-039 | D1消融诈胡核心验证：|Δw|=0，DR5%=50%(随机基线)，D1 STDP=唯一方向来源 | 2026-07-05 | — |
| T-038 | 50k步验证：T4.1 4.09→4.38x稳定，DR5%峰值75%，|Δw|=0.295，全部PASS | 2026-07-05 | — |
| T-037 | T4.1修复：VOR axis bundles 冻结STDP（3.97x）+ spinal_to_yaw w 0.002→0.020，21/21 PASS | 2026-07-05 | 44214c9 |
| T-036 | 200k步长程实验：全部PASS（P4-1 Δw=0.2991/P4-2 DR5%=60%/P4-3 w_ccw=0.2998），自我修复机制确认 | 2026-07-05 | — |
| T-035 | 两阶段实验第二阶段：50k步，P3-4/P3-5/P3-6 全部PASS，|Δw|=0.2821（CCW胜出，step 40k大逆转） | 2026-07-05 | — |
| T-034 | 两阶段实验第一阶段：20k步，P3-1/P3-2 PASS（fill 0.300→0.260，DA=0.66），P3-3 WARN | 2026-07-05 | — |
| T-033 | 50k步P0验证：P0-1/P0-2 PASS，P0-3 FAIL（热场环境不适合），yaw权重衰减（phasic≈0） | 2026-07-05 | — |
| T-033(P0) | P0三条物理修复：phasic钳位/intake→DA/BMR | 2026-07-05 | cac24ca |
| T-032 | 200k 步长程实验：fill=0.999✅，yaw FAIL（无分化），T4.1=0.25x，DA@热源=0.0（需分析） | 2026-07-05 | — |
| T-031 | Step 7：脆弱点3 V_feed→CPC + relay自适应增益（gate control AGC） | 2026-07-05 | a3aa9c6 |
| T-030 | Step 4：consume_nearby 移除（ThermalMouth 摄食切换） | 2026-07-05 | 9c31026 |
| T-031a | repair_cost 累积→瞬时+回归测试重标定（T4.1/T3.2） | 2026-07-05 | d20c443 |
| T-029 | 能量链修复：ThermalMouth eta 0.02→0.06 | 2026-07-05 | 818ce17 |
| T-028 | 饱腹 P1 Step 6：脊髓推挽互抑 Ia interneurons（sg=-1.0, w=0.1） | 2026-07-05 | 6c3fa65 |
| T-027 | 饱腹 P0 Step 5：slow_relay τ 双侧同步 5000→15000 + _W_RS 同步 | 2026-07-05 | 89ac1d5 |
| T-025 | 饱腹 P0 Step 1-3（IntakeSensor钳位+SatietyV_ss验证+Schmitt触发器） | 2026-07-05 | db9819c |
| T-012 | DelayedBundle 前庭接入（Aα/C纤维延迟） | 2026-07-05 | 38eec5c |
| T-011 | Ca²⁺ Phase B（CalciumChannel 接入 HairCell） | 2026-07-05 | 38eec5c |
| T-010 | HC-008 ReleaseNeuron（Ca²⁺→IHC重构） | 2026-07-05 | 38eec5c |
| T-024 | 前庭 Phase B（N=1→3 扩展）| 2026-07-04 | ec582fd |
| T-023 | 规模泛化 Prep（SkinPatch/Body 物理几何属性） | 2026-07-04 | 507921f |
| T-022 | 体感 Phase 3：环流耦合清洁化 | 2026-07-04 | 1121a72 |
| T-021 | P2-8 短程测试：noci 热前锋响应验证 | 2026-07-04 | — |
| T-020 | SomatosensoryChain 12贴片实际激活（T-015遗漏） | 2026-07-04 | 845ebf2 |
| T-015 | 体感重构 Phase 2：4→12贴片扩展（chain.py常量） | 2026-07-04 | c380be6 |
| T-014 | HC-011 shadow全连接（if/elif→21束STDP） | 2026-07-04 | 55bd015 |
| T-009 | HC-010 AGC移除+stub向后兼容 | 2026-07-04 | 55bd015 |
| T-008 | HC-025 MotorRhythm Kuramoto→VdP | 2026-07-04 | fd79dfe |
| T-007 | Ca²⁺ Phase A（CalciumChannel+CalciumDynamics 独立组件） | 2026-07-03 | 7963d28 |
| T-006 | HC-009 Phase 2（ThermalInputNeuron+NociInputNeuron+换能束） | 2026-07-03 | bc6d292 |
| T-005 | HC-009 Phase 1（ThermalInputNeuron 骨架） | 2026-07-03 | 51d4c41 |
| T-004 | EnergyStore 物理化+三接口 | 2026-07-03 | 6b296fd |
| T-003 | HC-016 yaw方向性（thermo_input→yaw bundle） | 2026-07-03 | — |
| T-002 | P0 HC-005/006/013/018 删除+DR5 patch温差 | 2026-07-02 | — |
| T-001 | P2 HC-007/002 relay→enc STDP bundles | 2026-07-02 | 5c2fade |

---

## ❌ 取消/无效

| ID | 任务描述 | 取消原因 |
|:---|:---|:---|
| T-052 | P0-C S2 spinal门槛调整 | S2参数从未被写入代码，当前 v_threshold=0.01 正常工作，v5.0文档分歧已消除 |
| T-049 | P1-D feed_alignment物理重建 | HC-006零值问题已由 T-031（Step7 _v_feed→CPC）解决，不需要再加relay_front路径 |

---

## 使用规则（Claude 操作说明）

### 何时读取
- **每次会话开始**：第一步读取本文件，掌握积压状态
- **用户要求"继续"/"做下一步"时**：先看这里

### 何时写入
| 事件 | 操作 |
|:---|:---|
| 决定做某任务 | 移入"⚡执行中"，写开始日期 |
| 任务完成 | 移入"✅已完成"，填 Commit hash |
| 发现遗留/新需求 | 加入"📋待执行" |
| 用户说暂缓 | 移入"⏸暂停"，写恢复条件 |
| 确认不做 | 移入"❌取消"，写原因 |

### 任务 ID 规则
- 新任务：看当前最大 ID+1，例如已有 T-024 则下一个是 T-025
- 不重复使用旧 ID

### 上下文压缩前
将所有"⚡执行中"的任务备注写清楚（进展到哪一步、下一步是什么），防止压缩后丢失上下文。
