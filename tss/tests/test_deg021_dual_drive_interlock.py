"""tss.tests.test_deg021_dual_drive_interlock — DEG-021 修复验证(T-DD-1~3)。

TYPE:INFRA

修复依据：degradation_registry DEG-021（feed 与 circuit.step() 双驱动
仅文档约束）；用户授权 2026-09-07：VariantCircuit.step() 加最小单调
`_step_serial` 标记（纯赋值），BaseGenerator.feed() 检查并 fail-fast。

测试映射：
  T-DD-1  纯 feed 驱动：连续 feed 不 raise（合法标定场景不受影响）
  T-DD-2  混用驱动：feed → circuit.step() → feed ⇒ RuntimeError
          （消息指向 DEG-021）
  T-DD-3  warmup 兼容：wrap 前/首次 feed 前的 circuit.step() 合法
          （基线取首次 feed 时的 serial，不产生假阳性）；
          退化兼容：_circuit_ref=None 的旧调用形态不检查
"""
import sys
sys.path.insert(0, '.')

import pytest

from nexus_v1.circuit.variant_adapter import VariantCircuit
from nexus_v1.components.structural_address import AddressRegistry
from tss.generators import wrap_base_generator

DT = 0.001


def _wrap(circuit):
    registry = AddressRegistry()
    return wrap_base_generator(circuit, 28, registry, polarity="warm")


def test_dd_1_pure_feed_ok():
    """T-DD-1：纯 feed 驱动不受互锁影响。"""
    gen = _wrap(VariantCircuit())
    for _ in range(20):
        gen.feed(0.05, DT)
    print("[PASS] T-DD-1 纯 feed 驱动合法")


def test_dd_2_interleaved_drive_raises():
    """T-DD-2：feed 与 circuit.step() 交错 ⇒ fail-fast。"""
    circuit = VariantCircuit()
    gen = _wrap(circuit)
    gen.feed(0.05, DT)              # 认领基线
    circuit.step({}, DT)            # 双驱动：world 路径推进
    with pytest.raises(RuntimeError, match="DEG-021"):
        gen.feed(0.05, DT)
    print("[PASS] T-DD-2 混用驱动 fail-fast（DEG-021 互锁生效）")


def test_dd_3_warmup_and_legacy_compat():
    """T-DD-3：首次 feed 前的 step 合法；旧调用形态不检查。"""
    # warmup：wrap 后、首次 feed 前 step 若干步——基线在首次 feed 取
    circuit = VariantCircuit()
    gen = _wrap(circuit)
    for _ in range(3):
        circuit.step({}, DT)
    gen.feed(0.05, DT)              # 不 raise：warmup 合法
    gen.feed(0.05, DT)              # 之后无 step，继续合法
    # 退化兼容：手工构造 _circuit_ref=None 的句柄（模拟旧调用形态）
    gen2 = _wrap(VariantCircuit())
    gen2._circuit_ref = None
    gen2.feed(0.05, DT)             # 不检查，不 raise
    print("[PASS] T-DD-3 warmup 基线 + 旧形态退化兼容")


def main():
    test_dd_1_pure_feed_ok()
    test_dd_2_interleaved_drive_raises()
    test_dd_3_warmup_and_legacy_compat()
    print()
    print("=" * 60)
    print("T-DD-1~3 ALL PASS — DEG-021 双驱动互锁交付")
    print("=" * 60)


if __name__ == "__main__":
    main()
