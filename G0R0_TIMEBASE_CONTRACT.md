# G0R0_TIMEBASE_CONTRACT — 统一物理时间轴 + 多率积分（修订版时间合同）

日期：2026-09-19
依据：外部《G0-R0 方案》§1-§2/§14-§16/§22-§24（经评判 D1-D6 采纳）。
**取代** T1B_PORT_AND_TIMEBASE_CONTRACT.md §二 中"generator dt=内部积分
粒度（非物理秒）"的表述（该断言经行为实验勘误，见 §二）。

---

## 一、时间原则（§2/§15）

```text
项目唯一物理时间：t_phys ∈ ℝ⁺ [s]。
各组件只有不同的数值积分分辨率：
    Δt_W = 1 s      （World/Boundary 外部采样步）
    Δt_G = 0.001 s  （generator 物理积分步——状态 A，实测裁定）
耦合：Δt_W = N_sub·Δt_G，N_sub = 1000（整数，余数拒绝）。
禁止独立的 World clock / Generator clock / TSS clock；
禁止 GlobalClock 对象——调度只是 time coordination（§24）。
```

## 二、§14 终裁：状态 A（含对 T1-B C2 的勘误）

```text
GENERATOR_DT = PHYSICAL_INTEGRATION_STEP = 0.001 s
```
行为实验证据（`g0r0_time_audit.py`，两档 dt 同物理时长）：
Capacitor.inject ΔQ=I·dt（总电荷两档相等）；Capacitor.leak
exp(-dt/RC)（终值相等）；Neuron 基类 trace τ=0.0200 s 两档不变
（ms→s 显式换算 neuron.py:587-588）。**T1-B 合同"dt=非物理秒"断言
正式勘误**——合同文字不能替代代码证据（外部 §14/§44 正确）。

## 三、例外清单（定点登记，修复属 G0-R1；census 全表见 CSV）

| 组件 | 语义 | 状态 |
|---|---|---|
| ThermalDeltaNeuron.pre_trace | DISCRETE_COUNTER（0.99/步，τ 随 dt_G 漂移，实测比=0.500） | 链内惰性（propagate 消费 activation，bundle.py:284-287）；修复留 G0-R1 |
| SynapticBundle.delay_steps | DISCRETE_COUNTER（步数制；实测 5 步=5.0/2.5 ms 随 dt_G 漂移） | 隐性（G0 核心链 delay=0 未行使；DA 路径 100-500 步受影响）；修复留 G0-R1 |
| OccurrenceClosure 计数器 | DISCRETE_COUNTER by design（t_up 等=step_index；rearm=500 步） | §22：保留计数器+提供 n→t_phys 映射（G0-R1 实施）；本轮未调阈值（§20） |
| DelayedBundle（bundle_v2） | PHYSICAL_TIME（τ_steps=round(τ_ms/dt_ms) dt-aware） | 正确先例，保留 |

## 四、多率调度合同（§6-§10）

- 研究层 `MultiRateScheduler`（`research/g0_reconnect/r0/g0r0_common.py`）。
- 边界保持策略登记：S1 线性插值 = CANONICAL_FOR_IMPLEMENTATION（≠OPTIMAL；
  **因果性登记：需下一样本 ⇒ live 实现=1×Δt_W 滞后**）；S0 零阶保持=零
  滞后备选；S2 细采样重放=参考基准非 production。
- Candidate 调度：A 逐子步 U_T^(k)=S·(Y^(k)−Y_ref)；B 采 **B1 逐子步
  重算** U_Ṫ^(k)=g·(Y^(k)−Y^(k−1))/Δt_G（B0 整段保持为对照；两者剂量
  等价 0.996，物理意义不同不混用，§9）。

## 五、同步点合同（§23）

边界帧携带 (t_phys, dt_boundary, sample_id)；G0 子步可得
(t_phys, dt_generator, substep_index)；跨层计时禁止依赖 `_step_serial`。
occurrence 未来推荐 χ=(t↑,t↓,t_rearm) 物理时间戳（内部保留 step
counter+映射，§22，G0-R1 实施）。

## 六、历史耦合登记（§40 负结果，定量化）

旧 1:1 步配对（一场步配一 tick）在状态 A 下剂量=细参考的 **0.00101
（≈1/1000）**——生成元曾以 1/1000 物理速率运行。全部已冻结结果为
step 语义内部自洽，登记不重审。
