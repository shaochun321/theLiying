"""nexus_v1.events — Event-level structure and support binding (P2-B1K0+)."""

from .event_support import (
    EventKernelSpec,
    EventSupportBinding,
    EventInstanceCandidate,
    create_event_candidate,
    EVENT_KERNEL_A_PRECEDES_B_FAST,
    STATUS_CANDIDATE,
    STATUS_REJECTED_INCOMPLETE_SUPPORT,
    STATUS_REJECTED_LINEAGE_MISMATCH,
)

__all__ = [
    "EventKernelSpec",
    "EventSupportBinding",
    "EventInstanceCandidate",
    "create_event_candidate",
    "EVENT_KERNEL_A_PRECEDES_B_FAST",
    "STATUS_CANDIDATE",
    "STATUS_REJECTED_INCOMPLETE_SUPPORT",
    "STATUS_REJECTED_LINEAGE_MISMATCH",
]
