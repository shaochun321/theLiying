# 全局架构图 — G-002

> 日期: 2026-05-24
> 版本: v3.0 (标量热感 + 方向学习涌现)
> 关联: G-001 (数学公式), C-001~C-004, layer_contracts

---

## §1 系统全景

```
  ┌──────────────────────────────────────────────────────────────────────────┐
  │                     VariantCircuit (step)                               │
  │                                                                        │
  │  前庭信号 ──▶ 前庭链(4级) ──┐                                           │
  │  (yaw,pitch,roll,           ├──▶ 赫布超图(7轴主环路) ──▶ Motor(3)       │
  │   oto_x,oto_y,oto_z)       │                               │           │
  │                             │                               ▼           │
  │  热源 ──▶ 热感(1标量) ──────┘ (直接→Enc, 跳过前庭链)    Muscle(3)       │
  │           ↑  甲基化适应                                     │           │
  │           │  dT/dt 时间导数                                 ▼           │
  │      ┌────┴────┐      绑定层(21) ← 列层共激活          Body(3D)        │
  │      │  World  │      影子层(24n, 35b)                    │  位置/速度   │
  │      │ 热源·3D │◀──────── 跨模态: Hebbian+decay ──────────┘              │
  │      └─────────┘      [辅助] ECM · PNN · VR · NVC                      │
  └──────────────────────────────────────────────────────────────────────────┘

  闭环: Motor → Muscle → Body → World → ThermalMembrane(1标量) → Enc → Col → Motor

  学习规则:
    轴内(enc→col, col→mot): BCM 竞争修剪 / STDP
    跨轴(shadow cross):     Hebbian+decay (FIX-018, 关联学习, 方向涌现)
    PNN 控制:              maturation_stage 0→1→2 (STDP→BCM→frozen)
```

---

## §2 信号流拓扑图

```
  前庭链（chain.py, 6轴）                    赫布超图 主环路（hebbian.py, 7轴）
  ─────────────────────                    ────────────────────────────────
                                            
  ┌──────┐  w=0.5  ┌──────┐  w=0.8  ┌──────┐       ┌──────────┐ w=0.2  ┌────────┐ w=0.15 ┌────────┐ w=0.1 ┌────────┐
  │ MET  │────────▶│  HC  │────────▶│ Aff  │──────▶│ Encoding │───────▶│ Column │───────▶│ Motor  │──────▶│Muscle │
  │ ×6   │         │ ×6   │         │reg+irr│      │ 14 (2×7) │        │ 7      │        │ 3 xyz  │       │ 3 xyz │
  └──────┘         └──────┘         └──────┘       └──────────┘        └────┬───┘        └────────┘       └───┬───┘
      ↑                                                 ↑                  │                                 │
  机械输入                                               │                  │                                 ▼
  (×6 轴)                                               │         ┌────────▼────────┐                   ┌────────┐
                                                        │         │  Binding Layer  │◀──feedback────────│ Body   │
  热膜(thermal_membrane.py)                              │         │ 21 bind (C(7,2))│                   │ 3D pos │
  ┌──────────┐                                          │         │ 15 intra + 6 cross│                 │ vel    │
  │ 6 MCP簇  │──(therm, dtherm)─── 直接 ───────────────┘         └─────────────────┘                   └───┬───┘
  │ 甲基化   │                    (跳过前庭链)                                                             │
  └────┬─────┘                                                                                             │
       │                                                                                                   │
  ┌────▼─────┐                                                                                             │
  │  World   │◀────────────────────────────────────────────────────────────────────────────────────────────┘
  │ 热源·3D  │   Body.position 变化 → World.temperature_at() → ThermalMembrane.sense()
  └──────────┘
```

### §2.1 节点计数

| 层 | 元件 | 数量 | 类型 |
|----|------|------|------|
| MET | 机械电转换 | 6 | continuous |
| HC | 毛细胞 | 6 | continuous (Ca²⁺ + ribbon) |
| Aff_reg | 传入(规则) | 6 | spiking |
| Aff_irr | 传入(不规则) | 6 | spiking |
| Encoding | 编码 | **14** (2×7轴) | continuous |
| Column | 柱 | **7** (6前庭+1热) | continuous |
| Motor | 运动 | 3 (xyz) | spiking |
| Muscle | 肌肉 | 3 (xyz) | delay buffer |
| Body | 身体 | 1 (3D pos+vel) | Newtonian |
| ThermalMembrane | 热膜 | 1 (6 MCP簇) | methylation |
| Binding | 绑定 | **21** (C(7,2)) | continuous |
| **主环路合计** | | **72** | |

### §2.2 多模态分化 (实验验证 2026-05-24)

