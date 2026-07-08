# DA=1.0 修复方案评判 — Fix-2 可逆性缺陷分析

**日期：** 2026-07-08
**评判对象：** `cell-cell/交叉报告/DA=1.0 根因诊断与修复方案（修订版）.md`（AG 平台，D:\cell-cc\2026.7.6）
**核对基准：** 当前 J:\cell-cc 母本 `variant_adapter.py` / `modulator.py` / `bundle.py`
**结论：** Fix-2 会把 DA 钉死在 0 且不可逆；Fix-1 治标不治本。方案数值反推、违反 model-before-tune。

---

## 一、结论摘要

修订版方案含两处改动：

| Fix | 改动 | 评判 |
|-----|------|------|
| Fix-1 | shadow_to_da `initial_weight` 0.05 → 0.01 | ❌ 治标不治本——shadow 是 frozen 束，权重不会长，病灶在 shadow 内部 BCM 发散 |
| Fix-2 | satiety_to_da `sg` −1.0 → −5.0, `w` 0.3 → 1.0 | ❌ 致命——把 DA 钉死在 0，破坏撤源后的再动员与跨周期学习 |

方案给出的预期数值表（贴源 DA≈0.01 / 远源 DA≈0.07）在当前架构下**物理不可实现**。

---

## 二、决定性架构事实：DA 浓度不是"净输入的线性映射"

方案表格假设 `净DA输入 → DA浓度` 线性（−4.0 → 0.01；+0.07 → 0.07）。真实映射见
`variant_adapter.py:2224-2225`：

```python
mean_da = sum(n.activation for n in self.da_neurons.values()) / max(len(self.da_neurons), 1)
self.dopamine._concentration = max(0.0, min(1.0, mean_da))   # 硬钳位 [0,1]
```

三点后果，全部推翻方案表格：

1. **modulator baseline=0.1 被旁路。** `dopamine.step()` 不被调用（L2226 注释明说"concentration is set structurally"）。不存在"衰减回 0.1"的兜底。
2. **地板是 0.0，不是 0.01。** 任何净负输入把 `mean_da` 压到负值，clamp 后是**精确的 0.0**。表中"~0.01""~0.07"是反推目标值，架构给不出这种精度。
3. **正向托底只有 bc_current ≈ 0.30**（诊断表自列）。satiety 注入 −1.0 以上即淹没托底 → `mean_da` 变负 → DA=0。

---

## 三、Fix-2 为什么"不可逆归零"

### 3.1 satiety 的慢电容尾巴

satiety_neuron 本身 τ=50 步（`C=50, r_leak=1.0`, `variant_adapter.py:1038`），但主输入
`intake_to_satiety`（L1053）来自 intake_sensor 的 feed 电容，**τ≈5000 步**
（L1050-1051 推导 V(30k)≈0.52V）。诊断表实测：**热源移除 5000 步后 satiety 仍在 −0.10**。

### 3.2 −5.0 增益把残余放大到淹没托底

satiety→DA 注入 `I = sat_act × G(w) × sg`（propagate 见 `bundle.py:261-262`）。
Fix-2 同时抬 w(0.3→1.0，Memristor 电导 G(1.0)/G(0.3)≈2–3×)与 sg(−1.0→−5.0)：

```
注入放大 ≈ [G(1.0)/G(0.3)] × [5.0/1.0] ≈ 10–15×
当前 −0.10 的注入 → Fix-2 下变成约 −1.0 ~ −1.5
```

即撤源 5000+ 步、身体**正应饥饿去找新源的再动员窗口**，satiety 仍往 DA 灌 ≈ −1.0，
+0.30 bc 托底与上升的 hunger 全被淹没 → **DA ≡ 0**。

### 3.3 与 P0 冻结叠加 → 半永久冻结

P0（DA_ema）语义：DA_ema→0 时 LTP 与 LTD **同步**归零 → 权重"保鲜冻结"。这是为
"奖励自然缺失"设计的。但 Fix-2 的 DA=0 是"satiety 强按"，代码无法区分二者
（都只是 `mean_da` 变低）。结果：

- 再动员窗口 DA 被钉 0 → LTP 门=0 → 新源路径**学不动**
- T-072 的正面证据（T_relocate3 比 T_relocate2 快 65% 的跨周期迁移）会被**直接抹掉**
- 刚起步的方向学习（memory 记 |Δw|=0.02）随之作废

**一句话:原 bug 是"该睡不睡(DA 卡 1.0)",Fix-2 把它翻成"该醒不醒(DA 卡 0)",后者更坏。**

---

## 四、Fix-1 治标不治本

诊断把 BUG-1 定为"shadow_to_da 0.75→3.09 正反馈"，Fix 是砍权重 0.05→0.01。但
`variant_adapter.py:2905`：

```python
learning_rule="frozen",   # shadow_to_da 是冻结束
initial_weight=0.05,      # 且注释明确 w=0.05 正确，"DA sleeps"是历史 gm=8.0 bug
```

