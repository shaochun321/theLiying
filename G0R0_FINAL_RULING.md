# G0R0_FINAL_RULING — 十四问首屏直答 + 六门 + 终态

日期：2026-09-19
聚合：`research/g0_reconnect/r0/g0r0_final_qualification.py` →
`data/qualification_summary.json`

---

## 十四问直答（§43）

1. **只有一条物理时间？** 是——t_phys 唯一，各组件只有积分分辨率差异。
2. **World dt？** Δt_W = 1.0 物理秒（W1 dt 收敛已证）。
3. **G0 dt？** Δt_G = 0.001 物理秒（**状态 A，行为实验裁定**——E1-E3
   inject/leak/trace 全按秒消费；T1-B"非物理秒"断言勘误）。
4. **1 World step = 多少 G0 substep？** N_sub = 1000（整数校验，余数拒绝）。
5. **Boundary 如何供子步信号？** S1 线性插值=CANONICAL_FOR_IMPLEMENTATION
   （因果性=需下一样本，live 为 1 s 滞后；S0 零滞后备选；S2 细采样为参考）。
6. **A 如何调度？** 逐子步 U_T^(k)=S·(Y^(k)−Y_ref)（无态，理想 scheduler
   探针）。
7. **B 如何调度？** B1 逐子步 U_Ṫ^(k)=g·ΔY^(k)/Δt_G（B0 整段保持为对照，
   剂量等价 0.996；物理意义不同不混用）。
8. **delay 保持物理时长？** DelayedBundle 是（dt-aware）；
   SynapticBundle.delay_steps **否**（实证 5 步=5.0/2.5 ms 漂移）——隐性
   （G0 核心 delay=0 未行使），登记留 G0-R1。
9. **RC 保持物理时间常数？** 是——HC trace τ=6.4201/6.4202 s（在体，
   两档 dt_G 五位不变）；例外=L1 自身 pre_trace（链内惰性）。
10. **replay 重现 G0 状态？** 是——live（交替步进）vs 纯 timestamped 帧
    重建**逐位一致**；Twin-2 无 CROSS_LAYER_HIDDEN_LEAK。
11. **有剂量重复？** 无——multirate/ref=1.0010，B0/B1=0.996；旧 1:1
    耦合=0.00101（1/1000 物理不一致定量化）。
12. **occurrence 时间字段单位？** step_index（generator 步）；rearm=500
    generator steps；n→t_phys 映射属 G0-R1（§22）。
13. **G0_MULTIRATE_TIMEBASE_QUALIFIED？** **是**（六门全 PASS）。
14. **允许进入 G0-R1？** **是**。

## 六门（§33）

| 门 | 判定 | 关键证据 |
|---|---|---|
| R0-M1 时间语义 | PASS | E1-E4 行为实验；状态 A；例外三项定点登记 |
| R0-M2 单一物理时间 | PASS | timestamped 帧；scheduler=纯协调无 GlobalClock |
| R0-M3 多率收敛 | PASS | Tier-1 一阶收敛（比=0.101）；全向量 FIRST_RESULT FAIL 原样保留→G0_OSCILLATOR_PHASE_SENSITIVITY（先证 exp_P2A1b_3） |
| R0-M4 延迟/RC 不变 | PASS | RC τ 五位不变；两例外（L1 trace 链内惰性/delay 隐性）登记留 G0-R1 |
| R0-M5 replay 纯度 | PASS | 逐位一致 + Twin-2 无跨层泄漏 |
| R0-M6 无剂量复制 | PASS | 1.0010 / 0.996；旧耦合 1/1000 定量化 |

## 终态

```text
G0-R0 终裁 = G0_MULTIRATE_TIMEBASE_QUALIFIED
```

## 下一轮 G0-R1（§36——定点修改，首次动 production）

typed port implementation / B transition bridge / A target port
plumbing / L1 input semantics rename / legacy compatibility
+ 本轮登记例外修复（L1 trace dt 化、delay_steps dt-aware 化、
closure n→t_phys 映射）→ **Occurrence Revalidation**（χ 全重验 +
closure 阈值与 B 桥 g 量级在物理秒制下重标——本轮 bridge 五场景
occurrence=1×5 与 L1 饱和 33.3% 两项信号已登记）。

## 测试结果（本轮收口）

production 零改动（新增 research/g0_reconnect/r0/ 6 文件与 5 文档）。
回归状态：test_regression 21/21 PASS（exit 0）；tss version_pairing
PASS；tss fast 43 passed；WT0×4 + T1A + W1×4 + T1B×3 共 12 个冻结
脚本复跑 exit 0 且数据 git 零 diff。
