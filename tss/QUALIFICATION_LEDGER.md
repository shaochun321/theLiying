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
  - 语义注记（EXT-2 P1-6，2026-09-10）：`physical_seed` 只固定相关 bundle
    的物理扰动，母体仍存在独立全局随机源（如 Langevin noise）——历史
    10-seed 资格是**复合随机环境下的鲁棒性样本**，不应解释成只扫描了
    bundle physical variation。冻结合格列表不变；未来多种子资格应区分
    `physical_seed` 与 `world_rng_seed` 两个随机变量（可做
    physical_seed × world_rng_seed 研究驱动），并同时保留 deterministic
    reproduction / stochastic robustness 两种模式，不得把固定 world RNG
    变成全部正式资格测试的唯一模式。
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

## E0-fix — E0 审计发现项修复（2026-09-07，用户裁定全修）

- 命令: `python -m tss.tests.test_e0_kernel_ledger`（T-KL-1~4）+
  `python -m tss.tests.test_deg021_dual_drive_interlock`（T-DD-1~3）+
  `python -m tss.tests._diag_deg018_dual_clock_equivalence`（EXP-DEG018-01）
- 结果: T-KL **4/4** / T-DD **3/3** PASS；母体回归 21 项 exit=0；
  DEG-020 消费方 T-R2F 4/4 + T-RLI 5/5 不退化
- 关键裁定与结论:
  - R-E0-1 已裁定（契约代码+JSON 快照）→ K 升 EXISTS，快照入库
    `tss/kernel_snapshots/c_ro_24_21.json`；ℒ 升 EXISTS_PARTIAL
    （kernel_ledger.py 只读账本；MOSFET 耗散仍未建模）
  - DEG-018 审计裁定**不合并二态**：第二时钟非冗余（t_rearm 系统性
    +500 步消费方可见；gap<500 新发生整个丢失）→
    DESIGN_DECISION_QUANTIFIED
  - DEG-019（注释侧）/DEG-020/DEG-021 RESOLVED；编号分叉解决
    （nexus_v1 版 DEG-015/016 → DEG-022/023）

## EXT-1 — 外部实测反馈修复轮（2026-09-08，《TSS (3) 全量实测后的最终修改清单》）

- 出处: 外部评判全量实测（214 pytest 212 PASS+2 XFAIL；17 非 pytest 项
  16 exit 0 + 1 exit 1；母体 21/21）→ `cell-cell/交叉比对/` 清单
- 修复内容与验证:
  - **DEG-024（唯一严重实现错误）**: KernelEnergyProbe neuron heat 误乘
    dt 少记 1000×→已修；新增 **T-KL-5 跨账本守恒**（probe vs 母体
    Σ`_cumulative_heat_out` 增量，rel_tol=1e-9）；修复后
    probe=0.3705778 与母体精确吻合；T-KL-1~5 **5/5 PASS**；
    ℒ 保持 EXISTS_PARTIAL（MOSFET 耗散仍未建模，不升级）
  - **exp_P2A1b_3（唯一 exit 1）**: 判据4 同步 epoch/token 语义（显式
    False→True 支撑上升沿）——exit 1 是门控正确工作非状态机 bug；新增
    判据6 负对照（同一支撑 epoch 仅 1 次 occurrence）；现 **exit 0,
    判据 6/6 PASS**；`_epoch_consumed` 未动
  - **X2c pytest 覆盖恢复**: module fixture 方案，ISO-1/2+K_R1/K_gen/
    K_out 独立收集（6 项，此前仅 1 项）；**6/6 PASS (83s)**
  - **C0 pytest wrapper**（§11 方案A，不改名）: `test_c0_relation_order_
    audit_full` 断言 run()==0
  - **markers**: lambda/sigma 移出 fast（外部实测 126s/191s）→ longrun；
    fast 层 43 项 13.9s
  - **版本配对**（§6）: `tss/VERSION_PAIRING.json`（required interface
    清单）+ `test_version_pairing` T-VP-1~2 fail-fast **2/2 PASS**
  - README DEG-021 过期 OPEN 段删除；manifest 双时长列（参考机/外部复现）
- 明确不动（评判确认保持现状）: LIM 两 XFAIL（禁调阈值）、DEG-018
  DESIGN_DECISION_QUANTIFIED、TSS-3a=测量脚本非 PASS、核心资格链
  （C1/基础生成元/E0）零改动

## EXT-2 — 2026-09-09/10 C1 理论资格复审（基于 2026-08-14 理论文档 + 外部数值复审）

