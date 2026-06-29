"""TYPE:INFRA — Axonal conduction delay buffer (ring-buffer FIFO).

BIO: Myelinated axon conduction delay (Waxman & Bennett 1972).
     Pre-filled with Gaussian noise to model embryonic spontaneous activity,
     preventing downstream "sensory deprivation" at simulation start.
"""
from __future__ import annotations

import collections
import random


class FIFODelayBuffer:
    """Ring-buffer FIFO for axonal signal delay.

    delay_steps = ceil(L_total / (v_cond * dt))
    Pre-filled with σ=0.01 noise per 以前庭重构-补充 §3.
    """

    def __init__(self, delay_steps: int, sigma: float = 0.01):
        if delay_steps < 1:
            delay_steps = 1
        self._delay = delay_steps
        # Pre-fill with low-amplitude Gaussian noise
        self._buf: collections.deque = collections.deque(
            [random.gauss(0.0, sigma) for _ in range(delay_steps)],
            maxlen=delay_steps,
        )

    def push_and_pop(self, value: float) -> float:
        """Push value to right; return the oldest value (= delay_steps ago)."""
        oldest = self._buf[0]
        self._buf.append(value)
        return oldest

    @property
    def delay_steps(self) -> int:
        return self._delay
