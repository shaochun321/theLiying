# SynapticBundle — 突触束 (超边)

## 物理对应

- **BIO**: 突触丛 (多源→多靶连接)
- **EE**: Memristor matrix + delay buffer + temporal coupler array

## 文件

[bundle.py](../../circuit/bundle.py)

## 功能

连接源神经元到靶神经元的超边。每对(源,靶)有一个 Memristor。
承载 propagate → learn → Xin → Fruit 的完整生命周期。

## 关键类

| 类 | 功能 |
|---|---|
| BundleConfig | 参数化配置 (90+ 字段) |
| SynapticBundle | 突触束主类 |

## 核心方法

| 方法 | 功能 |
|---|---|
| propagate() | 信号前向传播 (T-phase) |
| apply_to_targets() | 注入电流到目标 (经 coupler) |
| learn() | STDP/BCM/Hebbian 学习 |
| compute_xin() | 预测-比较→累积 Xin 张力 |
| update_fruit() | Fruit 状态机更新 |
| sprout() | 母本分化 (创建子 bundle) |
| should_prune() | 修剪判定 |

## 理论

- T001: Xin 守恒账本 (produced - consumed, checkpoint 每 10k 步)
- T002: 三种学习规则 (STDP/BCM/Hebbian+decay)
- T003: Fruit 生命周期 (∅→dormant→mature→expand/contract)

## 关键参数

| 参数 | 含义 | 来源 |
|---|---|---|
| synapse_gain | 突触增益 | 0.7-5.0, 按层设定 |
| fruit_threshold | Fruit 创建阈值 | 0.5 |
| XIN_LEAK_TAU | Xin 泄漏时间常数 | 1000s |
| MATURATION_TICKS | 果实成熟所需 tick | 500 |
| DA_MATURE_THRESHOLD | DA 门控阈值 | 0.15 |

## 修改历史

| 版本 | 变更 |
|---|---|
| v1.0 | 基础 propagate + STDP |
| v1.3 | 添加 Xin + Fruit 状态机 |
| v1.5 | 添加 C4 驻波检测 (ZCR) |
| v1.6 | C2 cross weight ceiling + sprouting filter |
| v1.7 | **移除 SW gate** (ZCR 双峰, 果实首次工作) |
