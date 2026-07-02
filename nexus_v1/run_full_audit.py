"""全链路熵账本审计 — cell-cc-other 专用

覆盖三条信号链路：
  A. 前庭链路   MET→HC→Aff→Enc→Col→Motor
  B. 热觉链路   Soma patches → enc_therm_* → col_therm_* → Motor
  C. DA/Shadow  Shadow(S_Enc/Col/Mot) → DA → Motor 调制

两阶段仿真：
  Phase 1: 10k步 dt=1.0  oto_x=200sin(0.5Hz)  — 前庭基准
  Phase 2: 10k步 dt=0.001 body@[75,20,25]       — 热觉基准

Run from cell-cc-other/:
    PYTHONIOENCODING=utf-8 python nexus_v1/run_full_audit.py
"""
from __future__ import annotations

import sys
import os
import io
import math
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if hasattr(sys.stdout, 'buffer'):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

# ─── helpers ────────────────────────────────────────────────────────────────

def bar(v, width=20, lo=0.0, hi=1.0):
    frac = max(0.0, min(1.0, (v - lo) / max(hi - lo, 1e-9)))
    n = int(frac * width)
    return '#' * n + '.' * (width - n)

def mean(lst):
    return sum(lst) / len(lst) if lst else 0.0

def std(lst):
    if len(lst) < 2:
        return 0.0
    m = mean(lst)
    return math.sqrt(mean([(x - m) ** 2 for x in lst]))

def weight_entropy(weights):
    """Shannon entropy of weight distribution (normalized to [0,1])."""
    if not weights:
        return 0.0
    total = sum(weights)
    if total < 1e-12:
        return 0.0
    probs = [w / total for w in weights]
    H = -sum(p * math.log2(p) for p in probs if p > 1e-12)
    return H

def section(title):
    print()
    print('=' * 72)
    print(f'  {title}')
    print('=' * 72)

def subsection(title):
    print(f'\n  ── {title} ──')

def health(ok, label=''):
    tag = '[OK ]' if ok else '[ERR]'
    return f'{tag} {label}'


# ─── Circuit factories ──────────────────────────────────────────────────────

def make_vestibular_circuit():
    """Circuit for vestibular chain audit: 10k steps dt=1.0 oto_x sinusoidal."""
    import random
    random.seed(42)
    from nexus_v1.circuit.variant_adapter import VariantCircuit
    c = VariantCircuit()
    return c

def make_thermal_circuit():
    """Circuit for thermal chain audit: body@[75,20,25] near heat source."""
    import random
    random.seed(99)
    from nexus_v1.circuit.variant_adapter import VariantCircuit
    c = VariantCircuit()
    c.world.body.position = [75.0, 20.0, 25.0]
    return c


# ─── Section 0: Census ──────────────────────────────────────────────────────

