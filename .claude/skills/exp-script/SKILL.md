---
name: exp-script
description: cell-cc 长程实验脚手架与监控规范。编写新实验脚本（exp_*.py，尤其 >10k 步）、启动或监控长程实验时调用。含账本字段表、ν探针强制规则、定时采样节奏、早停判据、脚手架样板。
---

# 长程实验脚手架与监控（exp-script）

## 脚手架样板（写新 exp_*.py 时）

- 位置：`nexus_v1/tests/exp_*.py`（TSS 侧：`tss/tests/exp_*.py`，不被 pytest 收集，需登记 `tss/EXPERIMENT_MANIFEST.md`）
- 路径写法：`sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))`（禁止硬编码 `d:\cell-cc` / `j:\cell-cc`）
- 标准构造：`VariantCircuit()` + `World/Body/HeatSource`（`c.world = world`），主循环 `for step in range(1, TOTAL+1): c.step({}, DT)`
- 常量置顶：`TOTAL / DT / SAMPLE / LOG_INTERVAL / SNAPSHOT_EVERY`
- 结尾输出 `=== 验收 ===` 段：逐条判据 `J1..Jn PASS/FAIL + 实测值`
- 参考格式：`nexus_v1/tests/exp_T071_fixA_step4.py`（表头 `step|DR5%|dist|sp2y|T4.1p|fill|ω_std|ν_sys|chrg%`）
- 运行时加 `PYTHONIOENCODING=utf-8` 前缀（Windows GBK 控制台）

## 账本字段：每条 LOG_INTERVAL 行必须暴露

（日志头格式参见 `exp_phase3_1M.py`）

| 字段 | 来源 | 含义 | 告警阈值 |
|------|------|------|----------|
| `Nv`（Noether new） | `len(c._noether_probe._violations) - prev` | 本窗口新增违规数 | **>0 立即打印违规详情** |
| `H_w`（weight entropy） | `c._entropy_probe.summary()['total_entropy']` | 权重分布熵 | <1.0 警告（权重塌缩） |
| `R_su`（efference ratio） | `c._efference_supp_ratio` | Efference 抑制比 | ≥0.9 警告 |

每条 `SNAPSHOT_EVERY` 快照额外输出：
- `[LEDGER] Noether total=X  H_struct=Y  weight_entropy=Z`
- `[LEDGER] L5_Col_activity=A  L6_Mot_activity=B`（检测信号是否到达 Motor 层）

Noether 违规出现时立即打印 `violation_counts` 明细（如 `kcl_charge`、`energy`、`weight`）。

## ν探针强制集成规则（2026-07-07 后生效）

**NuProbe 已内置于 VariantCircuit（variant_adapter.py），每步自动 update()，每 1000 步写入 summary()["nu_probe"]。从 `circuit._nu_probe` 读取，禁止手动实例化第二个 NuProbe。**

- 每个 >10k 步实验脚本的 SAMPLE 行必须含：`ν_sys（system_nu）| chrg%（charging bundles 占比）`
- 实验结束必须报告 Top-N |ν| bundle（遗漏 = 丢掉最高塑性信号的 bundle）
- 不打印 `nu.report()` 的 `system_nu` 和 `n_charging` = 违规（这是探针存在的意义）

## 定时采样规则（启动后不得全程后台等待）

触发条件（任一即适用）：脚本用到 `nu_probe`/`NoetherProbe`/`EntropyLedger`/`WeightEntropyProbe`；步数 >20k；目标含"STDP权重分化/DA门控/phasic信号"等分阶段行为。

采样节奏：
- 启动后 2-5 分钟：确认日志有输出、格式正常、无立即崩溃
- 前 10%（热身期）：每 ~5 分钟读一次，确认信号链路正常激活
- 中段 10%-80%：每 ~10-15 分钟读一次，观察权重趋势（上升/下降/饱和）
- 尾段 80%-完成：每 ~5 分钟读，确认收敛或发现平台期
- 实验结束：生成分析报告（调用 work-report skill 的七节模板）

读取方法：`run_in_background` 启动的实验用 `TaskOutput(block=False)` 读当前输出；写文件的实验 Read 输出文件末尾几十行（`tail -20`）。

## 早停判据（命中任一 → 立即告知用户并建议停止）

- 关键权重（yaw Δw、col→motor 轴向权重）连续 3 个 LOG_INTERVAL 无变化（停滞）
- DA 在应激活区域持续 = 0（DA 熄灭，学习窗口关闭）
- phasic 全程 ≈ 0 且实验目标依赖 phasic 信号（无 pre-synaptic 活动，STDP 只有 LTD 侵蚀）
- fill 触零（能量耗尽，motor 停摆）
- Noether 新增违规 > 0（物理守恒破坏，结果无效）
- 核心指标（DR5%、T4.1 等）超过 50% 步数后仍等同随机基线（无收益实验）

**血的教训（T-033）**：全程后台跑完 50k 步才读输出，错过 10k 步时就能发现的"phasic≈0 → yaw 权重在衰减"，早停可省 40k 步空跑。

## 其他陷阱（memory 沉淀）

- `dt=1.0` 陷阱：eligibility trace 的 `exp(-50)≈0`，STDP 学不到 —— `learn()` 必须放入 `_propagate_bundles()`，dt 语义先查调用点
- benchmark 指标只准用电路可感知信号（patch 温差、ISI），禁读 `world.` 全局真值（HC-012 教训）
- 新聚合层复用旧层电容常量会因上游阵发性输出完全不发放（RC 时间尺度失配教训）
