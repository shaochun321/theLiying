# TSS 实测错误与缺陷反馈清单

以下问题来自对新版 `tss (2).zip` 的实际运行，不是单纯阅读 README 得出的结论。

---

## 1. 【确认失败】`test_r_prec_replay_simple.py` 下游电流增益未达到资格阈值

**严重程度：中等**

这是目前我实际发现的最明确的 assertion failure。

测试目标大致是验证：

> 学习不仅改变内部权重，而且应该对后续输出产生足够明显的功能影响。

实际运行结果：

```text
初始权重：
0.108750

学习后权重：
0.109802

Δw：
+0.001052
```

说明学习机制本身确实工作，权重增加约：

```text
0.97%
```

但学习组和冻结基线的总输出电流为：

```text
learned:
0.9191515535

frozen:
0.9191215877
```

实际相对提升只有大约：

```text
0.0033%
```

而测试要求：

```text
至少 +1%
```

因此测试稳定失败。

### 重复性

我另外使用：

```text
PYTHONHASHSEED=0
PYTHONHASHSEED=1
PYTHONHASHSEED=2
```

进行了三次独立复跑。

结果：

```text
3 / 3 FAIL
```

且失败数值基本一致。

因此可以排除普通随机波动。

### 建议检查

重点检查：

1. 测试中的 `1%` 是否仍然是当前架构有效的冻结资格阈值；
2. STDP/DA 导致的权重变化是否被后续电路压缩；
3. 是否存在饱和、归一化、电流瓶颈或其它下游结构，使约 0.97% 的权重变化最终只形成约 0.0033% 的输出变化；
4. 此测试究竟想证明：
   - “发生学习”，还是
   - “学习产生显著功能效应”。

目前前者已有证据，后者在这个实验中没有通过。

### 推荐反馈措辞

> `test_r_prec_replay_simple.py` reproducibly fails its downstream-effect criterion. The learned weight increases from 0.108750 to 0.109802 (+0.001052, ~0.97%), but total downstream current only changes from 0.9191215877 to 0.9191515535 (~0.0033%), far below the required 1% increase. Reproduced with PYTHONHASHSEED 0/1/2, 3/3 failures. The plasticity itself occurs, but the claimed downstream effect size is not supported by this test.

---

# 2. 【确认测试框架缺陷】`test_r1_x2c.py` 不能作为普通 pytest 文件正确收集运行

**严重程度：中低**

直接让 pytest 收集：

```text
test_r1_x2c.py
```

时，有两个测试函数要求：

```text
dt_a_traj
dt_b_traj
```

作为参数。

pytest 会把它们解释成 fixtures。

但工程中没有对应 fixture，因此产生：

```text
ERROR
fixture 'dt_a_traj' not found
fixture 'dt_b_traj' not found
```

所以：

```text
pytest tss/tests
```

无法把这个文件当作正常测试文件完整运行。

---

## 但 X2c 实验本身没有失败

我随后按照这个文件原本设计的：

```text
run()
```

入口直接执行。

实验完整通过。

代表结果：

```text
A-only:
xi_a_max = 1.0020
xi_b_max = 0

B-only:
xi_a_max = 0
xi_b_max = 1.0020

空输入输出范数 = 0
A-only 输出范数 = 0
B-only 输出范数 = 0

AℓB 输出范数 = 0.125945
```

并且：

```text
K_R1  = 0.125945 > ε
K_gen = 0.125945 > ε
K_out = 0.125945 > ε
```

最后：

```text
T-X2C ALL PASS
```

所以这里应该明确分类为：

```text
实验：PASS
pytest 包装：BROKEN
```

而不是实验失败。

### 建议修复

任选其一：

**方案 A：正式 pytest 化**

把轨迹生成逻辑做成：

```python
@pytest.fixture
def dt_a_traj(...):
    ...
```

等 fixture。

**方案 B：不要让 pytest 收集**

如果它实际上是一个实验脚本，那么不要命名成：

```text
test_*.py
```

或者明确将需要参数的函数改成内部 helper。

### 推荐反馈措辞

> `test_r1_x2c.py` is not pytest-safe. Two test functions expose `dt_a_traj` / `dt_b_traj` as function parameters without defining corresponding fixtures, producing pytest collection/execution errors. Running the file through its intended `run()` entrypoint succeeds completely, so this appears to be a test harness defect rather than an X2c experimental failure.