def audit_census(c):
    section('SECTION 0: 神经元/Bundle 人口普查')

    all_n = c.get_all_neurons()
    all_b = c.get_all_bundles()

    # Categorize by ID prefix
    cats = {
        'L1_MET':    [], 'L2_HC':     [], 'L3_Aff':    [],
        'L4_Enc':    [], 'L5_Col':    [], 'L6_Mot':    [],
        'Shadow':    [], 'DA':        [], 'XinRelay':  [],
        'Soma_Therm':[], 'Soma_Noci': [], 'Soma_Relay':[],
        'Other':     [],
    }
    for n in all_n:
        nid = n.config.neuron_id
        if nid.startswith('met_'):            cats['L1_MET'].append(nid)
        elif nid.startswith('hc_'):           cats['L2_HC'].append(nid)
        elif nid.startswith('aff_'):          cats['L3_Aff'].append(nid)
        elif nid.startswith('s_enc_') or nid.startswith('s_col_') or nid.startswith('s_mot_'):
                                              cats['Shadow'].append(nid)
        elif nid.startswith('enc_') or nid.startswith('reg_') or nid.startswith('irr_'):
                                              cats['L4_Enc'].append(nid)
        elif nid.startswith('col_'):          cats['L5_Col'].append(nid)
        elif nid.startswith('da_'):           cats['DA'].append(nid)
        elif nid.startswith('motor_') or nid.startswith('move_'):
                                              cats['L6_Mot'].append(nid)
        elif nid == 'xin_relay':             cats['XinRelay'].append(nid)
        elif nid.startswith('thermo_') or nid.startswith('noci_tc_'):
                                              cats['Soma_Therm'].append(nid)
        elif nid.startswith('noci_'):         cats['Soma_Noci'].append(nid)
        elif nid.startswith('relay_'):        cats['Soma_Relay'].append(nid)
        else:                                 cats['Other'].append(nid)

    print(f'\n  神经元总计: {len(all_n)}')
    for cat, ids in cats.items():
        if ids:
            print(f'    {cat:<14s}: {len(ids):3d}  {ids[:3]}{"..." if len(ids)>3 else ""}')

    # Bundle categories
    bcat = {'vest':[], 'therm':[], 'shadow_da':[], 'xin_da':[], 'soma':[], 'other':[]}
    for b in all_b:
        bid = b.id
        if 'therm' in bid:                    bcat['therm'].append(bid)
        elif 'shadow' in bid or 'xin_to_da' in bid:
            if 'xin_to_da' in bid:           bcat['xin_da'].append(bid)
            else:                             bcat['shadow_da'].append(bid)
        elif 'thermo' in bid or 'soma' in bid or 'relay' in bid or 'noci' in bid:
                                              bcat['soma'].append(bid)
        else:                                 bcat['vest'].append(bid)

    print(f'\n  Bundle 总计: {len(all_b)}')
    for cat, ids in bcat.items():
        if ids:
            print(f'    {cat:<12s}: {len(ids):3d}')

    # DA circuit initialized?
    da_init = getattr(c, '_da_circuit_initialized', False)
    print(f'\n  DA 电路已初始化: {da_init}')
    print(f'  bundles_shadow_to_da: {len(c.bundles_shadow_to_da)}')
    print(f'  bundles_xin_to_da:    {len(c.bundles_xin_to_da)}')
    print(f'  Shadow neurons:       {len(c.shadow_sandbox.neurons)}')

    missing = []
    if not cats['DA']:        missing.append('DA neurons not in census')
    if not cats['Shadow']:    missing.append('Shadow neurons not in census')
    if not cats['Soma_Therm']:missing.append('Soma_Therm neurons not in census')
    if missing:
        print('\n  [WARN] census 缺口:')
        for m in missing:
            print(f'    ! {m}')
    else:
        print('\n  [OK] census 完整：DA / Shadow / Soma 全部可见')

    return cats, bcat


# ─── Section 1: 前庭链路 ────────────────────────────────────────────────────

def audit_vestibular(c, steps=10000, dt=1.0):
    section('SECTION 1: 前庭链路  MET→HC→Aff→Enc→Col→Motor')
    print(f'  参数: {steps} steps, dt={dt}')

    INPUT_FREQ = 0.5
    t0 = time.time()
    for i in range(steps):
        t = i * dt
        c.step({'oto_x': 200 * math.sin(2 * math.pi * INPUT_FREQ * t)}, dt)

    elapsed = time.time() - t0
    print(f'  运行耗时: {elapsed:.1f}s')

    vest = c.vestibular
    layers = [
        ('L1 MET',         list(vest.met_neurons.values())),
        ('L2 HC',          list(vest.haircell_neurons.values())),
        ('L3 Aff-reg',     list(vest.afferent_regular.values())),
        ('L3 Aff-irr',     list(vest.afferent_irregular.values())),
        ('L4 Enc (vest)',  [n for k,n in c.encoding_neurons.items() if 'therm' not in k]),
        ('L5 Col (vest)',  [n for k,n in c.column_neurons.items() if 'therm' not in k]),
        ('L6 Motor',       list(c.motor_neurons.values())),
    ]

    subsection('逐层激活 EMA')
    depth = 0
    for layer_name, neurons in layers:
        if not neurons:
            print(f'    {layer_name:<20s}: [EMPTY]')
            continue
        acts = [n._activation_ema for n in neurons]
        avg = mean(acts)
        mx  = max(acts)
        alive = avg > 1e-4
        if alive:
            depth += 1
        marker = '' if alive else '  << DEAD'
        print(f'    {layer_name:<20s}: avg={avg:.4f}  max={mx:.4f}  {bar(avg)}{marker}')

    print(f'\n  信号深度: {depth}/7 层活跃')

    subsection('Enc 选择性（oto_x vs therm_front）')
    enc_vest  = c.encoding_neurons.get('reg_oto_x')
    enc_therm = c.encoding_neurons.get('irr_therm_front')
    if enc_vest and enc_therm:
        ratio = enc_vest._activation_ema / max(enc_therm._activation_ema, 1e-6)
        print(f'    reg_oto_x    : {enc_vest._activation_ema:.4f}')
        print(f'    irr_therm_front: {enc_therm._activation_ema:.4f}')
        print(f'    selectivity ratio: {ratio:.1f}x  {health(ratio > 2.0, "target >2.0x")}')

    subsection('Col→Motor 权重')
    col_to_mot = c.bundles_col_to_motor
    axis_w  = [b._memristors[0][0].w for b in col_to_mot if 'cross' not in b.id]
    cross_w = [b._memristors[r][ci].w
               for b in col_to_mot if 'cross' in b.id
               for r in range(b.n_sources) for ci in range(b.n_targets)]
    if axis_w and cross_w:
        ratio = mean(axis_w) / max(mean(cross_w), 1e-6)
        print(f'    axis  w_avg={mean(axis_w):.4f}  spread={std(axis_w):.4f}')
        print(f'    cross w_avg={mean(cross_w):.4f}  max={max(cross_w):.4f}')
        print(f'    axis/cross ratio: {ratio:.2f}x  {health(ratio > 2.0, "target >2.0x")}')

    return c


