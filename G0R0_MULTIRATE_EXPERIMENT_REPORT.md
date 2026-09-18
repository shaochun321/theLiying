# G0R0_MULTIRATE_EXPERIMENT_REPORT — 调度实验 + 不变性攻击 + replay/bridge

日期：2026-09-19
脚本：`research/g0_reconnect/r0/{g0r0_scheduler,g0r0_invariance,g0r0_replay_bridge}.py`
数据：`research/g0_reconnect/r0/data/`

---

## 一、调度策略实验（§7-§13；T_phys=60 s，N_sub=1000）

全状态向量 E_state（**FIRST_RESULT 原样保留**）：S0-A=0.115 /
S1-A=0.105 / S1-A@dt_B=0.1=0.109——原 D4 判据 FAIL（比=1.037）。
逐分量分解定位根因：

| 层 | 分量 | 误差 | 结论 |
|---|---|---|---|
| Tier-1 接口层 | L1 activation, HC pre_trace | dt_B=1: **2.48e-3** → dt_B=0.1: **2.51e-4**（比=0.101，一阶收敛） | **MULTIRATE_CONVERGES（接口层）** |
| Tier-2 振荡层 | ensemble×8+collector | 0.36~1.49（O(1)，不随 dt_B 降） | `G0_OSCILLATOR_PHASE_SENSITIVITY`——ensemble/collector 自持极限环（先证=exp_P2A1b_3 600-700 步振荡）相位失相干；对**任何**边界采样策略不可收敛=G0 内部性质，非调度器缺陷 |

策略登记：S1 优于 S0（接口层）；S1 因果性=需下一样本（live=1 样本滞后）；
S2 为参考。B 桥：**真实秒制下 u_B 峰 0.274，u>0.05（L1 钳位起点）占
33.3% 子步 ⇒ `B_BRIDGE_L1_SATURATION`**（B1@S1 与 B1@S2ref 被钳成逐位
相同=饱和假象；g 量级源于 step 制，重标属 occurrence revalidation，
本轮 §20/§32 禁调）。

## 二、dt_G 不变性攻击（§17-§19；dt_G∈{2,1,0.5} ms，T_phys=60 s 恒定）

- Tier-1：err(2↔1ms)=0.110 → err(0.5↔1ms)=0.091 收敛 ✓（全向量 0.154/
  0.142 FIRST_RESULT 登记，振荡层同因）。
- **RC 在体**：HC trace τ = 6.4201 / 6.4202 s（两档 dt_G，5 位不变）✓。
- **延迟实证**：`delay_steps=5` 两档 dt_G 均 5 步到达 ⇒ 物理延迟 5.0 vs
  2.5 ms 漂移 ⇒ `DELAY_STEP_COUPLING` 实证（隐性：G0 核心链 delay=0）。

## 三、剂量审计（§29-§30）

| 路径 | E_proxy 相对细参考 |
|---|---|
| multirate S1-A (1ms) | **1.0010**（无复制 ✓） |
| B0 / B1 | 0.996（ZOH 无 1000× 复制 ✓） |
| **旧 1:1 耦合** | **0.00101**（≈1/1000——§40 负结果定量化） |

## 四、multirate replay + Twin-2 + B bridge（§25-§28）

- **Replay**：live（World 步进与 G0 子步消费交替）vs 纯 timestamped 帧
  重建——G0 状态轨迹**逐位一致**。
- **Twin-2**：边界逐位相同至样本 21；G0 状态前 20 秒逐位相同、分叉后
  才异 ⇒ 无 `CROSS_LAYER_HIDDEN_LEAK`。
- **B bridge 五场景**（v1 等价/v2 普通/强耗散/多源/twin 变体）：全部
  finite/L1≤钳位/状态连续 ⇒ PASS；**occurrence=1×5（只登记不判定**，
  对比 T1-B 旧 1:1 smoke 的 occ=0——多率真实速率输入首次驱动 closure
  完整走完 trigger→exit→rearm，为 revalidation 提供正向信号）。

## 复现入口

```bash
PYTHONIOENCODING=utf-8 python research/g0_reconnect/r0/g0r0_time_audit.py
PYTHONIOENCODING=utf-8 python research/g0_reconnect/r0/g0r0_scheduler.py
PYTHONIOENCODING=utf-8 python research/g0_reconnect/r0/g0r0_invariance.py
PYTHONIOENCODING=utf-8 python research/g0_reconnect/r0/g0r0_replay_bridge.py
PYTHONIOENCODING=utf-8 python research/g0_reconnect/r0/g0r0_final_qualification.py
```
