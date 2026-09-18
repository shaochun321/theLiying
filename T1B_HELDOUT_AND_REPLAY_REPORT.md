# T1B_HELDOUT_AND_REPLAY_REPORT — blind held-out + 双 twin + replay 纯度

日期：2026-09-19
脚本：`research/transduction_v2/t1b/t1b_heldout_replay.py`
数据：`data/{heldout_results.csv, replay_results.json, t1b_heldout.json}`

---

## 一、§40 冻结流程执行记录

```text
1. canonical 配置（合同 §四，provenance 预承诺）
   fingerprint = a64cf243772ea356…（SHA256）
2. held-out 封存校验：manifest SHA = 17db7a7f4323ee56…（与 dataset
   构建时封存值一致——未被触碰）
3. LOCK @ 2026-09-19 00:52:25
4. blind held-out 运行一次（本报告 §三）
```

## 二、W1 双 twin 测试（§17-§19）—— HIDDEN_ACCESS_OR_STATE_LEAK = PASS

| 检查 | 结果 |
|---|---|
| Twin-1（场隐藏，过去 Y 不同）：A 在 t0 等值（容差=S·\|ΔY(t0)\|内） | ✓ |
| Twin-1：B 在 t0 允许不同，且完整由录制 Y 重放解释（重算≡原值） | ✓ |
| Twin-2（源隐藏，过去 Y 逐位同）：A、B 在 t0 **逐位相等** | ✓ / ✓ |
| 未来分叉后按合同响应：A@Twin-1 分叉 1.05e0；B@Twin-2 分叉 2.74e-1 | ✓ |

**认识论合规（§18）**：转导未"恢复"任何隐藏态——当前边界相同即输出
相同；分叉只在未来边界分叉后按各自合同出现。D 不偷读 X_W（§38）再证。

## 三、FIRST_HELDOUT_RESULT（原样登记，跑一次未改参）

| 候选 | held-out 20 episodes（含全部困难角） |
|---|---|
| legacy | DEGRADED=12, SEMANTIC_FAIL=8 |
| **A** | **QUALIFIED=20/20** |
| **B** | **QUALIFIED=20/20** |

门（§41：A/B 无 NUMERIC_FAIL、无 TRANSDUCTION_LOSS 型 SEMANTIC_FAIL）
⇒ **PASS**。强耗散角（r_leak<50）中 B 未触发
STRUCTURALLY_EXPECTED_ZERO 降格——这些 episode 的边界在源燃烧期变化率
仍足够（如实登记于 CSV，逐行可查）。

## 四、Replay 纯度（§39）

4 个代表 episodes（cal×2 + hold×2）：live 逐步应用 vs 录制 Y_B 后离线
重放（B 按 C5 初始化合同 prev=首样本）——**逐位一致**。World 删除后
边界数据自含可复现。

## 五、occurrence smoke（§34，冻结后一次）

Candidate B 输出经 feed()（现 L1 dT_raw 口，过渡桥语义）喂入 fresh G0：
L1_max=10.0（触钳）、collector_max=1.0017、occurrence=0（**只登记不
判定**——rearm=500 标定源于 v1 尺度，v2 输入下的 closure 阈值资格属
G0_RECONNECT/occurrence revalidation）。链路存活 ✓，未回调任何参数。
