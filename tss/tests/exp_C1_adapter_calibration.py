"""tss.tests.exp_C1_adapter_calibration — EXP-C1-01：适配器电容单点响应反解。

TYPE:INFRA（标定实验，只测不判资格）

方法：TSS-R1 审计方案明令的**单点响应曲线反解**，禁网格搜索。

  1. 探测：capacitance=C_probe 下馈入单步 r=r_probe，实测 collector 膜
     电压增量 ΔV → 比例系数 k = ΔV·C_probe/r_probe（ΔV = k·r/C 线性区）。
  2. 反解：C = k·r_min/(margin·v_peak)，r_min=0.0026（EXP-C0-02 实测下界，
     coupling_contract.MEASURED_R_AMPLITUDE_RANGE），margin=2（最小幅度
     2× 裕量必越阈）。
  3. 验证（同一脚本内，非独立资格测试）：
     a. 全实测幅度域 {r_min, 0.05, 0.17, r_max} 单步脉冲 → 同步 spike
     b. 500 步零输入 → 零 spike（负例是精确零，无噪声地板）
     c. 两枚脉冲间隔 1204 步（E^↑ 最小间隔）→ 两次 spike（可重复触发）

输出：冻结常量 _COLLECTOR_CAPACITANCE 的推导值，回填
relation_event_adapter.py 并以本脚本名作 EXP 标签。
"""
import sys
sys.path.insert(0, '.')

from nexus_v1.components.structural_address import (
    AddressRegistry, DOMAIN_SKIN_PATCH, DOMAIN_OCC_THERMAL,
)
from tss.relations.coupling_contract import MEASURED_R_AMPLITUDE_RANGE
from tss.relations.relation_event_adapter import (
    RelationEventAdapter, _COLLECTOR_V_PEAK, _COLLECTOR_CAPACITANCE,
)

DT = 0.001
MARGIN = 2.0
R_MIN, R_MAX = MEASURED_R_AMPLITUDE_RANGE


def _make_parent_addrs(registry):
    p1 = registry.register_physical(DOMAIN_SKIN_PATCH, "thermpt28")
    p2 = registry.register_physical(DOMAIN_SKIN_PATCH, "thermpt21")
    a1 = registry.register_generated(DOMAIN_OCC_THERMAL, "thermpt28_warm", (p1,), 1)
    a2 = registry.register_generated(DOMAIN_OCC_THERMAL, "thermpt21_warm", (p2,), 1)
    return a1, a2


def _fresh_adapter(capacitance, label="cal"):
    registry = AddressRegistry()
    a1, a2 = _make_parent_addrs(registry)
    return RelationEventAdapter(registry, a1, a2, label, capacitance=capacitance)


def run():
    print("=" * 68)
    print("EXP-C1-01：适配器电容单点响应反解")
    print(f"实测 r 幅度域 [{R_MIN}, {R_MAX}]（EXP-C0-02），margin={MARGIN}")
    print("=" * 68)

    # ── 1. 单点响应探测 ──
    c_probe, r_probe = 1.0, 1.0
    ad = _fresh_adapter(c_probe, "probe")
    v0 = ad.collector._membrane.voltage
    ad.step(r_probe, DT)
    dv = ad.collector._membrane.voltage - v0
    k = dv * c_probe / r_probe
    print(f"探测：C_probe={c_probe}, r_probe={r_probe} → ΔV={dv:.6e} → "
          f"k=ΔV·C/r={k:.6e}")

    # ── 2. 反解 ──
    c_derived = k * R_MIN / (MARGIN * _COLLECTOR_V_PEAK)
    print(f"反解：C = k·r_min/(margin·v_peak) = {k:.4e}·{R_MIN}/"
          f"({MARGIN}·{_COLLECTOR_V_PEAK}) = {c_derived:.6e}")
    print(f"（relation_event_adapter.py 当前冻结值 {_COLLECTOR_CAPACITANCE:.6e}，"
          f"偏差 {abs(c_derived - _COLLECTOR_CAPACITANCE) / c_derived * 100:.1f}%）")

    # ── 3a. 全幅度域单脉冲验证 ──
    ok = True
    for r in (R_MIN, 0.05, 0.17, R_MAX):
        ad = _fresh_adapter(c_derived, f"amp{r}")
        spike = ad.step(r, DT)
        mark = "✓" if spike > 0.5 else "✗"
        if spike <= 0.5:
            ok = False
        print(f"  {mark} r={r:<8} → spike={spike}")

    # ── 3b. 零输入验证 ──
    ad = _fresh_adapter(c_derived, "zero")
    n_spikes = sum(1 for _ in range(500) if ad.step(0.0, DT) > 0.5)
    mark = "✓" if n_spikes == 0 else "✗"
    if n_spikes:
        ok = False
    print(f"  {mark} 500 步零输入 → {n_spikes} spikes")

    # ── 3c. 可重复触发验证（间隔=E^↑ 最小间隔 1204 步）──
    ad = _fresh_adapter(c_derived, "retrig")
    count = 0
    for t in range(1300):
        r = R_MIN if t in (0, 1204) else 0.0
        count += int(ad.step(r, DT) > 0.5)
    mark = "✓" if count == 2 else "✗"
    if count != 2:
        ok = False
    print(f"  {mark} 两枚 r_min 脉冲间隔 1204 步 → {count} spikes（期望 2）")

    print("=" * 68)
    if ok:
        print(f"EXP-C1-01 PASS：冻结 _COLLECTOR_CAPACITANCE = {c_derived:.6e}")
        return 0
    print("EXP-C1-01 FAIL：反解值未通过验证，检查响应线性假设")
    return 1


if __name__ == "__main__":
    sys.exit(run())
