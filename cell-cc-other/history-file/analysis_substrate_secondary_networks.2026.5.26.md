# 次级网络与基质：神经元"存在"的物质基础

## 1. 实验诊断：为什么纯 Mitosis 失败

27 次分裂 → 30 个 motor neuron → 15 个僵尸 + 1 个暴走

| 失败模式 | 数量 | 根因 |
|---------|------|------|
| 死于出生（0 Hz） | ~15 | 无输入连接（随机 50/50 分配运气差） |
| 级联分裂（5 层深） | 3 链 | 子代继承父代疲劳特性 → 立刻再分裂 |
| 暴走（145 Hz） | 1 | 获得多数输入 → 无基质限制 → 指数加速 |
| 负载不均（52.9% vs 0.2%） | 全局 | 无空间局部性 → 无竞争排斥 |

**核心缺陷**：当前 mitosis 只有"细胞分裂"，缺少"细胞存活条件"。

---

## 2. 生物学参考：三个次级网络

### 2.1 星形胶质细胞（Astrocyte）— 突触领地管理者

每个 astrocyte 管理 ~100,000 个突触的"领地"：
- **突触包裹**：astrocyte 突起包裹突触间隙，清除谷氨酸（防止兴奋毒性）
- **能量穿梭**：乳酸穿梭（astrocyte-neuron lactate shuttle）——
  astrocyte 吸收葡萄糖 → 乳酸 → 输送给活跃 neuron
- **领地排斥**：astrocyte 之间存在"领地边界"（tiling），
  每个 astrocyte 不与邻居重叠 → 天然的空间分区
- **三突触体**（Tripartite synapse）：突触不是 pre + post，
  而是 pre + post + astrocyte，astrocyte 释放 gliotransmitter 调节突触强度

> **映射到项目**：没有 astrocyte → 新生 neuron 没有"供养者"，
> 没有能量来源，没有突触维护。死于出生是必然的。

### 2.2 神经血管耦合（Neurovascular Coupling, NVC）— 能量分配器

- **按需供血**：活跃脑区的血流量在秒级时间内增加
- astrocyte endfoot 包裹血管 → 检测 neuron 活动 → 释放 vasodilator → 血管扩张
- **能量预算**：每个脑区有固定的血管密度 → 可支撑的 neuron 数量有上限
- 新生 neuron 只有在有足够血管支持的区域才能存活

> **映射到项目**：当前 PowerRail 对所有 neuron 均等供能。
> 30 个 motor neuron 共享同一个 PowerRail → 无竞争 → 无自然淘汰。

### 2.3 细胞外基质（ECM）— 结构脚手架

- **ECM 成分**引导轴突生长方向（层粘连蛋白、纤维连接蛋白等）
- **PNN**（Perineuronal Net）包裹成熟 neuron → 保护已有突触 → 限制新连接
- **ECM 降解**（MMP 酶）是突触可塑性的前提 → 没有降解就没有新连接
- **生长因子**（BDNF, NGF）嵌入 ECM → 扩散范围有限 → 空间局部性

> **映射到项目**：当前 ECM 只做热管理和 PNN 门控。
> 缺少：空间位置、领地划分、生长因子扩散。

---

## 3. 设计原则：从"分裂"到"存活"

### 原则 1：存在 = 时间 × 空间 × 物质（T × S × M）

```
Neuron 存在条件:
  T: 出生后需要 grace period 才能被评估（已有 sprout grace period）
  S: 必须有"空间位置"——即所属 astrocyte 领地的容量余量
  M: 必须有"物质供应"——所属 PowerRail 区域的能量预算
  
只有 T∧S∧M 同时满足，neuron 才能存活。
```

### 原则 2：次级网络是约束，不是控制

次级网络（astrocyte, vascular, ECM）不"决定"neuron 做什么，
而是"约束"neuron 能在哪里存在、能获得多少能量、能建立多少连接。

```
当前实现:
  Neuron 自己决定分裂（V_fat > threshold）
  Neuron 自己决定连接（50/50 random）
  → 无约束 → 爆炸

应该是:
  Astrocyte 决定：这个位置还能容纳新 neuron 吗？
  Vascular 决定：这个区域还有能量预算吗？
  ECM 决定：这个方向允许轴突延伸吗？
  → 约束先行 → 有序生长
```

### 原则 3：基质（Substrate）是"存在的容器"

