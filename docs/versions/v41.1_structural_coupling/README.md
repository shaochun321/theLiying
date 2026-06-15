# v41.1 Structural Spacetime Coupling

## 日期
2026-05-18

## 路线
被动门控采样 → 主动双向相位对齐

## 核心理念
信号不应通过人工耦合系数进入电路，而应通过 CPG 振荡器的相位门控（类丘脑门控）结构性地采样外部世界。生物体不是"调参数"来感知世界——它的感知窗口由内在的代谢节律决定。

## 讨论要点
- CPG 半中心振荡器需要对称性破缺才能启动（A=0.08, B=0.02）
- 门控必须是 ON/OFF 而非渐变（完全抑制输者）
- 50% 占空比 = 自然的感觉-运动交替
- 传播延迟 t_ret = r/v 已在 v40 实现

## 实施
- `hebbian_circuit.py`: `_cpg_step()` 对称性破缺 + tonic drive + reciprocal inhibition
- `_phase5_pipeline.py`: `inject_sensory()` 中 `phase_gate` 门控
- `run_v40_integrated.py`: CPG init 对齐

## 测试结果
| 指标 | 值 |
|------|-----|
| Gate duty | 50% |
| STDP weights | 0.97 |
| Intake Q4/Q1 | 4.7× |
| Noether anomaly | 0.008 → 0.0003 |

## 降级变化
- RECOVERED: `CPG_half_center_reciprocal_inhibition` (从简化代理→真正的半中心振荡器)
