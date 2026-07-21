"""nexus_v1.generators.base_generator — 抽取既有量子热生成元为可寻址句柄（P2-A 核心）。

TYPE:BIO — 句柄本身包装的是既有 BIO 结构（10 感受野 ensemble 神经元 +
AND 门 collector，见 `circuit/variant_adapter.py:_init_quantum_thermal_pathways`
的 REF/EXP 标注）；本模块新增的是抽取/地址/输入端口纪律，不改变被包装对象
的物理行为本身。

方案依据：`cell-cell/交叉比对/评判_反馈自然单位概念修正_2026-07-20.md`
§二(术语边界修正)、§九(执行顺序步骤 1-3)。四轮交叉比对已核实并要求的抽取
方式：

    现有十神经元结构已经存在，当前任务是抽取、参数化和建立正式输入/
    输出合同，而不是从零重建。

抽取范式对齐 `relations/temporal_r_prec.py` 的 `RPrecCircuitT1`——从既有
`VariantCircuit` 实例的 `thermal_quantum_*` 属性字典里按 `(site_index,
polarity)` 取出既有对象引用，**不新建任何 Neuron/SynapticBundle**（RULES.md
"不修改母本代码添加功能"）。

RULES.md 强制三问：

  Q1 生物对应物：
    本模块不引入新的生物机制——它包装的 10 ensemble + collector 结构，
    生物对应物已在 `_init_quantum_thermal_pathways` 及其 config 工厂
    （`_thermal_quantum_ensemble_config`/`_thermal_quantum_collector_config`）
    的既有注释中给出（感受野 ensemble 阶梯编码 + AND 门时间积分）。本模块
    新增的"D_i^sim 输入端口"命名，依据反馈文档 §2.2：局部感受转导结构
    `D_i^sim: x_i^skin(t) → u_i(t)` 与生成元核心 `𝒢_i: (u_i,z_i) →
    (ż_i, ξ_i^occ)` 的范畴区分——转导层（L1 ThermalDeltaNeuron + L2
    haircell）产生 u_i，生成元核心（10 ensemble + bundles + collector，
    即 z_i）消费 u_i。

  Q2 物理结构：
    `wrap_base_generator` 只读取 `VariantCircuit` 已构造好的属性字典
    （`thermal_quantum_l1_{warm,cool}` / `thermal_quantum_hc_{warm,cool}` /
    `thermal_quantum_ensembles` / `thermal_quantum_collectors` /
    `bundles_thermal_quantum_{l1_to_hc,in,collect}`），不创建新对象、
    不修改这些对象的现有连接。地址挂载复用 `AddressRegistry.register_
    physical`/`register_generated`（前者已用于 P2-A0 的 `register_skin_
    patch`），不新增电路机制。

  Q3 参数依据：
    本模块不引入任何新的物理参数（权重/阈值等均沿用母本既有常量）。
    闭合状态机的阈值参数见 `occurrence.py` 的 Q3 说明。
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional

from ..circuit.bundle import SynapticBundle
from ..components.neuron import Neuron
from ..components.structural_address import (
    AddressRegistry, DOMAIN_OCC_THERMAL, DOMAIN_SKIN_PATCH, GeneratedAddress, StructuralAddress,
)
from ..somatosensory.transducer_neurons import ThermalDeltaNeuron
from .occurrence import Occurrence, OccurrenceClosure
from .trajectory import GeneratorTrajectory


def register_occ_thermal(
    registry: AddressRegistry, collector_label: str, parent_addr: StructuralAddress,
) -> GeneratedAddress:
    """封装：为一个 ξ^occ 生成元分配 `GeneratedAddress`（对齐 P2-A0 的
    `register_skin_patch` 一步完成注册+挂载的模式）。

    `collector_label` 即 `f"thermpt{site_index}_{polarity}"`（与
    `circuit.thermal_quantum_collectors` 的键一致，保证地址 uid 与既有
    结构的命名约定天然一致，不需要额外的映射表）。`generation_depth=1`
    表示这是从物理支撑（皮肤）直接生成的第一层生成物。
    """
    return registry.register_generated(
        domain=DOMAIN_OCC_THERMAL,
        local_key=collector_label,
        parent_addresses=(parent_addr,),
        generation_depth=1,
    )


@dataclass
class BaseGenerator:
    """𝒢_i 句柄：包装既有量子热通路的生成元核心（10 ensemble + collector +
    连接 bundles），加地址与闭合状态机。**不拥有**对象的构造/生命周期——
    所有 Neuron/SynapticBundle 字段都是对母本 `VariantCircuit` 既有对象的
    引用（`wrap_base_generator` 只读取，不创建）。

    字段边界（对齐反馈 §2.2/§2.3 的范畴区分）：
      l1/hc              — D_i^sim 转导层引用（不属于生成元核心本身，
                            只是驱动生成元核心所需的上游输入点）
      ensemble/collector/
      bundle_in/bundle_col — 𝒢_i 生成元核心本身（z_i 内部状态）
      bundle_l1_hc        — 转导层内部连接，随 l1/hc 一起引用，供 feed()
                            完整复刻既有三级传播序列
      address             — α_gen(ξ_i^occ)，父地址回指皮肤支撑
      closure             — 触发/退出/重整状态机，读 collector.pre_trace
      trajectory          — 可选的 Λ^phys 轨迹记录器（`generators/trajectory.py`）；
                            为 None 时 `tick()` 不做任何记录（默认，向后兼容）；
                            非 None 时每次 `tick()` 自动追加一条 `TrajectoryRecord`。
                            与 `Occurrence` 并列（Λ^org ∥ Λ^phys），不融合进
                            `Occurrence` 本身（反馈文档 §5.3 纪律）。
    """
    site_index: int
    polarity: str
    address: GeneratedAddress
    l1: ThermalDeltaNeuron
    hc: Neuron
    ensemble: List[Neuron]
    collector: Neuron
    bundle_l1_hc: SynapticBundle
    bundle_in: SynapticBundle
    bundle_col: SynapticBundle
    closure: OccurrenceClosure
    trajectory: Optional[GeneratorTrajectory] = None

    def feed(self, dT_raw: float, dt: float = 0.001) -> None:
        """D_i^sim → 𝒢_i 正式输入端口：喂入原始温度差 dT_raw，驱动三级
        传播一步（L1 → L2 → ensemble → collector）。

        与 `tests/test_basegen_thermal_t0.py` 的 `_propagate_xi_point`
        是同一套传播序列——本方法把它从测试局部函数提升为生产代码，
        使测试与生成元核心本身共用一份实现，不再各自维护一份可能漂移
        的复制品。

        **与 `circuit.step()` 互斥**：`VariantCircuit._step_quantum_thermal_
        pathways`（`circuit/variant_adapter.py:1910`）在每次 `circuit.step()`
        时已经用 world/body 真实采样自动驱动同一批 l1/hc/ensemble/collector
        对象（本句柄只是引用，不是独立副本）。若调用方的 circuit 会持续
        跑 `circuit.step()`，不要再调用本方法注入合成 dT——否则同一 pathway
        每步会被驱动两次（真实 world dT + 合成 dT_raw 叠加），产生不属于
        任何物理过程的伪造信号。`feed()`/`tick()` 只适用于"绕开 world/body
        自主物理、手动喂合成 dT"的标定/测试场景（同 T0~T1 现有方法论），
        与母本主循环二选一使用。
        """
        self.l1.step(dT_raw, dt)

        currents_hc = self.bundle_l1_hc.propagate()
        self.hc.step(currents_hc[0] if currents_hc else 0.0, dt)

        currents_in = self.bundle_in.propagate()
        for k, neuron in enumerate(self.ensemble):
            neuron.step(currents_in[k] if k < len(currents_in) else 0.0, dt)

        currents_col = self.bundle_col.propagate()
        self.collector.step(currents_col[0] if currents_col else 0.0, dt)

    def sense(self) -> float:
        """当前发生检测信号——collector 的 `pre_trace`（既有量，非本模块
        新增，见 `components/neuron.py` 的 pre_trace 定义）。"""
        return self.collector.pre_trace

    def tick(self, dT_raw: float, dt: float, t_step: int) -> Optional[Occurrence]:
        """feed() + 闭合状态机推进一步 + (若挂载) 轨迹记录一步。返回本步
        若完成的 `Occurrence`（否则 None）。`t_step` 由调用方传入（生成元
        本身不维护全局时钟，避免与调用方的仿真主循环步数产生第二套计数源，
        同时也是 `trajectory` 记录与 `Occurrence` 边界共用的同一计数源）。
        """
        self.feed(dT_raw, dt)
        if self.trajectory is not None:
            self.trajectory.record(
                step_index=t_step,
                u_i=dT_raw,
                ensemble_values=tuple(n.pre_trace for n in self.ensemble),
                collector_value=self.collector.pre_trace,
            )
        return self.closure.update(self.sense(), t_step)


def wrap_base_generator(
    circuit, site_index: int, registry: AddressRegistry, *,
    polarity: str = "warm",
    theta_up: Optional[float] = None,
    theta_down: Optional[float] = None,
    record_trajectory: bool = False,
) -> BaseGenerator:
    """从已构造的 `VariantCircuit` 实例抽取生成元核心句柄（wrap，不重建）。

    `site_index` 必须对应一个 `_init_quantum_thermal_pathways` 已构造的
    Fibonacci-sphere 采样点（当前为 0..31，母本对全部 32 点无差别建通路）。
    本函数本身不限制 `site_index` 必须来自冻结选点集合——它是比
    `relations/site_selection.py` 低一层的通用抽取工具；生产/测试代码若
    要遵守"只读冻结集合，不动态搜索"的项目纪律，应从
    `relations.site_selection.get_frozen_site`/`FROZEN_THERMAL_SITES`
    取得 `site_index` 后再传入本函数，而不是自行遍历 0..31。

    地址自动挂载：内部先用 `registry.register_physical(DOMAIN_SKIN_PATCH,
    pid)` 注册（或幂等复用）皮肤支撑地址作为父地址，再调用
    `register_occ_thermal` 生成 `GeneratedAddress`。重复以相同
    `(site_index, polarity)` 调用本函数，两次注册均幂等——但会返回两个
    **不同**的 `BaseGenerator`/`OccurrenceClosure` 对象（因为句柄本身不
    做缓存/单例化；调用方若要多次驱动同一生成元，应自己保存第一次返回
    的句柄，不要重复 wrap）。

    `theta_up`/`theta_down` 为 None 时使用 `OccurrenceClosure` 的默认占位
    值（见 `occurrence.py` 模块 docstring Q3）。

    `record_trajectory=True` 时自动构造并挂载一个空的 `GeneratorTrajectory`
    （见 `generators/trajectory.py`），此后每次 `tick()` 自动记录一步。默认
    `False`，不挂载任何轨迹记录器——保持与本参数引入前的行为完全一致
    （已有调用点/测试不受影响）。
    """
    if polarity not in ("warm", "cool"):
        raise ValueError(f"wrap_base_generator: polarity must be 'warm' or 'cool', got {polarity!r}")

    pid = f"thermpt{site_index}"
    label = f"{pid}_{polarity}"

    l1_dict = circuit.thermal_quantum_l1_warm if polarity == "warm" else circuit.thermal_quantum_l1_cool
    hc_dict = circuit.thermal_quantum_hc_warm if polarity == "warm" else circuit.thermal_quantum_hc_cool

    if pid not in l1_dict:
        raise KeyError(
            f"wrap_base_generator: site_index={site_index} (pid={pid!r}) not found in "
            f"circuit.thermal_quantum_l1_{polarity} — is this a valid index actually "
            f"constructed by _init_quantum_thermal_pathways (currently 0..31)?")
    if label not in circuit.thermal_quantum_ensembles:
        raise KeyError(f"wrap_base_generator: label {label!r} not found in circuit.thermal_quantum_ensembles")

    l1 = l1_dict[pid]
    hc = hc_dict[pid]
    ensemble = circuit.thermal_quantum_ensembles[label]
    collector = circuit.thermal_quantum_collectors[label]

    # 与 _propagate_xi_point / _bundles_for 相同的扁平索引约定：
    # 站点循环 i 在先，极性 warm/cool 在后，故 idx = i*2 + (0 if warm else 1)。
    idx = site_index * 2 + (0 if polarity == "warm" else 1)
    bundle_l1_hc = circuit.bundles_thermal_quantum_l1_to_hc[idx]
    bundle_in = circuit.bundles_thermal_quantum_in[idx]
    bundle_col = circuit.bundles_thermal_quantum_collect[idx]

    parent_addr = registry.register_physical(DOMAIN_SKIN_PATCH, pid)
    address = register_occ_thermal(registry, label, parent_addr)

    closure_kwargs = {"address": address}
    if theta_up is not None:
        closure_kwargs["theta_up"] = theta_up
    if theta_down is not None:
        closure_kwargs["theta_down"] = theta_down
    closure = OccurrenceClosure(**closure_kwargs)
    trajectory = GeneratorTrajectory() if record_trajectory else None

    return BaseGenerator(
        site_index=site_index, polarity=polarity, address=address,
        l1=l1, hc=hc, ensemble=ensemble, collector=collector,
        bundle_l1_hc=bundle_l1_hc, bundle_in=bundle_in, bundle_col=bundle_col,
        closure=closure, trajectory=trajectory,
    )