```
SubstrateNetwork (已存在)
  └── PowerRail (能量供应)
  └── ECM (热管理 + PNN)
  └── [NEW] TrophicField (生长因子场 → 空间容量)
  └── [NEW] VascularBudget (血管能量预算 → 区域限制)
```

---

## 4. 具体方案：Substrate-First Mitosis (Phase 3b)

### 4.1 TrophicField（营养场）

每个网络层维护一个"容量场"，表示该区域能支撑多少 neuron：

```python
@dataclass
class TrophicField:
    """Trophic factor field for a network region.
    
    BIO: BDNF/NGF diffusion from target tissue.
    Capacity = max neurons this field can sustain.
    Occupancy = current neurons in this field.
    
    S0: implemented as Capacitor (charge = trophic factor concentration).
    """
    capacity: int = 6          # max neurons in this region
    occupancy: int = 3         # current neuron count
    trophic_cap: Capacitor     # concentration integrator
    
    def has_room(self) -> bool:
        """Is there capacity for a new neuron?"""
        return self.occupancy < self.capacity
    
    def admit(self):
        """Register a new neuron."""
        self.occupancy += 1
    
    def release(self):
        """Neuron died/removed."""
        self.occupancy -= 1
```

### 4.2 VascularBudget（血管能量预算）

每个网络层的 PowerRail 有最大供应电流。超过预算 → 所有 neuron 电压下降：

```python
# 已存在的 PowerRail:
#   V_actual = Vdd - I * R_internal
# 
# 当 neuron 数量增加时, 总 I 增加 → V_actual 下降
# → 自然限制: 太多 neuron → 供电不足 → 弱者淘汰
#
# 这已经是 S0 组件! 不需要新代码, 只需要正确使用。
```

### 4.3 修改后的 Mitosis 触发

```python
def should_split(self) -> bool:
    """Mitosis requires BOTH internal stress AND external capacity."""
    internal_ready = (
        self._mitosis_counter >= self.config.mitosis_confirm_steps
    )
    # External: trophic field must have room
    # (injected by circuit layer at check time)
    external_ready = self._trophic_room_available
    
    return internal_ready and external_ready
```

### 4.4 修改后的 Rewiring

```
分裂后:
  1. 子代获得父代 50% 的入边 (不变)
  2. 子代的出边初始权重由 ECM PNN 决定:
     - 高 PNN 区域: 子代出边几乎无法建立 (w_init = 1e-6)
     - 低 PNN 区域: 子代出边正常 (w_init = 1e-4)
  3. PowerRail 共享: 父代和子代共用同一 PowerRail
     → IR drop 自动增加 → V_actual 下降 → 自限
```

### 4.5 Apoptosis（细胞凋亡）— 自然淘汰

```python
def should_die(self) -> bool:
    """Neuron programmed death when it loses its reason to exist.
    
    BIO: neurons that fail to receive trophic support undergo apoptosis.
    Without BDNF from postsynaptic targets, the neuron activates caspase cascade.
    
    Conditions:
      1. Energy below critical for sustained period (no metabolic support)
      2. Zero outgoing synaptic activity (no functional role)
    """
    return (self.energy < 0.05 
            and self._zero_activity_counter > 50000)
```

---

## 5. 与 T/O/P/R/Xin 的关系

| 框架 | 次级网络的角色 |
|------|-------------|
| **T (Total Input)** | Vascular budget 限制了区域的总能量输入 |
| **O (Structure)** | ECM/PNN 保护已有结构沉积 |
| **P (Topological Core)** | Astrocyte 领地 = P 的空间锚点 |
| **R (Competitive Periphery)** | 新生 neuron 在 R 空间竞争，失败者凋亡 |
| **Xin (Prediction Residual)** | Trophic field 的"剩余容量"= 结构生长的许可条件 |

---

## 6. 实施优先级

| 优先级 | 项目 | 复杂度 | 效果 |
|-------|------|-------|------|
| **P0** | TrophicField 容量限制 | 低 | 阻止级联分裂 |
| **P0** | Apoptosis 自然淘汰 | 低 | 清除僵尸 neuron |
| **P1** | PowerRail IR drop 共享 | 中 | 自动能量竞争 |
| **P2** | ECM PNN 门控子代连接 | 低 | 利用已有 ECM |
| **P3** | 空间坐标 + 领地划分 | 高 | 真正的空间性 |
