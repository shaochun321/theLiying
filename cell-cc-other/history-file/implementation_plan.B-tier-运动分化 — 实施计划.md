# B-tier: 运动分化 — 实施计划

## 问题

当前 Col→Mot 只有**一个 4×3 全连接 bundle**。所有 column 同等驱动所有 motor：

```
col_yaw  ──┐      ┌── move_x
col_pitch ─┼──ALL──┼── move_y
col_roll  ─┤      └── move_z
col_oto_x ─┘
```

STDP 无法分化这些权重，因为所有 column 在正弦输入下有相同的 ema (~0.69)。结果：所有 motor 输出相同 (0.685)。

## 物理约束

生物中，前庭核→运动核的投射是**拓扑保守**的：
- **VOR**: yaw col → 水平眼肌 (roughly move_x)
- **VOR**: pitch col → 垂直眼肌 (roughly move_y)  
- **VSR**: roll col → 躯干肌 (roughly move_z)
- **Otolith**: oto_x → 线性加速度补偿

## 方案

将单个 4×3 bundle 拆成 **3 个轴特异 bundle + 1 个跨轴束**：

```
col_yaw  ──── bundle_yaw_x  ──── move_x   (主通路)
col_pitch ─── bundle_pitch_y ─── move_y   (主通路)
col_roll  ─── bundle_roll_z ──── move_z   (主通路)

col_* ──────── bundle_cross ───── move_*   (跨轴: 4×3, weak)
```

> [!IMPORTANT]
> 跨轴 bundle 保留全连接，但 **initial_weight 低** (0.05 vs 0.2) 且 **stdp_lr 低** (0.001)。
> 这允许 STDP 在需要时发展跨轴补偿（例如头倾斜时需要多轴协调），
> 但主通路有先天拓扑优势。

### 修改文件

#### [MODIFY] [hebbian.py](file:///d:/cell-cc/nexus_v1/circuit/hebbian.py)

替换 L398-L439 的单一 `col_to_motor` bundle 为 3 个轴特异 bundle + 1 个弱跨轴 bundle。

### Oto_x 通路

oto_x 测量线性加速度，不直接映射到单一运动轴。保留 oto_x→all_motors 连接在跨轴 bundle 中。

## 验证

1. 运行 10k 步，only oto_x 输入 → 检查是否 move_x 占优
2. 运行 10k 步，yaw 输入 → 检查是否 move_x 占优  
3. Noether 仍然 PASS
