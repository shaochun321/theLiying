"""tss.tests.test_version_pairing — TSS ↔ nexus_v1 版本配对 fail-fast。

TYPE:INFRA

背景（外部评判《TSS (3) 全量实测后的最终修改清单》§6，2026-09-08）：
tss (3) 包依赖 `VariantCircuit._step_serial`（DEG-021 母体最小标记），但
外部复现者拿旧母体运行时，直到 T-DD-2 才以晦涩的 FAIL 暴露版本不匹配。
本测试把配对约束前置为显式 fail-fast：母体缺 required interface 时在
这里就给出明确诊断，不必跑到 DEG-021 测试。

配对声明（机器可读）：tss/VERSION_PAIRING.json。接口清单变更时两处同步。

T-VP-1  配对声明文件存在、可解析、接口清单非空
T-VP-2  母体 required interface 实测存在：VariantCircuit step 一次后
        `_step_serial == 1`（惰性初始化语义——构造后不存在是合法的）
"""
import sys
sys.path.insert(0, '.')

import json
import os

_PAIRING_PATH = os.path.join(os.path.dirname(__file__), "..", "VERSION_PAIRING.json")


def test_vp_1_pairing_declaration_exists():
    """T-VP-1：VERSION_PAIRING.json 存在且接口清单非空。"""
    assert os.path.exists(_PAIRING_PATH), (
        "T-VP-1: tss/VERSION_PAIRING.json 缺失——TSS 包发布时必须携带"
        "版本配对声明（评判 §6）")
    with open(_PAIRING_PATH, encoding="utf-8") as f:
        pairing = json.load(f)
    assert pairing["requires_nexus_v1_interfaces"], "T-VP-1: 接口清单为空"
    assert pairing["dt"] == 0.001
    names = [it["interface"] for it in pairing["requires_nexus_v1_interfaces"]]
    assert "VariantCircuit._step_serial" in names
    print(f"[PASS] T-VP-1 配对声明在录（{len(names)} 个 required interface）")


def test_vp_2_mother_interface_present():
    """T-VP-2：母体实测具备 _step_serial（step 一次后 ==1）。"""
    from nexus_v1.circuit.variant_adapter import VariantCircuit
    c = VariantCircuit()
    # 惰性初始化：构造后不存在是合法的，只有 step() 后必须出现
    c.step({}, 0.001)
    serial = getattr(c, "_step_serial", None)
    assert serial == 1, (
        "当前 nexus_v1 不具备 required interface: VariantCircuit._step_serial"
        "（DEG-021 母体最小标记缺失，双驱动互锁会退化为文档级约束）。\n"
        "配对声明见 tss/VERSION_PAIRING.json——母体 step() 需含兼容行:\n"
        '    self._step_serial = getattr(self, "_step_serial", 0) + 1\n'
        f"实测: _step_serial={serial!r}")
    c.step({}, 0.001)
    assert c._step_serial == 2, "T-VP-2: _step_serial 未单调递增"
    print("[PASS] T-VP-2 母体 required interface 在位（_step_serial 单调递增）")


def main():
    test_vp_1_pairing_declaration_exists()
    test_vp_2_mother_interface_present()
    print()
    print("=" * 60)
    print("T-VP-1~2 ALL PASS — TSS ↔ nexus_v1 版本配对成立")
    print("=" * 60)


if __name__ == "__main__":
    main()