---

# 3. 【工程缺陷】部分诊断脚本对启动方式高度敏感

**严重程度：低**

至少一个诊断脚本直接使用：

```text
python tss/tests/_diag_....py
```

运行时会出现：

```text
ModuleNotFoundError: tss
```

而使用：

```text
python -m tss.tests._diag_...
```

则正常运行。

按照正确方式执行后，该诊断实验 PASS。

其中一次实际结果：

```text
线性 relay 路径比例误差：
0.0000

旧非线性读出最大 log-ratio 偏差：
约 1.3408
```

因此这不是实验失败。

但它暴露一个工程体验问题：

> 同一个仓库中的实验并不能统一通过文件路径直接运行。

### 建议

最好统一所有测试/实验入口。

例如统一要求：

```text
python -m ...
```

并提供：

```text
run_tests.py
run_experiments.py
```

或者确保 repository root 下的直接运行也有一致 import 行为。

---

# 4. 【测试体系问题】大量“pytest 测试”实际上是分钟级数值实验

**严重程度：中等，主要影响可验证性**

新版目前可被 pytest 收集到：

```text
204 tests
```

但是其中相当一部分并不是普通单元测试。

例如：

```text
activation_cloud_runtime
history_kernel
theta_unified
C1 coupling
r_prec replay
真实 occurrence 链
```

会运行大量真实母体 circuit step。

实际例子：

```text
activation_cloud_runtime
```

在给足时间以后：

```text
约 59 秒
PASS
```

之前如果设置 18 秒或 25 秒执行限制，就只能得到 TIMEOUT。

C1 一些完整真实母体实验甚至单项超过：

```text
120 秒
```

整套：

```text
pytest tss/tests
```

连续运行超过：

```text
300 秒
```

仍只完成早期一部分测试。

### 这不是理论错误

但会严重影响：

- CI；
- 全量回归；
- 外部复现；
- 判断代码修改是否退化；
- 新研究者验证结果。

### 建议分类

建议至少拆成：

```text
tests/unit/
tests/contracts/
tests/integration/
tests/longrun/
experiments/
```

pytest marker 也可以使用：

```python
@pytest.mark.fast
@pytest.mark.integration
@pytest.mark.longrun
@pytest.mark.experimental
```

这样：

```text
pytest -m fast
```

可以快速确定工程没有明显退化。

而：

```text
pytest -m longrun
```

专门用于完整物理资格实验。

---

# 5. 【测试分类缺陷】实验脚本、诊断脚本和 pytest 测试的边界不清楚

**严重程度：中低**

当前至少存在三类可运行文件：

```text
test_*.py
exp_*.py
_diag_*.py / _probe_*.py
```

其中：

```text
test_*.py
```

不一定真的是标准 pytest test。

例如 X2c。

同时一些真正重要的资格实验位于：

```text
exp_*.py
```

不会被：

```text
pytest tss/tests
```

统计。

新版目录至少还有约：

```text
10 个 exp_* 实验脚本
4 个诊断/探针脚本
```

因此：

```text
204 tests passed
```

即使未来做到，也不能等价于：

```text
整个 TSS 实验体系全部通过
```

### 建议

建立正式 manifest，例如：

```text
EXPERIMENT_MANIFEST.yaml
```

记录：

```text
id
file
entrypoint
category
expected_runtime
seed
qualification_status
required / optional
```

这样才能真正知道：

> 当前冻结资格一共依赖多少实验。

---

# 6. 【可复现性问题】部分真实链路结果与 README 保存值略有不同

**严重程度：低，目前没有导致资格失败**

README 曾记录一级时间链的三个延迟：

```text
Δt = {321, 360, 312}
```

我独立复跑真实链得到过：

```text
Δt = {315, 355, 308}
```

结果的**方向性质完全一致**：

```text
forward → 产生
reverse → 0
```

所以当前不是功能失败。

但精确数字存在变化。

### 建议检查

确认这些量是否受：

- Python hash seed；
- 随机 seed；
- circuit 初始化状态；
- floating-point 执行顺序；
- nexus_v1 与 tss 组合版本；

影响。

