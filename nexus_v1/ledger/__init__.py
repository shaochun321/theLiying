"""nexus_v1.ledger — Unified thermodynamic & information-theoretic bookkeeping.

All classes in this package are READ-ONLY observers. They NEVER modify
circuit state. Their role is accounting, verification, and diagnostics.

Architecture:
  - weight_entropy.py:  WeightEntropyProbe (Shannon entropy of weights)
  - toprxin.py:         TOPRXinLedger (phase intensities per bundle)
  - structural.py:      RecursionTracker, UltrametricSpace, StructuralEntropy,
                        StructuralBridge, GuidedConstructionAuditor
  - energy_ledger.py:   EntropyLedger (global energy/heat/spike accounting)
  - noether_probe.py:   NoetherProbe (conservation law verification)

REF: Jaynes 1957 (MaxEnt), Landauer 1961 (erasure bound)
REF: Attwell & Laughlin 2001 (energy budget for cortical signaling)
"""

from .weight_entropy import WeightEntropyProbe, EntropySnapshot
from .toprxin import TOPRXinLedger, TOPRXinSnapshot, BundlePhaseIntensity, RhoVector
from .structural import (RecursionTracker, RecursionCycle,
                         UltrametricSpace, StructuralEntropy, StructuralBridge,
                         SerialModificationLog, GuidedConstructionAuditor)
from .energy_ledger import EntropyLedger
from .noether_probe import NoetherProbe

__all__ = [
    'WeightEntropyProbe', 'EntropySnapshot',
    'TOPRXinLedger', 'TOPRXinSnapshot', 'BundlePhaseIntensity', 'RhoVector',
    'RecursionTracker', 'RecursionCycle',
    'UltrametricSpace', 'StructuralEntropy', 'StructuralBridge',
    'SerialModificationLog', 'GuidedConstructionAuditor',
    'EntropyLedger',
    'NoetherProbe',
]
