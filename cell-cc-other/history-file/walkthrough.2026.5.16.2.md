# v40.7 结构动力学 — 完整 Walkthrough

## 核心原则：Structural Dynamics Invariant

写入 `hebbian_circuit.py` 模块顶部作为项目底色：

```
元结构中的每个字段必须满足三元不变量：
  1. GENERATION — 有机制创建/增加值
  2. DECAY — 有机制减少/耗散值  
  3. STRUCTURAL COUPLING — 值影响至少一个相邻结构的字段
```

---

## 实现进展总览

| 版本 | 核心变化 | avg_cos | 物理标志 |
|------|---------|:-------:|---------|
| v40.6 | 基线（静态标签） | 0.329 | — |
| v40.7a | Column 不对称物理 + 果实 trace | 0.334 | PRP 出现 |
| v40.7b | STDP 疲劳/恢复 + PRP 适应 | 0.246 | cos(m,g)=0.006 |
| v40.7c | resting potential + energy + inertia 动力学 | 0.194 | 能量循环建立 |
| v40.7d | heat_output + activation_count + plasticity 链路闭合 | 0.191 | PRP 分化 |
| v40.7e | 收敛子流形检测（ACC 代理） | 0.337 | 12 个 conv_nodes |
| **v40.7f** | push-pull 对比 + bundle inertia 恢复 | **0.305** | **6 果实激活** |

---

## Phase 1: Column ≠ Spine (不对称物理法则)

Column 神经元通过 `try_mature()` 获得三种 Spine 不具备的物理行为：

1. **Lateral Suppression** — calcium 驱动的 basket cell 代理，推高邻近 Spine threshold
2. **Asymmetric STDP** — LTP boost 2× (可疲劳/可恢复的突触囊泡代理)
3. **PRP Emission** — calcium > threshold 时发射蛋白信号，被 dormant fruit 捕获

## Phase 2: 果实化学衰减 (时间信用分配)

Dormant fruit 的 `trace_strength` 按三因子调制衰减：
- 高 Xin tension（预测残差大）→ 衰减慢（保留重要错误）
- 低 Xin tension → 衰减快（忘记不重要的错误）
- PRP 捕获 → 延长 trace 寿命

## Phase 3: 共享子流形结构化 (收敛检测)

`_update_convergence()` 在 maintain() 中运行：
1. 扫描 z_t 维度的共激活对
2. 更新运行中的共激活矩阵（EMA）
3. 超过阈值 → 创建 convergence node（结构实体）
4. **Push-pull coupling (v40.7f)**:
   - **Prime**: 共享维度 threshold ↓（更容易激活）
   - **Contrast**: 排他维度 threshold ↑（更 selective）
5. 节点衰减（0.99/tick）→ 不被强化的子流形被遗忘

## 完整动力学链路

### MetaNeuron (所有字段完整)

| 字段 | 生成 | 衰减 | 耦合 |
|------|------|------|------|
| activation | activate() | decay() → rest | 驱动全部下游 |
| resting_potential | activation_ema | 向 0 衰减 | decay 目标 + inertia |
| calcium | |activation| 积分 | → target 衰减 | threshold/PRP/suppression |
| threshold | ca > target | ca < target | gate activation |
| energy | calcium 恢复 | transport + activate | is_alive() |
| inertia | stable +0.001 | volatile -0.001 | STDP/activate 分母 |
| stdp_ltp_boost | 向 base 恢复 | STDP 使用消耗 | LTP 乘数 |
| prp_emission | calcium 门控 | ×0.95 | 果实 trace 捕获 |
| prp_threshold | 初始化 | 向 ca×1.5 适应 | PRP 门控 |
| heat_output | activate() | maintain() 消费 | _temperature |
| activation_count | activate() | — (单调) | try_mature() 门控 |
| plasticity | maturation | — (属性) | STDP 学习率 |

### MetaSynapticBundle (所有字段完整)

| 字段 | 生成 | 衰减 | 耦合 |
|------|------|------|------|
| weights | STDP LTP | STDP LTD | propagate() |
| bundle_strength | weights 均值 | pruning | circulation |
| **bundle_inertia** | stable 恢复 +0.005 | STDP delta -0.01 | STDP/propagate 分母 |
| transport_cost | propagate | 每 tick 重算 | source energy 消耗 |
| xin_tension | accumulate_xin | 果实激活清零 | 果实 trace 调制 |
| dormant_fruit | tension > 0.5 | trace 衰减 | PRP + 三因子 |

---

## 15 个降级代理模块

```
degraded_from                                      → 代理实现
────────────────────────────────────────────────────────────────
basket_cell_interneuron_dynamics                   → calcium-scaled threshold push
protein_synthesis_and_diffusion_dynamics            → direct emission/capture
dopaminergic_modulation_of_eligibility_traces       → Xin tension magnitude
presynaptic_vesicle_release_probability             → linear depletion
synaptic_vesicle_pool_recycling                     → exponential recovery
transcription_factor_regulation                     → slow EMA
mitochondrial_ATP_synthesis                         → calcium-proportional recovery
axonal_transport_ATP_consumption                    → proportional drain (inter)
dendritic_transport_ATP_consumption                 → proportional drain (intra)
voltage_gated_ion_channel_redistribution            → slow EMA of activation
perineuronal_net_formation_and_degradation          → activation variance driven
local_substrate_thermodynamics                      → external entropy ledger
local_metabolic_heat_dissipation                    → sum aggregation
oligodendrocyte_myelination_dynamics                → delta-gated recovery
ACC_push_pull_conflict_monitoring                   → co-activation matrix + contrast
```

## 修改的文件

### [hebbian_circuit.py](file:///D:/cell-cc/Morphosphere_v37_0_native_runtime_prototype_flat_complete/morphosphere_v2pp/engines/hebbian_circuit.py)

