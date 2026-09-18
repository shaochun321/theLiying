# W1_HIDDEN_DYNAMICS_REPORT — World v2 隐藏因果动力学（M6 核心门）

日期：2026-09-18
脚本：`research/world_v2/w1_hidden_twins.py`
数据：`research/world_v2/data/{w1_hidden_twins.json, hidden_twin_pairs.csv}`

---

## 一、预登记阈值（§26 纪律：实验前冻结，未改动）

ε_B: ‖ΔY(t0)‖/RMS<1e-2；ε_X: ‖ΔX(t0)‖/RMS>0.2（X_W 含场节点+源剩余
能量，§2 定义）；ε_F: max‖ΔY⁺‖/RMS>5e-2。依据=v1 正对照数值尺度
（~1e-5/~1.5/~0.5），评判 B2。

## 二、Twin-1 场隐藏孪生（§26 一般化）——ESTABLISHED

N=10 链，Y_B=node0（REDUCED）。Γ_A: node0@1.0×100 步 vs Γ_B: node9@
s×100 步，s=线性反解（v1 正对照同法），源能量=P×100 精确燃尽。

| 门 | 实测 | 判定 |
|---|---|---|
| ΔY(t0)/RMS | 2.16e-17 | PASS（边界不可区分） |
| ΔX(t0)/RMS | 3.721 | PASS（隐藏态强可区分） |
| max ΔY⁺/RMS | 2.328 | PASS（未来强分叉） |

**因果阻断**：t0 将 B 全场态覆写为 A 场态（研究层状态手术）→ 未来边界
残差 2.53e-13 ⇒ `HIDDEN_STATE_CAUSALLY_SUPPORTED`（分叉全部归因于
隐藏场节点）。

## 三、Twin-2 源隐藏孪生（§27 新增）——ESTABLISHED

同一驱动历史（node0@P=1.0, t∈[0,100)），仅源剩余能量不同：
E_A(t0)=800 vs E_B(t0)=0（恰好耗尽）。**t0 场态逐位相同、边界逐位相同**
（ΔY=0.00e+00）；ΔX(t0)/RMS=0.302（差全在 E_source）；未来
max ΔY⁺/RMS=1.440。

**因果阻断**：intact(A) vs A@t0 源置零 → A_blocked ≡ B **逐位（残差
精确 0.0）**——干预即孪生，未来差异 100% 归因于环境对象（源）的因果
未来状态。证明 §27 命题：隐藏动力学不只来自 Field 内部节点。

## 四、Full vs Reduced 因果对照（§41 / NC4 / NC5）

同一 Twin-1 对：FULL 边界 t0 差=3.90（当前态可区分）vs REDUCED
2.16e-17（不可区分）⇒ "same-current / different-future" **只在
REDUCED 下出现**——隐藏动力学确系有限观察（partial observation）的
产物，非 World 算法随机黑箱。

## 五、登记

```text
WORLD_V2_HIDDEN_DYNAMICS = ESTABLISHED（场隐藏 + 源隐藏两型）
HIDDEN_STATE_CAUSALLY_SUPPORTED ×2（阻断实验，残差 2.5e-13 / 0.0）
```
隐藏自由度全部属于 X_W（场节点电荷/源剩余能量），无软件秘密变量
（§14 合规：删除/阻断该状态即改变未来）。该现象属 World 层，
不得改造为 TSS H_τ（WT0 §4 禁令继续有效）。

## 复现入口

```bash
PYTHONIOENCODING=utf-8 python research/world_v2/w1_hidden_twins.py   # exit 0
```
