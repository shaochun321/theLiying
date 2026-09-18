# T1B_PORT_AND_TIMEBASE_CONTRACT — 层级裁定 + 时间基合同 + typed port 定义

日期：2026-09-19
依据：外部《T1-B 方案》§5/§9/§30（经评判 C1-C5 修正采纳）。
本文档为合同层裁定：**production 代码零改动**（G0/L1/OccurrenceClosure/
tss/ READ_ONLY；代码修改属 G0_RECONNECT 阶段）。

---

## 一、层级归类裁定（§5）—— LAYER_CATEGORY_CONFLICT = RESOLVED_AT_CONTRACT_LEVEL

MAINLINE V2 正式四层归类（Boundary ≠ Transduction ≠ L1 ≠ OccurrenceClosure）：

| 层 | 职责 | 当前代码实体 |
|---|---|---|
| **Boundary** | World↔organism 物理接触；组织/介质热惯性；允许的有限观测 | SkinPatch（含其 RC 与 dT 差分寄存器）、ThermalFieldGraph 节点暴露、BoundaryView |
| **Transduction 𝒟_i** | typed port conversion / reference conversion / unit-scale conversion（薄、无状态优先） | `transduce()`（legacy）→ 未来 D_v2（Candidate A 目标态 / B 过渡态） |
| **L1** | 真正感受换能：整流/受体电流/激活/（未来如需）适应态 | `ThermalDeltaNeuron` |
| **OccurrenceClosure** | trigger / exit / rearm / occurrence identity 独占 | `occurrence.py` 状态机 |

- TSS 文档中 `D_i^sim ⊇ {transduce, L1, HC}` 的旧分类正式标记为
  **`LEGACY_LAYER_CLASSIFICATION`**（`base_generator.py:100-103` 注释的
  自述归类）——不再作为 MAINLINE V2 结构分类使用；tss/ 冻结文本不改动，
  引用时须注明该标记。
- 速率提取现状（T1-A 审计）：生产支路在 Boundary 层（SkinPatch.dT）；
  目标态归 L1 内部（Q1 卡 2）；D 层禁止承担（Candidate C 层位否决维持）。

## 二、MAINLINE_TIMEBASE_CONTRACT（§9，评判 C2）

```text
外部统一物理时间 t_ext，单位 [s]。
锚定（C2）：World/Boundary 一步 = Δt_ext = 1 s。
  依据：SkinPatch BIO 合同 "τ=5 s integration"（transducer_neurons.py
  docstring 既有约定）与 τ_env=R·C∈[20,2000] s 的环境耗散物理量级。
World v2 的 dt 参数即 Δt_ext（W1 已证 dt∈{1,0.1,0.01} 一阶收敛，
  物理时长恒定纪律已建立）。
Generator 的 dt=0.001 declared 为【内部积分粒度】，非物理秒——
  它是 tick 内部 RC 更新的数值常数（D3 双时钟债务的合同层了结）。
耦合合同：每 1 个 t_ext 步消费 1 个边界样本（现行 exp_P2A1b_3 的
  1:1 步配对显式化）。任何跨层速率量必须以 Δt_ext 计：
  Ṫ = ΔT/Δt_ext [T/s]。裸 ΔT 不得冒充速率（T1-A D2 债务了结路径）。
```

## 三、typed port 定义（§30）—— G0_INPUT_PORT_CONTRACT_V2

| | **U_T（幅值口）** | **U_Ṫ（速率口）** |
|---|---|---|
| 定义 | S·(Y_B − Y_ref) | g·(Y_B(t) − Y_B(t−Δt_ext))/Δt_ext |
| 单位 | [u]（生成元输入单位）= S·[T]；S:[u/T] | [u] = g·[T/s]；g:[u·s/T] |
| 时间基 | 瞬时（当前 t_ext 样本） | Δt_ext=1 s 物理差分（Δt 不是可调滤波宽度，§14） |
| 符号语义 | Y_B≥Y_ref ⇒ u≥0；无整流 | **带符号**（降温为负）；整流属 L1 半波，D 不做 |
| 允许范围 | 有限实数；**无 clip/死区/窗选**（§13） | 有限实数；无 clip |
| 生产者 | D_v2 Candidate A | D_v2 Candidate B（状态=单步寄存器，初始化合同 C5：prev=首样本 ⇒ u(0)=0） |
| 消费者 | G0_V2 的 L1（**需 L1 输入语义改为幅值→受体电流**，属 G0_RECONNECT） | 现 L1（dT_raw 口语义兼容，过渡桥） |
| Y_ref | episode 无关的静息参考（环境基线 0，PHYSICAL 来源；禁"好看 offset"，§13） | — |

裁定（§31）：typed port 首要目的是消除 `u_i/dT_raw` 一名双义；最终
production 采用哪个口属 G0_RECONNECT 裁定；本合同先冻结两口定义。

## 四、参数角色与 provenance 预承诺（§13/§14/§44 + 评判 C3）

**在 held-out 锁定之前声明（防事后挑选）**：

| 参数 | 角色 | canonical 值 | provenance |
|---|---|---|---|
| S（A） | 单位/尺度映射，不承担阈值/窗选 | 0.00137531 [u/T]（=legacy κ 数值） | **CANONICAL_REFERENCE**（延续现 G0 输入尺度直至端口改造；≠OPTIMAL） |
| Y_ref（A） | 静息参考 | 0.0 [T] | PHYSICAL（场静息基线，rest_baseline 实测） |
| g（B） | 速率增益 | 0.00137531×200=0.275062 [u·s/T] | CANONICAL_REFERENCE（=S×τ_field，使阶跃早期 U_Ṫ 与稳态 U_T 同量级；T1-A 机制扫描代表值延续） |
| Δt（B） | 物理采样时间 | 1 s（=Δt_ext，非可调） | PHYSICAL |

合法域（§12/§23，calibration 实验产出失效边界后登记于报告）：
S、g ∈ (0, 数值有限上界)，只需满足 §15 资格约束（有限输出/无隐藏
clip/无死区/符号语义/dt 一致/跨 World 稳定/held-out 非灾难）。

## 五、G0 回接前文本债务状态（§49）

```text
LAYER_CATEGORY_CONFLICT = RESOLVED_AT_CONTRACT_LEVEL（本文档 §一）
G0_PORT_CONTRACT_V2   = FROZEN（本文档 §三）
G0_PORT_CONTRACT_CHANGE_REQUIRED = 保持登记（实施属 G0_RECONNECT）
production code 未改动。
```
