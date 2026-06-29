"""TYPE:INFRA — Vestibular sub-network topology registry.

Implements V-N1..V-N5 from 以前庭重构为驱动的网络层接入方案.

Design:
  - All topology queries (delay, cost, gain, nearby) pre-computed at init.
  - Zero per-step runtime cost: network layer is consulted only at init.
  - α=5.0 vestibular gain applied only to region=0x02 addresses.

BIO: Brainstem vestibular nucleus topology (Brodal 1974).
     Cluster distances: canal↔canal=1, oto↔oto=1, canal↔oto=3, vest↔thermal=10.
     REF: 以前庭重构为驱动的网络层接入方案 §2-§5
"""
from __future__ import annotations

import math
from typing import Dict, List, NamedTuple, Optional, Tuple


# ─────────────────────────────────────────────────────────────────────────────
# Address definition (V-N1)
# ─────────────────────────────────────────────────────────────────────────────

class VestibularAddress(NamedTuple):
    """5-tuple topology address for vestibular neurons.

    Fields:
        region   : 0x02 = brainstem vestibular nucleus
        layer    : 1=MET, 2=HC, 3=Aff, 4=Enc, 5=Col
        tau_class: 1=fast (MET/HC/Aff), 2=medium (Enc/Col)
        axis     : 0=yaw, 1=pitch, 2=roll, 3=oto_x, 4=oto_y, 5=oto_z
        index    : 0=regular/default, 1=irregular (Aff only)
    """
    region: int
    layer: int
    tau_class: int
    axis: int
    index: int


# ─────────────────────────────────────────────────────────────────────────────
# Canonical address table (V-N1)
# ─────────────────────────────────────────────────────────────────────────────

AXES = ["yaw", "pitch", "roll", "oto_x", "oto_y", "oto_z"]

VESTIBULAR_ADDRESSES: Dict[str, VestibularAddress] = {}
for _i, _axis in enumerate(AXES):
    VESTIBULAR_ADDRESSES[f"met_{_axis}"]     = VestibularAddress(0x02, 1, 1, _i, 0)
    VESTIBULAR_ADDRESSES[f"hc_{_axis}"]      = VestibularAddress(0x02, 2, 1, _i, 0)
    VESTIBULAR_ADDRESSES[f"aff_reg_{_axis}"] = VestibularAddress(0x02, 3, 1, _i, 0)
    VESTIBULAR_ADDRESSES[f"aff_irr_{_axis}"] = VestibularAddress(0x02, 3, 1, _i, 1)
    VESTIBULAR_ADDRESSES[f"enc_{_axis}"]     = VestibularAddress(0x02, 4, 2, _i, 0)
    VESTIBULAR_ADDRESSES[f"col_{_axis}"]     = VestibularAddress(0x02, 5, 2, _i, 0)


# ─────────────────────────────────────────────────────────────────────────────
# Distance function (V-N2)
# ─────────────────────────────────────────────────────────────────────────────

# Conduction velocity: fast myelinated fibers ~1 m/ms = 1000 mm/ms
# With dt=0.001 s → delay_steps = ceil(L / (1000 × 0.001)) = ceil(L)
# BIO: VOR latency 5-15 ms; total MET→Col = 2+2+3+2 = 9 steps (9 ms) ✓
# REF: Hille (2001) Ion Channels; Carey & Bhatt (2005) J Neurophysiol
V_COND = 1000.0   # mm/ms (fast myelinated; scales L to ≈1 step/unit)
DT = 0.001        # simulation timestep (s)

# Spatial cluster distances
_L_INTRA = 1.0    # within canal cluster (yaw/pitch/roll) or otolith cluster (oto_x/y/z)
_L_INTER = 3.0    # canal ↔ otolith cross-cluster

# Scaling coefficients
_L_TAU_SCALE   = 0.5   # per τ_class difference
_L_LAYER_SCALE = 1.0   # per layer difference

# Gain parameters (V-N4) — vestibular-only
_G_BASE      = 2.0    # base synaptic gain
_ALPHA_VEST  = 5.0    # energy sensitivity: only region=0x02
_BETA        = 0.3    # temporal-mismatch compensation
_L_TAU_MAX   = 2.0    # max possible temporal distance (4 × 0.5)
_P_BASELINE  = 1.0    # energy reference: fill=1.0 at full capacity → ratio=1.0 at max


def _l_spatial(axis_i: int, axis_j: int) -> float:
    """Cluster-aware spatial distance (V-N2, §3.1)."""
    canal_i = axis_i <= 2
    canal_j = axis_j <= 2
    return _L_INTRA if (canal_i == canal_j) else _L_INTER


def l_total(a: VestibularAddress, b: VestibularAddress) -> float:
    """Total topological distance L = L_spatial + L_temporal + L_layer (V-N2)."""
    if a == b:
        return 0.0
    l_s = _l_spatial(a.axis, b.axis)
    l_t = abs(a.tau_class - b.tau_class) * _L_TAU_SCALE
    l_l = abs(a.layer - b.layer) * _L_LAYER_SCALE
    return l_s + l_t + l_l


# ─────────────────────────────────────────────────────────────────────────────
# Utility: soft saturation (replaces PowerRail hard cutoff)
# ─────────────────────────────────────────────────────────────────────────────

def soft_saturate(i_in: float, r_supply: float = 0.05) -> float:
    """Soft saturation I_out = I_in / (1 + I_in * r_supply).

    BIO: Metabolic supply limitation (Laughlin et al. 1998, Nature Neurosci).
    Replaces hard cutoff `max(0, 1 - I*r) = 0` in PowerRail.draw().
    Output is always > 0 for positive input; converges to 1/r_supply = 20.
    """
    if i_in <= 0.0:
        return 0.0
    return i_in / (1.0 + i_in * r_supply)


