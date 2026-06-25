# T005: T·S·I 框架 — 时间-空间-信息

> 状态: ❌ P×H 否定，框架待修正

## 原始假说

$$T \cdot S \cdot I = \text{const}$$

其中 T=时间测度, S=空间测度, I=信息量。
类似 Bekenstein bound: $I \leq \frac{2\pi R E}{\hbar c \ln 2}$

## 当前代理变量

| 量 | 公式 | 来源 |
|---|---|---|
| ν (运动势) | EMA(dK/dt, α=0.01) | variant_adapter.py L533 |
| ν_xyz | EMA(m·v_i·a_i, α=0.01) | variant_adapter.py L541 |
| P_ν (偏振) | max(\|ν_i\|) / Σ\|ν_i\| | variant_adapter.py L548 |
| H_struct | -Σ p_i log p_i (权重分布熵) | noether_probe.py |
| H_flow | -Σ q_i log q_i (电流分布熵) | noether_probe.py |

## 实验结果

### P_ν × H_flow "守恒" — 已否定

三对照实验 (v1.6.0):
1. 随机权重: 仍然"守恒" → 统计伪发现
2. 冻结权重: 仍然"守恒" → 不依赖学习
3. 零输入: 趋向常数 → 初始条件决定

**结论**: P_ν × H_flow 的稳定性是 EMA 平滑 + 有界变量的数学必然，不是物理守恒。

### FFT 频谱分析 (v1.7.0)

| 信号 | 基频 | 集中度 | 判定 |
|---|---|---|---|
| Xin axis | 0.49Hz | 81.4% | **周期性** (追踪输入) |
| Encoding | 0.49Hz | 20.9% | 准周期 |
| Motor | ~7Hz | 11.7% | 宽带 (输入频率消失) |
| ν EMA | 0.49Hz | 43.1% | 准周期 (EMA 恢复) |

## 前进方向

P×H 失败不代表 T·S·I 错——代理变量太窄。可能需要：
1. 从 Noether 定理的空间对称性直接推导
2. 用 B2 重整化群方法
3. 寻找更完整的代理变量组合

## 代码位置

| 文件 | 行 | 功能 |
|---|---|---|
| circuit/variant_adapter.py | L533-556 | A7 运动势计算 |
| circuit/noether_probe.py | H_struct/H_flow | 结构/流程熵 |

## 修改历史

| 版本 | 变更 |
|---|---|
| v1.6.0 | A7 初始实现 (raw dK/dt) |
| v1.6.0 | P×H 对照实验 → 否定 |
| v1.7.0 | ν EMA 平滑 (消除 Nyquist 伪峰) |
