# W1_FINAL_RULING — World v2 终裁（十二问首屏直答 + 六门 + 终态）

日期：2026-09-18
聚合：`research/world_v2/w1_final_qualification.py` →
`data/qualification_summary.json`

---

## 十二问直答（§60）

1. **World v2 的完整状态？** X_W = 场节点电荷（N∈{3,5,10,20}，每节点
   Capacitor C=1.0）⊕ 源状态（每源 energy_remaining；power/位置/t_start
   为参数）。
2. **哪些是 episode 条件采样变量？** (X_0, Θ_W, 𝒰_ext)=n_nodes/每边 κ/
   r_leak/源数与(E,P,node,t_start)/boundary 配置——Phase A 由
   WorldSampler 从 Θ_legal 采样后冻结。
3. **哪些是真动态状态？** 节点电荷 + 源 energy_remaining（二者都被
   因果阻断实验证明具有未来效应）。
4. **Source 与 Field 如何交换能量？** `DynamicHeatSource.release(dt)`
   （功率语义，受剩余能量预算钳制）→ `graph.step` 注入电流 → 节点
   Capacitor.inject；唯一入口，账本逐步记录。
5. **有效自由度多少？** Θ_legal 系综 PR：N=3→1.06 … N=20→3.33（单调
   增长）；单刺激/均匀 κ 子域的较低值如实并报（负结果 1/2）。
6. **独立时间尺度？** τ_diff≈47（扩散，κ 定）与 τ_env=R·C∈[20,2000]
   （耗散，r_leak 定）——实测解绑（100× vs 1.00×），三段位覆盖。
7. **Full/Reduced 分别暴露什么？** FULL=全部节点温度（物理调试/守恒/
   本体资格）；REDUCED=1~2 采样节点（有限观察，|Y_B|≪|X_W|），逐
   episode 显式登记 config+nodes。
8. **hidden dynamics 是否成立？** 成立（两型）：场隐藏（ΔY(t0)=2e-17/
   ΔX=3.72/未来分叉 2.33）+ 源隐藏（场态逐位同、E_src 800 vs 0、未来
   分叉 1.44）。
9. **hidden state 是否有因果未来作用？** 是——阻断实验：覆写场态残差
   2.5e-13；源置零后 A_blocked≡B **逐位（0.0）** ⇒
   HIDDEN_STATE_CAUSALLY_SUPPORTED ×2。
10. **能量与数值闭合状态？** WORLD_LOCAL_ENERGY_AUDITABLE（max 残差
    4.96e-11）；dt 三档一阶收敛（0.1→0.01 差 2.2e-4）；数值稳定域=
    谱界解析式四点验证；不宣称全项目闭合（§31）。
11. **是否 WORLD_V2_RAW_QUALIFIED？** **是**（六门+§39 全 PASS，见下表）。
12. **是否允许进入 T1-B？** **是**（§51；W1 立即停止扩 World，§50）。

## 六门判定（§47）

| 门 | 判定 | 关键证据 |
|---|---|---|
| M1 物理闭合 | PASS | 残差 4.96e-11；dt 收敛 2.2e-4 |
| M2 独立自由度 | PASS | Θ_legal 系综 PR 1.06→3.33 单调 |
| M3 独立时间尺度 | PASS | τ_env 100× vs τ_diff 1.00× |
| M4 条件采样 | PASS | 30 episodes 全域内/无重复/Phase A-B 分离 |
| M5 部分可观测 | PASS | FULL t0 差 3.90 vs REDUCED 2.2e-17 |
| M6 隐藏因果动力学 | PASS | 双孪生 ESTABLISHED + 因果阻断 ×2 |
| §39 边界记录 | PASS | 同 spec 重跑逐位一致 + BoundaryView 纯元组自含 |

```text
W1 终裁 = WORLD_V2_RAW_QUALIFIED
```

## 边界与债务（不变更）

- Candidate A/B 未参与任何 World 判据（§20/§21：G0 DISCONNECTED，零
  occurrence 指标）；未因下游反调任何 World 参数（§61 四禁全程遵守）。
- `G0_PORT_CONTRACT_CHANGE_REQUIRED` 与 `LAYER_CATEGORY_CONFLICT` 保持
  登记不动（§53；裁定时点=T1-B 开工，修复=G0 回接——评判 B3 折中）。
- production 零改动；world_v2 是否迁入 `nexus_v1/components/` 留待
  T1-B 后决定（§55）。

## 下一轮（§51/§64）

**T1-B**：World v1 reference + World v2 calibration ensemble + World v2
**held-out** ensemble 上完成 Transduction v2 候选终选与参数标定
（cross-pair 共谋攻击必做；held-out 禁止参与调参）。之后 G0 reconnect
→ occurrence revalidation → SCALE-0 → TSS relation reconnect（§54，
主线不再变化）。

## 测试结果（本轮收口）

母体 nexus_v1/ 与 tss/ 零改动（新增 research/world_v2/ 5 文件与 4 文档）。
回归状态：test_regression 21/21 PASS（exit 0）；tss version_pairing
PASS；tss fast 43 passed；WT0 四脚本 + T1A 诊断脚本复跑 exit 0 且数据
git 零 diff（冻结结果零扰动）。

## 复现入口

```bash
PYTHONIOENCODING=utf-8 python research/world_v2/w1_structure_scan.py
PYTHONIOENCODING=utf-8 python research/world_v2/w1_hidden_twins.py
PYTHONIOENCODING=utf-8 python research/world_v2/w1_physics_audit.py
PYTHONIOENCODING=utf-8 python research/world_v2/w1_final_qualification.py
```
