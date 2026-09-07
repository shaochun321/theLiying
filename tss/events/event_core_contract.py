"""tss.events.event_core_contract — E0：事件核/过程/残差源类型审计契约。

TYPE:INFRA（审计结论与类型契约，无物理载体主张——先例：coupling_contract.py）

路线依据：08_下一阶段路线图.md §8（E-1~E-5）+ §10 E0。
开启条件（§8 门槛）：**"当至少一个耦合生成元走通后，再开启"——已满足**：
c_ro 耦合候选 11/11 PASS 且 §11 最终判据单次跑通（commit 7f629fa，
见 QUALIFICATION_LEDGER.md C1 节）。

审计对象（06_当前冻结状态 §3）：C-05（事件核分量类型未冻结）、
C-06（残差资格门未建立）、C-07（组织约束未实现）。
本模块是 U-06 流程"类型定义 → 端口 → 最小载体 → 可证伪实验"的
**第一环（类型定义/审计）**，不实现载体，不授予任何资格。

═══ 措辞纪律 ═══

06_当前冻结状态 §6#12 冻结禁止宣称"事件核、残差源、Xin 后验重整已经
工程化"。本契约全程遵守：下方所有 EXISTS 状态的含义是"该分量可由
**既有**结构承载"（审计发现），不是"事件核已存在"。凡需用户权力的
决定一律标 RULING_REQUIRED 列入待裁定登记，不代行冻结。

═══ E-1：事件核六分量类型审计（C-05）═══

    𝔈 = (K, θ, Π, W, ℒ, 𝒞)      （06_后验重组 §3——后期理论整理式）

以已合格的 c_ro 对栈（2×RelationEventAdapter + 2×PhysicalEntryGate +
1×PhysicalHistoryKernel + 1×PhysicalThetaComparator）为审计样本，
逐分量判定"最低类型是什么、今天由什么承载、缺什么"。结论冻结于
EVENT_KERNEL_COMPONENT_AUDIT（test_e0_event_type_audit T-E0-2 逐条可执行
验证）。关键审计发现：

  - K（结构骨架）：类地址谱系 + 类名清单可完整枚举，但**无持久物理
    存储**——当前只存在于进程内 Python 对象；存储方式即 C-05 未冻结项。
  - ℒ（资源账本）：**GAP**——tss 层组件（适配器神经元/门/核/比较器）
    不在 organism census（get_all_neurons/get_all_bundles）内，对
    nexus_v1.ledger 全部观察者不可见；𝔈 的能量账本今天不存在。
    这是 E0 的真实缺口发现，不是文字性备注。
  - 𝒞（已合格测量）：由 QUALIFICATION_LEDGER.md + 契约冻结常量承载
    （文档级，非物理存储——与 K 同属 C-05 存储裁定范围）。

═══ E-2：残差源类型与资格门（C-06）═══

    ℛ = Y − Replay[𝔈]           （C-06 候选式）

四类来源的**类型**在此冻结（判定阈值/流程不冻结——RULING_REQUIRED，
避免 DEG-020 重复魔数教训）。资格门的物理前提由 EXP-E0-01 建立：

  **EXP-E0-01（复放算子地板，test_e0 T-E0-3 实测 2026-09-07）**：
  对 frozen c_ro 链，从声明输入端口（两条父关系电流 r_x/r_y——
  coupling_contract §6.2① 的合格输入）录制真实链路轨迹，馈入全新
  同参栈实例，Y_replay 与 Y_live **bit-exact 相同**（c_ro 产生步
  完全一致，下游电压残差 = 0.0）；扰动录制内容（删除父 A 脉冲）则
  复放输出归零——复放算子对记录内容敏感，非同义反复。
  ⇒ frozen 链上 Replay[𝔈] 物理可执行且残差地板为精确零：未来任何
  非零 ℛ 都是真实差异，不是复放机器自身的噪声。
  （对比：可塑链读出受 LIM-RPREC-READOUT-001 压缩 297×——残差若经
  可塑读出测量会被同一机制压缩，资格门设计必须避开该读出路径。）

  注入纪律（C-06"残差不得外部直接注入"的操作化）：复放的唯一合法
  注入点 = 𝔈 声明的父输入端口（对 c_ro 即 r_x/r_y）；向链路中段任何
  元件直接写状态（HC-009 原违规拓扑）都不构成 Replay[𝔈]。

═══ E-3：预生成候选（C-07 前半）═══

  既有承载：event_support.py 的 CANDIDATE/REJECTED_* 三态 +
  AddressRegistry 地址空间——候选可登记、可回指谱系，但**不因登记
  取得组织资格**（create_event_candidate 的拒绝路径是守卫，
  T-E0-4 验证其仍然生效）。E0 不新增状态机（READY/ACTIVE/EXIT/REARM
  仍按 P2-B1X 降格结论保持缺失，不写占位）。

═══ E-4：两道组织约束（C-07 后半，K-06"耦合→组织候选"的取得条件）═══

    持续真实激活 ∧ 拓扑关联保护 ⇒ 正式组织候选     （§8 E-4）

  约束一（持续真实激活）：EXISTS_PARTIAL——单发生级证据已有
  （T-C1-1：3 代表对 × 10 种子 = 30/30 在后继关系步真实产生）；
  **跨发生持续性未测**（同一结构在重复外部发生下反复产生——需要
  多发生实验，属 E0 后续阶段，非类型审计范围）。
  约束二（拓扑关联保护）：RULING_REQUIRED——"动态超图关联"的可测
  定义未裁定；候选操作化方向登记于 RULING_REQUIRED_REGISTRY R-E0-3，
  本契约不代行选择。

═══ E-5：Xin 后验重组 ═══

  全部 RULING_REQUIRED：Xin 的正定义本身在用户待裁定问题册
  （理念原典审计 08 问题册：Xin 是未被吸收的物理作用/触发条件/残差源/
  新生成方向，还是另一对象？）。E-2 的 REPEATABLE_RESIDUAL 类是唯一
  可能通往 E-5 的入口（06_后验重组 §"只有持续未被旧组织吸收、具有
  独立物理作用的残差，才可触发……"），但在 Xin 正定义裁定前不建链。

═══ RULES.md 强制三问 ═══

  Q1 生物/物理对应物：INFRA 审计契约（同 coupling_contract.py 先例），
     不对应具体物理机制，不执行动力学。
  Q2 物理结构：零新结构——只读引用既有类与冻结常量；唯一"实验"
     （EXP-E0-01）复用 C1 既有链路类，无新原语。
  Q3 参数依据：零新物理参数。本模块唯一数值 REPLAY_RESIDUAL_FLOOR
     来自 EXP-E0-01 实测（bit-exact ⇒ 0.0），非设计值。
"""

