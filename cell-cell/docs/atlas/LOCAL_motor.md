# LOCAL: 运动决策与输出 — Motor → Body

> **Version**: v1.7.2 | **Files**: [motor_decision.py](../../circuit/motor_decision.py), [variant_adapter.py](../../circuit/variant_adapter.py)

---

## 完整运动管线

```
Column ×7
  │
  ├─→ col→mot axis bundles (3×1×1)  ← 轴特异
  ├─→ col→mot cross bundle (1×7×3)  ← 跨轴
  └─→ sprouted bundles               ← 动态
  │
  ▼
Motor ×3+ (spiking, xyz)
  │ _activation_ema (continuous rate)
  │
  ├─→ Lateral inhibition (Renshaw cells)  ← 打破 clone 对称
  │     axis_individual[axis] = compete(acts)
  │
  ├─→ Cross-axis inhibition  ← push-pull
  │     strongest axis suppresses weakest
  │
  ▼
MotorDecision.process(axis_acts, motion_state, da, dt)
  │ 当前: passthrough (CPG/Direction/Navigator 全是 stub)
  │
  ▼
motor_acts [3]
  │ × kinetic_damping (速度衰减)
  │
  ▼
MuscleSystem.contract_all(motor_acts)
  │ delay buffer (2 steps)
  │ gain = 0.1
  │
  ▼
forces [3]
  │
  ▼
Body.step(forces, dt)
  │ Newtonian: F=ma, viscous drag
  │ → position, velocity, acceleration
  │
  ▼
World feedback:
  ├─→ body.acceleration × OTOLITH_GAIN=500 → oto_x/y/z (闭环)
  ├─→ thermal_membrane.sense(world, body) → therm/dtherm
  └─→ world.consume_nearby() → EnergyStore.deposit()
```

## A7 运动势

```
K = ½m|v|²                        动能
ν = EMA(dK/dt, α=0.01)            运动势 (100步窗口)
ν_xyz = EMA(m×v_i×a_i, α=0.01)    分轴运动势
P_ν = max(|ν_i|) / Σ|ν_i|          偏振度 [0.33, 1.0]
```

## Motor 反馈回路

```
Motor → feedback Capacitor (τ=0.5s)
     → filtered voltage
     → × feedback_gain (0.05)
     → inject -current into Column (efference copy)
```

## P0 前传模型 (Efference Copy)

```
predicted_acc = motor_acts[i] × efference_gain[axis]
actual_acc = body.acceleration[i]
error = actual - predicted
efference_gain += 0.001 × error  (慢速学习)
efficacy = f(mismatch, motor_acts)  (效力追踪)
```

## 已知限制

- CPG/Direction/Navigator 全是 stub
- Lateral inhibition 只在同轴 clones 间
- Motor mitosis 门控过于宽松
