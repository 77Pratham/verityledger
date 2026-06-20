"""
Local, file-based storage backend.

Free-tier default: an append-only JSONL file. No database required.
Each line is one Entry, serialized as JSON. Append is O(1); reads scan
the file, which is fine for the local/single-developer use case this
backend targets. A SQLite or Postgres backend (for the hosted product)
can implement the same Store interface with indexed lookups.
"""

from __future__ import annotations

import json
import os
from collections.abc import Iterator
from pathlib import Path

from ..chain import Entry
from ..exceptions import StorageError
from .base import Store


class LocalStore(Store):
    """Append-only JSONL store, one file per project/log."""

    def __init__(self, path: str | os.PathLike[str] = "./verityledger_log.jsonl"):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        if not self.path.exists():
            self.path.touch()

    def append(self, entry: Entry) -> None:
        try:
            serialized = json.dumps(entry.to_dict(), default=str)
        except TypeError as exc:
            raise StorageError(f"Entry is not JSON-serializable: {exc}") from exc

        try:
            with open(self.path, "a", encoding="utf-8") as f:
                f.write(serialized + "\n")
        except OSError as exc:
            raise StorageError(f"Failed to write to {self.path}: {exc}") from exc

    def get_session(self, session_id: str) -> list[Entry]:
        return [e for e in self._read_all() if e.session_id == session_id]

    def all_sessions(self) -> list[str]:
        seen: list[str] = []
        for entry in self._read_all():
            if entry.session_id not in seen:
                seen.append(entry.session_id)
        return seen

    def all_entries(self) -> list[Entry]:
        return list(self._read_all())

    def _read_all(self) -> Iterator[Entry]:
        if not self.path.exists():
            return
        try:
            with open(self.path, encoding="utf-8") as f:
                for line_number, line in enumerate(f, start=1):
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        yield Entry.from_dict(json.loads(line))
                    except (json.JSONDecodeError, TypeError) as exc:
                        raise StorageError(
                            f"Corrupt entry at {self.path}:{line_number}: {exc}"
                        ) from exc
        except OSError as exc:
            raise StorageError(f"Failed to read {self.path}: {exc}") from exc
