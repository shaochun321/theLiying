"""tss.relations.ratio_r_part_ternary — T3-C2: r_part/r_ρ 三元扩展
（短收口，通过后立即冻结，不做四元起扩展）。

TYPE:HYBRID

方案依据：cell-cell/claudecode方案/基础生成元双轨落地方案_v2_2026-07-16.md
第二十一节 21.6（L1）。第十二/十三份交叉比对批判确认 T3-C2 应做但限定为
"一次性原语资格测试"——证明 `r_ρ^τ` 能接收任意局部活跃关系集合，不是只能
处理固定二元组，通过后立即冻结，不向四元/五元/64元扩展。

═══════════════════════════════════════════════════════════════════════
强制三问（复用 T3-B/T3-C1 已确立的结论，三元扩展不改变生物对应物/物理
结构类型，只是共享池从两路输入变成三路）
═══════════════════════════════════════════════════════════════════════

Q1. 生物对应物是什么？
    与 `RPartCircuitT3`（T3-B）完全相同——分流抑制/横向抑制池是真实皮层
    机制（Carandini & Heeger 2012）。三元扩展对应"三个感受野竞争同一片
    横向抑制神经元"，机制不变，只是竞争通道数从2变3。

Q2. 物理结构是什么？
    Sources → SynapticBundle → Targets，与 T3-B 同构，扩展为三路：

      ξ_28 (thermal_quantum_collectors["thermpt28_warm"]，t2_chain hub)
      ξ_31 (thermal_quantum_collectors["thermpt31_warm"]，t1_pair b / t2_chain NB1)
      ξ_23 (thermal_quantum_collectors["thermpt23_warm"]，t2_chain NB2)
          │
          └─(frozen bundle, 各自独立)→ channel_relay_{28,31,23}
              (GradedPotentialRelay，三个同构实例，T3-C1已验证组件，不改动)

      shared_pool = DivisiveNormalizationReceptor(...)  # 三通道共享同一实例

    `DivisiveNormalizationReceptor.normalize()` 本身对输入路数无限制，
    `dt=0` 只读技术（12.2第1点已验证）同样适用于任意路数：
        normalize(i_28+i_31+i_23, dt)   # 真实dt，更新池一次
        normalize(i_28, 0.0)            # dt=0，只读
        normalize(i_31, 0.0)
        normalize(i_23, 0.0)
    三个 `GradedPotentialRelay` 实例各自独立状态（同T3-C1R/T3-C1既定模式，
    不共享中继内部状态，只共享上游 DN 池）。

Q3. 每个参数的依据是什么？
    - 三点选择：复用 T0 冻结集合 `FROZEN_THERMAL_SITES["sites"]` 的
      28/31/23（`t1_pair`=28↔31，`t2_chain`=31↔28↔23的完整链，28是两条
      最短出边的共同端点/真实几何邻接），不新选点，遵守 T0 冻结纪律。
    - `_W_XI_TO_CHANNEL=0.3`：直接复用 T3-B 已验证取值（同一 ξ 源系谱，
      同T1/T3-B/T3-C1一致的复用链条）。
    - DN 池参数：直接复用 T3-B 的 `_DN_SIGMA`/`_DN_POOL_CAPACITANCE`/
      `_DN_POOL_R_LEAK` 类默认值起点（同T3-B Q3 说明，预期需要后续校准）。
    - `GradedPotentialRelay` 三个实例：全部用类默认参数（同T3-C1R已标定
      的 `capacitance=1.0`/`r_leak=2.0`/`g_r=1.0`/`a_max=10.0`），三个
      实例同构（同一组参数），不为三元扩展重新标定。
"""

from __future__ import annotations

from typing import Dict, List

from .site_selection import FROZEN_THERMAL_SITES
from nexus_v1.circuit.variant_adapter import VariantCircuit
from nexus_v1.circuit.bundle import BundleConfig, SynapticBundle
from nexus_v1.components.neuron import Neuron, NeuronConfig, ChannelConfig
from nexus_v1.components.compensation import DivisiveNormalizationReceptor
from nexus_v1.components.graded_potential_relay import GradedPotentialRelay

DT = 0.001

# ── T3-C2 专属标定常量（复用 T3-B 已验证取值，见 Q3）──
_W_XI_TO_CHANNEL = 0.3
_DN_SIGMA = 1.0
_DN_POOL_CAPACITANCE = 5.0
_DN_POOL_R_LEAK = 5.0
_TARGET_CAPACITANCE = 0.05  # 同 T3-B _CHANNEL_CAPACITANCE
_TARGET_R_LEAK = 5.0
_TARGET_GM = 20.0

# 三元扩展固定用 T0 冻结的完整链：28(hub/t1_pair a)/31(t1_pair b)/23(t2_chain NB2)
_TERNARY_SITE_IDS = (28, 31, 23)


def _bundle_target_config(site_id: int) -> NeuronConfig:
    """Bundle 的形式化目标——只为让 `propagate()` 有一条有效的 Memristor
    通路可以计算原始电流，本身不承担最终读出（最终读出由
    `GradedPotentialRelay` 承担，同 T3-B `channel_*` Neuron 的既有用法：
    Bundle 的 target 存在是接口要求，真正的关系值走 `step_rpart3()` 手动
    路由，不经 `apply_to_targets()`）。
    """
    return NeuronConfig(
        neuron_id=f"rpart3_bundle_target_{site_id}",
        region=0x01,
        spiking=False,
        capacitance=_TARGET_CAPACITANCE,
        r_leak=_TARGET_R_LEAK,
        inertia=1.0,
        channels=[ChannelConfig(name="default", v_threshold=0.0, gm=_TARGET_GM)],
    )


