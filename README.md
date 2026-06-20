# VerityLedger

**Know exactly what your AI agent did, and prove nothing was changed after the fact.**

VerityLedger is a small Python library that wraps your agent's tool calls and
decisions in a tamper-evident, hash-chained log. When something goes wrong —
a bad refund, a broken deploy, a strange customer reply — you can pull up the
exact sequence of tool calls, model inputs/outputs, and reasoning that led
there, and prove the record hasn't been altered.

No database. No external service. No blockchain. Just an append-only file
and SHA-256.

```python
from verityledger import Tracer

tracer = Tracer()  # writes to ./verityledger_log.jsonl

with tracer.session(agent="support-bot", user="user_123") as session:

    @session.trace_tool
    def issue_refund(order_id: str, amount: float) -> str:
        return f"refunded {amount} for {order_id}"

    issue_refund("ORD-4471", 42.00)

    session.log_decision(
        "approved refund",
        reasoning="customer reported damaged item, photo provided, within policy",
    )
```

Every call to `issue_refund`, every `log_decision`, and any model calls you
log are written as chained entries — each one includes a hash of the
previous entry. If anyone edits a past entry, the chain breaks at exactly
that point.

## Why this exists

Agents are making real decisions — refunds, emails, code pushes, customer
replies — and most teams have no record of *why* beyond scattered print
statements and provider dashboards. When a regulator, a customer, or your
own team asks "why did the bot do that?", you want an answer that's both
complete and verifiable.

## Install

```bash
pip install verityledger
```

## Verify the chain

```python
valid, break_index = tracer.verify(session.id)
# valid == True, break_index == None  (until someone tampers with the log)

# Or raise on problems:
tracer.assert_valid(session.id)
# raises ChainIntegrityError or SessionNotFoundError
```

## Export an audit report

```python
tracer.export_report(session.id, "incident_report.json")
```

Produces a single JSON file with every entry for that session, plus the
verification result — ready to attach to an incident review or compliance
request.

## CLI

Installing the package also installs a `verityledger` command:

```bash
verityledger sessions                          # list session ids in the log
verityledger show <session_id>                 # print all entries for a session
verityledger verify <session_id>               # check the hash chain for tampering
verityledger export <session_id> report.json   # write a JSON audit report
```

All commands accept `--log PATH` to point at a specific log file
(default: `./verityledger_log.jsonl`).

## Architecture

The library is layered so each piece can be tested and replaced independently:

- **`chain.py`** — the cryptographic primitive. Defines `Entry`, hashing,
  and `verify_chain`. No I/O, no dependencies.
- **`storage/`** — the `Store` interface plus `LocalStore` (append-only
  JSONL). A hosted backend (SQLite/Postgres/API) implements the same
  interface and drops in without touching anything above it.
- **`core.py`** — the public API: `Tracer` and `Session`.
- **`cli/`** — the `verityledger` terminal command. Built entirely on top of
  the public API above; no logic of its own beyond argument parsing
  and output formatting.
- **`exceptions.py`** — shared error types (`StorageError`,
  `ChainIntegrityError`, `SessionNotFoundError`).

## Development

```bash
pip install -e ".[dev]"
ruff check .          # lint
mypy src/verityledger    # strict type check
pytest                # tests + coverage
```

## Status

Early release. The local file-based logger (above) is free and open source
(MIT) — your data never leaves your machine. A hosted dashboard for
searching across sessions, team access, and longer retention is in
development.

## Roadmap

- [x] Hash-chained local logging (Python)
- [x] Tool-call decorator, decision logging, model-call logging
- [x] Tamper detection / chain verification
- [x] Audit report export
- [x] Full test suite, type checking, CI
- [x] CLI (`verityledger sessions/show/verify/export`)
- [ ] JavaScript/TypeScript SDK
- [ ] Hosted dashboard (search, team accounts, retention policies)
- [ ] LangChain / OpenAI / Anthropic tool-use integrations
- [ ] Remote ingestion endpoint (send logs to VerityLedger Cloud)

## License

MIT
