"""tss.relations.generator_sigma — TSS-1：Σ_support^(1)物理支撑局部性投影原型。

TYPE:BIO（复用已有量子元通路）+ INFRA（Σ_support绑定/局部性验证）

方案依据：document - 2026-08-03T131304.153.md（TSS-1裁定）。
资格修正：document - 2026-08-03T135526.068.md（评判修正：宣称过强，
  "可达性"应降格为"物理支撑局部性投影"）。

**冻结结论（评判135526修正版）**：
  局部外部物理发生能够通过锚定链路，产生具有空间选择性的内部生成活动云。

**禁止宣称（评判明确）**：
  - 已证明皮肤点之间的物理传播
  - 已证明生成元之间的可达性
  - 已形成内部空间距离
  - 已形成方向或梯度
  - 已完成通用空间生成元

**当前实验实际证明了什么**：
  一次局部外部物理作用（HeatSource驱动），会激活部分锚定生成元（半径内的
  近邻站点31，d=1.09<radius=2.0），而不激活远方生成元（站点11，
  d=3.81>radius=2.0，HeatSource衰减因子直接为零）。切断ensemble→collector
  的bundle后collector响应归零（依赖内部神经链路）。
  这证明：外部局部物理支撑 → 内部生成元活动范围（Σ_support^(1)）。
  尚未证明：基础生成元G_i沿皮肤物理链传播到G_j（那是Σ_reach^(1)，需要额外
  满足：目标不能被外部场直接刺激；响应必须经过皮肤真实物理耦合边；切断该
  物理边后目标响应消失；结果跟随物理结构不跟随站点名称）。

**正确命名**：
  Σ_support^(1)（物理支撑局部性投影）≠ Σ_reach^(1)（生成元间物理可达性）
  当前资产只取得前者的资格。

评判裁定的Σ构造原则（供真正的Σ_reach^(1)实现时遵守）：
  不能直接读取外部欧氏坐标，应来自：
    - 实际可达链
    - 局部传播
    - 阻断实验
    - 邻接与方向性作用
    - 结构之间的响应差异

RULES.md 强制三问：
  Q1 生物对应物：感受野空间衰减与相邻神经元活动的传播依赖性——类比
     皮肤机械/热感受器感受野的空间衰减特性（Vallbo & Johansson 1984
     Hum Neurobiol 3:3-14："感受野大小与传入密度成反比，响应强度随
     距离刺激中心衰减"）。本文件复用已有的32点感温量子元阵列
     （variant_adapter.py._init_quantum_thermal_pathways），不新建
     BIO结构。
  Q2 物理结构：只读引用已有thermal_quantum_collectors/l1_warm等对象
     （32个站点全部预先构造好），不新建Neuron。阻断实验切断的是已有
     bundle（thermal_quantum_collect系列），不新建SynapticBundle。
  Q3 参数依据：HeatSource参数复用P2-B1X1d已标定场景并用物理推理定位
     radius=2.0（见_HEAT_RADIUS注释）。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, FrozenSet, List, Optional, Tuple

from nexus_v1.components.world import HeatSource
from .generator_contract import (
    GeneratorOperatorContract, SIGMA_ALLOWED_READ_FIELDS,
    SIGMA_FORBIDDEN_DECISION_FIELDS,
)

DT = 0.001
_HEAT_TEMPERATURE = 300.0  # 复用P2-B1X1d已标定值（同一站点28驱动场景）
# EXP-TSS1-01: radius=5.0（P2-B1X1d/X2c的标定值）在本场景下让近邻
# （d=1.09）和远方（d=3.81）站点都饱和到~1.0——这不是本文件的bug，是
# 已知的"高温窄半径下L1两点均饱和"现象（temporal_r_prec.py Q3已记录：
# T=500时L1两点均饱和，谁先越阈由hash扰动决定，与热源位置无关）。TSS-1
# 需要的是"近邻可达、远方不可达"的清晰对照，故用HeatSource衰减公式
# T=ambient+temperature×max(0,1-d/radius)推理：radius=2.0时远方
# d=3.81>radius，衰减因子max(0,1-3.81/2)=0（完全在范围外，不需要
# 网格搜索验证）；近邻d=1.09<radius，衰减因子max(0,1-1.09/2)=0.455
# （仍有意义响应）。实测确认：近邻response=1.002（饱和响应），
# 远方response=0.0（完全无响应）——清晰对照，推导后一次验证成功。
_HEAT_RADIUS = 2.0
_N_DRIVE_STEPS = 1600      # 复用P2-B1X2c已验证的窗口长度


@dataclass
class ReachabilityProbe:
    """一次"从source站点驱动，测量target站点响应"的探针配置。

    不持有欧氏坐标——只持有站点索引（用于查找已有collector对象）和
    响应测量结果。site_index本身不是决策依据，只是既有32点阵列的查找键
    （同site_selection.py的既定做法：站点索引用于get_frozen_site()查找，
    不用于计算距离本身）。
    """
    source_site: int
    target_site: int
    response_strength: Optional[float] = None  # 真实驱动后测得的collector峰值


@dataclass
class GeneratorSigmaReachability:
    """Σ^(1)的第一个真实资产：局部可达性生成算子。

    评判要求"结构之间的响应差异"而非坐标——本类的核心方法
    measure_reachability()驱动真实HeatSource并读取真实collector响应，
    不在任何环节调用距离公式。

    重要边界：本类只读引用circuit已有对象，不新建量子元通路（32个站点
    的L1/HC/ensemble/collector在VariantCircuit构造时已经全部就位）。
    """
    circuit: object   # VariantCircuit或其子类实例（已包含32点量子元阵列）
    source_site: int
    probes: List[ReachabilityProbe] = field(default_factory=list)

    def add_target(self, target_site: int) -> None:
        self.probes.append(ReachabilityProbe(
            source_site=self.source_site, target_site=target_site))

    def _drive_and_measure(self, cut_bundle_ids: FrozenSet[str] = frozenset()) -> Dict[int, float]:
        """驱动一次真实HeatSource（放在source_site的世界坐标上），
        测量全部已注册target的collector峰值响应。

        cut_bundle_ids：阻断实验用——切断指定bundle_id的synapse_gain
        （复用P2-B1X2c/P2-C1F-d已验证的切断方法），验证可达性确实依赖
        该链路，不是巧合的数值分布。
        """
        patches = self.circuit._thermal_quantum_patches
        source_patch = patches[self.source_site]
        heat_pos = source_patch.world_position(self.circuit.world.body)

        # 阻断实验：临时切断指定bundle，测量完毕后不恢复（每次探测都
        # 重新构造一次干净的响应轨迹记录，调用方负责决定是否重建circuit）
        cut_bundles = []
        for b in self.circuit.get_all_bundles():
            if b.config.bundle_id in cut_bundle_ids:
                b.config.synapse_gain = 0.0
                cut_bundles.append(b.config.bundle_id)

        self.circuit.world.heat_sources = [HeatSource(
            position=list(heat_pos), energy=100000.0,
            temperature=_HEAT_TEMPERATURE, radius=_HEAT_RADIUS,
            _drift=[0.0, 0.0, 0.0],
        )]

        max_response: Dict[int, float] = {p.target_site: 0.0 for p in self.probes}
        for t in range(_N_DRIVE_STEPS):
            self.circuit.step({}, DT)
            for target_site in max_response:
                collector = self.circuit.thermal_quantum_collectors[
                    f"thermpt{target_site}_warm"]
                max_response[target_site] = max(
                    max_response[target_site], collector.pre_trace)

        return max_response

    def measure_reachability(self) -> None:
        """驱动一次真实场景，把测得的响应强度写回各probe.response_strength。"""
        responses = self._drive_and_measure()
        for p in self.probes:
            p.response_strength = responses.get(p.target_site)

    def build_contract(self) -> GeneratorOperatorContract:
        """把已测得的可达性数据打包为Σ^(1)通用契约（同generator_contract.py
        的GeneratorOperatorContract形状，供后续TSS-2/CG-0复用同一套契约
        结构，不重新发明字段命名）。"""
        return GeneratorOperatorContract(
            operator_type="sigma",
            input_generators=tuple(p.target_site for p in self.probes),
            physical_carriers=(self.circuit,),
            active_interval=None,  # 本轮不接入R1PhysicalInterval的区间机制
            output_readable_fields=SIGMA_ALLOWED_READ_FIELDS,
            forbidden_decision_fields=SIGMA_FORBIDDEN_DECISION_FIELDS,
            exists_without_learning=True,  # 量子元通路全部frozen bundle
        )


def block_experiment(circuit_factory, source_site: int, target_site: int,
                     bundle_id_to_cut: str) -> Tuple[float, float]:
    """阻断实验：分别在"链路完整"和"切断指定bundle"两种条件下驱动，
    返回(response_with_link, response_cut)。

    circuit_factory：无参构造函数，每次调用返回一个新鲜circuit实例
    （阻断实验需要独立的两次驱动，不能在同一个已被驱动过的circuit上
    做第二次测量——同P2-B1X2c/P2-C1F-d已验证的"每条件用新鲜circuit"
    方法论）。
    """
    circuit_full = circuit_factory()
    probe_full = GeneratorSigmaReachability(circuit=circuit_full, source_site=source_site)
    probe_full.add_target(target_site)
    responses_full = probe_full._drive_and_measure()

    circuit_cut = circuit_factory()
    probe_cut = GeneratorSigmaReachability(circuit=circuit_cut, source_site=source_site)
    probe_cut.add_target(target_site)
    responses_cut = probe_cut._drive_and_measure(cut_bundle_ids=frozenset({bundle_id_to_cut}))

    return responses_full[target_site], responses_cut[target_site]
