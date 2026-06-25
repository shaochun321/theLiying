# Phase 1-4 完成报告: Morphosphere 物理回升

## 系统架构

```
外部信号源 (QuantitySource)
  ↓ inject(A·mod/spacing^(n-1))     ← Phase 1: n 编码辐射模式
介质晶格 (MediumLattice3D)           ← Phase 1: 432 粒子
  ├─ acoustic: ∂²p/∂t² = c²∇²p − γ∂p/∂t  (波动)
  └─ thermal:  ∂E/∂t = κ∇²E − λE          (扩散)
  ↓ T(Z_body, Z_medium) 阻抗匹配
身体 (ParticleSystem3D, 30 粒子)
  ├─ 弹簧-排斥物理 (Velocity Verlet)
  ├─ HH 离子通道                     ← Phase 2: Na⁺/K⁺ 门控
  │   ├─ g_Na·m³h·(V−E_Na)
  │   ├─ g_K·n⁴·(V−E_K)
  │   └─ g_L·(V−E_L)
  ├─ 前庭系统                        ← Phase 3: 6 轴 IMU
  │   ├─ 3 Semicircular Canals (ω)
  │   └─ 3 Otolith Organs (a+g)
  └─ 本体感觉                        ← Phase 4: 关节/肌肉/腱
      ├─ Spindle Ia (dθ/dt)
      ├─ Spindle II (θ−θ_rest)
      └─ Golgi (|F_spring|)
  ↓ 59 sensory channels
PracticeEngine → HebbianCircuit → Motor
```

## 新增文件

| 文件 | 内容 | Phase |
|---|---|---|
| [medium_system.py](file:///D:/cell-cc/Morphosphere_v37_0_native_runtime_prototype_flat_complete/morphosphere_v2pp/engines/medium_system.py) | 3D 晶格介质 | 1 |
| [hodgkin_huxley.py](file:///D:/cell-cc/Morphosphere_v37_0_native_runtime_prototype_flat_complete/morphosphere_v2pp/engines/hodgkin_huxley.py) | HH 离子通道 | 2 |
| [vestibular_system.py](file:///D:/cell-cc/Morphosphere_v37_0_native_runtime_prototype_flat_complete/morphosphere_v2pp/engines/vestibular_system.py) | 6 轴前庭 | 3 |
| [proprioceptive_system.py](file:///D:/cell-cc/Morphosphere_v37_0_native_runtime_prototype_flat_complete/morphosphere_v2pp/engines/proprioceptive_system.py) | 本体感觉 | 4 |
| [paper3_medium_physics.tex](file:///D:/cell-cc/paper/paper3_medium_physics.tex) | 论文 3 | 1 |

## 感知通道演化

| 版本 | 通道数 | 新增 |
|---|---|---|
| Phase 0 (LIF only) | 36 | — |
| + Medium3D | 36 | (替换，不增加) |
| + Vestibular | 48 | +12 (canal×3 + otolith×3 + derived×6) |
| + Proprioception | **59** | +11 (spindle×4 + golgi×2 + joint×4 + energy) |

## 降级回升状态

```
Phase 0:  29 DEGRADED,  2 RECOVERED
Phase 1:  +0 DEGRADED,  +1 RECOVERED  (medium propagation)
Phase 2:  +3 DEGRADED,  +1 RECOVERED  (LIF → HH)
Phase 3:  +3 DEGRADED,  +1 RECOVERED  (scalar → 6-axis IMU)
Phase 4:  +3 DEGRADED,  +1 RECOVERED  (no proprio → spindle/Golgi)
──────────────────────────────────────────────────
总计:      38 DEGRADED,  6 RECOVERED
```

## 科学发现

### Phase 1: DERC 阶梯效应
- n≤1 时 E[L] 恒定 (介质注入饱和)
- 反弹消失 (介质对称传播消除梯度陷阱)
- thermal L_pen=0.71 自动涌现 (近场热觉)

### Phase 2: HH 动态范围
- AP amplitude: 90.5 mV (LIF 只有 15 mV)
- 阈值 I=7 μA/cm² (与经典文献一致)
- f-I 曲线: Class II (全有或全无)

### Phase 3: 角速度感知
- Canal 正确追踪旋转 (overdamped τ=5s)
- Canal 适应: 持续旋转后信号衰减
- Otolith 追踪加速+重力 (不可分离, Einstein 等效)

### Phase 4: 体姿感知
- 148 个关节角度 (从 30 粒子的弹簧网络)
- Spindle Ia 追踪角速度 (运动中 0.16, 静止时 0.04)
- Golgi 追踪弹簧力 (运动中 0.51, 静止时 0.17)
- 6% 关节在极限范围 (身体有变形)

## 性能

| 指标 | 值 |
|---|---|
| Tick 时间 | 59.4 ms |
| 瓶颈 | HH sub-stepping (4×30粒子) |
| 偏好排序 | 保持 (acoustic > thermal > luminous) |
