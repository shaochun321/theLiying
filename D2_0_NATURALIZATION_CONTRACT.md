# D2_0_NATURALIZATION_CONTRACT — 自然化合同与候选资格

日期：2026-09-20　轮次：D2-0/P2-B Step1-2　依据：方案 §6-§7/§19 + 反馈
§二/§五/§九/§十（E-1~E-7、R-1~R-3 ACCEPTED）

## 一、数据合同（E-1 兑现）

**RawOccurrenceTrack**（反馈 §二最低字段全覆盖）：t_phys / site / u(t) /
collector 信号 / phys_support / epoch / energy 快照（每 100 子步）。
22 条 parent 轨迹（cal12+hold8+attack2，≤24 预算）逐子步录制入
`research/d2_relation_v0/data/parent_traces/`，IMMUTABLE_PARENT_TRACE
（write_track 拒绝覆盖）。raw track = 外部实验记录，非内部生成元状态；
D2 运行时不回读 G0 对象，消费缓存经显式 𝒩 是唯一合法路径。
OccurrencePortV2 ×36（raw_track_ref 指向缓存）。
hold manifest SHA256=f05f6a2451e1c11f，生成即封存（先入库后评估）。

## 二、自然化候选资格（§19 七问独立回答，无 winner）

| 候选 | 判定 | 关键实测 |
|---|---|---|
| N0 count | **INSUFFICIENT** | 恒 1，无时序/剂量/历史区分（存在基准，预期兑现） |
| N1 phase ϑ | **QUALIFIED_REFERENCE** | ϑ∈[0,1]+τ_phys 保留；**REPLAY_REFERENCE_ONLY**（分母含 t_rearm；CAUSAL_VARIANT_REQUIRED_BEFORE_LIVE_D2 已登记，本轮不解决） |
| N2 Δτ̂ | **QUALIFIED_REFERENCE** | C3(s,m,l)=+0.327/+0.948/+2.374、C4=−0.302/−0.923/−2.346 严格有序双向；分母=mean(τ_i,τ_j) 可追踪尺度；**REPLAY_REFERENCE_ONLY**；命名纪律：只述 relative temporal response，不称 order/direction |
| N3 A_i=∫a dt | **INSUFFICIENT** | 预注册 Q7 dt 稳健判据否决：2× 抽稀重算相对差 4.06e-2 > 1%（collector 尖峰结构对采样分辨率敏感）；Q6 区分度本身达标（spread=0.249）；如实登记，不软化阈值、不改 G0（反馈 §九明许） |

Q5 dose 诚实登记：cal 集 dose 轴=触发/不触发二分（u=0.02 亚阈值零
occurrence 实测：cal_C2_sim2/hold_dose1/hold_dur1）；触发内 dose 敏感性
仅 hold 盲评观察（未用于任何调参）。

## 三、进入关系结构的接口（E-3 强制换能链）

关系驱动 = N1 的 ϑ_i(t)（逐子步，`tss/adapters/relation_replay_adapter.py`
生成 RelayDriveSample(ϑ, parent_support, epoch)）。N2 不直接注入——相对
时序经两通道的物理时间差在关系动力学中自然表达（无语义标签）。带符号量
若未来需要直接驱动，按 ±半波双通道先例（thermal warm/cool）整流分裂。

数据：naturalized_values.csv / naturalized_pairs.csv /
naturalization_comparison.csv / d2_naturalization.json。
Commits：25af802（Step1）/ a96473b（Step2）。
