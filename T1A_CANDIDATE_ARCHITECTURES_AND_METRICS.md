# T1A_CANDIDATE_ARCHITECTURES_AND_METRICS — 候选架构族 + 度量合同

日期：2026-09-18
依据：外部《T1-A 执行方案》§10-§11（候选族）+ §15-§19（度量合同/参数
纪律）。**本文档先于诊断实验冻结**；只建立架构候选与参数角色，不冻结
最终参数值（§19）；不以 occurrence 排序（§14）；World v1 仅为
diagnostic stimulus generator（§20）。

---

## 一、候选族（原型实现：`research/transduction_v2/prototypes/`）

### Candidate A — Thin-Amplitude Port（§10.A）
```text
u_A = S·(Y_B − Y_ref)          Y_ref = 静息基线（三点皮肤 rest=0，实测值）
```
- D_i 只做 reference/units/scale；**无 clip、无死区、无适应、无事件筛选**。
- 参数角色：S=[u/T] 尺度（机制扫描用 κ_legacy 同值，非最终值）；
  Y_ref=[T] 静息参考（实测非拟合）。
- 若 L1 需要速率 → 由 L1 自己形成（本轮 L1 READ_ONLY，A 喂幅值给现 L1
  即复演支路 W 错位——诊断中如实测量该错位后果）。

### Candidate B — Explicit Rate Port（§10.B）
```text
u_B(t) = g·(Y_B(t) − Y_B(t−1))      （每步差分，带符号）
```
- 𝒫_Ṫ 的物理身份：**SkinPatch 差分先例**（`world.py:263` dT property，
  RC 接触态 + prev 寄存器）——不藏在无状态 transduce() 名下（§10.B 纪律），
  原型显式声明"单步寄存器"状态。
- 参数角色：g=[u/(T/step)] 速率增益（机制扫描）。
- 语义：与现 L1 端口（dT_raw）一致——半波整流留给 L1（不在 D 预做）。

### Candidate C — Physical Sensor State（§10.C）
```text
ẋ_D = (Y_B − x_D)/τ_a          u_C = g_c·(Y_B − x_D)
```
- 真动态转导器：适应态 x_D（Q1 卡 2/3：受体内慢变基线），u_C = 幅值−
  适应基线（高通/phasic）。参数角色：τ_a=[step] 适应时间尺度、g_c 增益。
- **重复性预警（§10.C 判据）**：τ_a→1 时 u_C→g_c·τ_a⁻¹ 尺度的差分
  ≈ Candidate B——诊断必须测 C 与 B 的输出相关性；且 Q1 卡 2 指明该
  机制的生理载体在 L1 内部，置于 D 层有搬错层+重复上游 SkinPatch 差分
  （支路 P）双重风险。判据：若 corr(u_C, u_B)≈1 或与 L1 应然职责重复 →
  `CANDIDATE_C = REJECT_DUPLICATION`（D 层形态被拒；L1 内部形态另行
  登记，非本轮范围）。

### Negative control — legacy affine+clip（§24）
```text
u_L = clip[κ(Y_B − q0) + b, 0, 0.04]      （REFERENCE_TRANSDUCTION_CONFIG 原样）
```

### Mathematical control — 宽动态范围函数（§24，明确标注非项目结构）
```text
u_M = a·asinh(s·(Y_B − Y_ref))            MATHEMATICAL_CONTROL
```
- 仅回答"只追求数值表现能到什么程度"；**不得升级为 candidate**（§11：
  无 Q1 机制对应，asinh 只是压缩函数）。

## 二、度量合同（§15-§18，先冻结）

对每场景/每候选并报（禁止裸 ratio；任何归一值必须同报分子分母）：
- `D_boundary_abs/norm`、`D_port_abs/norm`、`D_L1_abs/norm`
  （L1 读出 = `clip(max(0, u×200), 0, 10)`——现 L1 方程原样，READ_ONLY 消费）；
- 占用率：zero（|u|≤1e-12）/ saturation（命中候选自身上界，无界候选记 0）
  / interior（legacy 记 [0.005,0.03]，其余记非零非饱和）；
- sign preservation（降温段 u<0 是否可表达）；peak timing（argmax u vs
  argmax q offset）；rise-time sensitivity（R4 对内 D_port）；decay
  sensitivity（撤源段 D_port）。
- **§16 假放大防护**：D_port_norm > D_boundary_norm 时不得写
  "information amplified"，必须查绝对值——若归一上升仅因共同基线被抹 →
  `BASELINE_ZEROING_ARTIFACT = TRUE`。
- **§17/§18**：不设最佳 retention；每候选保存最大保留/最大丢失/最大
  假放大/最严重地板/最严重饱和/最明显时序丢失六类极端案例；禁综合评分、
  禁 WINNER（§25）。

## 三、R1-R8 诊断重放套件（§13；A2 修正：逐场景声明 Y_B 配置）

刺激源：三点皮肤 TEST 档（World v1 = diagnostic stimulus generator）。
除 R5 外 Y_B 配置均为 `BOUNDARY_REDUCED_N0`（node0 单节点）；R5 即
WT0 正对照协议原样（本身即 REDUCED_N0）。

| # | 场景 | 构造 | 攻击目标 |
|---|---|---|---|
| R1 | 静息附近小偏离 | node0@0.02 持续 300 步 | 全地板化 |
| R2 | 缓慢升温 | 线性 ramp 0→1.0 注入 1500 步 | 幅值/速率混淆 |
| R3 | 快速升温 | node0@1.0 阶跃持续 | 真速率敏感性 |
| R4 | 同峰值不同上升速度 | A: 恒流 600 步；B: 线性 ramp 600 步，末端幅值按线性叠加原理缩放使 T(600) 相等 | amplitude vs rate 核心区分 |
| R5 | 同当前值不同历史 | WT0 正对照协议原样（A: node0@1.0×100 / B: node2@1.996×100，t0=99 后撤源） | 候选是否私加历史 |
| R6 | 大幅输入 | node0@50 持续 2000 步 | ceiling collapse |
| R7 | 弱输入 | node0@0.1 持续 2000 步 | floor collapse |
| R8 | 脉冲 vs 持续 | w0e Γ_A（恒流 300）vs Γ_C（6×25×2 双脉冲）等能量 | 时序结构保留 |

## 四、参数纪律（§19）

本轮冻结：参数**角色**（S/g/τ_a/g_c 的量纲与物理意义）+ 合法域
（正值；τ_a≥1 step）。不冻结：任何最终值。禁止 grid search →
maximize → freeze（诊断只做机制扫描：每候选一组代表值跑全套 R，
不选优）。原型不被 nexus/tss import（§12）。
