# Phase 1: Medium3D — 介质作为物理实体

## 完成内容

### 新增文件

- **[medium_system.py](file:///D:/cell-cc/Morphosphere_v37_0_native_runtime_prototype_flat_complete/morphosphere_v2pp/engines/medium_system.py)**: 3D 晶格介质系统
  - `MediumParticle`: 晶格节点 (固定位置, 标量能量场)
  - `MediumLattice3D`: 晶格系统, 两种传播模式
  - 216 粒子 (spacing=2.0, 6×6×6 晶格)
  - 波动: 二阶标量波方程 `∂²p/∂t² = c²∇²p − γ∂p/∂t` (leapfrog + CFL)
  - 扩散: 一阶扩散方程 `∂E/∂t = κ∇²E − λE`

### 修改文件

- **[practice_engine.py](file:///D:/cell-cc/Morphosphere_v37_0_native_runtime_prototype_flat_complete/morphosphere_v2pp/engines/practice_engine.py)**:
  - `__init__`: 创建 acoustic + thermal 介质晶格
  - `step`: 源注入 → 介质传播 → 从晶格读取梯度/强度
  - luminous 保持解析 (v→∞ 近似)

## 涌现属性

| 属性 | acoustic | thermal | 来源 |
|---|---|---|---|
| **速度** | v = 1.414 unit/tick | v = 0.400 unit/tick | `spacing·√(k/m)` |
| **穿透深度** | L_pen = 28.3 units | L_pen = 0.71 units | `v/γ` or `√(κ/λ)` |
| **阻抗** | Z = 0.707 | Z = 1.000 | `√(k·m)/d²` |

## 关键发现

> **介质物理改变了偏好排序！**
> 
> - 无介质: `acoustic > thermal > luminous` (由 n 决定)
> - 有介质: `thermal > acoustic > luminous` (由 n + 介质属性共同决定)
> 
> thermal 的极短穿透深度 (0.71 units) 使得 thermal 信号几乎无法到达 agent →
> taxis 对 thermal 不响应 → E[L_thermal] 增大。

## 验证结果

| 测试 | 状态 |
|---|---|
| 波动稳定性 | ✅ 不再发散 |
| 热扩散衰减 | ✅ 指数衰减, L_pen=1.41 |
| 梯度方向 | ✅ 指向源 |
| 偏好排序 | ✅ 保持 luminous closest |
| 回归测试 (8项) | ✅ 全通过 |

## 降级状态

```
practice_engine.py:  15 DEGRADED + 2 RECOVERED
physics_particle_system.py:  8 DEGRADED + 1 RECOVERED
medium_system.py:  4 DEGRADED (new)
```
