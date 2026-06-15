# 拟真神经链路实验裁决

## 链路本身有效

```
4种配置全部成功:
  realistic     (delay=5,  p=0.3, atten=0.85): 33/40 结晶
  fast_reliable (delay=2,  p=0.7, atten=0.95): 33/40 结晶
  slow_unreliable (delay=12, p=0.15, atten=0.6): 33/40 结晶
  no_link       (delay=0,  p=1.0, atten=1.0):  33/40 结晶
```

**延迟和衰减不是障碍**——因为 fruit 的 trace 寿命 (~920 ticks) 远大于链路延迟 (5-12 ticks)。信号有足够的时间窗口到达。

链路自身通过 STDP **自我增强**: 权重从 0.5 → 0.998 (拟真) / 0.790 (慢链路)。

---

## 发现的关键问题: 同步信号饱和

```
学习阶段:   sync = 1.000  ← 预期: 高
巩固阶段:   sync = 1.000  ← 预期: 低, 但实际也是高!
休息阶段:   sync = 1.000  ← 预期: 极低, 但实际也是高!
```

**convergence_matrix 对所有共激活都响应——不区分高对比和低对比。**

```
学习: z_t = [0.9, 0.9, 0.9, 0.1, 0.1, 0.1, 0.1, 0.1]
      → 前3个强共激活 → co_strength = 0.81

巩固: z_t = [0.3, 0.3, 0.3, 0.3, 0.3, 0.3, 0.3, 0.3]
      → 所有8个共激活 → co_strength = 0.09
      → 但 28 对配对 × 0.09 = 累积到很高!
```

**温和的均匀信号也产生大量弱共激活 → 累积后仍然超过阈值 → 第三因子永远开启。**

> [!WARNING]
> **这意味着：简单地把 convergence_node 的输出连到 fruit capture 是不够的。**
> 
> 需要一个**对比度门控**: 只有信号分布的方差高时，同步才算"有意义"。
> 这就是 Park et al. 中 "error trial vs correct trial" 的区别:
> - Error trial: 部分 CF 强放电 → 高方差 → 高同步
> - Correct trial: 均匀放电 → 低方差 → 低同步

---

## 修正: 加入对比度门控

```
当前:
  sync = max(convergence_strength) × 100    [只看强度]

修正:
  contrast = std(z_t_activations)            [信号方差]
  sync = max(convergence_strength) × contrast × 100
  
  学习:  contrast = std([0.9, 0.9, 0.1, 0.1...]) ≈ 0.4  → sync 高
  巩固:  contrast = std([0.3, 0.3, 0.3, 0.3...]) ≈ 0.05 → sync 低
```

**对比度 = 信号在 z_t 空间中的"选择性"。**
高选择性 (部分维度强) = 有信息的输入 = 应该学习。
低选择性 (全部温和) = 噪声 = 不应该学习。

---

## 与小脑的对应

```
项目中            小脑            功能
─────────         ─────────       ─────────
convergence       CF 同步性       检测多信号共激活
contrast gate     error signal    区分 error vs correct
sync × contrast   MLI2 激活       门控第三因子
fruit capture     synaptic tag    标记→捕获→结晶
                  + capture
```

Park et al. 中 MLI2 不是简单地检测"CF 在放电"——
而是检测"CF 的放电模式是**异常的**（同步程度超出预期）"。

> [!IMPORTANT]
> **在 T/O/P/R/Xin 框架中：**
> 
> 第三因子 = **Xin 的对比度加权同步性**
> 
> ```
> third_factor = convergence_strength × contrast(z_t) 
>              = synchrony × information_content
> ```
> 
> 纯同步不够 (温和信号也同步)。
> 纯信息不够 (单个强信号无同步)。
> **必须两者兼备: 多个信号同时传递高信息量 = 真正的学习信号。**

---

## 完整链路设计 (修正后)

```
encoding.z_t neurons
       │
       ├─── contrast = std(activations)     [信号方差]
       │
       ├─── convergence_matrix[a][b]         [共激活检测]
       │         │
       │         ▼
       │    convergence_node.strength        [同步强度]
       │
       ▼ 乘法门控
  gated_signal = convergence × contrast
       │
       ▼ AxonalLink (delay=5, p=0.3, atten=0.85)
  [轴突传导: 延迟 + 随机释放 + 衰减]
       │
       ▼ DendriticIntegrator (τ=8, threshold=0.15)  
  [树突整合: 时间求和 + 阈值]
       │
       ▼ STDP (链路自身可塑性)
  [使用增强, 不用衰减]
       │
       ▼ try_activate_fruit(third_factor)
  [fruit capture: 捕获 or 衰减]
       │
       ├── capture → crystal (结构化)
       └── decay → dissolution (遗忘)
```
