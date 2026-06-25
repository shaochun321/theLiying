# Morphosphere 阶段性全量审计报告

**日期**: 2026-05-17  
**版本**: v40.10c (post taxis-reflex fix)

---

## 1. 全链路测试结果

| # | 测试项 | 结果 | 关键数据 |
|---|---|---|---|
| 1 | PracticeEngine 300 ticks | ✅ | obs=(-3.01, 3.93, 2.10) |
| 2 | 量源效应验证 | ✅ | diff=**4.834** (有源 vs 无源) |
| 3 | 物理系统 | ✅ | N=30, KE=10.55, PE=0.55 |
| 4 | 偏好测试 N=20 | ✅ | aco>the>lum, closest={lum:13, the:7} |
| 5 | 梯度场分析 | ✅ | 见下表 |
| 6 | 感官字典完整性 | ✅ | 36 keys |
| 7 | 模块导入 | ⚠️ | HebbianCircuit ✅, ParticleSystem3D 名称不匹配 |

### 梯度场衰减验证

| L | Acoustic (n=1) |G| | Thermal (n=2) |G| | Luminous (n=2) |G| |
|---|---|---|---|
| 3 | 0.556 | 0.222 | 0.296 |
| 5 | 0.200 | 0.048 | 0.064 |
| 7 | 0.102 | 0.017 | 0.023 |
| 10 | 0.050 | 0.006 | 0.008 |

> n=1 的梯度在远距离仍然显著 (L=10 时 0.050), 而 n=2 已接近零 (0.006-0.008)。
> 这是偏好排序的物理基础。

### 感官字典 (36 channels)

```
autocorrelation_H  delta_ke          dlever_{aco,the,lum}
energy_H           fano_H            gradient_H
gradient_{aco,the,lum}                integ_{aco,the,lum}
lever_{aco,the,lum}                   motor_{magnitude,x,y,z}
origin_{confidence,crystallizable,x,y,z}
received_{aco,the,lum}                sparseness_H
spectral_H         synchrony_H       work_done
work_grad_{aco,the,lum}
```

---

## 2. 项目架构清单

### 核心引擎 (3 个活跃文件)

