# 统一方向性冷启动方案 — 技术审查

## Q1-Q3 事实确认

### Q1: therm_front/back/left/right 是否独立读取？

**✅ 确认：是的，完全独立。**

信号链：
```
Body.sample_skin(world)
  → 遍历 4 个 SkinPatch
    → 每个 patch 调用 patch.world_position(body) 得到独立世界坐标
    → 调用 world.temperature_at(patch_pos) 得到该位置的温度
    → Fourier 热传导积分：dT_skin = k × (T_env - T_skin) / C × dt
```

代码证据（[world.py:265-277](file:///D:/cell-cc/cell-cc-xyj/cell-cc-other/nexus_v1/components/world.py#L265-L277)）：
```python
def sample_skin(self, world, dt):
    for patch in self.skin_patches:
        T, dT = patch.sample(world, self, dt)  # 每个 patch 独立采样
        result[patch.patch_id] = (T, dT, patch.damage_integral)
```

四个 patch 的 `local_offset`（[world.py:221-226](file:///D:/cell-cc/cell-cc-xyj/cell-cc-other/nexus_v1/components/world.py#L221-L226)）：
```python
front: [r, 0, 0]   # 前方
back:  [-r, 0, 0]  # 后方
left:  [0, r, 0]   # 左侧
right: [0, -r, 0]  # 右侧
```
其中 `r = effective_radius ≈ 1.29`（默认 volume=9）。

**结论**：四个 patch 确实在不同世界坐标采样，温差取决于 body 相对热源的位置和朝向。

---

### Q2: world_position 是否正确？

**✅ 确认：正确，但有一个重要细节。**

[world.py:122-159](file:///D:/cell-cc/cell-cc-xyj/cell-cc-other/nexus_v1/components/world.py#L122-L159) 的 `world_position()` 使用 Rodrigues 旋转将 `local_offset` 从 body frame 转到 world frame：

```python
# 朝向来自速度方向
if speed > 0.01:
    heading = velocity / |velocity|
else:
    heading = [1, 0, 0]  # 默认朝 x 正方向
```

> [!IMPORTANT]
> **静止时 heading = [1,0,0]**。这意味着：
> - 在实验初期（body 几乎静止），front patch 始终在 x+ 方向，back 在 x-，left 在 y+，right 在 y-
> - 方案提议 body 在 `[75, 20, 25]`，热源在 `[75, 25, 25]`
> - 热源在 body 的 **y+ 方向** = **left** patch 方向（不是 right！）
> 
> 方案原文假设 right patch 更近，但实际上是 **left** patch 更近。
> 不影响方案有效性（仍有温差），但预期方向标签需要修正。

---

### Q3: 实验脚本能否覆盖 body 位置？

**✅ 确认：可以。**

[world.py:399-400](file:///D:/cell-cc/cell-cc-xyj/cell-cc-other/nexus_v1/components/world.py#L399-L400)：
```python
if body is None:
    body = Body()
```

`VariantCircuit.__init__()` 调用 `World()` 时不传 body，所以使用默认 `Body()`，其位置默认 `[63, 25, 25]`。

在实验脚本中可以在初始化后直接覆盖：
```python
c = VariantCircuit()
c.world.body.position = [75.0, 20.0, 25.0]
```
不需要修改任何全局默认值。

---

## 四项修复的逐条审查

### 4.1 初始姿态偏移 — ✅ 通过

技术上正确。Body 默认 `[63, 25, 25]`，改为 `[75, 20, 25]` 使 left patch（y+方向）距热源 `[75,25,25]` 约 4 单位，right patch 约 6 单位。

**温差估算**：
```
d_left  ≈ sqrt(0 + (20+1.29-25)² + 0) ≈ 3.71
d_right ≈ sqrt(0 + (20-1.29-25)² + 0) ≈ 6.29
T_left  = 5.0 × (1 - 3.71/30) = 4.38
T_right = 5.0 × (1 - 6.29/30) = 3.95
ΔT = 0.43
```

ΔT ≈ 0.43 是显著信号，足够驱动差分学习。

---

### 4.2 空间侧向抑制 — ⚠️ L 层级问题

> [!WARNING]
> **这是本方案中我唯一有结构性保留的部分。**
>
> 提议的除法归一化公式：
> $$\tilde{x}_i = \frac{x_i^p}{\epsilon + \sum_{j=1}^{4} x_j^p}$$
>
> 这是**软件层面的数学运算**——不是电路原语（Capacitor/MOSFET/Memristor）实现的。
> RULES.md S0 规则要求：*"凡在信号通路上执行计算的位置，必须由 S0 原语实现"*。
>
> 除法归一化无法用单个 S0 原语表达。它本质上是一个**全局归一化器**，
> 需要知道所有 4 个通道的总和才能计算每个通道的输出——这是一个隐含的集中式比较操作。

**替代方案建议**：

现有体感链中的 **SomatoRelay** 已经有 `lateral_gain` 参数（构造时 `lateral_gain=0.05`），
实现了基于 InhibitorySynapse 的侧向抑制——这**已经是 S0 合规的**（MOSFET 结构）。

```python
# somatosensory/chain.py 构造时已有：
self.somatosensory = SomatosensoryChain(
    patch_ids=["front", "back", "left", "right"],
    lateral_gain=0.05,    # ← 已有侧向抑制
)
```

可以做的是**增大 `lateral_gain`** 从 0.05 到 0.3-0.5，而不是插入一个新的除法归一化层。
效果类似（强化对比度），但完全在 S0 框架内。

---

### 4.3 Langevin τ 延长 — ✅ 通过（但需要量化确认）

当前 τ=0.5s 确实太短。OU 过程的特征位移与 τ 成正比：

```
每次随机推力持续 ~τ 步
位移 ∝ σ × τ (OU 过程扩散标度)
当前: σ_eff ≈ 0.07, τ=500 步 → 位移/推力 ≈ 0.07 × 500 = 35 步等效
延长: τ=5000 步 → 位移/推力 ≈ 0.07 × 5000 = 350 步等效
```

但 τ=5s 改变的不只是位移——它也改变了 **shadow predictor 的 Xin 基线**。
OU 噪声变慢后，shadow 更容易预测 → Xin 残差降低 → DA 降低。

> [!NOTE]
> **建议起步 τ=3.0s（3000 步）而非 5.0s**，避免 shadow 预测能力过强导致 DA 信号被压制。
> 可在实验中扫描 τ ∈ {2.0, 3.0, 5.0} 确定最优值。

**实施**：只需修改 [langevin_noise.py:69](file:///D:/cell-cc/cell-cc-xyj/cell-cc-other/nexus_v1/components/langevin_noise.py#L69)：
```python
tau: float = 3.0  # was 0.5
```

---

### 4.4 YolkSac 扩容 — ✅ 通过

200→500，释放速率不变（0.002/步），耗尽时间从 100k→250k 步。数学简单且一致。

当前基础代谢净消耗约 3.56e-6/步（Phase 3 报告测算），yolk 贡献 0.002/步 >> 3.56e-6/步，
所以 yolk 期间 fill 不会下降。这正是设计意图：在 yolk 期间给学习提供安全窗口。

**实施**：修改 [yolk_sac.py:21](file:///D:/cell-cc/cell-cc-xyj/cell-cc-other/nexus_v1/components/yolk_sac.py#L21)：
```python
initial_level: float = 500.0  # was 200.0
```

---

## 方案整体评估

| 修复项 | 判定 | 理由 |
|--------|------|------|
| 初始姿态偏移 | ✅ 通过 | 物理初始条件，不改逻辑 |
| 空间侧向抑制 | ⚠️ 需调整 | 除法归一化违反 S0；建议用现有 `lateral_gain` 增大 |
| Langevin τ 延长 | ✅ 通过 | 建议 τ=3.0 起步 |
| YolkSac 扩容 | ✅ 通过 | 纯参数调整 |

---

## 关于"缺失的第五维"

> [!IMPORTANT]
> 此方案解决了**输入信号**（温差）、**信号对比度**（侧向抑制）、**位移**（Langevin τ）、**时间预算**（YolkSac）四个维度。
> 
> 但没有解决**第五维**：Binding→Motor 0.001 固定权重。
> 
> 即使四个 patch 有了显著温差，温差信号仍然只能通过两条路径驱动运动：
> 1. **Col→Motor STDP 束**（therm_front→move_x 等）— 有 STDP，能学习
> 2. **Binding→Motor 侧通道** — 0.001 固定，不能学习
> 
> 路径 1 在 Phase 3 中已工作（权重从 0.1→0.45），但缺乏方向分化。
> 方案的四修复改善了输入信号的方向性，**应该能使路径 1 的 STDP 产生方向分化**——
> 因为现在 front 和 back 的信号不再相同了。
> 
> **结论**：此方案有可能在不碰 Binding→Motor STDP 的情况下就实现方向分化。
> 值得先验证。如果 500k 步后四方向差仍 < 0.02，再考虑 Binding→Motor STDP。

---

## 建议的修改执行顺序

| 步骤 | 操作 | 文件 | 工作量 |
|------|------|------|--------|
| 1 | Langevin τ: 0.5→3.0 | `langevin_noise.py:69` | 1 行 |
| 2 | YolkSac: 200→500 | `yolk_sac.py:21` | 1 行 |
| 3 | `lateral_gain`: 0.05→0.3 | `variant_adapter.py` 构造 SomatosensoryChain | 1 行 |
| 4 | 实验脚本覆盖 body 位置 `[75, 20, 25]` | `exp_phase4_*.py`（新建）| ~5 行 |
| 5 | `max_deposit_per_step`: 0.05→0.12 | `energy_store.py` | 1 行 |
| 6 | 运行 500k 步 | — | ~50 min |

步骤 5 是从主项目 EXP-023 标定带来的，方案原文未提及但同样重要（防止代谢崩溃的根源修复）。
