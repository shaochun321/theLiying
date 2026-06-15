# 全局数学公式 — G-001 v2.0 草案

> 日期: 2026-05-24
> 版本: v2.0 (草案, 待审批后合并入 G-001)
> 基础: G-001 v1.0 (保留全部), C-001~C-005, Paper 1~3
> 性质: **扩展层**, 不替代 G-001 v1.0 中的任何公式
> 决议: activation 取自 MOSFET.conduct(V), 含亚阈值电流

---

## §0 公理

### §0.1 双层公理

项目遵循客观/主观双层分离:

**公理 Ω-1 (客观层不显式)**:
项目(生物体)的所有计算和学习只通过输入流 {a_i(t)} 进行。
项目不访问客观层的任何变量(position, mass, temperature_at, v_threshold 等)。

**公理 Ω-2 (客观层参与计算)**:
客观层的物质结构和物理定律参与产生输入流 {a_i(t)}。
输入流的统计特性由客观层的物理过程决定。

**公理 Ω-3 (主观层自生)**:
项目的空间、时间、因果知识只能从输入流的关联结构中生成(C-004)。
ds², ν, Xin 都是主观构建, 不是客观属性的映射。

```
推论:
  任何"修正"都分为两类:
    客观层修正 = 改变物质结构/物理属性 → 改变输入流的统计特性
    主观层修正 = 改变关联学习规则 → 改变知识构建方式
  不存在"从主观层修正客观层"的操作。
```

### §0.2 T/O/P/R/Xin 公理

**公理 Ψ-1**: T/O/P/R/Xin 是构建者的组织框架(C-005), 不是系统的运行规则。
**公理 Ψ-2**: Xin 是验证器。递归衰减是正确行为。信息在瞬态结构中。
**公理 Ψ-3**: 已固化递归链具有屏蔽性。新 T 驱动新 O/P/R, 不摧毁旧链。

---

## §1 客观层物理扩展

### §1E.1 激活函数 (决议)

$$
a = \text{MOSFET.conduct}(V)
$$

含亚阈值:
- 超阈: $a = g_m (V - V_{th})$
- 亚阈: $a = g_m \cdot nV_T \cdot (e^{(V-V_{th})/(nV_T)} - 1)$
- 两区域连续拼接, V=V_th 时 a=0

基线活动: 即使 V < V_th, 亚阈值电流 > 0 → 非零基线

### §1E.2 热介质 (Paper 3 原理迁移)

$$
\frac{\partial E_i}{\partial t} = \kappa \sum_{j \in \mathcal{N}(i)} \frac{E_j - E_i}{d^2} - \lambda E_i
$$

穿透深度: $L_{pen} = \sqrt{\kappa / \gamma}$

参数 $(m, k, \gamma)$ 在 nexus_v1 尺度下独立标定。

### §1E.3 阻抗匹配

$$
T = \min\left(1, \frac{2 Z_{body}}{Z_{body} + Z_{medium}}\right), \quad Z = \frac{\sqrt{km}}{d^2}
$$

### §1E.4 CPG 相位门控

$$
g(t) = \text{clamp}((a_A - a_B) \cdot \alpha + 0.5, 0, 1)
$$

### §1E.5 P→R 客观层闭合

$$
|\xi| \xrightarrow{} c_{DA} \xrightarrow{} \alpha_{lr} \xrightarrow{} \Delta w
$$

同步门控: $g_{sync} = \min(1, \sum a_{bind} / \theta_{sync})$

---

## §2 主观层构建 (修订)

### §2.1 激活偏移

$$
\delta a_i = a_i - \bar{a}_i, \quad \bar{a}_i = \text{EMA}(a_i, \tau)
$$

### §2.2 空间测度

$$
ds^2 = \sum_{i,j} g_{ij} \cdot \delta a_i \cdot \delta a_j, \quad g_{ij} = w_{cross}(i,j)
$$

对称性: BCM 统计对称, 不强制。正定性: 半正定, 退化有物理意义。

### §2.3 运动势 (扩展)

$$
\nu_p = d\rho_p / dt
$$

旋度: $\omega_{ij} = \frac{1}{2}(\Delta\nu_i/\Delta a_j - \Delta\nu_j/\Delta a_i)$
散度: $\nabla \cdot \nu = \sum_i \Delta\nu_i / \Delta a_i$

### §2.4 收缩度

$$
\kappa = \frac{\sum g_{ij} \delta a_i \delta a_j}{\sum (\delta a_i)^2}
$$

### §2.5 Xin (定位修订)

公式不变: $\xi = \hat{y} - a(t)$

定位: 验证器, 非定量驱动力。递归衰减是正确行为。

---

## §3 ds²/ν 主方法映射表

| 理念 | ds²/ν 表达 |
|------|-----------|
| MOSFET 阈值 | 度规退化边界 |
| STDP/BCM | 度规更新规则 |
| Xin | 测地线偏差 |
| 环流 μ | 度规空间体积流 |
| κ | 度规缩减 |
| PNN | 度规冻结 |

---

## §4 约束层 (理论预期)

- 坐标无关: ds² 不引用外部坐标
- 近似守恒: 稳态时 A < 0.001
- 近场限制: 热穿透有限
- 阻抗上限: T < 1

---

## §5 问题盘点 (21项)

架构级: A1(P→R断裂), A2(基线=0), A3(热解析), A4(body无物理), A5(第三因子)
度规级: M1(|a|→δa), M2(旋度), M3(κ公式), M4(activation定义→已决)
尺度级: S1(前庭衰减), S2(Motor同步), S3(热穿透)
理论级: T1(递归链判别), T2(PNN解冻), T3(fruit), T4(Noether), T5(变分)

---

## §6 与 G-001 v1.0 差异表

| v1.0 | 状态 | 变化 |
|------|------|------|
| §1 RC-MOSFET | 保留 | +§1E.1 亚阈值 |
| §1.2 max(0,V-V_th) | **修订** | → MOSFET.conduct(V) |
| §2 突触束 | 保留 | +§1E.5 P→R |
| §2.5 Xin | 保留公式, 修订定位 | 验证器 |
| §3 环流 | 保留 | +旋度散度 |
| §4 影子层 | 保留 | κ修订 |
| §5 ECM/VR | 保留 | 无变化 |
| (无) | 新增 | §0公理, §1E客观层, §4约束层 |