- 出处: `cell-cell/交叉比对/TSS C1 理论资格复审后的代码修改清单.md`。
  本轮**零物理路径改动**——只修 qualification semantics / test naming /
  audit boundary / documentation，C1 工程递归链不是失败代码。

### A8 父层同类不可重构

- 外部实测: 对父 relation event 间隔 Δt，c_ro_actual 可由父层同型
  PhysicalHistoryKernel + PhysicalThetaComparator 重构，测试范围内
  最大残差 ≈ **5.12e-15**（仅浮点误差）
- 本轮机器化: `test_c1_coupling.py::test_c1_6b_parent_theta_reconstructibility`
  （14 个 Δt₂ ∈ [1,800]，isclose 1e-12，同型栈重构实测残差 **0.0**
  bit-exact；Δt≥723 可读窗两边全零）——该测试 PASS 的语义 =
  **A8_NOT_MET 被稳定复现**，不是生成元资格 PASS
- 原 T-C1-6 改名 T-C1-6a（弱基线次序判别）：只证明不可由无记忆 AND /
  序盲对称基线重构，不再代表 A8
- **RULING: A8 NOT_MET**

### Adapter 信息压缩（P1-4 诊断）

- `_diag_c1_parent_amplitude_information_loss` exit 0（2026-09-10）:
  固定 Δt₂=50，两父幅度 7×7=49 越阈组合（0.002~0.36，覆盖 EXP-C0-02
  实测域）输出全等 **0.4340310902405273**（与外部实测逐位一致）；
  发放阈值实测 ≈1.617e-3（设计点 r_min=0.0026 为其 1.61×）
- 登记: level-2 当前消费的是"关系是否发生 + 发生时间"，而不是完整
  父关系幅度（设计现状，不判 bug；禁改 adapter 阈值保留 amplitude）

### Cross-occurrence（P1-5 诊断）

- `_diag_c1_cross_occurrence_history_reconstruction` exit 0（2026-09-10）:
  8 个 epoch gap ∈ [1204,5000] 第二次输出增强 ×1.0004~×1.1995 全部复现；
  同型栈重构残差 0.0，解析 H_τ 指数叠加最大相对残差 **9.81e-15**
- 登记: history dependence observed；fully explained by existing H_τ；
  **no independent persistent organization variable established**

### A9 谱系

- static address lineage: **PASS**（T-C1-9a，原 T-C1-9 改名——只证明
  静态结构地址谱系，不代表 runtime relation-instance lineage）
- runtime relation-instance lineage through adapter: **GAP**
  （`_diag_c1_runtime_lineage_collision` exit 0，2026-09-10：
  adapter.step(r, dt) 无 instance 身份端口，不同 lineage 声明 + 相同
  r trace → pulses/c_ro 逐位相同）。本轮只登记不实现 binder（P1-3：
  未来方向 = 物理路径原样 + 独立 lineage sidecar，待理论裁定）

### 总状态

```text
C1 engineering recursion: PASS
new-generator qualification: NOT_QUALIFIED
K-06 organization qualification: BLOCKED
```

机器可读状态常量: `tss/relations/coupling_contract.py` `C1_*`（纯审计
状态，不进物理路径，禁止据此加 if/else）。验收运行:
`pytest tss/tests/test_c1_coupling.py` 12/12 PASS（含 6b）+ 3 diag exit 0
+ 收集数 223→224 + 母体 21 项回归（2026-09-10）。

## 已知未达标（LIM，不在资格清单内但保持可见）

- LIM-RPREC-READOUT-001（2026-09-06 定量）: 压缩链诊断
  `python -m tss.tests._diag_rprec_effect_compression`（PYTHONHASHSEED=0，
  ~3min）——总压缩 297× = 8.3×(w→G 工作点) × 35.8×(积分稀释)；效应上限
  0.117% < 1% 阈值。外部评判 3-seed 独立复现 FAIL 一致。
  详见 cell-cell/docs/degradation_registry.md LIM 节。
  - **设计轮一收口（2026-09-07，EXP-LIM-01 标度律实测）**：多束并行
    读出方向被定量否证充分性——效应量层 N-不变（0.0035%@N=1 vs
    0.0034%@N=4，上限 ΔG/G 与 N 无关）；阻断距离层线性 4.035×@N=4、
    N*≈132 仅解一层。不建原型，LIM 保持可见；剩余方向：工作点上移 /
    判据改机制层等效量。

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
