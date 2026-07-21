# Memristor 结构扰动稳定化修复 + P2-A1b-2 皮肤-生成元转导映射

## 1. 目标

评判（`document - 2026-07-21T145017.166.md`）裁定P2-A1b-0/1通过，指出
**唯一阻塞**：`SynapticBundle.__init__`里驱动±25%初始权重扰动的种子
用Python内置`hash()`生成，逐进程随机化导致跨进程不可复现（已被
P2-A1b-0边界复核实测坐实）。要求先修复这项，再直接推进P2-A1b-2转导
映射设计，不再增加新的测量子阶段。用户确认：不加`model_seed`参数
（YAGNI），修复+P2-A1b-2一并完成。

## 2. 实际改动

**核心代码修复（唯一改动母本代码的部分）**：
- `nexus_v1/circuit/bundle.py`：`SynapticBundle.__init__`里
  `seed = hash((config.bundle_id, i_s, i_t)) % 10000`
  改为
  `seed = zlib.crc32(f"{config.bundle_id}:{i_s}:{i_t}".encode("utf-8")) % 10000`。
  数学不变（仍是[-0.25,+0.25]均匀分布扰动，仍由同一个三元组决定），
  只替换随机性来源。
- `nexus_v1/relations/site_selection.py`：文档字符串"已知复现性风险"
  更新为"历史复现性风险（已修复）"，记录修复方案。

**新增文件**：
- `nexus_v1/tests/exp_memristor_stable_hash_verification.py`：验证修复
  达成目的的临界档位跨进程一致性核实脚本。
- `nexus_v1/generators/skin_transduction.py`（TYPE:INFRA）：
  `TransductionConfig`/`transduce()`/`REFERENCE_TRANSDUCTION_CONFIG`。
- `nexus_v1/tests/test_skin_transduction.py`：T-TRANS-1~5契约测试。
- `nexus_v1/generators/__init__.py`：导出新模块符号。

## 3. 发现的真实问题

### 修复本身：影响范围确认为全电路，但无回归

`SynapticBundle`是全部约35条Bundle共享的核心构造函数，这次修复影响
全电路每一条Bundle的初始权重具体数值（虽然统计范围/分布形状完全不变）。
修复前后对比：不设置`PYTHONHASHSEED`跑同一段构造代码3次，修复前会得到
不同的权重矩阵（每次进程hash不同），修复后3次完全一致
`[[0.589275,0.614125],[0.4125,0.51205],[0.539925,0.459075]]`。

临界档位验证（u∈{0.001,0.02,0.05,0.08}，覆盖低端启动/𝒟_disc/𝒮_cap
转折三个区段，各不设PYTHONHASHSEED跑3次）全部完全一致：
```
u=0.0010: [(2, 2678), (2, 2678), (2, 2678)] -> PASS
u=0.0200: [(7, 583), (7, 583), (7, 583)]    -> PASS
u=0.0500: [(2, 384), (2, 384), (2, 384)]    -> PASS
u=0.0800: [(2, 384), (2, 384), (2, 384)]    -> PASS
```
全量回归21/21 PASS（部分数值如T4.3 Motor diff因权重具体实现改变而
在阈值范围内小幅变化：0.2467→0.0825，仍远高于阈值0.001，无回归）。
T-P2AG-1~12、T-STP-1~8 共20/20 PASS。

### P2-A1b-2：转导映射校准的参考集合选择需要给出依据

评判明确要求"选定已有实验中的一个参考物理过程集合，不能用最小值/最大值
直接反推κ_i"。选择依据：采用T-STP-6/7/8六场景（Γ_A~Γ_F，注入幅度统一
1.0）而非P2-A1b-1完整剂量扫描的8个数量级，理由是这组数据代表"有意义地
不同的真实刺激模式"（位置/次序/单点-组合反例），不是用来探测极端/钳位
鲁棒性的探针幅度。六场景全部18个温度值范围`[43.6483,61.8260]`，两点
线性求解映射到目标区间`[0.005,0.03]`（下界是u_on的约10倍，上界比
𝒮_cap转折点0.05留40%裕量）：
```
κ_i = (0.03-0.005)/(61.8260-43.6483) ≈ 0.0013759
b_i = 0.005 - κ_i×43.6483 ≈ -0.0550663
```
clip边界`[0.0, 0.04]`独立于校准区间——静息基线q=0映射后钳位到0.0
（不产生虚假激活）；极端dose场景（50.0注入，q≈3091.30）映射后精确
钳位到0.04（安全压缩，不越界送入生成元）。

## 4. 测试结果

| 测试 | 结果 |
|---|---|
| Memristor稳定哈希跨进程一致性（4个临界档位×3次） | 全部PASS |
| 全量回归 | 21/21 PASS |
| T-P2AG-1~12 | 12/12 PASS |
| T-STP-1~8 | 8/8 PASS |
| T-TRANS-1~5（新增） | 5/5 PASS |

## 5. 冻结契约

- **Memristor±25%扰动的随机性来源固定为`zlib.crc32`稳定摘要**，不再
  依赖Python内置`hash()`/`PYTHONHASHSEED`。任何后续需要跨进程比较
  Bundle初始权重绝对数值的测试/实验不再需要显式设置`PYTHONHASHSEED`。
- **不加`model_seed`参数**（YAGNI已确认）——如未来出现"同一结构地址
  需要多个可复现的不同实现"的具体需求，再单独设计，不预先占位。
- **`skin_transduction.py`的映射函数不接入`BaseGenerator`实际驱动
  循环**——等P2-A1b-3落地驱动权归属守卫（`MANUAL_CALIBRATION`/
  `WORLD_COUPLED`互斥）之后再接线，避免本轮引入`feed()`潜在双重驱动
  的风险窗口。
- **`REFERENCE_TRANSDUCTION_CONFIG`的每个参数均可追溯**（q_i0=测得的
  静息基线，κ_i/b_i=两点线性求解，clip边界=独立于校准区间的安全护栏），
  不是拍脑袋数值。

## 6. 未完成项

- **P2-A1b-3**：`θ↑`/`θ↓`/`t_rearm`闭合参数标定 + 驱动权归属守卫
  （`MANUAL_CALIBRATION`/`WORLD_COUPLED`互斥落实，含把`skin_
  transduction.transduce()`真正接入`BaseGenerator`驱动循环）。
- **P2-A3**：成对时序分辨率标定。
- **审查点2三项前置工作**（评判明确留到审查点2统一处理）：世界→接触→
  皮肤端到端可区分反例；`exp_validate_thermal_delta_50k.py`（FIX-019
  完全闭合条件）；在线状态转换流与完整`Occurrence`记录的接口区分。
