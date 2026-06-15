# Walkthrough: 基因隔离手术 + F6 信息热寂熔断

## 变更清单

### 1. `deepcopy` 宪法修正（三处）

| 文件 | 函数 | 行 | 变更 |
|------|------|------|------|
| [neuron.py](file:///d:/cell-cc/nexus_v1/components/neuron.py#L672-L674) | `Neuron.split()` | L672-674 | `copy` → `deepcopy` |
| [bundle.py](file:///d:/cell-cc/nexus_v1/circuit/bundle.py#L646-L651) | `SynapticBundle.sprout()` | L646,651 | `copy` → `deepcopy` |
| [hebbian.py](file:///d:/cell-cc/nexus_v1/circuit/hebbian.py#L988-L1004) | `_rewire_after_split()` | L988,1004 | `copy` → `deepcopy` |

**修复的物理缺陷**：
- `channels: List[ChannelConfig]` — 母子共享同一离子通道列表（定域性违反）
- `silent_snapshot: dict` — 子代休眠状态覆写母本记忆（**活跃 bug**）

### 2. F6 信息热寂熔断

文件: [fuse.py](file:///d:/cell-cc/governance/fuse.py)

新增检测条件：
```python
if k_ema < 1e-6 and Σ|ξ| < 0.01:  # sustained 5000 steps
    → F6: INFORMATION_HEAT_DEATH
```

**新增字段**：`k_ema_min`, `xin_abs_min`, `f6_confirm_steps`, `_f6_dead_counter`

**监控逻辑**：
- 读取 `shadow_sandbox._k_ema`（影子层自由能）
- 计算 `Σ|b.config.xin_tension|`（全局预测误差）
- 双零持续 5000 步 → 触发熔断

## 验证结果

```
parent ch[0].v_th = 0.3      ← 母本未被污染 ✅
child ch[0].v_th = 999.0     ← 子代独立修改 ✅
deepcopy isolation CONFIRMED

parent snapshot: {'w': 0.5}           ← 母本未被污染 ✅
child snapshot:  {'w': 0.5, 'injected': True}  ← 子代独立 ✅
sprout deepcopy isolation CONFIRMED

F6 thresholds: k_ema_min=1e-06, xin_abs_min=0.01, confirm=5000 ✅
Fuse import OK
```

## 未执行项（继续观察）

- **体感饱和修复**：TRP 通道电导模型改造（根因修复），留给后续 EXP-016c 实施
- **体感法网收编**：`get_all_neurons/bundles` 纳入 soma 神经元
- **张力神经搭桥**：soma bundles 接入 `_apply_xin_tension`