def _frozen_bundle(bundle_id: str, sources, targets, weight: float) -> SynapticBundle:
    cfg = BundleConfig(
        bundle_id=bundle_id,
        learning_rule="frozen",
        initial_weight=weight,
        weight_max=weight,
        synapse_gain=1.0,
        bundle_role="feedforward",
        remodel_cost_kappa=0.0,
    )
    return SynapticBundle(cfg, sources, targets)


class RPartCircuitT3Ternary(VariantCircuit):
    """TYPE:HYBRID — T3-C2 三元扩展：在冻结集合 {28,31,23} 上叠加共享池
    r_part/r_ρ 生成元，验证 `r_ρ^τ` 能接收任意局部活跃关系集合（不止二元）。

    子类叠加，不修改母本 `VariantCircuit`（同 `RPartCircuitT3` 先例）。
    只在专项测试里实例化，常规回归套件不受影响。短收口：通过后立即冻结，
    不向四元/五元/64元扩展（方案第二十一节 21.6）。
    """

    def __init__(self):
        super().__init__()

        assert set(_TERNARY_SITE_IDS) <= set(FROZEN_THERMAL_SITES["sites"].keys()), (
            "三元扩展的三个点必须全部来自 T0 冻结集合，不得新选点")
        self.rpart3_site_ids = _TERNARY_SITE_IDS

        self.rpart3_xi = {
            site_id: self.thermal_quantum_collectors[f"thermpt{site_id}_warm"]
            for site_id in _TERNARY_SITE_IDS
        }

        # ── 三个同构 GradedPotentialRelay 实例（T3-C1已验证组件，不改动）──
        self.rpart3_relay: Dict[int, GradedPotentialRelay] = {
            site_id: GradedPotentialRelay() for site_id in _TERNARY_SITE_IDS
        }

        # ── 共享分流池（三通道共享同一实例，路径B机制的三元推广）──
        self.rpart3_shared_pool = DivisiveNormalizationReceptor(
            sigma=_DN_SIGMA,
            pool_capacitance=_DN_POOL_CAPACITANCE,
            pool_r_leak=_DN_POOL_R_LEAK,
        )

        # ── bundles: xi → 形式化target（各自独立，非共享目标，无需求和）──
        self.rpart3_bundle_targets: Dict[int, Neuron] = {
            site_id: Neuron(_bundle_target_config(site_id)) for site_id in _TERNARY_SITE_IDS
        }
        self.rpart3_bundles: Dict[int, SynapticBundle] = {
            site_id: _frozen_bundle(
                f"rpart3_xi_{site_id}_to_pool",
                [self.rpart3_xi[site_id]],
                [self.rpart3_bundle_targets[site_id]],
                _W_XI_TO_CHANNEL,
            )
            for site_id in _TERNARY_SITE_IDS
        }

        self._rpart3_pool_step_count = 0

    def rpart3_relation_relays(self) -> List[GradedPotentialRelay]:
        return list(self.rpart3_relay.values())

    def rpart3_relation_bundles(self) -> List[SynapticBundle]:
        return list(self.rpart3_bundles.values())

    def rpart3_relation_pool_stats(self) -> Dict[str, float]:
        """同 T3-B `rpart_relation_pool_stats()` 的既定模式，三元推广。"""
        return {
            "pool_instance_count": 1,
            "pool_step_count": self._rpart3_pool_step_count,
            "pool_activity": self.rpart3_shared_pool.pool_activity,
        }

    def get_all_bundles(self):
        """同 T3-B `RPartCircuitT3.get_all_bundles()` 既定修正：关系 Bundle
        进census，关系 relay/neuron 排除。"""
        return super().get_all_bundles() + self.rpart3_relation_bundles()

    def step_rpart3(self, dt: float = DT) -> Dict[str, Dict[int, float]]:
        """手动传播一步三元 r_part/r_ρ 生成元链路（同 T3-B `step_rpart()`
        方法论，独立由测试驱动，不接入 circuit.step() 主循环）。

        返回 {"i_raw": {site_id: ...}, "y": {site_id: ...}, "z": {site_id: ...}}
        """
        # 1. 各自 Bundle propagate，取原始电流（propagate() 无副作用）。
        i_raw: Dict[int, float] = {}
        for site_id in _TERNARY_SITE_IDS:
            currents = self.rpart3_bundles[site_id].propagate()
            i_raw[site_id] = currents[0] if currents else 0.0

        # 2. 共享池按三路电流之和更新一次（真实 dt）。
        total = sum(i_raw.values())
        self.rpart3_shared_pool.normalize(total, dt)
        self._rpart3_pool_step_count += 1

        # 3. 分别只读读出（dt=0，不产生副作用，12.2 第1点已验证的技术）。
        y: Dict[int, float] = {
            site_id: self.rpart3_shared_pool.normalize(i_raw[site_id], 0.0)
            for site_id in _TERNARY_SITE_IDS
        }

        # 4. 显式驱动各自 GradedPotentialRelay（线性中继，T3-C1已验证）。
        z: Dict[int, float] = {
            site_id: self.rpart3_relay[site_id].step(y[site_id], dt)
            for site_id in _TERNARY_SITE_IDS
        }

        return {"i_raw": i_raw, "y": y, "z": z}