**冻结束权重不可能增长。** 0.75→3.09 来自 shadow **列神经元 calcium_rate 上升**——即
shadow 内部 enc→col 的 BCM 自激（`stdp_lr=0.01, synapse_gain=10.0`）。这正是 CLAUDE.md
记录的已知未解问题**"shadow-layer free energy diverges, K_ema grows unbounded"**。

因此 Fix-1 只是把发散输出 ×1/5，推后饱和、不消除发散。calcium_rate 继续无界增长，
w=0.01 迟早仍把 DA 顶到 1.0。真正病灶在 shadow 内部 BCM 缺稳态约束（滑动阈值 θ_M /
突触归一化），不在输出束权重。

---

## 五、实证：T-083 DA 可逆性对照实验

**脚本：** `nexus_v1/tests/exp_T083_da_reversibility.py`
**设计：** 三段（贴源饱腹 → 撤源再动员 → 新源重现），两条件对照
（baseline sg=−1.0 vs Fix-2 sg=−5.0/w=1.0，实例级 mutate，不改母本）。

**判据：**
- R1：baseline 撤源后 DA 可回升 > baseline(0.1) — 证明当前系统可逆
- R2：Fix-2 撤源期 DA_mean < baseline条件 × 0.5 — 证明 Fix-2 压制再动员
- R3：Fix-2 撤源期 DA 被钉在 ~0（min<0.02 且 mean<0.05）— 核心质疑证实

**实测结果（T-083 完成）：**

| 指标 | baseline (sg=−1.0) | fix2 (sg=−5.0,w=1.0) |
|------|------|------|
| satiety→DA 注入电流 | −0.06 ~ −0.10 | **−21 ~ −42** |
| Phase2 撤源再动员 DA_mean | 1.0000 | **0.0000** |
| Phase3 新源重现 DA_mean | 1.0000 | **0.0005** |

- **R2 PASS / R3 PASS：** Fix-2 使 satiety 注入 **−21~−42 A**（不是方案预期的温和抑制），
  DA 在**所有阶段**（含再动员、新源重现）被钉死 **0.0000**。
- 方案预期表"贴源 DA≈0.01 / 远源 DA≈0.07"**完全不成立**——实测 DA ≡ 0.0，无任何动态范围。
- **确认核心质疑：** Fix-2 把"DA 卡 1.0"翻转成"DA 卡 0.0"，两者都是死信号；再动员窗口 DA≡0
  → 跨周期学习被摧毁。

> **补充（T-084 溯源，见下）：** baseline 的 DA≡1.0 并非 satiety 太弱所致，而是
> **intake_to_da_reward（进食期注入 8~14 A）和 shadow_to_da（撤源期涨到 3.5）两个源电流严重超标**。
> 这说明 DA 源电流整体失标：正向源 +8~14、Fix-2 的负向源 −21~−42，都比生理量级（O(0.1)）大 1~2 个数量级。
> **真正的修法是重标源电流，不是加 satiety 反力，也不是重写 DA 浓度映射。**

---

## 六、正确方向（建议）

1. **先只上 Fix-1 并验证，别叠 Fix-2。** 若 shadow 砍到 0.01 后贴源期 DA 能自然回落，
   症状够用；若很快复发，证明病灶在 shadow 内部发散 → 去修 BCM 稳态（θ_M 滑动阈值或
   权重归一化），而非加 satiety 反力。
2. **satiety 若确需增强，在 −1.0 的原推导框架内小步上调**（如 −1.5），保留"不静默"
   下界（贴源期 DA 应 ≈ baseline 的 30–40%，不是 0），使 P0 冻结是"温和保鲜"而非"强按到死"。
3. **satiety 应调制 learning window（lr_factor）而非把 concentration 拖到 0。** P0 要的
   是 LTP/LTD 同步归零，不是 DA 本身被外力钉 0。
4. **验证判据必须加"可逆性"检查。** 方案原验证计划（diag/Test1/Test3）只查"DA 是否降下来"，
   未查"新源出现后 DA 能否回升、权重能否解冻"。须加：撤源→重现后 DA 在 N 步内恢复 > baseline
   且 relay→yaw 权重重新可塑——这正是 Fix-2 会挂掉的地方。

---

## 七、规范违反登记

- **magnitude 无推导：** Berthoud 2008（POMC→VTA 抑制）只支持 satiety→DA 的**符号与存在性**，
  不支持 −5.0 的量级。原 −1.0 有推导（L3138-3139：satiety_act=0.5→抑制到 baseline 35%）。
  方案弃之，反推一个能压出"0.01"的数 = RULES.md 禁止的"改参数看能不能过"。
- **把行为目标写进参数：** 为"贴源→DA≈0"选 −5.0，等于把行为结论编码进增益（语义硬编码变体）。

---

*评判者：Claude Code，2026-07-08。核对基准 commit 4bb83b1。*
