# 客观评判：Doc 6.11.1 & 6.11.2 + Shadow 生长审计

---

## 一、两份文档的逐点评判

### Doc 6.11.1（"物理引擎总架构师"角色）

| 指令 | 准确性 | 备注 |
|---|---|---|
| τ=100 vs τ=0.5 阻抗匹配 | ✅ **正确且关键** | 热扩散 ~1s vs 机械 ~5ms → 200× 差异真实存在 |
| SomatoRelay lateral inhibition = 拉普拉斯算子 ∇²T | ✅ **数学正确** | 中心兴奋+环绕抑制 = 离散拉普拉斯，天然梯度放大 |
| Thermo→Reg, Noci→Irr 分化 | ✅ **你已接受** | 温度慢=DC, 伤害快=AC，与前庭 reg/irr 物理对称 |
| SomatoRelay 抑制 gain < 0.05 防刚性振荡 | ✅ **正确** | dt/τ=0.001/τ_relay, 如果 gain 过大确实会 ping-pong |
| v_threshold 锚定物理毁损线 | ✅ **你已确认** | 物理参数决定阈值，不是标签 |
| Binding C(N,2) 维度诅咒 → metabolic_tax 自然修剪 | ✅ **正确机制** | 已有: `_apply_metabolic_tax()` 每 100 步耗能 |
| P_ν × P_th ≠ const，而是 Lyapunov 追踪 | ⚠️ **可能正确但需验证** | 守恒 vs 追踪关系是实验问题，不是理论可定的 |

**Doc 6.11.1 的核心洞察**（值得采纳）：
- "RC 频响替你把数学算完了"——正确。我们不需要写 dT/dt 代码，Capacitor.leak() 本身就是低通滤波器。
- P_ν 滞后追踪 P_th 的相图预测——如果成立，这比乘积守恒更有信息量。可以在第二主体建成后用实验数据画 P_ν vs P_th 相图验证。

**Doc 6.11.1 的问题**：
- ⚠️ 再次提到"数值气蚀"——上次分析已确认 dt/τ = 0.001 远不到不稳定区，但提醒仍有价值（如果 τ_relay 设得很小会出问题）。
- ⚠️ "damage_integral > 0" 隐含了一个新的物理量（皮肤损伤积分），这需要 B.00 刚体壳先定义"损伤"的物理含义。

### Doc 6.11.2（系统性评审角色）

| 指令 | 准确性 | 备注 |
|---|---|---|
| 热测度与运动测度的对称映射 | ✅ **准确总结** | dT/dt ↔ dω/dt, ΔT ↔ θ, ν_th ↔ ν |
| T·S·I 框架无需修改即可适用 | ⚠️ **部分正确** | T 和 S 可以直接用，但 I(= mean_xi) 需要确认 Xin 如何在新 patch bundles 上计算 |
| ν × ΔT 是 STDP 方向学习信号 | ✅ **正确** | 因果相关性是方向涌现的物理基础 |
| SomatoRelay = 结构即计算 | ✅ **准确** | 拓扑编码空间，不是坐标编码 |
| τ 桥接不创建新组件 | ✅ **准确** | TemporalCoupler 已有，改参数就行 |

**Doc 6.11.2 的价值**：系统性、无遗漏的总结。适合作为外部检查清单。

---

## 二、Shadow 自适应生长机制审计

### 现有机制

| 机制 | 状态 | 位置 |
|---|---|---|
| STDP 权重学习 | ✅ 生效 | `shadow_sandbox.py:413` — `bundle.learn(dt)` |
| Silent synapse (休眠/唤醒) | ✅ 生效 | `shadow_sandbox.py:470` — `_manage_silent_synapses()` |
| ECM + PNN (临界期调制) | ✅ 生效 | `shadow_sandbox.py:294-315` — `ecm_enc/col/mot` |
| Weight change rate (新异性信号) | ✅ 生效 | `shadow_sandbox.py:723` — `_update_weight_change_rate()` |
| Vascular cooling | ✅ 生效 | `shadow_sandbox.py:438` — `vascular.step()` |
| δa baseline tracking (M1) | ✅ 生效 | `shadow_sandbox.py:664` — `_update_baselines()` |
| κ contraction degree (M3) | ✅ 生效 | `shadow_sandbox.py:681` — `_update_kappa()` |

### 缺失机制

| 机制 | 状态 | 说明 |
|---|---|---|
| **Sprouting (沉积)** | ❌ **不存在** | Shadow sandbox 没有 `_structural_growth()`。主系统的 `hebbian._structural_growth()` 不操作 shadow bundles |
| **Pruning (修剪)** | ❌ **不存在** | 同上。Shadow 的 silent synapse 只做休眠/唤醒，不删除 |
| **Mitosis (有丝分裂)** | ❌ **不存在** | Shadow 没有 `_check_mitosis()`。Shadow 神经元数量固定 |
| **Metabolic tax** | ❌ **不存在** | Shadow bundles 不被 `_apply_metabolic_tax()` 覆盖 |

### 结论

> [!WARNING]
> Shadow 层有**权重可塑性**（STDP + silent synapse），但没有**结构可塑性**（sprout/prune/mitosis）。
> Shadow 的拓扑在 `initialize()` 时固定，之后永不改变。这意味着 Merzenich 1984 式的「使用依赖重组」在 shadow 层**未实现**。

这是否是问题取决于设计意图：
- 如果 shadow 是"结构固定的预测器"（frozen topology, plastic weights）→ **当前状态合法**
- 如果 shadow 需要"动态生长来适应新模态"（热 patch 加入后 shadow 需要扩展）→ **需要实现**

---

## 三、用户决策记录

| 开放问题 | 用户决定 | 来源 |
|---|---|---|
| Reg/Irr 分化 (8.1) | ✅ 接受: Thermo→Reg, Noci→Irr | "接收建议" |
| SomatoRelay lateral inhibition 参数 (8.2) | ✅ 从 gain=0.05 开始，**可反馈调节** | 明确指定 |
| 热源分化阈值 (8.3) | ✅ 由 nociceptor v_threshold 决定（物理参数） | 已确认 |
| Binding Layer 交互 (8.4) | ❓ 这似乎是"平行的测试方向" | 需要澄清 |

### 关于 Q4 (Binding Layer)

用户说"这似乎是平行的测试方向"。这是准确的：

Binding Layer 的 C(n,2) 扩展可以**独立于**核心感受链构建。核心链是 B.00→B.01→B.02→B.02b→B.03→B.04（必须串行），而 Binding 扩展只需要 B.02 完成后新轴加入 `all_axes` 即可自动触发（代码已有 `col_act_dict = {ax: ... for ax in self.all_axes}`）。

```
串行路径 (阻塞):   B.00 → B.01 → B.02 → B.02b → B.03 → B.04
平行路径 (可同时):  B.02 完成后 → Binding 自动扩展 (无额外代码)
                              → metabolic_tax 自然修剪 (已有)
```

所以 Binding 扩展确实是平行测试方向，不在关键路径上。
