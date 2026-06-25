# 代谢壁根因报告 — EXP-023

> 诊断时间：2026-06-21  
> 工具：`diag_metabolic_wall.py` + `diag_position_vs_feed.py`

---

## 一、症状

EXP-022（200k 步）及后续长程实验观测到 EnergyStore `fill` 在约 100k 步内归零，
此后系统进入"僵尸生存"状态（神经元靠自身 energy 残余维持）。

---

## 二、诊断数据

### 2.1 能量收支（diag_metabolic_wall.py 输出）

| 时段 | P_in/步 | P_out/步 | 净 |
|------|---------|---------|-----|
| 步 0-100 | **0.0495** | 0.0099 | +0.040 |
| 步 101+ | **0.0000** | 0.0104 | **-0.010** |

- deposit 利用率：**3.4%**（上限 0.05 几乎从未被触及）
- 预计从初始 500 耗尽时间：**~60k 步**（与实验吻合）

### 2.2 位置追踪（diag_position_vs_feed.py 输出）

```
热源布局:
  src[0]: pos=[70, 50, 50]  strength=5.0  radius=20
  src[1]: pos=[30, 70, 40]  strength=3.5  radius=15
  src[2]: pos=[80, 20, 60]  strength=4.0  radius=18

身体初始位置: [50, 50, 50]
  → 到 src[0] 距离 = 20.001 (刚好在边界外 0.001)
  → 到 src[1] 距离 = 22.36
  → 到 src[2] 距离 = 33.54

步  1-5:   dist=20.0, T_local=0.10, P_in=0.000 (在热源边界外)
步  6-140: dist<20,   T_local↑到0.71, P_in=0.050 (在 radius 内，满载)
步  150:   dist=31.1, T_local=0.10, P_in=0.000 (已漂出)
步  600:   dist=42.6, T_local=0.10, P_in=0.000 (单调远离)
```

---

## 三、根因

**热趋性关键期（critical period）内，进食窗口太短且不可重复。**

```
初始位置 [50,50,50]
    → 到最近热源 src[0] 距离 = 20.001 (radius = 20)
    → 几乎从一开始就在边界外

VitalOscillator 产生的随机漂移（步 1-5）碰巧把身体推进热源（步 6 起）
    → 进食 140 步
    → 漂移方向反转（VitalOscillator 相位）
    → 步 150 飞出半径，此后单调远离

饥饿驱动趋热反射（AGC×hunger）尚未通过 STDP 建立
    → 无有效归航机制
    → P_in 永久归零
```

**这不是能量参数问题，是"先有鸡还是先有蛋"的 bootstrap 困境：**
- 趋热反射需要 STDP 学习（需要时间）
- 学习需要 EnergyStore 充足（需要在热源附近）
- 但身体在学习成熟前就漂离了热源

---

## 四、排除项

- ❌ max_deposit_per_step 不是问题（实际进食从不触及上限，因为 dist>radius）
- ❌ P_withdraw 不是问题（0.010/步是合理的神经代谢成本）
- ❌ basal_drain 不是问题（0.0001/步 = 微不足道）
- ❌ consume_nearby 函数本身无误（正确实现了 (1-d/r) falloff）
- ❌ regenerate_sources 无误（热源在实验期间未耗尽）

---

## 五、修复方案

### 方案 A：初始位置内嵌（推荐，最小改动）

将身体初始位置从 [50, 50, 50] 改为热源内部，例如 [65, 50, 50]（在 src[0] 内，距离=5）。

```python
# world.py 或 variant_adapter.py 初始化处
body.position = [65.0, 50.0, 50.0]  # inside src[0] radius=20
```

**效果**：启动时立即进食，EnergyStore 在学习期保持充足，
趋热反射 STDP 有足够时间成熟。

**风险**：低。只改初始位置，不影响任何神经/物理参数。

### 方案 B：扩大世界热源覆盖率

在 World 初始化时增加热源密度或扩大 radius，使随机漂移无法完全逃出覆盖区。

```python
# 增加热源，或扩大 radius
HeatSource(pos=[50,50,50], radius=30, strength=4.0)  # 覆盖初始位置
```

**效果**：更稳健，不依赖初始位置巧合。

**风险**：改变世界物理，可能影响其他实验的可复现性。

### 方案 C（否决）：提高 max_deposit_per_step

不能解决根本问题（dist > radius → T_local = background → P_in = 0）。

---

## 六、验证协议

修复后运行：
```bash
python -X utf8 nexus_v1/tests/diag_position_vs_feed.py
```

验收标准：
- 步 1-5000 内 P_in > 0 持续出现
- fill 在 5000 步后 > 0.4
- 预计耗尽时间 > 200k 步（或正平衡）

---

## 七、后续

修复代谢壁后，下一步是运行完整 500k 步验证，确认：
1. 趋热反射能在 fill 充足期内 STDP 成熟
2. 生物体实现自持进食（正反馈闭环完成）
