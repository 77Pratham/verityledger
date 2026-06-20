"""
VerityLedger — public API.

Quickstart:

    from verityledger import Tracer

    tracer = Tracer()  # writes to ./verityledger_log.jsonl by default

    with tracer.session(agent="weather-bot") as session:

        @session.trace_tool
        def get_weather(city: str) -> dict:
            return {"city": city, "forecast": "sunny"}

        result = get_weather("Mumbai")

        session.log_decision(
            "no umbrella needed",
            reasoning="forecast is sunny",
        )

    tracer.export_report(session.id, "report.json")
"""

from __future__ import annotations

import functools
import json
import logging
import time
import uuid
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from typing import Any, TypeVar

from .chain import Entry, make_entry, verify_chain
from .exceptions import ChainIntegrityError, SessionNotFoundError
from .storage import LocalStore, Store

logger = logging.getLogger("verityledger")

F = TypeVar("F", bound=Callable[..., Any])


class Session:
    """A single traced run (e.g. one agent conversation or job)."""

    def __init__(self, tracer: Tracer, session_id: str, metadata: dict[str, Any] | None = None):
        self._tracer = tracer
        self.id = session_id
        if metadata:
            self.log_event("session_start", metadata)

    def log_event(self, event_type: str, data: dict[str, Any]) -> Entry:
        """Log a raw event to this session's chain. Returns the stored entry."""
        store = self._tracer.store
        previous_hash = store.latest_hash(self.id)
        entry = make_entry(self.id, event_type, data, previous_hash)
        store.append(entry)
        logger.debug("logged %s entry for session %s", event_type, self.id)
        return entry

    def log_decision(self, decision: str, reasoning: str | None = None, **extra: Any) -> Entry:
        """Record a decision an agent made, with optional reasoning/context."""
        data: dict[str, Any] = {"decision": decision}
        if reasoning is not None:
            data["reasoning"] = reasoning
        data.update(extra)
        return self.log_event("decision", data)

    def log_model_call(
        self, prompt: Any, response: Any, model: str | None = None, **extra: Any
    ) -> Entry:
        """Record an LLM call's input and output."""
        data: dict[str, Any] = {"prompt": prompt, "response": response}
        if model:
            data["model"] = model
        data.update(extra)
        return self.log_event("model_call", data)

    def trace_tool(self, func: F) -> F:
        """
        Decorator: wraps a tool function so each call (args, result, timing,
        and any exception) is recorded as a tool_call entry.
        """

        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            started = time.monotonic()
            try:
                result = func(*args, **kwargs)
                self.log_event(
                    "tool_call",
                    {
                        "tool": func.__name__,
                        "args": _safe(args),
                        "kwargs": _safe(kwargs),
                        "result": _safe(result),
                        "duration_seconds": time.monotonic() - started,
                        "status": "success",
                    },
                )
                return result
            except Exception as exc:
                self.log_event(
                    "tool_call",
                    {
                        "tool": func.__name__,
                        "args": _safe(args),
                        "kwargs": _safe(kwargs),
                        "error": str(exc),
                        "error_type": type(exc).__name__,
                        "duration_seconds": time.monotonic() - started,
                        "status": "error",
                    },
                )
                raise

        return wrapper  # type: ignore[return-value]


class Tracer:
    """Top-level entry point. Holds the storage backend and creates sessions."""

    def __init__(self, store: Store | None = None, log_path: str = "./verityledger_log.jsonl"):
        self.store: Store = store or LocalStore(log_path)

    @contextmanager
    def session(self, session_id: str | None = None, **metadata: Any) -> Iterator[Session]:
        """
        Context manager that yields a Session with a unique id (auto-generated
        if not provided). Any metadata kwargs are recorded as a session_start event.
        """
        sid = session_id or str(uuid.uuid4())
        session = Session(self, sid, metadata=metadata or None)
        try:
            yield session
        finally:
            session.log_event("session_end", {})

    def verify(self, session_id: str) -> tuple[bool, int | None]:
        """Verify the hash chain for a session is intact (no tampering)."""
        entries = self.store.get_session(session_id)
        return verify_chain(entries)

    def assert_valid(self, session_id: str) -> None:
        """
        Like verify(), but raises instead of returning a tuple.

        Raises:
            SessionNotFoundError: if the session has no entries.
            ChainIntegrityError: if the chain is broken or tampered with.
        """
        entries = self.store.get_session(session_id)
        if not entries:
            raise SessionNotFoundError(session_id)
        valid, break_index = verify_chain(entries)
        if not valid:
            assert break_index is not None
            raise ChainIntegrityError(session_id, break_index)

    def export_report(self, session_id: str, path: str) -> dict[str, Any]:
        """
        Export a JSON audit report for a session: full entry list plus
        a verification result. Returns the report dict and writes it to `path`.

        Raises:
            SessionNotFoundError: if the session has no entries.
        """
        entries = self.store.get_session(session_id)
        if not entries:
            raise SessionNotFoundError(session_id)

        valid, break_index = verify_chain(entries)
        report = {
            "session_id": session_id,
            "entry_count": len(entries),
            "chain_valid": valid,
            "chain_break_index": break_index,
            "entries": [e.to_dict() for e in entries],
        }
        with open(path, "w", encoding="utf-8") as f:
            json.dump(report, f, indent=2, default=str)
        return report


def _safe(value: Any) -> Any:
    """
    Best-effort JSON-safe conversion for log payloads.

    Recurses into lists/tuples/dicts so that a single non-serializable
    object (e.g. a custom class instance) doesn't make the whole
    container fall back to a single opaque repr string.
    """
    if isinstance(value, (list, tuple)):
        return [_safe(v) for v in value]
    if isinstance(value, dict):
        return {str(k): _safe(v) for k, v in value.items()}
    try:
        json.dumps(value)
        return value
    except TypeError:
        return repr(value)