# ─── Section 2: 热觉链路 ────────────────────────────────────────────────────

def audit_thermal(c, steps=10000, dt=0.001):
    section('SECTION 2: 热觉链路  Soma patches → Enc → Col → Motor')
    print(f'  参数: {steps} steps, dt={dt}  body=[75,20,25]')

    # 确认热源
    print(f'\n  热源: {len(c.world.heat_sources)}')
    for i, s in enumerate(c.world.heat_sources):
        alive = getattr(s, 'alive', True)
        print(f'    src[{i}] pos={[round(p,1) for p in s.position]}  T={s.temperature:.1f}  alive={alive}')

    # 初始皮肤温度
    try:
        env = {}
        for patch in c.world.body.skin_patches:
            wp = patch.world_position(c.world.body)
            env[patch.patch_id] = c.world.temperature_at(wp)
        print(f'\n  初始皮肤温度:')
        for pid, T in env.items():
            print(f'    {pid:<10s}: {T:.4f}')
        if 'left' in env and 'right' in env:
            dT = env['left'] - env['right']
            print(f'    ΔT(left-right) = {dT:+.4f}  {health(abs(dT) > 0.1, "target |ΔT|>0.1")}')
    except Exception as e:
        print(f'  [WARN] 皮肤温度读取失败: {e}')

    t0 = time.time()
    for i in range(steps):
        c.step({}, dt)
    elapsed = time.time() - t0
    print(f'\n  运行耗时: {elapsed:.1f}s')

    subsection('Somatosensory 链路激活')
    soma_neurons = c.somatosensory.get_all_neurons()
    soma_cats = {'thermo': [], 'relay': [], 'noci': [], 'other': []}
    for n in soma_neurons:
        nid = n.config.neuron_id
        if 'thermo' in nid:   soma_cats['thermo'].append(n)
        elif 'relay' in nid:  soma_cats['relay'].append(n)
        elif 'noci' in nid:   soma_cats['noci'].append(n)
        else:                  soma_cats['other'].append(n)

    for cat, neurons in soma_cats.items():
        if neurons:
            acts = [n._activation_ema for n in neurons]
            avg = mean(acts)
            marker = '' if avg > 1e-4 else '  << DEAD'
            print(f'    soma_{cat:<8s}: avg={avg:.4f}  max={max(acts):.4f}  {bar(avg)}{marker}')

    subsection('Enc 热觉层激活')
    therm_enc = {k: n for k, n in c.encoding_neurons.items() if 'therm' in k}
    if therm_enc:
        for k, n in sorted(therm_enc.items()):
            act = n._activation_ema
            marker = '' if act > 1e-4 else '  << DEAD'
            print(f'    {k:<30s}: {act:.4f}  {bar(act)}{marker}')
    else:
        print('    [WARN] encoding_neurons 中无 therm 键')

    subsection('Col 热觉层激活')
    therm_col = {k: n for k, n in c.column_neurons.items() if 'therm' in k}
    if therm_col:
        for k, n in sorted(therm_col.items()):
            act = n._activation_ema
            v   = n._membrane.voltage
            marker = '' if act > 1e-4 else '  << DEAD'
            print(f'    col_{k:<25s}: act={act:.4f}  V={v:.4f}  {bar(act)}{marker}')
    else:
        print('    [WARN] column_neurons 中无 therm 键')

    subsection('Motor therm bundle 权重分布')
    therm_bundles = [b for b in c.bundles_col_to_motor if 'therm' in b.id]
    if therm_bundles:
        for b in sorted(therm_bundles, key=lambda x: x.id):
            ws = [b._memristors[r][ci].w
                  for r in range(b.n_sources) for ci in range(b.n_targets)]
            print(f'    {b.id:<40s}: w_mean={mean(ws):.5f}  w_max={max(ws):.5f}')
        # 左右对比
        left_b  = [b for b in therm_bundles if 'left'  in b.id]
        right_b = [b for b in therm_bundles if 'right' in b.id]
        if left_b and right_b:
            wl = mean([b._memristors[0][0].w for b in left_b])
            wr = mean([b._memristors[0][0].w for b in right_b])
            spread = abs(wl - wr)
            print(f'\n    left_avg={wl:.5f}  right_avg={wr:.5f}  |Δw|={spread:.5f}  {health(spread > 0.005, "target |Δw|>0.005")}')
    else:
        print('    [WARN] bundles_col_to_motor 中无 therm bundle')

    return c