| 测量 | 纯前庭 (15) | 跨模态 (6) | 分化比 |
|------|-------------|-----------|--------|
| 绑定首次激活 | step 2217 | step 7570 | 3.4× 延迟 |
| enc→col 权重增长 | +113% | +25% | 4.5× 差异 |
| 影子层跨轴权重 | 0.00279 | 0.00225 | 0.81 ratio |

---

## §3 环流拓扑

```
        ┌────────────────────────────────────────────────────────────────┐
        │                        主 环 流                                │
        │                                                                │
        │   Col_yaw ──▶ Bind_yaw_pitch ──▶ Mot_x ──feedback──▶ Col_yaw  │
        │   Col_pitch ─┘                                      └─ Col_pitch │
        │                                                                │
        │   × 6轴 × C(6,2)绑定 × 3运动 = 最多 270 条路径                  │
        │   实测: 60 条活跃路径 (20k步后)                                  │
        └────────────────────────────────────────────────────────────────┘

        环流测量（CirculationMeter）:
          P = 最强路径 (yaw→bind_yaw_pitch→move_x, flow=0.000396)
          R = 最弱活跃路径
          μ_total = 0.0205 (20k步)
          频率 = 0.39
          方差 = 7.7e-6 (稳定)
```

### §3.1 Bundle 角色分化

| 角色 | delay | gain | 生物对应 | 当前 bundle |
|------|-------|------|---------|------------|
| feedforward | 0 | 10 | 有髓鞘投射轴突 | vest→enc, enc→col, col→mot |
| feedback | 1 | 10 | 丘脑中继 | mot→col (efference copy) |
| cross_axis | 2 | 10 | 联络纤维 | s_cross_* |
| shadow | 1 | 10 | 默认网络内部 | s_enc→col, s_col→mot |

---

## §4 影子层结构

```
                影子层（shadow_sandbox.py, 7轴）
                ─────────────────────────────
                                                     
  主环路 Xin ──▶ ┌─────────────┐  w=0.1  ┌─────────┐  w=0.05  ┌─────────┐
     (|Xin|×K)   │ s_Encoding  │────────▶│ s_Column│─────────▶│ s_Motor │
                  │ 14 neurons  │         │ 7 neur. │          │ 3 neur. │
                  └─────────────┘         └────┬────┘          └─────────┘
                                               │
                              ┌─────────────────┼─────────────────┐
                              │        跨轴 cross_axis             │
                              │        21 bundles (C(7,2))         │
                              │                                    │
                              │  自体几何(15):     世界知识(6):     │
                              │  w≈0.0028 (+179%)  w≈0.0022 (+125%)│
                              │  BCM 快速学习      BCM 缓慢追赶    │
                              └────────────────────────────────────┘
                                               │
                                        测量: κ(收缩度)
                                              ν(运动势)
                                              K_ema(自由能)

    影子层参数:
      τ_shadow = 15 (C=3, R=5)
      observe 间隔: 10 主步
      spiking = False
      maturation_stage = 1 (BCM)
      construction_power = True (临时)

    影子层节点: 24 (14 enc + 7 col + 3 mot)
    影子层突触: 7 (enc→col) + 7 (col→mot) + 21 (cross) = 35

    跨模态权重排列 (BCM 学习后, 非均匀):
      s_cross_yaw_therm:   0.0036  ← 最高 (半规管-热 耦合)
      s_cross_oto_z_therm: 0.0015  ← 最低 (耳石-热 耦合)
      → 反映了各轴与热变化的共激活强度差异
```

---

## §5 辅助系统

```
  ┌──────────────────────────────────────────────────────────────────┐
  │                       辅助系统 (不在信号流中)                      │
  │                                                                  │
  │  ECM (ecm.py)           VR (vascular.py)     PNN (ecm.py)       │
  │  ├─ 温度场 dT/dt        ├─ NVC 血管冷却       ├─ 成熟度 [0,1]    │
  │  ├─ 离子缓冲 B           ├─ 能量输送 dE/dt    ├─ 可塑性门控 g_ℓ   │
  │  └─ K+ 浓度              └─ 活动依赖           └─ STDP 调制       │
  │                                                                  │
  │  Oscillator (oscillator.py)    NDR (ndr.py)       DA (modulator) │
  │  ├─ ISI 同步 (CPG)            ├─ 不应期门控        ├─ 奖赏信号     │
  │  └─ Hopf 分岔                 └─ 侧向抑制          └─ 第三因子     │
  │                                                                  │
  │  Router (router.py)    Damper (damper.py)   Compensation (comp.) │
  │  ├─ 动态拓扑重连         ├─ 自适应阻抗         ├─ Fourier 补偿    │
  │  └─ 液态金属路由          └─ 磁流体阻尼         └─ 相位对齐        │
  └──────────────────────────────────────────────────────────────────┘
```

