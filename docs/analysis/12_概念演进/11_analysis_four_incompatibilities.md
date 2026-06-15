# 四个关键不兼容的代码级详解

---

## 1. P/R/Xin 测度: 二元 vs 连续

### 设计要求

```
每个信息块上有:
  ρ = (p_c, p_b, r_c, r_b, m_b, x, u)
  
  p_c + p_b + r_c + r_b + m_b + x + u = 1
  
  含义:
  "这个信息 35% 被 P 核心锚定, 25% 在 P 边沿被吸收,
   15% 被 R 反压挑战, 10% masking 过渡, 10% Xin 残余, 5% 未解决"
```

### 代码实际做的

[hebbian_circuit.py L1432-1435](file:///D:/cell-cc/Morphosphere_v37_0_native_runtime_prototype_flat_complete/morphosphere_v2pp/engines/hebbian_circuit.py#L1432-L1435):
```python
# P = max flow path, R = runner-up
cycles.sort(key=lambda c: c[0], reverse=True)
self._p_circulation = cycles[0][1]          # List[str] 或 None
self._r_circulation = cycles[1][1] if len(cycles) > 1 else None  # List[str] 或 None
```

[hebbian_circuit.py L1056](file:///D:/cell-cc/Morphosphere_v37_0_native_runtime_prototype_flat_complete/morphosphere_v2pp/engines/hebbian_circuit.py#L1056):
```python
self._xin_tensions: Dict[str, float] = {}  # bundle_id → 标量
```

### 差距逐点

```
设计                          代码
─────────────────────────    ─────────────────────────
ρ 是 7 分量向量              没有 ρ 向量
p_c = 0.35 (连续比例)        P = [bundle_A, bundle_B] (路径列表) 或 None
r_c = 0.15 (连续比例)        R = [bundle_C] (路径列表) 或 None
m_b = 0.10 (masking 占比)    没有 masking 分量
x = 0.10 (残余占比)          xin_tension = 0.37 (标量, 不是比例)
u = 0.05 (未解决占比)        没有 unresolved 分量
sum = 1.0                    没有归一化约束

P 和 R 可以同时存在          ✅ (但只是有/无, 不知道各占多少)
P band 和 P core 区分        ❌ 没有
R band 成核判定              ❌ 没有
```

### 具体后果

```
问题: 无法回答 "这个信息有多少比例被 P 稳定?"

代码能回答:
  ✅ "P 路径存在吗?" → 有/没有
  ✅ "P 路径经过哪些 bundle?" → [b1, b2, b3]
  ✅ "P 路径的流量是多少?" → circulation_measure

代码不能回答:
  ❌ "P 占总信息的比例是多少?" → 不知道
  ❌ "R 和 P 的竞争程度是多少?" → 不知道 (只知道谁是第一第二)
  ❌ "有多少信息完全未被解释?" → 不知道
  ❌ "Xin 是背景噪声还是真实异常?" → 不知道
```

---

## 2. 运动势: 计数器 vs 涌现

### 设计要求

```
运动势 = 信息在元单元组合中变更时,
         环流相对历史基线的衰减或增强。

它不是一个公式——它是一个涌现的结构性状态变化。
"势"不是一个数, 而是信息"倾向于往哪里走"。
```

### 代码实际做的

[MetaNeuron L194-197](file:///D:/cell-cc/Morphosphere_v37_0_native_runtime_prototype_flat_complete/morphosphere_v2pp/engines/hebbian_circuit.py#L194-L197):
```python
# potential 的更新 (在 activate 方法中):
self.potential += abs(self.activation) * 0.01
# 只增不减。它是一个里程表, 不是势。
```

[HebbianCircuit L1242-1245](file:///D:/cell-cc/Morphosphere_v37_0_native_runtime_prototype_flat_complete/morphosphere_v2pp/engines/hebbian_circuit.py#L1242-L1245):
```python
total_energy = sum(
    n.energy for layer in self.layers.values()
    for n in layer.neurons.values())
self._free_energy = total_energy - self._temperature * 0.1
```

### 差距逐点

```
设计                              代码
──────────────────────────       ──────────────────────────
环流基线比对                      potential = Σ|activation|×0.01
相对变化 (增强/衰减)               绝对累积 (只增不减)
方向性 (往哪走)                    没有方向
多组分 (P吸引+R排斥+Xin压力)      单一标量
从结构中涌现                       从公式中计算
用运动状态作为锚点                 没有运动状态锚点
```

### 具体后果

```
问题: potential = 47.3 意味着什么?

回答: 只意味着这个元单元"从出生到现在一共被激活了这么多次"。
     不意味着它倾向于往哪里走。
     不意味着它处于高张力还是低张力。
     不意味着它与任何运动状态的耦合程度。

free_energy = 8.2 意味着什么?
     只意味着"所有神经元的能量总和减去温度×0.1"。
     不意味着系统有多少余力做结构性工作。
     不意味着自由能在 P/R/Xin/U 之间如何分配。
```

---

## 3. Xin 守恒: 三个漏洞

### 设计要求

```
铁律: Xin 不能凭空出现或消失。
X(t₁) - X(t₀) = S_X + I_X - A_P - A_R - D_X - H_X

每一份 Xin 必须有来源和去向的账目。
```

### 代码中的三个漏洞

**漏洞 1: 果实激活时 Xin 归零**

[L797-798](file:///D:/cell-cc/Morphosphere_v37_0_native_runtime_prototype_flat_complete/morphosphere_v2pp/engines/hebbian_circuit.py#L797-L798):
```python
self.xin_dormant_fruit = None
self.xin_tension = 0.0     # ← Xin 归零, 没有记录去了哪里
```

```
xin_tension 从 0.73 变成 0.0。
这 0.73 去了哪里? 被 P 吸收了? 被 R 消解了?
没有记录。凭空消失。
```

**漏洞 2: 果实溶解时 Xin 丢失**

[L771-772](file:///D:/cell-cc/Morphosphere_v37_0_native_runtime_prototype_flat_complete/morphosphere_v2pp/engines/hebbian_circuit.py#L771-L772):
```python
if f["trace_strength"] < 0.01:
    self.xin_dormant_fruit = None  # ← 果实溶解, tension_at_creation 丢失
```

```
果实内储存的 tension_at_creation = 0.73 随果实消失。
shadow_memory 吸收了上下文快照, 但没有记录 Xin 的去向。
相当于: 一笔账目从账本上消失了。
```

**漏洞 3: Bundle 被剪枝时 Xin 丢失**

```python
# Bundle 被 should_prune() 判定为该剪除 → 整个 bundle 被删除
# bundle.xin_tension 随之消失
# 没有任何地方记录这份 Xin 被转移到了哪里
```

### 守恒审计

```
Xin 的来源:
  ✅ accumulate_xin(predicted, actual) → tension += (predicted - actual)
  来源清晰: 预测误差

Xin 的去向:
  ❌ 果实激活: tension → 0 (去哪了? 没记录)
  ❌ 果实溶解: tension_at_creation → 消失 (去哪了? 没记录)
  ❌ Bundle 剪枝: tension → 消失 (去哪了? 没记录)
  ❌ 没有 "被 P 吸收" 的记录
  ❌ 没有 "被 R 消解" 的记录
  ❌ 没有 "衰减/耗散" 的记录
  ❌ 没有 "进入 heat bath" 的记录

结论: Xin 的入口有记录, 出口全部丢失。
     系统无法回答 "Xin 总量是增加还是减少了?"
```

---

## 4. RLIS: 几乎空白

### 设计要求

```
RLIS = Relativistic Ledger Information Store
  独立外部存储系统, 记录:
  - 每个账本事件的时空坐标 (t, x, φ, τ, E)
  - Minkowski-like 间隔 s²_L
  - 自由能 7 分量拆分 (ΔF_Pc + ΔF_Pb + ... + ΔF_U)
  - Gamma 同步强度
  - Xin 从开始到结束的守恒
  - 审计光锥判定
  
  铁律: 不反写主线
```

### 代码实际

[L993-1004](file:///D:/cell-cc/Morphosphere_v37_0_native_runtime_prototype_flat_complete/morphosphere_v2pp/engines/hebbian_circuit.py#L993-L1004):
```python
def __init__(self, entropy_ledger_proxy=None):
    ...
    self._entropy_ledger_proxy = entropy_ledger_proxy
```

```
这就是 RLIS 在代码中的全部存在: 一个构造函数参数。

没有事件存储。
没有间隔计算。
没有自由能拆分。
没有同步强度。
没有守恒检查。
没有审计光锥。
```

### 后果

```
因为 RLIS 不存在, 以下功能全部缺失:

  ❌ 不知道系统整体的能量流向
  ❌ 不知道 Xin 是在增长还是在消耗
  ❌ 不知道两个事件是否在因果锥内
  ❌ 不知道 P/R/Xin 各消耗了多少自由能
  ❌ 不知道系统是在收敛还是在发散
  ❌ 没有外部审计视角

  系统在"盲飞"——没有仪表盘。
```

---

## 总结: 四个不兼容的关系

```
这四个不兼容不是独立的——它们互相锁定:

  P/R/Xin 没有连续测度
    → 无法计算自由能在各分量间的拆分
      → RLIS 没有数据可以记录
        → 无法检查 Xin 守恒
          → 系统在盲飞

  运动势只是计数器
    → 不知道信息倾向于往哪走
      → P/R 竞争没有方向
        → 无法区分运动类型
          → 所有信息被同等处理

修复顺序建议:
  1. 先修 P/R/Xin 连续测度 (把环流检测的输出归一化为 ρ)
  2. 用 ρ 开始记录 Xin 的来源和去向 (守恒)
  3. 把 ρ 的变化记入 RLIS (有了仪表盘)
  4. 运动势从 ρ 的时序变化中涌现 (不需要单独修)
```