# ─── Section 3: DA / Shadow 链路 ────────────────────────────────────────────

def audit_da_shadow(c):
    section('SECTION 3: DA / Shadow 链路')

    # DA 电路是否已初始化（需要 ≥1000 步）
    da_init = getattr(c, '_da_circuit_initialized', False)
    print(f'  DA 电路初始化: {da_init}  {health(da_init, "需要 ≥1000 步才触发")}')

    subsection('Shadow 层激活')
    shadow_cats = {'s_enc': [], 's_col': [], 's_mot': []}
    for nid, n in c.shadow_sandbox.neurons.items():
        for cat in shadow_cats:
            if nid.startswith(cat):
                shadow_cats[cat].append(n)
                break

    for cat, neurons in shadow_cats.items():
        if neurons:
            acts = [n._activation_ema for n in neurons]
            avg = mean(acts)
            marker = '' if avg > 1e-4 else '  << DEAD'
            print(f'    {cat:<10s}: avg={avg:.4f}  max={max(acts):.4f}  {bar(avg)}{marker}')

    subsection('Shadow Free Energy (K_ema)')
    k_ema = c.shadow_sandbox._k_ema
    k_hist = c.shadow_sandbox._k_history if hasattr(c.shadow_sandbox, '_k_history') else []
    print(f'    K_ema = {k_ema:.6f}')
    if len(k_hist) >= 2:
        trend = k_hist[-1] - k_hist[0]
        print(f'    K 趋势: {trend:+.6f}  {health(trend < 0.1, "应收敛，正值=发散")}')
    # DEG-P4-003 检查
    print(f'    {health(k_ema < 10.0, "K_ema < 10 (发散阈值)")}')

    subsection('DA 神经元激活')
    da_neurons = list(c.da_neurons.values())
    if da_neurons:
        acts = [n._activation_ema for n in da_neurons]
        vs   = [n._membrane.voltage for n in da_neurons]
        avg_act = mean(acts)
        avg_v   = mean(vs)
        print(f'    DA 神经元数: {len(da_neurons)}')
        print(f'    avg act={avg_act:.4f}  max act={max(acts):.4f}  {bar(avg_act)}')
        print(f'    avg V  ={avg_v:.4f}  max V  ={max(vs):.4f}')
        # D-04 检查：饱和预警
        v_peak_da = da_neurons[0].config.v_peak if hasattr(da_neurons[0].config, 'v_peak') else None
        if v_peak_da is not None:
            saturated = sum(1 for v in vs if v >= v_peak_da * 0.9)
            print(f'    v_peak={v_peak_da:.3f}  ≥90% 饱和: {saturated}/{len(da_neurons)}  {health(saturated == 0, "D-04: 饱和=0")}')
    else:
        print('    [WARN] da_neurons 为空')

    subsection('Shadow→DA Bundle 权重')
    if c.bundles_shadow_to_da:
        for b in c.bundles_shadow_to_da:
            ws = [b._memristors[r][ci].w
                  for r in range(b.n_sources) for ci in range(b.n_targets)]
            print(f'    {b.id:<35s}: w_mean={mean(ws):.4f}  w_max={max(ws):.4f}  n={len(ws)}')
    else:
        print('    [INFO] bundles_shadow_to_da 为空（DA 电路未初始化）')

    subsection('Xin→DA Bundle 权重')
    if c.bundles_xin_to_da:
        for b in c.bundles_xin_to_da:
            ws = [b._memristors[r][ci].w
                  for r in range(b.n_sources) for ci in range(b.n_targets)]
            xin = getattr(b.config, 'xin_tension', 0.0)
            print(f'    {b.id:<35s}: w_mean={mean(ws):.4f}  Xin={xin:.4f}')
    else:
        print('    [INFO] bundles_xin_to_da 为空（DA 电路未初始化）')

    subsection('Xin 积分器状态')
    xin_v = c._xin_integrator.voltage
    xin_relay_act = c._xin_relay._activation_ema
    print(f'    xin_integrator voltage = {xin_v:.6f}')
    print(f'    xin_relay activation   = {xin_relay_act:.6f}  {health(xin_relay_act > 0, "relay 需有信号才能驱动 DA")}')