### §5.1 辅助系统交互

| 系统 | 读取 | 写入 |
|------|------|------|
| ECM | 神经元热输出 | 温度 → PNN → 可塑性门控 |
| VR | 活动量, 温度 | 神经元能量 |
| PNN | ECM 温度, 共激活 | 可塑性门控 g_ℓ |
| Oscillator | Afferent ISI | CPG 同步输出 |
| NDR | Afferent 激活 | 不应期门控 |
| DA | 奖赏信号 | STDP 第三因子 |
| Router | 列层激活 | Enc→Col 拓扑重连 |
| Damper | 列层能量 | Enc/Col 泄漏电阻 |

---

## §6 成熟与学习阶段

```
  Spine (M=0)                  Column (M=1)                Area (M=2)
  ─────────                    ──────────                  ─────────
  PNN < 0.3                    0.3 ≤ PNN < 0.7             PNN ≥ 0.7
  学习率 = 0.18                学习率 = 0.01               学习率 = 0.001
  STDP (脉冲 trace)            BCM (速率 activation)        Frozen
  高可塑性                      中可塑性                     低可塑性
  
  DERC Zone I                  DERC Zone II                DERC Zone III
  梯度控制                      饱和/稳定                    噪声主导
```

---

## §7 完整文件索引

### 核心元件 (components/)

| 文件 | 元件 | §公式 |
|------|------|-------|
| [neuron.py](file:///d:/cell-cc/nexus_v1/components/neuron.py) | RC膜 + MOSFET + 脉冲 | G-001 §1 |
| [ecm.py](file:///d:/cell-cc/nexus_v1/components/ecm.py) | ECM + PNN | G-001 §5 |
| [vascular.py](file:///d:/cell-cc/nexus_v1/components/vascular.py) | NVC 血管冷却 | G-001 §5 |
| [binding.py](file:///d:/cell-cc/nexus_v1/components/binding.py) | 绑定层 (21 cells) | — |
| [shadow_sandbox.py](file:///d:/cell-cc/nexus_v1/components/shadow_sandbox.py) | 影子层 (24n+35b) | G-001 §4 |
| [world.py](file:///d:/cell-cc/nexus_v1/components/world.py) | **3D世界 + Body + 热源** | — |
| [thermal_membrane.py](file:///d:/cell-cc/nexus_v1/components/thermal_membrane.py) | **热膜 (6 MCP簇)** | — |
| [muscle.py](file:///d:/cell-cc/nexus_v1/components/muscle.py) | **肌肉 (3组 xyz)** | — |
| [entropy_ledger.py](file:///d:/cell-cc/nexus_v1/components/entropy_ledger.py) | 熵账本 | — |
| [oscillator.py](file:///d:/cell-cc/nexus_v1/components/oscillator.py) | CPG 振荡器 | — |
| [damper.py](file:///d:/cell-cc/nexus_v1/components/damper.py) | 磁流体阻尼 | — |
| [ndr.py](file:///d:/cell-cc/nexus_v1/components/ndr.py) | NDR + 抑制 | — |
| [router.py](file:///d:/cell-cc/nexus_v1/components/router.py) | 液态金属路由 | — |
| [modulator.py](file:///d:/cell-cc/nexus_v1/components/modulator.py) | DA 调制 | — |
| [semiconductor.py](file:///d:/cell-cc/nexus_v1/components/semiconductor.py) | MOSFET 模型 | G-001 §1.2 |
| [compensation.py](file:///d:/cell-cc/nexus_v1/components/compensation.py) | Fourier 补偿 | — |

### 电路 (circuit/)

| 文件 | 功能 | §公式 |
|------|------|-------|
| [bundle.py](file:///d:/cell-cc/nexus_v1/circuit/bundle.py) | 突触束 + 忆阻器 + 学习 | G-001 §2 |
| [circulation.py](file:///d:/cell-cc/nexus_v1/circuit/circulation.py) | 环流测量 | G-001 §3 |
| [hebbian.py](file:///d:/cell-cc/nexus_v1/circuit/hebbian.py) | 赫布电路 (基础) | — |
| [variant_adapter.py](file:///d:/cell-cc/nexus_v1/circuit/variant_adapter.py) | 变体电路 (完整) | — |
| [observer.py](file:///d:/cell-cc/nexus_v1/circuit/observer.py) | 观测器 | — |

### 概念文档 (docs/)

| 编号 | 主题 |
|------|------|
| C-001 | 环流架构与赫布超图 |
| C-002 | 学习分工与成熟阶段 |
| C-003 | Nature 论文、耦合与第三因子 |
| **C-004** | **自生时空与主体性** |
| **G-001** | **全局数学公式** |
| **G-002** | **全局架构图（本文档）** |
