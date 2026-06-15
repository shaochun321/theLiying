# nexus_v1 阶段性检测报告

## 项目总览

| 维度 | 统计 |
|------|------|
| 元件文件 | 14 (`components/`) |
| 电路文件 | 6 (`circuit/`) |
| 测试文件 | 18 (`tests/`) |
| 文档文件 | 19 (`docs/`) |
| 回归门控 | **5/5 PASS** |
| 总代码量 | ~5500 行（元件+电路） |

---

## 一、元件层（components/）

| 元件 | 文件 | 功能 | 状态 |
|------|------|------|------|
| Capacitor, MOSFET, Memristor, PowerRail | `semiconductor.py` | 基础半导体模型 | ✅ 稳定 |
| Neuron (MetaNeuron) | `neuron.py` | 统一神经元：RC+通道+Ca²⁺+spiking+STDP traces | ✅ 稳定 |
| VoltageRegulator, DecouplingCap, BiasCurrent, AGC | `compensation.py` | 代谢恢复+平滑+偏置+增益 | ✅ 稳定 |
| ResonantOscillator | `oscillator.py` | CPG 节律耦合 | ✅ 稳定 |
| MagnetofluidDamper | `damper.py` | 非线性阻尼 | ✅ 稳定 |
| ExtracellularMatrix | `ecm.py` | 温度场+离子缓冲+PNN 门控 | ✅ 稳定 |
| VascularCooling | `vascular.py` | NVC 血流+散热+ATP 递送 | ✅ 稳定 |
| NDRElement, InhibitorySynapse | `ndr.py` | 负微分电阻+侧抑制 | ✅ 稳定 |
| LiquidMetalRouter | `router.py` | 结构可塑性路由 | ✅ 稳定 |
| Neuromodulator | `modulator.py` | 多巴胺三因子学习 | ✅ 稳定 |
| BindingLayer | `binding.py` | 超边 AND 门（§5） | ✅ 稳定 |
| EntropyLedger | `entropy_ledger.py` | 熵账本审计 | ✅ 稳定 |
| **ShadowSandbox** | `shadow_sandbox.py` | 影子层（21N+27B+3ECM+1V） | ✅ **新建** |

---

## 二、电路层（circuit/）

| 模块 | 文件 | 功能 | 状态 |
|------|------|------|------|
| SynapticBundle | `bundle.py` | STDP/BCM 学习 + Memristor 权重 + Xin/Fruit + **E_remodel + Silent Synapse** | ✅ 增强 |
| HebbianCircuit | `hebbian.py` | 母本：6轴前庭 MET→HC→Aff→Enc→Col→Mot | ✅ 稳定 |
| VariantCircuit | `variant_adapter.py` | 变体：全部叠加组件 + 影子层 | ✅ 增强 |
| CirculationDetector | `circulation.py` | P/R/Xin 环流检测 | ✅ 稳定 |
| CircuitObserver | `observer.py` | 外部审计 | ✅ 稳定 |

---

## 三、数学建模（§编号 vs 实现对照）

### 已实现（正式定义，ACTIVE）

| §编号 | 理论 | 实现位置 | 验证 |
|-------|------|---------|------|
| §1 | 前庭转导链 MET→HC→Aff | `hebbian.py` | ✅ depth=6 |
| §2 | 多轴拓扑 (6轴) | `hebbian.py` | ✅ 6 axis |
| §3 | 成熟阶段 spine→column→area | `variant_adapter.py` | ✅ PNN 门控 |
| §4 | 学习规则 STDP→BCM→frozen | `bundle.py` | ✅ 三阶段 |
| §5 | 超边绑定层 | `binding.py` | ✅ AND 门 |
| §6 | P/R 环流检测 | `circulation.py` | ✅ 运行 |
| §7 | Xin 张力 + Fruit 生命周期 | `bundle.py` | ✅ 张力+果实 |
| §8 | 结晶检测 | `variant_adapter.py` | ✅ σ²<0.01 |
| §9 | 影子层（下葬+衰减+共振） | `variant_adapter.py` | ✅ 基础版 |
| §9+ | **影子层（结构化，21N+27B）** | `shadow_sandbox.py` | ✅ **新建** |
| ECM | 温度+PNN+离子缓冲 | `ecm.py` + `variant_adapter.py` | ✅ 22/22 PASS |
| NVC | 血管冷却+ATP | `vascular.py` + `variant_adapter.py` | ✅ 集成 |

