# TSS (3) 全量实测后的最终修改清单
## 2026-09-07

## 0. 本轮完整实测结果

### 正式 pytest

实际收集：

```text
214 tests
```

最终结果：

```text
212 PASS
2 XFAIL
0 FAIL
0 ERROR
0 TIMEOUT
0 NOT RUN
```

两个 XFAIL 均是项目已经明确登记的 LIM：

```text
test_r_prec_replay_simple
test_r_prec_replay
```

分别对应当前可塑读出的效应量层和 R2 效应量层未达标。

这与项目清单当前明确保留的 LIM 状态一致，不应该通过降低阈值把它们“修绿”。

---

### 非 pytest 实验/诊断

全部 17 项已经运行：

```text
16 exit 0
1 exit 1
```

唯一 exit 1：

```text
exp_P2A1b_3_closure_calibration
```

后面会说明：它目前更像**旧实验与新 epoch/token 语义不一致**，不能直接判定为 OccurrenceClosure 实现失败。

---

### 手动资格入口

pytest 不直接覆盖的完整入口也补跑：

```text
C0 relation order audit      PASS
X2c full run()               PASS
TSS-3a 五种子审计            全部执行完成
```

TSS-3a 本身是测量型脚本，没有最终 assertion PASS/FAIL；项目 manifest 也把它登记为“测量脚本（无断言判定）”。

---

### nexus_v1 母体回归

```text
21 / 21 PASS
```

本轮使用的旧上传母体缺少 DEG-021 后来要求的 `_step_serial`，因此测试副本仅补入报告明确规定的一行兼容性修改后运行：

```python
self._step_serial = getattr(self, "_step_serial", 0) + 1
```

没有做其它母体修改。

项目最新工作报告也明确说明 DEG-021 需要这项母体最小标记。

---

# P0 — 必须修复

## 1. `KernelEnergyProbe` 神经元热耗散量纲错误

### 实测

当前实现：

```python
self.total_neuron_heat += n.heat_output * dt
```

但母体 `Neuron.heat_output` 已经表示**该 step 实际扣除/释放的能量**，不是功率。

我让 TSS probe 和母体自身的累计热账本对同一条轨迹计数：

```text
KernelEnergyProbe:
0.00037057781099210374

母体累计 heat:
0.370577810992087

ratio:
0.0010000000000000453
```

而：

```text
dt = 0.001
```

因此：

\[
\frac{E_{\mathrm{probe}}}{E_{\mathrm{mother}}}
\simeq dt
=0.001
\]

即当前 TSS 神经元热账本**少记约 1000 倍**。

### 修改

如果母体 `heat_output` 的单位继续保持“每步能量”，应改为：

```python
self.total_neuron_heat += n.heat_output
```

而不是：

```python
self.total_neuron_heat += n.heat_output * dt
```

### 必须增加的新测试

不能再只检查：

```python
assert probe.total_neuron_heat >= 0
```

当前 T-KL-3 正是因为只做非负、非 NaN 等 sanity check，才让这个 1000× 错误通过。

增加类似：

```text
initial = Σ neuron._cumulative_heat_out
运行同一轨迹
final   = Σ neuron._cumulative_heat_out

mother_delta = final - initial

assert probe.total_neuron_heat ≈ mother_delta
```

这是**跨账本守恒测试**。

建议容差使用浮点误差级，而不是百分比级。

### 文档同步

明确写出：

```text
Neuron.heat_output:
energy per simulation step

不是:
power
```

否则以后很容易再次多乘或少乘 `dt`。

---

# P0 — 修复实验语义，不要误改状态机

## 2. `exp_P2A1b_3_closure_calibration` 当前 exit 1

实际失败：

```text
AssertionError:
重整后应能重新触发进入ACTIVE
```

看起来像：

> rearm 完成后 OccurrenceClosure 无法触发第二次 occurrence。

但读完现在的状态机以后，原因更加具体。

### 当前状态机后来增加了 epoch/token 门控

现在 ARMED → ACTIVE 不仅要求：

```text
value >= theta_up
```

还要求：

```text
phys_support == True
```

而且每一个连续物理支撑 epoch：

```text
最多消费一次 occurrence candidate
```

只有出现新的：

```text
False → True
```

物理支撑上升沿，才会开启一个新的 epoch 并重置：

```text
_epoch_consumed = False
```

这是为了防止同一个连续真实刺激期间，因为内部振荡反复产生“新 occurrence”。

### 旧校准脚本的问题

当前脚本第二次 occurrence 测试写的是：

```python
closure.update(0.02, t)
```

没有显式传：

```python
phys_support
```

而默认值是：

```python
phys_support=True
```

