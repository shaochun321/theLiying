# 自适应时间耦合器 — 实现总结

## 问题

所有 spiking 神经元 100% 饱和。原因：dt/τ 不匹配 + 固定 coupler τ + 旁路注入。

## 解决方案：双层自适应 + 全局校准

### 1. 全局 τ 校准（物种级修改）

所有神经元的 τ_RC 统一到 O(dt=1.0) 范围：

| 层 | C_old → C_new | τ_old → τ_new | dt/τ |
|---|---|---|---|
| Encoding | 0.1 → 0.15 | 0.5 → 0.75 | 1.33 |
| Column | 0.05 → 0.20 | 0.25 → 1.00 | 1.00 |
| Motor | 0.01 → 0.30 | 0.05 → 1.50 | 0.67 |

**文件**: [hebbian.py](file:///d:/cell-cc/nexus_v1/circuit/hebbian.py)

---

### 2. VoltageRegulator + Bias 校准

**规则**: V_ss(VR) < v_peak/3, V_ss(bias) < v_peak/2

| 层 | vr_base | bc_current | 效果 |
|---|---|---|---|
| Encoding | 0.05→0.04 | 0.05 (不变) | VR 不再驱动 spike |
| Column | 0.05→0.015 | 0.03 (不变) | VR 纯恢复 |
| Motor | 0.5→0.015 | 0.032→0.01 | 必须由 Column 驱动 |

---

### 3. Binding→Motor 旁路修复

[variant_adapter.py L744-750](file:///d:/cell-cc/nexus_v1/circuit/variant_adapter.py#L744-L750)

binding 通道直接 `mot._membrane.inject(... * 10.0)` 绕过了 coupler。每步注入 dV=7.0 >> v_peak=0.2。

**修复**: gain 10.0 → 0.1（休眠通道）。

---

### 4. C-layer: 快速逆行反馈

[temporal_coupler.py](file:///d:/cell-cc/nexus_v1/components/temporal_coupler.py)

```
downstream ema → [MOSFET: vth=0.2, gm=2.0] → extra leak
```

- 当 ema > 0.2 → MOSFET 导通 → coupler 加速排空 → 输出降低
- 生物对应：**内源性大麻素** (endocannabinoid)
- 时间尺度：每步

### 5. B-layer: 慢环流反馈

```
ema_upstream → [MOSFET_up] → I_charge ↓
                                       [C_slow: τ=1000步] → V_slow → R_leak
ema_downstream → [MOSFET_dn] → I_drain ↑
```

- V_slow > 0 (upstream 更活跃) → R_leak 增 → τ_base 增 → 传更多
- V_slow < 0 (downstream 更活跃) → R_leak 减 → τ_base 减 → 传更少
- **吸引子**: ema_up ≈ ema_down (阻抗匹配)
- 生物对应：**突触缩放** (synaptic scaling, Turrigiano 2008)
- 时间尺度：~1000 步

---

## 验证结果 (10000 步)

```
Column oto_x: 67.3% duty (从 100% 降下来)
Motor move_x: 69.4% duty (从 100% 降下来)
Motor Vm: 0.07-0.15 (从 7.0/210 降到合理范围)
Noether: 0 violations ✅
```

### B-layer 吸引子验证

| 连接 | ema_up | ema_down | V_slow | τ_base | 状态 |
|---|---|---|---|---|---|
| Col→Mot | 0.692 | 0.693 | ≈0 | 2.000 | **平衡** ✅ |
| Enc→Col | 1.000 | 0.692 | +0.031 | 2.123 | 缓慢收敛中 |

Col→Mot 已达到完美阻抗匹配。Enc→Col 正在正确方向上漂移。
