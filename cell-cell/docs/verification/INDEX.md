# 验证体系索引 — nexus_v1

> 本目录存放**可重复**的验证测试结果和分析报告。

---

## 自动化回归测试

### 测试套件

- **文件**: [test_regression.py](../../tests/test_regression.py)
- **测试数**: 21
- **运行时间**: ~30s (10k steps)
- **触发**: 每次代码修改后

### 测试清单 (v1.7.2)

| ID | 名称 | 阈值 | 物理意义 |
|---|---|---|---|
| T0.1 | Circuit builds | no crash | 构建健全性 |
| T0.2 | 10k steps complete | no crash | 运行健全性 |
| T1.1 | Noether violations | == 0 | 能量守恒 |
| T1.2 | Energy balance | < 0.01 | 能量审计精度 |
| T1.3 | Landauer bound | True | 信息热力学一致性 |
| T2.1 | Active encoding > 0.3 | > 0.3 | 输入信号传导 |
| T2.2 | Quiet encoding < 0.5 | < 0.5 | 无输入时抑制 |
| T2.3 | Encoding selectivity | > 1.5× | 信号/噪声分离 |
| T3.1 | Vest column active | > 0.3 | 柱状结构响应 |
| T3.2 | Thermal < vestibular | therm < vest | 模态分化 |
| T4.1 | Axis/cross ratio | > 2.0× | 运动拓扑特异性 |
| T4.2 | Cross weight ceiling | < 0.20 | 防止轴间追赶 |
| T4.3 | Motor differentiation | > 0.001 | 运动神经元分化 |
| T5.1 | Xin peak freq | 0.5Hz ± 0.2 | 预测误差周期性 |
| T5.2 | Xin input power | > 10% | 输入频率主导 |
| T6.1 | Sprouted < 20 at 10k | < 20 | 发芽速率控制 |
| T7.1 | Kinetic energy > 0 | > 0 | 身体在运动 |
| T7.2 | Polarization [0.3,1.0] | [0.3, 1.0] | 运动方向性 |
| T8.1 | H_struct > 0 | > 0 | 结构熵存在 |
| T8.2 | H_flow > 0 | > 0 | 流熵存在 |
| T9.1 | Fan-in ratio < 2.0 | < 2.0× | Xin 跨轴公平性 |

---

## 系统级验证 (手动)

### E1: 扩容自检

- **方法**: 每 10k 步比较 N 变化前后的 system mean Xin
- **阈值**: ratio < 1.05 (扩容不恶化)
- **最新结果**: 7/7 OK (80k, v1.7.2)

### P2.1: 热力学容量上限

- **方法**: 80k/500k 运行, 观察 N_bundles 和 EnergyStore 演化
- **预期**: N 自然减速, ES 不枯竭到 0
- **最新结果**: 80k N=37→61, ES fill 50%→21%, 减速 1.5×

---

## 长程验证数据

| 版本 | 步数 | 文件 | 关键结论 |
|---|---|---|---|
| v1.5 | 500k | [regression_500k_v1.5.json](../regression_500k_v1.5.json) | Xin 周期性确认 |
| v1.6 | 500k | [regression_500k_v1.6.json](../regression_500k_v1.6.json) | P_ν × H_flow 准守恒 (后证伪) |
| v1.7 | 500k | [regression_500k_v1.7.json](../regression_500k_v1.7.json) | cross/axis 修复验证 |
| v1.7.2 | 500k | *(运行中)* | P2.1 热力学天花板 |

---

## 验证报告

- [V001_regression_baseline.md](V001_regression_baseline.md) — 回归测试基线 (v1.7.2)
- [V002_P2.1_thermodynamic_ceiling.md](V002_P2.1_thermodynamic_ceiling.md) — P2.1 能量墙验证