所以整个第一轮、refractory 和第二轮，从状态机看来其实都是：

```text
True → True → True → True
```

根本没有新的物理支撑 epoch。

第一轮已经把当前 epoch：

```text
_epoch_consumed = True
```

因此第二次：

```text
value = 0.02
```

理应被拒绝。

所以这个 exit 1 **不能直接证明当前 OccurrenceClosure 错了**。

更准确地说：

> 旧 P2-A1b-3 校准实验没有同步后来加入的 phys_support epoch/token 语义。

---

## 建议修改该实验

第一轮：

```text
phys_support=True
```

结束外部支撑：

```text
phys_support=False
```

等待 down/rearm 完成。

第二轮新的真实刺激开始：

```text
phys_support=True
```

形成真正：

```text
False → True
```

的新 epoch。

然后再检查第二次 occurrence。

也就是测试应该表达：

```text
physical epoch 1
     ↓
occurrence 1
     ↓
support disappears
     ↓
rearm
     ↓
physical epoch 2
     ↓
occurrence 2
```

而不是：

```text
一个持续不间断的 phys_support=True
     ↓
要求状态机产生两个 occurrence
```

后者现在正是 epoch/token 门控刻意禁止的行为。

---

## 同时增加一个负对照

应该正式冻结：

```text
phys_support 连续保持 True
```

即使：

```text
value 上下越阈多次
```

也只能消费一次 occurrence。

即：

```text
same support epoch
→ occurrence count = 1
```

这样才能证明 epoch gate 不是偶然存在。

---

## 重要：不要为了让这个旧实验 PASS 而删除 `_epoch_consumed`

否则会重新引入此前已经发现的问题：

> 一个连续真实物理支撑期间，由 collector 内部振荡制造多个伪 occurrence。

因此这里首先要**修实验**。

实验改完后如果新的 `False → True` epoch 仍无法生成第二 occurrence，才应该把它升级成状态机 bug。

---

# P1 — 测试覆盖缺口

## 3. X2c 的 pytest 修复方式不完整

上一版的问题是：

```text
dt_a_traj
dt_b_traj
```

被 pytest 当成不存在的 fixtures。

新版把：

```python
test_x2c_iso_1_a_only(...)
test_x2c_iso_2_b_only(...)
```

改成：

```python
_x2c_iso_1_a_only(...)
_x2c_iso_2_b_only(...)
```

所以 collection ERROR 消失。

但是现在：

```text
pytest test_r1_x2c.py
```

实际只收集：

```text
test_x2c_cut_0_cut_method
```

而真正重要的：

```text
A-only isolation
B-only isolation
K_R1
K_gen
K_out
```

只会在：

```text
python -m tss.tests.test_r1_x2c
```

的 `run()` 中运行。

我已经完整跑过 `run()`：

```text
PASS
```

所以 X2c 当前机制没有发现失败。

问题是：

> **pytest 全绿不能保护 X2c 核心资格不退化。**

项目 manifest 当前却把：

```text
test_r1_x2c
```

登记为 longrun PASS。

这容易造成测试覆盖理解偏差。

---

## 推荐修改

最好用 module-scoped fixture：

```python
@pytest.fixture(scope="module")
def recorded_dt_trajs():
    return _record_dt_trajectories()
```

然后恢复：

```python
def test_x2c_iso_1_a_only(recorded_dt_trajs):
    ...

def test_x2c_iso_2_b_only(recorded_dt_trajs):
    ...

def test_x2c_irreducibility(recorded_dt_trajs):
    ...
```

这样真实轨迹只录制一次，但 pytest 能单独显示：

```text
ISO-1 PASS/FAIL
ISO-2 PASS/FAIL
K_R1 PASS/FAIL
K_gen PASS/FAIL
K_out PASS/FAIL
```

比单纯一个巨大 wrapper 更容易定位退化。

---

# P1 — pytest marker 分类错误

## 4. `generator_lambda` / `generator_sigma` 不应该标成 fast

当前 `conftest.py` 自己定义：

```text
fast:
纯组件/契约
无真实电路驱动
秒级
```

但 `_FAST` 中包含：

```text
test_generator_lambda
test_generator_sigma
```

manifest 也仍然把它们写成：

```text
fast / 秒级
```



### 本轮实际时间

我独立完整运行得到大约：

```text
generator_lambda    126 s
generator_sigma     191 s
```

它们不只是“不太快”。

而是已经明显违反：

```text
fast = 无真实电路 + 秒级
```

的定义。

### 修改建议

从 `_FAST` 删除：

```python
"test_generator_lambda",
"test_generator_sigma",
```

按照现在的定义，它们应该进入：

