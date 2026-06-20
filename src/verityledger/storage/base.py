"""
Storage interface.

Any backend (local file, SQLite, Postgres, hosted API) implements this
protocol. The rest of the library only depends on this interface, never
on a concrete backend - that's what lets a hosted "VerityLedger Cloud" store
be dropped in later with zero changes to chain.py or core.py.
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from ..chain import GENESIS_HASH, Entry


class Store(ABC):
    """Abstract base class for VerityLedger storage backends."""

    @abstractmethod
    def append(self, entry: Entry) -> None:
        """Persist a single entry. Must preserve insertion order."""

    @abstractmethod
    def get_session(self, session_id: str) -> list[Entry]:
        """Return all entries for a session, in the order they were written."""

    @abstractmethod
    def all_sessions(self) -> list[str]:
        """Return distinct session ids, in first-seen order."""

    @abstractmethod
    def all_entries(self) -> list[Entry]:
        """Return every entry across all sessions, in insertion order."""

    def latest_hash(self, session_id: str) -> str:
        """
        Return the hash of the most recent entry for a session, or
        GENESIS_HASH if the session has no entries yet.

        Backends may override this with a more efficient implementation
        (e.g. an indexed query) - the default just scans get_session().
        """
        entries = self.get_session(session_id)
        return entries[-1].hash if entries else GENESIS_HASH