```diff:hebbian_circuit.py
"""Morphosphere v40 — Hebbian Circuit: Neural System Embedded in Hypergraph.

Architecture Document Reference: implementation_plan.md §1-§5

Design Goals (v40):
  1. MetaNeuron / MetaSynapticBundle / CircuitLayer as core primitives
  2. Spine-layer T/O/P/R/Xin lifecycle on the circuit itself
  3. Shadow dormant-fruit mechanism (replaces tombstone-only model)
  4. Substrate heat exchange delegated to external entropy ledger (annotated)
  5. Solve: W_signal discrimination failure via structural transport feedback
  6. Solve: Defense layer mismatch via circuit-level hysteresis

Degraded components (annotated inline with DEGRADED markers):
  - Substrate → delegated to external entropy ledger
  - Column layer learning → exponential moving average (not BCM)
  - Circulation detection → depth-limited DFS (not full homology)
  - P/R competition → Top-2 selection (not full energy competition)
  - MeasureCoordinate → retained as proxy (not emergent coordinate)
"""
from __future__ import annotations
import math, uuid, json
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple, Any
from datetime import datetime, timezone

def _now(): return datetime.now(timezone.utc).isoformat()
def _uid(p): return f"{p}_{uuid.uuid4().hex[:8]}"


# ═══════════════════════════════════════════════════════════════
# 1. MetaNeuron — Computational node in the Hebbian circuit
# ═══════════════════════════════════════════════════════════════

@dataclass
class MetaNeuron:
    """A computational node in the Hebbian circuit-hypergraph.

    v40.1: Three structural plasticity mechanisms from real neural circuits:

    1. STDP Traces (Spike-Timing-Dependent Plasticity):
       - pre_trace/post_trace: exponentially-decaying timing memory
       - Replaces Oja correlation with causal timing relationships

    2. Homeostatic Target Rate (calcium-based feedback):
       - target_rate: desired average activation (neural set-point)
       - calcium: slow-integrated activity sensor (like Ca²⁺)
       - Prevents runaway excitation or silencing

    3. Intrinsic Excitability (memristor conductance analogy):
       - threshold: dynamic gating level (adapts homeostatically)
       - Input < threshold → leak current only; > threshold → full pass
       - Creates stimulus-selective response profiles

    Energy: DEGRADED to entropy ledger proxy (annotated).
    """
    neuron_id: str
    layer_id: str

    # ── Core state ──
    activation: float = 0.0
    resting_potential: float = 0.0
    potential: float = 0.0       # Φ: accumulated history
    inertia: float = 1.0        # M: resistance to change

    # ── STDP Traces ──
    pre_trace: float = 0.0      # x_i(t): incremented on input, decays
    post_trace: float = 0.0     # y_j(t): incremented on output, decays
    trace_tau_pre: float = 20.0
    trace_tau_post: float = 20.0

    # ── Homeostatic regulation ──
    target_rate: float = 0.03   # desired average activation
    calcium: float = 0.03       # slow-integrated activity (Ca²⁺ proxy)
    calcium_tau: float = 20.0   # integration time constant (faster feedback)

    # ── Intrinsic excitability (memristor conductance) ──
    threshold: float = 0.003    # dynamic firing threshold
    threshold_adapt_rate: float = 0.01   # fast adaptation (like fast homeostasis)

    # ── Metabolic state ──
    # DEGRADED: energy managed by external entropy ledger proxy
    energy: float = 1.0
    heat_output: float = 0.0

    # ── Maturation ──
    maturation: str = "spine"
    activation_count: int = 0

    # ── Proxy slot ──
    proxy_for: Optional[str] = None
    is_proxy_host: bool = False

    @property
    def plasticity(self) -> float:
        return {"spine": 0.18, "column": 0.01, "area": 0.001}.get(
            self.maturation, 0.18)

    @property
    def decay_rate(self) -> float:
        return {"spine": 0.025, "column": 0.005, "area": 0.001}.get(
            self.maturation, 0.025)

    def activate(self, input_signal: float) -> float:
        """Threshold-gated activation (memristor conductance model).

        Input < threshold → leak (0.1×). Input ≥ threshold → pass.
        This creates per-neuron selectivity: each neuron's threshold
        adapts homeostatically, so different neurons respond to
        different input magnitudes.
        """
        effective = input_signal / max(self.inertia, 0.5)
        if abs(effective) < self.threshold:
            self.activation = effective * 0.1  # sub-threshold leak
        else:
            sign = 1.0 if effective >= 0 else -1.0
            self.activation = sign * (abs(effective) - self.threshold)

        self.activation_count += 1
        self.pre_trace += 1.0  # mark timing for STDP

        # Calcium: slow activity integrator (homeostasis sensor)
        self.calcium += (abs(self.activation) - self.calcium) / self.calcium_tau

        # Energy cost → entropy ledger proxy
        cost = abs(self.activation) * 0.01
        self.heat_output = cost
        self.energy = max(0.0, self.energy - cost)
        return self.activation

    def post_activate(self):
        """Mark output timing for STDP (called after downstream use)."""
        self.post_trace += 1.0

    def decay(self):
        """Per-tick: activation decay, trace decay, homeostatic adaptation."""
        rate = self.decay_rate
        self.activation += rate * (self.resting_potential - self.activation)
        self.potential += abs(self.activation) * 0.01

        # STDP trace exponential decay
        self.pre_trace *= (1.0 - 1.0 / max(self.trace_tau_pre, 1.0))
        self.post_trace *= (1.0 - 1.0 / max(self.trace_tau_post, 1.0))

        # Homeostatic threshold adaptation
        # calcium > target → too active → raise threshold
        # calcium < target → too quiet → lower threshold
        error = self.calcium - self.target_rate
        self.threshold += self.threshold_adapt_rate * error
        self.threshold = max(0.0001, min(0.5, self.threshold))  # near-zero floor

    def try_mature(self, column_threshold: float = 50.0,
                   area_threshold: float = 500.0):
        """Maturation: spine → column → area."""
        if self.maturation == "spine" and self.potential > column_threshold:
            self.maturation = "column"
            self.inertia = max(self.inertia, 2.0)
            self.threshold_adapt_rate *= 0.5
        elif self.maturation == "column" and self.potential > area_threshold:
            self.maturation = "area"
            self.inertia = max(self.inertia, 5.0)
            self.threshold_adapt_rate *= 0.1

    def is_alive(self) -> bool:
        return self.energy > 0.0


# ═══════════════════════════════════════════════════════════════
# 2. MetaSynapticBundle — Hyperedge connecting neuron sets
# ═══════════════════════════════════════════════════════════════

@dataclass
class MetaSynapticBundle:
    """A hyperedge: directed connection from source neuron SET to target SET.

    Unlike a simple edge (A→B), a bundle connects {A,B,C} → {D,E}.
    This is the 'hyper' in hypergraph.

    The bundle has:
      - weight matrix: weights[i][j] = source[i] → target[j]
      - bundle_strength: aggregate strength (below threshold → pruning)
      - bundle_inertia: resistance to weight change
      - transport_cost: cost of propagation through this bundle
      - xin_tension: prediction residual curled on this edge
    """
    bundle_id: str
    source_neuron_ids: List[str]
    target_neuron_ids: List[str]

    # ── Weight tensor ──
    weights: List[List[float]] = field(default_factory=list)

    # ── Bundle-level properties ──
    bundle_strength: float = 1.0
    bundle_inertia: float = 1.0
    transport_cost: float = 0.0

    # ── Learning ──
    learning_rule: str = "oja"   # "oja" | "frozen"
    last_pre_activation: float = 0.0
    last_post_activation: float = 0.0

    # ── Xin tension (§3.3: prediction residual curled on this edge) ──
    xin_tension: float = 0.0    # > 0 = expected but didn't happen
    xin_dormant_fruit: Optional[Dict] = None  # shadow fruit if tension persists

    # ── Degradation annotation ──
    degraded_features: List[str] = field(default_factory=list)

    def init_weights(self):
        """Initialize weight matrix if empty."""
        if not self.weights:
            n_src = len(self.source_neuron_ids)
            n_tgt = len(self.target_neuron_ids)
            # Small uniform initialization
            self.weights = [
                [0.1 + 0.02 * ((i * 7 + j) % 5) for j in range(n_tgt)]
                for i in range(n_src)
            ]

    def propagate(self, source_activations: List[float]) -> List[float]:
        """Forward propagation: source activations → target activations."""
        self.init_weights()
        n_tgt = len(self.target_neuron_ids)
        target_acts = [0.0] * n_tgt
        total_pre = 0.0

        for i, a_pre in enumerate(source_activations):
            if i >= len(self.weights):
                break
            total_pre += abs(a_pre)
            for j in range(n_tgt):
                if j < len(self.weights[i]):
                    target_acts[j] += self.weights[i][j] * a_pre

        self.last_pre_activation = total_pre / max(len(source_activations), 1)
        self.last_post_activation = sum(abs(a) for a in target_acts) / max(n_tgt, 1)

        # Transport cost = propagation effort
        self.transport_cost = total_pre * 0.01 / max(self.bundle_inertia, 0.5)
        return target_acts

    def stdp_update(self, pre_neurons: List['MetaNeuron'],
                    post_neurons: List['MetaNeuron'],
                    eta_scale: float = 1.0):
        """STDP learning rule: weight change depends on timing traces.

        Based on computational STDP (Bi & Poo 1998, Song et al 2000):
          - pre fires before post (pre_trace high when post fires):
            → LTP (potentiation): ΔW = +A+ × pre_trace
          - post fires before pre (post_trace high when pre fires):
            → LTD (depression): ΔW = -A- × post_trace

        This replaces Oja's simple correlation with causal timing,
        which creates direction-selective weight patterns: synapses
        that consistently CAUSE downstream activity get strengthened,
        while synapses that are uncorrelated or anti-causal get weakened.

        Structural plasticity effects:
          - Weights that grow → bundle_strength increases → bundle consolidates
          - Weights that shrink → bundle_strength decreases → pruning candidate
          - If bundle_strength drops below threshold → structural pruning
        """
        if self.learning_rule == "frozen":
            return 0.0
        self.init_weights()

        A_plus = 0.01 * eta_scale    # LTP rate
        A_minus = 0.012 * eta_scale  # LTD rate (slightly stronger → stability)
        total_delta = 0.0

        for i, pre_n in enumerate(pre_neurons):
            if i >= len(self.weights):
                break
            for j, post_n in enumerate(post_neurons):
                if j >= len(self.weights[i]):
                    break

                # STDP: weight change = f(timing traces)
                # LTP: pre was recently active when post fires
                ltp = A_plus * pre_n.pre_trace * abs(post_n.activation)
                # LTD: post was recently active when pre fires
                ltd = A_minus * post_n.post_trace * abs(pre_n.activation)

                delta = (ltp - ltd) / max(self.bundle_inertia, 0.5)

                # Weight-dependent scaling (multiplicative STDP):
                # Near w_max → LTP slows; near w_min → LTD slows
                w = self.weights[i][j]
                if delta > 0:
                    delta *= (1.0 - w)  # closer to max → less potentiation
                else:
                    delta *= w           # closer to min → less depression

                self.weights[i][j] = max(0.0, min(1.0, w + delta))
                total_delta += abs(delta)

        # Update bundle strength (structural health indicator)
        flat = [self.weights[i][j]
                for i in range(len(self.weights))
                for j in range(len(self.weights[i]))]
        self.bundle_strength = sum(flat) / max(len(flat), 1)

        # Update conductance state (memristor analogy)
        # Total activity through this bundle → conductance increases
        self._conductance_history = getattr(self, '_conductance_history', 0.0)
        self._conductance_history += total_delta
        self.bundle_inertia = max(0.5, self.bundle_inertia - total_delta * 0.01)

        return total_delta

    # Keep backward compat
    def hebbian_update(self, pre_acts, post_acts, eta_scale=1.0):
        """Legacy interface — delegates to stdp_update when neurons available."""
        # Fallback to simplified Oja when no neuron objects available
        if self.learning_rule == "frozen":
            return 0.0
        self.init_weights()
        eta = 0.01 * eta_scale / max(self.bundle_inertia, 0.5)
        total_delta = 0.0
        for i in range(min(len(pre_acts), len(self.weights))):
            for j in range(min(len(post_acts), len(self.weights[i]))):
                delta = eta * pre_acts[i] * (
                    post_acts[j] - self.weights[i][j] * pre_acts[i])
                self.weights[i][j] = max(0.0, min(1.0,
                    self.weights[i][j] + delta))
                total_delta += abs(delta)
        flat = [self.weights[i][j]
                for i in range(len(self.weights))
                for j in range(len(self.weights[i]))]
        self.bundle_strength = sum(flat) / max(len(flat), 1)
        return total_delta

    def should_prune(self, threshold: float = 0.02) -> bool:
        """Structural pruning: considers weight AND recent activity.

        A bundle is pruned if:
          - bundle_strength < threshold (weights too weak), AND
          - no recent conductance growth (not actively learning)
        """
        conductance = getattr(self, '_conductance_history', 0.0)
        return self.bundle_strength < threshold and conductance < 0.001

    def accumulate_xin(self, predicted: float, actual: float):
        """Accumulate Xin tension (§3.3)."""
        self.xin_tension += (predicted - actual)
        # If tension persists → create dormant fruit
        if abs(self.xin_tension) > 0.5 and self.xin_dormant_fruit is None:
            self.xin_dormant_fruit = {
                "tension_at_creation": self.xin_tension,
                "bundle_id": self.bundle_id,
                "created_at": _now(),
                "state": "dormant",
            }

    def try_activate_fruit(self, bias_signal: float) -> Optional[Dict]:
        """If bias aligns with dormant fruit tension → activate it."""
        if self.xin_dormant_fruit is None:
            return None
        tension = self.xin_dormant_fruit["tension_at_creation"]
        # Bias in same direction as tension → fruit ripens
        if tension * bias_signal > 0 and abs(bias_signal) > 0.3:
            fruit = self.xin_dormant_fruit.copy()
            fruit["state"] = "activated"
            fruit["activated_at"] = _now()
            fruit["activation_bias"] = bias_signal
            self.xin_dormant_fruit = None
            self.xin_tension = 0.0
            return fruit
        return None


# ═══════════════════════════════════════════════════════════════
# 3. CircuitLayer — A layer of neurons + internal bundles
# ═══════════════════════════════════════════════════════════════

@dataclass
class CircuitLayer:
    """One layer of the Hebbian circuit."""
    layer_id: str
    neurons: Dict[str, MetaNeuron] = field(default_factory=dict)
    bundles: List[MetaSynapticBundle] = field(default_factory=list)

    def add_neuron(self, neuron_id: str, **kwargs) -> MetaNeuron:
        n = MetaNeuron(neuron_id=neuron_id, layer_id=self.layer_id, **kwargs)
        self.neurons[neuron_id] = n
        return n

    def add_bundle(self, source_ids: List[str], target_ids: List[str],
                   **kwargs) -> MetaSynapticBundle:
        b = MetaSynapticBundle(
            bundle_id=_uid("bundle"),
            source_neuron_ids=source_ids,
            target_neuron_ids=target_ids,
            **kwargs)
        b.init_weights()
        self.bundles.append(b)
        return b

    def get_activations(self) -> Dict[str, float]:
        return {nid: n.activation for nid, n in self.neurons.items()}


# ═══════════════════════════════════════════════════════════════
# 4. HebbianCircuit — The full circuit with T/O/P/R/Xin
# ═══════════════════════════════════════════════════════════════

class HebbianCircuit:
    """Multi-layer Hebbian circuit embedded in a hypergraph topology.

    The circuit has its own T/O/P/R/Xin lifecycle:
      T = activation propagation along hyperedges (with dissipation)
      O = measurable configuration change (observable from outside)
      P = primary circulation (winner-take-most closed path)
      R = secondary competing circulation
      Xin = prediction residual curled as tension on edges

    DEGRADED: Substrate heat exchange delegated to external entropy ledger.
    degraded_from = "local_substrate_thermodynamics"

    Solves:
      - W_signal discrimination: transport feedback flows into encoding layer
      - Defense layer mismatch: circuit-level hysteresis on bundle updates
    """

    def __init__(self, entropy_ledger_proxy=None):
        self.layers: Dict[str, CircuitLayer] = {}
        self.inter_layer_bundles: List[MetaSynapticBundle] = []
        self.tick = 0

        # DEGRADED: Substrate → external entropy ledger proxy
        # degraded_from = "local_substrate_thermodynamics"
        self._entropy_ledger_proxy = entropy_ledger_proxy
        self._temperature = 1.0
        self._free_energy = 10.0
        self._total_heat = 0.0

        # T/O/P/R/Xin state
        self._transport_log: List[Dict] = []
        self._observable_delta: float = 0.0
        self._p_circulation: Optional[List[str]] = None  # bundle_id path
        self._r_circulation: Optional[List[str]] = None
        self._xin_tensions: Dict[str, float] = {}  # bundle_id → tension
        self._activated_fruits: List[Dict] = []

        # Audit
        self._audit: List[Dict] = []

    def add_layer(self, layer_id: str) -> CircuitLayer:
        layer = CircuitLayer(layer_id=layer_id)
        self.layers[layer_id] = layer
        return layer

    def add_inter_layer_bundle(self, source_layer: str, source_ids: List[str],
                                target_layer: str, target_ids: List[str],
                                **kwargs) -> MetaSynapticBundle:
        b = MetaSynapticBundle(
            bundle_id=_uid("ilb"),
            source_neuron_ids=source_ids,
            target_neuron_ids=target_ids,
            **kwargs)
        b.init_weights()
        self.inter_layer_bundles.append(b)
        return b

    # ─── T: Transport (activation propagation) ───

    def transport(self, input_activations: Dict[str, float],
                  input_layer: str) -> Dict[str, float]:
        """T-phase: propagate activations through the circuit.

        Returns: output activations from the last layer.
        """
        layer = self.layers.get(input_layer)
        if not layer:
            return {}

        # Inject inputs
        for nid, val in input_activations.items():
            if nid in layer.neurons:
                layer.neurons[nid].activate(val)

        # Propagate through intra-layer bundles
        tick_heat = 0.0
        for bundle in layer.bundles:
            src_acts = [layer.neurons[sid].activation
                        for sid in bundle.source_neuron_ids
                        if sid in layer.neurons]
            if not src_acts:
                continue
            tgt_acts = bundle.propagate(src_acts)
            # Apply to target neurons
            for j, tid in enumerate(bundle.target_neuron_ids):
                if tid in layer.neurons and j < len(tgt_acts):
                    layer.neurons[tid].activate(tgt_acts[j])
            tick_heat += bundle.transport_cost

        # Propagate through inter-layer bundles
        for bundle in self.inter_layer_bundles:
            src_layer = None
            for lid, l in self.layers.items():
                if bundle.source_neuron_ids[0] in l.neurons:
                    src_layer = l
                    break
            if src_layer is None:
                continue
            src_acts = [src_layer.neurons.get(sid, MetaNeuron("_","_")).activation
                        for sid in bundle.source_neuron_ids]
            tgt_acts = bundle.propagate(src_acts)
            for lid, l in self.layers.items():
                for j, tid in enumerate(bundle.target_neuron_ids):
                    if tid in l.neurons and j < len(tgt_acts):
                        l.neurons[tid].activate(tgt_acts[j])
            tick_heat += bundle.transport_cost

        # ── Lateral inhibition (structural discrimination mechanism) ──
        # In real neural circuits (V1, barrel cortex), the most activated
        # neuron in a population suppresses its neighbors via inhibitory
        # interneurons. This creates stimulus selectivity: different inputs
        # activate DIFFERENT dominant neurons.
        #
        # Inhibition strength is modulated by entropy ledger temperature:
        #   high temperature → weak inhibition (exploratory, broad tuning)
        #   low temperature  → strong inhibition (sharp, narrow tuning)
        self._apply_lateral_inhibition(layer)

        # DEGRADED: heat → entropy ledger proxy
        self._total_heat += tick_heat
        self._temperature = self._total_heat / max(self.tick + 1, 1)

        self._transport_log.append({
            "tick": self.tick, "heat": tick_heat,
            "temperature": self._temperature,
        })

        return layer.get_activations()

    # ─── O: Observable (measurable configuration change) ───

    def observe(self) -> Dict[str, Any]:
        """O-phase: compute observable state change."""
        total_activation = 0.0
        total_neurons = 0
        for layer in self.layers.values():
            for n in layer.neurons.values():
                total_activation += abs(n.activation)
                total_neurons += 1

        prev_delta = self._observable_delta
        self._observable_delta = total_activation / max(total_neurons, 1)
        return {
            "observable_activation": self._observable_delta,
            "delta_from_prev": self._observable_delta - prev_delta,
            "temperature": self._temperature,
            "tick": self.tick,
        }

    # ─── Lateral Inhibition (structural discrimination) ───

    def _apply_lateral_inhibition(self, layer: CircuitLayer):
        """Apply lateral inhibition among target (z_t) neurons.

        Biological basis: In cortical circuits, excitatory neurons activate
        inhibitory interneurons which suppress neighboring excitatory neurons.
        The result: the most strongly activated neuron "wins" and the others
        are relatively suppressed. This creates stimulus selectivity.

        Mechanism:
          1. Find all target neurons (z_t dimensions) in the layer
          2. Compute mean activation
          3. Suppress neurons below mean, boost neurons above mean
          4. Strength modulated by temperature (entropy ledger proxy)

        The inhibition creates DIRECTION changes in the z_t vector — different
        stimuli will have different winner neurons, breaking the trivial
        resonance (cos > 0.998) that plagued the flat W_signal.
        """
        # Identify target neurons (z_t cost dimensions)
        target_ids = ["transition", "drift", "gamma_desync",
                      "xin_residual", "potential_disp", "churn", "magnitude"]
        targets = [(nid, layer.neurons[nid])
                   for nid in target_ids if nid in layer.neurons]
        if len(targets) < 2:
            return

        activations = [max(0.0, n.activation) for _, n in targets]

        # ── Divisive Normalization (Carandini & Heeger 2012) ──
        # R_i = x_i^n / (σ^n + Σ_j x_j^n)
        #
        # This is the canonical cortical gain control model:
        # - Each neuron's response is divided by the total pool activity
        # - Weak responses remain positive (just proportionally smaller)
        # - σ (semi-saturation constant) prevents division by zero and
        #   controls how much suppression occurs at low activity
        #
        # Temperature modulates n (exponent):
        # - Cold → high n → sharp selectivity (winner takes more)
        # - Hot → low n → flat (exploratory, everyone gets some)
        temp = max(self._temperature, 0.001)
        n_exp = min(3.0, max(1.0, 0.02 / temp))  # exponent: 1.0-3.0

        # Semi-saturation constant: controls baseline suppression
        sigma_n = 0.01 ** n_exp  # small σ → strong normalization

        # Compute x_i^n for each neuron
        powered = [max(0.0, a) ** n_exp for a in activations]
        pool_sum = sum(powered) + sigma_n  # denominator

        for i, (nid, neuron) in enumerate(targets):
            if pool_sum > 0 and activations[i] > 0:
                neuron.activation = powered[i] / pool_sum
            else:
                neuron.activation = 0.0

        # ── Stage 2: Mild subtractive contrast (post-normalization) ──
        # After divisive normalization, all values sum to ~1.
        # Apply mild contrast enhancement to sharpen differences.
        # This is gentler than raw subtractive because we start from
        # normalized proportions, not raw values.
        norm_acts = [n.activation for _, n in targets]
        norm_mean = sum(norm_acts) / len(norm_acts)
        contrast = 0.3  # mild: preserve 70% of original + 30% contrast
        for nid, neuron in targets:
            dev = neuron.activation - norm_mean
            neuron.activation = neuron.activation + contrast * dev
            neuron.activation = max(0.0, neuron.activation)


    # ─── P/R: Circulation Measure (probabilistic hypergraph integral) ───

    def detect_circulations(self) -> Tuple[Optional[List[str]],
                                            Optional[List[str]]]:
        """Compute the circulation measure μ(G) of the entire Hebbian hypergraph.

        ALL circulations — active, dormant, pruned — contribute to ONE
        probability measure. Each circuit path's contribution is weighted
        by its structural occupation:

          μ(G) = Σ_cycle_i  ω_i · Π_{bundle ∈ cycle_i} s(bundle)

        where:
          ω_i = occupation probability = s(bundle) / Σ_all s(bundle)
          s(bundle) = bundle_strength for active bundles
                    = ghost_strength for pruned bundles (0 < ghost << 1)
                    = dormant_value for fruit-bearing bundles

        The primary circulation P is the maximum-flow path;
        the secondary R is the runner-up. But critically:

          P.value = Σ_all μ_i   (P CONTAINS all secondary values)

        This means P is not just "the strongest path" but the integral
        of the entire structure's information occupation in the long window.
        Dormant fruits and ghost residuals contribute their curled values
        to P, making P the total structural fingerprint.
        """
        all_bundles = []
        ghost_bundles = []
        for layer in self.layers.values():
            all_bundles.extend(layer.bundles)
            # Ghost bundles: residuals of pruned bundles (low-probability states)
            ghost_bundles.extend(getattr(layer, '_ghost_bundles', []))
        all_bundles.extend(self.inter_layer_bundles)

        if not all_bundles and not ghost_bundles:
            self._p_circulation = None
            self._r_circulation = None
            self._circulation_measure = 0.0
            return None, None

        # ── Compute structural occupation probability per bundle ──
        # All bundles (active + ghost) contribute to the total measure
        total_strength = sum(b.bundle_strength for b in all_bundles) + \
                         sum(g.get("ghost_strength", 0.001) for g in ghost_bundles)
        total_strength = max(total_strength, 1e-10)

        # Occupation probability: each bundle's fraction of total structure
        bundle_occupation = {}
        for b in all_bundles:
            # Active bundles: strength + dormant fruit tension contribution
            fruit_contribution = 0.0
            if b.xin_dormant_fruit is not None:
                # Dormant fruit's curled value contributes to occupation
                fruit_tension = abs(b.xin_dormant_fruit.get(
                    "tension_at_creation", 0.0))
                fruit_contribution = fruit_tension * 0.01  # small but nonzero
            bundle_occupation[b.bundle_id] = (
                b.bundle_strength + fruit_contribution) / total_strength

        # Ghost bundles: very low occupation (pruned ≈ probability→0, not 0)
        for g in ghost_bundles:
            g_id = g.get("bundle_id", "ghost_unknown")
            bundle_occupation[g_id] = g.get(
                "ghost_strength", 0.001) / total_strength

        # ── Build adjacency for cycle detection ──
        src_to_bundles: Dict[str, List[MetaSynapticBundle]] = {}
        for b in all_bundles:
            for sid in b.source_neuron_ids:
                src_to_bundles.setdefault(sid, []).append(b)

        # Find closed paths (cycles) up to depth 4
        cycles: List[Tuple[float, List[str]]] = []

        for start_bundle in all_bundles:
            path = [start_bundle.bundle_id]
            flow = bundle_occupation.get(start_bundle.bundle_id, 0.0)
            current_targets = set(start_bundle.target_neuron_ids)
            start_sources = set(start_bundle.source_neuron_ids)

            self._dfs_cycles(current_targets, start_sources, path, flow,
                            src_to_bundles, cycles, max_depth=3,
                            occupation=bundle_occupation)

        if not cycles:
            self._p_circulation = None
            self._r_circulation = None
            self._circulation_measure = 0.0
            return None, None

        # ── Compute full circulation measure ──
        # μ(G) = sum of ALL cycle flows (P contains all)
        self._circulation_measure = sum(c[0] for c in cycles)

        # P = max flow path, R = runner-up
        cycles.sort(key=lambda c: c[0], reverse=True)
        self._p_circulation = cycles[0][1]
        self._r_circulation = cycles[1][1] if len(cycles) > 1 else None

        # Store per-cycle contributions for structural audit
        self._all_cycle_measures = [
            {"path": c[1], "flow": c[0],
             "fraction": c[0] / max(self._circulation_measure, 1e-10)}
            for c in cycles[:10]  # top 10 for audit
        ]

        return self._p_circulation, self._r_circulation

    def _dfs_cycles(self, current_targets, goal_sources, path, flow,
                    src_to_bundles, cycles, max_depth, occupation=None):
        if max_depth <= 0:
            return
        overlap = current_targets & goal_sources
        if overlap and len(path) >= 2:
            cycles.append((flow, list(path)))
            return

        for tid in current_targets:
            for next_b in src_to_bundles.get(tid, []):
                if next_b.bundle_id in path:
                    continue
                # Flow = min(current, next bundle's occupation)
                next_occ = (occupation or {}).get(
                    next_b.bundle_id, next_b.bundle_strength)
                new_flow = min(flow, next_occ)
                path.append(next_b.bundle_id)
                next_targets = set(next_b.target_neuron_ids)
                self._dfs_cycles(next_targets, goal_sources, path,
                                new_flow, src_to_bundles, cycles,
                                max_depth - 1, occupation)
                path.pop()

    # ─── Xin: Prediction residual → tension on edges ───

    def compute_xin(self, predicted_activations: Dict[str, float]):
        """Xin-phase: compare predicted vs actual, store tension."""
        self._activated_fruits = []
        for layer in self.layers.values():
            for bundle in layer.bundles:
                for tid in bundle.target_neuron_ids:
                    pred = predicted_activations.get(tid, 0.0)
                    actual = layer.neurons[tid].activation if tid in layer.neurons else 0.0
                    bundle.accumulate_xin(pred, actual)
                    self._xin_tensions[bundle.bundle_id] = bundle.xin_tension

                    # Try to activate dormant fruits
                    bias = actual - pred  # negative tension = unexpected signal
                    fruit = bundle.try_activate_fruit(bias)
                    if fruit:
                        self._activated_fruits.append(fruit)

    # ─── Learn: STDP on all bundles ───

    def learn(self):
        """STDP learning on all bundles, modulated by entropy ledger temperature.

        Uses neuron STDP traces (pre_trace, post_trace) for causal timing.
        Temperature from entropy ledger proxy modulates learning rate:
          hot → slower learning (exploration)
          cold → faster learning (exploitation/consolidation)
        """
        eta_scale = 1.0 / max(self._temperature, 0.1)
        eta_scale = max(0.1, min(2.0, eta_scale))

        total_delta = 0.0
        for layer in self.layers.values():
            for bundle in layer.bundles:
                # Get actual neuron objects for STDP traces
                pre_neurons = [layer.neurons[sid]
                               for sid in bundle.source_neuron_ids
                               if sid in layer.neurons]
                post_neurons = [layer.neurons[tid]
                                for tid in bundle.target_neuron_ids
                                if tid in layer.neurons]
                if pre_neurons and post_neurons:
                    d = bundle.stdp_update(pre_neurons, post_neurons, eta_scale)
                    total_delta += d

                    # Mark post-activation timing for STDP
                    for n in post_neurons:
                        n.post_activate()

        return total_delta

    # ─── Maintain: decay, pruning, maturation ───

    def maintain(self):
        """Per-tick maintenance: decay, pruning, maturation, synaptic scaling.

        v40.1: Added homeostatic synaptic scaling (Turrigiano 1998):
        When a postsynaptic neuron's calcium is below target, all incoming
        synaptic weights are multiplicatively scaled UP. This is the
        structural mechanism that prevents neuron silencing.
        """
        pruned = []
        for layer in self.layers.values():
            # Neuron decay + maturation
            for n in layer.neurons.values():
                n.decay()
                n.try_mature()

            # ── Homeostatic Synaptic Scaling (HSS) ──
            # For each target neuron: if calcium < target → scale up incoming weights
            # This is multiplicative, not additive — preserves relative weight structure
            for bundle in layer.bundles:
                for j, tid in enumerate(bundle.target_neuron_ids):
                    if tid not in layer.neurons:
                        continue
                    target_n = layer.neurons[tid]
                    if target_n.calcium < target_n.target_rate * 0.5:
                        # Neuron is significantly below target → scale up
                        scale = 1.0 + 0.02 * (target_n.target_rate - target_n.calcium) / max(target_n.target_rate, 0.001)
                        scale = min(scale, 1.05)  # max 5% per tick
                        for i in range(len(bundle.weights)):
                            if j < len(bundle.weights[i]):
                                bundle.weights[i][j] = min(1.0, bundle.weights[i][j] * scale)
                    elif target_n.calcium > target_n.target_rate * 2.0:
                        # Neuron is significantly above target → scale down
                        scale = 1.0 - 0.01 * (target_n.calcium - target_n.target_rate) / max(target_n.target_rate, 0.001)
                        scale = max(scale, 0.95)  # max 5% down per tick
                        for i in range(len(bundle.weights)):
                            if j < len(bundle.weights[i]):
                                bundle.weights[i][j] = max(0.0, bundle.weights[i][j] * scale)

            # Bundle pruning → ghost residuals
            # Pruned bundles don't vanish: they leave ghost residuals
            # at extremely low occupation probability. Their information
            # trajectory still exists in the structure's long-window measure.
            surviving = []
            if not hasattr(layer, '_ghost_bundles'):
                layer._ghost_bundles = []
            for b in layer.bundles:
                if b.should_prune():
                    pruned.append(b.bundle_id)
                    # Create ghost: structural residual of the pruned bundle
                    ghost = {
                        "bundle_id": b.bundle_id,
                        "source_neuron_ids": list(b.source_neuron_ids),
                        "target_neuron_ids": list(b.target_neuron_ids),
                        "ghost_strength": max(0.001, b.bundle_strength * 0.01),
                        "xin_tension_at_death": b.xin_tension,
                        "fruit_at_death": b.xin_dormant_fruit,
                        "created_tick": self.tick,
                    }
                    layer._ghost_bundles.append(ghost)
                else:
                    surviving.append(b)
            layer.bundles = surviving

            # Ghost decay: ghosts slowly fade but never reach zero
            for g in layer._ghost_bundles:
                g["ghost_strength"] = max(0.0001,
                    g["ghost_strength"] * 0.99)  # 1% decay per tick

            # Ghost resurrection: if a ghost's tension is confirmed by
            # current circuit state (high Xin tension in its target area),
            # the ghost can revive as a weak active bundle.
            # This implements: dormant → activated → competitive
            revived = []
            still_ghosts = []
            for g in layer._ghost_bundles:
                # Check if ghost's target neurons have high unmet tension
                tension_sum = sum(
                    abs(self._xin_tensions.get(bid, 0.0))
                    for bid in [b.bundle_id for b in layer.bundles]
                    if any(t in g["target_neuron_ids"]
                           for t in [b2 for b in layer.bundles
                                     for b2 in b.target_neuron_ids])
                )
                # Resurrection threshold: ghost can revive if system tension
                # in its region exceeds the tension at death
                death_tension = abs(g.get("xin_tension_at_death", 0.0))
                if tension_sum > death_tension * 2.0 and death_tension > 0.1:
                    # Resurrect: create a new weak bundle from ghost
                    new_b = MetaSynapticBundle(
                        bundle_id=g["bundle_id"] + "_revived",
                        source_neuron_ids=g["source_neuron_ids"],
                        target_neuron_ids=g["target_neuron_ids"],
                        bundle_strength=g["ghost_strength"] * 10.0,
                    )
                    new_b.init_weights()
                    # Scale weights down — ghost is weak initially
                    for i in range(len(new_b.weights)):
                        for j in range(len(new_b.weights[i])):
                            new_b.weights[i][j] *= 0.1
                    revived.append(new_b)
                else:
                    still_ghosts.append(g)
            layer._ghost_bundles = still_ghosts
            layer.bundles.extend(revived)
            if revived:
                pruned.append(f"REVIVED:{len(revived)}")

        self.tick += 1
        return pruned

    # ─── Full tick ───

    def run_tick(self, input_activations: Dict[str, float],
                 input_layer: str,
                 predicted_activations: Optional[Dict[str, float]] = None):
        """Run one full T/O/P/R/Xin tick."""
        # T: Transport
        self.transport(input_activations, input_layer)
        # O: Observe
        obs = self.observe()
        # P/R: Circulation detection
        p_circ, r_circ = self.detect_circulations()
        # Xin: Prediction residual
        if predicted_activations:
            self.compute_xin(predicted_activations)
        # Learn
        total_dw = self.learn()
        # Maintain
        pruned = self.maintain()

        result = {
            "tick": self.tick - 1,
            "observable": obs,
            "p_circulation": p_circ,
            "r_circulation": r_circ,
            "xin_tensions": len(self._xin_tensions),
            "activated_fruits": len(self._activated_fruits),
            "total_delta_w": round(total_dw, 6),
            "pruned_bundles": pruned,
            "temperature": round(self._temperature, 6),
        }

        self._audit.append(result)
        return result

    # ─── Metrics ───

    def get_metrics(self) -> Dict[str, Any]:
        total_neurons = sum(len(l.neurons) for l in self.layers.values())
        total_bundles = (sum(len(l.bundles) for l in self.layers.values())
                        + len(self.inter_layer_bundles))
        alive = sum(1 for l in self.layers.values()
                    for n in l.neurons.values() if n.is_alive())
        maturation_counts = {"spine": 0, "column": 0, "area": 0}
        for l in self.layers.values():
            for n in l.neurons.values():
                maturation_counts[n.maturation] = (
                    maturation_counts.get(n.maturation, 0) + 1)
        dormant_fruits = sum(
            1 for l in self.layers.values()
            for b in l.bundles if b.xin_dormant_fruit is not None)

        return {
            "total_neurons": total_neurons,
            "alive_neurons": alive,
            "total_bundles": total_bundles,
            "maturation": maturation_counts,
            "dormant_fruits": dormant_fruits,
            "p_circulation": self._p_circulation,
            "r_circulation": self._r_circulation,
            "temperature": round(self._temperature, 6),
            "tick": self.tick,
        }

    # ─── Transport Feedback Injection ───

    def inject_transport_feedback(self, edge_costs: list,
                                  theta: float, rejection_count: int,
                                  total_edges: int):
        """Inject pipeline transport costs as structural signal into circuit.

        This is the key mechanism for solving W_signal discrimination:
        instead of relying only on signal statistics (sig_mean, sig_std...),
        the circuit also receives structural information from the transport
        layer — edge cost distribution, gating rejection rate, cost entropy.

        These structural signals modulate the z_t target neurons directly,
        giving different stimulus types distinguishable transport signatures.

        Args:
            edge_costs: list of transport edge costs from write_transport
            theta: adaptive gating threshold
            rejection_count: number of edges rejected by theta
            total_edges: total edges evaluated
        """
        if not edge_costs:
            return

        enc = self.layers.get("encoding")
        if enc is None:
            return

        import math

        # ── Compute 3 structural features from transport costs ──
        n = len(edge_costs)
        cost_mean = sum(edge_costs) / n
        cost_std = math.sqrt(sum((c - cost_mean)**2 for c in edge_costs) / n)

        # Transport entropy (how spread out is the cost distribution?)
        # Higher entropy = more uniform = less structured transport
        sorted_c = sorted(edge_costs)
        bins = min(10, n)
        bin_size = n // bins
        probs = []
        for b in range(bins):
            start = b * bin_size
            end = start + bin_size if b < bins - 1 else n
            p = (end - start) / n
            probs.append(p)
        transport_entropy = -sum(p * math.log(max(p, 1e-10)) for p in probs)
        transport_entropy /= math.log(max(bins, 2))  # normalize to [0, 1]

        # Rejection rate (how selective is the gating?)
        rejection_rate = rejection_count / max(total_edges, 1)

        # ── Temporal derivatives (these DO vary across stimulus types) ──
        prev_cost = getattr(self, '_prev_transport_cost_mean', cost_mean)
        prev_std = getattr(self, '_prev_transport_cost_std', cost_std)
        prev_entropy = getattr(self, '_prev_transport_entropy', transport_entropy)
        prev_reject = getattr(self, '_prev_rejection_rate', rejection_rate)

        d_cost = cost_mean - prev_cost           # signed change
        d_std = cost_std - prev_std               # variability change
        d_entropy = transport_entropy - prev_entropy  # structure change
        d_reject = rejection_rate - prev_reject   # selectivity change

        self._prev_transport_cost_mean = cost_mean
        self._prev_transport_cost_std = cost_std
        self._prev_transport_entropy = transport_entropy
        self._prev_rejection_rate = rejection_rate

        # ── Multiplicative gain modulation on z_t neurons ──
        # Instead of adding a constant (which doesn't discriminate),
        # we SCALE each z_t dimension by a stimulus-dependent gain.
        # gain > 1.0 amplifies that dimension, gain < 1.0 suppresses it.
        gain_map = {
            "transition":     1.0 + d_cost * 10.0,     # cost jump → amplify transition
            "drift":          1.0 + d_std * 8.0,        # variability change → amplify drift
            "gamma_desync":   1.0 + d_entropy * 5.0,    # entropy shift → amplify desync
            "xin_residual":   1.0 + d_reject * 6.0,     # selectivity change → residual
            "potential_disp": 1.0 + abs(d_cost) * 4.0,  # any cost change → potential
            "churn":          1.0 + abs(d_std) * 3.0,   # any spread change → churn
            "magnitude":      1.0 - d_entropy * 2.0,    # entropy increase → suppress magnitude
        }

        for nid, gain in gain_map.items():
            if nid in enc.neurons:
                n_obj = enc.neurons[nid]
                # Clamp gain to prevent explosion
                g = max(0.1, min(3.0, gain))
                n_obj.activation *= g



# ═══════════════════════════════════════════════════════════════
# 5. Bridge: Build circuit from existing pipeline components
# ═══════════════════════════════════════════════════════════════

def build_circuit_from_signal_transform(signal_transform) -> HebbianCircuit:
    """Construct a HebbianCircuit from existing HebbianSignalTransform.

    Maps:
      6 signal features → 6 source MetaNeurons (encoding layer)
      7 z_t dimensions  → 7 target MetaNeurons (encoding layer)
      W_signal rows     → 6 MetaSynapticBundles (1→7 hyperedges)

    This solves W_signal discrimination by making each W row a
    structural bundle with its own inertia, strength, and Xin tension.
    """
    circuit = HebbianCircuit()

    # Encoding layer: signal features → z_t dimensions
    enc = circuit.add_layer("encoding")

    feature_names = getattr(signal_transform, 'SIGNAL_FEATURES',
                           ["sig_mean", "sig_std", "sig_peak_rate",
                            "sig_temporal_d", "sig_sync", "sig_range"])
    cost_names = ["transition", "drift", "gamma_desync",
                  "xin_residual", "potential_disp", "churn", "magnitude"]

    # Source neurons (signal features)
    for fname in feature_names:
        enc.add_neuron(fname)

    # Target neurons (z_t dimensions)
    for cname in cost_names:
        enc.add_neuron(cname)

    # Bundles from W_signal rows (each row = 1-to-7 hyperedge)
    W = getattr(signal_transform, 'W', None)
    if W:
        for i, fname in enumerate(feature_names):
            if i < len(W):
                bundle = enc.add_bundle(
                    source_ids=[fname],
                    target_ids=cost_names)
                bundle.weights = [list(W[i])]
                bundle.bundle_strength = sum(W[i]) / len(W[i])
                # Mark sig_sync bundle as proxy if sync is dead
                if fname == "sig_sync":
                    bundle.degraded_features.append(
                        "sig_sync_always_zero: degraded_from=cell_coupling_spectral_gap")

    # ── Feedback bundles: z_t → signal features (creates closed loops) ──
    # These enable circulation detection (P/R).
    # Physical meaning: z_t dimensions influence future signal interpretation.
    # DEGRADED: uniform feedback weights (should emerge from learning).
    # degraded_from = "emergent_feedback_topology"
    feedback_groups = [
        # z_t group → signal feature it feeds back to
        (["transition", "drift"], ["sig_mean", "sig_std"]),
        (["gamma_desync", "xin_residual"], ["sig_peak_rate", "sig_temporal_d"]),
        (["potential_disp", "churn", "magnitude"], ["sig_sync", "sig_range"]),
    ]
    for src_ids, tgt_ids in feedback_groups:
        fb = enc.add_bundle(source_ids=src_ids, target_ids=tgt_ids)
        fb.learning_rule = "oja"
        fb.degraded_features.append(
            "uniform_feedback: degraded_from=emergent_feedback_topology")

    # ── Column layer (DEGRADED: simple EMA consolidation) ──
    # degraded_from = "BCM_learning_rule"
    col = circuit.add_layer("column")
    for cname in cost_names:
        col.add_neuron(f"col_{cname}", maturation="column")

    # Inter-layer: encoding z_t → column (consolidation path)
    circuit.add_inter_layer_bundle(
        "encoding", cost_names,
        "column", [f"col_{c}" for c in cost_names])

    return circuit

===
"""Morphosphere v40 — Hebbian Circuit: Neural System Embedded in Hypergraph.

Architecture Document Reference: implementation_plan.md §1-§5

════════════════════════════════════════════════════════════════════════
STRUCTURAL DYNAMICS INVARIANT (v40.7 — Project Foundation)
════════════════════════════════════════════════════════════════════════
Every field in the meta-structure (MetaNeuron, MetaSynapticBundle,
CircuitLayer) MUST satisfy the following invariant:

  1. GENERATION: The field has a mechanism that creates/increases its value
  2. DECAY: The field has a mechanism that reduces/dissipates its value
  3. STRUCTURAL COUPLING: The field's value influences at least one other
     field in the same or a neighboring structure

If a field lacks any of these three, it is either:
  (a) A STATIC LABEL — must be replaced with a dynamic proxy, or
  (b) A DEGRADED PROXY — must carry a `degraded_from` annotation naming
      the real physical mechanism it approximates

Complex thermodynamic relationships are delegated to the external entropy
ledger. But the structural dynamics within the meta-structure must be
complete enough to simulate the behavior of real physical systems at a
degraded resolution.

All proxy modules are annotated with their degraded source:
  # DEGRADED: <what is simplified> → proxy as <what we do instead>
  # degraded_from = "<real physical mechanism>"
════════════════════════════════════════════════════════════════════════

Design Goals (v40):
  1. MetaNeuron / MetaSynapticBundle / CircuitLayer as core primitives
  2. Spine-layer T/O/P/R/Xin lifecycle on the circuit itself
  3. Shadow dormant-fruit mechanism (replaces tombstone-only model)
  4. Substrate heat exchange delegated to external entropy ledger (annotated)
  5. Solve: W_signal discrimination failure via structural transport feedback
  6. Solve: Defense layer mismatch via circuit-level hysteresis

Degraded components (annotated inline with DEGRADED markers):
  - Substrate → delegated to external entropy ledger
  - Column layer learning → exponential moving average (not BCM)
  - Circulation detection → depth-limited DFS (not full homology)
  - P/R competition → Top-2 selection (not full energy competition)
  - MeasureCoordinate → retained as proxy (not emergent coordinate)
  - Basket cell lateral inhibition → calcium-scaled threshold push
  - Protein synthesis & diffusion → direct emission/capture
  - Dopaminergic modulation → Xin tension magnitude proxy
  - Vesicle pool recycling → linear depletion + exponential recovery
  - Metabolic ATP cycle → energy recovery proportional to calcium
  - Membrane resting potential adaptation → slow EMA of activation
"""
from __future__ import annotations
import math, uuid, json
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple, Any
from datetime import datetime, timezone

def _now(): return datetime.now(timezone.utc).isoformat()
def _uid(p): return f"{p}_{uuid.uuid4().hex[:8]}"


# ═══════════════════════════════════════════════════════════════
# 1. MetaNeuron — Computational node in the Hebbian circuit
# ═══════════════════════════════════════════════════════════════

@dataclass
class MetaNeuron:
    """A computational node in the Hebbian circuit-hypergraph.

    v40.1: Three structural plasticity mechanisms from real neural circuits:

    1. STDP Traces (Spike-Timing-Dependent Plasticity):
       - pre_trace/post_trace: exponentially-decaying timing memory
       - Replaces Oja correlation with causal timing relationships

    2. Homeostatic Target Rate (calcium-based feedback):
       - target_rate: desired average activation (neural set-point)
       - calcium: slow-integrated activity sensor (like Ca²⁺)
       - Prevents runaway excitation or silencing

    3. Intrinsic Excitability (memristor conductance analogy):
       - threshold: dynamic gating level (adapts homeostatically)
       - Input < threshold → leak current only; > threshold → full pass
       - Creates stimulus-selective response profiles

    Energy: DEGRADED to entropy ledger proxy (annotated).
    """
    neuron_id: str
    layer_id: str

    # ── Core state ──
    activation: float = 0.0
    resting_potential: float = 0.0  # V_rest: adapts to long-term activity mean
    potential: float = 0.0       # Φ: accumulated history
    inertia: float = 1.0        # M: resistance to change (adapts to stability)
    _activation_ema: float = 0.0   # v40.7: slow EMA of |activation| for resting_potential

    # ── STDP Traces ──
    pre_trace: float = 0.0      # x_i(t): incremented on input, decays
    post_trace: float = 0.0     # y_j(t): incremented on output, decays
    trace_tau_pre: float = 20.0
    trace_tau_post: float = 20.0

    # ── Homeostatic regulation ──
    target_rate: float = 0.03   # desired average activation
    calcium: float = 0.03       # slow-integrated activity (Ca²⁺ proxy)
    calcium_tau: float = 20.0   # integration time constant (v40.6: dynamically set)
    _calcium_tau_initialized: bool = False  # internal flag for dynamic init

    # ── Intrinsic excitability (memristor conductance) ──
    threshold: float = 0.003    # dynamic firing threshold
    threshold_adapt_rate: float = 0.01   # fast adaptation (like fast homeostasis)

    # ── Metabolic state ──
    # DEGRADED: full ATP/ADP cycle → proxy as linear drain + calcium-recovery
    # degraded_from = "mitochondrial_ATP_synthesis"
    energy: float = 1.0
    heat_output: float = 0.0
    _metabolic_recovery_rate: float = 0.005  # v40.7: energy recovery per tick

    # ── Maturation ──
    maturation: str = "spine"
    activation_count: int = 0

    # ── v40.7: Column physical privilege ──
    # Column neurons have asymmetric physics that Spine neurons do not.
    # Based on cortical microcolumn properties (Mountcastle 1997, Frégnac 2003):
    #   - lateral_suppression_radius: topological distance of threshold suppression
    #   - stdp_ltp_boost: asymmetric STDP acceleration factor for LTP
    #   - prp_emission: plasticity-related protein level (synaptic tagging & capture)
    #   - prp_threshold: calcium level above which PRP is emitted
    lateral_suppression_radius: int = 0     # Spine=0 (no suppression), Column=3, Area=5
    stdp_ltp_boost: float = 1.0             # Spine=1.0 (symmetric), Column=2.0, Area=3.0
    prp_emission: float = 0.0               # current PRP level (decays each tick)
    prp_threshold: float = 0.0              # calcium above this → emit PRP

    # ── Proxy slot ──
    # PLACEHOLDER: proxy delegation mechanism (not yet implemented)
    # When implemented, proxy_for will name the physical mechanism this
    # neuron substitutes for, and is_proxy_host will mark the host neuron.
    # Until then, these are structural annotations with no dynamical coupling.
    proxy_for: Optional[str] = None
    is_proxy_host: bool = False

    @property
    def plasticity(self) -> float:
        return {"spine": 0.18, "column": 0.01, "area": 0.001}.get(
            self.maturation, 0.18)

    @property
    def decay_rate(self) -> float:
        return {"spine": 0.025, "column": 0.005, "area": 0.001}.get(
            self.maturation, 0.025)

    def activate(self, input_signal: float) -> float:
        """Threshold-gated activation (memristor conductance model).

        Input < threshold → leak (0.1×). Input ≥ threshold → pass.
        This creates per-neuron selectivity: each neuron's threshold
        adapts homeostatically, so different neurons respond to
        different input magnitudes.
        """
        # v40.6: Dynamic calcium_tau — inversely proportional to target_rate
        # Sparse responders (low target_rate) need longer accumulation periods;
        # tonic responders (high target_rate) need fast adaptation
        if not self._calcium_tau_initialized:
            self.calcium_tau = max(5.0, min(50.0, 1.0 / max(self.target_rate, 0.001)))
            self.calcium = self.target_rate  # initialize calcium to target to prevent floor-pinning
            # v40.6: Initialize threshold proportional to target_rate
            # High target_rate → low threshold (tonic responder, passes more)
            # Low target_rate → high threshold (sparse responder, selective)
            self.threshold = max(0.0001, min(0.1, self.target_rate * 0.5))
            # Faster adaptation rate for higher target_rate neurons
            self.threshold_adapt_rate = max(0.005, min(0.05, self.target_rate * 0.5))
            self._calcium_tau_initialized = True

        effective = input_signal / max(self.inertia, 0.5)
        if abs(effective) < self.threshold:
            self.activation = effective * 0.1  # sub-threshold leak
        else:
            sign = 1.0 if effective >= 0 else -1.0
            self.activation = sign * (abs(effective) - self.threshold)

        self.activation_count += 1
        self.pre_trace += 1.0  # mark timing for STDP

        # Calcium: slow activity integrator (homeostasis sensor)
        self.calcium += (abs(self.activation) - self.calcium) / self.calcium_tau

        # Energy cost → entropy ledger proxy
        cost = abs(self.activation) * 0.01
        self.heat_output = cost
        self.energy = max(0.0, self.energy - cost)
        return self.activation

    def post_activate(self):
        """Mark output timing for STDP (called after downstream use)."""
        self.post_trace += 1.0

    def decay(self):
        """Per-tick: activation decay, trace decay, homeostatic adaptation.

        Structural Dynamics Invariant: every field updated here has
        generation ↔ decay ↔ coupling. See module docstring.
        """
        rate = self.decay_rate
        self.activation += rate * (self.resting_potential - self.activation)
        self.potential += abs(self.activation) * 0.01

        # STDP trace exponential decay
        self.pre_trace *= (1.0 - 1.0 / max(self.trace_tau_pre, 1.0))
        self.post_trace *= (1.0 - 1.0 / max(self.trace_tau_post, 1.0))

        # v40.7: Resting potential adaptation
        # In real neurons, resting potential shifts with sustained activity
        # (intrinsic plasticity, Desai et al 1999). A neuron that has been
        # tonically active develops a slightly depolarized resting state.
        # DEGRADED: ion channel conductance adaptation → proxy as slow EMA
        # degraded_from = "voltage_gated_ion_channel_redistribution"
        self._activation_ema += 0.001 * (abs(self.activation) - self._activation_ema)
        # Resting potential drifts toward a fraction of the EMA
        self.resting_potential += 0.002 * (self._activation_ema * 0.1 - self.resting_potential)
        self.resting_potential = max(-0.1, min(0.1, self.resting_potential))

        # v40.7: Metabolic energy recovery
        # Real neurons use ATP from mitochondria; more active neurons have
        # higher metabolic rates AND higher recovery (more mitochondria).
        # DEGRADED: ATP synthesis → proxy as calcium-proportional recovery
        # degraded_from = "mitochondrial_ATP_synthesis"
        # Recovery ∝ calcium (active neurons invest more in metabolism)
        recovery = self._metabolic_recovery_rate * (1.0 + self.calcium * 10.0)
        self.energy = min(1.0, self.energy + recovery)

        # v40.7: Inertia adaptation (activity-stability driven)
        # In real neurons, stable firing patterns increase synaptic inertia
        # (perineuronal nets, myelin). Volatile patterns decrease it.
        # DEGRADED: perineuronal net formation → proxy as activation variance
        # degraded_from = "perineuronal_net_formation_and_degradation"
        # Inertia grows when activation is close to resting (stable)
        # Inertia shrinks when activation is far from resting (volatile)
        deviation = abs(self.activation - self.resting_potential)
        if deviation < 0.01:
            # Stable state → inertia grows (perineuronal nets solidify)
            self.inertia = min(10.0, self.inertia + 0.001)
        elif deviation > 0.1:
            # Volatile state → inertia degrades (nets dissolve)
            self.inertia = max(0.5, self.inertia - 0.001)

        # Homeostatic threshold adaptation
        # calcium > target → too active → raise threshold
        # calcium < target → too quiet → lower threshold
        error = self.calcium - self.target_rate
        self.threshold += self.threshold_adapt_rate * error
        # v40.6: Floor proportional to target_rate — creates structural differentiation
        floor = max(0.0001, self.target_rate * 0.15)
        self.threshold = max(floor, min(0.5, self.threshold))

        # v40.7: STDP LTP boost fatigue/recovery dynamics
        # The asymmetric STDP boost is a resource (like neurotransmitter vesicles).
        # It fatigues with use and recovers toward the maturation base level.
        # This prevents Column from having infinite amplification power.
        # DEGRADED: vesicle pool dynamics → proxy as exponential recovery
        # degraded_from = "synaptic_vesicle_pool_recycling"
        base_boost = {"spine": 1.0, "column": 2.0, "area": 3.0}.get(self.maturation, 1.0)
        # Recovery: 1% per tick toward base level
        self.stdp_ltp_boost += 0.01 * (base_boost - self.stdp_ltp_boost)
        # Ensure minimum boost is 1.0 (Spine level)
        self.stdp_ltp_boost = max(1.0, self.stdp_ltp_boost)

        # v40.7: PRP threshold slow adaptation
        # PRP gate adapts to track the neuron's actual activity level,
        # not just the initial target_rate. This prevents static gating.
        # DEGRADED: gene expression regulation → proxy as slow EMA
        # degraded_from = "transcription_factor_regulation"
        if self.prp_threshold > 0:
            # Adapt toward 1.5× running calcium average (slow, τ≈100 ticks)
            self.prp_threshold += 0.01 * (self.calcium * 1.5 - self.prp_threshold)

    def try_mature(self, column_threshold: float = 50.0,
                   area_threshold: float = 500.0):
        """Maturation: spine → column → area.

        v40.7: Maturation grants ASYMMETRIC PHYSICAL LAWS.
        Column is NOT just 'a bigger Spine' — it gains:
          - Lateral suppression: raises threshold of nearby Spine neurons
          - Asymmetric STDP: LTP boost factor 2× (accelerator, per Frégnac)
          - PRP emission: calcium > target → emit plasticity-related proteins
            that can be captured by distant tagged Spines (synaptic tagging)

        v40.7d: Maturation requires BOTH potential AND activation_count.
        A neuron that accumulated potential passively (low activation_count)
        cannot mature — it must have actually participated in computation.
        This prevents "phantom maturation" of dormant neurons.
        """
        if self.maturation == "spine" and self.potential > column_threshold:
            # v40.7d: Gate on activation_count — must have fired enough
            if self.activation_count < 20:
                return  # not enough participation to mature
            self.maturation = "column"
            self.inertia = max(self.inertia, 2.0)
            self.threshold_adapt_rate *= 0.5
            # v40.7: Grant Column physical privilege
            self.lateral_suppression_radius = 3   # suppress 3 topo-neighbors
            self.stdp_ltp_boost = 2.0              # asymmetric STDP accelerator
            self.prp_threshold = self.target_rate * 1.5  # PRP emission gate
        elif self.maturation == "column" and self.potential > area_threshold:
            # v40.7d: Area maturation also requires activation_count
            if self.activation_count < 200:
                return  # not enough participation
            self.maturation = "area"
            self.inertia = max(self.inertia, 5.0)
            self.threshold_adapt_rate *= 0.1
            # v40.7: Area = stronger privilege
            self.lateral_suppression_radius = 5
            self.stdp_ltp_boost = 3.0
            self.prp_threshold = self.target_rate * 1.2

    def is_alive(self) -> bool:
        return self.energy > 0.0


# ═══════════════════════════════════════════════════════════════
# 2. MetaSynapticBundle — Hyperedge connecting neuron sets
# ═══════════════════════════════════════════════════════════════

@dataclass
class MetaSynapticBundle:
    """A hyperedge: directed connection from source neuron SET to target SET.

    Unlike a simple edge (A→B), a bundle connects {A,B,C} → {D,E}.
    This is the 'hyper' in hypergraph.

    The bundle has:
      - weight matrix: weights[i][j] = source[i] → target[j]
      - bundle_strength: aggregate strength (below threshold → pruning)
      - bundle_inertia: resistance to weight change
      - transport_cost: cost of propagation through this bundle
      - xin_tension: prediction residual curled on this edge
    """
    bundle_id: str
    source_neuron_ids: List[str]
    target_neuron_ids: List[str]

    # ── Weight tensor ──
    weights: List[List[float]] = field(default_factory=list)

    # ── Bundle-level properties ──
    bundle_strength: float = 1.0
    bundle_inertia: float = 1.0
    transport_cost: float = 0.0

    # ── Learning ──
    learning_rule: str = "oja"   # "oja" | "frozen"
    last_pre_activation: float = 0.0
    last_post_activation: float = 0.0

    # ── Xin tension (§3.3: prediction residual curled on this edge) ──
    xin_tension: float = 0.0    # > 0 = expected but didn't happen
    xin_dormant_fruit: Optional[Dict] = None  # shadow fruit if tension persists

    # ── Degradation annotation ── ANNOTATION_ONLY
    # These strings document which features are degraded and why.
    # They do NOT participate in computation — they are structural metadata.
    degraded_features: List[str] = field(default_factory=list)

    def init_weights(self):
        """Initialize weight matrix if empty."""
        if not self.weights:
            n_src = len(self.source_neuron_ids)
            n_tgt = len(self.target_neuron_ids)
            # Small uniform initialization
            self.weights = [
                [0.1 + 0.02 * ((i * 7 + j) % 5) for j in range(n_tgt)]
                for i in range(n_src)
            ]

    def propagate(self, source_activations: List[float]) -> List[float]:
        """Forward propagation: source activations → target activations."""
        self.init_weights()
        n_tgt = len(self.target_neuron_ids)
        target_acts = [0.0] * n_tgt
        total_pre = 0.0

        for i, a_pre in enumerate(source_activations):
            if i >= len(self.weights):
                break
            total_pre += abs(a_pre)
            for j in range(n_tgt):
                if j < len(self.weights[i]):
                    target_acts[j] += self.weights[i][j] * a_pre

        self.last_pre_activation = total_pre / max(len(source_activations), 1)
        self.last_post_activation = sum(abs(a) for a in target_acts) / max(n_tgt, 1)

        # Transport cost = propagation effort
        self.transport_cost = total_pre * 0.01 / max(self.bundle_inertia, 0.5)
        return target_acts

    def stdp_update(self, pre_neurons: List['MetaNeuron'],
                    post_neurons: List['MetaNeuron'],
                    eta_scale: float = 1.0):
        """STDP learning rule: weight change depends on timing traces.

        Based on computational STDP (Bi & Poo 1998, Song et al 2000):
          - pre fires before post (pre_trace high when post fires):
            → LTP (potentiation): ΔW = +A+ × pre_trace
          - post fires before pre (post_trace high when pre fires):
            → LTD (depression): ΔW = -A- × post_trace

        This replaces Oja's simple correlation with causal timing,
        which creates direction-selective weight patterns: synapses
        that consistently CAUSE downstream activity get strengthened,
        while synapses that are uncorrelated or anti-causal get weakened.

        Structural plasticity effects:
          - Weights that grow → bundle_strength increases → bundle consolidates
          - Weights that shrink → bundle_strength decreases → pruning candidate
          - If bundle_strength drops below threshold → structural pruning
        """
        if self.learning_rule == "frozen":
            return 0.0
        self.init_weights()

        A_plus = 0.01 * eta_scale    # LTP rate
        A_minus = 0.012 * eta_scale  # LTD rate (slightly stronger → stability)
        total_delta = 0.0

        # v40.7d: Modulate learning rate by post-synaptic plasticity.
        # Column neurons (plasticity=0.01) learn 18× slower than Spine (0.18).
        # This is the functional consequence of maturation: mature neurons
        # are more stable, less plastic — their weights change slowly.
        # DEGRADED: NMDA receptor density → proxy as maturation-keyed scalar
        # degraded_from = "NMDA_receptor_density_regulation"
        avg_post_plasticity = 1.0
        if post_neurons:
            avg_post_plasticity = sum(
                getattr(pn, 'plasticity', 0.18) for pn in post_neurons
            ) / len(post_neurons) / 0.18  # normalize so spine=1.0
            avg_post_plasticity = max(0.01, avg_post_plasticity)  # floor
        A_plus *= avg_post_plasticity
        A_minus *= avg_post_plasticity

        for i, pre_n in enumerate(pre_neurons):
            if i >= len(self.weights):
                break
            # v40.7: Column pre-neurons boost LTP (asymmetric STDP accelerator)
            # Spine neurons use symmetric STDP (boost=1.0)
            # Column neurons use asymmetric STDP (boost=2.0) — Frégnac 2003
            ltp_boost = getattr(pre_n, 'stdp_ltp_boost', 1.0)
            for j, post_n in enumerate(post_neurons):
                if j >= len(self.weights[i]):
                    break

                # STDP: weight change = f(timing traces)
                # LTP: pre was recently active when post fires
                # v40.7: Column pre-neurons amplify LTP by ltp_boost
                ltp = A_plus * ltp_boost * pre_n.pre_trace * abs(post_n.activation)
                # LTD: post was recently active when pre fires
                ltd = A_minus * post_n.post_trace * abs(pre_n.activation)

                delta = (ltp - ltd) / max(self.bundle_inertia, 0.5)

                # Weight-dependent scaling (multiplicative STDP):
                # Near w_max → LTP slows; near w_min → LTD slows
                w = self.weights[i][j]
                if delta > 0:
                    delta *= (1.0 - w)  # closer to max → less potentiation
                else:
                    delta *= w           # closer to min → less depression

                self.weights[i][j] = max(0.0, min(1.0, w + delta))
                total_delta += abs(delta)

        # Update bundle strength (structural health indicator)
        flat = [self.weights[i][j]
                for i in range(len(self.weights))
                for j in range(len(self.weights[i]))]
        self.bundle_strength = sum(flat) / max(len(flat), 1)

        # Update conductance state (memristor analogy)
        # Total activity through this bundle → conductance increases
        self._conductance_history = getattr(self, '_conductance_history', 0.0)
        self._conductance_history += total_delta
        self.bundle_inertia = max(0.5, self.bundle_inertia - total_delta * 0.01)

        # v40.7f: Record recent delta for inertia recovery in maintain()
        self._recent_delta = total_delta

        # v40.7: STDP LTP boost fatigue (vesicle depletion proxy)
        # Pre-neurons that contributed LTP have their boost depleted.
        # This prevents infinite amplification — the boost must RECOVER
        # in decay() before it can be used again at full strength.
        # DEGRADED: vesicle recycling kinetics → proxy as linear depletion
        # degraded_from = "presynaptic_vesicle_release_probability"
        if total_delta > 0.001:
            for pre_n in pre_neurons:
                if pre_n.stdp_ltp_boost > 1.0:
                    # Depletion ∝ total weight change caused
                    depletion = min(0.1, total_delta * 0.05)
                    pre_n.stdp_ltp_boost = max(1.0, pre_n.stdp_ltp_boost - depletion)

        return total_delta

    # Keep backward compat
    def hebbian_update(self, pre_acts, post_acts, eta_scale=1.0):
        """Legacy interface — delegates to stdp_update when neurons available."""
        # Fallback to simplified Oja when no neuron objects available
        if self.learning_rule == "frozen":
            return 0.0
        self.init_weights()
        eta = 0.01 * eta_scale / max(self.bundle_inertia, 0.5)
        total_delta = 0.0
        for i in range(min(len(pre_acts), len(self.weights))):
            for j in range(min(len(post_acts), len(self.weights[i]))):
                delta = eta * pre_acts[i] * (
                    post_acts[j] - self.weights[i][j] * pre_acts[i])
                self.weights[i][j] = max(0.0, min(1.0,
                    self.weights[i][j] + delta))
                total_delta += abs(delta)
        flat = [self.weights[i][j]
                for i in range(len(self.weights))
                for j in range(len(self.weights[i]))]
        self.bundle_strength = sum(flat) / max(len(flat), 1)
        return total_delta

    def should_prune(self, threshold: float = 0.02) -> bool:
        """Structural pruning: considers weight AND recent activity.

        A bundle is pruned if:
          - bundle_strength < threshold (weights too weak), AND
          - no recent conductance growth (not actively learning)
        """
        conductance = getattr(self, '_conductance_history', 0.0)
        return self.bundle_strength < threshold and conductance < 0.001

    def accumulate_xin(self, predicted: float, actual: float):
        """Accumulate Xin tension (§3.3)."""
        self.xin_tension += (predicted - actual)
        # If tension persists → create dormant fruit with chemical trace
        if abs(self.xin_tension) > 0.5 and self.xin_dormant_fruit is None:
            self.xin_dormant_fruit = {
                "tension_at_creation": self.xin_tension,
                "bundle_id": self.bundle_id,
                "created_at": _now(),
                "state": "dormant",
                # v40.7: Chemical trace — exponentially decaying Ca²⁺ residual
                # Like real synaptic tagging: the trace fades over time.
                # Without this, a fruit created at tick 100 has full strength
                # at tick 5000 — violating thermodynamic memory limits.
                "trace_strength": 1.0,     # starts at full strength
                "trace_decay": 0.995,      # τ ≈ 200 ticks half-life
                "created_tick": 0,         # will be set by circuit
            }

    def decay_fruit_trace(self):
        """v40.7: Decay the chemical trace of dormant fruit each tick.

        Biological basis: Eligibility traces (Gerstner et al 2018).
        The Ca²⁺ residual at a tagged synapse decays exponentially.
        If no neuromodulatory signal (third factor) arrives before
        the trace expires, the fruit naturally dissolves — the system
        forgets the prediction error.
        """
        if self.xin_dormant_fruit is None:
            return
        f = self.xin_dormant_fruit
        f["trace_strength"] *= f["trace_decay"]
        # Fruit expires when trace falls below threshold
        if f["trace_strength"] < 0.01:
            self.xin_dormant_fruit = None  # dissolved — no backward signal possible

    def try_activate_fruit(self, bias_signal: float) -> Optional[Dict]:
        """If bias aligns with dormant fruit tension → activate it.

        v40.7: Activation strength is modulated by remaining trace.
        A fresh fruit (trace ≈ 1.0) activates at full tension.
        An old fruit (trace ≈ 0.1) activates weakly — temporal discount.
        This implements temporal credit assignment: recent errors matter
        more than ancient ones.
        """
        if self.xin_dormant_fruit is None:
            return None
        tension = self.xin_dormant_fruit["tension_at_creation"]
        trace = self.xin_dormant_fruit.get("trace_strength", 1.0)
        # Effective tension = original × chemical trace (temporal discount)
        effective_tension = tension * trace
        # Bias in same direction as tension → fruit ripens
        if effective_tension * bias_signal > 0 and abs(bias_signal) > 0.3:
            fruit = self.xin_dormant_fruit.copy()
            fruit["state"] = "activated"
            fruit["activated_at"] = _now()
            fruit["activation_bias"] = bias_signal
            fruit["effective_tension"] = effective_tension
            fruit["temporal_discount"] = trace
            self.xin_dormant_fruit = None
            self.xin_tension = 0.0
            return fruit
        return None


# ═══════════════════════════════════════════════════════════════
# 3. CircuitLayer — A layer of neurons + internal bundles
# ═══════════════════════════════════════════════════════════════

@dataclass
class CircuitLayer:
    """One layer of the Hebbian circuit."""
    layer_id: str
    neurons: Dict[str, MetaNeuron] = field(default_factory=dict)
    bundles: List[MetaSynapticBundle] = field(default_factory=list)

    def add_neuron(self, neuron_id: str, **kwargs) -> MetaNeuron:
        n = MetaNeuron(neuron_id=neuron_id, layer_id=self.layer_id, **kwargs)
        self.neurons[neuron_id] = n
        return n

    def add_bundle(self, source_ids: List[str], target_ids: List[str],
                   **kwargs) -> MetaSynapticBundle:
        b = MetaSynapticBundle(
            bundle_id=_uid("bundle"),
            source_neuron_ids=source_ids,
            target_neuron_ids=target_ids,
            **kwargs)
        b.init_weights()
        self.bundles.append(b)
        return b

    def get_activations(self) -> Dict[str, float]:
        return {nid: n.activation for nid, n in self.neurons.items()}


# ═══════════════════════════════════════════════════════════════
# 4. HebbianCircuit — The full circuit with T/O/P/R/Xin
# ═══════════════════════════════════════════════════════════════

class HebbianCircuit:
    """Multi-layer Hebbian circuit embedded in a hypergraph topology.

    The circuit has its own T/O/P/R/Xin lifecycle:
      T = activation propagation along hyperedges (with dissipation)
      O = measurable configuration change (observable from outside)
      P = primary circulation (winner-take-most closed path)
      R = secondary competing circulation
      Xin = prediction residual curled as tension on edges

    DEGRADED: Substrate heat exchange delegated to external entropy ledger.
    degraded_from = "local_substrate_thermodynamics"

    Solves:
      - W_signal discrimination: transport feedback flows into encoding layer
      - Defense layer mismatch: circuit-level hysteresis on bundle updates
    """

    def __init__(self, entropy_ledger_proxy=None):
        self.layers: Dict[str, CircuitLayer] = {}
        self.inter_layer_bundles: List[MetaSynapticBundle] = []
        self.tick = 0

        # DEGRADED: Substrate → external entropy ledger proxy
        # degraded_from = "local_substrate_thermodynamics"
        self._entropy_ledger_proxy = entropy_ledger_proxy
        self._temperature = 1.0
        self._free_energy = 10.0
        self._total_heat = 0.0

        # T/O/P/R/Xin state
        self._transport_log: List[Dict] = []
        self._observable_delta: float = 0.0
        self._p_circulation: Optional[List[str]] = None  # bundle_id path
        self._r_circulation: Optional[List[str]] = None
        self._xin_tensions: Dict[str, float] = {}  # bundle_id → tension
        self._activated_fruits: List[Dict] = []

        # v40.7e: Convergence detection — shared sub-manifold representation
        # Tracks which z_t dimensions co-activate. When co-activation exceeds
        # threshold, a structural "convergence node" is created that explicitly
        # represents the shared P/R/Xin subspace.
        # DEGRADED: association cortex dynamics → proxy as co-activation matrix
        # degraded_from = "anterior_cingulate_cortex_convergence_detection"
        self._convergence_matrix: Dict[str, Dict[str, float]] = {}  # (i,j) → strength
        self._convergence_nodes: Dict[str, Dict] = {}  # node_id → {dims, strength, ...}
        self._convergence_decay: float = 0.99  # per-tick decay of co-activation

        # Audit
        self._audit: List[Dict] = []

    def add_layer(self, layer_id: str) -> CircuitLayer:
        layer = CircuitLayer(layer_id=layer_id)
        self.layers[layer_id] = layer
        return layer

    def add_inter_layer_bundle(self, source_layer: str, source_ids: List[str],
                                target_layer: str, target_ids: List[str],
                                **kwargs) -> MetaSynapticBundle:
        b = MetaSynapticBundle(
            bundle_id=_uid("ilb"),
            source_neuron_ids=source_ids,
            target_neuron_ids=target_ids,
            **kwargs)
        b.init_weights()
        self.inter_layer_bundles.append(b)
        return b

    # ─── T: Transport (activation propagation) ───

    def transport(self, input_activations: Dict[str, float],
                  input_layer: str) -> Dict[str, float]:
        """T-phase: propagate activations through the circuit.

        Returns: output activations from the last layer.
        """
        layer = self.layers.get(input_layer)
        if not layer:
            return {}

        # Inject inputs
        for nid, val in input_activations.items():
            if nid in layer.neurons:
                layer.neurons[nid].activate(val)

        # Propagate through intra-layer bundles
        tick_heat = 0.0
        for bundle in layer.bundles:
            src_acts = [layer.neurons[sid].activation
                        for sid in bundle.source_neuron_ids
                        if sid in layer.neurons]
            if not src_acts:
                continue
            tgt_acts = bundle.propagate(src_acts)
            # Apply to target neurons
            for j, tid in enumerate(bundle.target_neuron_ids):
                if tid in layer.neurons and j < len(tgt_acts):
                    layer.neurons[tid].activate(tgt_acts[j])
            tick_heat += bundle.transport_cost
            # v40.7: Transport cost → source neuron energy drain (intra-layer)
            # DEGRADED: dendritic ATP consumption → proxy as proportional drain
            # degraded_from = "dendritic_transport_ATP_consumption"
            if bundle.transport_cost > 0:
                per_neuron_cost = bundle.transport_cost / max(len(bundle.source_neuron_ids), 1)
                for sid in bundle.source_neuron_ids:
                    sn = layer.neurons.get(sid)
                    if sn:
                        sn.energy = max(0.0, sn.energy - per_neuron_cost)

        # Propagate through inter-layer bundles
        for bundle in self.inter_layer_bundles:
            src_layer = None
            for lid, l in self.layers.items():
                if bundle.source_neuron_ids[0] in l.neurons:
                    src_layer = l
                    break
            if src_layer is None:
                continue
            src_acts = [src_layer.neurons.get(sid, MetaNeuron("_","_")).activation
                        for sid in bundle.source_neuron_ids]
            tgt_acts = bundle.propagate(src_acts)
            for lid, l in self.layers.items():
                for j, tid in enumerate(bundle.target_neuron_ids):
                    if tid in l.neurons and j < len(tgt_acts):
                        l.neurons[tid].activate(tgt_acts[j])
            tick_heat += bundle.transport_cost
            # v40.7: Transport cost → source neuron energy drain
            # DEGRADED: axonal ATP consumption → proxy as proportional drain
            # degraded_from = "axonal_transport_ATP_consumption"
            if bundle.transport_cost > 0 and src_layer is not None:
                per_neuron_cost = bundle.transport_cost / max(len(bundle.source_neuron_ids), 1)
                for sid in bundle.source_neuron_ids:
                    sn = src_layer.neurons.get(sid)
                    if sn:
                        sn.energy = max(0.0, sn.energy - per_neuron_cost)

        # ── Lateral inhibition (structural discrimination mechanism) ──
        # In real neural circuits (V1, barrel cortex), the most activated
        # neuron in a population suppresses its neighbors via inhibitory
        # interneurons. This creates stimulus selectivity: different inputs
        # activate DIFFERENT dominant neurons.
        #
        # Inhibition strength is modulated by entropy ledger temperature:
        #   high temperature → weak inhibition (exploratory, broad tuning)
        #   low temperature  → strong inhibition (sharp, narrow tuning)
        self._apply_lateral_inhibition(layer)

        # DEGRADED: heat → entropy ledger proxy
        self._total_heat += tick_heat
        self._temperature = self._total_heat / max(self.tick + 1, 1)

        self._transport_log.append({
            "tick": self.tick, "heat": tick_heat,
            "temperature": self._temperature,
        })

        return layer.get_activations()

    # ─── O: Observable (measurable configuration change) ───

    def observe(self) -> Dict[str, Any]:
        """O-phase: compute observable state change."""
        total_activation = 0.0
        total_neurons = 0
        for layer in self.layers.values():
            for n in layer.neurons.values():
                total_activation += abs(n.activation)
                total_neurons += 1

        prev_delta = self._observable_delta
        self._observable_delta = total_activation / max(total_neurons, 1)
        return {
            "observable_activation": self._observable_delta,
            "delta_from_prev": self._observable_delta - prev_delta,
            "temperature": self._temperature,
            "tick": self.tick,
        }

    # ─── Lateral Inhibition (structural discrimination) ───

    def _apply_lateral_inhibition(self, layer: CircuitLayer):
        """Apply lateral inhibition among target (z_t) neurons.

        Biological basis: In cortical circuits, excitatory neurons activate
        inhibitory interneurons which suppress neighboring excitatory neurons.
        The result: the most strongly activated neuron "wins" and the others
        are relatively suppressed. This creates stimulus selectivity.

        Mechanism:
          1. Find all target neurons (z_t dimensions) in the layer
          2. Compute mean activation
          3. Suppress neurons below mean, boost neurons above mean
          4. Strength modulated by temperature (entropy ledger proxy)

        The inhibition creates DIRECTION changes in the z_t vector — different
        stimuli will have different winner neurons, breaking the trivial
        resonance (cos > 0.998) that plagued the flat W_signal.
        """
        # Identify target neurons (z_t cost dimensions)
        target_ids = ["transition", "drift", "gamma_desync",
                      "xin_residual", "potential_disp", "churn", "magnitude"]
        targets = [(nid, layer.neurons[nid])
                   for nid in target_ids if nid in layer.neurons]
        if len(targets) < 2:
            return

        activations = [max(0.0, n.activation) for _, n in targets]

        # ── Divisive Normalization (Carandini & Heeger 2012) ──
        # R_i = x_i^n / (σ^n + Σ_j x_j^n)
        #
        # This is the canonical cortical gain control model:
        # - Each neuron's response is divided by the total pool activity
        # - Weak responses remain positive (just proportionally smaller)
        # - σ (semi-saturation constant) prevents division by zero and
        #   controls how much suppression occurs at low activity
        #
        # Temperature modulates n (exponent):
        # - Cold → high n → sharp selectivity (winner takes more)
        # - Hot → low n → flat (exploratory, everyone gets some)
        temp = max(self._temperature, 0.001)
        n_exp = min(3.0, max(1.0, 0.02 / temp))  # exponent: 1.0-3.0

        # Semi-saturation constant: controls baseline suppression
        sigma_n = 0.01 ** n_exp  # small σ → strong normalization

        # Compute x_i^n for each neuron
        powered = [max(0.0, a) ** n_exp for a in activations]
        pool_sum = sum(powered) + sigma_n  # denominator

        for i, (nid, neuron) in enumerate(targets):
            if pool_sum > 0 and activations[i] > 0:
                neuron.activation = powered[i] / pool_sum
            else:
                neuron.activation = 0.0

        # ── Stage 2: Mild subtractive contrast (post-normalization) ──
        # After divisive normalization, all values sum to ~1.
        # Apply mild contrast enhancement to sharpen differences.
        # This is gentler than raw subtractive because we start from
        # normalized proportions, not raw values.
        norm_acts = [n.activation for _, n in targets]
        norm_mean = sum(norm_acts) / len(norm_acts)
        contrast = 0.3  # mild: preserve 70% of original + 30% contrast
        for nid, neuron in targets:
            dev = neuron.activation - norm_mean
            neuron.activation = neuron.activation + contrast * dev
            neuron.activation = max(0.0, neuron.activation)


    # ─── P/R: Circulation Measure (probabilistic hypergraph integral) ───

    def detect_circulations(self) -> Tuple[Optional[List[str]],
                                            Optional[List[str]]]:
        """Compute the circulation measure μ(G) of the entire Hebbian hypergraph.

        ALL circulations — active, dormant, pruned — contribute to ONE
        probability measure. Each circuit path's contribution is weighted
        by its structural occupation:

          μ(G) = Σ_cycle_i  ω_i · Π_{bundle ∈ cycle_i} s(bundle)

        where:
          ω_i = occupation probability = s(bundle) / Σ_all s(bundle)
          s(bundle) = bundle_strength for active bundles
                    = ghost_strength for pruned bundles (0 < ghost << 1)
                    = dormant_value for fruit-bearing bundles

        The primary circulation P is the maximum-flow path;
        the secondary R is the runner-up. But critically:

          P.value = Σ_all μ_i   (P CONTAINS all secondary values)

        This means P is not just "the strongest path" but the integral
        of the entire structure's information occupation in the long window.
        Dormant fruits and ghost residuals contribute their curled values
        to P, making P the total structural fingerprint.
        """
        all_bundles = []
        ghost_bundles = []
        for layer in self.layers.values():
            all_bundles.extend(layer.bundles)
            # Ghost bundles: residuals of pruned bundles (low-probability states)
            ghost_bundles.extend(getattr(layer, '_ghost_bundles', []))
        all_bundles.extend(self.inter_layer_bundles)

        if not all_bundles and not ghost_bundles:
            self._p_circulation = None
            self._r_circulation = None
            self._circulation_measure = 0.0
            return None, None

        # ── Compute structural occupation probability per bundle ──
        # All bundles (active + ghost) contribute to the total measure
        total_strength = sum(b.bundle_strength for b in all_bundles) + \
                         sum(g.get("ghost_strength", 0.001) for g in ghost_bundles)
        total_strength = max(total_strength, 1e-10)

        # Occupation probability: each bundle's fraction of total structure
        bundle_occupation = {}
        for b in all_bundles:
            # Active bundles: strength + dormant fruit tension contribution
            fruit_contribution = 0.0
            if b.xin_dormant_fruit is not None:
                # Dormant fruit's curled value contributes to occupation
                fruit_tension = abs(b.xin_dormant_fruit.get(
                    "tension_at_creation", 0.0))
                fruit_contribution = fruit_tension * 0.01  # small but nonzero
            bundle_occupation[b.bundle_id] = (
                b.bundle_strength + fruit_contribution) / total_strength

        # Ghost bundles: very low occupation (pruned ≈ probability→0, not 0)
        for g in ghost_bundles:
            g_id = g.get("bundle_id", "ghost_unknown")
            bundle_occupation[g_id] = g.get(
                "ghost_strength", 0.001) / total_strength

        # ── Build adjacency for cycle detection ──
        src_to_bundles: Dict[str, List[MetaSynapticBundle]] = {}
        for b in all_bundles:
            for sid in b.source_neuron_ids:
                src_to_bundles.setdefault(sid, []).append(b)

        # Find closed paths (cycles) up to depth 4
        cycles: List[Tuple[float, List[str]]] = []

        for start_bundle in all_bundles:
            path = [start_bundle.bundle_id]
            flow = bundle_occupation.get(start_bundle.bundle_id, 0.0)
            current_targets = set(start_bundle.target_neuron_ids)
            start_sources = set(start_bundle.source_neuron_ids)

            self._dfs_cycles(current_targets, start_sources, path, flow,
                            src_to_bundles, cycles, max_depth=3,
                            occupation=bundle_occupation)

        if not cycles:
            self._p_circulation = None
            self._r_circulation = None
            self._circulation_measure = 0.0
            return None, None

        # ── Compute full circulation measure ──
        # μ(G) = sum of ALL cycle flows (P contains all)
        self._circulation_measure = sum(c[0] for c in cycles)

        # P = max flow path, R = runner-up
        cycles.sort(key=lambda c: c[0], reverse=True)
        self._p_circulation = cycles[0][1]
        self._r_circulation = cycles[1][1] if len(cycles) > 1 else None

        # Store per-cycle contributions for structural audit
        self._all_cycle_measures = [
            {"path": c[1], "flow": c[0],
             "fraction": c[0] / max(self._circulation_measure, 1e-10)}
            for c in cycles[:10]  # top 10 for audit
        ]

        return self._p_circulation, self._r_circulation

    def _dfs_cycles(self, current_targets, goal_sources, path, flow,
                    src_to_bundles, cycles, max_depth, occupation=None):
        if max_depth <= 0:
            return
        overlap = current_targets & goal_sources
        if overlap and len(path) >= 2:
            cycles.append((flow, list(path)))
            return

        for tid in current_targets:
            for next_b in src_to_bundles.get(tid, []):
                if next_b.bundle_id in path:
                    continue
                # Flow = min(current, next bundle's occupation)
                next_occ = (occupation or {}).get(
                    next_b.bundle_id, next_b.bundle_strength)
                new_flow = min(flow, next_occ)
                path.append(next_b.bundle_id)
                next_targets = set(next_b.target_neuron_ids)
                self._dfs_cycles(next_targets, goal_sources, path,
                                new_flow, src_to_bundles, cycles,
                                max_depth - 1, occupation)
                path.pop()

    # ─── Xin: Prediction residual → tension on edges ───

    def compute_xin(self, predicted_activations: Dict[str, float]):
        """Xin-phase: compare predicted vs actual, store tension."""
        self._activated_fruits = []
        for layer in self.layers.values():
            for bundle in layer.bundles:
                for tid in bundle.target_neuron_ids:
                    pred = predicted_activations.get(tid, 0.0)
                    actual = layer.neurons[tid].activation if tid in layer.neurons else 0.0
                    bundle.accumulate_xin(pred, actual)
                    self._xin_tensions[bundle.bundle_id] = bundle.xin_tension

                    # Try to activate dormant fruits
                    bias = actual - pred  # negative tension = unexpected signal
                    fruit = bundle.try_activate_fruit(bias)
                    if fruit:
                        self._activated_fruits.append(fruit)

    # ─── Learn: STDP on all bundles ───

    def learn(self):
        """STDP learning on all bundles, modulated by entropy ledger temperature.

        Uses neuron STDP traces (pre_trace, post_trace) for causal timing.
        Temperature from entropy ledger proxy modulates learning rate:
          hot → slower learning (exploration)
          cold → faster learning (exploitation/consolidation)
        """
        eta_scale = 1.0 / max(self._temperature, 0.1)
        eta_scale = max(0.1, min(2.0, eta_scale))

        total_delta = 0.0
        for layer in self.layers.values():
            for bundle in layer.bundles:
                # Get actual neuron objects for STDP traces
                pre_neurons = [layer.neurons[sid]
                               for sid in bundle.source_neuron_ids
                               if sid in layer.neurons]
                post_neurons = [layer.neurons[tid]
                                for tid in bundle.target_neuron_ids
                                if tid in layer.neurons]
                if pre_neurons and post_neurons:
                    d = bundle.stdp_update(pre_neurons, post_neurons, eta_scale)
                    total_delta += d

                    # Mark post-activation timing for STDP
                    for n in post_neurons:
                        n.post_activate()

        return total_delta

    # ─── Maintain: decay, pruning, maturation ───

    def maintain(self):
        """Per-tick maintenance: decay, pruning, maturation, synaptic scaling.

        v40.1: Added homeostatic synaptic scaling (Turrigiano 1998):
        When a postsynaptic neuron's calcium is below target, all incoming
        synaptic weights are multiplicatively scaled UP. This is the
        structural mechanism that prevents neuron silencing.
        """
        pruned = []
        for layer in self.layers.values():
            # Neuron decay + maturation
            tick_neuron_heat = 0.0
            for n in layer.neurons.values():
                n.decay()
                n.try_mature()
                # v40.7d: Aggregate neuron heat_output → circuit temperature
                # This closes the heat_output chain:
                #   activate() writes → maintain() reads → _temperature updates
                # _temperature in turn modulates lateral inhibition strength.
                # DEGRADED: local metabolic heat transfer → proxy as sum
                # degraded_from = "local_metabolic_heat_dissipation"
                tick_neuron_heat += n.heat_output
                n.heat_output = 0.0  # reset each tick (consumed)
            self._total_heat += tick_neuron_heat
            self._temperature = self._total_heat / max(self.tick + 1, 1)

            # ── v40.7: Column Lateral Suppression Field ──
            # Physical mechanism: Column neurons generate an inhibitory field
            # via basket cell interneurons. The field strength is NOT static —
            # it is driven by the Column's calcium (integrated activity history).
            #   suppression_force = calcium / target_rate × activation × 1/distance
            # This means: a highly active Column (high calcium) suppresses harder.
            # An inactive Column (low calcium) has negligible suppression.
            # DEGRADED: basket cell dynamics → proxy as calcium-scaled threshold push
            # degraded_from = "basket_cell_interneuron_dynamics"
            neuron_ids = list(layer.neurons.keys())
            for idx, nid in enumerate(neuron_ids):
                n = layer.neurons[nid]
                if n.lateral_suppression_radius <= 0:
                    continue  # Spine — no suppression power
                # Suppression field strength ∝ calcium relative to target
                # Column with calcium=0 has zero suppression even if matured
                field_strength = n.calcium / max(n.target_rate, 0.001)
                field_strength = min(field_strength, 3.0)  # cap at 3× target
                if field_strength < 0.1:
                    continue  # negligible field — skip computation
                radius = n.lateral_suppression_radius
                for offset in range(-radius, radius + 1):
                    if offset == 0:
                        continue
                    neighbor_idx = idx + offset
                    if 0 <= neighbor_idx < len(neuron_ids):
                        neighbor = layer.neurons[neuron_ids[neighbor_idx]]
                        if neighbor.maturation == "spine":
                            dist = abs(offset)
                            # Force = field_strength × activation × 1/dist²
                            # 1/dist² gives inverse-square law (physical)
                            suppression = field_strength * abs(n.activation) * 0.001 / (dist * dist)
                            neighbor.threshold += suppression

            # ── v40.7: PRP Emission + Capture (Synaptic Tagging & Capture) ──
            # Mechanism (Frey & Morris 1997):
            #   1. Column emits PRP when calcium > prp_threshold (emission phase)
            #   2. PRP proteins diffuse to nearby bundles (diffusion proxy)
            #   3. Bundles whose target Spines have dormant fruits CAPTURE the PRP
            #   4. Capture boosts the fruit's trace_strength (extends eligibility window)
            # This is the structural coupling between Column privilege and
            # Spine memory consolidation — without it PRP is just a number.
            # DEGRADED: protein diffusion → proxy as direct emission/capture
            # degraded_from = "protein_synthesis_and_diffusion_dynamics"
            total_prp_available = 0.0
            for n in layer.neurons.values():
                if n.prp_threshold > 0 and n.calcium > n.prp_threshold:
                    n.prp_emission = min(1.0, n.prp_emission + 0.05)
                    total_prp_available += n.prp_emission
                else:
                    n.prp_emission *= 0.95  # PRP decays when not actively emitted

            # PRP Capture: bundles with dormant fruits on Spine targets capture PRP
            if total_prp_available > 0.01:
                for bundle in layer.bundles:
                    if bundle.xin_dormant_fruit is None:
                        continue
                    # Check if any target neuron is a Spine (capturable)
                    has_spine_target = any(
                        layer.neurons.get(tid, MetaNeuron("_","_")).maturation == "spine"
                        for tid in bundle.target_neuron_ids
                    )
                    if has_spine_target:
                        # Capture: PRP extends the fruit's eligibility window
                        f = bundle.xin_dormant_fruit
                        capture_amount = min(0.1, total_prp_available * 0.02)
                        f["trace_strength"] = min(1.0, f["trace_strength"] + capture_amount)

            # ── v40.7: Dormant Fruit Chemical Trace Decay + Third Factor ──
            # Three-factor learning (Gerstner et al 2018):
            #   Δw = η × eligibility_trace × neuromodulatory_signal
            # The fruit's trace_strength IS the eligibility trace.
            # The "third factor" is the Xin tension on the bundle itself:
            #   - High |xin_tension| = strong prediction error = preserve trace longer
            #   - Low |xin_tension| = system is well-predicted = let trace decay faster
            # This implements: recent errors in high-tension regions are remembered
            # longer than errors in stable regions.
            # DEGRADED: neuromodulatory signal → proxy as Xin tension magnitude
            # degraded_from = "dopaminergic_modulation_of_eligibility_traces"
            for bundle in layer.bundles:
                if bundle.xin_dormant_fruit is not None:
                    f = bundle.xin_dormant_fruit
                    # Third factor: Xin tension modulates decay rate
                    # High tension → slower decay (trace preserved)
                    # Low tension → faster decay (trace forgotten)
                    tension_factor = min(2.0, abs(bundle.xin_tension))
                    # Effective decay = base_decay^(1 / (1 + tension_factor))
                    # When tension=0: decay=0.995 (normal)
                    # When tension=2: decay=0.995^(1/3)=0.9983 (slower)
                    base_decay = f.get("trace_decay", 0.995)
                    effective_decay = base_decay ** (1.0 / (1.0 + tension_factor))
                    f["trace_strength"] *= effective_decay
                    if f["trace_strength"] < 0.01:
                        bundle.xin_dormant_fruit = None  # expired
            for bundle in self.inter_layer_bundles:
                if bundle.xin_dormant_fruit is not None:
                    f = bundle.xin_dormant_fruit
                    tension_factor = min(2.0, abs(bundle.xin_tension))
                    base_decay = f.get("trace_decay", 0.995)
                    effective_decay = base_decay ** (1.0 / (1.0 + tension_factor))
                    f["trace_strength"] *= effective_decay
                    if f["trace_strength"] < 0.01:
                        bundle.xin_dormant_fruit = None

            # ── Homeostatic Synaptic Scaling (HSS) ──
            # For each target neuron: if calcium < target → scale up incoming weights
            # This is multiplicative, not additive — preserves relative weight structure
            for bundle in layer.bundles:
                for j, tid in enumerate(bundle.target_neuron_ids):
                    if tid not in layer.neurons:
                        continue
                    target_n = layer.neurons[tid]
                    if target_n.calcium < target_n.target_rate * 0.5:
                        # Neuron is significantly below target → scale up
                        scale = 1.0 + 0.02 * (target_n.target_rate - target_n.calcium) / max(target_n.target_rate, 0.001)
                        scale = min(scale, 1.05)  # max 5% per tick
                        for i in range(len(bundle.weights)):
                            if j < len(bundle.weights[i]):
                                bundle.weights[i][j] = min(1.0, bundle.weights[i][j] * scale)
                    elif target_n.calcium > target_n.target_rate * 2.0:
                        # Neuron is significantly above target → scale down
                        scale = 1.0 - 0.01 * (target_n.calcium - target_n.target_rate) / max(target_n.target_rate, 0.001)
                        scale = max(scale, 0.95)  # max 5% down per tick
                        for i in range(len(bundle.weights)):
                            if j < len(bundle.weights[i]):
                                bundle.weights[i][j] = max(0.0, bundle.weights[i][j] * scale)

            # ── v40.7f: Bundle inertia recovery ──
            # STDP depletes inertia; stable bundles recover it.
            # This closes the bundle_inertia dynamics chain:
            #   STDP → depletes inertia → maintain() → recovers inertia
            # A bundle with stable weights (low _recent_delta) consolidates,
            # like myelin sheath thickening around stable axonal connections.
            # DEGRADED: myelin formation dynamics → proxy as delta-gated recovery
            # degraded_from = "oligodendrocyte_myelination_dynamics"
            for bundle in layer.bundles:
                recent_delta = getattr(bundle, '_recent_delta', 0.0)
                if recent_delta < 0.01:
                    # Stable bundle → recover inertia (myelination proxy)
                    bundle.bundle_inertia = min(5.0, bundle.bundle_inertia + 0.005)
                bundle._recent_delta = 0.0  # reset for next tick
            for bundle in self.inter_layer_bundles:
                recent_delta = getattr(bundle, '_recent_delta', 0.0)
                if recent_delta < 0.01:
                    bundle.bundle_inertia = min(5.0, bundle.bundle_inertia + 0.005)
                bundle._recent_delta = 0.0

            # Bundle pruning → ghost residuals
            # Pruned bundles don't vanish: they leave ghost residuals
            # at extremely low occupation probability. Their information
            # trajectory still exists in the structure's long-window measure.
            surviving = []
            if not hasattr(layer, '_ghost_bundles'):
                layer._ghost_bundles = []
            for b in layer.bundles:
                if b.should_prune():
                    pruned.append(b.bundle_id)
                    # Create ghost: structural residual of the pruned bundle
                    ghost = {
                        "bundle_id": b.bundle_id,
                        "source_neuron_ids": list(b.source_neuron_ids),
                        "target_neuron_ids": list(b.target_neuron_ids),
                        "ghost_strength": max(0.001, b.bundle_strength * 0.01),
                        "xin_tension_at_death": b.xin_tension,
                        "fruit_at_death": b.xin_dormant_fruit,
                        "created_tick": self.tick,
                    }
                    layer._ghost_bundles.append(ghost)
                else:
                    surviving.append(b)
            layer.bundles = surviving

            # Ghost decay: ghosts slowly fade but never reach zero
            for g in layer._ghost_bundles:
                g["ghost_strength"] = max(0.0001,
                    g["ghost_strength"] * 0.99)  # 1% decay per tick

            # Ghost resurrection: if a ghost's tension is confirmed by
            # current circuit state (high Xin tension in its target area),
            # the ghost can revive as a weak active bundle.
            # This implements: dormant → activated → competitive
            revived = []
            still_ghosts = []
            for g in layer._ghost_bundles:
                # Check if ghost's target neurons have high unmet tension
                tension_sum = sum(
                    abs(self._xin_tensions.get(bid, 0.0))
                    for bid in [b.bundle_id for b in layer.bundles]
                    if any(t in g["target_neuron_ids"]
                           for t in [b2 for b in layer.bundles
                                     for b2 in b.target_neuron_ids])
                )
                # Resurrection threshold: ghost can revive if system tension
                # in its region exceeds the tension at death
                death_tension = abs(g.get("xin_tension_at_death", 0.0))
                if tension_sum > death_tension * 2.0 and death_tension > 0.1:
                    # Resurrect: create a new weak bundle from ghost
                    new_b = MetaSynapticBundle(
                        bundle_id=g["bundle_id"] + "_revived",
                        source_neuron_ids=g["source_neuron_ids"],
                        target_neuron_ids=g["target_neuron_ids"],
                        bundle_strength=g["ghost_strength"] * 10.0,
                    )
                    new_b.init_weights()
                    # Scale weights down — ghost is weak initially
                    for i in range(len(new_b.weights)):
                        for j in range(len(new_b.weights[i])):
                            new_b.weights[i][j] *= 0.1
                    revived.append(new_b)
                else:
                    still_ghosts.append(g)
            layer._ghost_bundles = still_ghosts
            layer.bundles.extend(revived)
            if revived:
                pruned.append(f"REVIVED:{len(revived)}")
        # ── v40.7e: Convergence detection (shared sub-manifold) ──
        self._update_convergence()

        self.tick += 1
        return pruned

    def _update_convergence(self):
        """v40.7e: Detect and structurally represent shared P/R/Xin sub-manifolds.

        Physical basis: Anterior Cingulate Cortex (ACC) and prefrontal regions
        detect when multiple independent processing streams converge on
        overlapping representations. This convergence is NOT just a metric —
        it becomes a structural entity that influences future processing.

        Mechanism:
          1. Scan z_t neurons in encoding layer for concurrent activation
          2. Update running co-activation matrix (exponential average)
          3. When co-activation > threshold → create convergence node
          4. Convergence nodes feed back: lower threshold of constituent dims
             (shared subspace becomes easier to activate = structural priming)
          5. Nodes decay without reinforcement → circuit forgets unused manifolds

        Structural Dynamics Invariant:
          Generation: co-activation creates/strengthens nodes
          Decay: nodes × 0.99 per tick without reinforcement
          Coupling: nodes lower constituent dim thresholds (priming)

        DEGRADED: ACC/PFC associative dynamics → proxy as co-activation matrix
        degraded_from = "anterior_cingulate_cortex_convergence_detection"
        """
        enc = self.layers.get("encoding")
        if enc is None:
            return

        # Identify z_t neurons by exclusion (not zone_ or sig_ prefixed)
        zt_neurons = {nid: n for nid, n in enc.neurons.items()
                      if not nid.startswith("zone_") and not nid.startswith("sig_")}

        # Step 1: Compute current activation vector
        active_dims = []
        for nid, n in zt_neurons.items():
            if abs(n.activation) > n.threshold * 0.5:  # above half-threshold
                active_dims.append(nid)

        # Step 2: Update co-activation matrix for all active pairs
        for i, a in enumerate(active_dims):
            for b in active_dims[i+1:]:
                key = tuple(sorted([a, b]))
                if key[0] not in self._convergence_matrix:
                    self._convergence_matrix[key[0]] = {}
                # Exponential moving average of co-activation
                prev = self._convergence_matrix[key[0]].get(key[1], 0.0)
                co_strength = abs(zt_neurons[a].activation) * abs(zt_neurons[b].activation)
                self._convergence_matrix[key[0]][key[1]] = prev * 0.95 + co_strength * 0.05

        # Step 3: Decay all co-activation entries
        for a_key in list(self._convergence_matrix.keys()):
            for b_key in list(self._convergence_matrix[a_key].keys()):
                self._convergence_matrix[a_key][b_key] *= self._convergence_decay
                if self._convergence_matrix[a_key][b_key] < 1e-6:
                    del self._convergence_matrix[a_key][b_key]
            if not self._convergence_matrix[a_key]:
                del self._convergence_matrix[a_key]

        # Step 4: Create/strengthen convergence nodes for strong pairs
        convergence_threshold = 0.0001
        for a_key, b_dict in self._convergence_matrix.items():
            for b_key, strength in b_dict.items():
                if strength > convergence_threshold:
                    node_id = f"conv_{a_key}_{b_key}"
                    if node_id not in self._convergence_nodes:
                        self._convergence_nodes[node_id] = {
                            "dims": [a_key, b_key],
                            "strength": strength,
                            "created_tick": self.tick,
                            "priming_applied": 0.0,
                        }
                    else:
                        node = self._convergence_nodes[node_id]
                        node["strength"] = node["strength"] * 0.9 + strength * 0.1

        # Step 5: Decay convergence nodes
        dead_nodes = []
        for node_id, node in self._convergence_nodes.items():
            node["strength"] *= 0.99
            if node["strength"] < 0.01 * convergence_threshold:
                dead_nodes.append(node_id)
        for node_id in dead_nodes:
            del self._convergence_nodes[node_id]

        # Step 6: Structural coupling — convergence push-pull
        # A. PRIMING (excitatory): shared dims get threshold LOWERED
        #    → shared subspace becomes easier to activate
        # B. CONTRAST (inhibitory): exclusive dims get threshold RAISED
        #    → exclusive subspace becomes harder to activate from shared context
        # This push-pull prevents priming from destroying discrimination.
        # DEGRADED: associative priming + lateral inhibition
        # degraded_from = "ACC_push_pull_conflict_monitoring"
        converged_dims = set()
        for node in self._convergence_nodes.values():
            if node["strength"] > convergence_threshold * 0.5:
                for d in node["dims"]:
                    converged_dims.add(d)

        for node_id, node in self._convergence_nodes.items():
            if node["strength"] < convergence_threshold * 0.5:
                continue
            # A. Prime converged dims (threshold ↓)
            for dim_id in node["dims"]:
                if dim_id in enc.neurons:
                    n = enc.neurons[dim_id]
                    priming = min(node["strength"] * 0.001, 0.0001)
                    n.threshold = max(n.threshold - priming,
                                      max(0.0001, n.target_rate * 0.1))
                    node["priming_applied"] = priming

        # B. Contrast: exclusive dims (in zt but NOT in any convergence node)
        # get a small threshold INCREASE — making them more selective
        exclusive_dims = set(zt_neurons.keys()) - converged_dims
        if converged_dims and exclusive_dims:
            # Contrast strength proportional to total convergence
            total_conv_strength = sum(
                n["strength"] for n in self._convergence_nodes.values())
            contrast = min(total_conv_strength * 0.0005, 0.00005)
            for dim_id in exclusive_dims:
                if dim_id in enc.neurons:
                    n = enc.neurons[dim_id]
                    n.threshold = min(0.5, n.threshold + contrast)

    # ─── Full tick ───

    def run_tick(self, input_activations: Dict[str, float],
                 input_layer: str,
                 predicted_activations: Optional[Dict[str, float]] = None):
        """Run one full T/O/P/R/Xin tick."""
        # T: Transport
        self.transport(input_activations, input_layer)
        # O: Observe
        obs = self.observe()
        # P/R: Circulation detection
        p_circ, r_circ = self.detect_circulations()
        # Xin: Prediction residual
        if predicted_activations:
            self.compute_xin(predicted_activations)
        # Learn
        total_dw = self.learn()
        # Maintain
        pruned = self.maintain()

        result = {
            "tick": self.tick - 1,
            "observable": obs,
            "p_circulation": p_circ,
            "r_circulation": r_circ,
            "xin_tensions": len(self._xin_tensions),
            "activated_fruits": len(self._activated_fruits),
            "total_delta_w": round(total_dw, 6),
            "pruned_bundles": pruned,
            "temperature": round(self._temperature, 6),
        }

        self._audit.append(result)
        return result

    # ─── Metrics ───

    def get_metrics(self) -> Dict[str, Any]:
        total_neurons = sum(len(l.neurons) for l in self.layers.values())
        total_bundles = (sum(len(l.bundles) for l in self.layers.values())
                        + len(self.inter_layer_bundles))
        alive = sum(1 for l in self.layers.values()
                    for n in l.neurons.values() if n.is_alive())
        maturation_counts = {"spine": 0, "column": 0, "area": 0}
        for l in self.layers.values():
            for n in l.neurons.values():
                maturation_counts[n.maturation] = (
                    maturation_counts.get(n.maturation, 0) + 1)
        dormant_fruits = sum(
            1 for l in self.layers.values()
            for b in l.bundles if b.xin_dormant_fruit is not None)

        return {
            "total_neurons": total_neurons,
            "alive_neurons": alive,
            "total_bundles": total_bundles,
            "maturation": maturation_counts,
            "dormant_fruits": dormant_fruits,
            "p_circulation": self._p_circulation,
            "r_circulation": self._r_circulation,
            "temperature": round(self._temperature, 6),
            "tick": self.tick,
        }

    # ─── Transport Feedback Injection ───

    def inject_transport_feedback(self, edge_costs: list,
                                  theta: float, rejection_count: int,
                                  total_edges: int):
        """Inject pipeline transport costs as structural signal into circuit.

        This is the key mechanism for solving W_signal discrimination:
        instead of relying only on signal statistics (sig_mean, sig_std...),
        the circuit also receives structural information from the transport
        layer — edge cost distribution, gating rejection rate, cost entropy.

        These structural signals modulate the z_t target neurons directly,
        giving different stimulus types distinguishable transport signatures.

        Args:
            edge_costs: list of transport edge costs from write_transport
            theta: adaptive gating threshold
            rejection_count: number of edges rejected by theta
            total_edges: total edges evaluated
        """
        if not edge_costs:
            return

        enc = self.layers.get("encoding")
        if enc is None:
            return

        import math

        # ── Compute 3 structural features from transport costs ──
        n = len(edge_costs)
        cost_mean = sum(edge_costs) / n
        cost_std = math.sqrt(sum((c - cost_mean)**2 for c in edge_costs) / n)

        # Transport entropy (how spread out is the cost distribution?)
        # Higher entropy = more uniform = less structured transport
        sorted_c = sorted(edge_costs)
        bins = min(10, n)
        bin_size = n // bins
        probs = []
        for b in range(bins):
            start = b * bin_size
            end = start + bin_size if b < bins - 1 else n
            p = (end - start) / n
            probs.append(p)
        transport_entropy = -sum(p * math.log(max(p, 1e-10)) for p in probs)
        transport_entropy /= math.log(max(bins, 2))  # normalize to [0, 1]

        # Rejection rate (how selective is the gating?)
        rejection_rate = rejection_count / max(total_edges, 1)

        # ── Temporal derivatives (these DO vary across stimulus types) ──
        prev_cost = getattr(self, '_prev_transport_cost_mean', cost_mean)
        prev_std = getattr(self, '_prev_transport_cost_std', cost_std)
        prev_entropy = getattr(self, '_prev_transport_entropy', transport_entropy)
        prev_reject = getattr(self, '_prev_rejection_rate', rejection_rate)

        d_cost = cost_mean - prev_cost           # signed change
        d_std = cost_std - prev_std               # variability change
        d_entropy = transport_entropy - prev_entropy  # structure change
        d_reject = rejection_rate - prev_reject   # selectivity change

        self._prev_transport_cost_mean = cost_mean
        self._prev_transport_cost_std = cost_std
        self._prev_transport_entropy = transport_entropy
        self._prev_rejection_rate = rejection_rate

        # ── Multiplicative gain modulation on z_t neurons ──
        # Instead of adding a constant (which doesn't discriminate),
        # we SCALE each z_t dimension by a stimulus-dependent gain.
        # gain > 1.0 amplifies that dimension, gain < 1.0 suppresses it.
        gain_map = {
            "transition":     1.0 + d_cost * 10.0,     # cost jump → amplify transition
            "drift":          1.0 + d_std * 8.0,        # variability change → amplify drift
            "gamma_desync":   1.0 + d_entropy * 5.0,    # entropy shift → amplify desync
            "xin_residual":   1.0 + d_reject * 6.0,     # selectivity change → residual
            "potential_disp": 1.0 + abs(d_cost) * 4.0,  # any cost change → potential
            "churn":          1.0 + abs(d_std) * 3.0,   # any spread change → churn
            "magnitude":      1.0 - d_entropy * 2.0,    # entropy increase → suppress magnitude
        }

        for nid, gain in gain_map.items():
            if nid in enc.neurons:
                n_obj = enc.neurons[nid]
                # Clamp gain to prevent explosion
                g = max(0.1, min(3.0, gain))
                n_obj.activation *= g



# ═══════════════════════════════════════════════════════════════
# 5. Bridge: Build circuit from existing pipeline components
# ═══════════════════════════════════════════════════════════════

def build_circuit_from_signal_transform(signal_transform) -> HebbianCircuit:
    """Construct a HebbianCircuit from existing HebbianSignalTransform.

    Maps:
      6 signal features → 6 source MetaNeurons (encoding layer)
      7 z_t dimensions  → 7 target MetaNeurons (encoding layer)
      W_signal rows     → 6 MetaSynapticBundles (1→7 hyperedges)

    This solves W_signal discrimination by making each W row a
    structural bundle with its own inertia, strength, and Xin tension.
    """
    circuit = HebbianCircuit()

    # Encoding layer: signal features → z_t dimensions
    enc = circuit.add_layer("encoding")

    feature_names = getattr(signal_transform, 'SIGNAL_FEATURES',
                           ["sig_mean", "sig_std", "sig_peak_rate",
                            "sig_temporal_d", "sig_sync", "sig_range"])
    cost_names = ["transition", "drift", "gamma_desync",
                  "xin_residual", "potential_disp", "churn", "magnitude"]

    # Source neurons (signal features)
    for fname in feature_names:
        enc.add_neuron(fname)

    # Target neurons (z_t dimensions)
    for cname in cost_names:
        enc.add_neuron(cname)

    # Bundles from W_signal rows (each row = 1-to-7 hyperedge)
    W = getattr(signal_transform, 'W', None)
    if W:
        for i, fname in enumerate(feature_names):
            if i < len(W):
                bundle = enc.add_bundle(
                    source_ids=[fname],
                    target_ids=cost_names)
                bundle.weights = [list(W[i])]
                bundle.bundle_strength = sum(W[i]) / len(W[i])
                # Mark sig_sync bundle as proxy if sync is dead
                if fname == "sig_sync":
                    bundle.degraded_features.append(
                        "sig_sync_always_zero: degraded_from=cell_coupling_spectral_gap")

    # ── Feedback bundles: z_t → signal features (creates closed loops) ──
    # These enable circulation detection (P/R).
    # Physical meaning: z_t dimensions influence future signal interpretation.
    # DEGRADED: uniform feedback weights (should emerge from learning).
    # degraded_from = "emergent_feedback_topology"
    feedback_groups = [
        # z_t group → signal feature it feeds back to
        (["transition", "drift"], ["sig_mean", "sig_std"]),
        (["gamma_desync", "xin_residual"], ["sig_peak_rate", "sig_temporal_d"]),
        (["potential_disp", "churn", "magnitude"], ["sig_sync", "sig_range"]),
    ]
    for src_ids, tgt_ids in feedback_groups:
        fb = enc.add_bundle(source_ids=src_ids, target_ids=tgt_ids)
        fb.learning_rule = "oja"
        fb.degraded_features.append(
            "uniform_feedback: degraded_from=emergent_feedback_topology")

    # ── Column layer (DEGRADED: simple EMA consolidation) ──
    # degraded_from = "BCM_learning_rule"
    col = circuit.add_layer("column")
    for cname in cost_names:
        n = col.add_neuron(f"col_{cname}", maturation="column")
        # v40.7: Grant Column physical privilege at creation
        # These neurons start as Column — give them the same asymmetric
        # physics they would get if they matured from Spine via try_mature()
        n.lateral_suppression_radius = 3
        n.stdp_ltp_boost = 2.0
        n.prp_threshold = n.target_rate * 1.5
        n.inertia = max(n.inertia, 2.0)
        n.threshold_adapt_rate *= 0.5

    # Inter-layer: encoding z_t → column (consolidation path)
    circuit.add_inter_layer_bundle(
        "encoding", cost_names,
        "column", [f"col_{c}" for c in cost_names])

    return circuit

```