```text
longrun
```

因为 `integration` 当前定义也只有：

```text
≲ 60 s
```

同步修改：

```text
EXPERIMENT_MANIFEST.md
```

中的：

```text
fast / 秒级
```

描述。

---

# P1 — README 状态过期

## 5. DEG-021 在 README 同时处于 OPEN 和 RESOLVED

当前 README 前面仍写：

```text
已知护栏缺口：
base_generator.feed() 与 circuit.step()
双驱动互斥仅有文档警告、无代码级互锁
```



但最新工作报告和资格台账实际上已经把 DEG-021 标记：

```text
RESOLVED
```

并建立了 T-DD-1~3。

### 修改

README 前面的旧段落应删除或改成：

```text
DEG-021 已解决：
BaseGenerator 与 VariantCircuit.step() 之间已有 step_serial
双驱动 fail-fast 互锁。
```

---

# P1 — 版本配对/发布问题

## 6. `tss (3)` 不能和旧 `nexus_v1` 独立组成最新冻结状态

这是本轮复现实测暴露出来的工程问题。

`tss (3)` 已经依赖：

```text
VariantCircuit._step_serial
```

但你这次上传的 TSS 包本身不包含对应的新母体。

用旧 `nexus_v1`：

```text
T-DD-2 FAIL
```

只加入最新报告明确要求的：

```python
self._step_serial = getattr(self, "_step_serial", 0) + 1
```

之后：

```text
3 / 3 PASS
```

所以问题不是 DEG-021 逻辑错误，而是：

> **TSS 包与所需母体版本之间没有机器可读的版本约束。**

---

## 推荐增加

至少保存：

```text
required_nexus_commit
tss_commit
python_version
dt
```

例如：

```json
{
  "tss_commit": "...",
  "requires_nexus_v1_commit": "...",
  "dt": 0.001
}
```

也可以在测试启动时 fail-fast：

```text
当前 nexus_v1 不具备 required interface:
VariantCircuit._step_serial
```

而不是让外部复现者跑到某个 DEG-021 test 才发现母体不匹配。

资格台账本来就已经强调区分“历史资格”和“当前版本重新复现结果”。

现在应该再把**代码版本配对**也纳入台账。

---

# P2 — 更新 manifest 的真实耗时

## 7. 当前参考时长已经明显低估部分测试

本轮实际测得部分长项约为：

```text
boundary_process        530 s
entry_boundary          528 s
C1 coupling             497 s
r2_x2c                  403 s
entry_gate              288 s
history_kernel          281 s
r_prec_t2               205 s
generator_sigma         191 s
r2_fork                 182 s
generator_lambda        126 s
r_prec_t3               701 s
```

其中部分与 manifest 大体一致，但部分差异明显。

manifest 已明确说：

> marker 应按实测时长修订。

所以这次数据应该直接写回去。

建议记录：

```text
reference runtime
external reproduction runtime
```

两列。

不要只有一个绝对“~2min”。

因为机器、Python 版本和并行负载会影响很大。

---

# P2 — ℒ 仍然不能升级为完整 EXISTS

## 8. 修完 ×dt 以后也不要把能量账本宣布完整

最新台账目前已经很谨慎：

```text
ℒ = EXISTS_PARTIAL
```

原因之一：

```text
MOSFET conduction / switching dissipation
仍未建模
```



本轮又发现 neuron heat 的 ×dt bug。

所以正确顺序应该是：

```text
先修 neuron heat 量纲
↓
加入跨账本测试
↓
重新跑 T-KL
↓
ℒ 仍保持 EXISTS_PARTIAL
↓
未来再处理 MOSFET dissipation
```

不能因为 T-KL 重新 PASS 就升级：

```text
ℒ = EXISTS
```

---

# P2 — DEG-018 仍是设计裁定，不是普通 bug

## 9. 500-step refractory 会丢失部分新发生

项目自己的最新审计已经实测：

```text
gap < 500
```

的新支撑 epoch 可能被整个丢失，而不是仅延迟。

同时：

```text
t_rearm
```

会系统性比无第二时钟版本晚 500 步。

因此项目已经正确把 DEG-018 定为：

```text
DESIGN_DECISION_QUANTIFIED
```

而不是 RESOLVED。

这个状态应该继续保持。

### 下一实验建议

不要立刻改 500。

做一个二维实验：

```text
gap between physical epochs
×
new support duration
```

例如：

```text
gap = 50,100,...,700
duration = 20,50,100,...,800
```

记录：

```text
new physical epoch observed?
occurrence generated?
occurrence delayed?
occurrence permanently lost?
```

然后由你裁定：

