"""nexus_v1.circuit.circulation — P/R/Xin Circulation Meter (§6 of math spec).

Measures persistent circulation patterns in the Hebbian circuit.
Circulation is continuous (C-001.2): it doesn’t appear or disappear.
This module measures the strength, frequency, and topology of
the signal flow that is always running through the structure.

With the Binding Layer, closed loops exist:
    Col_i → Bind_p → Mot_m → feedback → Col_i

This module:
    1. Enumerates all closed paths through the binding layer
    2. Computes flow φ(γ) = Π σ_k for each path
    3. Filters paths below MIN_FLOW threshold (C-001.5)
    4. Identifies P (strongest) and R (second strongest)
    5. Computes the ρ vector (§6.3)
    6. Tracks flow history for frequency analysis

Pure observer — reads circuit state, NEVER writes.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple


@dataclass
class CirculationPath:
    """A closed loop through the circuit."""
    path_id: str
    # Source column axis
    col_axis: str
    # Binding cell used
    binding_id: str
    # Target motor neuron
    motor_id: str
    # Flow = product of connection strengths along the path
    flow: float = 0.0


@dataclass
class CirculationState:
    """Current circulation state of the circuit."""
    tick: int = 0
    # P: dominant circulation (strongest closed path)
    p_path: Optional[CirculationPath] = None
    # R: runner-up circulation
    r_path: Optional[CirculationPath] = None
    # Total circulation measure μ(G)
    total_flow: float = 0.0
    # ρ vector (§6.3)
    rho: Dict[str, float] = field(default_factory=dict)
    # Motion potential ν = dρ/dt (§12)
    nu: Dict[str, float] = field(default_factory=dict)
    # Xin summary
    total_xin: float = 0.0
    # All paths for detailed analysis
    all_paths: List[CirculationPath] = field(default_factory=list)
    # Frequency of P path (cycles per 100-tick window), C-001.5
    p_frequency: float = 0.0
    # Flow variance (stability indicator)
    flow_variance: float = 0.0
    # M2: curl (vorticity) of motion potential
    # omega_ij = (dnu_i/da_j - dnu_j/da_i) / 2
    curl: Dict[str, float] = field(default_factory=dict)
    # M2: divergence of motion potential
    divergence: float = 0.0


class CirculationMeter:
    """Measures persistent circulation strength, frequency, and topology.

    Circulation is always running (C-001.2). This class measures it,
    not detects it. Like a heart rate monitor — the heart beats
    regardless of whether you’re measuring.

    Usage:
        meter = CirculationMeter()
        state = meter.measure(circuit, tick)
    """

    # Minimum flow to count a path (C-001.5: weak paths ignored)
    # NOTE: bind→mot weights start at 0.001, so flow ≈ 1e-4 initially.
    # Use 1e-5 to observe weak circulations during construction.
    MIN_FLOW = 1e-5

    def __init__(self):
        self._prev_rho: Dict[str, float] = {}
        self._prev_tick: int = 0
        # Flow history per path for frequency analysis
        self._flow_history: Dict[str, list] = {}
        # Total flow history for variance
        self._total_flow_history: list = []
        # M2: previous nu for curl computation
        self._prev_nu: Dict[str, float] = {}
        # M2: previous rho for da (denominator of curl)
        self._prev_rho_for_curl: Dict[str, float] = {}
        # M1: δa baseline tracking (EMA of activation per neuron)
        # §2.1: only deviations from baseline carry information.
        # δa_i = a_i - ā_i, where ā = EMA(a, τ=500)
        self._baseline_ema: Dict[str, float] = {}
        self._baseline_tau: float = 500.0  # EMA window (ticks)

    def measure(self, circuit, tick: int) -> CirculationState:
        """Measure current circulation state.

        Args:
            circuit: VariantCircuit with binding_layer and feedback.
            tick: Current tick number.

        Returns:
            CirculationState with P, R, ρ, ν, frequency.
        """
        state = CirculationState(tick=tick)

        # ── 1. Enumerate all closed paths ──
        # Path: Col[axis_i] → Bind[axis_i, axis_j] → Mot[m] → feedback → Col[axis_i]
        paths = []

        if not hasattr(circuit, 'binding_layer'):
            return state

        binding_layer = circuit.binding_layer

        for bid, cell in binding_layer.cells.items():
            if cell.activation < 0.01:
                continue  # C-001.5: meaningful activation threshold

            for mid, mot in circuit.motor_neurons.items():
                # Binding → Motor weight
                bind_mot_w = circuit._binding_motor_weights.get(bid, {}).get(mid, 0.0)
                if bind_mot_w < 1e-8:
                    continue

                # Motor → Column feedback strength
                fb_trace = circuit._feedback_traces.get(mid, 0.0)

                for axis in cell.config.source_axes:
                    # M1 fix: use δa (deviation from baseline) instead of |a|
                    # §2.1: only deviations carry information, not absolute level.
                    nid = f"col_{axis}"
                    raw_act = circuit.column_neurons[axis]._activation_ema  # M4: rate
                    baseline = self._baseline_ema.get(nid, 0.0)
                    col_da = abs(raw_act - baseline)  # δa = |a - ā|

                    # Col→Motor direct weight (from mother bundle)
                    col_mot_bundle = circuit.bundles_col_to_motor[0]
                    # Find the column index and motor index
                    col_idx = list(circuit.column_neurons.keys()).index(axis)
                    mot_idx = list(circuit.motor_neurons.keys()).index(mid)
                    if col_idx < len(col_mot_bundle._memristors) and mot_idx < len(col_mot_bundle._memristors[col_idx]):
                        col_mot_w = col_mot_bundle._memristors[col_idx][mot_idx].w
                    else:
                        col_mot_w = 0.0

                    # Flow = product of all strengths along the loop
                    # δa_col × binding activation × bind→mot weight × feedback
                    flow = col_da * cell.activation * bind_mot_w * max(fb_trace, 0.001)

                    path = CirculationPath(
                        path_id=f"{axis}→{bid}→{mid}",
                        col_axis=axis,
                        binding_id=bid,
                        motor_id=mid,
                        flow=flow,
                    )
                    paths.append(path)

        # ── 2. Filter weak paths and sort (C-001.5) ──
        paths = [p for p in paths if p.flow > self.MIN_FLOW]
        paths.sort(key=lambda p: p.flow, reverse=True)
        state.all_paths = paths
        state.total_flow = sum(p.flow for p in paths)

        if len(paths) >= 1:
            state.p_path = paths[0]
        if len(paths) >= 2:
            state.r_path = paths[1]

        # ── 3. Compute ρ vector (§6.3) ──
        total_xin = sum(abs(b.config.xin_tension) for b in circuit.get_all_bundles())
        state.total_xin = total_xin

        z = state.total_flow + total_xin + 1e-8  # normalization

        p_flow = state.p_path.flow if state.p_path else 0.0
        r_flow = state.r_path.flow if state.r_path else 0.0
        other_flow = state.total_flow - p_flow - r_flow

        # Determine crystallized fraction
        p_crystal = self._crystal_fraction(circuit, state.p_path)
        r_crystal = self._crystal_fraction(circuit, state.r_path)

        rho = {
            "p_c": p_flow * p_crystal / z,       # P crystallized
            "p_b": p_flow * (1 - p_crystal) / z,  # P bandwidth
            "r_c": r_flow * r_crystal / z,        # R crystallized
            "r_b": r_flow * (1 - r_crystal) / z,  # R bandwidth
            "m_b": other_flow / z,                 # masking
            "x": total_xin / z,                    # Xin tension
        }
        rho["u"] = max(0.0, 1.0 - sum(rho.values()))  # unresolved
        state.rho = rho

        # ── 4. Motion potential ν = dρ/dt (§12) ──
        if self._prev_rho and self._prev_tick > 0:
            dt_ticks = max(tick - self._prev_tick, 1)
            nu = {}
            for key in rho:
                prev_val = self._prev_rho.get(key, 0.0)
                nu[key] = (rho[key] - prev_val) / dt_ticks
            state.nu = nu
        else:
            state.nu = {k: 0.0 for k in rho}

        self._prev_rho = dict(rho)
        self._prev_tick = tick

        # ── 5. Track flow history per path (C-001.5) ──
        for path in paths:
            if path.path_id not in self._flow_history:
                self._flow_history[path.path_id] = []
            self._flow_history[path.path_id].append(path.flow)
            if len(self._flow_history[path.path_id]) > 50:
                self._flow_history[path.path_id].pop(0)

        # Track total flow history
        self._total_flow_history.append(state.total_flow)
        if len(self._total_flow_history) > 50:
            self._total_flow_history.pop(0)

        # ── 6. Compute frequency and variance (C-001.5) ──
        if state.p_path and state.p_path.path_id in self._flow_history:
            hist = self._flow_history[state.p_path.path_id]
            if len(hist) >= 4:
                # Frequency estimate: count zero-crossings of (flow - mean)
                mean_f = sum(hist) / len(hist)
                crossings = sum(
                    1 for i in range(1, len(hist))
                    if (hist[i] - mean_f) * (hist[i-1] - mean_f) < 0
                )
                # Each crossing pair = 1 cycle
                state.p_frequency = crossings / (2.0 * len(hist))

        if len(self._total_flow_history) >= 2:
            mean_tf = sum(self._total_flow_history) / len(self._total_flow_history)
            state.flow_variance = sum(
                (f - mean_tf) ** 2 for f in self._total_flow_history
            ) / len(self._total_flow_history)
        # ── 7. M2: Curl and divergence of ν (§2.3) ──
        self._compute_curl_divergence(state)

        # ── 8. M1: Update δa baselines ──
        self._update_baselines(circuit)

        return state

    def _compute_curl_divergence(self, state: CirculationState):
        """M2: Compute curl and divergence of motion potential nu.

        Curl (vorticity): omega_ij = (dnu_i/da_j - dnu_j/da_i) / 2
        Divergence: div(nu) = sum(dnu_i/da_i)

        Uses finite differences: dnu_i = nu_i(t) - nu_i(t-1)
                                 da_j  = rho_j(t) - rho_j(t-1)

        Non-zero curl = rotational dynamics in rho-space.
        Positive divergence = expanding, negative = contracting.
        """
        nu = state.nu
        if not nu or not self._prev_nu:
            state.curl = {}
            state.divergence = 0.0
            # Store for next step
            self._prev_nu = dict(nu)
            self._prev_rho_for_curl = dict(state.rho)
            return

        # Compute dnu_i and da_j
        keys = sorted(nu.keys())
        dnu = {k: nu.get(k, 0) - self._prev_nu.get(k, 0) for k in keys}
        da = {k: state.rho.get(k, 0) - self._prev_rho_for_curl.get(k, 0)
              for k in keys}

        # Curl: for each pair (i,j), omega_ij = (dnu_i/da_j - dnu_j/da_i) / 2
        curl = {}
        for i, ki in enumerate(keys):
            for j, kj in enumerate(keys):
                if i >= j:
                    continue
                da_j = da.get(kj, 0)
                da_i = da.get(ki, 0)
                # Avoid division by zero
                term1 = dnu[ki] / da_j if abs(da_j) > 1e-12 else 0.0
                term2 = dnu[kj] / da_i if abs(da_i) > 1e-12 else 0.0
                omega = (term1 - term2) / 2.0
                if abs(omega) > 1e-10:
                    curl[f"{ki},{kj}"] = omega
        state.curl = curl

        # Divergence: sum of dnu_i/da_i
        div_total = 0.0
        for k in keys:
            da_k = da.get(k, 0)
            if abs(da_k) > 1e-12:
                div_total += dnu[k] / da_k
        state.divergence = div_total

        # Store for next step
        self._prev_nu = dict(nu)
        self._prev_rho_for_curl = dict(state.rho)

    def _crystal_fraction(self, circuit, path: Optional[CirculationPath]) -> float:
        """Estimate how crystallized a circulation path is (§8.1).

        Uses weight variance as proxy: low variance = more crystallized.
        """
        if path is None:
            return 0.0

        # Check col→motor bundle weight variance
        bundle = circuit.bundles_col_to_motor[0]
        weights = [m.w for row in bundle._memristors for m in row]
        if not weights:
            return 0.0

        mean_w = sum(weights) / len(weights)
        var_w = sum((w - mean_w) ** 2 for w in weights) / len(weights)

        # Low variance → high crystallization
        # Threshold from §8.1: σ²_cry = 0.01
        if var_w < 0.01:
            return min(1.0, 1.0 - var_w / 0.01)
        return 0.0

    def _update_baselines(self, circuit):
        """M1: Update EMA baselines for column neurons (§2.1).

        ā_i(t+1) = ā_i(t) + α × (a_i(t) - ā_i(t))
        α = 1/τ_baseline

        δa_i = a_i - ā_i captures DEVIATION from baseline,
        which is the information-carrying component.
        """
        alpha = 1.0 / max(self._baseline_tau, 1.0)
        for axis, neuron in circuit.column_neurons.items():
            nid = f"col_{axis}"
            act = neuron._activation_ema  # M4: track rate for spiking neurons
            if nid not in self._baseline_ema:
                self._baseline_ema[nid] = act
            else:
                self._baseline_ema[nid] += alpha * (
                    act - self._baseline_ema[nid])

