"""nexus_v1.components.binding_temporal — STF temporal convolution for Binding.

TYPE:BIO
Extends BindingCell with a leaky integrator (Capacitor) on vestibular axes,
implementing presynaptic short-term facilitation (STF) for causal coincidence
detection between vestibular motion and thermal signals.

Causal asymmetry: vestibular axes are time-convolved; thermal axes are
instantaneous. This ensures STDP learns "motion caused thermal change",
not "thermal change caused motion".

BIO: Presynaptic Ca2+ remnant fast component (~20-50ms) drives STF.
REF: Zucker RS & Regehr WG (2002) "Short-term synaptic plasticity."
     Annual Review of Physiology 64:355-405.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Dict, List, Set

from .binding import BindingCell, BindingConfig, BindingLayer


@dataclass
class TemporalBindingConfig(BindingConfig):
    # BIO: STF fast calcium remnant time constant 20-50ms; 30ms = midpoint.
    # Units: steps (at dt=0.001s, 30 steps = 30ms).
    # REF: Zucker & Regehr 2002, Annu Rev Physiol 64:355-405.
    tau_w: int = 30
    # Axes kept instantaneous (no convolution — causal asymmetry preserved).
    # Thermal axis stays instantaneous so STDP can infer causal direction.
    thermal_axes: Set[str] = field(
        default_factory=lambda: {'therm'}
    )


class TemporalBindingCell(BindingCell):
    """TYPE:BIO — Vestibular-thermal coincidence detector with STF window.

    Extends BindingCell by applying an exponential moving average (Capacitor)
    to vestibular axes only. Thermal axes pass through instantaneously.

    Leaky integrator: Ṽ_i[t] = decay × Ṽ_i[t-1] + (1-decay) × V_i[t]
    where decay = exp(-1/tau_w).

    Causal asymmetry: V_i(t) → convolved; T_j(t) → instantaneous.
    This asymmetry is what allows STDP to distinguish "motion → heat" from
    "heat → motion" — only the vestibular signal has temporal persistence.

    BIO: Presynaptic Ca2+ remnant drives STF, tau_STF fast ~20-50ms.
    REF: Zucker & Regehr 2002, Annu Rev Physiol 64:355-405.
    """

    def __init__(self, config: TemporalBindingConfig):
        super().__init__(config)
        self._tau_config: TemporalBindingConfig = config
        # Capacitor: per-step exponential decay factor
        self._decay: float = math.exp(-1.0 / max(config.tau_w, 1))
        self._update: float = 1.0 - self._decay
        # Leaky integrator state for vestibular axes (Capacitor analogue)
        self._v_tilde: Dict[str, float] = {
            ax: 0.0 for ax in config.source_axes
            if ax not in config.thermal_axes
        }

    def compute(self, col_activations: Dict[str, float]) -> float:
        """Override: convolve vestibular axes, pass thermal axes instantaneously."""
        # Step 1: update leaky integrators for vestibular axes
        for ax in self._v_tilde:
            v_now = col_activations.get(ax, 0.0)
            self._v_tilde[ax] = (self._decay * self._v_tilde[ax]
                                 + self._update * v_now)

        # Step 2: build effective activation dict for parent AND gate
        effective: Dict[str, float] = {}
        for ax in self._tau_config.source_axes:
            if ax in self._tau_config.thermal_axes:
                effective[ax] = col_activations.get(ax, 0.0)   # instantaneous
            else:
                effective[ax] = self._v_tilde[ax]               # time-convolved

        # Step 3: delegate to parent product AND gate
        return super().compute(effective)

    def reset_integrators(self) -> None:
        """Reset leaky integrators to zero (e.g., between trials)."""
        for ax in self._v_tilde:
            self._v_tilde[ax] = 0.0


class TemporalBindingLayer(BindingLayer):
    """Collection of TemporalBindingCells for all axis pairs.

    Drop-in replacement for BindingLayer. Creates TemporalBindingCell
    instances instead of plain BindingCell, with causal asymmetry for
    thermal axes.

    The co_activation_threshold=0.0 (learning window fully open) is set
    at construction time so that time-convolved vestibular signals (which
    are attenuated to ~0.632× peak) are not spuriously gated out.
    """

    def __init__(self, axes: List[str],
                 co_activation_threshold: float = 0.0,
                 tau_w: int = 30,
                 thermal_axes: Set[str] | None = None):
        # Do not call super().__init__() — we override cell creation entirely
        if thermal_axes is None:
            thermal_axes = {'therm'}
        self._axes = axes
        self._tau_w = tau_w
        self._thermal_axes = thermal_axes
        self.cells: Dict[str, TemporalBindingCell] = {}

        # Create C(n,2) TemporalBindingCell pairs
        for i in range(len(axes)):
            for j in range(i + 1, len(axes)):
                pair_id = f"bind_{axes[i]}_{axes[j]}"
                cell = TemporalBindingCell(TemporalBindingConfig(
                    binding_id=pair_id,
                    source_axes=(axes[i], axes[j]),
                    co_activation_threshold=co_activation_threshold,
                    tau_w=tau_w,
                    thermal_axes=set(thermal_axes),
                ))
                self.cells[pair_id] = cell

    def reset_all_integrators(self) -> None:
        """Reset all leaky integrators (e.g., between experimental trials)."""
        for cell in self.cells.values():
            cell.reset_integrators()
