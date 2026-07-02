"""nexus_v1.ledger.component_registry — Runtime Component Registry.

TYPE:INFRA — Scans all live objects in a VariantCircuit instance,
reads TYPE tags from class docstrings, and reports census visibility,
activity levels, and hidden/idle components.

Pattern-1 ledger style: __init__() no args; scan(circuit, tick);
summary()→dict; print_report().

Pure observer — reads circuit state, NEVER writes.
"""

from __future__ import annotations

import inspect
import re
from dataclasses import dataclass, field
from typing import Dict, List, Optional


# ─────────────────────────────────────────────────────────────
# Data structures
# ─────────────────────────────────────────────────────────────

@dataclass
class ComponentEntry:
    """TYPE:INFRA — One row in the component registry."""
    name: str           # attribute path (e.g. "shadow_sandbox.neurons.s_col_yaw")
    class_name: str     # type(obj).__name__
    source_file: str    # "nexus_v1/...file.py:lineno"
    type_tag: str       # BIO / SEMI / MATH / HYBRID / INFRA / UNTAGGED
    census_visible: bool  # True if in get_all_neurons() or get_all_bundles()
    kind: str           # "neuron" | "bundle" | "physics" | "ledger" | "other"
    idle: bool          # activity below threshold
    activity: float     # quantitative activity level (activation or mean_weight)


# ─────────────────────────────────────────────────────────────
# ComponentRegistry
# ─────────────────────────────────────────────────────────────

