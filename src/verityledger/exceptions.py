"""
VerityLedger exception hierarchy.

All exceptions raised by this library inherit from VerityLedgerError, so
callers can catch broadly (`except VerityLedgerError`) or narrowly.
"""


class VerityLedgerError(Exception):
    """Base class for all VerityLedger exceptions."""


class StorageError(VerityLedgerError):
    """Raised when a storage backend fails to read or write entries."""


class ChainIntegrityError(VerityLedgerError):
    """Raised when a hash chain is found to be broken or tampered with."""

    def __init__(self, session_id: str, break_index: int):
        self.session_id = session_id
        self.break_index = break_index
        super().__init__(
            f"Hash chain for session '{session_id}' is broken at entry "
            f"index {break_index}."
        )


class SessionNotFoundError(VerityLedgerError):
    """Raised when a requested session has no entries in storage."""

    def __init__(self, session_id: str):
        self.session_id = session_id
        super().__init__(f"No entries found for session '{session_id}'.")
