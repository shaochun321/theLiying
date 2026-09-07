"""tss.tests.test_e0_kernel_ledger — E0 修复：ℒ/K 承载测试(T-KL-1~4)。

TYPE:INFRA

修复依据：event_core_contract.py E-1 审计（ℒ GAP / K 无持久存储）+
用户裁定 2026-09-07（R-E0-1 = 契约代码 + JSON 快照）。
被测模块：tss/events/kernel_ledger.py。

测试映射：
  T-KL-1  census 完整性：双适配器 c_ro 栈 → 4 神经元/2 束/3 电容
          （比较器无电容如实为空）；重复传入 fail-fast
  T-KL-2  只读性（最强形式）：同一合成 r 轨迹驱动两个全新同参栈，
          一侧挂 probe 逐步 record——fires/下游电压/全部电容电荷/
          束权重 bit-exact 相同（观察者零反作用）
  T-KL-3  能量合理性：轨迹无 NaN、储能非负、泄漏耗散>0（门电容
          脉冲后经 r_leak 恢复必然耗散）、账目字段齐全含诚实边界声明
  T-KL-4  快照往返：snapshot→JSON→load 深等；适配器冻结参数与
          relation_event_adapter 模块常量逐项一致；地址谱系在录

驱动方式：合成 r 脉冲（同 test_c1_coupling._run_synthetic 惯例），
无真实母体电路——纯组件层，fast。
"""
import sys
sys.path.insert(0, '.')

import json
import math
import os
import tempfile

import pytest

from tss.relations.relation_event_adapter import (
    _COLLECTOR_CAPACITANCE, _ADAPTER_PHYSICAL_SEED, _TRANSDUCER_WEIGHT,
)
from tss.tests.test_c1_coupling import DT, _PairStack, _make_l1_address
from tss.tests.test_e0_event_type_audit import _PAIR, _fresh_pair_assembly
from tss.events.kernel_ledger import (
    KernelCensus, KernelEnergyProbe,
    snapshot_kernel, write_snapshot, load_snapshot,
)

# 合成 r 轨迹：x 在 100 步、y 在 160 步各一枚脉冲（Δt₂=60 ⊂ 合格窗）
_N = 900
_R_AMP = 0.17          # test_c1 合成惯例值（实测幅度域内）
_PULSE = {_PAIR[0]: 100, _PAIR[1]: 160}


def _census_of(adapters, stack) -> KernelCensus:
    return KernelCensus(
        adapters=[adapters[x] for x in _PAIR],
        gates=[stack.gate2_x, stack.gate2_y],
        kernels=[stack.kernel2_x],
        comparators=[stack.comp2])


def _drive(with_probe: bool):
    """合成驱动一个全新栈；可选逐步挂 probe。返回可比对的完整终态。"""
    adapters, stack = _fresh_pair_assembly()
    census = _census_of(adapters, stack)
    probe = KernelEnergyProbe() if with_probe else None
    for t in range(_N):
        for x in _PAIR:
            r = _R_AMP if t == _PULSE[x] else 0.0
            adapters[x].step(r, DT)
        stack.step(t, DT)
        if probe is not None:
            probe.record(census, DT)
    state = {
        "fires": list(stack.fire_steps),
        "downstream_v": stack.downstream.voltage,
        "cap_charges": [cap.charge for _l, cap, _r in census.capacitors()],
        "weights": [ad.bundle.weight_matrix() for ad in census.adapters],
    }
    return state, census, probe


def test_kl_1_census_completeness():
    """T-KL-1：标准 c_ro 栈的 census 计数 + 重复传入 fail-fast。"""
    adapters, stack = _fresh_pair_assembly()
    census = _census_of(adapters, stack)
    assert len(census.neurons()) == 4, "T-KL-1: 2 适配器应贡献 4 神经元"
    assert len(census.bundles()) == 2
    caps = census.capacitors()
    assert len(caps) == 3, "T-KL-1: 2 门电容 + 1 核电容（比较器无电容）"
    assert all(r_leak is not None and r_leak > 0 for _l, _c, r_leak in caps), (
        "T-KL-1: 门/核电容均有泄漏路径")
    assert len(census.clamp_heats()) == 2
    # 神经元无重复对象
    ids = list(map(id, census.neurons()))
    assert len(set(ids)) == len(ids)
    with pytest.raises(ValueError):
        KernelCensus(adapters=[adapters[_PAIR[0]], adapters[_PAIR[0]]])
    print("[PASS] T-KL-1 census 完整性")