# ─── Section 4: 热力学健康 ──────────────────────────────────────────────────

def audit_thermodynamics(c, label=''):
    section(f'SECTION 4: 热力学健康 {label}')

    probe = c._noether_probe
    s = probe.summary()

    subsection('Noether 守恒')
    print(f'    violations      : {s["violations"]}  {health(s["violations"] == 0, "== 0")}')
    print(f'    energy balance  : {s["energy"]["balance_avg"]:.6f}  {health(s["energy"]["balance_avg"] < 0.01, "< 0.01")}')
    print(f'    Landauer bound  : {s["xin"]["landauer_ok"]}  {health(s["xin"]["landauer_ok"], "True")}')
    xin_cons = s.get('xin_conservation', {})
    if xin_cons:
        viol = xin_cons.get('violations', 0)
        print(f'    xin_conservation: {viol} violations  {health(viol == 0, "DEG-P4-002 检查")}')

    subsection('熵账本 — 各层平均激活（最近 window）')
    ledger = c._energy_ledger
    report = ledger.summary()
    if report['layers']:
        layer_order = ['L1_MET', 'L2_HC', 'L3_Aff', 'L4_Enc', 'L5_Col', 'L6_Mot',
                       'S_Enc', 'S_Col', 'S_Mot', 'DA',
                       'Soma_Therm', 'Soma_Noci', 'Soma_Relay']
        print(f'    {"Layer":<14s}  {"Avg Act":>8s}  {"Avg Heat":>9s}  {"E trend":>9s}')
        for ln in layer_order:
            if ln in report['layers']:
                L = report['layers'][ln]
                marker = '' if L['avg_activity'] > 1e-4 else '  << DEAD'
                print(f'    {ln:<14s}  {L["avg_activity"]:>8.4f}  {L["avg_heat"]:>9.6f}  {L["energy_trend"]:>+9.4f}{marker}')
    else:
        print('    [WARN] 熵账本 layers 为空（步数不足？）')

    subsection('电压范围检查（量纲 D-03 诊断）')
    all_n = c.get_all_neurons()
    out_of_range = []
    nan_inf = []
    for n in all_n:
        v = n._membrane.voltage
        if math.isnan(v) or math.isinf(v):
            nan_inf.append((n.config.neuron_id, v))
        elif abs(v) > 100:
            out_of_range.append((n.config.neuron_id, v))

    print(f'    NaN/Inf 神经元: {len(nan_inf)}  {health(len(nan_inf) == 0, "必须为 0")}')
    print(f'    |V| > 100 神经元: {len(out_of_range)}  {health(len(out_of_range) == 0, "超出归一化方案")}')
    for nid, v in out_of_range[:5]:
        print(f'      ! {nid}: V={v:.2f}')

    subsection('Column v_peak 量纲 (D-03)')
    col_vpeak = {}
    for k, n in c.column_neurons.items():
        vp = getattr(n.config, 'v_peak', None)
        if vp is not None:
            col_vpeak[k] = vp
    if col_vpeak:
        vp_vals = list(col_vpeak.values())
        print(f'    col v_peak range: [{min(vp_vals):.3f}, {max(vp_vals):.3f}]')
        # 归一化方案：V_th_norm = (V_th_bio - E_K) / (E_Ca - E_K)
        # L2/3 pyramidal: V_th=-52mV → norm=((-52)+80)/130 = 0.215
        n_below_norm = sum(1 for v in vp_vals if v < 0.20)
        print(f'    < 0.20 (低于归一化方案 L2/3 阈值): {n_below_norm}/{len(vp_vals)}  {health(n_below_norm == 0, "D-03")}')