class ComponentRegistry:
    """TYPE:INFRA — Runtime registry of all live components in a VariantCircuit.

    Covers census objects (get_all_neurons / get_all_bundles) PLUS all
    non-census physics components, shadow internals, and ledger objects.
    TYPE tags are read automatically from class docstring first lines.

    Usage:
        registry = ComponentRegistry()
        registry.scan(circuit, tick)
        registry.print_report()
    """

    IDLE_NEURON_THRESHOLD = 1e-6   # |activation| below this → idle
    IDLE_BUNDLE_THRESHOLD = 1e-4   # mean_weight below this → idle

    def __init__(self):
        self._entries: List[ComponentEntry] = []
        self._last_tick: int = 0

    @property
    def latest(self) -> List[ComponentEntry]:
        return self._entries

    # ── Public API ────────────────────────────────────────────

    def scan(self, circuit, tick: int = 0) -> List[ComponentEntry]:
        """Scan all live components and build registry.

        Args:
            circuit: VariantCircuit instance (read-only).
            tick: current tick number.

        Returns:
            List[ComponentEntry], one per discovered object.
        """
        self._last_tick = tick
        entries: List[ComponentEntry] = []

        # ── 1. Census-visible neurons ──────────────────────────
        census_neuron_ids: set = set()
        for n in circuit.get_all_neurons():
            census_neuron_ids.add(id(n))
            act = abs(n.activation)
            entries.append(ComponentEntry(
                name=f"census.{n.id}",
                class_name=type(n).__name__,
                source_file=self._source_loc(type(n)),
                type_tag=self._get_type(type(n)),
                census_visible=True,
                kind="neuron",
                idle=act < self.IDLE_NEURON_THRESHOLD,
                activity=act,
            ))

        # ── 2. Census-visible bundles ──────────────────────────
        census_bundle_ids: set = set()
        for b in circuit.get_all_bundles():
            census_bundle_ids.add(id(b))
            w = b.mean_weight()
            entries.append(ComponentEntry(
                name=f"census.{b.id}",
                class_name=type(b).__name__,
                source_file=self._source_loc(type(b)),
                type_tag=self._get_type(type(b)),
                census_visible=True,
                kind="bundle",
                idle=w < self.IDLE_BUNDLE_THRESHOLD,
                activity=w,
            ))

        # ── 3. Shadow sandbox hidden neurons + bundles ─────────
        ss = getattr(circuit, 'shadow_sandbox', None)
        if ss is not None:
            for nid, n in getattr(ss, 'neurons', {}).items():
                if id(n) not in census_neuron_ids:
                    act = abs(n.activation)
                    entries.append(ComponentEntry(
                        name=f"shadow_sandbox.neurons.{nid}",
                        class_name=type(n).__name__,
                        source_file=self._source_loc(type(n)),
                        type_tag=self._get_type(type(n)),
                        census_visible=False,
                        kind="neuron",
                        idle=act < self.IDLE_NEURON_THRESHOLD,
                        activity=act,
                    ))
            for bid, b in getattr(ss, 'bundles', {}).items():
                if id(b) not in census_bundle_ids:
                    w = b.mean_weight()
                    entries.append(ComponentEntry(
                        name=f"shadow_sandbox.bundles.{bid}",
                        class_name=type(b).__name__,
                        source_file=self._source_loc(type(b)),
                        type_tag=self._get_type(type(b)),
                        census_visible=False,
                        kind="bundle",
                        idle=w < self.IDLE_BUNDLE_THRESHOLD,
                        activity=w,
                    ))
            # Shadow ECM + vascular
            for attr, label in [('ecm_enc', 'shadow_sandbox.ecm_enc'),
                                 ('ecm_col', 'shadow_sandbox.ecm_col'),
                                 ('ecm_mot', 'shadow_sandbox.ecm_mot'),
                                 ('vascular', 'shadow_sandbox.vascular')]:
                obj = getattr(ss, attr, None)
                if obj is not None:
                    entries.append(ComponentEntry(
                        name=label,
                        class_name=type(obj).__name__,
                        source_file=self._source_loc(type(obj)),
                        type_tag=self._get_type(type(obj)),
                        census_visible=False,
                        kind="physics",
                        idle=False,
                        activity=0.0,
                    ))

        # ── 4. Top-level physics / support objects ─────────────
        _physics_attrs = [
            'ecm_vestibular', 'ecm_encoding', 'ecm_column',
            'vascular', 'world', 'thermal_membrane', 'muscle_system',
            'somatosensory', 'energy_store', 'yolk_sac', 'da_gate',
            'vital_oscillator', 'spinal_reflex', 'agc', 'dopamine',
            'binding_layer', 'lateral_inhibition', 'motor_lateral_inhibition',
            'circulation_proportion', '_langevin', 'shadow_sandbox',
        ]
        for attr in _physics_attrs:
            obj = getattr(circuit, attr, None)
            if obj is None:
                continue
            entries.append(ComponentEntry(
                name=attr,
                class_name=type(obj).__name__,
                source_file=self._source_loc(type(obj)),
                type_tag=self._get_type(type(obj)),
                census_visible=False,
                kind="physics",
                idle=False,
                activity=0.0,
            ))

        # ── 5. Dict-valued physics containers (per-axis) ───────
        _dict_attrs = [
            'dampers_enc', 'dampers_col', 'ndr_afferent', 'routers_enc_col',
        ]
        for attr in _dict_attrs:
            d = getattr(circuit, attr, None)
            if not isinstance(d, dict):
                continue
            for k, obj in d.items():
                if obj is None:
                    continue
                entries.append(ComponentEntry(
                    name=f"{attr}.{k}",
                    class_name=type(obj).__name__,
                    source_file=self._source_loc(type(obj)),
                    type_tag=self._get_type(type(obj)),
                    census_visible=False,
                    kind="physics",
                    idle=False,
                    activity=0.0,
                ))

        # ── 6. Ledger / observability objects ──────────────────
        _ledger_attrs = [
            '_entropy_probe', '_toprxin_ledger', '_recursion_tracker',
            '_ultrametric', '_structural_entropy', '_structural_bridge',
            '_noether_probe', '_energy_ledger', '_circulation_meter',
        ]
        for attr in _ledger_attrs:
            obj = getattr(circuit, attr, None)
            if obj is None:
                continue
            entries.append(ComponentEntry(
                name=attr,
                class_name=type(obj).__name__,
                source_file=self._source_loc(type(obj)),
                type_tag=self._get_type(type(obj)),
                census_visible=False,
                kind="ledger",
                idle=False,
                activity=0.0,
            ))

        self._entries = entries
        return entries

    def summary(self) -> dict:
        """Return structured summary dict."""
        if not self._entries:
            return {'scanned': False}

        by_type: Dict[str, int] = {}
        for e in self._entries:
            by_type[e.type_tag] = by_type.get(e.type_tag, 0) + 1

        census_count = sum(1 for e in self._entries if e.census_visible)
        hidden_count = sum(1 for e in self._entries if not e.census_visible)
        idle_count = sum(1 for e in self._entries if e.idle)
        hidden_neural = [e for e in self._entries
                         if not e.census_visible and e.kind in ('neuron', 'bundle')]

        return {
            'tick': self._last_tick,
            'total': len(self._entries),
            'by_type': by_type,
            'census_visible': census_count,
            'hidden': hidden_count,
            'idle': idle_count,
            'untagged': by_type.get('UNTAGGED', 0),
            'hidden_neural_count': len(hidden_neural),
        }

    def print_report(self):
        """Print formatted component registry report to stdout."""
        if not self._entries:
            print("ComponentRegistry: not yet scanned.")
            return

        print("=" * 80)
        print(f"COMPONENT REGISTRY  (tick={self._last_tick})")
        print("=" * 80)

        s = self.summary()
        print(f"\nTotal: {s['total']}  |  Census: {s['census_visible']}  |  "
              f"Hidden: {s['hidden']}  |  Idle: {s['idle']}  |  Untagged: {s['untagged']}")

        print("\n-- TYPE distribution --")
        for tag, count in sorted(s['by_type'].items()):
            print(f"  {tag:10s}: {count:3d}  {'#' * count}")

        hidden_neural = [e for e in self._entries
                         if not e.census_visible and e.kind in ('neuron', 'bundle')]
        if hidden_neural:
            print(f"\n-- Hidden neurons/bundles ({len(hidden_neural)}) --")
            for e in hidden_neural:
                idle_marker = " [IDLE]" if e.idle else ""
                print(f"  {e.name:50s}  {e.type_tag:6s}  act={e.activity:.4f}{idle_marker}")

        idle_census = [e for e in self._entries if e.idle and e.census_visible]
        if idle_census:
            print(f"\n-- Idle census items ({len(idle_census)}) --")
            for e in idle_census:
                print(f"  {e.name:50s}  {e.type_tag:6s}  act={e.activity:.4f}")

        physics = [e for e in self._entries
                   if e.kind == 'physics' and not e.census_visible]
        if physics:
            print(f"\n-- Physics support ({len(physics)}) --")
            for e in physics:
                print(f"  {e.name:50s}  {e.type_tag:6s}  {e.class_name}")

        ledgers = [e for e in self._entries if e.kind == 'ledger']
        if ledgers:
            print(f"\n-- Ledger/observability ({len(ledgers)}) --")
            for e in ledgers:
                print(f"  {e.name:50s}  {e.type_tag:6s}  {e.class_name}")

        untagged = [e for e in self._entries if e.type_tag == 'UNTAGGED']
        if untagged:
            print(f"\n-- UNTAGGED ({len(untagged)}) --")
            for e in untagged:
                print(f"  {e.name:50s}  {e.source_file}")
        else:
            print("\n  [OK] All components are tagged.")

        print("=" * 80)

    # ── Internal helpers ──────────────────────────────────────

    @staticmethod
    def _get_type(cls) -> str:
        """Extract TYPE:XXX from class docstring first line."""
        doc = inspect.getdoc(cls)
        if not doc:
            return "UNTAGGED"
        first_line = doc.split('\n')[0].strip()
        m = re.match(r'TYPE:(\w+)', first_line)
        return m.group(1) if m else "UNTAGGED"

    @staticmethod
    def _source_loc(cls) -> str:
        """Return 'nexus_v1/.../file.py:lineno' for a class."""
        try:
            src = inspect.getsourcefile(cls) or "?"
            _, lineno = inspect.getsourcelines(cls)
            src = src.replace('\\', '/')
            idx = src.find('nexus_v1')
            if idx >= 0:
                src = src[idx:]
            return f"{src}:{lineno}"
        except (OSError, TypeError):
            return "?:?"
