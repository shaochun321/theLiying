# 半导体物理层重建 — 任务追踪

## Phase 1: semiconductor.py
- [x] Capacitor (charge, inject, leak, discharge_to)
- [x] MOSFET (conduct with exponential subthreshold, adapt_threshold)
- [x] Memristor (w, conduct, update STDP)
- [x] PowerRail (draw, v_actual, power_dissipated)

## Phase 2: MetaNeuron 半导体化
- [x] 新增 _membrane, _gate, _power 字段
- [x] 重写 activate() → 电路模型
- [x] 重写 decay() → RC leak + Vth drift + hunger ceiling
- [x] 向后兼容 (threshold, energy, activation 同步)

## Phase 3: Bundle Memristor 化
- [x] weights → _memristors array (init_weights 同步初始化)
- [x] propagate() 保持 weights 兼容 (STDP 写 weights)
- [x] inject_pulse / deliver_pulses 延迟传播 (原有)

## Phase 4: 代谢环流修复
- [x] Bug #1: CPG tonic drive → membrane charge
- [x] Bug #2: hunger ceiling 同步降低 floor (via _hunger_ceiling)
- [x] Bug #3: basal consumption capped (防止 pool 瞬间耗尽)
- [x] Bug #4: 指数亚阈值 (MOSFET.conduct exp-1 形式)

## Phase 5: 涌现测试 ✅ 6/6
- [x] ✅ 饥饿→Vth↓ (ratio=0.5575, hungry Vth < fed Vth)
- [x] ✅ 权重分化 (4.80x differentiation)
- [x] ✅ Landauer 学习约束 (high=1.0 > low=0.5)
- [x] ✅ 空间功能分化 (enc=0.020 vs col=0.002)
- [x] ✅ 学习稀疏化 (70% near 0, 16.7% near 1)
- [x] ✅ CPG-代谢耦合 (fed=0.010 vs starved=0.038)
