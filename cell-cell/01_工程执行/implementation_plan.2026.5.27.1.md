# Phase 5: 基线修复 (V_ss > V_th → δa 有方向)

## 问题诊断

### 全层基线状态

| Layer | bc_current | R_leak | V_ss=bc×R | V_th | V_ss > V_th? |
|-------|-----------|--------|-----------|------|-------------|
| MET | 0 | 5 | 0 | 0.001 | No（传感层，无需基线） |
| HC | 0 | 5 | 0.115 (v_rest) | 0.05 | ✓ |
| Aff_reg | 0.05 | 10 | 0.50 | v_peak=0.23 | ✓（持续放电） |
| Aff_irr | 0.045 | 8 | 0.36 | v_peak=0.23 | ✓（持续放电） |
| Encoding | 0.012 | 5 | 0.06 | 0.01 | ✓ |
| Column | 0.012 | 5 | 0.06 | 0.01 | ✓ |
| **Motor** | **0.02** | **5** | **0.10** | **0.15** | **✗ ← 唯一断裂点** |

### 后果

Motor V_ss = 0.10 < V_th = 0.15：
- 无外部输入时，motor **永远不放电**
- δa = {0→1, 1→0} 只有"开/关"两种方向
- ds² 无法区分"变得更活跃"和"从静默变为放电"
- STDP 缺少 post_trace 基线 → LTD 路径几乎不存在
- col_to_motor 权重只能增长（只有 LTP）→ 解释了之前的 0.5 饱和

### 数学验证

$$V_{ss} = I_{bc} \times R_{leak} = 0.02 \times 5 = 0.10$$

需要：$V_{ss} \geq V_{th} = 0.15$

$$I_{bc} \geq V_{th} / R_{leak} = 0.15 / 5 = 0.03$$

**留出余量**：$I_{bc} = 0.035 \Rightarrow V_{ss} = 0.035 \times 5 = 0.175 > 0.15$ ✓

### 预期基线放电率

$V_{ss} = 0.175$，$V_{th} = 0.15$，$V_{peak} = 0.20$

多出阈值的电压 = 0.175 - 0.15 = 0.025
到达 V_peak 的驱动力 = 0.20 - 0.15 = 0.05

膜时间常数 τ = R×C = 5×0.01 = 50ms
充电时间到 V_peak ≈ τ × ln(1/(1 - 0.025/0.05)) ≈ 50ms × 0.69 = 35ms
→ 大约 **28 Hz 基线放电率**

> [!WARNING]
> 28 Hz 太高了（motor 以前 3-7 Hz 就已经在分裂了）。
> FatigueCapacitor 会自然压制到更低：V_fat 积累 → 超极化 → 有效阈值提高。
> 但需要验证 FatigueCapacitor 是否足以将 28 Hz 降到合理范围（1-5 Hz）。
>
> 备选：bc = 0.032 → V_ss = 0.16（刚过阈值）→ 更低基线率

## 修复方案

### [MODIFY] [hebbian.py](file:///d:/cell-cc/nexus_v1/circuit/hebbian.py)

`_motor_config()` 中：
```python
bc_current=0.02  →  bc_current=0.032
```

最小改动：只改一个参数值。V_ss = 0.032 × 5 = 0.16 > V_th = 0.15。

## Open Questions

> [!IMPORTANT]
> bc_current = 0.032 vs 0.035：
> - 0.032 → V_ss = 0.16（刚过阈值 0.01）→ 低基线率，保守
> - 0.035 → V_ss = 0.175（超过阈值 0.025）→ 更高基线率，可能需要更强 fatigue
> 
> 建议先用 **0.032**（保守），如果基线太低再增加。

## Verification Plan

1. `test_governance.py`
2. 500k 步运行：
   - Motor 基线放电率 > 0 Hz（不再全零）
   - col_to_motor 权重不饱和
   - 总体行为合理（不因基线过高而爆炸）
