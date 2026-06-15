# 对应关系断裂分析

## 你的原始设计

```
每个细胞 ↔ 一个传输管线束 ↔ 半个 T/O/P/R/Xin 元数组

N=30 个粒子 → 30 个管线 → 15 个 T/O/P/R/Xin 单元
```

**规模严格挂钩**: 上层随底层变化而变化。

## 现在的实际状况

```
底层 (PracticeEngine):
  N=30 个粒子 (particles)
  每个粒子有: 位置(x,y,z), 速度(vx,vy,vz), 膜电位(V_m), 应力(stress), 脉冲(spike)
  = 每个粒子约 10 个独立信号

中间层 (_compute_sensory):
  30 个粒子 → 聚合成 7 个标量:
    spectral_H  = 所有粒子 V_m 的标准差
    fano_H      = V_m 的 Fano 因子
    synchrony_H = 脉冲的同步率
    gradient_H  = 应力的平均值
    sparseness_H = 1 - 同步率
    autocorrelation_H = 速度一致性
    energy_H    = 总动能

  ↑↑↑ 30个粒子的个体身份在这里被彻底抹掉了 ↑↑↑

上层 (HebbianCircuit):
  6 个信号神经元 (sig_mean, sig_std, ...)
  7 个 z_t 神经元 (transition, drift, ...)
  7 个 column 神经元

  这 6+7+7=20 个神经元与粒子数量完全无关
```

## 断裂在哪里

```
粒子 1 ─┐
粒子 2 ─┤
粒子 3 ─┤     聚合
  ...    ├──────→  7 个标量  ──→  6 个信号  ──→  7 个 z_t
粒子 28 ─┤     (sum/mean/std)
粒子 29 ─┤
粒子 30 ─┘
         ↑
         │
     这里: 30→7
     所有个体信息被压成统计量
     第 1 个粒子和第 30 个粒子不再可区分
```

**`_compute_sensory()` 就是断裂点。** 它把 30 个粒子的完整信息压缩成 7 个标量。

## 代码证据

```python
# practice_engine.py L870-911
def _compute_sensory(self):
    particles = self.system.particles
    n = len(particles)

    # 所有粒子的 V_m 被平均:
    v_means = [p.V_m for p in particles]
    v_avg = sum(v_means) / n          # ← 30→1
    v_std = ...                        # ← 30→1

    # 所有粒子的脉冲被统计:
    recent_spikes = sum(1 for p in particles if p.spike)
    synchrony = recent_spikes / n      # ← 30→1
    
    # ...最终返回 7 个标量
```

```python
# hebbian_circuit.py L3385-3397
# 电路根据 SIGNAL_FEATURES 建造, 与粒子数无关:
feature_names = ["sig_mean", "sig_std", "sig_peak_rate",
                 "sig_temporal_d", "sig_sync", "sig_range"]  # 6 个, 固定
cost_names = ["transition", "drift", "gamma_desync",
              "xin_residual", "potential_disp", "churn", "magnitude"]  # 7 个, 固定
```

**6 和 7 是硬编码的, 与 N=30 没有任何函数关系。**

## 为什么会断裂

```
你的原始设计:
  每个细胞 → 自己的管线 → 自己的 T/O/P/R/Xin 槽位
  = 信息是按细胞组织的

引入外部数据 (Allen Brain) 后:
  外部数据格式: n_cells × n_timepoints 的矩阵
  但进入系统时被转成: 统计特征 (mean, std, sync, ...)
  = 信息按统计量组织, 不按细胞组织

  → 电路被重建为匹配统计量的结构 (6→7)
  → 细胞级别的对应关系丢失
  → 规模挂钩断裂
```

**根本原因: 外部数据适配器把 per-cell 信息压缩成了 aggregate 信息。**
电路跟着 aggregate 信息走, 就与细胞规模脱钩了。

---

## 恢复方案的思路

要恢复 1:1:0.5 的对应关系, 需要:

```
选项 A: 恢复 per-cell 管线

  粒子 1 → signal_cell_1 → zt_cell_1 → T/O/P/R/Xin_cell_1
  粒子 2 → signal_cell_2 → zt_cell_2 → T/O/P/R/Xin_cell_1
  ...
  粒子 30 → signal_cell_30 → zt_cell_30 → T/O/P/R/Xin_cell_15
  
  encoding 层: 30 个信号神经元 + 30 个 z_t 神经元 = 60
  column 层: 30 个
  总计: 90 个神经元 (现在是 20 个)

选项 B: 保持聚合, 但加入 per-cell 索引层

  底层: 30 个粒子 → 7 个统计量 (现有路径, 保留)
  新增: 30 个粒子 → 30 个 cell_index 神经元 (保留个体身份)
  上层: 7 个 z_t + 30 个 cell_index → column

  相当于: "知道发生了什么 (z_t)" + "知道是谁 (cell_index)"

选项 C: 动态规模——电路跟随粒子数自动缩放

  build_circuit(signal_transform, n_cells=N)
  → 自动创建 N 个信号神经元, N 个 z_t, N/2 个 T/O/P/R/Xin
  → 外部数据变了, N 变了, 电路自动重建
```

> [!IMPORTANT]
> **不管选哪种, 核心修正是同一个:**
> 
> **`_compute_sensory()` 不能只输出 7 个聚合标量。**
> 它必须保留 per-cell 的信息, 或者至少保留一个索引,
> 让上层知道 "第 i 个粒子" 和 "第 j 个粒子" 是不同的实体。
> 
> 没有这个, 系统永远只知道 "群体在做什么",
> 不知道 "谁在做什么"。
