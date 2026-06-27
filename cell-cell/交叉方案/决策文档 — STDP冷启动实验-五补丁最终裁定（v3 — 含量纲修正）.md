
> 文档性质：正式设计决策记录  
> 日期：2026-06-25  
> 状态：最终裁定，可进入实施  
> 相关文档：批次1问题清单、批次2规格、交叉比对分析  
> 实验：《STDP独立涌现趋热行为 — 冷启动实验方案》  
> 版本：v2 — 含 YolkSac 量纲修正


## 一、裁定的参数与设计决策

以下五项均在批次1中被标记为“待澄清”，在本决策文档中逐条给出最终裁定。


### 决策 D01：σ₀ 数值（ISSUE-01）

| 项目 | 内容 |
|------|------|
| 问题 | `langevin_noise.py` 中 σ₀=0.70，但实验文档写 σ₀=0.07，两者差10倍 |
| 裁定 | **σ₀ = 0.70 保持不变** |
| 数理依据 | 实际输出噪声由 $\sigma_{\text{eff}} = \sigma_0 \cdot \sqrt{T_{\text{bath}}}$ 给出。$T_{\text{bath}} \approx 0.01$ 时，$\sigma_{\text{eff}} = 0.70 \times 0.1 = 0.07$，与文档目标一致。若改为 0.07，实际输出变为 0.007，即使在 AGC 放大 6 倍后（$0.007 \times 6 = 0.042$）仍无法跨越 Motor 阈值 $[0.15, 0.35]$。0.70 是涨落耗散定理中的底层乘子，不是输出噪声幅度 |
| 代码位置 | `langevin_noise.py:L64` — 保留 `sigma0=0.70` |
| 注释更新 | 补充注释，说明 0.70 是底层乘子，实际输出受 T_bath 调制 |


### 决策 D02：τ_w 生物来源与数值（ISSUE-02）

| 项目 | 内容 |
|------|------|
| 问题 | 强制三问 Q1 要求生物对应，实验文档只写了“估计值” |
| 裁定 | **τ_w = 30 步，生物对应为短时程易化（STF）快成分** |
| 数理依据 | Binding 激活为时序卷积：$\tilde{V}_i(t) = \int_0^{\tau_w} V_i(t-s) \cdot e^{-s/\tau_w} \, ds$，$B_{ij}(t) = \tilde{V}_i(t) \cdot T_j(t)$。$\tau_w$ 覆盖运动→热变化传导延迟时，$B_{ij} > 0$，STDP 获有效因果配对。Zucker & Regehr (2002) 综述中突触前钙残余（presynaptic calcium remnant）导致的短时程易化快成分时间常数在 20-50ms 区间，30ms 为该区间合法值 |
| 代码位置 | 新建 `TemporalBindingCell`（方案B），`tau_w=30` 配置项 |
| 注释格式 | `# BIO: Short-Term Facilitation (STF) fast calcium remnant (tau ~20-50ms). Zucker & Regehr 2002.` |


### 决策 D03：η_da 增益值与标定策略（ISSUE-03）

| 项目 | 内容 |
|------|------|
| 问题 | 批次2中 `eta_da` 留作 `ETA_DA_TBD`，未指定数值 |
| 裁定 | **η_da = 7.5（初始值），配合独立标定实验 EXP-CAL-DA 微调** |
| 数理依据 | DA 释放锚定于能量变化率：$DA(t) = \max(0, \eta_{da} \cdot d(\text{fill})/dt)$。典型进食脉冲 $d(\text{fill})/dt \approx (0.12 \times 0.9)/1000 \approx 1.08 \times 10^{-4}$。目标 DA 峰值（旧系统工作点）$DA_{\text{peak}} \approx 0.8$，则 $\eta_{da} = 0.8 / 1.08 \times 10^{-4} \approx 7.4 \approx 7.5$。`clip_max=5.0` 提供防爆保护 |
| 代码位置 | `DADifferentialConfig.eta_da = 7.5` |
| 标定预留 | EXP-CAL-DA：在固定进食脉冲下测量 DA 输出，微调 η_da 使峰值稳定在 0.5-0.8 区间 |


### 决策 D04：Phase 0 与 Phase 1 执行时序（ISSUE-04）

| 项目 | 内容 |
|------|------|
| 问题 | 批次1询问 Phase 0（五补丁落地）与 Phase 1（移除 process_hunger）是否允许分阶段执行 |
| 裁定 | **原子级同步** |
| 数理依据 | 若分步执行，存在中间状态 $I_{\text{motor}} = \eta_{\text{Langevin}} \cdot (1 + G_{\text{agc}}) + \eta_{\text{hunger}} \cdot G_{\text{agc}}$，两股电流在 Motor 膜上方向可能相反，STDP 学到的是两股信号的混合统计量而非单一策略。同步执行则 $I_{\text{motor}} = \eta_{\text{Langevin}} \cdot (1 + G_{\text{agc}})$，唯一运动源为 Langevin 噪声，STDP 学习单一因果链 |
| 执行方式 | 五补丁 + process_hunger 注释移除，在同一次提交中完成 |


