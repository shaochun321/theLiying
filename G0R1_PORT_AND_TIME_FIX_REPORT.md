# G0R1_PORT_AND_TIME_FIX_REPORT — 时间债务修复与 typed 端口落地

日期：2026-09-19　轮次：G0-R1/OCC Step1-2　依据：外部方案 §3-§5/§8（评判
ADOPT with amendments，R-1~R-4 用户裁定 2026-09-19）

## 一、D1 — L1 trace dt 化（四类神经元统一，R-4 裁定扩至同族第四处）

- 实现：`nexus_v1/somatosensory/transducer_neurons.py` 新增
  `trace_decay_factor(decay_at_ref, dt) = decay_at_ref ** (dt/0.001)`；
  τ_phys = −0.001/ln(0.99) ≈ 99.5 ms。dt=0.001 时**逐位=0.99**（快路径
  锚定，零 diff 判据由此平凡成立）。
- 覆盖：ThermalInputNeuron / NociInputNeuron / ThermalDeltaNeuron ＋
  同族第四处 `tss/relations/relation_event_adapter.py` RelationInputNeuron
  （其 docstring 自引 ThermalInputNeuron 先例，同一债务同一修法）。
- **独立证实**：G0-R0 冻结审计脚本 `g0r0_time_audit.py` 复跑，E4 行为
  实验漂移比 0.500 → **1.000000000000003**，`E4_discrete_counter: false`
  （`research/g0_reconnect/r0/data/g0r0_time_audit.json` /
  `time_semantics_census.csv` 两文件的 diff 即修复证据，已作为新基线
  提交）。

## 二、D2 — SynapticBundle delay 物理化（双字段 opt-in）

- `BundleConfig.delay_tau_s: Optional[float]`（新 canonical，物理秒）；
  `SynapticBundle(..., dt=)` 构造期 `delay_steps=round(delay_tau_s/dt)`
  （沿 DelayedBundle τ_steps=round(τ_ms/dt_ms) 先例）；与非零 legacy
  `delay_steps` 互斥（raise）。
- legacy `delay_steps` 字面步数**零改动**（标注 DEPRECATED_STEP_SEMANTICS）
  ——bundle_v2/shadow_sandbox/muscle/variant_adapter/region_topology 全部
  现有调用点行为逐位不变。

## 三、D3 — OccurrenceClosure n→t_phys 映射（计数器保留 by design）

- `Occurrence.to_physical(dt) → (t_up·dt, t_down·dt, t_rearm·dt)`；
  `OccurrenceClosure.dt` 可选字段（不参与状态机逻辑）。
- rearm 语义登记：`rearm_min_steps=500 ≡ 0.5 s`（G0R0_PHYSICAL_TIME_AUDIT
  §三口径）。DEG-018 诊断复跑：结论不变（不合并二态，定量边界一致）；
  Step3 重标结论 rearm canonical 仍=500，边界无需更新。

## 四、R1-1/R1-3 — typed 端口（tss 侧，R-1 裁定）

- 新增 `tss/adapters/typed_ports.py`：`UTSample`/`UdotTSample`（typed
  dataclass，port 标签机器强制）；`u_t = S·(Y−Y_ref)`、
  `u_dot_t = g·ΔY/Δt_ext`（C5 初始化合同 prev=首样本 ⇒ u(0)=0）；
  canonical S=0.00137531 / Y_ref=0 / Δt_ext=1s（T1B 合同 provenance）。
- `BaseGeneratorHandle.tick_rate_port(sample)`：只接受 UdotTSample，
  UTSample 被 TypeError 拒绝（速率/幅值语义混用的类型层禁令）。
- A 长期口：`amplitude_port_stub()` 仅登记升级接口（G0_RECONNECT 合同，
  L1 amplitude→receptor-current 改造不在本轮，方案 R1-3 明令）。
- 依赖方向：tss/adapters 只 import nexus_v1（单向铁律核查 ✓）。

## 五、R1-2 — B 桥 g 真实秒制重标（cal 三场景）

| 项 | 值 |
|---|---|
| physical meaning | u=g·ΔY/Δt_ext 必须落在 L1 线性区（钳位起点 u=0.05=10/200, FIX-019） |
| legal region | [2.513e-3, 5.025e-2]（sat_frac=0 ∧ 链路存活） |
| failure boundary | 上=g_sat_onset=5.025e-2；下=g_dead∈(5.03e-5, 2.51e-3) |
| canonical g_v2 | **2.512531e-2**（预注册规则 (u_clamp/2)/max\|Ẏ\|_cal，非搜索） |
| provenance | max\|Ẏ\|_cal=0.995 T/s；交叉验证 0.995×g_v1=0.274=G0-R0 登记 u_B 峰 |

g_v1=0.275062 在 cal 集 sat_frac=0.578——B_BRIDGE_L1_SATURATION 确认并清偿。

## 六、§5 调度器二分（R-3 裁定=对 G0R0_TIMEBASE_CONTRACT §四 的正式修订）

`REFERENCE_RECONSTRUCTION_POLICY="S1"` / `LIVE_CAUSAL_POLICY="S0"`
（`tss/adapters/typed_ports.py` 常量）。**本节即修订登记**：G0-R0 的
"S1=CANONICAL_FOR_IMPLEMENTATION"自本轮起适用面收窄为 reference/replay；
live production 唯一合法策略=S0（零未来访问）。live 因果桥=S0+**B0**
（见 NEGATIVE_RESULTS：S0+B1 结构性错误）。

## 回归状态

test_regression 21/21 PASS；contracts 13/15（C2/C3 ⊆ DEG-004 基线逐字
一致）；TSS version_pairing PASS + fast 43 passed；熵审计 signal depth
6/6；17 冻结脚本（WT0×4+T1A+W1×4+T1B×3+G0R0×5）全 exit 0，数值零 diff
（唯二例外=E4 审计两文件=修复证据）；DEG-018 诊断结论不变。

Commits：2fe5f8d（Step1+R1-1）/ 38eae9d（R1-2）。
