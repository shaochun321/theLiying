# G0R1_OCC_FINAL_RULING — G0-R1/OCC 终裁

日期：2026-09-19　依据：外部方案《MAINLINE V2 — G0-R1-OCC》（评判 ADOPT
with amendments，0f47a4d；R-1~R-4 用户裁定 2026-09-19）

## 首屏：§33 十七问

1. **live scheduler 最终采用什么？** S0（零阶保持，零未来访问）；
   reference/replay=S1。live 因果桥=S0+**B0**（S0+B1 被证伪，N-1）。
   本裁定=对 G0R0_TIMEBASE_CONTRACT §四 适用面的正式修订（R-3）。
2. **B→L1 是否仍有饱和？** 否。g_v2=2.5125e-2 下 cal/hold 全部
   sat_frac=0（g_v1=0.275062 在 cal 集 sat_frac=0.578，债务确认并清偿）。
3. **A target port 是否已建立正式 production 路径？** 建立了 typed 接口
   与升级存根（UTSample + amplitude_port_stub）；正式接入=L1
   amplitude→receptor-current 改造，按 T1B_FINAL_RULING 属 G0_RECONNECT
   升级合同，本轮不实施（R1-3 明令）。
4. **delay 是否物理时间不变？** 是（opt-in）：delay_tau_s 构造期
   round(τ/dt)；legacy delay_steps 字面语义零改动（DEPRECATED 登记）。
5. **L1 trace 是否 dt-aware？** 是：0.99**(dt/0.001)，四类同族神经元
   统一；G0-R0 E4 审计复跑漂移比 0.500→1.000 独立证实。
6. **occurrence 是否输出物理秒？** 是：Occurrence.to_physical(dt) +
   OccurrencePortV2 的 t_*_s 字段；计数器保留 by design。
7. **trigger/exit/rearm 是否在 held-out 中成立？** 是：hold12 冻结参数
   盲评一次过 12/12（SHA 先验证后运行，零回调）。
8. **不同输入剂量是否仍保留可测差异？** 是：latency 748/558/443 严格
   有序 + Σ|u| 有序；幅值维被 Zener 顶棚吸收（登记 N-5，§10 允许）。
9. **energy / Noether 是否闭合？** 研究区账本（R-2 审计面）：cal16+
   hold12 能量账本全有限、drop≥0；organism 侧 Noether 探针经母体回归
   21/21 覆盖（G0 手动驱动路径不跑 organism 主循环，DEG-021 互锁）。
10. **hidden twin 是否存在？** 是：t0=4917 可见面 |Δ|=1.01e-05、隐藏态
    L2=1.37 的相位 twin。
11. **哪个状态真正造成不同未来？** hc+ensemble+collector 的完整神经元
    状态（含膜电容电荷）；仅 pre_trace 不够（N-4）。
12. **causal block 是否确认？** 移植方向确认：Z_full 移植后未来逐位
    等化（RMSE=0.0）+ sham 负对照不消除 ⇒ HIDDEN_STATE_CAUSALLY_SUPPORTED。
13. **是否已经达到当前最小充分状态？** 是（候选）：Z_full 在当前分辨率
    下最小充分；Z_low 反例排除了更低维 trace 表示。
14. **是否可以停止继续下钻？** 是：CURRENT_MINIMAL_SUFFICIENT_STATE_
    CANDIDATE + STOP_DEEPER_DECOMPOSITION（§14），除非出现新反例。
15. **是否得到 G0_OCCURRENCE_V2_QUALIFIED？** **是**（六门 OCC-M1~M6
    全 PASS，qualification_summary.json）。
16. **是否得到 D1_SUFFICIENT_FOR_D2？** **是**（§20 九条件对应六门+
    端口交付；"不完美"项按 §21 不阻塞）。
17. **是否立即进入 D2-0/P2-B？** 是：**FREEZE G0-CENTRIC MAINLINE**
    （§25）生效——禁止 G0-R2/R1b/Occurrence-v3/Entropy redesign/
    World-v3/Transduction-v3，除非 D2 产生可复现阻断性反例。BACKLOG
    下一轮已指向 D2-0/P2-B。

## 六门判定

| 门 | 结果 | 依据 |
|---|---|---|
| OCC-M1 Physical Time | PASS | to_physical/delay_tau_s/rearm≡0.5s 机器验证 |
| OCC-M2 Typed Chain | PASS | tick_rate_port 接受 UdotTSample、拒绝 UTSample |
| OCC-M3 Finite Closure | PASS | §7 四段合同 cal_K1a 全项（exit_mode=internal_dynamics 合法） |
| OCC-M4 Held-out | PASS | hold12 SHA 验证+冻结参数盲评 12/12 零回调 |
| OCC-M5 Physical Ledger | PASS | 研究区账本 16 行有限+端口无语义标签+lineage 非空 |
| OCC-M6 Hidden Dynamics | PASS | 一轮完整 same-visible→定位→干预→stop 裁定 |

## 冻结参数（v2 canonical，全部 CANONICAL_REFERENCE ≠ OPTIMAL）

`g_v2=2.512531e-2`（(u_clamp/2)/max|Ẏ|_cal 预注册规则）；
`theta_up=0.01`、`rearm=500`（v1 值经 v2 合法域确认，连续性锚定）；
`dt_G=0.001 s`（状态 A）；live=S0+B0 / reference=S1。

## 交付

- production：D1×4 / D2 / D3 定点修改 + `tss/adapters/`
  （typed_ports + occurrence_port_v2，D2 消费合同：**D2 不得读 G0 内部
  neuron state**）
- research：`research/g0_reconnect/r1_occ/`（5 脚本 + data/ 14 文件，
  含 §30 清单全部：port_calibration / occurrence_trials /
  occurrence_heldout / closure_timing / energy_ledger /
  hidden_twin_pairs / hidden_interventions / minimal_state_ruling /
  qualification_summary）
- 报告：本文件 + PORT_AND_TIME_FIX / OCCURRENCE_V2_REVALIDATION /
  HIDDEN_DYNAMICS_CLOSURE / NEGATIVE_RESULTS（§31 五份）

## 回归状态

test_regression 21/21 PASS；contracts 13/15（C2/C3 ⊆ DEG-004）；TSS
version_pairing PASS + fast 43 passed；熵审计 6/6；17 冻结脚本全 exit 0
数值零 diff（例外=E4 审计两文件=D1 修复证据）；DEG-018 结论不变；
hold12 盲评 12/12。

## 复现入口

```bash
PYTHONIOENCODING=utf-8 python research/g0_reconnect/r1_occ/r1_dataset.py
PYTHONIOENCODING=utf-8 python research/g0_reconnect/r1_occ/r1_calibration.py
PYTHONIOENCODING=utf-8 python research/g0_reconnect/r1_occ/occurrence_revalidation.py
PYTHONIOENCODING=utf-8 python research/g0_reconnect/r1_occ/hidden_dynamics_closure.py
PYTHONIOENCODING=utf-8 python research/g0_reconnect/r1_occ/final_qualification.py
PYTHONIOENCODING=utf-8 python -m nexus_v1.tests.test_regression
```