> refractory 的角色到底是“去抖”还是“允许真实发生被压制”。

这个问题属于理论/工程语义裁定，不能靠测试作者自己决定。

---

# P2 — LIM 不要“修绿”

## 10. 两个 XFAIL 应继续保持

当前完整 pytest：

```text
212 PASS
2 XFAIL
```

这两个 XFAIL 是有价值的。

项目当前已经定量得到：

```text
N=1: ~0.0035%
N=4: ~0.0034%
```

说明多束并行不能解决相对效应量判据；而当前机制上限仍低于 1% 标准。

所以禁止采用：

```text
把 1% 改成 0.001%
```

或者：

```text
pytest.xfail → PASS
```

这种“修复”。

应该继续保留：

```text
mechanism PASS
effect-size XFAIL
```

这恰恰是当前项目测试体系里比较健康的一部分。

---

# P3 — C0 / TSS-3a 的 pytest 表述要更明确

## 11. `test_c0_relation_order_audit.py` 名字像 pytest，但没有 pytest test

执行：

```text
pytest test_c0_relation_order_audit.py
```

得到：

```text
exit 5
no tests collected
```

但：

```text
python -m tss.tests.test_c0_relation_order_audit
```

完整 PASS。

manifest 已经把其入口明确写成 `run()`，所以这不算实验 bug。

不过文件仍然叫：

```text
test_*.py
```

很容易让全量 pytest 用户误解。

任选一个方向：

### A

真正加 pytest wrapper。

或者：

### B

重命名：

```text
exp_c0_relation_order_audit.py
```

考虑项目强调“不批量改名冒充新资格”，我更倾向 **A**。

---

## 12. TSS-3a 应继续叫 measurement，不应该写 PASS

本轮五个 seed 都执行完成。

但其脚本没有最终 assertion 判定。

因此状态应该是：

```text
MEASURED / COMPLETED
```

而不是：

```text
PASS
```

manifest 当前已经基本这么做：

> “测量脚本（无断言判定）”。

保持即可。

---

# 不需要修改的部分

本轮没有发现以下链路的 assertion failure：

```text
基础生成元
physical occurrence
entry gate
history kernel
Θ comparator
C0
C1
relation occurrence
R2 fork
R1/R2 X2c
E0 type audit
```

特别是：

```text
C1 full chain
```

完整长跑通过。

所以目前没有证据支持去重写：

```text
关系适配器
H_tau
Theta comparator
c_ro
```

这些核心链。

---

# 修改优先级最终排序

## 第一批：立即修

```text
1. KernelEnergyProbe 去掉错误的 heat_output × dt
2. 增加 mother cumulative heat ↔ TSS probe 的交叉账本测试
3. 修 exp_P2A1b_3_closure_calibration 的 phys_support epoch 语义
4. 给该实验增加“同一 support epoch 不允许第二 occurrence”的负对照
```

---

## 第二批：测试工程

```text
5. 恢复 X2c ISO-1 / ISO-2 / K_R1/K_gen/K_out 的 pytest 覆盖
6. generator_lambda / generator_sigma 从 fast 移出
7. 更新 manifest 的实际 runtime
8. C0 增加 pytest wrapper
9. README 删除 DEG-021 过期 OPEN 描述
10. 建立 TSS ↔ nexus_v1 版本配对声明
```

---

## 第三批：继续保留为开放问题

```text
11. DEG-018：500-step refractory 的语义裁定
12. LIM：保持两项 XFAIL，不调阈值放行
13. MOSFET 耗散仍未建模，ℒ 保持 EXISTS_PARTIAL
14. 跨 occurrence 持续性仍未测
15. 拓扑关联保护 R-E0-3 仍未定义
16. Residual qualification R-E0-2 仍未冻结
17. Xin / Shadow / S1-S2 空间来源仍不得视作已完成
```

项目自己的资格台账也明确说明：E0 当前只是**类型审计资格，不是事件核资格**；跨 occurrence 持续性未测，拓扑关联保护仍需裁定。

---

# 一句话结论

这次完整实测之后，当前最需要修的并不是 C1 或基础生成元。

真正明确的实现错误只有一个非常具体而严重的：

> **E0 能量 probe 把已经是“每步能量”的 neuron heat 又乘了 dt，导致神经元热耗散少记 1000 倍。**

唯一非 pytest `exit 1` 则应首先视为：

> **旧 P2-A1b-3 校准实验没有同步新的 phys_support epoch/token 规则。**

而不是立即去修改 OccurrenceClosure。

其余核心资格链在这次完整运行中没有出现 assertion failure；两个 XFAIL 是已经登记、应该继续保留的 LIM 负结果。