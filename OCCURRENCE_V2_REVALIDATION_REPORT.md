# OCCURRENCE_V2_REVALIDATION_REPORT — χ 全重验、阈值/rearm 重标与 dose 结构

日期：2026-09-19　轮次：G0-R1/OCC Step3　依据：外部方案 §6-§10（E-6 预注册
/E-8 封存纪律）

## 一、数据集（§9 八类场景）

cal 16（8 类×2）+ hold 12，`research/g0_reconnect/r1_occ/data/
r1_{cal,hold}_manifest.json`。hold 清单 SHA256=a4c9ad7e5c61cdef… 于任何
评估前提交（4b95339）；hold 不参与任何重标，仅 final_qualification 冻结
参数盲评一次。

## 二、重标结果（离线重放法：closure 是只读观察者，物理每 episode 只跑一次）

驱动：g_v2=2.5125e-2，S0+B0 因果桥，dt_G=0.001，60k 子步/episode。

| 参数 | legal region | failure boundary | canonical | 规则 |
|---|---|---|---|---|
| theta_up | [0.005, 0.9]（网格内 sat 期望全满足） | ∈(0.9, 1.1)=collector Zener 顶棚(~1.0)之上无触发 | **0.01（=v1 不变）** | 合法域内取 v1 连续性锚定，非最优 |
| rearm | [0, 10000] 步 | ∈(10000, 25000)：K8b 第二脉冲 t_rearm 越出 episode 窗 | **500（=v1 不变，≡0.5s）** | 同上 |

合法域 42/64 组合；theta_down=0.1·theta_up 迟滞比沿 v1 登记不另扫。
**结论：v1 canonical (0.01, 500) 在 v2 输入合法域内——T1-B smoke occ=0
的病灶不在 closure 阈值而在旧 1:1 timebase + 旧 g 量级（G0-R0 已定量），
两者修复后 closure 参数无需改动。** rearm 不变 ⇒ DEG-018 定量边界维持
现登记。

## 三、χ 三边界合同（§7，canonical，cal_K1a）

trigger_after_support_on ✓（latency=558 步=0.558s）；sustain 有限
（duration=139 步=0.139s）；exit_by_state_machine ✓（exit_mode=
**internal_dynamics**——§7 明文第二合法模式：collector 对 onset 瞬态
响应后经内部动力学退出，输入仍在场）；rearm_gap=500 步 ✓；三边界物理秒
=(1.558, 1.697, 2.197)。无任何 episode 标签指定时刻。

## 四、dose 结构（§10，A1<A2<A3 = power 0.5/1.0/2.0）

| 维度 | A1 | A2 | A3 | 可测差异 |
|---|---|---|---|---|
| latency（步） | 748 | 558 | 443 | ✓ 严格有序 |
| Σ\|u\| | 364.1 | 540.1 | 678.7 | ✓ 严格有序 |
| duration | 139 | 139 | 139 | ✗（collector 顶棚后退出动力学相同） |
| col_peak | 1.0014 | 1.0011 | 1.0012 | ✗（Zener 顶棚吸收幅值差） |
| occ count | 1 | 1 | 1 | 不要求单调（§10） |

**PASS**：剂量差异保留在 latency 与输入功率积分两维（时序编码），未被
saturation 完全抹掉。登记：幅值维（peak/duration）被 collector Zener
顶棚吸收——与 W0-E/T0 已知"顶棚"家族一致，属登记事实非本轮缺陷。

## 五、方法登记（两处，NEGATIVE_RESULTS 同步）

1. 首轮 5×5 网格 25/25 全 LEGAL=不鉴别（TSS-2b 教训重演）→ 扩网格至
   失败沿（theta_up→顶棚方向、rearm→K8 脉冲间隔方向）后边界双侧定位。
2. 合同 exit 检查初版错编码为"t_down≥支撑衰减"（严于 §7 原文，漏
   "内部动力学退出"合法模式）→ 对齐原文并登记 exit_mode 分类。

## 数据交付

`r1_occ/data/`：occurrence_trials.csv（16×64 组合）/ closure_timing.csv
/ energy_ledger.csv（R-2 研究区审计面，16 行）/ dose_structure.csv /
r1_revalidation.json（参数五元组）。Commit：d037eb7。
