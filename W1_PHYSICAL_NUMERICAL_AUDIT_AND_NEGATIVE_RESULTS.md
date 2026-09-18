# W1_PHYSICAL_NUMERICAL_AUDIT_AND_NEGATIVE_RESULTS — 物理/数值审计 + 负结果

日期：2026-09-18
脚本：`research/world_v2/{w1_structure_scan,w1_physics_audit}.py`
数据：`research/world_v2/data/`（manifest/energy_ledger/dt_convergence/
boundary_trajectories 等 CSV + 两份 JSON）

---

## 一、M1 物理闭合（§30/§31）

10 个采样 episode 全程逐步账本：max|ΔE−injected+leaked| = **4.96e-11**
（浮点级）。能量谱系（E_source/E_field/E_injected/E_leaked/residual
每步）落 `energy_ledger.csv`。范围声明：`WORLD_LOCAL_ENERGY_AUDITABLE`，
不宣称全项目闭合（§31，G0/TSS 未回接）。

## 二、dt 收敛（§33）

物理时长 T_phys=2000 恒定，dt∈{1.0, 0.1, 0.01}（步数 2000/20000/200000
——杜绝"步数与 dt 同缩放"旧病）：

| 相邻档 | 最大相对差（E_final 与 τ_relax） |
|---|---|
| 1.0 → 0.1 | 2.248e-03 |
| 0.1 → 0.01 | 2.250e-04（十倍收敛 ✓，<1% ✓） |

τ_relax 三档均 200.0（=R·C 解析值）。⇒ 一阶收敛正常，dt=1.0 档的
物理误差 ~0.2% 登记在案。

## 三、负控制（§40）

| NC | 结果 |
|---|---|
| NC1 无源 | 初始脉冲纯耗散：能量单调降 ✓ 零注入 ✓ |
| NC2 断连源 | 源在场但永不释放 → 场轨迹与 NC1 **逐位相同** ✓ |
| NC3 无场耦合 | κ=0：驱动节点独热，其余恒 0（零跨节点传输）✓ |
| NC4/NC5 | Full 可区分当前态 / Reduced 恢复隐藏动力学——见 W1_HIDDEN_DYNAMICS_REPORT §四 ✓ |

## 四、M2/M3/B4（结构扫描，详见 w1_structure_scan.json）

- **M2**：Θ_legal 本域系综 PR：N=3→1.06 / 5→1.16 / 10→1.90 / 20→**3.33**
  （单调，3.13×>1.5×，>3 ✓）。均匀 κ 子域 PR(20)=2.90（差 3.5% 未过
  绝对杠）与单刺激 PR≤1.82 **如实并报**——异质 κ 是自由度的真实来源
  之一；单一平滑刺激只能探到低阶模。
- **M3**：τ_env 实测 = 20/200/2000（精确=R·C，100× 跨度）；τ_diff
  （相对梯度衰减）恒 47.2（跨度 1.00×）⇒ 解绑成立，≪/≈/≫ 三段位覆盖。
- **B4**：谱稳定界 κ·λ_max(L)+1/r_leak<2/dt 四点预测/实测全符
  （κ_crit≈0.552@N=5）；失稳=数值性质，非物理复杂性。

## 五、E1-E5 episode 族覆盖（§24）

E1 单源弛豫 / E2 位置族（node 0/2/4，边界轨迹互异）/ E3 多源同时 vs
错时 / E4 时间尺度对比（r_leak 20 vs 2000）——代表轨迹降采样落
`boundary_trajectories.csv`（B6）；E5=隐藏孪生（专报告）。

## 六、§35 极端案例（30 episodes manifest）

κ∈[0.0101, 0.1993]；τ_env∈[25, 1845]；max 能量残差 5.80e-11。

## 七、负结果登记（§58——同等保存）

1. **单刺激 PR 低（≤1.82，且 N=20 不单调）**：单一平滑双源刺激下链扩散
   高度共线——World 的可达自由度需要多样驱动才能展开；对 T1-B 的含义：
   校准集必须用采样系综而非单场景。
2. **均匀 κ 子域 PR(20)=2.90 未过绝对杠**：同 N 下若无 κ 异质性，
   有效自由度增长放缓（20 节点 ≈2.9 有效模）。
3. **首轮测量方法两处返工（透明登记）**：M3 未归一化展宽被 τ_env 污染
   （r_leak=20 档 τ_diff 虚低 14.0→修正后 47.2）；B4 逐点度数界漏判
   κ=0.9（正确为谱界）。均为测量端修正，World 本体无改动。
4. E4 r_leak=20 档：强耗散下源注入的空间结构寿命极短（边界轨迹峰后
   快速趋平）——合法域内存在"历史被环境耗散快速抹除"的角落，T1-B
   held-out 集应包含。

## 复现入口

```bash
PYTHONIOENCODING=utf-8 python research/world_v2/w1_structure_scan.py   # exit 0
PYTHONIOENCODING=utf-8 python research/world_v2/w1_physics_audit.py    # exit 0
```
