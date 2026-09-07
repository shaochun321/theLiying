# TSS 资格台账 (QUALIFICATION LEDGER)

> 建立于 2026-09-06（外部实测反馈清单 §7 的诉求）。冻结资格结果的运行
> 出处台账——区分"历史资格记录"与"当前版本重新复现结果"。
> **今后约定：任何新资格冻结必须同步在此记账。**
>
> 环境（下列全部记录共用）：Windows 10 (GBK console)，Python 3.14.3，
> `PYTHONIOENCODING=utf-8`，仓库根 `J:/cell-cc`，dt=0.001。
> 精确数值（Δt/onset 步数/电流值）对环境与浮点执行序敏感，均为
> representative observed run；资格判定依赖的是结构性质
> （产生/不产生、方向、窗口覆盖、精确零负例），不是具体数字。

## M1 — H_τ 物理历史保持核（TSS-R1c）

- 命令: `python -m tss.tests.test_history_kernel`
- commit: `db92165`（实现），日期 2026-09-06，时长 ~2min
- 结果: T-R1C-1~8 **8/8 PASS**
- 关键统计: 可读窗实测 723 步（解析 723）；单脉冲衰减与 e^{-n·dt/τ} 容差
  1e-6 内吻合；最小间隔 12 脉冲峰值 1.1553 ≤ 上界 1.1553；真实链路
  8000 步进入 1 次@step 384、充电 1 次
- 参数出处: τ_h=600 步（EXP-T1-01 slow，TSS-3a 裁定复用）；C_h=q_pulse=1.0

## M2 — 统一 Θ（C_Θ 物理比较器）

- 命令: `python -m tss.tests.test_theta_unified`
- commit: `dafba5f`，日期 2026-09-06，时长 ~3min
- 结果: T-TH-1~9 **9/9 PASS**
- 关键统计: 真实链路 源@389，Δt={15:321, 21:360, 24:312}（representative；
  外部独立复跑 {315,355,308}，方向性质一致）；阻断实验下游 0.2146 vs 0.0
- 裁定出处: C-02=全物理 MOSFET（用户 2026-09-06）

## C0 — 耦合目标对审计（EXP-C0-01/02）

- 命令: `python -m tss.tests.test_c0_relation_order_audit`
- commit: `e855a7d`，日期 2026-09-06，时长 ~8min（12 站点 × 10 种子）
- 种子: default(bundle_id) + 81000..89000（`_reseed_site` 显式重建）
- 结果: level-1 合格 **9 站点**（10/7/12 淘汰）；level-2 合格 **25 对**
  （Δt₂⊂[35,319]）；排除 11 对；r 幅度 [0.0026, 0.3660] (n=97)
- 判据: TSS-3a 三条（全产生/全正/极差≤min），两级施加

## C1 — 关系次序耦合候选 c_ro

- 标定: `python -m tss.tests.exp_C1_adapter_calibration`（EXP-C1-01）
  - commit `18ec583`，~5s；k=1.401306e-04 实测 → C=7.920427e-07 反解
- 资格: `python -m tss.tests.test_c1_coupling`
  - commit `7f629fa`，~10min（10 种子真实链路共享测量）
  - 结果: T-C1-1~11 **11/11 PASS**
  - 关键统计: 3 代表对 × 10 种子 = 30/30 恰在后继关系步产生；阴性对照
    (29≺26) fwd=5/10 rev=5/10（与 EXP-C0-02 审计一致）；§11 判据链
    真实发生@389 → r@701/749 → c_ro@[749] → 下游 0.4362 vs 阻断 0.0000
  - 措辞: c_ro=耦合输出/组织候选（K-05），非新生成元；"方向"未冻结

## E0 — 事件核/残差源类型审计（E-1~E-5）

- 命令: `python -m tss.tests.test_e0_event_type_audit`
- 日期 2026-09-07，时长 ~1min（单种子真实链路 + 复放）
- 结果: T-E0-1~4 **4/4 PASS**（**类型审计资格，非事件核资格**——
  06 §6#12 禁止宣称"事件核已工程化"仍然生效）
- 关键结论:
  - E-1 六分量审计冻结（event_core_contract.py）: θ/Π/W/𝒞 可由既有
    结构承载；**K 无持久存储（EXISTS_PARTIAL）、ℒ 是真实缺口（GAP：
    tss 层元件不在 organism census，账本观察者不可见，实测确认）**
  - EXP-E0-01 复放算子地板: frozen c_ro 链从声明父输入端口（r_x/r_y）
    复放 **bit-exact**（fires=[749] 与 C1 一致，下游 0.436181，残差
    精确 0.0）；扰动录制（删父 A 脉冲）→ 复放归零（非同义反复）
    ⇒ Replay[𝔈] 物理可执行，未来任何非零 ℛ 都是真实差异
  - E-4 约束一（持续真实激活）单发生级证据已有（T-C1-1 30/30），
    **跨发生持续性未测**；约束二（拓扑关联保护）RULING_REQUIRED
  - 待裁定登记 R-E0-1~5（存储方式/残差阈值流程/拓扑保护定义/
    Xin 正定义/影子层收纳）——组织候选资格在 R-E0-3 裁定前不可取得

## 已知未达标（LIM，不在资格清单内但保持可见）

- LIM-RPREC-READOUT-001（2026-09-06 定量）: 压缩链诊断
  `python -m tss.tests._diag_rprec_effect_compression`（PYTHONHASHSEED=0，
  ~3min）——总压缩 297× = 8.3×(w→G 工作点) × 35.8×(积分稀释)；效应上限
  0.117% < 1% 阈值。外部评判 3-seed 独立复现 FAIL 一致。
  详见 cell-cell/docs/degradation_registry.md LIM 节。

## 复现指引

全量资格复现（分钟级到 20 分钟级不等，见 EXPERIMENT_MANIFEST 时长列）：
```bash
cd J:/cell-cc
PYTHONIOENCODING=utf-8 python -m tss.tests.test_history_kernel
PYTHONIOENCODING=utf-8 python -m tss.tests.test_theta_unified
PYTHONIOENCODING=utf-8 python -m tss.tests.test_c0_relation_order_audit
PYTHONIOENCODING=utf-8 python -m tss.tests.exp_C1_adapter_calibration
PYTHONIOENCODING=utf-8 python -m tss.tests.test_c1_coupling
```
快速回归（不含资格实验）: `pytest tss/tests -m "not longrun"`
