# nexus_v1 建模分析 — 从生物数据推导半导体参数

## 目标

信号当前在第 3 层（传入神经）被卡住。本分析不"试参数"，
而是从真实前庭神经科学数据出发，通过维度分析推导每一层的
半导体参数候选值，然后用熵账本验证。

---

## 1. 归一化方案（维度对齐）

### 生物单位空间

| 量 | 单位 | 典型范围 |
|----|------|---------|
| 电压 | mV | E_K = -80 到 E_Ca = +50 |
| 电流 | pA | 0 ~ 300 |
| 电容 | pF | 4 ~ 10 |
| 电导 | nS | 0.1 ~ 40 |
| 时间 | ms | 0.1 ~ 500 |

### 归一化映射

```
V_norm = (V_bio - E_K) / (E_Ca - E_K)
       = (V_bio + 80) / 130

E_K 归一化:   0.000
V_rest 归一化: (-65+80)/130 = 0.115
V_thresh_Ca:  (-40+80)/130 = 0.308
V_thresh_K:   (-30+80)/130 = 0.385
V_peak:       (0+80)/130   = 0.615
V_reset:      (-70+80)/130 = 0.077
E_Ca 归一化:   1.000

t_norm = t_bio(ms) / dt(ms)   (dt = 1 ms)

g_norm = g_bio / g_ref   (g_ref = 30 nS, 典型最大 MET 电导)

C_norm = C_bio / C_ref   (C_ref = 5 pF, 典型毛细胞)
```

---

## 2. 逐层参数推导

### Layer 1: MET 神经元

**生物参考**:
- REF: Fettiplace & Kim 2014; Eatock & Songer 2011
- MET 通道单一电导: 100-300 pS
- 总 MET 电导: ~10-30 nS
- MET 激活时间: < 0.1 ms (机械直连)
- 膜电容: 4-10 pF
- 膜时间常数: ~5 ms

**推导**:
```
capacitance = C_bio / C_ref = 5/5 = 1.0
tau_m = 5 ms → r_leak = 5.0 / 1.0 = 5.0
MET gm = g_MET / g_ref = 30/30 = 1.0
MET tau_gate = 0.0 (< 0.1 ms, instantaneous)
```

**候选值**:
```python
# REF: Eatock & Songer 2011, Fettiplace & Kim 2014
capacitance = 1.0    # NORM: 5 pF / 5 pF
r_leak = 5.0         # NORM: tau = 5 ms
inertia = 1.0
v_threshold = 0.05   # MET: minimal voltage gating
gm = 1.0             # NORM: 30 nS / 30 nS
tau_gate = 0.0       # BIO: < 0.1 ms
```

---

### Layer 2: 毛细胞 — 多通道

**生物参考**:
- REF: Eatock & Songer 2011; Hodgkin & Huxley 1952
- g_MET ~ 30 nS, g_K(BK) ~ 20 nS, g_Ca(CaV1.3) ~ 5 nS, g_leak ~ 0.5 nS
- tau_MET < 0.1 ms, tau_Ca = 0.5-2 ms, tau_K = 1-10 ms
- E_MET = 0 mV, E_K = -80 mV, E_Ca = +50 mV, E_leak = -60 mV

**推导**:
```
g_MET_norm = 30/30 = 1.0     E_MET_norm = (0+80)/130 = 0.615
g_K_norm   = 20/30 = 0.67    E_K_norm   = 0.0
g_Ca_norm  = 5/30  = 0.17    E_Ca_norm  = 1.0
g_leak     = 0.5/30 = 0.017  E_leak_norm = (-60+80)/130 = 0.154
tau_MET = 0.0, tau_Ca = 1.0, tau_K = 5.0
```

**Ca subsystem** (REF: Roberts et al. 1990):
- tau_Ca = 50-200 ms, take 100 → Ca_C × Ca_R = 100
- Ca_capacitance = 0.2, Ca_r_leak = 500
- Release threshold = 0.01
- Release gm = 5.0 (proxy for 3rd-5th power Ca dependence)

