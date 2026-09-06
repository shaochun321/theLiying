"""tss.events — Event-level structure and support binding (P2-B1X+)."""

from .event_support import (
    EventKernelSpec,
    EventSupportBinding,
    EventInstanceCandidate,
    create_event_candidate,
    RELATION_LINEAGE_A_PRECEDES_B_FAST,
    STATUS_CANDIDATE,
    STATUS_REJECTED_INCOMPLETE_SUPPORT,
    STATUS_REJECTED_LINEAGE_MISMATCH,
)

__all__ = [
    "EventKernelSpec",
    "EventSupportBinding",
    "EventInstanceCandidate",
    "create_event_candidate",
    "RELATION_LINEAGE_A_PRECEDES_B_FAST",
    "STATUS_CANDIDATE",
    "STATUS_REJECTED_INCOMPLETE_SUPPORT",
    "STATUS_REJECTED_LINEAGE_MISMATCH",
]
