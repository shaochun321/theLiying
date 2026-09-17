# F1_FEEDBACK_POWER_CONTRACT — 反馈供能物理契约（第四轮 P0-2）

日期：2026-09-18
依据：`cell-cell/交叉比对/F1 A8-v2 最小物理闭合复审 — Agent 执行方案.md` §五/§六
状态：本契约先于任何代码修改冻结；rail 因果化实现必须逐条符合本契约。

---

## 一、契约四问

### Q1. `MOSFET.conduct(v_gate)` 的物理含义

母体实现（`nexus_v1/components/semiconductor.py:141-167`）：

```
I = gm × (V_gs − V_th)    （超阈线性；无 V_ds 参数）
```

**裁定：母体 `conduct()` 的语义是 A——"已假设 drain/source 理想供电存在后的漏极电流"。**
证据：(1) 无 V_ds 依赖，V_ds 饱和假设隐含；(2) 母体 `PowerRail.draw()` docstring
（semiconductor.py:287-311）明确设计为"draw current, return available voltage
after IR drop"，即供电约束本应由调用方消费返回电压来实现——第三轮 RailLatch
丢弃了该返回值（rail_latch.py:102），把隐含假设"理想供电"变成了无条件事实。

**契约要求：在 F1 反馈支路中，`conduct()` 的输出今后只能作为"理想供电下的
期望电流"（外部方案的 B 理解），不得直接注入电容。实际反馈电流必须显式经过
供能端裁定（见 Q2-Q4）。**

### Q2. I_fb 的能量由哪个物理端提供

**PowerRail（drain 端供电源）。** 输入电流 `k_in·u` 的能量由上游 relation
链路提供（换能接口，维持现状）；反馈电流 I_fb 的能量从本轮起必须显式来自
rail：I_fb 是 rail 输出电流的一部分，rail EMF 做功 = ∫vdd·I_fb·dt。

### Q3. V_supply = 0 ⇒ I_fb = 0

由实现结构**自动**满足（不是靠 if 检查）：I_fb = G(V_g)·V_supply，
V_supply=0 时乘积恒为 0。断电后高态由 RC 泄漏自然衰减（τ = RC = 0.6 s），
不存在任何维持通路。

### Q4. 有限内阻 R_s > 0 的 I–V 自洽关系

电导支路与电源内阻串联，负载线交点封闭解：

```
V_supply = vdd − I_fb·R_s          （rail 端）
I_fb     = G(V_g)·V_supply          （电导支路端）
⇒ I_fb     = G·vdd / (1 + G·R_s)
  V_supply = vdd / (1 + G·R_s)
```

这是每步内的静态电路方程求解（构造期/解析数学，非行为 if），物理对应
"电导负载 + 内阻分压"。R_s=0 退化为 I_fb = G·vdd。`v_actual` 不再只是
日志字段，而是动力学量。

---

## 二、路径选择：B（显式电导原语）

### 路径 A（受控电流支路 I_fb = F(I_request, V_supply, R_s)）——不采用

F() 无唯一物理形式（min/线性缩放/软饱和均可辩护），自由度过大，任何选择
都难以通过 Q3 参数依据审查（"任意经验缩放"风险）。仅当路径 B 失败时回退
重审。

### 路径 B（I = G(V_g)·V_supply）——采用

1. **物理对应直接**：即真实 MOSFET 线性（triode）区方程
   I_D = k′·(V_GS−V_th)·V_DS 的小 V_DS 段。BIO/SEMI 对应无需发明。
2. **量纲闭合**：G(V_g) = g_c·max(0, V_g−θ)，[g_c]=S/V，[G]=S，
   [G·V_supply]=A ✓。
3. **数值零成本**（与第三轮 N=3≡k=3 同模式）：canonical v_rail=1.0、
   R_s=0 时 I_fb = g_c·(V_g−θ)·1.0；取 g_c 数值 = gm 数值（1.0）则与现
   `conduct()` 输出逐位一致 ⇒ 外部已复现的 M1–M4 基线预期原样保持，
   资格判据未被调参改动（方案 §二 约束）。
4. **g_c 的 Q3 依据**：g_c = gm / V_ref，V_ref = vdd = 1.0 V（母体
   PowerRail 默认 = entry_gate _DEFAULT_V_CLAMP）。含义："额定供电 1.0 V
   下电导支路输出等于原 transconductance 支路"。这是单位换算
   （A/V ÷ V = S/V），不引入新自由参数。

