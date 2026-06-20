"""
Hash-chained, tamper-evident log entries.

Each entry includes a hash of the previous entry, forming a chain.
Any modification to a past entry breaks the chain for everything after it,
making tampering detectable without needing a blockchain or external service.

This module has zero dependencies on storage or the public API — it is the
single source of truth for what an "entry" is and how the chain is verified.
"""

from __future__ import annotations

import hashlib
import json
import time
import uuid
from dataclasses import asdict, dataclass, field
from typing import Any

GENESIS_HASH = "0" * 64


def _canonical_json(data: dict[str, Any]) -> str:
    """Serialize a dict deterministically so hashes are reproducible."""
    return json.dumps(data, sort_keys=True, separators=(",", ":"), default=str)


@dataclass(frozen=True)
class Entry:
    """A single chained log entry."""

    id: str
    session_id: str
    timestamp: float
    event_type: str
    data: dict[str, Any]
    previous_hash: str
    hash: str = field(default="")

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, raw: dict[str, Any]) -> Entry:
        return cls(**raw)

    @property
    def content_hash(self) -> str:
        """Hash of this entry's content, excluding the stored `hash` field."""
        content = {k: v for k, v in self.to_dict().items() if k != "hash"}
        return hashlib.sha256(_canonical_json(content).encode("utf-8")).hexdigest()


def make_entry(
    session_id: str,
    event_type: str,
    data: dict[str, Any],
    previous_hash: str,
) -> Entry:
    """
    Build a single chained log entry, with its hash computed and set.

    Args:
        session_id: identifier for the agent run / conversation this belongs to.
        event_type: e.g. "tool_call", "model_call", "decision".
        data: arbitrary JSON-serializable payload for this event.
        previous_hash: hash of the prior entry in this session's chain
                        (use GENESIS_HASH for the first entry).

    Returns:
        A completed, hashed Entry.
    """
    entry = Entry(
        id=str(uuid.uuid4()),
        session_id=session_id,
        timestamp=time.time(),
        event_type=event_type,
        data=data,
        previous_hash=previous_hash,
        hash="",
    )
    return Entry(**{**entry.to_dict(), "hash": entry.content_hash})


def verify_chain(entries: list[Entry]) -> tuple[bool, int | None]:
    """
    Verify a list of entries forms an unbroken, untampered hash chain.

    The list is assumed to be in chronological order for a single session.
    An empty list is considered valid (vacuously).

    Returns:
        (is_valid, index_of_first_break_or_none)
    """
    expected_previous = GENESIS_HASH

    for i, entry in enumerate(entries):
        if entry.previous_hash != expected_previous:
            return False, i

        if entry.content_hash != entry.hash:
            return False, i

        expected_previous = entry.hash

    return True, None