---

### Layer 4: 传入神经 — 堵点定量分析

**生物参考**: REF: Goldberg 2000
- Regular: 50-100 Hz, CV = 0.05-0.1, tau_adapt = 200-500 ms
- Irregular: 20-80 Hz, CV = 0.3-0.5, tau_adapt = 5-20 ms
- Threshold: ~15 mV above rest → 0.115 normalized

> [!IMPORTANT]
> **堵因定量分析**

```
当前 release_rate = 0.011
当前 bundle weight = 0.3, memristor G = 0.14
传入收到的电流: I = 0.011 x 0.14 = 0.0015
传入稳态电压:   V_ss = I x R = 0.0015 x 10 = 0.015
当前 v_peak = 0.3

V_ss / v_peak = 0.015 / 0.3 = 5% ← 只有阈值的 5%，永远不可能放电
```

**真实系统**: 带状突触释放率 6000-9500 vesicles/s, EPSC 20-700 pA，
几乎每次释放都触发 afferent spike。

**修正方向**:

| 修正 | 从 | 到 | 来源 |
|------|-----|-----|------|
| Ca capacitance | 0.5 | 0.2 | 更小 → Ca电压升更快 |
| Ca r_leak | 200 | 500 | 保持 tau_Ca=100 |
| Ca release threshold | 0.005 | 0.01 | Roberts 1990 |
| Ca release gm | 5.0 | 5.0 | 高阶Ca依赖 |
| HC→Aff weight | 0.3 | 0.8 | 带状突触 ≈ 高效 (Bao 2003) |
| Aff v_peak | 0.3 | 0.23 | NORM: 15mV/130mV + V_rest |
| Aff v_reset | -0.1 | 0.077 | NORM: (-70+80)/130 |
| Aff capacitance | 0.3 | 0.5 | NORM: 10pF/5pF (取中) |
| Regular b_adapt | 0.02 | 0.005 | Goldberg: slow adapt |
| Regular tau_w | 0.2 | 300.0 | BIO: 200-500 ms |
| Irregular b_adapt | 0.15 | 0.05 | Goldberg: fast adapt |
| Irregular tau_w | 0.05 | 10.0 | BIO: 5-20 ms |

### Fix 4: Bundle propagation 用 pre_trace 而非瞬时 activation

spike 只持续 1 dt = 1 ms，但真实 EPSP 持续 5-10 ms。
修改 `propagate()` 使用 `src.pre_trace`（指数衰减的历史）替代 `src.activation`。

---

## 3. 修复后预测

```
Ca voltage (修正后):
  I_ca_peak = 0.1, 积分 100 steps (100ms), C_ca = 0.2
  Q_ca = 0.1 x 0.001 x 100 = 0.01
  V_ca = 0.01 / 0.2 = 0.05

release_rate = 5.0 x (0.05 - 0.01) = 0.20

HC→Aff: I = 0.20 x G(w=0.8) = 0.20 x 2.0 = 0.40

Aff V_ss = 0.40 x 10 / 0.5 = 8.0 >> v_peak(0.23)

→ 传入应该以约 50-100 Hz 持续放电 ✓
→ 信号应该贯通到编码层 ✓
```

---

## 4. 执行清单

- [ ] 修改 chain.py: MET 参数 → 生物推导值
- [ ] 修改 chain.py: HairCell 通道参数 → 归一化推导值
- [ ] 修改 chain.py: Ca subsystem → 修正后参数
- [ ] 修改 chain.py: HC→Aff bundle weight → 0.8
- [ ] 修改 chain.py: Afferent 参数 → Goldberg 推导值
- [ ] 修改 bundle.py: propagate() 使用 pre_trace
- [ ] 运行 run_audit.py 熵账本验证
- [ ] 检查 signal_depth 是否达到 6/6
- [ ] 检查无电压爆炸

> [!IMPORTANT]
> 请确认以上分析和候选参数后，我再开始修改代码。