### [run_v40_integrated.py](file:///D:/cell-cc/Morphosphere_v37_0_native_runtime_prototype_flat_complete/morphosphere_v2pp/runners/run_v40_integrated.py)

```diff:run_v40_integrated.py
#!/usr/bin/env python3
"""v40 Integrated Circuit — Full Pipeline + Signal Entropy + STDP + R-chain.

Holistic integration:
  1. Run full pipeline → writes ALL ledgers (entropy, anomaly, masking, transport)
  2. Write NEW v40_signal_entropy_ledger (spectral_H, fano, synchrony, gradient)
     — these actually vary across stimulus types unlike pipeline-structural entropy
  3. Read signal entropy + masking counterevidence from DB
  4. Feed into circuit: signal entropy as structural input neurons,
     masking survival rate as modulatory gain on z_t neurons
  5. STDP + homeostasis adapts structure based on measured quantities
  6. Compare discrimination with R-chain validation

The whole loop mirrors T/O/P/R/Xin:
  T = pipeline transport → DB
  O = observe signal entropy variation
  P = primary discrimination path (STDP circuit)
  R = counter-evidence from masking layer → refute weak dimensions
  Xin = residual tension → structural adjustment
"""
import sys, os, math, json, sqlite3
from pathlib import Path
from collections import defaultdict

BASE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE / "src"))
sys.path.insert(0, str(BASE))
sys.path.insert(0, str(BASE / "engines"))

from allen_brain_adapter import AllenBrainAdapter
from motion_recognition_engine import FeatureExtractor, BayesianMotionRecognizer
from hebbian_circuit import (HebbianCircuit, CircuitLayer, MetaNeuron,
                             MetaSynapticBundle, build_circuit_from_signal_transform)
import pipeline_engine as pe
import h5py

DB_PATH = str(BASE / "db" / "v40_integrated.db")


def build_signal_entropy_circuit(signal_transform) -> HebbianCircuit:
    """Build circuit with sensitivity zone differentiation.

    Architecture — differentiated sensitivity zones:
    ────────────────────────────────────────────────────────────────
    Each entropy channel gets its OWN receptive field (zone).
    All zones are simultaneously activated as the circulation baseline.
    This prevents any single dominant dimension from killing
    signal-source information from other channels.

    signal_entropy_layer: 4 neurons (spectral_H, fano_H, synchrony_H, gradient_H)
          │
          ├─→ zone_spectral (2 intermediate neurons) ─→ z_t targets
          ├─→ zone_fano (2 intermediate neurons) ─→ z_t targets
          ├─→ zone_synchrony (2 intermediate neurons) ─→ z_t targets
          └─→ zone_gradient (2 intermediate neurons) ─→ z_t targets
          │
    encoding_layer: 6 signal features → 7 z_t costs
          │
    column_layer: consolidation

    Within each zone:
      - Dedicated intermediate neurons transform entropy into
        zone-specific activation patterns
      - Each zone has its OWN feedback loop (closed circulation per zone)
      - STDP operates per-zone, allowing independent weight adaptation

    Cross-zone integration:
      - All zones project to shared z_t targets
      - Divisive normalization operates across z_t, not within zones
      - This creates proportional contribution, not winner-take-all

    The resulting μ(G) contains:
      - Per-zone circulations (local, always active at baseline)
      - Cross-zone circulations (global, emerge from STDP convergence)
      - The genuine P is the circulation that persists when any
        single zone is masked (validated by R-chain counterevidence)
    ────────────────────────────────────────────────────────────────
    """
    circuit = build_circuit_from_signal_transform(signal_transform)

    # Signal entropy input layer
    entropy_layer = CircuitLayer(layer_id="signal_entropy")
    entropy_names = ["spectral_H", "fano_H", "synchrony_H", "gradient_H",
                     "sparseness_H", "autocorrelation_H", "energy_H"]
    for name in entropy_names:
        n = entropy_layer.add_neuron(name)
        n.target_rate = 0.2
        n.threshold = 0.001
        n.energy = 1000.0  # input neurons: externally driven, should never die
    circuit.layers["signal_entropy"] = entropy_layer

    z_t_names = ["transition", "drift", "gamma_desync",
                 "xin_residual", "potential_disp", "churn", "magnitude"]

    # ── Create sensitivity zones ──
    # Each zone: entropy channel → 2 intermediate neurons → z_t targets
    # The intermediates allow per-zone STDP to learn independent patterns

    zone_specs = {
        "spectral": {
            "source": ["spectral_H"],
            "intermediates": ["zone_spec_mag", "zone_spec_pot"],
            "targets": ["magnitude", "potential_disp"],
        },
        "fano": {
            "source": ["fano_H"],
            "intermediates": ["zone_fano_churn", "zone_fano_drift"],
            "targets": ["churn", "drift"],
        },
        "synchrony": {
            "source": ["synchrony_H"],
            "intermediates": ["zone_sync_gamma", "zone_sync_trans"],
            "targets": ["gamma_desync", "transition"],
        },
        "gradient": {
            "source": ["gradient_H"],
            "intermediates": ["zone_grad_xin", "zone_grad_trans"],
            "targets": ["xin_residual", "transition"],
        },
    }

    # Higher-order features: parallel bundles to existing zone intermediates
    # These AUGMENT the existing zones without adding neurons or zones
    higher_order_pairs = [
        # (source_H, target_zone_intermediates, name)
        ("energy_H",          ["zone_spec_mag", "zone_spec_pot"], "energy_to_spectral"),
        ("sparseness_H",      ["zone_fano_churn", "zone_fano_drift"], "sparseness_to_fano"),
        ("autocorrelation_H", ["zone_grad_xin", "zone_grad_trans"], "autocorr_to_gradient"),
    ]

    for zone_name, spec in zone_specs.items():
        # Add intermediate neurons to encoding layer
        enc = circuit.layers["encoding"]
        for iname in spec["intermediates"]:
            n = enc.add_neuron(iname)
            n.target_rate = 0.1     # lower target: zone neurons are modulatory
            n.threshold = 0.0001    # very low: always respond to entropy
            n.energy = 1000.0       # modulatory neurons should never die

        sources = spec["source"]  # list of entropy channel names

        # Bundle 1: entropy sources → intermediate neurons
        b_in = MetaSynapticBundle(
            bundle_id=f"sigH_{zone_name}_to_zone",
            source_neuron_ids=sources,
            target_neuron_ids=spec["intermediates"],
            bundle_inertia=0.5, learning_rule="stdp")
        b_in.init_weights()
        # Higher initial weights for zone input — entropy should pass through
        for i in range(len(b_in.weights)):
            for j in range(len(b_in.weights[i])):
                b_in.weights[i][j] = 0.3
        circuit.inter_layer_bundles.append(b_in)

        # Bundle 2: intermediate neurons → z_t targets (within encoding)
        b_out = enc.add_bundle(
            source_ids=spec["intermediates"],
            target_ids=spec["targets"])
        b_out.bundle_id = f"zone_{zone_name}_to_zt"
        b_out.learning_rule = "stdp"
        # Initial weights: moderate, to be shaped by STDP
        for i in range(len(b_out.weights)):
            for j in range(len(b_out.weights[i])):
                b_out.weights[i][j] = 0.2

        # Bundle 3: z_t targets → entropy sources (feedback loop)
        # This closes the per-zone circulation, making each zone
        # a self-contained T/O/P/R/Xin mini-loop
        b_fb = MetaSynapticBundle(
            bundle_id=f"zone_{zone_name}_feedback",
            source_neuron_ids=spec["targets"],
            target_neuron_ids=sources,
            bundle_inertia=0.8, learning_rule="oja")
        b_fb.init_weights()
        for i in range(len(b_fb.weights)):
            for j in range(len(b_fb.weights[i])):
                b_fb.weights[i][j] = 0.05  # weak feedback initially
        circuit.inter_layer_bundles.append(b_fb)

    # Higher-order features (sparseness, autocorrelation, energy) are applied
    # as contrastive gain modulation in Step 3.5 of the circuit loop, not as
    # parallel bundles. This prevents range-mismatch flooding.

    return circuit


def cosine_sim(a, b):
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a)) + 1e-12
    nb = math.sqrt(sum(x * x for x in b)) + 1e-12
    return dot / (na * nb)


def main():
    print("=" * 72)
    print("v40 INTEGRATED: Signal Entropy + STDP + R-chain Validation")
    print("=" * 72)

    # ══════════════════════════════════════════════════════════════
    # Phase 1: T — Full pipeline → all ledgers
    # ══════════════════════════════════════════════════════════════
    print(f"\n{'─' * 72}")
    print("  Phase 1 [T]: Pipeline transport → all ledgers")
    print(f"{'─' * 72}")

    if os.path.exists(DB_PATH):
        os.remove(DB_PATH)
    conn = sqlite3.connect(DB_PATH)
    pe.apply_migrations(conn)
    conn.commit()

    adapter = AllenBrainAdapter(split_role="all")
    run_id = "v40_integrated_001"
    pe.register_adapter(conn, run_id, adapter)

    ext = FeatureExtractor()
    rec = BayesianMotionRecognizer(prior_var=1.0)
    prev_cells = None
    WINDOWS = adapter.total_windows

    # Load stimulus epochs
    nwb_path = str(BASE / "data/allen_brain/ophys_experiment_data/500964514.nwb")
    f = h5py.File(nwb_path, "r")
    pres = f["stimulus"]["presentation"]
    epochs = []
    for sn in pres.keys():
        ds = pres[sn]
        if "timestamps" in ds:
            ts = ds["timestamps"][:]
            if len(ts) >= 2:
                clean = sn.replace("_stimulus", "")
                block_start = ts[0]
                prev_t = ts[0]
                for i in range(1, len(ts)):
                    if ts[i] - prev_t > 30:
                        epochs.append((clean, float(block_start), float(prev_t)))
                        block_start = ts[i]
                    prev_t = ts[i]
                epochs.append((clean, float(block_start), float(prev_t)))
    # Sort by DURATION ascending (narrowest first) for proper matching
    # static_gratings spans [50,3803] but movie is [2362,2662] — narrowest wins
    epochs.sort(key=lambda x: x[2] - x[1])
    fl_ts = f["processing"]["brain_observatory_pipeline"]["DfOverF"]["imaging_plane_1"]["timestamps"][:]
    sub_ts = fl_ts[::38][:3003]
    f.close()

    for k in range(WINDOWS):
        cells = adapter.generate_cells(k)
        if not cells:
            continue

        env = adapter.make_envelope(k)
        env_id = pe.write_envelope(conn, run_id, env)
        pw_id = pe.write_process_window(conn, run_id, adapter, k, env_id,
                                         len(cells), ["ingest", "transport"])
        uid_map = pe.write_cells(conn, run_id, adapter, k, cells)

        if prev_cells is not None:
            pe.write_transport(conn, run_id, adapter, k, prev_cells, cells)

        hyps = pe.write_hypotheses(conn, run_id, adapter, k, cells)
        xi_id = pe.write_xi(conn, run_id, adapter, k, hyps, cells[:5])

        if prev_cells is not None:
            disps = {}
            for i in range(min(len(prev_cells), len(cells))):
                dx = cells[i].x - prev_cells[i].x
                dy = cells[i].y - prev_cells[i].y
                disps[i] = math.sqrt(dx*dx + dy*dy)
            feats = ext.extract(
                {i: (c.x, c.y) for i, c in enumerate(prev_cells)},
                {i: (c.x, c.y) for i, c in enumerate(cells)},
                disps, signal_values=[c.V_mean for c in cells])
            pred, _, _ = rec.classify(feats)
            rec.learn(feats, pred)

        # Write ALL ledgers
        pe.write_external_ledgers(conn, run_id, adapter, k, env, cells)
        # Write v40 SIGNAL entropy (the key new ledger)
        pe.write_signal_entropy_ledger(conn, run_id, adapter, k, cells)

        prev_cells = cells
        if k % 20 == 0:
            conn.commit()

    conn.commit()
    ext._signal_transform.freeze()

    # ══════════════════════════════════════════════════════════════
    # Phase 1.5 [O]: Observe signal entropy variation
    # ══════════════════════════════════════════════════════════════
    print(f"\n{'─' * 72}")
    print("  Phase 1.5 [O]: Observe signal entropy variation")
    print(f"{'─' * 72}")

    sig_rows = conn.execute(
        "SELECT window_id, spectral_entropy, fano_factor, synchrony_entropy, gradient_entropy, "
        "population_sparseness, temporal_autocorrelation, energy_concentration "
        "FROM v40_signal_entropy_ledger ORDER BY CAST(stage_k_id AS INTEGER)"
    ).fetchall()
    print(f"  Signal entropy rows: {len(sig_rows)} (7-channel)")
    for col, name in [(1, "spectral_H"), (2, "fano_H"), (3, "synchrony_H"), (4, "gradient_H")]:
        vals = [r[col] for r in sig_rows]
        mean_v = sum(vals)/len(vals)
        std_v = math.sqrt(sum((v-mean_v)**2 for v in vals)/len(vals))
        print(f"    {name:15s}: [{min(vals):.4f}, {max(vals):.4f}]  "
              f"mean={mean_v:.4f}  std={std_v:.4f}  cv={std_v/max(abs(mean_v),1e-10):.2%}")

    # Compare: old pipeline entropy vs new signal entropy coefficient of variation
    old_rows = conn.execute(
        "SELECT transport_entropy, candidate_fragment_entropy, origin_support_entropy, "
        "residual_accumulation_entropy FROM external_entropy_ledger"
    ).fetchall()
    print(f"\n  Pipeline entropy (old) — coefficient of variation:")
    for col, name in [(0, "transport_H"), (1, "candidate_H"), (2, "origin_H"), (3, "residual_H")]:
        vals = [r[col] for r in old_rows]
        mean_v = sum(vals)/len(vals)
        std_v = math.sqrt(sum((v-mean_v)**2 for v in vals)/len(vals))
        cv = std_v/max(abs(mean_v), 1e-10)
        print(f"    {name:15s}: cv={cv:.2%}  {'✓ varies' if cv > 0.05 else '✗ near-constant'}")

    # Masking counterevidence stats
    mask_count = conn.execute("SELECT COUNT(*) FROM masking_counterevidence_record").fetchone()[0]
    mask_support = conn.execute(
        "SELECT verdict, COUNT(*) FROM masking_counterevidence_record GROUP BY verdict"
    ).fetchall()
    print(f"\n  Masking counterevidence: {mask_count} records")
    for verdict, cnt in mask_support:
        print(f"    {verdict}: {cnt}")

    # Anomaly stats
    anom_rows = conn.execute(
        "SELECT anomaly_type, COUNT(*) FROM external_anomaly_ledger GROUP BY anomaly_type"
    ).fetchall()
    print(f"  Anomaly ledger:")
    for atype, cnt in anom_rows:
        print(f"    {atype}: {cnt}")

    # ══════════════════════════════════════════════════════════════
    # Phase 2 [P]: Build circuit + run with signal entropy
    # ══════════════════════════════════════════════════════════════
    print(f"\n{'─' * 72}")
    print("  Phase 2 [P]: STDP circuit with signal entropy inputs")
    print(f"{'─' * 72}")

    circuit = build_signal_entropy_circuit(ext._signal_transform)
    print(f"  Circuit: {sum(len(l.neurons) for l in circuit.layers.values())} neurons, "
          f"{sum(len(l.bundles) for l in circuit.layers.values()) + len(circuit.inter_layer_bundles)} bundles")

    feature_names = ["sig_mean", "sig_std", "sig_peak_rate",
                     "sig_temporal_d", "sig_sync", "sig_range"]
    z_t_names = ["transition", "drift", "gamma_desync",
                 "xin_residual", "potential_disp", "churn", "magnitude"]

    circuit_z_t_by_stim = defaultdict(list)
    flat_z_t_by_stim = defaultdict(list)
    prev_activations = None
    prev_cells = None

    # Collect per-window signal entropy for injection
    sig_entropy_map = {}
    for row in sig_rows:
        sig_entropy_map[row[0]] = {
            "spectral_H": row[1],
            "fano_H": row[2],
            "synchrony_H": row[3],
            "gradient_H": row[4],
            "sparseness_H": row[5] if len(row) > 5 else 0.5,
            "autocorrelation_H": row[6] if len(row) > 6 else 0.5,
            "energy_H": row[7] if len(row) > 7 else 0.5,
        }

    # Also read masking survival rates per window
    mask_map = defaultdict(float)
    mask_rows = conn.execute(
        "SELECT hypothesis_id, verdict FROM masking_counterevidence_record"
    ).fetchall()
    for hyp_id, verdict in mask_rows:
        # Extract window k from hypothesis_id pattern
        mask_map[hyp_id] = 1.0 if verdict == "supports_confirmation" else -0.5

    for k in range(WINDOWS):
        cells = adapter.generate_cells(k)
        if not cells or prev_cells is None:
            prev_cells = cells
            continue

        sigs = [c.V_mean for c in cells]
        sf = ext._signal_transform.extract_signal_features(sigs)
        _, _, z_t_old = ext._signal_transform.transform(sigs)

        # Read REAL signal entropy from DB
        win_id = f"win_{adapter.adapter_name}_{k}"
        entropy_inputs = sig_entropy_map.get(win_id, {
            "spectral_H": 0.5, "fano_H": 0.5,
            "synchrony_H": 0.5, "gradient_H": 0.5,
            "sparseness_H": 0.5, "autocorrelation_H": 0.5,
            "energy_H": 0.5})

        # Compute circulation feedback amplification from DB history
        circ_gain = pe.compute_circulation_amplification(
            conn, run_id, k, win_id, lookback=5)

        # Apply gain to entropy inputs: amplify when entropy is falling
        # Cap amplified values to prevent flooding from high-range channels
        amplified_entropy = {}
        for key in entropy_inputs:
            g = circ_gain.get(key, 1.0)
            val = entropy_inputs[key] * g
            # Cap at 1.0 to prevent high-range features from flooding zones
            amplified_entropy[key] = min(1.0, val)

        # Step 1: Transport signal features → encoding
        signal_inputs = {feature_names[i]: sf[i] for i in range(len(sf))}
        circuit.transport(signal_inputs, "encoding")

        # Step 2: Transport AMPLIFIED signal entropy → signal_entropy layer
        circuit.transport(amplified_entropy, "signal_entropy")

        # Step 3: Propagate signal entropy → encoding via inter-layer bundles
        for bundle in circuit.inter_layer_bundles:
            src_layer = None
            for lid, l in circuit.layers.items():
                if bundle.source_neuron_ids[0] in l.neurons:
                    src_layer = l
                    break
            if src_layer is None:
                continue
            src_acts = [src_layer.neurons.get(sid, MetaNeuron("_","_")).activation
                        for sid in bundle.source_neuron_ids]
            tgt_acts = bundle.propagate(src_acts)
            for lid, l in circuit.layers.items():
                for j, tid in enumerate(bundle.target_neuron_ids):
                    if tid in l.neurons and j < len(tgt_acts):
                        l.neurons[tid].activation += tgt_acts[j]

        # Step 3.5: Contrastive gain modulation from higher-order features
        # Instead of directly injecting sparseness/autocorr/energy (which are
        # near-constant ~0.9 and flood zones), compute z-scores relative to
        # population mean and use as multiplicative gain on z_t neurons.
        # This extracts the DISCRIMINATIVE signal (scenes vs gratings).
        enc = circuit.layers["encoding"]
        ho_features = {
            "sparseness_H": ("churn", "drift"),      # scenes=0.85 < gratings=0.89
            "autocorrelation_H": ("transition", "drift"),  # scenes=0.43 > gratings=0.34
            "energy_H": ("magnitude", "potential_disp"),    # scenes=0.93 < gratings=0.97
        }
        # Population means from discovery diagnostic
        ho_means = {"sparseness_H": 0.88, "autocorrelation_H": 0.38, "energy_H": 0.95}
        ho_stds = {"sparseness_H": 0.05, "autocorrelation_H": 0.07, "energy_H": 0.03}
        for ho_name, (target_up, target_down) in ho_features.items():
            val = amplified_entropy.get(ho_name, ho_means.get(ho_name, 0.5))
            mean_v = ho_means[ho_name]
            std_v = max(ho_stds[ho_name], 1e-6)
            z = (val - mean_v) / std_v  # z-score: positive=above mean, negative=below
            # Clamp z to [-2, 2] to prevent extreme modulation
            z = max(-2.0, min(2.0, z))
            # Gain modulation: above-mean amplifies target_up, below amplifies target_down
            if target_up in enc.neurons:
                enc.neurons[target_up].activation *= (1.0 + 0.1 * z)
            if target_down in enc.neurons:
                enc.neurons[target_down].activation *= (1.0 - 0.1 * z)

        # Circulation gain amplification for starving neurons
        G = circ_gain.get("combined", 1.0)
        for nid in z_t_names:
            n = enc.neurons[nid]
            if n.calcium < n.target_rate * 0.5 and G > 1.01:
                n.activation *= G

        # Step 4: Lateral inhibition
        circuit._apply_lateral_inhibition(circuit.layers["encoding"])

        # Step 5: O/P/R/Xin
        circuit.observe()
        circuit.detect_circulations()
        if prev_activations:
            circuit.compute_xin(prev_activations)

        # Step 6: Learn (STDP + inter-layer)
        circuit.learn()
        for bundle in circuit.inter_layer_bundles:
            src_layer = None
            for lid, l in circuit.layers.items():
                if bundle.source_neuron_ids[0] in l.neurons:
                    src_layer = l
                    break
            if src_layer is None:
                continue
            pre_neurons = [src_layer.neurons[sid]
                           for sid in bundle.source_neuron_ids
                           if sid in src_layer.neurons]
            post_neurons = []
            for lid, l in circuit.layers.items():
                for tid in bundle.target_neuron_ids:
                    if tid in l.neurons:
                        post_neurons.append(l.neurons[tid])
            if pre_neurons and post_neurons:
                bundle.stdp_update(pre_neurons, post_neurons, 1.0)

        # Step 7: Maintain
        circuit.maintain()

        # Extract z_t
        enc = circuit.layers["encoding"]
        circuit_z_t = [enc.neurons[c].activation for c in z_t_names]

        si = k * 30
        if si < len(sub_ts):
            t_mid = sub_ts[si]
            for sn, es, ee in epochs:
                if es <= t_mid <= ee:
                    circuit_z_t_by_stim[sn].append(tuple(circuit_z_t))
                    break

        prev_activations = {nid: n.activation for nid, n in enc.neurons.items()}
        prev_cells = cells

    # ══════════════════════════════════════════════════════════════
    # Phase 3 [R]: Counter-evidence validation + discrimination
    # ══════════════════════════════════════════════════════════════
    print(f"\n{'─' * 72}")
    print("  Phase 3 [R]: Discrimination + counter-evidence analysis")
    print(f"{'─' * 72}")

    stim_names = sorted(circuit_z_t_by_stim.keys())
    print(f"  Stimuli: {stim_names}")
    print(f"  Samples: {', '.join(f'{s}={len(circuit_z_t_by_stim[s])}' for s in stim_names)}")

    def compute_mean(z_list):
        n = len(z_list)
        dim = len(z_list[0])
        return tuple(sum(z[d] for z in z_list) / n for d in range(dim))

    circuit_means = {}
    for s in stim_names:
        if circuit_z_t_by_stim.get(s):
            circuit_means[s] = compute_mean(circuit_z_t_by_stim[s])

    print(f"\n  Circuit discrimination (signal entropy driven):")
    circuit_sims = []
    for i, s1 in enumerate(stim_names):
        for s2 in stim_names[i+1:]:
            if s1 in circuit_means and s2 in circuit_means:
                sim = cosine_sim(circuit_means[s1], circuit_means[s2])
                circuit_sims.append(sim)
                print(f"    cos({s1[:18]:18s}, {s2[:18]:18s}) = {sim:.6f}")

    avg_circuit = sum(circuit_sims) / max(len(circuit_sims), 1)

    print(f"\n  Per-dimension z_t profiles:")
    for s in stim_names:
        if s in circuit_means:
            vals = "  ".join(f"{v:.4f}" for v in circuit_means[s])
            print(f"    {s[:22]:22s}: [{vals}]")

    # Signal entropy bundle evolution
    print(f"\n  Signal entropy → z_t bundle evolution:")
    for b in circuit.inter_layer_bundles:
        if b.bundle_id.startswith("sigH_"):
            cond = getattr(b, '_conductance_history', 0.0)
            print(f"    {b.bundle_id:35s}: strength={b.bundle_strength:.4f}  "
                  f"conductance={cond:.4f}  inertia={b.bundle_inertia:.4f}")

    # Circulation amplification stats
    try:
        amp_rows = conn.execute(
            "SELECT gain_combined, entropy_slope_spectral, entropy_slope_fano "
            "FROM v40_circulation_amplification_ledger "
            "WHERE run_id=? ORDER BY CAST(stage_k_id AS INTEGER)",
            (run_id,)).fetchall()
        if amp_rows:
            gains_all = [r[0] for r in amp_rows]
            amplified = sum(1 for g in gains_all if g > 1.01)
            print(f"\n  Circulation amplification (from entropy ledger):")
            print(f"    Windows amplified: {amplified}/{len(gains_all)}")
            print(f"    Gain range: [{min(gains_all):.3f}, {max(gains_all):.3f}]  "
                  f"mean={sum(gains_all)/len(gains_all):.3f}")
    except Exception:
        pass

    # Homeostatic state: structural differentiation
    print(f"\n  Homeostatic differentiation (encoding layer):")
    for nid in z_t_names:
        n = circuit.layers["encoding"].neurons[nid]
        print(f"    {nid:18s}: threshold={n.threshold:.6f}  "
              f"calcium={n.calcium:.6f}  pre_trace={n.pre_trace:.4f}")

    # R-chain: which z_t dims have structural support?
    print(f"\n  R-chain: structural support per z_t dimension:")
    for nid in z_t_names:
        n = circuit.layers["encoding"].neurons[nid]
        # Dimension has support if: threshold adapted away from initial AND calcium > 0
        calcium_active = n.calcium > 0.001
        threshold_adapted = abs(n.threshold - 0.005) > 0.0001
        has_bundle_support = any(
            nid in b.target_neuron_ids and b.bundle_strength > 0.05
            for b in circuit.layers["encoding"].bundles + circuit.inter_layer_bundles
        )
        status = "✅" if (calcium_active or threshold_adapted) else "⚠️ weak"
        print(f"    {nid:18s}: ca={calcium_active}  thr_adapt={threshold_adapted}  "
              f"bundle={has_bundle_support}  → {status}")

    m = circuit.get_metrics()
    print(f"\n  Circuit: alive={m['alive_neurons']}/{m['total_neurons']}  "
          f"P={'✓' if m['p_circulation'] else '✗'}  "
          f"R={'✓' if m['r_circulation'] else '✗'}  "
          f"T={m['temperature']:.4f}  fruits={m['dormant_fruits']}")

    # Circulation measure (probability integral over all paths)
    circ_mu = getattr(circuit, '_circulation_measure', 0.0)
    all_cycles = getattr(circuit, '_all_cycle_measures', [])
    ghost_count = sum(len(getattr(l, '_ghost_bundles', []))
                      for l in circuit.layers.values())
    print(f"\n  Circulation measure μ(G) = {circ_mu:.6f}")
    print(f"    Active cycles: {len(all_cycles)}")
    if all_cycles:
        print(f"    P fraction: {all_cycles[0]['fraction']:.4f}")
        if len(all_cycles) > 1:
            print(f"    R fraction: {all_cycles[1]['fraction']:.4f}")
            print(f"    Secondary+: {sum(c['fraction'] for c in all_cycles[2:]):.4f}")
    print(f"    Ghost bundles: {ghost_count}")

    # ══════════════════════════════════════════════════════════════
    # Phase 4 [Xin]: Verdict + structural tension
    # ══════════════════════════════════════════════════════════════
    print(f"\n{'=' * 72}")
    print("  Phase 4 [Xin]: VERDICT + remaining tension")
    print(f"{'=' * 72}")

    flat_avg = 0.999460  # known baseline from flat W_signal
    improved = avg_circuit < flat_avg
    print(f"  Flat baseline cosine: {flat_avg:.6f}")
    print(f"  Circuit avg cosine:   {avg_circuit:.6f}")
    print(f"  Improvement:          {flat_avg - avg_circuit:.6f}")
    print(f"  Discrimination:       {'✅ YES' if improved else '❌ NO'}")

    thresholds = [circuit.layers["encoding"].neurons[n].threshold for n in z_t_names]
    thr_std = math.sqrt(sum((t - sum(thresholds)/len(thresholds))**2 for t in thresholds)/len(thresholds))
    print(f"  Threshold diversity:  std={thr_std:.6f} {'✅' if thr_std > 0.0005 else '❌'}")

    # Count non-zero dimensions per stimulus
    active_dims = {}
    for s in stim_names:
        if s in circuit_means:
            active = sum(1 for v in circuit_means[s] if abs(v) > 0.001)
            active_dims[s] = active
    print(f"  Active dimensions:    {active_dims}")

    # Remaining Xin tension
    xin_total = sum(abs(v) for v in circuit._xin_tensions.values())
    print(f"  Xin total tension:    {xin_total:.4f}")
    print(f"  Activated fruits:     {len(circuit._activated_fruits)}")

    report = {
        "flat_avg_cosine": flat_avg,
        "circuit_avg_cosine": avg_circuit,
        "improvement": flat_avg - avg_circuit,
        "improved": improved,
        "threshold_diversity": thr_std,
        "active_dims": active_dims,
        "xin_tension": xin_total,
        "circuit_metrics": m,
        "signal_entropy_rows": len(sig_rows),
        "masking_records": mask_count,
    }
    rp = str(BASE / "db" / "v40_integrated_report.json")
    with open(rp, "w") as f_out:
        json.dump(report, f_out, indent=2, default=str)
    print(f"\n  DB:     {DB_PATH}")
    print(f"  Report: {rp}")
    print("=" * 72)

    conn.close()


if __name__ == "__main__":
    main()
===
#!/usr/bin/env python3
"""v40 Integrated Circuit — Full Pipeline + Signal Entropy + STDP + R-chain.

Holistic integration:
  1. Run full pipeline → writes ALL ledgers (entropy, anomaly, masking, transport)
  2. Write NEW v40_signal_entropy_ledger (spectral_H, fano, synchrony, gradient)
     — these actually vary across stimulus types unlike pipeline-structural entropy
  3. Read signal entropy + masking counterevidence from DB
  4. Feed into circuit: signal entropy as structural input neurons,
     masking survival rate as modulatory gain on z_t neurons
  5. STDP + homeostasis adapts structure based on measured quantities
  6. Compare discrimination with R-chain validation

The whole loop mirrors T/O/P/R/Xin:
  T = pipeline transport → DB
  O = observe signal entropy variation
  P = primary discrimination path (STDP circuit)
  R = counter-evidence from masking layer → refute weak dimensions
  Xin = residual tension → structural adjustment
"""
import sys, os, math, json, sqlite3
from pathlib import Path
from collections import defaultdict

BASE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE / "src"))
sys.path.insert(0, str(BASE))
sys.path.insert(0, str(BASE / "engines"))

from allen_brain_adapter import AllenBrainAdapter
from motion_recognition_engine import FeatureExtractor, BayesianMotionRecognizer
from hebbian_circuit import (HebbianCircuit, CircuitLayer, MetaNeuron,
                             MetaSynapticBundle, build_circuit_from_signal_transform)
import pipeline_engine as pe
import h5py

DB_PATH = str(BASE / "db" / "v40_integrated.db")


def build_signal_entropy_circuit(signal_transform) -> HebbianCircuit:
    """Build circuit with sensitivity zone differentiation.

    Architecture — differentiated sensitivity zones:
    ────────────────────────────────────────────────────────────────
    Each entropy channel gets its OWN receptive field (zone).
    All zones are simultaneously activated as the circulation baseline.
    This prevents any single dominant dimension from killing
    signal-source information from other channels.

    signal_entropy_layer: 4 neurons (spectral_H, fano_H, synchrony_H, gradient_H)
          │
          ├─→ zone_spectral (2 intermediate neurons) ─→ z_t targets
          ├─→ zone_fano (2 intermediate neurons) ─→ z_t targets
          ├─→ zone_synchrony (2 intermediate neurons) ─→ z_t targets
          └─→ zone_gradient (2 intermediate neurons) ─→ z_t targets
          │
    encoding_layer: 6 signal features → 7 z_t costs
          │
    column_layer: consolidation

    Within each zone:
      - Dedicated intermediate neurons transform entropy into
        zone-specific activation patterns
      - Each zone has its OWN feedback loop (closed circulation per zone)
      - STDP operates per-zone, allowing independent weight adaptation

    Cross-zone integration:
      - All zones project to shared z_t targets
      - Divisive normalization operates across z_t, not within zones
      - This creates proportional contribution, not winner-take-all

    The resulting μ(G) contains:
      - Per-zone circulations (local, always active at baseline)
      - Cross-zone circulations (global, emerge from STDP convergence)
      - The genuine P is the circulation that persists when any
        single zone is masked (validated by R-chain counterevidence)
    ────────────────────────────────────────────────────────────────
    """
    circuit = build_circuit_from_signal_transform(signal_transform)

    # Signal entropy input layer
    entropy_layer = CircuitLayer(layer_id="signal_entropy")
    entropy_names = ["spectral_H", "fano_H", "synchrony_H", "gradient_H",
                     "sparseness_H", "autocorrelation_H", "energy_H"]
    for name in entropy_names:
        n = entropy_layer.add_neuron(name)
        n.target_rate = 0.2
        n.threshold = 0.001
        n.energy = 1000.0  # input neurons: externally driven, should never die
    circuit.layers["signal_entropy"] = entropy_layer

    z_t_names = ["transition", "drift", "gamma_desync",
                 "xin_residual", "potential_disp", "churn", "magnitude"]

    # ── Create sensitivity zones ──
    # Each zone: entropy channel → 2 intermediate neurons → z_t targets
    # The intermediates allow per-zone STDP to learn independent patterns

    zone_specs = {
        "spectral": {
            "source": ["spectral_H"],
            "intermediates": ["zone_spec_mag", "zone_spec_pot"],
            "targets": ["magnitude", "potential_disp"],
        },
        "fano": {
            "source": ["fano_H"],
            "intermediates": ["zone_fano_churn", "zone_fano_drift"],
            "targets": ["churn", "drift"],
        },
        "synchrony": {
            "source": ["synchrony_H"],
            "intermediates": ["zone_sync_gamma", "zone_sync_trans"],
            "targets": ["gamma_desync", "transition"],
        },
        "gradient": {
            "source": ["gradient_H"],
            "intermediates": ["zone_grad_xin", "zone_grad_trans"],
            "targets": ["xin_residual", "transition"],
        },
    }

    # Higher-order features: parallel bundles to existing zone intermediates
    # These AUGMENT the existing zones without adding neurons or zones
    higher_order_pairs = [
        # (source_H, target_zone_intermediates, name)
        ("energy_H",          ["zone_spec_mag", "zone_spec_pot"], "energy_to_spectral"),
        ("sparseness_H",      ["zone_fano_churn", "zone_fano_drift"], "sparseness_to_fano"),
        ("autocorrelation_H", ["zone_grad_xin", "zone_grad_trans"], "autocorr_to_gradient"),
    ]

    # v40.6: Zone-differentiated target_rates based on entropy channel CV
    zone_target_rates = {
        "spectral": 0.05,    # cv=24.6% → moderate variability → moderate target
        "fano": 0.02,        # cv=56.2% → high variability → low target (sparse responder)
        "synchrony": 0.06,   # cv=29.8% → moderate → slightly higher
        "gradient": 0.08,    # cv=19.3% → low variability → high target (tonic responder)
    }

    # v40.6: Per-dimension z_t target_rates based on zone coverage frequency
    z_t_target_rates = {
        "transition": 0.04,     # covered by synchrony + gradient
        "drift": 0.03,          # covered by fano alone
        "gamma_desync": 0.04,   # covered by synchrony alone
        "xin_residual": 0.03,   # covered by gradient alone
        "potential_disp": 0.02, # covered by spectral alone
        "churn": 0.03,          # covered by fano alone
        "magnitude": 0.02,      # covered by spectral alone
    }

    # Apply z_t target_rates to z_t neurons already in encoding layer
    enc_layer = circuit.layers["encoding"]
    for zt_name, zt_rate in z_t_target_rates.items():
        if zt_name in enc_layer.neurons:
            enc_layer.neurons[zt_name].target_rate = zt_rate

    for zone_name, spec in zone_specs.items():
        # Add intermediate neurons to encoding layer
        enc = circuit.layers["encoding"]
        zt_rate = zone_target_rates.get(zone_name, 0.05)
        for iname in spec["intermediates"]:
            n = enc.add_neuron(iname)
            n.target_rate = zt_rate  # v40.6: zone-differentiated target
            n.threshold = 0.0001    # very low: always respond to entropy
            n.energy = 1000.0       # modulatory neurons should never die

        sources = spec["source"]  # list of entropy channel names

        # Bundle 1: entropy sources → intermediate neurons
        b_in = MetaSynapticBundle(
            bundle_id=f"sigH_{zone_name}_to_zone",
            source_neuron_ids=sources,
            target_neuron_ids=spec["intermediates"],
            bundle_inertia=0.5, learning_rule="stdp")
        b_in.init_weights()
        # Higher initial weights for zone input — entropy should pass through
        for i in range(len(b_in.weights)):
            for j in range(len(b_in.weights[i])):
                b_in.weights[i][j] = 0.3
        circuit.inter_layer_bundles.append(b_in)

        # Bundle 2: intermediate neurons → z_t targets (within encoding)
        b_out = enc.add_bundle(
            source_ids=spec["intermediates"],
            target_ids=spec["targets"])
        b_out.bundle_id = f"zone_{zone_name}_to_zt"
        b_out.learning_rule = "stdp"
        # Initial weights: moderate, to be shaped by STDP
        for i in range(len(b_out.weights)):
            for j in range(len(b_out.weights[i])):
                b_out.weights[i][j] = 0.2

        # Bundle 3: z_t targets → entropy sources (feedback loop)
        # This closes the per-zone circulation, making each zone
        # a self-contained T/O/P/R/Xin mini-loop
        b_fb = MetaSynapticBundle(
            bundle_id=f"zone_{zone_name}_feedback",
            source_neuron_ids=spec["targets"],
            target_neuron_ids=sources,
            bundle_inertia=0.8, learning_rule="oja")
        b_fb.init_weights()
        for i in range(len(b_fb.weights)):
            for j in range(len(b_fb.weights[i])):
                b_fb.weights[i][j] = 0.05  # weak feedback initially
        circuit.inter_layer_bundles.append(b_fb)

    # Higher-order features (sparseness, autocorrelation, energy) are applied
    # as contrastive gain modulation in Step 3.5 of the circuit loop, not as
    # parallel bundles. This prevents range-mismatch flooding.

    return circuit


def cosine_sim(a, b):
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a)) + 1e-12
    nb = math.sqrt(sum(x * x for x in b)) + 1e-12
    return dot / (na * nb)


def main():
    print("=" * 72)
    print("v40 INTEGRATED: Signal Entropy + STDP + R-chain Validation")
    print("=" * 72)

    # ══════════════════════════════════════════════════════════════
    # Phase 1: T — Full pipeline → all ledgers
    # ══════════════════════════════════════════════════════════════
    print(f"\n{'─' * 72}")
    print("  Phase 1 [T]: Pipeline transport → all ledgers")
    print(f"{'─' * 72}")

    if os.path.exists(DB_PATH):
        os.remove(DB_PATH)
    conn = sqlite3.connect(DB_PATH)
    pe.apply_migrations(conn)
    conn.commit()

    adapter = AllenBrainAdapter(split_role="all")
    run_id = "v40_integrated_001"
    pe.register_adapter(conn, run_id, adapter)

    ext = FeatureExtractor()
    rec = BayesianMotionRecognizer(prior_var=1.0)
    prev_cells = None
    WINDOWS = adapter.total_windows

    # Load stimulus epochs
    nwb_path = str(BASE / "data/allen_brain/ophys_experiment_data/500964514.nwb")
    f = h5py.File(nwb_path, "r")
    pres = f["stimulus"]["presentation"]
    epochs = []
    for sn in pres.keys():
        ds = pres[sn]
        if "timestamps" in ds:
            ts = ds["timestamps"][:]
            if len(ts) >= 2:
                clean = sn.replace("_stimulus", "")
                block_start = ts[0]
                prev_t = ts[0]
                for i in range(1, len(ts)):
                    if ts[i] - prev_t > 30:
                        epochs.append((clean, float(block_start), float(prev_t)))
                        block_start = ts[i]
                    prev_t = ts[i]
                epochs.append((clean, float(block_start), float(prev_t)))
    # Sort by DURATION ascending (narrowest first) for proper matching
    # static_gratings spans [50,3803] but movie is [2362,2662] — narrowest wins
    epochs.sort(key=lambda x: x[2] - x[1])
    fl_ts = f["processing"]["brain_observatory_pipeline"]["DfOverF"]["imaging_plane_1"]["timestamps"][:]
    sub_ts = fl_ts[::38][:3003]
    f.close()

    for k in range(WINDOWS):
        cells = adapter.generate_cells(k)
        if not cells:
            continue

        env = adapter.make_envelope(k)
        env_id = pe.write_envelope(conn, run_id, env)
        pw_id = pe.write_process_window(conn, run_id, adapter, k, env_id,
                                         len(cells), ["ingest", "transport"])
        uid_map = pe.write_cells(conn, run_id, adapter, k, cells)

        if prev_cells is not None:
            pe.write_transport(conn, run_id, adapter, k, prev_cells, cells)

        hyps = pe.write_hypotheses(conn, run_id, adapter, k, cells)
        xi_id = pe.write_xi(conn, run_id, adapter, k, hyps, cells[:5])

        if prev_cells is not None:
            disps = {}
            for i in range(min(len(prev_cells), len(cells))):
                dx = cells[i].x - prev_cells[i].x
                dy = cells[i].y - prev_cells[i].y
                disps[i] = math.sqrt(dx*dx + dy*dy)
            feats = ext.extract(
                {i: (c.x, c.y) for i, c in enumerate(prev_cells)},
                {i: (c.x, c.y) for i, c in enumerate(cells)},
                disps, signal_values=[c.V_mean for c in cells])
            pred, _, _ = rec.classify(feats)
            rec.learn(feats, pred)

        # Write ALL ledgers
        pe.write_external_ledgers(conn, run_id, adapter, k, env, cells)
        # Write v40 SIGNAL entropy (the key new ledger)
        pe.write_signal_entropy_ledger(conn, run_id, adapter, k, cells)

        prev_cells = cells
        if k % 20 == 0:
            conn.commit()

    conn.commit()
    ext._signal_transform.freeze()

    # ══════════════════════════════════════════════════════════════
    # Phase 1.5 [O]: Observe signal entropy variation
    # ══════════════════════════════════════════════════════════════
    print(f"\n{'─' * 72}")
    print("  Phase 1.5 [O]: Observe signal entropy variation")
    print(f"{'─' * 72}")

    sig_rows = conn.execute(
        "SELECT window_id, spectral_entropy, fano_factor, synchrony_entropy, gradient_entropy, "
        "population_sparseness, temporal_autocorrelation, energy_concentration "
        "FROM v40_signal_entropy_ledger ORDER BY CAST(stage_k_id AS INTEGER)"
    ).fetchall()
    print(f"  Signal entropy rows: {len(sig_rows)} (7-channel)")
    for col, name in [(1, "spectral_H"), (2, "fano_H"), (3, "synchrony_H"), (4, "gradient_H")]:
        vals = [r[col] for r in sig_rows]
        mean_v = sum(vals)/len(vals)
        std_v = math.sqrt(sum((v-mean_v)**2 for v in vals)/len(vals))
        print(f"    {name:15s}: [{min(vals):.4f}, {max(vals):.4f}]  "
              f"mean={mean_v:.4f}  std={std_v:.4f}  cv={std_v/max(abs(mean_v),1e-10):.2%}")

    # Compare: old pipeline entropy vs new signal entropy coefficient of variation
    old_rows = conn.execute(
        "SELECT transport_entropy, candidate_fragment_entropy, origin_support_entropy, "
        "residual_accumulation_entropy FROM external_entropy_ledger"
    ).fetchall()
    print(f"\n  Pipeline entropy (old) — coefficient of variation:")
    for col, name in [(0, "transport_H"), (1, "candidate_H"), (2, "origin_H"), (3, "residual_H")]:
        vals = [r[col] for r in old_rows]
        mean_v = sum(vals)/len(vals)
        std_v = math.sqrt(sum((v-mean_v)**2 for v in vals)/len(vals))
        cv = std_v/max(abs(mean_v), 1e-10)
        print(f"    {name:15s}: cv={cv:.2%}  {'✓ varies' if cv > 0.05 else '✗ near-constant'}")

    # Masking counterevidence stats
    mask_count = conn.execute("SELECT COUNT(*) FROM masking_counterevidence_record").fetchone()[0]
    mask_support = conn.execute(
        "SELECT verdict, COUNT(*) FROM masking_counterevidence_record GROUP BY verdict"
    ).fetchall()
    print(f"\n  Masking counterevidence: {mask_count} records")
    for verdict, cnt in mask_support:
        print(f"    {verdict}: {cnt}")

    # Anomaly stats
    anom_rows = conn.execute(
        "SELECT anomaly_type, COUNT(*) FROM external_anomaly_ledger GROUP BY anomaly_type"
    ).fetchall()
    print(f"  Anomaly ledger:")
    for atype, cnt in anom_rows:
        print(f"    {atype}: {cnt}")

    # ══════════════════════════════════════════════════════════════
    # Phase 1.6 [O]: Dynamic contrastive gain statistics from DB
    # ══════════════════════════════════════════════════════════════
    print(f"\n{'─' * 72}")
    print("  Phase 1.6 [O]: Dynamic contrastive gain statistics")
    print(f"{'─' * 72}")

    ho_channels = ["population_sparseness", "temporal_autocorrelation", "energy_concentration"]
    ho_stats = {}
    for col_name in ho_channels:
        vals = conn.execute(
            f"SELECT {col_name} FROM v40_signal_entropy_ledger WHERE run_id=?",
            (run_id,)
        ).fetchall()
        vals = [v[0] for v in vals if v[0] is not None]
        if vals:
            mu = sum(vals) / len(vals)
            std = math.sqrt(sum((v - mu)**2 for v in vals) / len(vals))
        else:
            mu, std = 0.5, 0.1
        # Map column name to ho_key
        ho_key_map = {
            "population_sparseness": "sparseness_H",
            "temporal_autocorrelation": "autocorrelation_H",
            "energy_concentration": "energy_H",
        }
        ho_key = ho_key_map[col_name]
        ho_stats[ho_key] = {"mean": mu, "std": max(std, 1e-6)}
        print(f"    {ho_key:22s}: μ={mu:.6f}  σ={std:.6f}")

    # ══════════════════════════════════════════════════════════════
    # Phase 1.7 [O]: Temporal resolution audit + bootstrap augmentation
    # ══════════════════════════════════════════════════════════════
    print(f"\n{'─' * 72}")
    print("  Phase 1.7 [O]: Temporal resolution audit")
    print(f"{'─' * 72}")

    # Identify stimulus for each window via epoch matching
    stim_window_counts = defaultdict(int)
    stim_window_ids = defaultdict(list)
    for row in sig_rows:
        win_id_check = row[0]
        # Extract k from window_id pattern: win_<adapter>_<k>
        parts = win_id_check.rsplit("_", 1)
        if len(parts) == 2 and parts[1].isdigit():
            si = int(parts[1]) * 30
            if si < len(sub_ts):
                t_mid = sub_ts[si]
                for sn, es, ee in epochs:
                    if es <= t_mid <= ee:
                        stim_window_counts[sn] += 1
                        stim_window_ids[sn].append(win_id_check)
                        break

    MIN_WINDOWS = 20
    for stim, count in sorted(stim_window_counts.items()):
        if count < MIN_WINDOWS:
            print(f"  ⚠ {stim}: {count} windows < {MIN_WINDOWS} → augmenting")
            aug_rows = pe.compute_temporal_resolution_augmentation(
                conn, run_id, stim, stim_window_ids[stim],
                target_windows=MIN_WINDOWS)
            print(f"    → generated {aug_rows} bootstrap windows")
            # Refresh sig_rows after augmentation
            sig_rows = conn.execute(
                "SELECT window_id, spectral_entropy, fano_factor, synchrony_entropy, gradient_entropy, "
                "population_sparseness, temporal_autocorrelation, energy_concentration "
                "FROM v40_signal_entropy_ledger WHERE run_id=? ORDER BY CAST(stage_k_id AS INTEGER)",
                (run_id,)
            ).fetchall()
        else:
            print(f"  ✓ {stim}: {count} windows ≥ {MIN_WINDOWS}")

    # Rebuild sig_entropy_map with augmented data
    sig_entropy_map = {}
    for row in sig_rows:
        sig_entropy_map[row[0]] = {
            "spectral_H": row[1],
            "fano_H": row[2],
            "synchrony_H": row[3],
            "gradient_H": row[4],
            "sparseness_H": row[5] if len(row) > 5 else 0.5,
            "autocorrelation_H": row[6] if len(row) > 6 else 0.5,
            "energy_H": row[7] if len(row) > 7 else 0.5,
        }

    # ══════════════════════════════════════════════════════════════
    # Phase 2 [P]: Build circuit + run with signal entropy
    # ══════════════════════════════════════════════════════════════
    print(f"\n{'─' * 72}")
    print("  Phase 2 [P]: STDP circuit with signal entropy inputs")
    print(f"{'─' * 72}")

    circuit = build_signal_entropy_circuit(ext._signal_transform)
    print(f"  Circuit: {sum(len(l.neurons) for l in circuit.layers.values())} neurons, "
          f"{sum(len(l.bundles) for l in circuit.layers.values()) + len(circuit.inter_layer_bundles)} bundles")

    feature_names = ["sig_mean", "sig_std", "sig_peak_rate",
                     "sig_temporal_d", "sig_sync", "sig_range"]
    z_t_names = ["transition", "drift", "gamma_desync",
                 "xin_residual", "potential_disp", "churn", "magnitude"]

    circuit_z_t_by_stim = defaultdict(list)
    flat_z_t_by_stim = defaultdict(list)
    prev_activations = None
    prev_cells = None

    # Collect per-window signal entropy for injection
    sig_entropy_map = {}
    for row in sig_rows:
        sig_entropy_map[row[0]] = {
            "spectral_H": row[1],
            "fano_H": row[2],
            "synchrony_H": row[3],
            "gradient_H": row[4],
            "sparseness_H": row[5] if len(row) > 5 else 0.5,
            "autocorrelation_H": row[6] if len(row) > 6 else 0.5,
            "energy_H": row[7] if len(row) > 7 else 0.5,
        }

    # Also read masking survival rates per window
    mask_map = defaultdict(float)
    mask_rows = conn.execute(
        "SELECT hypothesis_id, verdict FROM masking_counterevidence_record"
    ).fetchall()
    for hyp_id, verdict in mask_rows:
        # Extract window k from hypothesis_id pattern
        mask_map[hyp_id] = 1.0 if verdict == "supports_confirmation" else -0.5

    for k in range(WINDOWS):
        cells = adapter.generate_cells(k)
        if not cells or prev_cells is None:
            prev_cells = cells
            continue

        sigs = [c.V_mean for c in cells]
        sf = ext._signal_transform.extract_signal_features(sigs)
        _, _, z_t_old = ext._signal_transform.transform(sigs)

        # Read REAL signal entropy from DB
        win_id = f"win_{adapter.adapter_name}_{k}"
        entropy_inputs = sig_entropy_map.get(win_id, {
            "spectral_H": 0.5, "fano_H": 0.5,
            "synchrony_H": 0.5, "gradient_H": 0.5,
            "sparseness_H": 0.5, "autocorrelation_H": 0.5,
            "energy_H": 0.5})

        # Compute circulation feedback amplification from DB history
        circ_gain = pe.compute_circulation_amplification(
            conn, run_id, k, win_id, lookback=5)

        # Apply gain to entropy inputs: amplify when entropy is falling
        # Cap amplified values to prevent flooding from high-range channels
        amplified_entropy = {}
        for key in entropy_inputs:
            g = circ_gain.get(key, 1.0)
            val = entropy_inputs[key] * g
            # Cap at 1.0 to prevent high-range features from flooding zones
            amplified_entropy[key] = min(1.0, val)

        # Step 1: Transport signal features → encoding
        signal_inputs = {feature_names[i]: sf[i] for i in range(len(sf))}
        circuit.transport(signal_inputs, "encoding")

        # Step 2: Transport AMPLIFIED signal entropy → signal_entropy layer
        circuit.transport(amplified_entropy, "signal_entropy")

        # Step 3: Propagate signal entropy → encoding via inter-layer bundles
        for bundle in circuit.inter_layer_bundles:
            src_layer = None
            for lid, l in circuit.layers.items():
                if bundle.source_neuron_ids[0] in l.neurons:
                    src_layer = l
                    break
            if src_layer is None:
                continue
            src_acts = [src_layer.neurons.get(sid, MetaNeuron("_","_")).activation
                        for sid in bundle.source_neuron_ids]
            tgt_acts = bundle.propagate(src_acts)
            for lid, l in circuit.layers.items():
                for j, tid in enumerate(bundle.target_neuron_ids):
                    if tid in l.neurons and j < len(tgt_acts):
                        l.neurons[tid].activation += tgt_acts[j]

        # Step 3.5: Contrastive gain modulation from higher-order features
        # Instead of directly injecting sparseness/autocorr/energy (which are
        # near-constant ~0.9 and flood zones), compute z-scores relative to
        # population mean and use as multiplicative gain on z_t neurons.
        # This extracts the DISCRIMINATIVE signal (scenes vs gratings).
        enc = circuit.layers["encoding"]
        ho_features = {
            "sparseness_H": ("churn", "drift"),      # scenes=0.85 < gratings=0.89
            "autocorrelation_H": ("transition", "drift"),  # scenes=0.43 > gratings=0.34
            "energy_H": ("magnitude", "potential_disp"),    # scenes=0.93 < gratings=0.97
        }
        # v40.6: Population means from DB (computed in Phase 1.6), not hardcoded
        for ho_name, (target_up, target_down) in ho_features.items():
            val = amplified_entropy.get(ho_name, 0.5)
            stats = ho_stats.get(ho_name, {"mean": 0.5, "std": 0.1})
            mean_v = stats["mean"]
            std_v = stats["std"]
            z = (val - mean_v) / std_v  # z-score: positive=above mean, negative=below
            # Clamp z to [-2, 2] to prevent extreme modulation
            z = max(-2.0, min(2.0, z))
            # Gain modulation: above-mean amplifies target_up, below amplifies target_down
            if target_up in enc.neurons:
                enc.neurons[target_up].activation *= (1.0 + 0.1 * z)
            if target_down in enc.neurons:
                enc.neurons[target_down].activation *= (1.0 - 0.1 * z)

        # Circulation gain amplification for starving neurons
        G = circ_gain.get("combined", 1.0)
        for nid in z_t_names:
            n = enc.neurons[nid]
            if n.calcium < n.target_rate * 0.5 and G > 1.01:
                n.activation *= G

        # Step 4: Lateral inhibition
        circuit._apply_lateral_inhibition(circuit.layers["encoding"])

        # Step 5: O/P/R/Xin
        circuit.observe()
        circuit.detect_circulations()
        if prev_activations:
            circuit.compute_xin(prev_activations)

        # Step 6: Learn (STDP + inter-layer)
        circuit.learn()
        for bundle in circuit.inter_layer_bundles:
            src_layer = None
            for lid, l in circuit.layers.items():
                if bundle.source_neuron_ids[0] in l.neurons:
                    src_layer = l
                    break
            if src_layer is None:
                continue
            pre_neurons = [src_layer.neurons[sid]
                           for sid in bundle.source_neuron_ids
                           if sid in src_layer.neurons]
            post_neurons = []
            for lid, l in circuit.layers.items():
                for tid in bundle.target_neuron_ids:
                    if tid in l.neurons:
                        post_neurons.append(l.neurons[tid])
            if pre_neurons and post_neurons:
                bundle.stdp_update(pre_neurons, post_neurons, 1.0)

        # Step 7: Maintain
        circuit.maintain()

        # Extract z_t
        enc = circuit.layers["encoding"]
        circuit_z_t = [enc.neurons[c].activation for c in z_t_names]

        si = k * 30
        if si < len(sub_ts):
            t_mid = sub_ts[si]
            for sn, es, ee in epochs:
                if es <= t_mid <= ee:
                    circuit_z_t_by_stim[sn].append(tuple(circuit_z_t))
                    break

        prev_activations = {nid: n.activation for nid, n in enc.neurons.items()}
        prev_cells = cells

    # ── B.3: Inject synthetic bootstrap windows into circuit ──
    # For starved stimuli, run additional circuit ticks with synthetic entropy
    # STDP weight is attenuated: real_windows / total_windows
    syn_windows = [row for row in sig_rows
                   if row[0].startswith("syn_")]
    if syn_windows:
        print(f"\n  Injecting {len(syn_windows)} synthetic windows into circuit...")
        for syn_row in syn_windows:
            syn_win_id = syn_row[0]
            entropy_inputs = {
                "spectral_H": syn_row[1],
                "fano_H": syn_row[2],
                "synchrony_H": syn_row[3],
                "gradient_H": syn_row[4],
                "sparseness_H": syn_row[5] if len(syn_row) > 5 else 0.5,
                "autocorrelation_H": syn_row[6] if len(syn_row) > 6 else 0.5,
                "energy_H": syn_row[7] if len(syn_row) > 7 else 0.5,
            }

            # Transport synthetic entropy → signal_entropy layer → zone intermediates
            circuit.transport(entropy_inputs, "signal_entropy")

            # Forward-propagate inter-layer bundles (signal_entropy → encoding)
            for bundle in circuit.inter_layer_bundles:
                src_layer = None
                for lid, l in circuit.layers.items():
                    if bundle.source_neuron_ids[0] in l.neurons:
                        src_layer = l
                        break
                if src_layer is None:
                    continue
                src_acts = [src_layer.neurons.get(sid, MetaNeuron("_","_")).activation
                            for sid in bundle.source_neuron_ids]
                tgt_acts = bundle.propagate(src_acts)
                for lid, l in circuit.layers.items():
                    for j, tid in enumerate(bundle.target_neuron_ids):
                        if tid in l.neurons and j < len(tgt_acts):
                            l.neurons[tid].activation += tgt_acts[j]

            # v40.6: Also inject z_t from entropy directly, proportional to
            # how much each z_t dimension is informative for this stimulus.
            # Different stimuli have different entropy profiles → different z_t patterns
            enc = circuit.layers["encoding"]
            entropy_to_zt_map = {
                "transition": ("synchrony_H", "gradient_H"),   # temporal structure
                "drift": ("fano_H", "sparseness_H"),          # variability metrics
                "gamma_desync": ("synchrony_H",),              # synchronization
                "xin_residual": ("gradient_H", "energy_H"),    # spatial gradient
                "potential_disp": ("spectral_H",),             # spectral content
                "churn": ("fano_H", "autocorrelation_H"),      # temporal dynamics
                "magnitude": ("energy_H", "spectral_H"),       # signal strength
            }
            for zt_name, entropy_keys in entropy_to_zt_map.items():
                if zt_name in enc.neurons:
                    # Use z-scored entropy: how much this stimulus DEVIATES from population
                    zt_val = 0.0
                    for k in entropy_keys:
                        raw = entropy_inputs.get(k, 0.5)
                        stats = ho_stats.get(k, None)
                        if stats:
                            z = (raw - stats["mean"]) / max(stats["std"], 1e-6)
                        else:
                            z = 0.0
                        zt_val += z
                    zt_val /= len(entropy_keys)
                    # Scale: z-scored values → small activation
                    # Positive z = above population mean → more activation
                    zt_val = max(0.0, zt_val * 0.01)  # only positive deviations
                    if zt_val > 0:
                        enc.neurons[zt_name].activate(zt_val)

            # Contrastive gain modulation for synthetic windows (same as Step 3.5)
            enc = circuit.layers["encoding"]
            ho_features = {
                "sparseness_H": ("churn", "drift"),
                "autocorrelation_H": ("transition", "drift"),
                "energy_H": ("magnitude", "potential_disp"),
            }
            for ho_name, (target_up, target_down) in ho_features.items():
                val = entropy_inputs.get(ho_name, 0.5)
                stats = ho_stats.get(ho_name, {"mean": 0.5, "std": 0.1})
                mean_v = stats["mean"]
                std_v = stats["std"]
                z = (val - mean_v) / std_v
                z = max(-2.0, min(2.0, z))
                if target_up in enc.neurons:
                    enc.neurons[target_up].activation *= (1.0 + 0.1 * z)
                if target_down in enc.neurons:
                    enc.neurons[target_down].activation *= (1.0 - 0.1 * z)

            # Lateral inhibition
            circuit._apply_lateral_inhibition(circuit.layers["encoding"])

            # O/P/R/Xin
            circuit.observe()
            circuit.detect_circulations()
            if prev_activations:
                circuit.compute_xin(prev_activations)

            # Learn with ATTENUATED STDP weight
            # Parse stdp_weight from calculation_variant stored in DB
            stdp_weight = 0.4  # default fallback
            cv_row = conn.execute(
                "SELECT calculation_variant FROM v40_signal_entropy_ledger "
                "WHERE window_id=? AND run_id=?",
                (syn_win_id, run_id)).fetchone()
            if cv_row and "weight_" in cv_row[0]:
                try:
                    stdp_weight = float(cv_row[0].rsplit("_", 1)[1])
                except (ValueError, IndexError):
                    pass

            # Scale STDP learning by synthetic weight
            eta_orig = 1.0 / max(circuit._temperature, 0.1)
            eta_syn = max(0.1, min(2.0, eta_orig)) * stdp_weight
            for layer in circuit.layers.values():
                for bundle in layer.bundles:
                    pre_neurons = [layer.neurons[sid]
                                   for sid in bundle.source_neuron_ids
                                   if sid in layer.neurons]
                    post_neurons = [layer.neurons[tid]
                                    for tid in bundle.target_neuron_ids
                                    if tid in layer.neurons]
                    if pre_neurons and post_neurons:
                        bundle.stdp_update(pre_neurons, post_neurons, stdp_weight)

            for bundle in circuit.inter_layer_bundles:
                src_layer = None
                for lid, l in circuit.layers.items():
                    if bundle.source_neuron_ids[0] in l.neurons:
                        src_layer = l
                        break
                if src_layer is None:
                    continue
                pre_neurons = [src_layer.neurons[sid]
                               for sid in bundle.source_neuron_ids
                               if sid in src_layer.neurons]
                post_neurons = []
                for lid, l in circuit.layers.items():
                    for tid in bundle.target_neuron_ids:
                        if tid in l.neurons:
                            post_neurons.append(l.neurons[tid])
                if pre_neurons and post_neurons:
                    bundle.stdp_update(pre_neurons, post_neurons, stdp_weight)

            # Extract z_t for synthetic windows BEFORE maintain (decay zeroes it)
            enc = circuit.layers["encoding"]
            circuit_z_t = [enc.neurons[c].activation for c in z_t_names]

            # Map synthetic window to stimulus name for discrimination
            # syn_<stim_name>_<i> → stim_name
            stim_from_syn = syn_win_id.replace("syn_", "").rsplit("_", 1)[0]
            circuit_z_t_by_stim[stim_from_syn].append(tuple(circuit_z_t))

            circuit.maintain()

            prev_activations = {nid: n.activation for nid, n in enc.neurons.items()}

        print(f"    Synthetic injection complete. Total circuit ticks: {circuit.tick}")


    # ══════════════════════════════════════════════════════════════
    # Phase 3 [R]: Counter-evidence validation + discrimination
    # ══════════════════════════════════════════════════════════════
    print(f"\n{'─' * 72}")
    print("  Phase 3 [R]: Discrimination + counter-evidence analysis")
    print(f"{'─' * 72}")

    stim_names = sorted(circuit_z_t_by_stim.keys())
    print(f"  Stimuli: {stim_names}")
    print(f"  Samples: {', '.join(f'{s}={len(circuit_z_t_by_stim[s])}' for s in stim_names)}")

    def compute_mean(z_list):
        n = len(z_list)
        dim = len(z_list[0])
        return tuple(sum(z[d] for z in z_list) / n for d in range(dim))

    circuit_means = {}
    for s in stim_names:
        if circuit_z_t_by_stim.get(s):
            circuit_means[s] = compute_mean(circuit_z_t_by_stim[s])

    print(f"\n  Circuit discrimination (signal entropy driven):")
    circuit_sims = []
    for i, s1 in enumerate(stim_names):
        for s2 in stim_names[i+1:]:
            if s1 in circuit_means and s2 in circuit_means:
                sim = cosine_sim(circuit_means[s1], circuit_means[s2])
                circuit_sims.append(sim)
                print(f"    cos({s1[:18]:18s}, {s2[:18]:18s}) = {sim:.6f}")

    avg_circuit = sum(circuit_sims) / max(len(circuit_sims), 1)

    print(f"\n  Per-dimension z_t profiles:")
    for s in stim_names:
        if s in circuit_means:
            vals = "  ".join(f"{v:.4f}" for v in circuit_means[s])
            print(f"    {s[:22]:22s}: [{vals}]")

    # Signal entropy bundle evolution
    print(f"\n  Signal entropy → z_t bundle evolution:")
    for b in circuit.inter_layer_bundles:
        if b.bundle_id.startswith("sigH_"):
            cond = getattr(b, '_conductance_history', 0.0)
            print(f"    {b.bundle_id:35s}: strength={b.bundle_strength:.4f}  "
                  f"conductance={cond:.4f}  inertia={b.bundle_inertia:.4f}")

    # Circulation amplification stats
    try:
        amp_rows = conn.execute(
            "SELECT gain_combined, entropy_slope_spectral, entropy_slope_fano "
            "FROM v40_circulation_amplification_ledger "
            "WHERE run_id=? ORDER BY CAST(stage_k_id AS INTEGER)",
            (run_id,)).fetchall()
        if amp_rows:
            gains_all = [r[0] for r in amp_rows]
            amplified = sum(1 for g in gains_all if g > 1.01)
            print(f"\n  Circulation amplification (from entropy ledger):")
            print(f"    Windows amplified: {amplified}/{len(gains_all)}")
            print(f"    Gain range: [{min(gains_all):.3f}, {max(gains_all):.3f}]  "
                  f"mean={sum(gains_all)/len(gains_all):.3f}")
    except Exception:
        pass

    # Homeostatic state: structural differentiation
    print(f"\n  Homeostatic differentiation (encoding layer):")
    for nid in z_t_names:
        n = circuit.layers["encoding"].neurons[nid]
        print(f"    {nid:18s}: threshold={n.threshold:.6f}  "
              f"calcium={n.calcium:.6f}  pre_trace={n.pre_trace:.4f}")

    # R-chain: which z_t dims have structural support?
    print(f"\n  R-chain: structural support per z_t dimension:")
    for nid in z_t_names:
        n = circuit.layers["encoding"].neurons[nid]
        # Dimension has support if: threshold adapted away from initial AND calcium > 0
        calcium_active = n.calcium > 0.001
        threshold_adapted = abs(n.threshold - 0.005) > 0.0001
        has_bundle_support = any(
            nid in b.target_neuron_ids and b.bundle_strength > 0.05
            for b in circuit.layers["encoding"].bundles + circuit.inter_layer_bundles
        )
        status = "✅" if (calcium_active or threshold_adapted) else "⚠️ weak"
        print(f"    {nid:18s}: ca={calcium_active}  thr_adapt={threshold_adapted}  "
              f"bundle={has_bundle_support}  → {status}")

    m = circuit.get_metrics()
    print(f"\n  Circuit: alive={m['alive_neurons']}/{m['total_neurons']}  "
          f"P={'✓' if m['p_circulation'] else '✗'}  "
          f"R={'✓' if m['r_circulation'] else '✗'}  "
          f"T={m['temperature']:.4f}  fruits={m['dormant_fruits']}")

    # v40.7: Column physical privilege report
    print(f"\n  v40.7 Structural privilege (Column ≠ Spine):")
    columns_found = 0
    total_prp = 0.0
    for lid, layer in circuit.layers.items():
        for nid, n in layer.neurons.items():
            if n.maturation != "spine":
                columns_found += 1
                total_prp += n.prp_emission
                print(f"    {nid:18s}: {n.maturation:6s}  "
                      f"lat_r={n.lateral_suppression_radius}  "
                      f"ltp×={n.stdp_ltp_boost:.1f}  "
                      f"prp={n.prp_emission:.4f}")
    if columns_found == 0:
        print("    (no neurons matured beyond Spine yet)")
    else:
        print(f"    → {columns_found} Column/Area neurons, total PRP={total_prp:.4f}")

    # v40.7: Dormant fruit trace decay statistics
    all_fruits = []
    for lid, layer in circuit.layers.items():
        for b in layer.bundles:
            if b.xin_dormant_fruit is not None:
                all_fruits.append(b.xin_dormant_fruit)
    for b in circuit.inter_layer_bundles:
        if b.xin_dormant_fruit is not None:
            all_fruits.append(b.xin_dormant_fruit)
    if all_fruits:
        traces = [f.get("trace_strength", 1.0) for f in all_fruits]
        print(f"\n  Dormant fruit traces: {len(all_fruits)} alive")
        print(f"    trace range: [{min(traces):.4f}, {max(traces):.4f}]  "
              f"mean={sum(traces)/len(traces):.4f}")

    # Circulation measure (probability integral over all paths)
    circ_mu = getattr(circuit, '_circulation_measure', 0.0)
    all_cycles = getattr(circuit, '_all_cycle_measures', [])
    ghost_count = sum(len(getattr(l, '_ghost_bundles', []))
                      for l in circuit.layers.values())
    print(f"\n  Circulation measure μ(G) = {circ_mu:.6f}")
    print(f"    Active cycles: {len(all_cycles)}")
    if all_cycles:
        print(f"    P fraction: {all_cycles[0]['fraction']:.4f}")
        if len(all_cycles) > 1:
            print(f"    R fraction: {all_cycles[1]['fraction']:.4f}")
            print(f"    Secondary+: {sum(c['fraction'] for c in all_cycles[2:]):.4f}")
    print(f"    Ghost bundles: {ghost_count}")

    # v40.7e: Convergence sub-manifold report
    conv_nodes = getattr(circuit, '_convergence_nodes', {})
    if conv_nodes:
        print(f"\n  v40.7e Shared sub-manifold convergence nodes: {len(conv_nodes)}")
        for node_id, node in sorted(conv_nodes.items(),
                                     key=lambda x: -x[1]["strength"]):
            dims = " × ".join(node["dims"])
            print(f"    {dims:30s}  strength={node['strength']:.6f}  "
                  f"prime={node['priming_applied']:.6f}  "
                  f"age={circuit.tick - node['created_tick']}")
    else:
        print(f"\n  v40.7e Convergence: (no sub-manifold nodes detected yet)")

    # ══════════════════════════════════════════════════════════════
    # Phase 4 [Xin]: Verdict + structural tension
    # ══════════════════════════════════════════════════════════════
    print(f"\n{'=' * 72}")
    print("  Phase 4 [Xin]: VERDICT + remaining tension")
    print(f"{'=' * 72}")

    flat_avg = 0.999460  # known baseline from flat W_signal
    improved = avg_circuit < flat_avg
    print(f"  Flat baseline cosine: {flat_avg:.6f}")
    print(f"  Circuit avg cosine:   {avg_circuit:.6f}")
    print(f"  Improvement:          {flat_avg - avg_circuit:.6f}")
    print(f"  Discrimination:       {'✅ YES' if improved else '❌ NO'}")

    thresholds = [circuit.layers["encoding"].neurons[n].threshold for n in z_t_names]
    thr_std = math.sqrt(sum((t - sum(thresholds)/len(thresholds))**2 for t in thresholds)/len(thresholds))
    print(f"  Threshold diversity:  std={thr_std:.6f} {'✅' if thr_std > 0.0005 else '❌'}")

    # Count non-zero dimensions per stimulus
    active_dims = {}
    for s in stim_names:
        if s in circuit_means:
            active = sum(1 for v in circuit_means[s] if abs(v) > 0.001)
            active_dims[s] = active
    print(f"  Active dimensions:    {active_dims}")

    # Remaining Xin tension
    xin_total = sum(abs(v) for v in circuit._xin_tensions.values())
    print(f"  Xin total tension:    {xin_total:.4f}")
    print(f"  Activated fruits:     {len(circuit._activated_fruits)}")

    report = {
        "flat_avg_cosine": flat_avg,
        "circuit_avg_cosine": avg_circuit,
        "improvement": flat_avg - avg_circuit,
        "improved": improved,
        "threshold_diversity": thr_std,
        "active_dims": active_dims,
        "xin_tension": xin_total,
        "circuit_metrics": m,
        "signal_entropy_rows": len(sig_rows),
        "masking_records": mask_count,
    }
    rp = str(BASE / "db" / "v40_integrated_report.json")
    with open(rp, "w") as f_out:
        json.dump(report, f_out, indent=2, default=str)
    print(f"\n  DB:     {DB_PATH}")
    print(f"  Report: {rp}")
    print("=" * 72)

    conn.close()


if __name__ == "__main__":
    main()
```