如果资格真正依赖的是：

```text
forward positive
reverse zero
```

建议 README 不要把一组具体 Δt 写得像冻结常数。

可以写：

```text
representative observed run
```

或附 seed / commit / environment。

---

# 7. 【验证状态问题】README 中部分“全通过”目前依赖历史记录，而非容易重新复现的快速资格

**严重程度：中等，属于研究可信度问题**

例如 C1 README 声称：

```text
11/11 PASS
10 seeds
30/30 positive relations
```

这并不代表记录是假的。

我已经独立复现：

- C1 多项轻量资格；
- adapter calibration；
- 一个真实完整母体链；
- 三组二级耦合输出；
- parent block 后输出严格归零。

所以 C1 确实存在真实可运行证据。

但是完整：

```text
10 seeds × full mother circuit
```

的复现成本非常高。

在当前执行环境下，单次完整执行无法迅速重新获得 README 中所有统计值。

### 建议

冻结资格结果时同时保存：

```text
raw result artifact
seed
commit hash
Python version
dependency versions
runtime
exact command
```

甚至保存：

```text
CSV / JSON experiment ledger
```

而不要只在 README 中留下：

```text
30/30 PASS
```

这样以后可以区分：

> 历史资格记录

和：

> 当前版本重新复现结果。

---

# 8. 【定量判据问题】需要区分“机制存在”和“功能效应足够大”

**严重程度：中等**

这个问题由 `test_r_prec_replay_simple.py` 暴露出来，但影响可能比一个测试更广。

例如当前可能出现：

```text
权重确实改变
```

所以：

```text
plasticity mechanism exists
```

成立。

但：

```text
下游输出几乎不变
```

则：

```text
functional consequence
```

未必成立。

建议所有类似资格分成两层：

```text
Mechanism qualification
```

和：

```text
Effect-size qualification
```

例如：

```text
STDP changed weight             PASS
DA gating controlled learning   PASS
downstream response > 1%        FAIL
```

不要最后合并成一句：

```text
learning PASS
```

否则容易掩盖真正有价值的负结果。

---

# 当前最重要的反馈优先级

如果只反馈三个问题，我建议按这个顺序：

## P1 — 真实实验失败

```text
test_r_prec_replay_simple.py
```

学习存在，但 downstream 1% effect-size 资格稳定失败。

这是最值得技术人员检查的。

## P2 — pytest 基础设施错误

```text
test_r1_x2c.py
```

直接 pytest 会出现两个缺失 fixture ERROR，但作者自带 `run()` 实验完整 PASS。

应该修复测试包装。

## P3 — 全量验证体系过重且分类不清

204 pytest 项中混有大量分钟级完整数值实验，同时还有不被 pytest 收集的 `exp_*`。

建议把：

```text
fast regression
full integration
qualification experiment
diagnostic
```

明确拆开。

---

# 当前不要误报为 bug 的内容

下面这些我已经检查过，**暂时不要反馈成错误**：

### C1 parent blocking

我实际复现过：

```text
正常：
second-order output > 0

阻断必要父关系：
output = 0
```

这是通过结果。

### C1 基本不可约资格

单父、交换顺序、超窗、序盲基线等，我已经复跑通过。

### X2c

不是实验失败。

是 pytest fixture / 包装问题。

### 诊断脚本 import failure

不是实验失败。

按照文件要求用：

```text
python -m ...
```

即可正常运行。

### 长测试 TIMEOUT

不能直接归为失败。

已经有至少一个此前 TIMEOUT 的测试在允许完整运行后：

```text
59 秒 PASS
```

所以所有长项必须等待真实退出状态才能判断。

---

## 一句话反馈总结

> 目前独立实测发现一个稳定的定量实验失败：旧关系学习回放中权重确实发生约 0.97% 的学习变化，但下游总电流只改善约 0.0033%，未达到测试要求的 1%，三个 hash seed 下均复现。另外发现 `test_r1_x2c.py` 的 pytest fixture 设计错误，虽然其原生 `run()` 实验本身完整通过。测试体系还存在长物理实验与快速单测混杂、部分实验不由 pytest 收集、部分脚本启动方式不统一等验证工程问题。暂未发现基础生成元或 C1 已复现核心链路的明确 assertion failure。