# ─── Section 5: Xin 张力分布 ────────────────────────────────────────────────

def audit_xin(c):
    section('SECTION 5: Xin 张力分布')
    all_b = c.get_all_bundles()
    xin_vals = [(b.id, abs(getattr(b.config, 'xin_tension', 0.0))) for b in all_b]
    xin_vals.sort(key=lambda x: -x[1])

    if not xin_vals:
        print('  [WARN] 无 bundle Xin 数据')
        return

    total_xin = sum(v for _, v in xin_vals)
    print(f'  总 Xin 张力: {total_xin:.2f}')
    print(f'  非零 bundles: {sum(1 for _, v in xin_vals if v > 0)}/{len(xin_vals)}')

    print('\n  Top-10 Xin 张力 bundles:')
    for bid, xin in xin_vals[:10]:
        print(f'    {xin:8.2f}  {bid}')

    print('\n  Bottom-5 Xin 张力 bundles (学习信号最弱):')
    for bid, xin in xin_vals[-5:]:
        print(f'    {xin:8.4f}  {bid}')

    # 热觉 bundle Xin 检查
    therm_xin = [(bid, xin) for bid, xin in xin_vals if 'therm' in bid]
    if therm_xin:
        print(f'\n  热觉 bundle Xin ({len(therm_xin)} 条):')
        for bid, xin in therm_xin:
            print(f'    {xin:8.4f}  {bid}')
    else:
        print('\n  [WARN] 无热觉 bundle Xin（热觉链路 Xin=0 → STDP 无法学习）')


# ─── Section 6: 对齐审计报告 ────────────────────────────────────────────────

def audit_align_issues(c_vest, c_therm):
    section('SECTION 6: 审计报告问题对齐（实测验证）')

    print('\n  ── 结构违规 (V 系列) ──')

    # V-01: Hunger DA
    hunger_da_code = True  # 已知存在
    has_hunger_neuron = hasattr(c_therm, '_hunger_neuron')
    print(f'  V-01 Hunger DA 直接注入: 硬编码存在={hunger_da_code}  HungerNeuron={has_hunger_neuron}  [待修复 P1-A]')

    # V-03: Deviation reflex
    import inspect
    from nexus_v1.circuit import variant_adapter as va_mod
    src = inspect.getsource(va_mod.VariantCircuit.step)
    has_deviation_inject = 'mot._membrane.inject' in src and 'motor_drive' in src
    has_gain = 'DEVIATION_MOTOR_GAIN' in src
    print(f'  V-03 Deviation 语义硬编码: inject存在={has_deviation_inject}  GAIN存在={has_gain}  [待修复 P2]')

    # V-04: Xin relay 量纲
    has_xin_relay_direct = 'self._xin_relay.step(self._xin_integrator.voltage' in src
    print(f'  V-04 Xin relay 电压×电流混用: {has_xin_relay_direct}  [待修复 P2]')

    print('\n  ── 量纲问题 (D 系列) ──')

    # D-01: DEVIATION_MOTOR_GAIN
    gain_line = [l.strip() for l in src.split('\n') if 'DEVIATION_MOTOR_GAIN' in l and '=' in l]
    if gain_line:
        print(f'  D-01 DEVIATION_MOTOR_GAIN: {gain_line[0]}')
        is_1000 = '1000' in gain_line[0]
        print(f'       [FIX-P0-01 已应用: {is_1000}]')

    # D-02: LangevinNoise tau
    try:
        from nexus_v1.components.langevin_noise import LangevinNoise
        import dataclasses
        tau_default = next((f.default for f in dataclasses.fields(LangevinNoise) if f.name == 'tau'), None)
        print(f'  D-02 LangevinNoise tau={tau_default}  {health(tau_default is not None, f"当前={tau_default}")}')
    except Exception as e:
        print(f'  D-02 LangevinNoise tau: 读取失败 ({e})')

    # D-03: Column v_peak (已在 Section 4 中检查)
    vp_sample = getattr(next(iter(c_vest.column_neurons.values())).config, 'v_peak', None)
    print(f'  D-03 Column v_peak 样本: {vp_sample}  {health(vp_sample is not None and vp_sample >= 0.20, "target>=0.20")}')

    # D-04: DA 饱和
    da_ns = list(c_therm.da_neurons.values())
    if da_ns:
        max_da_v = max(n._membrane.voltage for n in da_ns)
        vp_da = getattr(da_ns[0].config, 'v_peak', None)
        saturated = vp_da is not None and max_da_v >= vp_da * 0.9
        print(f'  D-04 DA 电压最大值={max_da_v:.4f}  v_peak={vp_da}  饱和={saturated}  {health(not saturated, "D-04")}')

    print('\n  ── 信息结构 (I 系列) ──')

    # I-01: ThermalMembrane 死调用
    has_dead_sense = 'therm_signal = self.thermal_membrane.sense' in src
    print(f'  I-01 ThermalMembrane.sense() 死调用: {has_dead_sense}  {health(not has_dead_sense, "已删除")}')

    # I-02: grad_dot_v
    has_grad_dot_v = 'grad_dot_v' in src
    has_thermal_alignment = 'thermal_alignment' in src
    print(f'  I-02 grad_dot_v 计算存在: {has_grad_dot_v}  写入 motion_state: {has_thermal_alignment}  {health(has_thermal_alignment, "FIX-P0-04")}')

    # I-03: Hunger DA 对熵账本可见性
    ledger = c_therm._energy_ledger
    has_hunger_in_ledger = any('hunger' in k for k in ledger._layer_activity)
    print(f'  I-03 Hunger DA 在熵账本中: {has_hunger_in_ledger}  {health(has_hunger_in_ledger, "P1-A 修复后可见")}')

    # I-05a: xin_conservation
    probe_s = c_therm._noether_probe.summary()
    xin_viol = probe_s.get('xin_conservation', {}).get('violations', 0)
    print(f'  I-05a xin_conservation violations: {xin_viol}  {health(xin_viol == 0, "DEG-P4-002")}')

    # I-05b: K_ema
    k_ema = c_therm.shadow_sandbox._k_ema
    print(f'  I-05b Shadow K_ema={k_ema:.6f}  {health(k_ema < 10.0, "DEG-P4-003 发散阈值")}')


