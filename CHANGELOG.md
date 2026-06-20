# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/).

## [0.1.0] - Unreleased

### Added
- Hash-chained `Entry` model and `verify_chain` (`verityledger.chain`).
- `Store` interface and `LocalStore` (append-only JSONL) backend.
- `Tracer` / `Session` public API: `log_event`, `log_decision`,
  `log_model_call`, `trace_tool` decorator.
- `verify()` and `assert_valid()` for chain integrity checks.
- `export_report()` for JSON audit report generation.
- Exception hierarchy: `VerityLedgerError`, `StorageError`,
  `ChainIntegrityError`, `SessionNotFoundError`.
- Full test suite (pytest), strict type checking (mypy), linting (ruff),
  and CI across Python 3.10-3.12.
- `py.typed` marker for downstream type checking.
