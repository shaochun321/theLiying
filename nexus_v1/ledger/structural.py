"""nexus_v1.ledger.structural — Structural event tracking & ultrametric space.

Maps structural events (sprout/prune/mitosis) to T/O/P/R/Xin recursive
cycles with ancestry tracking. Provides ultrametric distance on the
recursion tree and structural entropy metrics.

Components:
  1. RecursionTracker: event → cycle mapping
  2. UltrametricSpace: LCA-based ultrametric distance
  3. StructuralEntropy: depth distribution entropy
  4. StructuralBridge: ds²/ν ↔ ultrametric correlation
  5. GuidedConstructionAuditor: 过渡自限 detection

REF: Rammal et al. 1986 (ultrametricity in spin glasses)
REF: Mézard et al. 1984 (replica symmetry breaking → ultrametric)
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Dict, List, Optional

from .toprxin import TOPRXinSnapshot


# ─────────────────────────────────────────────────────────────────────
# 1. RecursionTracker — structural events as T/O/P/R/Xin cycles
# ─────────────────────────────────────────────────────────────────────

@dataclass
class RecursionCycle:
    """One T/O/P/R/Xin recursive cycle triggered by a structural event.

    A sprout starts a new cycle.
    A prune or apoptosis ends a cycle.
    A mitosis branches a cycle.
    """
    cycle_id: int
    start_tick: int
    end_tick: Optional[int] = None  # None = ongoing
    trigger_event: str = ""         # "sprout", "mitosis"
    entity_id: str = ""             # bundle or neuron ID
    parent_cycle_id: Optional[int] = None  # for nesting
    outcome: str = "ongoing"        # "ongoing", "pruned", "survived", "split"
    # Phase transition log: [(tick, dominant_phase, intensity)]
    phase_log: List[tuple] = field(default_factory=list)
    # Ancestry depth (for ultrametric distance)
    depth: int = 0


class RecursionTracker:
    """Maps structural events to T/O/P/R/Xin recursive cycles.

    Each sprout = new recursion: T(new bundle transmits) → O(target sees new input)
    → P(ξ accumulates) → R(STDP adjusts) → Xin(DA if ξ persists)

    Each prune = recursion ends (outcome: "pruned")
    Each mitosis = recursion branches (new child cycle)

    The ancestry tree of cycles IS the ultrametric space
    described in the Phase 7 candidate math framework.
    """

    def __init__(self):
        self._cycles: Dict[int, RecursionCycle] = {}
        self._entity_to_cycle: Dict[str, int] = {}  # entity_id → cycle_id
        self._next_id: int = 0
        self._completed: List[RecursionCycle] = []

    def on_sprout(self, tick: int, parent_bundle_id: str,
                  child_bundle_id: str) -> int:
        """Record a new sprout event → new recursion cycle."""
        parent_cycle = self._entity_to_cycle.get(parent_bundle_id)
        depth = 0
        if parent_cycle is not None and parent_cycle in self._cycles:
            depth = self._cycles[parent_cycle].depth + 1

        cycle = RecursionCycle(
            cycle_id=self._next_id,
            start_tick=tick,
            trigger_event="sprout",
            entity_id=child_bundle_id,
            parent_cycle_id=parent_cycle,
            depth=depth,
        )
        self._cycles[self._next_id] = cycle
        self._entity_to_cycle[child_bundle_id] = self._next_id
        self._next_id += 1
        return cycle.cycle_id

    def on_prune(self, tick: int, bundle_id: str):
        """Record a prune event → close recursion cycle.

        Orphan handling: if this cycle has active children, re-parent
        them to the grandparent (preserves ancestry chain).
        """
        cid = self._entity_to_cycle.get(bundle_id)
        if cid is not None and cid in self._cycles:
            cycle = self._cycles[cid]
            cycle.end_tick = tick
            cycle.outcome = "pruned"

            # Re-parent orphaned children to grandparent
            grandparent = cycle.parent_cycle_id
            for child_cycle in self._cycles.values():
                if child_cycle.parent_cycle_id == cid:
                    child_cycle.parent_cycle_id = grandparent
                    # Depth decreases by 1 (closer to root)
                    child_cycle.depth = max(0, child_cycle.depth - 1)

            self._completed.append(cycle)
            del self._cycles[cid]
            del self._entity_to_cycle[bundle_id]

    def on_mitosis(self, tick: int, parent_neuron_id: str,
                   child_neuron_id: str) -> int:
        """Record a mitosis event → branch recursion cycle."""
        parent_cycle = self._entity_to_cycle.get(parent_neuron_id)
        depth = 0
        if parent_cycle is not None and parent_cycle in self._cycles:
            depth = self._cycles[parent_cycle].depth + 1

        cycle = RecursionCycle(
            cycle_id=self._next_id,
            start_tick=tick,
            trigger_event="mitosis",
            entity_id=child_neuron_id,
            parent_cycle_id=parent_cycle,
            depth=depth,
        )
        self._cycles[self._next_id] = cycle
        self._entity_to_cycle[child_neuron_id] = self._next_id
        self._next_id += 1
        return cycle.cycle_id

    def update_phases(self, tick: int, toprxin_snap: TOPRXinSnapshot):
        """Update phase log for all active cycles from latest TOPRXin measurement."""
        for cid, cycle in self._cycles.items():
            entity = cycle.entity_id
            bpi = toprxin_snap.bundles.get(entity)
            if bpi is None:
                continue
            # Determine dominant phase
            phases = {
                "T": bpi.t_intensity,
                "O": bpi.o_intensity,
                "P": bpi.p_intensity,
                "R": bpi.r_intensity,
                "Xin": bpi.xin_intensity,
            }
            dominant = max(phases, key=phases.get)
            intensity = phases[dominant]
            cycle.phase_log.append((tick, dominant, round(intensity, 4)))
            # Keep log bounded
            if len(cycle.phase_log) > 100:
                cycle.phase_log.pop(0)

    def summary(self) -> dict:
        """Return summary for monitoring."""
        active = len(self._cycles)
        completed = len(self._completed)
        # Count outcomes
        outcomes = {}
        for c in self._completed:
            outcomes[c.outcome] = outcomes.get(c.outcome, 0) + 1

        # Max depth
        max_depth = 0
        for c in self._cycles.values():
            if c.depth > max_depth:
                max_depth = c.depth

        return {
            "active_cycles": active,
            "completed_cycles": completed,
            "outcomes": outcomes,
            "max_depth": max_depth,
            "total_cycles": self._next_id,
        }

    @property
    def active_cycles(self) -> Dict[int, RecursionCycle]:
        return self._cycles


# ─────────────────────────────────────────────────────────────────────
# 2. UltrametricSpace — Phase 7: candidate math framework
# ─────────────────────────────────────────────────────────────────────

class UltrametricSpace:
    """Ultrametric distance on the recursion ancestry tree.

    Phase 7: Candidate math framework operating at the structural level.
    While ds²/ν describes signal flow WITHIN a fixed structure,
    ultrametric distance describes relationships BETWEEN structural events.

    Distance definition:
        d_u(a, b) = 1 / (1 + depth(LCA(a, b)))

    Where LCA = Lowest Common Ancestor in the recursion tree.

    Properties (strong triangle inequality):
        d_u(a, c) <= max(d_u(a, b), d_u(b, c))

    This is strictly stronger than the Euclidean triangle inequality.
    It means: in this space, ALL triangles are isosceles with the
    unequal side being the shortest. This is the hallmark of tree-like,
    hierarchical structure — exactly what biological development produces.

    REF: Rammal et al. 1986 (ultrametricity in spin glasses)
    REF: Mézard et al. 1984 (replica symmetry breaking → ultrametric)
    """

    def __init__(self, tracker: RecursionTracker):
        self._tracker = tracker

    def _get_all_cycles(self) -> Dict[int, RecursionCycle]:
        """Get all cycles (active + completed)."""
        all_c = dict(self._tracker._cycles)
        for c in self._tracker._completed:
            all_c[c.cycle_id] = c
        return all_c

    def _ancestors(self, cycle_id: int) -> List[int]:
        """Return list of ancestor cycle IDs from root to this cycle."""
        all_c = self._get_all_cycles()
        path = []
        cid = cycle_id
        visited = set()
        while cid is not None and cid not in visited:
            visited.add(cid)
            path.append(cid)
            cycle = all_c.get(cid)
            if cycle is None:
                break
            cid = cycle.parent_cycle_id
        path.reverse()
        return path

    def _lca_depth(self, id_a: int, id_b: int) -> int:
        """Find depth of Lowest Common Ancestor."""
        if id_a == id_b:
            all_c = self._get_all_cycles()
            c = all_c.get(id_a)
            return c.depth if c else 0

        path_a = self._ancestors(id_a)
        path_b = self._ancestors(id_b)

        # Find deepest common prefix
        lca_depth = -1  # no common ancestor
        for i in range(min(len(path_a), len(path_b))):
            if path_a[i] == path_b[i]:
                all_c = self._get_all_cycles()
                c = all_c.get(path_a[i])
                lca_depth = c.depth if c else i
            else:
                break

        return max(0, lca_depth)

    def distance(self, entity_a: str, entity_b: str) -> float:
        """Ultrametric distance between two structural entities.

        Uses entity_id → cycle_id mapping, then computes LCA depth.
        Returns 1.0 if entities share no common ancestor.
        Returns 0.0 if same entity.
        """
        if entity_a == entity_b:
            return 0.0

        cid_a = self._tracker._entity_to_cycle.get(entity_a)
        cid_b = self._tracker._entity_to_cycle.get(entity_b)

        # Check completed cycles too
        if cid_a is None:
            for c in self._tracker._completed:
                if c.entity_id == entity_a:
                    cid_a = c.cycle_id
                    break
        if cid_b is None:
            for c in self._tracker._completed:
                if c.entity_id == entity_b:
                    cid_b = c.cycle_id
                    break

        if cid_a is None or cid_b is None:
            return 1.0  # no ancestry → maximal distance

        lca_d = self._lca_depth(cid_a, cid_b)
        if lca_d < 0:
            return 1.0
        return 1.0 / (1.0 + lca_d)

    def clan(self, entity: str, radius: float) -> List[str]:
        """All entities within ultrametric radius (同族).

        In ultrametric space, balls are either disjoint or nested.
        A clan is a ball: all entities with d_u(entity, x) <= radius.
        """
        members = []
        all_entities = set(self._tracker._entity_to_cycle.keys())
        for c in self._tracker._completed:
            all_entities.add(c.entity_id)

        for other in all_entities:
            if self.distance(entity, other) <= radius:
                members.append(other)
        return members

    def verify_ultrametric(self) -> dict:
        """Verify strong triangle inequality on all triples.

        Returns dict with 'satisfied', 'violations', 'total_triples'.
        """
        all_entities = list(self._tracker._entity_to_cycle.keys())
        for c in self._tracker._completed:
            if c.entity_id not in all_entities:
                all_entities.append(c.entity_id)

        violations = 0
        total = 0
        for i in range(len(all_entities)):
            for j in range(i + 1, len(all_entities)):
                for k in range(j + 1, len(all_entities)):
                    a, b, c = all_entities[i], all_entities[j], all_entities[k]
                    d_ab = self.distance(a, b)
                    d_bc = self.distance(b, c)
                    d_ac = self.distance(a, c)
                    total += 1
                    # Strong triangle: d(a,c) <= max(d(a,b), d(b,c))
                    if d_ac > max(d_ab, d_bc) + 1e-10:
                        violations += 1
                    if d_ab > max(d_ac, d_bc) + 1e-10:
                        violations += 1
                    if d_bc > max(d_ab, d_ac) + 1e-10:
                        violations += 1

        return {
            "satisfied": violations == 0,
            "violations": violations,
            "total_triples": total,
        }

    def summary(self) -> dict:
        """Summary for monitoring."""
        all_c = self._get_all_cycles()
        n = len(all_c)
        if n == 0:
            return {"n_entities": 0, "max_depth": 0}

        depths = [c.depth for c in all_c.values()]
        return {
            "n_entities": n,
            "max_depth": max(depths) if depths else 0,
            "mean_depth": round(sum(depths) / len(depths), 2) if depths else 0,
        }


# ─────────────────────────────────────────────────────────────────────
# 3. StructuralEntropy — tree complexity
# ─────────────────────────────────────────────────────────────────────

class StructuralEntropy:
    """Complexity of the recursion tree.

    Measures how diverse the structural evolution has been.
    High entropy = diverse branching at many depths.
    Low entropy = concentrated at one depth (monotonic growth).

    H_struct = -Σ p_d log₂ p_d

    where p_d = fraction of cycles at depth d.
    """

    def __init__(self, tracker: RecursionTracker):
        self._tracker = tracker
        self._history: List[dict] = []

    def measure(self, tick: int) -> dict:
        """Measure structural entropy at current tick."""
        all_cycles = list(self._tracker._cycles.values())
        all_cycles.extend(self._tracker._completed)

        if not all_cycles:
            result = {"tick": tick, "H_struct": 0.0, "branching": 0.0,
                      "survival": {}, "n_cycles": 0}
            self._history.append(result)
            return result

        # Depth distribution
        depths = [c.depth for c in all_cycles]
        max_depth = max(depths) if depths else 0
        depth_counts = [0] * (max_depth + 1)
        for d in depths:
            depth_counts[d] += 1

        n = len(depths)
        h_struct = 0.0
        for count in depth_counts:
            if count > 0:
                p = count / n
                h_struct -= p * math.log2(p)

        # Branching factor
        children_count = {}
        for c in all_cycles:
            pid = c.parent_cycle_id
            if pid is not None:
                children_count[pid] = children_count.get(pid, 0) + 1
        avg_branch = (sum(children_count.values()) / len(children_count)
                      if children_count else 0.0)

        # Survival rate per depth
        survival = {}
        for d in range(max_depth + 1):
            at_depth = [c for c in all_cycles if c.depth == d]
            if not at_depth:
                continue
            survived = sum(1 for c in at_depth
                          if c.outcome in ("ongoing", "survived", "split"))
            survival[d] = round(survived / len(at_depth), 3)

        # Phase diversity: how many different dominant phases across cycles
        phase_counts = {}
        for c in all_cycles:
            if c.phase_log:
                last_phase = c.phase_log[-1][1]
                phase_counts[last_phase] = phase_counts.get(last_phase, 0) + 1

        result = {
            "tick": tick,
            "H_struct": round(h_struct, 4),
            "branching": round(avg_branch, 2),
            "survival": survival,
            "phase_diversity": phase_counts,
            "n_cycles": len(all_cycles),
            "max_depth": max_depth,
        }

        self._history.append(result)
        if len(self._history) > 200:
            self._history.pop(0)

        return result

    def summary(self) -> dict:
        if not self._history:
            return {"H_struct": 0, "n_cycles": 0}
        return self._history[-1]


# ─────────────────────────────────────────────────────────────────────
# 4. StructuralBridge — ds²/ν ↔ ultrametric
# ─────────────────────────────────────────────────────────────────────

class StructuralBridge:
    """Bridge between ultrametric (structural) and ds²/ν (signal) spaces.

    Core question: does structural proximity (small d_u) predict
    similar signal flow behavior (similar weight changes)?

    If yes → the two mathematical layers are coupled.
    If no → they are independent (and the ultrametric is just a label).

    Measures:
    1. metric_correlation: corr(d_u, |Δw_a - Δw_b|)
       Low d_u + similar Δw = coupled ✓
    2. structural_influence: per-cycle, how much did this event
       change the total weight entropy?
    """

    def __init__(self, ultrametric: UltrametricSpace,
                 tracker: RecursionTracker,
                 entropy_probe: 'WeightEntropyProbe'):
        self._um = ultrametric
        self._tracker = tracker
        self._entropy = entropy_probe
        self._influence_log: List[dict] = []

    def metric_correlation(self, circuit) -> dict:
        """Compute correlation between d_u and weight change similarity."""
        active = self._tracker._cycles
        if len(active) < 2:
            return {"correlation": 0.0, "n_pairs": 0, "message": "too few cycles"}

        pairs_du = []
        pairs_dw = []

        cycle_list = list(active.values())
        for i in range(len(cycle_list)):
            for j in range(i + 1, len(cycle_list)):
                ca, cb = cycle_list[i], cycle_list[j]
                du = self._um.distance(ca.entity_id, cb.entity_id)

                wa = self._find_bundle_weight(circuit, ca.entity_id)
                wb = self._find_bundle_weight(circuit, cb.entity_id)
                if wa is not None and wb is not None:
                    dw = abs(wa - wb)
                    pairs_du.append(du)
                    pairs_dw.append(dw)

        if len(pairs_du) < 2:
            return {"correlation": 0.0, "n_pairs": len(pairs_du),
                    "message": "insufficient pairs"}

        n = len(pairs_du)
        mean_du = sum(pairs_du) / n
        mean_dw = sum(pairs_dw) / n
        cov = sum((pairs_du[k] - mean_du) * (pairs_dw[k] - mean_dw)
                  for k in range(n)) / n
        std_du = math.sqrt(sum((x - mean_du) ** 2 for x in pairs_du) / n)
        std_dw = math.sqrt(sum((x - mean_dw) ** 2 for x in pairs_dw) / n)

        if std_du < 1e-12 or std_dw < 1e-12:
            corr = 0.0
        else:
            corr = cov / (std_du * std_dw)

        return {
            "correlation": round(corr, 4),
            "n_pairs": n,
            "mean_du": round(mean_du, 4),
            "mean_dw": round(mean_dw, 4),
        }

    def structural_influence(self, tick: int) -> dict:
        """Per-cycle: weight entropy change attributed to this structural event."""
        latest_entropy = self._entropy.latest
        if latest_entropy is None:
            return {"tick": tick, "influences": {}}

        delta_s = latest_entropy.delta_entropy
        active = self._tracker._cycles

        total_r = 0.0
        r_per_cycle = {}
        for cid, cycle in active.items():
            if cycle.phase_log:
                last_entry = cycle.phase_log[-1]
                r_per_cycle[cid] = last_entry[2]
                total_r += last_entry[2]

        influences = {}
        for cid, r_val in r_per_cycle.items():
            if total_r > 1e-12:
                influences[cid] = round(delta_s * r_val / total_r, 6)
            else:
                influences[cid] = 0.0

        result = {"tick": tick, "delta_entropy": round(delta_s, 6),
                  "influences": influences}
        self._influence_log.append(result)
        if len(self._influence_log) > 200:
            self._influence_log.pop(0)
        return result

    def _find_bundle_weight(self, circuit, entity_id: str) -> Optional[float]:
        """Find mean weight of a bundle by entity_id."""
        for b in circuit.get_all_bundles():
            if b.id == entity_id:
                return b.mean_weight()
        return None

    def summary(self) -> dict:
        """Summary for monitoring."""
        if not self._influence_log:
            return {"measurements": 0}
        latest = self._influence_log[-1]
        return {
            "measurements": len(self._influence_log),
            "last_delta_entropy": latest.get("delta_entropy", 0),
            "n_influenced": len(latest.get("influences", {})),
        }


# ─────────────────────────────────────────────────────────────────────
# 5. GuidedConstructionAuditor — 引导性构建审计
# ─────────────────────────────────────────────────────────────────────

@dataclass
class SerialModificationLog:
    """Track serial modifications to the same structural pathway.

    When the same pathway receives N consecutive parameter modifications
    without improvement, it triggers GUIDED CONSTRUCTION mode — meaning
    the pathway needs a new differentiated component, not more tuning.

    BIO: serial mutations to the same gene rarely fix the phenotype;
    a new gene (via duplication + divergence) is needed.
    """
    pathway_id: str = ""                # e.g. "shadow_col_to_da"
    modifications: List[dict] = field(default_factory=list)

    def record(self, tick: int, param: str, old_val: float,
               new_val: float, metric_before: float, metric_after: float):
        """Record a parameter modification and its result."""
        improved = metric_after > metric_before
        self.modifications.append({
            "tick": tick,
            "param": param,
            "old": round(old_val, 6),
            "new": round(new_val, 6),
            "metric_before": round(metric_before, 4),
            "metric_after": round(metric_after, 4),
            "improved": improved,
        })
        # Keep last 20 modifications
        if len(self.modifications) > 20:
            self.modifications.pop(0)

    def is_self_limiting(self, threshold: int = 3) -> bool:
        """过渡自限：consecutive N modifications failed to improve.

        When this returns True, the pathway should enter GUIDED
        CONSTRUCTION mode — create a new differentiated component
        rather than continue serial parameter tuning.
        """
        if len(self.modifications) < threshold:
            return False
        recent = self.modifications[-threshold:]
        return all(not m["improved"] for m in recent)


class GuidedConstructionAuditor:
    """Entropy ledger Section 7: 引导性构建审计.

    Rules:
      1. DIFFERENTIATION_REQUIRED: When serial modifications hit
         self-limit (过渡自限), flag that a new differentiated
         component is needed for the pathway.
      2. COMPONENT_LOCALITY: Each structural modification must be
         scoped to a specific component (NeuronConfig flag), not
         applied globally (anti-pattern).
      3. ANCESTRY_TRACKING: New components must declare which
         neuron types they apply to (via use_X config flags).

    This auditor does NOT make structural changes — it only flags
    pathways that need guided construction. The actual construction
    is human-directed.
    """

    def __init__(self):
        self._pathway_logs: Dict[str, SerialModificationLog] = {}
        self._guided_flags: List[dict] = []

    def get_log(self, pathway_id: str) -> SerialModificationLog:
        """Get or create a modification log for a pathway."""
        if pathway_id not in self._pathway_logs:
            self._pathway_logs[pathway_id] = SerialModificationLog(
                pathway_id=pathway_id)
        return self._pathway_logs[pathway_id]

    def check_self_limit(self, pathway_id: str, tick: int) -> bool:
        """Check if a pathway has hit 过渡自限.

        Returns True if guided construction is needed.
        """
        log = self._pathway_logs.get(pathway_id)
        if log is None:
            return False
        if log.is_self_limiting():
            self._guided_flags.append({
                "tick": tick,
                "pathway_id": pathway_id,
                "n_failed_mods": len(log.modifications),
                "action": "DIFFERENTIATION_REQUIRED",
            })
            return True
        return False

    def summary(self) -> dict:
        """Summary for monitoring."""
        return {
            "pathways_tracked": len(self._pathway_logs),
            "guided_flags": len(self._guided_flags),
            "self_limited": [
                pid for pid, log in self._pathway_logs.items()
                if log.is_self_limiting()
            ],
            "recent_flags": self._guided_flags[-5:]
                if self._guided_flags else [],
        }
