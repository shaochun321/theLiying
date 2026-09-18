# G0R0_PHYSICAL_TIME_AUDIT — 生产代码时间语义普查（§3-§5/§21）

日期：2026-09-19
脚本：`research/g0_reconnect/r0/g0r0_time_audit.py`（行为实验判定，
§4 纪律：不靠变量名）；census 全表 `data/time_semantics_census.csv`。

---

## 一、行为实验（两档 dt 同物理时长，物理量不变性判定）

| # | 对象 | 实测 | 语义 |
|---|---|---|---|
| E1 | Capacitor.leak | 终值 0.01832/0.01832 相等 | PHYSICAL_TIME |
| E2 | Capacitor.inject | 总电荷 0.20000/0.20000 相等 | PHYSICAL_TIME（无剂量复制） |
| E3 | Neuron 基类 pre_trace | τ=0.0200/0.0200 s 不变 | PHYSICAL_TIME（ms→s 显式换算） |
| E4 | ThermalDeltaNeuron.pre_trace | τ=0.0995/0.0497 s，比=**0.500** | **DISCRETE_COUNTER**（0.99/步） |

## 二、census 摘要（全表见 CSV）

PHYSICAL_TIME：World/Boundary（dt=1.0 s）、Capacitor、Neuron 基类
（膜 RC/traces/适应）、DelayedBundle（τ_steps=round(τ_ms/dt_ms)）、
da_ema β（bundle.py:125-127 动态依 dt——Phase B P1 陷阱教训已制度化）、
SkinPatch（RC；其 dT 每步差分未除 dt 的 D2 约束维持登记）。
DISCRETE_COUNTER：ThermalDeltaNeuron.pre_trace（链内惰性——propagate
对非 spiking 源消费 activation，bundle.py:284-287）、
SynapticBundle.delay_steps（隐性——G0 核心链 delay=0；DA 路径 100-500
步受影响）、OccurrenceClosure 计数器（by design，需 n→t_phys 映射）。

## 三、§21 closure 量纲审计（只审不改）

`rearm=500` = **500 generator steps**（在旧 1:1 耦合下曾被当作"500 个
边界样本"使用——即 500 s 外部时间只推进 0.5 s 生成元时间）；
t_up/t_down/t_rearm = step_index（occurrence.py:135）。duration 同为
步数（NaturalUnit.duration_seconds=steps×dt 已有正确换算先例）。
阈值数值未动（§20）；v2 重标属 Occurrence Revalidation。

## 四、§14 终裁

```text
GENERATOR_DT = PHYSICAL_INTEGRATION_STEP = 0.001 s（状态 A）
T1-B 合同 C2"非物理秒"断言勘误（详见 G0R0_TIMEBASE_CONTRACT.md §二）
例外三项定点登记（修复属 G0-R1）
```