### 实现红线

- 不修改母体 `nexus_v1/components/semiconductor.py`（MOSFET 不加
  conductance API）；电导语义在 research 层 RailLatch 内实现：
  读取 FET 的 `gm`/`v_threshold` 器件参数组成 G(V_g)，不调用返回 A 的
  `conduct()` 冒充电导。
- 解析层（analytic_step / fixed_points / 离散-连续固定点函数）同步加入
  V_supply 项，否则解析-实验 0 容差比对假失败。
- `PowerRail.draw(I_fb)` 的返回电压即 V_supply 的实测通道；R_s>0 时以
  负载线封闭解为准，并断言 draw() 返回值与封闭解一致（一致性自检）。

---

## 三、断电-恢复判据（含 T_off 器件历史效应）

电容残压是物理残留，不是非法记忆。解析预测：断电后
V(t) = V_off·exp(−t/τ)，τ=0.6 s（600 步）。恢复供电时刻残压 V_res 与
不稳定固定点 V_u 的关系决定行为：

- **V_res < V_u ⇒ 回落 0 态**（不记起）——合法必须行为；
- **V_res > V_u ⇒ 反馈重新点火回高态**——电容动态节点的正常物理
  （DRAM 同理），登记为 `DEVICE_HISTORY: CAPACITIVE_RESIDUE`，不算
  "自动记起"违规，但必须与解析临界时间一致：

```
T_off* = τ·ln(V_off / V_u)
```

canonical（V_off=1.0 钳位读数，V_u 按 N=1 解析值）下 T_off* ≈
τ·ln(1/0.301) ≈ 1.20τ ≈ 720 步。

**验收判据**（exp_F1_rail_causality.py）：
1. 断电期间每步 I_fb = 0（逐位）；
2. T_off 扫描 {0.1τ, 0.5τ, 1τ, 2τ, 5τ}：重新点火/不点火的分界与 T_off*
   预测一致（允许 ±1 步离散误差）；
3. T_off > T_off* 的所有档位：恢复供电后不回高态（除非输入历史重新形成
   候选）；
4. 若观察到与解析预测不符的记忆行为 ⇒ 登记新器件历史效应，另审，
   不得并入本轮资格结论。

---

## 四、因果能源账本（P0-4）

每步记录（八字段，方案 §八）：

| 字段 | 定义 |
|---|---|
| requested_feedback_current | G(V_g)·vdd（理想供电期望值） |
| delivered_feedback_current | G·vdd/(1+G·R_s)（实际注入） |
| supply_voltage | vdd/(1+G·R_s) |
| supply_current | = delivered_feedback_current |
| supply_energy | Σ vdd·I_fb·dt（EMF 做功） |
| stored_capacitor_energy | Q²/2C |
| clamp_dissipation | 现 _e_clamp（Zener/finite 记账维持） |
| rail_internal_dissipation | Σ I_fb²·R_s·dt |

局部闭合检查：

```
E_supply + E_input ≈ ΔE_stored + E_leak + E_clamp + E_rail_loss
E_input = Σ v_node·(k_in·u)·dt      E_leak = Σ v²/R·dt
```

离散 Euler 记账存在 O(dt) 残差：判定标准为**残差/总吞吐随 dt 一阶收敛**
（dt、dt/10、dt/100 三点验证）。收敛 ⇒ LOCAL_ENERGY_CLOSURE=AUDITABLE；
不收敛 ⇒ LOCAL_ENERGY_CLOSURE=NOT_MET 如实登记，不得再写
ENERGY_SUPPORT=EXTERNAL_IDEAL_RAIL 为已证事实。

---

## 五、生效范围

- canonical 更新：N_feedback=1（外部实测 N=1 双稳 + 上一轮 §10 自认
  N≥1 恒双稳 ⇒ N=3 非最小）；新 fingerprint 在 rail 因果化 + N=1 落地后
  重新生成，旧 `72c828f910f7243b` 作废为历史指纹。
- M1–M5 全部从零重跑，不继承 F1_M5_VALIDATED；新增 M5-P 门
  （断电零流 / 断电失忆 / 账本可审计）。
- F3/F5 冻结；K-07 仅在 F1_A8v2_PHYSICALLY_VALIDATED 后开启。
