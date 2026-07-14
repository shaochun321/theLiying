"""nexus_v1.components.skin_network — Spherical point-distribution geometry.

TYPE:MATH

Pure geometry: generates N near-uniformly distributed points on a sphere.
No neuron/bundle code here — this module has zero dependency on the
Neuron/SynapticBundle mother classes, by design (a coordinate generator
should not know about circuits).

Used by the thermal quantum-meta-unit reconstruction (variant_adapter.py)
to place local generator units (ξ) on a skin-surface sphere, replacing
hand-written 12-patch coordinate tables with a formula that scales to
arbitrary N.
"""

from __future__ import annotations

import math
from typing import List, Tuple


def fibonacci_sphere_points(n: int, radius: float = 1.0) -> List[Tuple[float, float, float]]:
    """Generate n near-uniformly distributed points on a sphere (golden angle spiral).

    REF: Swinbank & Purser 2006 Q.J.R. Meteorol. Soc. 132:1769 — Fibonacci
         grids for near-uniform spherical sampling (used in global climate
         modeling for even coverage without polar clustering).

    Unlike a naive lat/long grid (which over-samples the poles) or an
    icosphere (which only admits specific subdivision counts: 12, 42, 162...),
    this formula accepts ANY n >= 1 and is O(n), with no iterative relaxation.

    Args:
        n: number of points (must be >= 1).
        radius: sphere radius (same units as body-frame local_offset, mm).

    Returns:
        List of (x, y, z) tuples, each at distance `radius` from origin.
    """
    if n < 1:
        raise ValueError(f"fibonacci_sphere_points: n must be >= 1, got {n}")

    points: List[Tuple[float, float, float]] = []
    golden_angle = math.pi * (3.0 - math.sqrt(5.0))  # ≈ 2.399963 rad
    for i in range(n):
        # z sweeps linearly from just-below +1 to just-above -1 (avoids
        # placing a point exactly at either pole, which would zero out
        # r_xy and waste a sample).
        z = 1.0 - 2.0 * (i + 0.5) / n
        r_xy = math.sqrt(max(0.0, 1.0 - z * z))
        theta = i * golden_angle
        points.append((
            radius * r_xy * math.cos(theta),
            radius * r_xy * math.sin(theta),
            radius * z,
        ))
    return points


def compute_coupling_weights(
    positions: List[Tuple[float, float, float]],
    directions: List[Tuple[float, float, float]],
    sharpness: float = 2.0,
    base_weight: float = 0.5,
) -> List[List[float]]:
    """Construction-time cos^sharpness coupling weights from points to directions.

    BIO: dorsal-horn wide-dynamic-range neurons pool primary afferents whose
         receptive-field centers cluster along a preferred spatial axis —
         the pooling geometry is fixed by anatomy, not learned (Willis &
         Coggeshall 2004, spinal dorsal horn convergence). This mirrors the
         half-wave-rectified cos^2 receptive-field weighting already used
         for vestibular canal afferent convergence in this codebase.

    Each row d gives 64 (or N) weights for how strongly point i couples into
    direction d: w[d][i] = base_weight * max(0, cos(theta))^sharpness, where
    theta is the angle between position i and direction d. Points behind the
    direction (cos(theta) <= 0) get weight 0 — half-wave rectification is
    the physical basis of directional selectivity (no sign()/if branching
    on semantic meaning; it falls out of the dot product itself).

    Args:
        positions: N point coordinates (e.g. from fibonacci_sphere_points).
        directions: M unit-ish direction vectors (need not be pre-normalized).
        sharpness: exponent on the rectified cosine (tuning sharpness).
        base_weight: peak weight at cos(theta) = 1.

    Returns:
        M x N matrix: weights[d][i] = coupling weight from point i to direction d.
    """
    weights: List[List[float]] = []
    for d in directions:
        d_norm = math.sqrt(d[0] * d[0] + d[1] * d[1] + d[2] * d[2])
        row: List[float] = []
        for p in positions:
            p_norm = math.sqrt(p[0] * p[0] + p[1] * p[1] + p[2] * p[2])
            denom = p_norm * d_norm
            if denom <= 0.0:
                row.append(0.0)
                continue
            cos_theta = (p[0] * d[0] + p[1] * d[1] + p[2] * d[2]) / denom
            cos_theta = max(0.0, min(1.0, cos_theta))
            row.append(base_weight * (cos_theta ** sharpness))
        weights.append(row)
    return weights
