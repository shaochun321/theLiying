# WT0_POSITIVE_CONTROL_AND_REPLAY_REPORT — 正对照冻结 + 边界重放

日期：2026-09-18
脚本：`research/wt0/{wt0_positive_control,wt0_boundary_replay}.py`
数据：`research/wt0/data/{wt0_positive_control,wt0_replay}.json`

---

## 一、WORLD_HIDDEN_DYNAMICS_POSITIVE_CONTROL（§4）—— ESTABLISHED

冻结协议（外部文档缺失参数已由评判附录一补全，本轮以脚本冻结）：
TEST 档三点皮肤；Γ_A: node0@1.0 / Γ_B: node2@1.996，t_drive=100，t0=99；
**Y_B = node0（BOUNDARY_REDUCED_N0 配置，显式声明）**；撤驱动自由演化 1000 步。

| 门 | 判据 | 实测 | 判定 |
|---|---|---|---|
| G1 | t0 边界不可区分 \|Δq0\|<0.001 | 3.98e-04（36.29715 vs 36.29675） | PASS |
| G2 | t0 隐藏态可区分 max\|Δ\|>20 | 54.26（[36.30,24.02,18.18] vs [36.30,47.93,72.45]） | PASS |
| G3 | 未来边界分叉 max\|qA0−qB0\|>10 | **18.6811**（外部基准 ≈18.68 ✓） | PASS |

命题成立：即使完整 World 是确定动力系统，有限边界观测也表现出历史依赖。
按 §4 禁令登记：该现象属 **World 层**，不得改造为 TSS 的 H_τ。

## 二、Boundary Replay Test（§5）—— HIDDEN_SIDE_CHANNEL = PASS

配置：node0@1.0 驱动 900 步 + 撤去观测 3000 步；G0 = exp_P2A1b_3 模板
（site=t1_pair.a, warm, theta_down=0.001, rearm=500）；每步签名 =
(q_skin, u_i, collector.pre_trace, ensemble pre_traces, l1.activation)
+ occurrence 事件字段表；比较用 `==` 逐位判等，非近似。

| Gate | 内容 | 结果 |
|---|---|---|
| Gate 0 | live 臂独立构造 ×2（自确定性基线） | 签名/事件表/q 轨迹全部逐位一致 → PASS |
| Gate 1 | live vs replay（replay 臂**零 World 对象**，喂录制 Y_B 序列） | 签名/事件表逐位一致 → PASS |

occurrence 事件（两臂同一）：`t_up=673, t_down=2828, t_rearm=3328,
epoch_id=1, count=1`——事件比较被真正行使（首轮 1100 步撤去窗过短
事件未及完成，已延至 3000 步与 exp_P2A1b_3 判据 2 预算对齐）。

结论：World 与下游 D_i+G0 之间**无未声明耦合**（无共享 RNG/全局步数/
对象引用/未来访问侧信道）；§5 前置条件满足，不阻塞 W1 建设。

## 三、方法说明

- G0 全程只运行未修改（§21 READ_ONLY）。
- 重放判等用浮点 `==`（bit-exact），与 EXP-E0-01 复放纪律一致。
- 复现入口：
```bash
PYTHONIOENCODING=utf-8 python research/wt0/wt0_positive_control.py   # exit 0
PYTHONIOENCODING=utf-8 python research/wt0/wt0_boundary_replay.py    # exit 0
```