def test_kl_2_probe_is_read_only():
    """T-KL-2：挂 probe 与不挂 probe 的终态 bit-exact 相同。"""
    state_plain, _, _ = _drive(with_probe=False)
    state_probed, _, probe = _drive(with_probe=True)
    assert probe.total_steps == _N
    assert state_probed == state_plain, (
        "T-KL-2: 观察者改变了被观察系统——只读性被破坏\n"
        f"plain={state_plain}\nprobed={state_probed}")
    assert state_plain["fires"], (
        "T-KL-2 前提：合成正例应产生 c_ro（Δt₂=60 在合格窗内）")
    print(f"[PASS] T-KL-2 只读性 bit-exact（fires={state_plain['fires']}）")


def test_kl_3_energy_sanity():
    """T-KL-3：无 NaN / 储能非负 / 泄漏耗散>0 / 账目齐全。"""
    _state, census, probe = _drive(with_probe=True)
    assert not probe.has_nan(), "T-KL-3: 能量轨迹出现 NaN"
    assert all(e >= 0.0 for e in probe.cap_energy_trace), (
        "T-KL-3: 电容储能出现负值（Q²/2C 不可能为负——采样逻辑错误）")
    assert probe.total_leak_dissipation > 0.0, (
        "T-KL-3: 门电容脉冲后经 r_leak 恢复，泄漏耗散必须为正")
    assert probe.total_neuron_heat >= 0.0
    report = probe.summary(census)
    for key in ("total_steps", "total_neuron_heat", "total_leak_dissipation",
                "final_cap_energy", "not_modeled", "clamp_heat"):
        assert key in report, f"T-KL-3: 账目缺字段 {key}"
    assert "MOSFET" in report["not_modeled"], (
        "T-KL-3: 诚实边界声明（MOSFET 耗散未建模）必须随账目输出")
    print(f"[PASS] T-KL-3 能量合理性（leak={probe.total_leak_dissipation:.3e} "
          f"heat={probe.total_neuron_heat:.3e}）")


def test_kl_4_snapshot_roundtrip():
    """T-KL-4：快照→JSON→load 深等；冻结参数与模块常量逐项一致。"""
    adapters, stack = _fresh_pair_assembly()
    census = _census_of(adapters, stack)
    snap = snapshot_kernel(census, stamp="T-KL-4")

    with tempfile.TemporaryDirectory() as td:
        path = os.path.join(td, "snap", "c_ro_test.json")
        write_snapshot(snap, path)
        loaded = load_snapshot(path)
    assert loaded == json.loads(json.dumps(snap)), "T-KL-4: 往返不等"

    roles = [c["role"] for c in snap["components"]]
    assert roles.count("relation_event_adapter") == 2
    assert roles.count("entry_gate") == 2
    assert roles.count("history_kernel") == 1
    assert roles.count("theta_comparator") == 1
    for comp in snap["components"]:
        if comp["role"] == "relation_event_adapter":
            b = comp["bundle"]
            assert b["physical_seed"] == _ADAPTER_PHYSICAL_SEED
            assert b["initial_weight"] == b["weight_max"] == _TRANSDUCER_WEIGHT
            assert b["learning_rule"] == "frozen"
            assert comp["collector_capacitance"] == _COLLECTOR_CAPACITANCE
            assert comp["address"]["generation_depth"] == 2
            assert len(comp["address"]["parents"]) == 2
    assert snap["note"].startswith("record-only"), (
        "T-KL-4: 快照必须声明 record-only（禁止状态写回）")
    print("[PASS] T-KL-4 快照往返 + 冻结参数核对")


def main():
    test_kl_1_census_completeness()
    test_kl_2_probe_is_read_only()
    test_kl_3_energy_sanity()
    test_kl_4_snapshot_roundtrip()
    print()
    print("=" * 60)
    print("T-KL-1~4 ALL PASS — ℒ 账本 + K/𝒞 快照承载交付")
    print("=" * 60)


if __name__ == "__main__":
    main()