### 降级目标（DEGRADED，未实现）

| 理论 | 文档 | 状态 |
|------|------|------|
| 层级 P/R/Xin 递归 | `modeling_hierarchical_prxin.md` | ❌ 保留参考 |
| 超边耦合面+变分内核 | `modeling_coupling_recursion_vfe.md` | ❌ 保留参考 |
| 影子驱动结构可塑性 | `modeling_shadow_dual_metric.md` | ❌ 保留参考 |
| 影子层 ν 反馈到主系统 | `modeling_shadow_layer.md` §5 | ❌ 只读模式 |

---

## 四、信号链路完整性

```
外部输入 (mechanical_inputs)
    │
    ▼
MET ──→ HairCell ──→ Afferent ──→ Encoding ──→ Column ──→ Motor
         (Ca²⁺)      (AdEx spike)   (STDP)      (BCM)     (output)
                        │                │          │
                     NDR 门控         Damper     侧抑制
                                    Oscillator
                                     Router
                                    Modulator
                                      │
                                   Binding (超边)
                                      │
                                   Xin → Shadow Layer (只读)
                                      │
                                 ECM (温度+PNN)
                                 Vascular (散热+ATP)
                                 EntropyLedger (审计)
```

**depth=6 验证**：MET(1) → HC(2) → Aff(3) → Enc(4) → Col(5) → Mot(6) ✅

---

## 五、验证覆盖

| 测试 | 文件 | 结果 |
|------|------|------|
| 母本-变体合同 | `run_variant_contracts.py` | **5/5 PASS** |
| ECM+Vascular 独立 | `test_ecm_vascular.py` | 22/22 PASS |
| 新系统 (Binding+Xin+Shadow) | `test_new_systems.py` | ✅ |
| 影子层结构化 | `test_shadow_sandbox.py` | ✅ |
| 多轴印记 | `test_multiaxis.py` | ✅ |
| 长跑 30s | `test_longrun_30s.py` | ✅ |
| PNN 临界期 | `test_pnn_critical.py` | ✅ |

---

## 六、阶段性完成判定

### ✅ 已完成

1. **完整的六层前庭转导链** — MET→HC→Aff→Enc→Col→Mot，6轴，depth=6
2. **统一的元件库** — 14 种组件，全部基于半导体原语（MOSFET/Capacitor/Memristor）
3. **三阶段学习** — spine(STDP) → column(BCM) → area(frozen)，PNN 门控
4. **超边绑定** — AND 门检测多轴协同激活
5. **预测编码** — Xin 张力 + Fruit 生命周期
6. **环流检测** — P/R 路径 + 运动势 ν
7. **结晶** — σ² < 0.01 检测权重稳定
8. **影子层** — 21 Neuron + 27 Bundle + 3 ECM + 1 Vascular，Xin 驱动 STDP 收缩
9. **物理计算** — 温度场、PNN、NVC 血管、能量守恒
10. **审计系统** — EntropyLedger + CircuitObserver + CirculationDetector

### ⏳ 进行中 / 待观测

| 项目 | 说明 | 下一步 |
|------|------|--------|
| 影子层收缩效果 | 10000 步后跨轴尚未激活 | 需更长运行（≥50000步）或增大 Xin 输入差异性 |
| 运动状态区分 | 收缩后能否区分 yaw/pitch/roll | 需要设计差异化输入测试 |
| ds² 审计 | 目前全为类空间隔 | 等收缩出现后再评估 |
| E_remodel 平衡 | κ=0.01 是否合理 | 需观测能量耗尽速率 |

### ❌ 未开始（降级目标）

| 项目 | 前置条件 |
|------|---------|
| ν 反馈到主系统 | 影子收缩验证通过 |
| 层级 P/R/Xin 递归 | ν 反馈验证通过 |
| 影子驱动结构可塑性 | 递归验证通过 |

---

## 七、风险与关注项

| 风险 | 严重性 | 现状 |
|------|--------|------|
| 影子层度规塌缩 | 🟡 中 | 自适应排斥+E_remodel 限制，10000步内无塌缩 |
| 影子层收缩太慢 | 🟡 中 | Xin 张力 ~0.02，STDP Δw 很小 |
| Unicode 编码 | 🟢 低 | `run_variant_contracts.py` 末尾打印报错，不影响逻辑 |
