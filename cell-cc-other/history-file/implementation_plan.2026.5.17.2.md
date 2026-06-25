# 赫布超图分化：运动皮层/实践层

## 现有机制 (encoding 层)

```
encoding 层内部:
  z_t neurons 共激活 → convergence_matrix 记录强度 →
  强度>阈值 → convergence_node 形成 →
  持续>50tick + 强度>0.01 → 结晶为 cx_ neuron →
  cx_ → column 层 (固化)
```

## 扩展到 motor-vestibular 空间

### Phase 1: 实践层收敛矩阵

在 motor + vestibular 层的神经元之间检测共激活：

```python
# 参与收敛检测的神经元:
practice_neurons = [
    # motor
    "move_x", "move_y", "move_z",
    # vestibular rates
    "dlever_acoustic", "dlever_thermal", "dlever_luminous",
    # vestibular integrators
    "integ_acoustic", "integ_thermal", "integ_luminous",
]

# 在 hebbian_circuit.py 的 maintain() 中:
# 与 encoding 的 convergence_matrix 并列
# 新增 _practice_convergence_matrix
```

### Phase 2: 实践皮层结晶

当 motor-vestibular 共激活模式持续时，结晶为 `px_` 神经元：

```
例：
  move_x 和 dlever_luminous 持续共激活
  → convergence node: "conv_mov_dle"
  → 持续 50+ tick, 强度 > 0.01
  → 结晶为 px_mov_dle neuron（在新的 practice_cortex 层）
  → 含义："向光源方向运动"的固化P
```

### Phase 3: 环流门控

只有参与活跃环流的模式才能结晶：

```
条件:
  convergence_strength > 0.01  AND
  age > 50 ticks  AND
  μ(G) > 0.1 (存在活跃环流)  AND
  at least one integ_* neuron in the pair (确保是运动-感觉闭环模式)
```

## 具体改动

### [MODIFY] hebbian_circuit.py

1. 新增 `_practice_convergence_matrix`
2. 在 `maintain()` 的 convergence 检测后，并行检测 motor+vestibular 共激活
3. 新增 `crystallize_practice()` 方法，与 `crystallize()` 并列

### [MODIFY] run_v40_integrated.py

1. 在 `build_signal_entropy_circuit()` 中新增 `practice_cortex` 层
2. px_ 结晶后创建 px_ → motor 和 px_ → encoding 的束
3. 遥测输出新增实践皮层报告
4. 结晶条件加入环流门控

### 降级记录

| 完整版 | 降级版 |
|---|---|
| 运动皮层 somatotopic 空间映射 | 平面收敛空间 |
| 层级化运动规划 (SMA→M1→脊髓) | 单层直接结晶 |
| 6层皮层柱微电路 | 单层 px_ 神经元 |
| 基底节选择门控 | 环流阈值门控 |

## 验证计划

1. `python engines/practice_engine.py` — 自测通过
2. 300 tick 运行 — 无崩溃
3. 500 tick 运行 — 应出现 px_ 结晶
4. 审计: px_ 的语义是否可解释 (e.g. move_x × dlever_luminous = "向光运动")
5. 环流 μ(G) 在结晶后应增加（更多结构化回路）

## 开放问题

> [!IMPORTANT]
> px_ 结晶后应该连接到哪里？
>
> 选项 A: px_ → motor (直接强化已学的运动模式)
> 选项 B: px_ → encoding (运动经验影响感知)
> 选项 C: 两者都 (双向)
>
> 生物学上是 C：运动皮层既投射到脊髓(运动执行)也回投到感觉皮层(传出拷贝)。
> 建议用 C，但需要确认。