### 决策 D05：BindingCell 修改策略（ISSUE-05）

| 项目 | 内容 |
|------|------|
| 问题 | 批次1提出方案A（原地修改）和方案B（子类扩展），询问选择 |
| 裁定 | **方案B：子类扩展（TemporalBindingCell）** |
| 数理依据 | BindingCell 母类是空间 AND 门：$B_{ij}^{\text{space}}(t) = V_i(t) \cdot T_j(t)$。时间扩展子类添加记忆核：$B_{ij}^{\text{temp}}(t) = \left( \int_0^{\tau_w} V_i(t-s) e^{-s/\tau_w} ds \right) \cdot T_j(t)$。当 $\tau_w \to 0$ 时子类退化为母类，两者正交。符合“不改母代码”原则 |
| 代码位置 | 新建 `components/binding_temporal.py`，实现 `TemporalBindingCell(BindingCell)` |


## 二、YolkSac 量纲修正（补丁 C）

### 修正前的问题

原设计 $\lambda_{\text{yolk}} = 0.002$，`transfer = λ_yolk × dt`，$dt = 0.001$。

每步注入：$2 \times 10^{-6}$，100k 步总注入：0.2。目标为 200 单位，差距 1000 倍。

### 修正后

**裁定：$\lambda_{\text{yolk}} = 0.002$ 保持不变，`step()` 中不乘以 $dt$**

$$\text{transfer} = \lambda_{\text{yolk}} = 0.002 \text{ 单位/步}$$

100k 步总注入：

$$E_{\text{total}} = 0.002 \times 100000 = 200$$

**量纲说明**：$\lambda_{\text{yolk}}$ 的量纲是“单位/步”，与 EnergyStore 的 `basal_drain` 同量纲，不乘以 $dt$。

### 设计意图：温和热力学逆差

$$\lambda_{\text{yolk}} = 0.002 < \bar{P}_{\text{out}} \approx 0.006$$

释放率低于平均代谢消耗率，产生温和热力学逆差 $\Delta P = \bar{P}_{\text{out}} - \lambda_{\text{yolk}} \approx 0.004$ 单位/步。效果：fill 缓慢下降，AGC 缓慢爬坡，给 STDP 留出学习窗口。补给耗尽时刻 $\approx 200 / 0.004 \approx 50k$ 步，与学习窗口预期一致。


## 三、五补丁最终参数汇总

| 补丁 | 组件 | 参数 | 值 | 数理形式 |
|------|------|------|-----|---------|
| A | LangevinNoise | σ₀ | 0.70 | $\sigma_{\text{eff}} = \sigma_0 \cdot \sqrt{T_{\text{bath}}} \cdot (1 + G_{\text{agc}})$ |
| A | AGC→Langevin | G_agc 接入 | 乘法调制 | 同上 |
| B | TemporalBindingCell | τ_w | 30 步 | $\tilde{V}(t) = \int_0^{\tau_w} V(t-s)e^{-s/\tau_w}ds$ |
| C | YolkSac | yolk_initial_level | 200 单位 | $E_{\text{yolk}}(t) = 200 - 0.002 \cdot t$ |
| C | YolkSac | λ_yolk | 0.002/步 | 不乘 dt，与 basal_drain 同量纲 |
| D | DADifferentialGate | η_da | 7.5 | $DA(t) = \max(0, \eta_{da} \cdot d(\text{fill})/dt)$ |
| D | DADifferentialGate | clip_max | 5.0 | 防爆保护 |
| E | Efference Copy 监控 | 抑制阈值 | 0.9 | $R_{\text{supp}} = N_{\text{supp}} / N_{\text{total}}$ |


## 四、执行顺序（原子级同步提交）

```
提交：STDP冷启动实验 — 五补丁 + 移除 process_hunger

文件变更清单：
  [NEW]  components/yolk_sac.py                 （补丁C）
  [NEW]  components/da_differential_gate.py     （补丁D）
  [NEW]  components/binding_temporal.py         （补丁B）
  [MOD]  components/langevin_noise.py           （补丁A：sigma0 注释确认）
  [MOD]  components/agc.py                      （补丁A：输出端重路由）
  [MOD]  circuit/variant_adapter.py             （五补丁集成 + process_hunger 移除）
  [MOD]  circuit/binding.py                     （不改母代码，仅确认接口）
  [MOD]  components/spinal_reflex.py            （process_hunger 返回零值 + 废弃警告）
```

提交后状态：
- process_hunger 不再产生任何 Motor 驱动
- AGC 输出端重路由至 Langevin 噪声幅度
- Binding Cell 获得时间卷积窗口
- 卵黄囊向 EnergyStore 单向供能
- DA 释放锚定于 d(fill)/dt
- Efference Copy 抑制比例开始记录（供监控，不参与控制）