# ─── Component Registry ─────────────────────────────────────────────────────

def audit_component_registry(c):
    """Scan all live components: TYPE tags, census visibility, idle detection."""
    from nexus_v1.ledger import ComponentRegistry
    section('SECTION CR: 组件注册表审计 (TYPE tags + census visibility)')
    reg = ComponentRegistry()
    reg.scan(c, tick=0)
    reg.print_report()
    s = reg.summary()
    print()
    print(health(s.get('untagged', 0) == 0, f"UNTAGGED组件数 = {s.get('untagged', 0)}"))
    print(f"  Census可见: {s.get('census_visible', 0)}")
    print(f"  隐藏组件:   {s.get('hidden', 0)}  (其中神经/bundle: {s.get('hidden_neural_count', 0)})")
    print(f"  闲置组件:   {s.get('idle', 0)}")
    return reg


# ─── Final Summary ───────────────────────────────────────────────────────────

def print_summary(c_vest, c_therm):
    section('FINAL SUMMARY: 链路健康状态 + 修复优先级')

    # 1. 前庭链路
    vest_enc = c_vest.encoding_neurons.get('reg_oto_x')
    vest_col = c_vest.column_neurons.get('oto_x')
    vest_mot = c_vest.motor_neurons.get('move_x')
    vest_alive = (vest_enc and vest_enc._activation_ema > 0.3 and
                  vest_col and vest_col._activation_ema > 0.3)
    print(f'\n  A. 前庭链路  : {health(vest_alive, "L4 enc={:.3f} col={:.3f}".format(vest_enc._activation_ema if vest_enc else 0, vest_col._activation_ema if vest_col else 0))}')

    # 2. 热觉链路
    therm_col_l = c_therm.column_neurons.get('therm_left')
    therm_col_r = c_therm.column_neurons.get('therm_right')
    therm_alive = (therm_col_l and therm_col_l._activation_ema > 1e-4 and
                   therm_col_r and therm_col_r._activation_ema > 1e-4)
    left_act  = therm_col_l._activation_ema if therm_col_l else 0
    right_act = therm_col_r._activation_ema if therm_col_r else 0
    print(f'  B. 热觉链路  : {health(therm_alive, "col_therm_left={:.4f} right={:.4f}".format(left_act, right_act))}')

    # 3. DA/Shadow
    da_init = getattr(c_therm, '_da_circuit_initialized', False)
    shadow_active = any(n._activation_ema > 1e-4 for n in c_therm.shadow_sandbox.neurons.values())
    da_active = any(n._activation_ema > 1e-4 for n in c_therm.da_neurons.values())
    print(f'  C. Shadow 层 : {health(shadow_active, "neurons active")}')
    print(f'  D. DA 电路   : {health(da_init and da_active, "initialized={} active={}".format(da_init, da_active))}')

    # 4. Noether
    probe_s = c_therm._noether_probe.summary()
    noether_ok = probe_s['violations'] == 0
    print(f'  E. Noether   : {health(noether_ok, "violations={}".format(probe_s["violations"]))}')

    print('\n  ── 修复优先级（基于实测） ──')
    priority = []

    if not therm_alive:
        priority.append(('P0', '热觉链路 col 层死链路 → 检查 v_peak / enc→col bundle 权重'))
    if not shadow_active:
        priority.append(('P0', 'Shadow 层全死 → 检查 shadow_sandbox.initialize() 时序'))
    if not da_init:
        priority.append(('P0', 'DA 电路未初始化 → 步数不足 1000 步？'))

    vp_sample = getattr(next(iter(c_vest.column_neurons.values())).config, 'v_peak', 1.0)
    if vp_sample < 0.20:
        priority.append(('P1-B', f'D-03: col v_peak={vp_sample:.3f} < 0.20 → 需恢复归一化方案值'))

    da_ns = list(c_therm.da_neurons.values())
    if da_ns:
        max_da_v = max(n._membrane.voltage for n in da_ns)
        vp_da = getattr(da_ns[0].config, 'v_peak', None)
        if vp_da and max_da_v >= vp_da * 0.9:
            priority.append(('P1-B', f'D-04: DA 饱和 V={max_da_v:.3f} ≥ 0.9×v_peak={vp_da:.3f}'))

    k_ema = c_therm.shadow_sandbox._k_ema
    if k_ema > 1.0:
        priority.append(('P2', f'I-05b: Shadow K_ema={k_ema:.4f} 偏高 → 检查 ShadowSandbox 衰减'))

    priority.append(('P1-A', 'V-01: Hunger DA 直接注入 → HungerDriveNeuron 结构重建'))
    priority.append(('P2',   'V-03: Deviation reflex 语义硬编码 → DeviationRelayNeuron'))
    priority.append(('P2',   'V-04: Xin relay 量纲混用 → XinIntegratorNeuron 适配器'))

    for pri, desc in priority:
        print(f'    [{pri:5s}] {desc}')


