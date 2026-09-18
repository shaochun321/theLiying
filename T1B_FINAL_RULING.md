# T1B_FINAL_RULING — 十二问首屏直答 + 六门 + 终态

日期：2026-09-19
聚合：`research/transduction_v2/t1b/t1b_final_qualification.py` →
`data/qualification_summary.json`

---

## 十二问直答（§58）

1. **Candidate A 是否跨 World 合格？** 是——canonical 固定参数下
   cal 30/30 + held-out 20/20 QUALIFIED + v1 retention=1.000。
2. **Candidate B 是否跨 World 合格？** 是——同上 30/30 + 20/20；dt-aware
   收敛；符号语义保留。
3. **架构身份？** A = 长期目标口（U_T thin amplitude，消费端需 L1 输入
   语义改造）；B = 过渡桥（U_Ṫ explicit rate，兼容现 L1 dT_raw 口）。
4. **最终长期 Transduction 目标？** **A**（World→Boundary→Thin D→
   L1_dynamic，§27 默认目标态未被数据推翻）。
5. **G0 reconnect 是否需要 bridge？** 需要——`G0_RECONNECT_BRIDGE = B`
   （在 L1 端口改造完成前）。
6. **U_T / U_Ṫ 正式单位？** U_T：[u]=S·[T]，S=[u/T]；U_Ṫ：[u]=g·[T/s]，
   g=[u·s/T]（合同 §三表）。
7. **全项目统一 physical dt 合同？** MAINLINE_TIMEBASE_CONTRACT：
   Δt_ext=1 s（锚=SkinPatch τ=5s 约定）；generator dt=0.001=内部积分
   粒度非物理秒；每 t_ext 消费 1 边界样本（D2/D3 债务了结）。
8. **Layer category conflict 裁定？** RESOLVED_AT_CONTRACT_LEVEL——四层
   归类表冻结（合同 §一）；TSS 旧 D_i^sim 分类标 LEGACY_LAYER_
   CLASSIFICATION（tss/ 文本不改）。
9. **Calibration/held-out 是否严格隔离？** 是——held-out 建成即 SHA256
   封存（17db7a7f…），canonical fingerprint（a64cf243…）锁定后才解封
   运行一次；canonical 参数未经任何拟合。
10. **首次 held-out 是否通过？** 是（FIRST_HELDOUT_RESULT：A/B 20/20
    QUALIFIED；legacy 12 DEGRADED+8 SEMANTIC_FAIL 原样登记）。
11. **是否存在 World↔D 共适应？** 否——cross-pair 30 条件 + LORO 两
    排除域零失败；CO_ADAPTATION_RISK=LOW（注：canonical 零拟合使 LORO
    退化为跨域状态检查，如实登记）。
12. **是否允许进入 G0_RECONNECT？** **是**。

## 六门（§45）

| 门 | 判定 |
|---|---|
| T1B-M1 port semantics | PASS（typed port+timebase 冻结；A dt 不变；B dt-aware 收敛；naive 负控制确认失效） |
| T1B-M2 cross-World | PASS（A/B 各 30/30 + v1 ref） |
| T1B-M3 no co-adaptation | PASS（cross-pair+LORO 零失败，零拟合） |
| T1B-M4 held-out | PASS（blind 一次，20/20+20/20） |
| T1B-M5 replay purity | PASS（4 eps 逐位；双 twin 无泄漏） |
| T1B-M6 controlled reduction | PASS（全部损失带 §37 归因；A/B 无未归因损失） |

## 终态（§47/§48）

```text
T1-B 终裁 = TRANSDUCTION_V2_QUALIFIED
A_LONG_TERM_PORT_QUALIFIED  = YES
B_TRANSITION_PORT_QUALIFIED = YES
FINAL_MAINLINE_TARGET       = A（U_T；G0_RECONNECT 改 L1 输入语义后接入）
G0_RECONNECT_BRIDGE         = B（U_Ṫ；兼容现 L1）
LAYER_CATEGORY_CONFLICT     = RESOLVED_AT_CONTRACT_LEVEL
G0_PORT_CONTRACT_V2         = FROZEN（实施属 G0_RECONNECT）
§59 硬停止生效：不再寻找更好的 transform/compression/retention。
```

## 下一轮（§50-§52/§60）

**G0_RECONNECT**（只做定点修改）：typed port implementation / L1 input
semantics / timebase plumbing / legacy compatibility → 立即
**Occurrence Revalidation**（χ_i^k=trigger/exit/rearm/duration/energy/
lineage 全重验，不沿用旧 P2-A 正结果）→ SCALE-0 → TSS Relation
reconnect。G0 reconnect ≠ 重新发明十神经元。

## 测试结果（本轮收口）

母体 nexus_v1/ 与 tss/ 与 research/world_v2/ 零改动（新增
research/transduction_v2/t1b/ 6 文件与 5 文档）。回归状态：
test_regression 21/21 PASS（exit 0）；tss version_pairing PASS；tss
fast 43 passed；WT0 四脚本 + T1A 诊断 + W1 四脚本复跑 exit 0 且数据
git 零 diff（全部冻结结果零扰动）。

## 复现入口

```bash
PYTHONIOENCODING=utf-8 python research/transduction_v2/t1b/t1b_dataset.py
PYTHONIOENCODING=utf-8 python research/transduction_v2/t1b/t1b_calibration_cross_world.py
PYTHONIOENCODING=utf-8 python research/transduction_v2/t1b/t1b_timebase_audit.py
PYTHONIOENCODING=utf-8 python research/transduction_v2/t1b/t1b_heldout_replay.py
PYTHONIOENCODING=utf-8 python research/transduction_v2/t1b/t1b_final_qualification.py
```
