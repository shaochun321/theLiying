# RELATIONS — 全局 ↔ 局部关系图

> **Version**: v1.7.2

---

## 子系统依赖矩阵

```
                 Vest  Circuit  Motor  Shadow  Energy  Entropy  MotionSt
Vestibular        -     →→→      ·       ·       ·       ·       ·
Circuit          ←←←     -      →→→     →→      ←←←     ←←      →→
Motor             ·     ←←←      -       ·      ←←       ·      →→→
Shadow            ·      ←←      ·       -       ←       ·       ·
Energy            ·     →→→     →→       →       -       ←       ·
Entropy           ·      →→      ·       ·       →       -       ·
MotionState       ·      ←←     ←←←      ·       ·       ·       -

→→→ 强依赖 (数据流)   →→ 依赖   → 弱依赖   · 无依赖   ← 反向
```

## 数据流 (按 step 时序)

```
Phase 0: Motor→Muscle→Body→World→EnergyStore     [LOCAL_motor, LOCAL_energy]
  │
Phase 1: World→Vestibular→Encoding                [LOCAL_vestibular]
  │
Phase 2: Encoding→Column→Motor                    [LOCAL_circuit]
  │         │
  │         └→ Sprouted bundles                   [LOCAL_circuit §结构生长]
  │
Phase 3: Motor feedback→Column                    [LOCAL_motor §反馈]
  │
Phase 4: Learning (STDP, DA×PNN gated)            [LOCAL_circuit §学习]
  │
Phase 5: Metabolic tax (每100步)                   [LOCAL_energy]
  │         │
  │         └→ EnergyStore.withdraw()             [LOCAL_energy]
  │
Phase 6: Structural growth (每10k步)               [LOCAL_circuit §结构]
  │         │
  │         └→ EnergyStore gate                   [LOCAL_energy]
  │
Phase 7: Shadow observe (每10步)                   [LOCAL_shadow]
  │         │
  │         └→ DA circuit                         [LOCAL_shadow §DA回路]
  │
Phase 8: Entropy audit                            [LOCAL_entropy]
  │         │
  │         ├→ Noether probe                      [LOCAL_entropy §Layer1]
  │         └→ TOPRXin ledger                     [LOCAL_entropy §Layer3]
  │
Phase 9: MotionState update                       [LOCAL_motion_state]
```

## 能量流

```
World heat sources
  │ consume_nearby()
  ▼
EnergyStore  ←──── deposit (cap: 0.05/step)
  │
  ├──→ DA neurons (0.003/step)         [LOCAL_shadow]
  ├──→ Vascular → neurons (~0.0015)    [LOCAL_circuit]
  ├──→ Bundle basal (N×0.0005/100)     [LOCAL_energy]
  ├──→ Basal drain (0.0001/step)       [LOCAL_energy]
  └──→ Sprout events (0.1 one-time)    [LOCAL_circuit]
```

## 信息流

```
外部输入 (oto_x/y/z)
  │ × impedance_match
  ▼
前庭链 → Encoding → Column → Motor → Muscle → Body
  │                   │                        │
  │                   ▼                        ▼
  │              Shadow observe           Body.acceleration
  │                   │                        │
  │                   ▼                   OTOLITH_GAIN
  │              DA circuit                    │
  │                   │                        ▼
  │                   ▼                   oto_x/y/z (闭环)
  │           dopamine.concentration
  │                   │
  │                   ▼
  │              三因子门控
  │                   │
  └──────────────────→↓
                    STDP 学习
```

## 理论↔局部映射

| 理论 | 涵盖局部 | 核心约束 |
|---|---|---|
| T001 Noether | LOCAL_entropy | 能量/电荷/信息守恒 |
| T002 STDP | LOCAL_circuit | 学习规则 |
| T003 Fruit | LOCAL_circuit | 结构生长/修剪 |
| T005 T·S·I | LOCAL_motion_state, LOCAL_energy | 代谢约束 |
| T006 Anchors | ALL | 四物理锚点 |

## 版本历史

| 版本 | 关系变更 |
|---|---|
| v0.10.1 | 世界→EnergyStore→Vascular 通路建立 |
| v1.5.0 | 影子层→DA 连接 |
| v1.6.0 | MotionState→Noether 连接 |
| v1.7.2 | EnergyStore→Sprout gate (P2.1) |