# ─── Main ────────────────────────────────────────────────────────────────────

def main():
    print('=' * 72)
    print('  cell-cc-other 全链路熵账本审计')
    print(f'  工作目录: {os.getcwd()}')
    print('=' * 72)

    t_total = time.time()

    # ── Phase 1: 前庭电路 ──────────────────────────────────────────────────
    print('\n[Phase 1] 初始化前庭审计电路...')
    c_vest = make_vestibular_circuit()
    cats, bcat = audit_census(c_vest)
    audit_vestibular(c_vest, steps=10000, dt=1.0)
    audit_thermodynamics(c_vest, label='(前庭电路 10k steps dt=1.0)')

    # ── Phase 2: 热觉电路 ──────────────────────────────────────────────────
    print('\n[Phase 2] 初始化热觉审计电路（body@[75,20,25]）...')
    c_therm = make_thermal_circuit()
    audit_thermal(c_therm, steps=10000, dt=0.001)
    audit_da_shadow(c_therm)
    audit_thermodynamics(c_therm, label='(热觉电路 10k steps dt=0.001)')
    audit_xin(c_therm)

    # ── Phase 3: 问题对齐 ─────────────────────────────────────────────────
    audit_align_issues(c_vest, c_therm)

    # ── Phase 4: 组件注册表 ───────────────────────────────────────────────
    audit_component_registry(c_vest)

    # ── Final ─────────────────────────────────────────────────────────────
    print_summary(c_vest, c_therm)

    elapsed = time.time() - t_total
    print(f'\n  总耗时: {elapsed:.1f}s')
    print('=' * 72)


if __name__ == '__main__':
    main()
