# D2_0_FINAL_RULING — D2-0/P2-B 终裁

日期：2026-09-20　依据：外部方案（44 节）+ 评判（51f2cec）+ 反馈全接受
（E-1~E-7 + R-1~R-3 ACCEPTED，执行序 §26 冻结）

## 首屏：§42 十七问

1. **使用了几个基础 occurrence？** 36 个 OccurrencePortV2（22 条 parent
   轨迹：cal12+hold8+attack2；主实验 G_a=site28/G_b=site31，G_c=site23
   仅攻击——R-1 定点）。
2. **自然化用了哪些字段？** port 三边界（t_up/t_rearm）→ ϑ_i(t) 与
   τ_phys（N1）；成对 t_up 差 + duration 均值（N2）；raw track 的
   collector 信号积分（N3，被否决）。全部经显式 𝒩，零 G0 内部读取。
3. **哪些自然化候选失败？** N0=INSUFFICIENT（恒 1，预期）；
   N3=INSUFFICIENT（预注册 Q7 dt 稳健判据：抽稀重算差 4.06e-2>1%）。
4. **Relation 是否有自己的状态？** 是：x_ρ 由 RelationCell 膜电容承担；
   C6 同输入不同前史 x(t0)=0.559 vs 0.049、未来 RMSE=0.118。
5. **Relation 状态由什么物理结构承担？** 非 spiking Neuron 膜 RC
   （C=0.1,R=5.0,τ=0.5s）+ PowerRail 能量账本；换能链=
   RelationInputNeuron×2 → frozen SynapticBundle×2（E-3 强制路径，
   零 inject/零直接设电荷）。
6. **输入停止后如何耗散？** RC 泄漏：τ_decay 实测 0.456s（设计 0.5s）；
   全部 cal 运行 x_end=0.000。
7. **A→B 和 B→A 是否产生不同动力学？** 是（RMSE=2.15e-2），但根因=
   **parent 个体性**（site28/31 换能潜伏期差 8ms），非细胞级 order
   检测——命名纪律维持，不称 order/direction（反馈 §N2）。
8. **simultaneous 是否与 sequential 不同？** 是：peak C2=5.233 vs
   C3_m=3.335（RMSE>1e-6，差 36%）；overlap 居间
   （5.233≥4.527≥3.619≥3.335）。
9. **same-current/different-history 是否出现不同未来？** 是（C6，
   问 4 数据）——RELATION MEMORY CONFIRMED。
10. **hidden-state 最小充分候选是什么？** RelationCell 膜态（单细胞
    x_ρ 载体）；tier0（换能态）不充分、tier1 移植 RMSE 精确 0.0。
11. **是否停止进一步分解？** 是：RELATION_MINIMAL_SUFFICIENT_STATE_
    CANDIDATE + STOP_DEEPER_DECOMPOSITION（不拆电容/bundle 微态）。
12. **阻断 parent 是否改变关系过程？** 是：blockA/blockB RMSE 均 >1e-3
    （1.4/1.9 量级）；site23 替换攻击过程成立（泛化）。
13. **pure coincidence 负对照是否被正确拒绝？** 是：NC1
    RELATION_SIGNAL=YES / RELATION_PROCESS=NO；NC2 无记忆反例对
    （同标签同瞬时输入、x 不同值）成立。
14. **held-out 是否通过？** 是：SHA 验证后冻结参数盲评 8/8 合法
    （6 个 relation_occ=1 + 2 个 STRUCTURALLY_NO_RELATION），零回调。
15. **是否形成 relation occurrence candidate？** 是：χ_ρ^(1) ×9（cal
    双父轨迹全部恰 1 次、单父全 0——关系发生需双父）；谱系
    `relation_rho:d2_rho0`（depth=1 ← G_a,G_b 地址）；三边界物理秒可出；
    **仅登记 RELATION_OCCURRENCE_CANDIDATE，禁 G1**（反馈 §二十二）。
16. **是否得到 D2_RELATION_PROCESS_V0_QUALIFIED？** **是**（六门
    D2-M1~M6 全 PASS，qualification_summary.json）。
17. **是否进入 D2-1/P2-C？** 是：**FREEZE D2-0** 生效（反馈 §二十四：
    禁 Naturalization-v2/RelationCell-v2/更多 site/更多模态/更大网络/
    更大扫描）；下一轮唯一问题=χ_ρ^(1) 能否再次成为关系输入
    （反馈 §二十五）。

## 六门判定

| 门 | 结果 | 依据 |
|---|---|---|
| D2-M1 Naturalization legality | PASS | N1/N2 QUALIFIED_REFERENCE + N0 预期 INSUFFICIENT + lineage/物理轨/量纲保留 |
| D2-M2 Stateful relation | PASS | C6 记忆确认 + RELATION_STATE_CAUSALLY_SUPPORTED |
| D2-M3 Physical realization | PASS | Neuron/SynapticBundle/RelationInputNeuron 实体 + 禁模式静态扫描零命中 |
| D2-M4 Causal parentage | PASS | NC4 双向阻断显著 + attack 泛化 |
| D2-M5 Replay/held-out | PASS | replay 逐位一致 + SHA 验证 + hold 8/8 零回调 |
| D2-M6 No label promotion（最高优先） | PASS | NC2 反例对 + C6——无 (A_id,B_id,timing) 无记忆函数可复现 x_ρ |

## 冻结参数（v0 canonical，全部新鲜推导，未抄 G0）

g_rel=0.25（peak 线性区中点规则）；theta_up_ρ=2.6164（u_work/2）；
theta_down_ρ=0.26164（比例约定）；rearm_ρ=456 步≡0.456s（一个实测
τ_decay）；phys_support=任一父窗活跃（epoch/token 继承）。

## 交付

- production：`tss/adapters/relation_replay_adapter.py`（唯一新增，R-2）
- research：`research/d2_relation_v0/`（8 脚本 + data/ §40 八件全交付 +
  relation_occurrence_candidates.csv）
- 报告四份（§41）：本文件 + NATURALIZATION_CONTRACT +
  RELATION_DYNAMICS_REPORT + NEGATIVE_RESULTS

## 回归状态

test_regression 21/21 PASS；TSS version_pairing PASS + fast 43 passed
（Step3 production 触碰后与收口各一轮）；D2 全程 replay-first，物理轨迹
22/24 预算内，干预 3/6，标定评估 7/16。

## 复现入口

```bash
PYTHONIOENCODING=utf-8 python research/d2_relation_v0/dataset_builder.py     # 需先清 parent_traces（IMMUTABLE）
PYTHONIOENCODING=utf-8 python research/d2_relation_v0/naturalization_candidates.py
PYTHONIOENCODING=utf-8 python research/d2_relation_v0/calibration.py
PYTHONIOENCODING=utf-8 python research/d2_relation_v0/relation_trials.py
PYTHONIOENCODING=utf-8 python research/d2_relation_v0/hidden_state_attack.py
PYTHONIOENCODING=utf-8 python research/d2_relation_v0/d2_final_qualification.py
```
