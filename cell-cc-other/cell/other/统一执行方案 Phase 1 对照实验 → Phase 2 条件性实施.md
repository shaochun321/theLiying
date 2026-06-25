

### 一、两份分析的共识提炼

| 共识点 | 内容 |
|--------|------|
| **不立即实施 Phase 2** | 先跑 100k-150k 步对照实验，让物理系统自行演化 |
| **剪刀差收窄≠共模死锁** | 差分拓扑的净驱动公式为 `I = 10.0 × (w_front × a_front - w_back × a_back)`，只要 `a_front > a_back`，即使权重相等仍有梯度驱动。w_back 上涨真正威胁是“拉起手刹”——增加负电流耗散 Motor 能量 |
| **Phase 2 机制被认可** | 基于各束 `_ema_calcium` 的相对活跃度调制 STDP 学习率，在神经科学中对应“异突触竞争” |
| **对照实验的判决红线** | 剪刀差在 100k 步后企稳 >0.02 → 无需 Phase 2；剪刀差跌破 <0.01 → 执行 Phase 2 |


### 二、对照实验方案（立即执行，不修改代码）

#### 2.1 目标
将当前 Phase 1 完全体（差分拓扑 + 分级编码 + 阻抗匹配）从 50k 步延伸至 **100k-150k 步**，观测：
1. 剪刀差 `Δw = w_front - w_back` 是否自然趋稳
2. 位移速率是否衰减
3. `w_front` 和 `w_back` 是否双双撞到 0.5 天花板

#### 2.2 运行规范
- **场景**：热源在 +x 方向（与 Phase 1 验证相同）
- **步数**：100k 步（从 0 开始，或从当前 50k 检查点继续）
- **记录间隔**：每 10k 步记录一次 `w_front`、`w_back`、`Δw`、body 位置、Motor 平均发放率

#### 2.3 判决标准

| 100k 步观测结果 | 判定 | 下一步 |
|----------------|------|--------|
| `Δw > 0.02` 且稳定 | 物理系统自稳定，Phase 2 不必要 | 直接进入 Phase 3（三因子适格迹）|
| `0.01 < Δw < 0.02` 且仍在缓慢收窄 | 临界状态，需继续观察至 150k | 延长对照至 150k 步 |
| `Δw < 0.01` 或权重双双撞 0.5 天花板 | 经典 STDP 盲目性导致系统失效 | **执行 Phase 2** |


### 三、Phase 2 方案（条件性执行，仅在对照失败后实施）

#### 3.1 核心机制：异突触竞争（Heterosynaptic Competition）

**修改位置**：`bundle.py` 的 STDP 更新循环

**原理**：每个束维护一个慢速漏积分器 `_ema_calcium`，追踪其源的钙信号活跃度。在 STDP 更新时，该束的学习率由其相对于同模态其他束的活跃度比例调制。

**数学形式**：

```python
# 在 bundle 初始化时增加
self._ema_calcium = 0.0  # 慢速漏积分器

# 在 propagate() 中更新
self._ema_calcium += (src.calcium_rate - self._ema_calcium) * 0.0001  # τ≈10000步

# 在 stdp_update() 中，由外部传入同模态所有束的 ema_calcium 列表
# 计算相对活跃度
sum_ema = sum(ema_list) + epsilon
relative_activity = self._ema_calcium / sum_ema

# 调制学习率
effective_lr = base_lr * (1.0 + (relative_activity - 1/len(ema_list)) * COMPETITIVE_SCALE)
```

**关键参数**：
- `COMPETITIVE_SCALE = 2.0`（初步建议）
- 如果某束的 ema_calcium 是同模态平均的 2 倍，其 lr 翻倍；如果只有 0.5 倍，其 lr 减半

**配置位置**：`BundleConfig` 新增字段

```python
use_heterosynaptic_competition: bool = False
competitive_scale: float = 2.0
```

**不引入 if-else**：使用漏积分器 + 数学比例计算，无硬编码阈值。

#### 3.2 与热梯度验证扩展的关系

| 场景 | Phase 2 状态 | 热梯度验证 |
|------|-------------|----------|
| 对照成功（Δw 自稳定）| 不执行 | 继续观察至 150k 确认 |
| 对照失败（Δw 崩塌）| 执行 Phase 2 | 重新从 0 开始运行 100k 步验证 |


### 四、技术债务评估

| 维度 | 对照实验 | Phase 2（条件执行）|
|------|---------|-------------------|
| 代码改动 | 0 行 | ~50 行 |
| 新参数 | 0 个 | 2 个（`use_heterosynaptic_competition`, `competitive_scale`）|
| 运行时开销 | 无 | 每个 bundle 新增一个 EMA 更新 |
| 回滚成本 | 0 | 将 `use_heterosynaptic_competition=False` 即可 |
| 对后续阶段的影响 | 无 | 不依赖 DA，不影响 Phase 3/4 |


### 五、总结：行动指令

| 顺序 | 操作 | 产出 |
|------|------|------|
| **1** | 运行 100k 步对照实验（不修改代码）| 剪刀差演化轨迹 + 位移数据 |
| **2** | 根据判决标准评估结果 | 确定是否需要 Phase 2 |
| **3a** | 若对照成功 → 直接进入 Phase 3 | 确认 Phase 1 已足够 |
| **3b** | 若对照失败 → 执行 Phase 2 | 实施异突触竞争，重新验证 |

**立即执行对照实验**。代码保持 Phase 1 状态，一行不改。等待 100k 步数据回来后再决定是否需要 Phase 2。