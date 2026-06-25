# V8 引擎合入计划

## 背景

`theLiying-main` 与本地 `nexus_v1` 存在 **1968 行差异，27 个文件**。  
这不是简单的"拉取"关系——**双方都有对方没有的东西**。

## 关键发现：双向分歧

| 组件 | 本地独有 | 远端独有 |
|------|---------|---------|
| `SpinalReflexArc` | ✅ | ❌ |
| `AutomaticGainControl` (Phase 4) | ✅ | ❌ |
| 4-patch Somatosensory chain | ✅ | ❌ |
| `LangevinNoise` (OU 过程) | ❌ | ✅ |
| `GuidedConstructionAuditor` | ❌ | ✅ (但为观测器) |
| Thermal encoding 非脉冲模式 | ❌ | ✅ (hebbian.py) |
| CRI 参数 q=0.02, R=1.0 | ❌ | ✅ (hebbian.py) |
| Memristor 负电阻 fix | ❌ | ✅ |
| LangevinNoise 注入 oto_x | ❌ | ✅ |
| T_local 自标定喂食 | ❌ | ✅ |

> [!CAUTION]
> **不能整体替换** `variant_adapter.py` / `hebbian.py`！  
> 远端版本**缺少** Phase 4 AGC、SpinalReflex、4-patch 体感链，  
> 整体替换会丢失已验证的本地工作成果。

---

## 方案：外科手术式合入（4 项 V8 精准移植）

### 目标：保留本地所有成果 + 加入 V8 的四个物理改动

---

### 项目 1：Memristor 负电阻 fix ⭐ 风险最低，收益确定

#### [MODIFY] [semiconductor.py](file:///D:/cell-cc/nexus_v1/components/semiconductor.py)

远端在 `resistance` 属性和 `conductance` 属性加了两处保护：

```python
# resistance: w_safe clamp
w_safe = max(0.0, min(1.0, self.w))
return self.r_min + (self.r_max - self.r_min) * (1.0 - w_safe)

# conductance: double-cap
g = 1.0 / max(resistance_val, self.r_min)
return min(g, 1.0 / self.r_min)
```

纯防御性修复，无行为副作用。

---

### 项目 2：LangevinNoise 组件（新文件）⭐ 风险零

#### [NEW] [langevin_noise.py](file:///D:/cell-cc/nexus_v1/components/langevin_noise.py)

直接复制远端文件，不修改任何现有代码。

---

### 项目 3：LangevinNoise 注入 variant_adapter.py ⭐⭐ 风险低

远端在 `variant_adapter.py` 中：
1. `import LangevinNoise`
2. `self._langevin = LangevinNoise()`
3. 在 `step()` 中：`eta = self._langevin.step(ecm_vestibular, dt)`，加到 `oto_x/y/z`

本地也有对 `oto_x/y/z` 的处理，需要在现有代码中**插入** Langevin 注入，不替换。

---

### 项目 4：Thermal Encoding 非脉冲模式 + CRI 参数 ⭐⭐⭐ 风险中等

远端 `hebbian.py` 有：

**A. `bc_current`: 0.02 → 0.005**（降低 Encoding 偏置，防止常驻饱和）

```python
bc_current=0.005,  # 本地是 0.02
```

**B. 新增 `_thermal_encoding_config()` 函数**（非脉冲，模拟量输出）

**C. CRI 参数**（远端 `cri_q` 名为 `spike_charge_q` = 0.02, `cri_r_leak` = 1.0）

> [!WARNING]
> 改变 `bc_current` 和 CRI 参数会影响所有热感受器的激活动态。  
> 需要在合入后**重新运行回归测试**确认无退化。

---

## 不合入的远端内容

| 远端内容 | 原因 |
|---------|------|
| `GuidedConstructionAuditor` | 纯观测器，非必要，引入依赖 |
| `soma_to_da bundles` 删除 | 本地保留，不删 |
| T_local 自标定喂食 | 影响能量平衡，需单独评估 |
| `variant_adapter` 大块重构 | 本地 Phase4/SpinalReflex 结构已稳定 |

---

## 执行顺序

```
Step 1: semiconductor.py fix          (5 min, 15行)
Step 2: 复制 langevin_noise.py        (2 min, 新文件)
Step 3: variant_adapter.py 注入 Langevin (20 min)
Step 4: hebbian.py bc_current 调整    (10 min)
Step 5: 运行回归测试套件               (5 min)
Step 6: 若通过 → 运行 diag_agc_validation
Step 7: 若通过 → 记录 EXP-022 结果
```

---

## 验证计划

### 自动测试
```
python -m pytest nexus_v1/tests/test_regression.py -v
python -m nexus_v1.tests.diag_agc_validation
```

### 回归基线
- T2.2 编码选择性必须保持 (若 bc_current 降低会影响此项)
- T4 权重比/交叉上限必须通过
- AGC 5/5 必须保持

---

## 开放问题

> [!IMPORTANT]
> **你是否要合入项目 4（bc_current + CRI）？**  
> 这是最有争议的改动：  
> - 合入后：热感受器动态改变，回归风险中等，但可能改善 STDP 学习  
> - 不合入：只做防御性 fix（memristor + Langevin），风险极低

请确认是否：
- **完整合入**（全部 4 项）  
- **保守合入**（仅项目 1+2+3，跳过 bc_current/CRI 参数变更）