from __future__ import annotations

# ─────────────────────────────────────────────────────────────────────
# 审计状态词汇（E-1 用；语义见模块 docstring 措辞纪律节）
# ─────────────────────────────────────────────────────────────────────

AUDIT_EXISTS = "EXISTS"                    # 可由既有结构完整承载
AUDIT_EXISTS_PARTIAL = "EXISTS_PARTIAL"    # 部分承载，缺口已列明
AUDIT_GAP = "GAP"                          # 今天不存在承载（真实缺口）
AUDIT_RULING_REQUIRED = "RULING_REQUIRED"  # 需用户/评判裁定，本契约不代行

_VALID_AUDIT_STATUSES = frozenset({
    AUDIT_EXISTS, AUDIT_EXISTS_PARTIAL, AUDIT_GAP, AUDIT_RULING_REQUIRED,
})

# ─────────────────────────────────────────────────────────────────────
# E-1：𝔈 六分量审计表
# 每行 = (符号, 理论角色, 最低类型, 既有承载, 状态, 缺口/备注)
# ─────────────────────────────────────────────────────────────────────

EVENT_KERNEL_COMPONENT_AUDIT: tuple = (
    ("K", "结构骨架",
     "地址谱系元组 + 链路元件类清单（2×适配器+2×门+1×核+1×比较器）",
     "AddressRegistry/GeneratedAddress + tss.relations 既有类（进程内对象）",
     AUDIT_EXISTS_PARTIAL,
     "无持久物理存储——存储方式属 C-05 未冻结项（R-E0-1）"),
    ("theta", "初始条件",
     "冻结物理参数集（C/v_peak/r_leak/w/gain/physical_seed/门核比较器默认参）",
     "relation_event_adapter.py 模块常量（Q3 溯源）+ M1/M2 零自由参数默认值",
     AUDIT_EXISTS,
     "全部有 Q3/裁定出处；共参纪律（T-C1-7）已守卫"),
    ("Pi", "组合谱系",
     "parent_addresses 有向谱系（D1 occurrence → D2 关系 → D3 候选）",
     "GeneratedAddress.parent_addresses + event_support 谱系一致性检查",
     AUDIT_EXISTS,
     "P2-B1X 基础设施直接复用；D3 仅候选登记，不含资格"),
    ("W", "窗口",
     "可读窗上界 + 逐对 Δt₂ 实测范围",
     "coupling_contract.QUALIFIED_LEVEL2_PAIRS（Δt₂⊂[35,319]）+ T_READ=723",
     AUDIT_EXISTS,
     "EXP-C0-02 冻结；T-E0-2 验证 well-formed（0<min≤max<723）"),
    ("L", "资源账本",
     "𝔈 所辖元件的能量/耗散账目（只读观察者语义）",
     "（无）——tss 层组件不在 organism census，nexus_v1.ledger 不可见",
     AUDIT_GAP,
     "E0 真实缺口发现；补账本=新载体工程，属 U-06 后续环节+R-E0-1"),
    ("C", "已合格测量",
     "资格记录（判据/命令/commit/关键统计）",
     "QUALIFICATION_LEDGER.md + coupling_contract 冻结常量 + 测试套件",
     AUDIT_EXISTS,
     "文档级承载；是否需物理级存储并入 R-E0-1 裁定"),
)

