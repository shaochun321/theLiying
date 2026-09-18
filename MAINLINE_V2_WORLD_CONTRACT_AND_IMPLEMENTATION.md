# MAINLINE_V2_WORLD_CONTRACT_AND_IMPLEMENTATION — World v2 合同 + 实现报告

日期：2026-09-18
依据：外部《MAINLINE V2 — W1》（经评判 B1-B6 修正采纳）。
代码：`research/world_v2/world_v2_core.py`（production 零改动，§55）。

---

## 一、阶段登记（§0/§63）

```text
TSS = FROZEN；WT0 = CLOSED；T1-A = CLOSED
MAINLINE_V2_STARTED = TRUE（research/world_v2/ 已开工）
主线：𝒲 → ℬ → 𝒟 → G0 → ξ^occ → 𝒮 → ℛ_TSS → 𝒪 → G1?
本轮只建 𝒲+ℬ。
```

## 二、World v2 正式定义（§2）与实现映射

𝒲 = (X_0, Θ_W, ℰ, 𝒮_W, 𝒞_W, 𝒰_ext, ℬ_W)：

| 定义项 | 实现 | 复用标记（§7） |
|---|---|---|
| ℰ Field | `ThermalCell`+`ThermalLink`+`ThermalFieldGraph`（每边独立 κ） | **REUSE_AS_IS** |
| 𝒮_W Sources | `DynamicHeatSource`（E/P/位置/t_start/耗尽） | **REUSE_AS_IS** |
| 𝒞_W 耦合 | link 扩散（Field↔Field）+ source.release→injection（Source→Field） | REUSE_AS_IS |
| X_0/Θ_W/𝒰_ext | `WorldEpisodeSpec`（纯参数，Phase A 产物） | 新增 research 层 |
| ℬ_W Boundary | `BoundaryView`（§38 结构隔离：只持纯元组帧） | 新增 research 层 |
| 采样 | `WorldSampler`（`random.Random(seed)` 独立 RNG，B5） | 新增 research 层 |
| 账本 | `WorldLedger`（复用图内建 `conservation_residual` 等，不重复计账） | 新增 research 层 |

§7 其余组件：`ThermalFieldLocator`/`ThermalContact`/`JointThermalStepPlan`
本轮未消费，标记 **REUSE_WITH_PARAMETER_GENERALIZATION（T1-B 接触界面时
再审）**；`ThermalSourceCoupler` 类名不存在（评判勘误：功能=Source.release
+JointThermalStepPlan 编排）。无 LEGACY_ONLY 判定、无重写。

## 三、Θ_legal 合法参数域（§34：只声明域，不找最佳点）

```text
n_nodes ∈ {3,5,10,20}（链拓扑）        每边 κ ∈ [0.01, 0.2] log-均匀
r_leak_ambient ∈ [20, 2000] log-均匀（与 κ 独立 = M3 解绑）
源数 ∈ {1,2,3}；E ∈ [30,3000] log-均匀；P ∈ [0.2,5]；t_start ∈ [0,500)
dt=1.0；t_total=2000；boundary ∈ {FULL, REDUCED(1~2 节点)}
数值稳定域（§32，谱界）：κ·λ_max(L)+1/r_leak < 2/dt；
  链 λ_max=2−2cos(π(N−1)/N)；N=5 时 κ_crit≈0.552（Θ_legal 上限 0.2
  留 2.7× 裕量）；域外失稳=数值性质非物理复杂性（实测四点与谱界全符）
```

条件 c 只含物理范围；无任何 occurrence/G0/relation 条件（§3）。

## 四、两阶段原则实现（§4）

Phase A：`WorldSampler.sample()` → 冻结 `WorldEpisodeSpec`（frozen
dataclass）。Phase B：`WorldEpisode.step()` 只按 F_W 推进；对象无任何
下游读回通道（不 import G0/转导；Candidate A/B 若离线消费只读
BoundaryView 帧，§20）。语义纪律（§43/§44）：全部 id 为纯物理地址。

## 五、边界配置（§16/§17）

每 episode 显式登记 `boundary_config` + `boundary_nodes`；FULL 用于
物理调试/守恒审计/World 本体资格，REDUCED（1~2 节点，采样多位置，
不固定 node0）用于有限观察/隐藏动力学/后续接口。Boundary 无阈值/
无事件检测（§18——BoundaryView 只有 append 纯帧）。

## 六、资格结论（详见 W1_FINAL_RULING.md）

```text
六门 M1-M6 + §39 边界记录检查 全 PASS ⇒ WORLD_V2_RAW_QUALIFIED
§50：立即停止扩 World；§51：下一轮 T1-B。
迁入 nexus_v1/components/ 的决定留待 T1-B 后（§55）。
```
