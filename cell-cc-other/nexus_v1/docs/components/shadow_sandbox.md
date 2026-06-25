# ShadowSandbox — 影子层

## 物理对应

- **BIO**: 默认模式网络 (DMN) / 小脑前向模型
- **EE**: 并行影子电路 (BCM 学习)

## 文件

[shadow_sandbox.py](../../components/shadow_sandbox.py)

## 功能

- 只读观测主层 Column 激活
- 内部 BCM 学习追踪统计
- 输出 → DA 神经元 (通过 shadow_to_da bundles)
- 每 10 步更新 (SHADOW_K=10)

## 当前状态

影子层为**读取-预测**模块，尚未升级为完整决策层。
未来路线: A8 影子层将作为 DC 处理器，驱动结构决策。

## 理论

- T006 §2: FEP action path (影子层 = DC 处理器)
- DC/AC 分离: 影子层处理 DC (结构), 主层处理 AC (权重)