# ─────────────────────────────────────────────────────────────────────
# E-2：残差源四类（类型冻结；阈值/流程 RULING_REQUIRED → R-E0-2）
# ─────────────────────────────────────────────────────────────────────

RESIDUAL_DEFINITION = "R = Y - Replay[E]"  # C-06 候选式；E=事件核样本

RESIDUAL_SOURCE_NOISE = "NOISE"                # 低于复放/跨run地板的波动
RESIDUAL_SOURCE_TECH_DEBT = "TECH_DEBT"        # 可归因于已登记 DEG/LIM
RESIDUAL_SOURCE_MODEL_INSUFFICIENCY = "MODEL_INSUFFICIENCY"  # 已知结构改动可消除
RESIDUAL_SOURCE_REPEATABLE = "REPEATABLE_RESIDUAL"  # 跨种子可重复且不可归因
# —— 仅 REPEATABLE_RESIDUAL 可作为 E-5 入口（Xin 正定义裁定后）

RESIDUAL_SOURCE_CLASSES: tuple = (
    RESIDUAL_SOURCE_NOISE,
    RESIDUAL_SOURCE_TECH_DEBT,
    RESIDUAL_SOURCE_MODEL_INSUFFICIENCY,
    RESIDUAL_SOURCE_REPEATABLE,
)

# EXP-E0-01 实测（2026-09-07，test_e0_event_type_audit T-E0-3）：
# frozen c_ro 链复放 bit-exact ⇒ 复放算子自身残差地板为精确零。
# 非设计值——若未来复放实测非零，此常量必须随实测更新而非当阈值调。
REPLAY_RESIDUAL_FLOOR = 0.0

# C-06 注入纪律的操作化：复放唯一合法注入点=𝔈 声明的父输入端口。
REPLAY_INJECTION_PORT = "declared_parent_inputs"   # 对 c_ro 即 (r_x, r_y)

# ─────────────────────────────────────────────────────────────────────
# E-4：两道组织约束（K-06"耦合→组织候选"取得条件）
# 每行 = (约束名, 判定谓词候选, 状态, 证据/缺口)
# ─────────────────────────────────────────────────────────────────────

ORGANIZATION_CONSTRAINT_AUDIT: tuple = (
    ("sustained_real_activation",
     "结构在每次合格运行中真实产生输出（单发生级）∧ 跨重复发生持续产生",
     AUDIT_EXISTS_PARTIAL,
     "单发生级：T-C1-1 30/30（3代表对×10种子）；跨发生持续性未测"),
    ("topology_association_protection",
     "（未裁定）动态超图关联的可测定义——候选方向见 R-E0-3",
     AUDIT_RULING_REQUIRED,
     "本契约不代行定义选择"),
)

# ─────────────────────────────────────────────────────────────────────
# 待裁定登记（凡 RULING_REQUIRED 必在此有对应条目；T-E0-4 守卫非空）
# 每行 = (编号, 问题, 理论出处)
# ─────────────────────────────────────────────────────────────────────

RULING_REQUIRED_REGISTRY: tuple = (
    ("R-E0-1", "𝔈 各分量（尤其 K/𝒞）的物理存储方式如何冻结？",
     "06_当前冻结状态 C-05"),
    ("R-E0-2", "残差四类的判定阈值与判定流程（谁测、何时测、多少算可重复）？",
     "06_当前冻结状态 C-06；DEG-020 教训：不预填魔数"),
    ("R-E0-3", "拓扑关联保护的可测定义？候选：共享源站点超边（28→X 对族）/"
               "共享适配器实例/共享 level-1 关系——三者物理含义不同，需裁定",
     "08_路线图 E-4；06_当前冻结状态 C-07"),
    ("R-E0-4", "Xin 的正定义（未被吸收的物理作用/触发条件/残差源/新方向？）",
     "理念原典审计 08 待裁定问题册（Xin 条）"),
    ("R-E0-5", "影子层收纳对象（事件核/未闭合组织/残差源/沉积/地址候选？）"
               "及候选重新进入正式结构的裁定权归属",
     "理念原典审计 08 待裁定问题册（影子层条）"),
)

# ─────────────────────────────────────────────────────────────────────
# 禁止宣称（T-E0-4 静态守卫本契约自身不越界）
# ─────────────────────────────────────────────────────────────────────

FORBIDDEN_CLAIMS: tuple = (
    "事件核已工程化",             # 06 §6#12
    "残差源已工程化",             # 06 §6#12
    "Xin 后验重整已工程化",       # 06 §6#12
    "组织候选资格已取得",         # E-4 约束二未裁定 ⇒ 合取不成立
    "c_ro 已形成闭合/新生成深度",  # K-04/K-05
)
