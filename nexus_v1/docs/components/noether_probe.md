# NoetherProbe — 守恒定律审计探针

## 物理对应

- **BIO**: —
- **EE**: 守恒定律验证器 (Noether 定理的工程实现)

## 文件

[noether_probe.py](../../circuit/noether_probe.py)

## 功能

每步检查四条守恒律:

| 守恒律 | 公式 | 容差 |
|---|---|---|
| 能量守恒 | E_in = E_out + E_stored + E_leak | < 0.01 |
| 电荷 KCL | ΣI_in = ΣI_out (每个 Capacitor) | < 1e-6 |
| Landauer | Q_dissipated / bits_erased ≥ kT ln2 | True |
| 权重稳定 | \|mean(dw)\| < drift_threshold | < 0.01/step |

## 回归测试

- T1.1: Noether violations == 0
- T1.2: Energy balance < 0.01
- T1.3: Landauer bound = True

## 历史

500k 步持续 0 violations (v1.5.0 → v1.7.2)
