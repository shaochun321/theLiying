# Cell-CC 变更日志

> 纪律性版本跟踪。每次实质性代码变更后更新此文件。

---

## v0.9.0 — 2026-06-06

### 母本分化 (Mother Differentiation)

**新增文件**:
- `nexus_v1/components/compensation.py`: 3 个新分化组件

**新增组件**:
| 组件 | 类名 | 目标 | 物理对应 |
|------|------|------|----------|
| H | `CalciumRateIntegrator` | Shadow col (spiking) | CaMKII 浓度 |
| I | `DivisiveNormalizationReceptor` | Shadow enc (sensory) | 视网膜增益控制 |
| J | `D2Autoreceptor` | DA neurons | VTA D2 自受体 |

**修改文件**:
- `neuron.py`: NeuronConfig 新增 use_calcium_integrator, use_dn_receptor, use_d2_autoreceptor flags; step() 集成
- `shadow_sandbox.py`: Shadow col 配置 CRI+spiking, Shadow enc 配置 DN
- `variant_adapter.py`: DA neurons 配置 D2R+bias+gm=8; DA 能量 refill Noether 记账
- `bundle.py`: propagate() 支持 CRI calcium_rate 信号路径
- `noether_probe.py`: xin_bound 动态缩放 (base=100k)
- `toprxin_ledger.py`: Landauer 修正 (补 kT); Section 7 GuidedConstructionAuditor

**修复**:
- DA neurons V_m=0 → 补 use_bias_current=True
- DA activation 过低 → gm: 1→8 (补偿二次门控压缩)
- DA energy refill 破坏 Noether → 记入 _cumulative_energy_in

**验证**: 50k 步, Noether 0 violations, ALL PASSED

---

### 熵账本前置化 (Entropy Ledger Pre-Step Guard)

**架构变更**:
- 熵账本从 Phase 17 (step 末尾) 移到 Phase 0 (step 开头)
- 新增 `_entropy_ledger_pre_step()` 和 `_entropy_ledger_post_step()` 方法
- 新增 `_structural_freeze` 门控 (Noether 违规时冻结结构操作)

**修改文件**:
- `variant_adapter.py`: Phase 0/Z 方法; 删除旧 Phase 17/T4
- `hebbian.py`: _structural_freeze 属性; sprout/mitosis 门控

**采样尺度保留**:
- 每步: heat accumulation
- 100步: Noether + weight entropy + TOPRXIN + recursion
- 1000步: structural entropy + structural bridge

**验证**: 50k 步, 0 violations, 0 freezes, ALL PASSED

---

## v0.8.x — 2026-06-05 (之前的工作, 从上下文重建)

- DA 电路初始化 (_init_da_circuit)
- Shadow sandbox dual-metric observation
- Circulation meter
- ECM + Vascular + Thermal membrane
- Structural growth (sprout/prune/mitosis)
- T/O/P/R/Xin entropy ledger
- Noether conservation probe
- (详细变更记录因上下文截断不完整)
