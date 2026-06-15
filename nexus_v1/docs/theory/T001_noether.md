# T001: Noether 守恒定律

> 状态: ✅ 已验证 (500k steps, 0 violations)

## 理论

系统的每一个连续对称性对应一个守恒量 (Noether 1918)。

在 nexus_v1 中实施的三条守恒律：

### 能量守恒 (时间平移对称)

$$E_{in} = E_{out} + E_{leak}$$

- $E_{in}$: 输入电流 × 膜电压
- $E_{out}$: 突触传输消耗
- $E_{leak}$: RC 膜泄漏

### 电荷守恒 (KCL)

$$\sum I_{in} = \sum I_{out}$$

每个节点的电流总和为零。

### Landauer 信息热力学

$$Q/\text{bit} \gg kT \ln 2$$

每个不可逆计算操作释放的热量必须大于 Landauer 极限。

## 代码位置

| 文件 | 行 | 功能 |
|---|---|---|
| circuit/noether_probe.py | 全文件 | 守恒审计器 |
| circuit/bundle.py | L399-415 | Xin 守恒账本 (produced - consumed) |
| components/entropy_ledger.py | 全文件 | 结构事件熵审计 |

## 验证方法

- 回归测试 T1.1 (violations == 0)
- 回归测试 T1.2 (energy balance < 0.01)
- 回归测试 T1.3 (Landauer bound = True)

## 修改历史

| 版本 | 变更 |
|---|---|
| v1.5.0 | Noether probe 初始实现 |
| v1.6.0 | 添加 H_struct, H_flow, Ω 结构熵 |