| 文件 | 大小 | 职责 |
|---|---|---|
| [practice_engine.py](file:///D:/cell-cc/Morphosphere_v37_0_native_runtime_prototype_flat_complete/morphosphere_v2pp/engines/practice_engine.py) | 37KB | 感知运动闭环 (QuantitySource + IntegratorColumn + Taxis + Origin) |
| [physics_particle_system.py](file:///D:/cell-cc/Morphosphere_v37_0_native_runtime_prototype_flat_complete/morphosphere_v2pp/engines/physics_particle_system.py) | 21KB | 3D 弹簧-斥力粒子系统 + LIF 神经动力学 |
| [hebbian_circuit.py](file:///D:/cell-cc/Morphosphere_v37_0_native_runtime_prototype_flat_complete/morphosphere_v2pp/engines/hebbian_circuit.py) | 118KB | Hebbian 超图电路 (STDP, 层, 突触, 结晶) |

### 主运行器

| 文件 | 大小 | 职责 |
|---|---|---|
| [run_v40_integrated.py](file:///D:/cell-cc/Morphosphere_v37_0_native_runtime_prototype_flat_complete/morphosphere_v2pp/runners/run_v40_integrated.py) | 96KB | 全管线集成 (信号熵 + STDP + R-chain) |

### 论文产出

| 文件 | 状态 |
|---|---|
| [morphosphere_preference_emergence.tex](file:///D:/cell-cc/paper/morphosphere_preference_emergence.tex) | ✅ 论文1: 因果证据 (拉丁方 6/6) |
| [paper2_decay_exponent_response.tex](file:///D:/cell-cc/paper/paper2_decay_exponent_response.tex) | ✅ 论文2: DERC 定量曲线 |
| [references.bib](file:///D:/cell-cc/paper/references.bib) | ✅ 共用引用 |
| figures/ (7 files) | ✅ 4 PDF (论文1) + 2 PDF (论文2) + 3 SVG (历史) |

---

## 3. 代码健康度

### ✅ 工作正常

| 组件 | 验证方式 |
|---|---|
| 粒子物理 (弹簧 + 斥力 + 阻尼 + 边界反射) | N=30, 100 ticks 无崩溃 |
| 量源 (1/r, 1/r²) + 梯度计算 | 数值精确, 4 距离验证 |
| Taxis 反射 (approach/avoid) | diff=4.83 (有源 vs 无源) |
| 积分器 (leaky + log compression) | 状态非零, 三通道独立 |
| CPG + Babbling | 运动持续, 非停滞 |
| Origin Tracker | 运行 300 ticks, confidence=0.11 |
| 偏好排序 | N=20: aco > the > lum, 与理论一致 |
| 拉丁方因果 | 6/6 条件确认 n 是唯一因果变量 |
| DERC 曲线 | 9 个 n 值, 小 n 区精度 ≤3% |

### ⚠️ 需要注意

| 问题 | 严重性 | 说明 |
|---|---|---|
| ParticleSystem3D 导入名不匹配 | 低 | 类名是 `ParticleSystem3D` 非 `ParticleSystem` |
| Origin 不结晶 | 中 | 300 ticks 后 confidence=0.11, 远低于阈值 0.5 |
| run_v40_integrated 未单独验证 | 中 | 96KB 的主运行器本轮未端到端执行 |
| 论文数据来自 N=20 seeds | 低 | 足够显著但可扩展到 N=50+ |

### ❌ 已修复的关键 Bug

| Bug | 发现日期 | 修复方式 |
|---|---|---|
| **量源不影响物理轨迹** | 2026-05-17 | 在 `compute_reflex` 添加 taxis 反射 |
| SVG 不能被 LaTeX 编译 | 2026-05-17 | 改用 matplotlib 生成 PDF |
| berg1993random 缺少 journal | 2026-05-17 | `@article` → `@book` |
| float specifier 'h' 太严格 | 2026-05-17 | 改为 `[htbp]` |

---

## 4. 公式验证状态

| # | 公式 | 验证状态 | 精度 |
|---|---|---|---|
| 1 | $\Phi_c = A/r^n$ | ✅ 数值精确 | 精确 |
| 2 | $\nabla\Phi = nA\hat{L}/L^{n+1}$ | ✅ 数值精确 | 精确 |
| 3 | $I(t+1) = (1-\lambda)I + \gamma\cdot\text{sgn}(u)\cdot\ln(1+|u|)$ | ✅ | 能量守恒 residual=0 |
| 4 | $L^* = (nA\sqrt{N}/\sigma)^{1/(n+1)}$ | ✅ Zone I | n≤1: ≤3% |
| 5 | $n_1 < n_2 \Rightarrow \mathbb{E}[L_1] > \mathbb{E}[L_2]$ | ✅ 拉丁方 | 6/6 (p<0.002) |
| 6 | DERC 三区结构 | ✅ | 9 个 n 值扫描 |

---

## 5. 识别的缺口

### Gap 1: run_v40_integrated 全链路未测试

完整管线（pipeline + signal entropy + STDP + R-chain）未在本轮运行。
需要验证 `hebbian_circuit` 与 `practice_engine` 的闭环集成。

### Gap 2: Origin 结晶阈值永远达不到

300 ticks 后 confidence=0.11。阈值 0.5 需要 30 个连续 tick > 0.5。
**原因**: babbling 导致运动方向随机变化 → 位移场散度不稳定。
**影响**: `try_crystallize()` 永远不会触发。

### Gap 3: 论文 2 引用缺失

`paper2_decay_exponent_response.tex` 引用了 `references.bib` 中的条目,
但没有自己独特的引用 (如 Langevin 方程、gradient-diffusion balance 相关文献)。

### Gap 4: 实验脚本散落

7 个实验脚本在 `D:\cell-cc\` 根目录下:
- `_debug_sources.py`, `_sensitivity_analysis.py`, `_experiment_symmetric.py`
- `_full_test.py`, `_generate_figures.py`, `_paper2_n_sweep.py`, `_paper2_figures.py`

应该集中到 `paper/scripts/` 或 `experiments/` 目录。

### Gap 5: 59 项降级无源码内联标注

论文声称 59 项降级，但源码中只有少量 `DEGRADED:` 注释。
应统一标注格式。

---

## 6. 项目产出总结

### 学术产出

| 产出 | 内容 |
|---|---|
| **论文 1** | 拉丁方因果证据: n 决定偏好排序 (6/6, p<0.002) |
| **论文 2** | DERC: $L^*(n)$ 连续曲线 + 反弹现象 |
| **公式 6 条** | 场→梯度→积分器→L*→NESS→DERC |
| **降级清单** | 59 项, 按子系统分组 |

### 工程产出

| 产出 | 规模 |
|---|---|
| practice_engine | 862 行, 7 个类 |
| physics_particle_system | 604 行 |
| hebbian_circuit | 2700+ 行 |
| 实验脚本 | 7 个, 共 ~30KB |
| PDF 图表 | 6 个 |

### 验证链

```
代码 → 公式 → 实验 → 统计检验 → 论文
  ↑         ↓
  └── Bug 修复 (taxis reflex) ←── 降级审计发现
```

---

## 7. 建议下一步

| 优先级 | 动作 | 理由 |
|---|---|---|
| **P0** | 整理实验脚本到 `experiments/` | 项目卫生 |
| **P0** | 论文 2 补充引用 | 学术完整性 |
| **P1** | 降低 Origin 结晶阈值或延长运行 | 让 `try_crystallize` 工作 |
| **P1** | 跑一次 run_v40_integrated 端到端 | 验证完整管线 |
| **P2** | 论文 1 扩展 N=50 seeds | 增强统计力 |
| **P2** | 论文 2 补充更多 n 值 (如 n=0.3, 0.4) | 精化 Zone I 边界 |
| **P3** | 添加传播延迟 (retardation) 作为降级回升 | 第一个 Tier-1 升级 |
