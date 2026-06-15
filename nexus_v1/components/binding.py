"""nexus_v1.components.binding — Hyperedge Binding Layer (§5 of math spec).

Detects conjunctive activation across column neurons.
Structurally created at build time (15 pairs from C(6,2)).
Initial weights ≈ 0.001 (dormant). STDP/BCM activates relevant ones.

DEGRADED from "dynamic_structural_plasticity":
  In biology, shadow layer pressure could grow new hyperedges.
  Current implementation: structure fixed, weights variable.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Dict, List, Tuple

from .neuron import Neuron


@dataclass
class BindingConfig:
    """Configuration for one hyperedge (binding cell)."""
    binding_id: str = ""
    source_axes: Tuple[str, ...] = ()   # e.g. ("yaw", "pitch")
    co_activation_threshold: float = 0.05  # θ_p: minimum activation
    gain: float = 1.0                      # G_p


class BindingCell:
    """A single hyperedge that detects conjunctive activation (§5.2).

    Activation = G × Π ReLU((a_i - θ) / θ)  (AND gate)

    When ALL source axes exceed threshold → output > 0.
    When ANY source axis is below threshold → output = 0.
    """

    def __init__(self, config: BindingConfig):
        self.config = config
        self.activation: float = 0.0
        self._activation_ema: float = 0.0

    def compute(self, col_activations: Dict[str, float]) -> float:
        """Compute binding cell activation from column activations.

        Args:
            col_activations: {axis_name: activation_value}

        Returns:
            Hyperedge activation (0 if any source below threshold).
        """
        product = self.config.gain
        theta = self.config.co_activation_threshold

        for axis in self.config.source_axes:
            a = abs(col_activations.get(axis, 0.0))
            # ReLU((a - θ) / θ)
            normalized = (a - theta) / max(theta, 1e-8)
            if normalized <= 0:
                self.activation = 0.0
                return 0.0
            product *= normalized

        # FIX-015: Saturate binding output.
        # BIO: Receptor saturation + vesicle depletion limit synaptic AND gates.
        # Without this, product grows as O(a^n) where n=#sources → explosion.
        self.activation = min(product, 10.0)  # cap at 10 (same as neuron activation)
        self._activation_ema += 0.01 * (self.activation - self._activation_ema)
        return self.activation


class BindingLayer:
    """Collection of all hyperedges for the circuit (§5.3).

    Structurally creates C(n,2) binding cells at initialization.
    All start dormant (gain=1.0 but weights to motor are ~0.001).
    """

    def __init__(self, axes: List[str], co_activation_threshold: float = 0.05):
        """Create binding cells for all pairs of axes.

        Args:
            axes: List of axis names (e.g. 6 vestibular axes).
            co_activation_threshold: Shared θ_p for all cells.
        """
        self.cells: Dict[str, BindingCell] = {}
        self._axes = axes

        # Create C(n,2) pairs
        for i in range(len(axes)):
            for j in range(i + 1, len(axes)):
                pair_id = f"bind_{axes[i]}_{axes[j]}"
                cell = BindingCell(BindingConfig(
                    binding_id=pair_id,
                    source_axes=(axes[i], axes[j]),
                    co_activation_threshold=co_activation_threshold,
                ))
                self.cells[pair_id] = cell

    @property
    def n_cells(self) -> int:
        return len(self.cells)

    def compute_all(self, col_activations: Dict[str, float]) -> Dict[str, float]:
        """Compute all binding cell activations.

        Args:
            col_activations: {axis: activation} from column neurons.

        Returns:
            {binding_id: activation} for all cells.
        """
        results = {}
        for bid, cell in self.cells.items():
            results[bid] = cell.compute(col_activations)
        return results

    def get_active_bindings(self, threshold: float = 0.001) -> Dict[str, float]:
        """Get only the currently active binding cells."""
        return {
            bid: cell.activation
            for bid, cell in self.cells.items()
            if cell.activation > threshold
        }

    def summary(self) -> dict:
        return {
            "n_cells": self.n_cells,
            "active": sum(1 for c in self.cells.values() if c.activation > 0.001),
            "activations": {
                bid: round(c.activation, 6)
                for bid, c in self.cells.items()
            },
        }
