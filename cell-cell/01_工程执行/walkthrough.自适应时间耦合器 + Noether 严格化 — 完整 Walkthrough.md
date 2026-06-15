# 自适应时间耦合器 + Noether 严格化 — 完整 Walkthrough

## 修改文件清单

| 文件 | 改动 |
|---|---|
| [temporal_coupler.py](file:///d:/cell-cc/nexus_v1/components/temporal_coupler.py) | B+C 双层自适应 + 能量追踪 |
| [bundle.py](file:///d:/cell-cc/nexus_v1/circuit/bundle.py) | B-layer 配置 + ema_upstream 传递 + Xin 签名追踪 + 滚动账本 + fruit 修复 |
| [hebbian.py](file:///d:/cell-cc/nexus_v1/circuit/hebbian.py) | 全局 τ 校准 + 所有 bundle 启用 B+C coupler + ZCR-guided pruning |
| [noether_probe.py](file:///d:/cell-cc/nexus_v1/circuit/noether_probe.py) | 纳入 coupler 能量 + Xin 严格守恒 + 滚动账本读取 |
| [variant_adapter.py](file:///d:/cell-cc/nexus_v1/circuit/variant_adapter.py) | Binding→Motor gain 10→0.1 |
| [neuron.py](file:///d:/cell-cc/nexus_v1/components/neuron.py) | (审计确认无需修改) |

---

## 1. 自适应 TemporalCoupler

### C-layer（快速逆行反馈）
- MOSFET 读 downstream ema → 当 ema > 0.2 时导通 → 额外 leak → τ_eff 降低
- 时间尺度：每步
- 生物：内源性大麻素 (endocannabinoid)

### B-layer（慢环流反馈）
- 差分 MOSFET 比较器：ema_upstream vs ema_downstream
- 慢电容积分 (τ_slow = 1000 步) → V_slow → 调节 R_leak → τ_base 漂移
- 吸引子：ema_up ≈ ema_down（阻抗匹配）
- 生物：突触缩放 (Turrigiano 2008)

### 验证结果 (100k 步)
- Col→Mot: **完美阻抗匹配** (ema 0.694 ≈ 0.685, V_slow ≈ 0)
- B-layer 在 ~10k 步内收敛，此后稳定

---

## 2. 全局校准

| 项目 | 修改 | 效果 |
|---|---|---|
| τ_RC | Enc 0.75, Col 1.0, Mot 1.5 | dt/τ ∈ [0.67, 1.33] |
| VR base_rate | 0.05→0.04 (Enc), 0.5→0.015 (Mot) | VR 不驱动 spike |
| Motor bias | 0.032→0.01 | 必须由 Column 驱动 |
| Binding gain | 10.0→0.1 | 消除旁路注入 (dV 7.0→0.007) |

---

## 3. Noether 严格化

### 能量守恒
- TemporalCoupler 加 `stored_energy = 0.5CV²` + 累计 in/out
- NoetherProbe 纳入 coupler 能量到全局账本
- 结果：**0.0012% 误差**

### Xin 守恒（三轮修复）
1. **abs→signed**：`_xin_produced += total_residual * dt`（不用 abs）
2. **滚动账本**：每 10000 步 checkpoint，防止浮点大数吞噬
3. **Fruit 修复**：`update_fruit()` 的 `xin_tension *= 0.5` 现在正确追踪
- 结果：**0 violations**

---

## 4. ZCR-Guided Pruning (#5)

驻波节点 vs 腹点：
- **高 ZCR (>0.15) = 波节 = 信息干线** → 受保护，抵抗 pruning
- **低 ZCR = 波腹 = 能量死水** → 优先被剪
- 仅 `_contract_request` (显式需求) 可覆盖 ZCR 保护

---

## 5. Spike 时序审计 (#6)

确认顺序正确：Input → Channels → Adaptation/Fatigue → **Spike Check** → **Leak**

无需修改。

---

## 6. 外部评审比较

| 维度 | 2026.6.7.txt | 2026.6.7.1.txt |
|---|---|---|
| 强项 | 精准 bug 定位 + 防爆指令 | T·S·I 统一 + 影子层目标 |
| 最有价值贡献 | Xin 大数吞噬警告 (已实施) | 阻抗匹配 = 自由能最小 |
| 性质 | 战术手册 | 战略地图 |

---

## 最终验证

```
Noether: PASS (0 violations, 0.0012% energy error)
Column duty: 67-69%
Motor duty: 69%
B-layer: 10k步收敛, 100k步稳定
Body: 有运动, 无饱和
```