## 五、待监控项（运行阶段）

| 监控项 | 目标 | 告警条件 |
|--------|------|----------|
| Efference Copy 抑制比例 | < 0.9 | ≥0.9 提示检查阈值 |
| Binding Cell 激活频率 | 稳定 | 连续 10k 步无激活 |
| DA 峰值 | 0.5-0.8 区间 | >0.8 持续 1k 步或 =0 持续 10k 步 |
| YolkSac 剩余水平 | >0 至 100k 步 | 提前耗尽则增加 yolk_initial_level |
| fill_fraction 冷启动期 | 第 50k 步 >0.1 | 低于阈值则需增加卵黄囊容量 |


## 六、验证标准

| 判据 | 数理形式 | 目标 |
|------|----------|------|
| 权重分化 | $\Delta w_{ij} = w_{ij}(T) - w_{ij}(0)$ | $\max(\Delta w_{ij}) > 0.02$ |
| 位移轨迹 | $\Delta x(t) = x(t) - x(0)$ | 200k 步时 $\Delta x > 0$ |
| 能量生存 | $\min_{t \in [0,1M]} \text{fill}(t)$ | $> 0$ |
| 抑制比例 | $R_{\text{supp}} = N_{\text{supp}} / N_{\text{total}}$ | $< 0.9$ |


## 七、终止条件

实验终止条件为能量耗竭：当 $\text{fill}(t) = 0$ 且持续 10k 步未恢复时，记录当前状态并终止实验。此时保存全部已有数据用于分析失败原因。


## 八、决策与代换映射

| 批次1中的 ID | 决策结果 | 本表对照 |
|-------------|----------|---------|
| ISSUE-01（σ₀）| 保持 0.70 | D01 |
| ISSUE-02（τ_w）| 30 步，STF 文献 | D02 |
| ISSUE-03（η_da）| 7.5，配合 EXP-CAL-DA | D03 |
| ISSUE-04（时序）| 原子级同步 | D04 |
| ISSUE-05（修改策略）| 方案B（子类扩展）| D05 |



---

### 一、补丁 B：因果非对称性

| 项目 | 内容 |
|------|------|
| 裁定 | **仅前庭信号展宽，热感信号保持瞬时** |
| 数理形式 | $\tilde{V}_i(t) = \int_0^{\tau_w} V_i(t-s) \cdot e^{-s/\tau_w} \, ds$，$B_{ij}(t) = \tilde{V}_i(t) \cdot T_j(t)$ |
| 核心要求 | 热感信号 $T_j(t)$ 不经过任何时间卷积。如果两端都被展宽，因果方向将变得不可区分：系统将不知道是“运动导致了热变化”还是“热变化导致了运动” |

---

### 二、补丁 A：AGC 零点纯度

| 项目 | 内容 |
|------|------|
| 裁定 | **AGC 放大后的 OU 噪声均值必须保持为 0** |
| 数理形式 | $\mathbb{E}[\eta_{\text{Langevin}}(t)] = 0$，$\mathbb{E}[\eta_{\text{Langevin}}(t) \cdot (1 + G_{\text{agc}}(t))] = 0$ |
| 核心要求 | 饥饿状态只改变随机搜索的**幅度**（方差），不改变其**方向分布**（均值）。方向偏好必须来自 STDP，不能来自 AGC 引入的任何隐性偏置 |
| 实现检查 | 确认 `LangevinNoise.step()` 的输出经 AGC 乘法后仍在零附近对称分布。如果 AGC 的乘法操作引入了数值偏移，需检查其内部实现是否包含了误加的常数项 |

---

### 三、补丁 D：DA 微分门控的量纲与防爆

| 项目 | 内容 |
|------|------|
| 裁定 | **η_da 的推导基于归一化后的 d(fill)/dt 值，与代码实现中的实际量纲一致** |
| 数理形式 | $DA(t) = \max(0, \eta_{da} \cdot d(\text{fill})/dt)$，$\eta_{da}=7.5$，$DA_{\max}=5.0$ |
| 量纲校验 | $d(\text{fill})/dt$ 在归一化形式下约为 $1.08\times10^{-4}$，在 `(fill - fill_prev)/dt` 形式下约为 $0.108$。两种实现方式对应不同的 η_da 量纲，但输出结果相同。实施时只需确保代码中的 η_da 与导数计算形式匹配即可 |
| 核心要求 | `clip_max=5.0` 是防爆保险，防止大面积极速进食导致的单步 DA 过冲，但应确保 η_da 的最终值在标定实验后不超过安全边界 |
| 实施确认 | 确认 DA 神经元的输入驱动端已串联 `clip_max` 保护，且该保护在正常进食脉冲下不触发 |

---