# ─────────────────────────────────────────────────────────────────────────────
# Network layer (V-N1..V-N5)
# ─────────────────────────────────────────────────────────────────────────────

class VestibularNetworkLayer:
    """Topology registry for the vestibular sub-network.

    All 24 canonical addresses pre-registered. Queries (delay, cost, gain,
    nearby) are cached at first call. No per-step runtime cost.

    Args:
        p_avail_ref: mutable list of length 1 holding current P_avail/P_baseline.
            Update p_avail_ref[0] each step from EnergyStore.fill for dynamic G_eff.
            Defaults to [1.0] (always full energy) if not provided.
    """

    def __init__(self, p_avail_ref: Optional[List[float]] = None):
        self._addresses: Dict[str, VestibularAddress] = dict(VESTIBULAR_ADDRESSES)
        self._p_avail: List[float] = p_avail_ref if p_avail_ref is not None else [1.0]
        self._delay_cache: Dict[Tuple, int] = {}
        self._cost_cache:  Dict[Tuple, float] = {}

    # ── V-N1: address registry ────────────────────────────────────────────

    def register(self, name: str) -> VestibularAddress:
        """Return pre-defined address for a named neuron (V-N1)."""
        if name not in self._addresses:
            raise KeyError(f"VestibularNetworkLayer: unknown neuron '{name}'")
        return self._addresses[name]

    # ── V-N3: delay and energy cost queries ──────────────────────────────

    def delay(self, src: VestibularAddress, dst: VestibularAddress) -> int:
        """FIFO delay in simulation steps for connection src→dst (V-N3).

        delay_steps = ceil(L_total / (V_COND * DT))
        With V_COND=1000, DT=0.001: delay_steps = ceil(L_total) (integer steps).
        Minimum 1 step (never zero-delay for distinct neurons).
        """
        key = (src, dst)
        if key not in self._delay_cache:
            l = l_total(src, dst)
            steps = max(1, math.ceil(l / (V_COND * DT)))
            self._delay_cache[key] = steps
        return self._delay_cache[key]

    def energy_cost(self, src: VestibularAddress, dst: VestibularAddress) -> float:
        """Structural energy cost proportional to L_total (V-N3).

        Longer connections pay a higher structural maintenance tax (P_S).
        """
        key = (src, dst)
        if key not in self._cost_cache:
            self._cost_cache[key] = l_total(src, dst)
        return self._cost_cache[key]

    # ── V-N4: energy-gated dynamic gain ──────────────────────────────────

    def gain_coeff(self, src: VestibularAddress, dst: VestibularAddress) -> float:
        """Dynamic gain G_eff for Aff→Enc vestibular connections (V-N4).

        G_eff = G_base × (1 + α × P_avail) × (1 + β × (1 - L_t / L_max))

        α=5.0 only for vestibular region (0x02); prevents thermal test interference.
        Verification at 2 Hz, P_avail=1.0, L_t=0.5:
          G_eff = 2.0 × 6.0 × 1.225 = 14.7
          V_ss = 2 × 2.5 × 14.7 × 0.001 × 5.0 = 0.367 V > V_th=0.30 V ✓ (22% margin)
        BIO: Metabolic modulation of synaptic gain (Harris & Attwell 2012)
        """
        alpha = (_ALPHA_VEST
                 if (src.region == 0x02 and dst.region == 0x02)
                 else 0.0)
        p_avail = self._p_avail[0]
        l_t = abs(src.tau_class - dst.tau_class) * _L_TAU_SCALE
        return (_G_BASE
                * (1.0 + alpha * p_avail / _P_BASELINE)
                * (1.0 + _BETA * (1.0 - l_t / _L_TAU_MAX)))

    # ── V-N5: topological proximity query ────────────────────────────────

    def nearby(self, addr: VestibularAddress, radius: float = 3.0) -> List[VestibularAddress]:
        """All registered addresses with L_total ≤ radius (V-N5).

        Used by Col→Motor sprout decisions. radius=3 selects same-cluster Motor nodes.
        """
        return [a for a in self._addresses.values()
                if a != addr and l_total(addr, a) <= radius]

    # ── Convenience ──────────────────────────────────────────────────────

    def make_fifo(self, src: VestibularAddress, dst: VestibularAddress,
                  sigma: float = 0.01) -> "FIFODelayBuffer":
        """Create a pre-filled FIFO buffer for the (src→dst) connection."""
        from nexus_v1.vestibular.fifo_buffer import FIFODelayBuffer
        return FIFODelayBuffer(self.delay(src, dst), sigma=sigma)

    def summary(self) -> dict:
        """Return address table and sample delay values for verification."""
        sample = {}
        axes = AXES
        for ax in axes[:2]:
            met = self._addresses[f"met_{ax}"]
            hc  = self._addresses[f"hc_{ax}"]
            aff = self._addresses[f"aff_reg_{ax}"]
            enc = self._addresses[f"enc_{ax}"]
            col = self._addresses[f"col_{ax}"]
            sample[ax] = {
                "met→hc":  self.delay(met, hc),
                "hc→aff":  self.delay(hc, aff),
                "aff→enc": self.delay(aff, enc),
                "enc→col": self.delay(enc, col),
                "G_eff(aff→enc)": round(self.gain_coeff(aff, enc), 3),
            }
        return {
            "n_addresses": len(self._addresses),
            "sample_delays": sample,
            "p_avail": self._p_avail[0],
        }
