整合三份分析的共识：**移除 `v_target`，采用纯净的生理匮乏双引擎驱动，增加物理钳位保护。**

### 一、整合后的数理核心

**最终认可的驱动信号（采纳三份分析的共识，剔除 `v_target`）：**

```
S_energy = max(0, 0.5 - fill_fraction)      # 能量缺口
S_da = max(0, 0.2 - DA_concentration)        # 价值缺口
S_drive = α × S_energy + β × S_da
```

其中 α=1.0，β=0.5（能量需求优先于信息需求）。这三个驱动信号都是物理状态变量，不含语义标签。

**慢速积分器（RC 漏积分器，无硬编码阈值）：**

```
G_agc(t+dt) = G_agc(t)·(1 - dt/τ_agc) + S_drive·(dt/τ_agc)
```

其中 τ_agc = 30k-50k 步，对应行为稳态调节的时间尺度。

**物理钳位（采纳审计官处方）：**

```
G_agc_clamped = min(G_agc, MAX_AGC_MULTIPLIER)
g_eff = g_base × (1.0 + G_agc_clamped)
```

MAX_AGC_MULTIPLIER = 4.0，对应最大 5 倍增益（1 + 4）。

**S_energy 的物理含义：**
- fill > 0.5：系统“不饿”，增益保持基线。
- fill ∈ (0.1, 0.5)：系统“饿了”，增益逐渐上升，驱动机体寻找热源。
- fill → 0：增益趋向最大（1+4=5倍），对应绝境中的最大爆发。

与 Phase 2 的区别：Phase 2 在 fill<0.05 时**冻结一切可塑性**（紧急刹车），AGC 在 fill∈(0.1,0.5) 时**提升行为增益**（巡航控制）。两者作用于不同状态区间、不同时间尺度。

### 二、时间尺度分离（确认）

| 机制 | 时间常数 | 作用对象 | 操作 |
|------|----------|----------|------|
| Phase 2 冻结 | 瞬时 | 突触更新 | 门控（0/1） |
| Phase 3 适格迹 | τ≈300步 | LTP标记 | 门控（DA确认） |
| **Phase 4 AGC** | **τ≈30k步** | **行为增益** | **缩放（连续）** |
| Capacity自适应 | τ≈100k步 | 存储容量 | 结构调节（长期） |

各机制在不同频段并行运作，时间常数分离确保相位干涉不会发生。

### 三、执行步骤

| 步骤 | 内容 | 涉及文件 |
|------|------|----------|
| 1 | 在 `variant_adapter.py` 中新增 AGC 状态 | variant_adapter.py |
| 2 | 在 `step()` 中更新 G_agc 并钳位 | variant_adapter.py |
| 3 | 传入 `spinal_reflex.process_hunger()` | variant_adapter.py |
| 4 | 传入 `col_to_motor` bundle 动态增益 | variant_adapter.py / hebbian.py |
| 5 | 运行回归测试，确认通过 | tests/ |
| 6 | 运行对比实验（有/无 AGC）| diag_agc_validation.py |

### 四、验证标准

| 验证项 | 方法 | 通过标准 |
|--------|------|----------|
| AGC 响应 | 对比有/无 AGC 的位移 | 有 AGC 的 Δx 高于无 AGC |
| 增益调制 | 测量 G_agc 随 fill 下降的变化 | G_agc 随 S_energy 上升而上升 |
| 无干扰 | Phase 2/3 测试保持通过 | 12/12 回归全绿 |
| 稳定性 | G_agc 变化平滑 | 无明显振荡 |
| 饱和保护 | 验证增益被钳位在限值内 | G_agc_clamped ≤ 4.0 |

### 五、与 capacity 自适应的关系（保留为附录）

capacity 自适应与 AGC 的时间尺度不同，两机制互不阻塞，可顺序推进。在 Phase 4 AGC 验证通过后，capacity 自适应可作为独立的 Phase 5 设计。当前阶段只构建 AGC。

**最终确认：** 方案已整合三份分析的修正意见，可直接进入代码实施。