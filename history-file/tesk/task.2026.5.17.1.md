# Task: 实践层赫布超图分化

## Phase 1: 物理基础
- [x] QuantitySource (3个固定点源: 声/热/光)
- [x] 衰减律: 声1/r, 热1/r², 光1/r² (ratio=1.000 验证)
- [x] 力臂计算 + d|L|/dt
- [x] 量源熵账本 (v40_quantity_source_ledger)

## Phase 2: 前庭层
- [x] 前庭层 (7+3=10 neuron): lever/dlever/integ × 3源 + angular_vel
- [x] IntegratorColumn: leaky integration + Weber-Fechner log 压缩
- [x] CPG 泄漏矫正 (cerebellum analog)
- [x] 积分器熵账本 (v40_integrator_ledger)
- [x] 激活值归一化 + clamp [-1,1]

## Phase 3: 环路闭合
- [x] integ → motor 束 (w=0.08, 环路闭合)
- [x] integ → encoding 束 (w=0.04)
- [x] μ(G) 检测更新 (基于积分器持续状态)
- [x] μ(G) = 1.201 ✅

## Phase 4: 实践皮层分化
- [x] practice_cortex 层 (空初始化)
- [x] _practice_convergence_matrix (motor+vestibular 共激活)
- [x] _detect_practice_convergence() 方法
- [x] 环流门控: μ(G)>0.1 + integ 神经元必须参与
- [x] px_ 结晶: 3个 (px_dlev_inte, px_inte_move, px_inte_inte)
- [x] 双向束: px_→motor (w=0.05) + px_→encoding (w=0.03)
- [x] 遥测报告

## 降级记录
- [x] 11项降级全部记录在 docstring 中
- [x] 新增3项: SMA→M1→脊髓→单层, 皮层柱→单px_, 基底节→环流阈值

## 验证
- [x] practice_engine.py 自测 ✅ PASS
- [x] 500 tick 管线 exit 0
- [x] 分辨力 cos=-0.333 ✅ YES
- [x] 物理衰减 ratio=1.000
- [x] 熵账本可审计
- [x] px_ 结晶语义可解释
