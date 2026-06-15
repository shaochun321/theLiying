# 建模分析 007 — 并行分析 (Thread A + Thread B)

> **日期**: 2026-05-22
> **方法**: 相平面分析 + 互信息 + 信噪比

---

## Thread A: 上游信号瓶颈 (DEG-004)

### A1. HairCell 相平面

```
vm range:  [1.006, 3.065]    ← 远超 E_Ca (1.0)！
Ca range:  [0.013, 0.013]    ← 几乎常数
Ca > threshold: 100% of time  ← Ca 始终在释放
Trajectory: SLOWLY VARYING    ← 接近固定点
```

**关键发现**: HC 电压达到 3.065，远超 Ca 反转电位 (E_Ca=1.0)。
Ca 系统已经**饱和**在释放态 (100% 时间 > threshold)，
所以 release_rate 几乎常数 (0.013-0.016)。

这意味着 HC 输出是一个**近似 DC 信号**，不是脉冲调制。

### A2. HC → Aff 电流链分析

```
release_rate = 0.015 (constant)
G(w=0.8) = 0.48
synapse_gain = 80
→ HC→Aff current = 0.015 × 0.48 × 80 = 0.58
→ dV/step = 0.58 × 0.001 / 0.5 = 0.00116
→ Predicted ISI = 0.153 / 0.00116 = 131 ms (7.6 Hz)
→ Measured: 12.6 Hz (faster due to RC leak providing extra charging?)
```

**瓶颈定位**: release_rate = 0.015 太低。
这是因为 Ca_gate 的 gm = 5.0，但 Ca 本身只有 0.013，
所以 release = gm × conduct(Ca) = 5.0 × 0.003 ≈ 0.015。

### A3. 互信息瓶颈

```
Link                  MI (bits)  MI/H(X)
MET→HC_vm                3.28     76.4%     ← 高效
HC_vm→Ca                 3.16     82.2%     ← 高效
Ca→Release               4.32    100.0%     ← 完美
Release→Aff_v            0.02      0.5%     ← ███ 瓶颈 1
Aff→Enc                  0.19      4.4%     ← ███ 瓶颈 2
Enc→Col                  0.31     35.0%     ← 中等
```

> **互信息揭示了两个信息瓶颈**：
> 1. **Release → Aff_v**: 只有 0.5% 的信息通过！
>    因为 release 是近 DC (0.013-0.016)，但 Aff_v 有丰富的
>    充电-放电-充电周期 → 两者几乎不相关
> 2. **Aff → Enc**: 只有 4.4%
>    Aff 是 spiking (0/1), Enc 有 DecouplingCap 平滑 → 维度失配

---

## Thread B: Motor 偏置移除结果

### B1. 去偏后更糟

```
Motor spikes: 124 (全部在 t < 1500, 即信号到达之前)
Post-signal spikes: 0  ← 信号驱动的放电 = 零！
SNR: 0.0
```

**Motor 在信号到达后反而不放电了！**

这是因为：
1. t < 1500: Encoding/Column 的 bias current 驱动了一些活动 → 传到 Motor
2. t > 1500: 信号到达后，Column 活动被 AGC 压制 → Motor 收到的电流不够

### B2. Energy

```
Motor energy: 0.001 (仍然耗尽)
Column energy: 0.001 (也耗尽了！)
Encoding energy: 1.0 (OK)
```

**Column 也耗尽了** — VR 在 Column 上也不够。

### B3. Heat

```
Motor mean heat: 68.08 (从 3.5 升到 68！)
```

这是因为 Column→Motor 的 AGC gain 在低活动时变高，
导致 Motor 收到放大的电流 → I²R 很大 → 但电流仍不到 v_peak。

---

## 根因总结

### 核心问题: 两个信息瓶颈

1. **HC release → Aff**: MI = 0.5%
   - 原因: release ≈ 常数 DC (Ca 饱和)
   - 需要: 让 Ca 有动态变化 (不是一直在阈值以上)

2. **Aff → Enc**: MI = 4.4%  
   - 原因: Aff 是 spiking, Enc 有 DecouplingCap 平滑
   - 需要: 调整时间常数匹配

### 关联发现

- Column energy 也耗尽 → VR activity_coeff 不够
- Motor 信号驱动为零 → Col→Motor 增益链断裂
- AGC 在低活动时 gain=5 → 放大了噪声但不够驱动 spike
