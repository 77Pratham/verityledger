"""
VerityLedger CLI.

Lets you inspect, verify, and export logs from the terminal without
writing any Python. Built entirely on top of the public `verityledger`
API (Tracer/LocalStore) - the CLI has no logic of its own beyond
argument parsing and formatting.

Usage:
    verityledger sessions [--log PATH]
    verityledger show SESSION_ID [--log PATH]
    verityledger verify SESSION_ID [--log PATH]
    verityledger export SESSION_ID OUT_PATH [--log PATH]
"""

from __future__ import annotations

import argparse
import sys
from datetime import datetime, timezone

from ..core import Tracer
from ..exceptions import ChainIntegrityError, SessionNotFoundError, VerityLedgerError

DEFAULT_LOG_PATH = "./verityledger_log.jsonl"


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="verityledger",
        description="Inspect, verify, and export VerityLedger agent logs.",
    )
    parser.add_argument(
        "--log",
        default=DEFAULT_LOG_PATH,
        help=f"Path to the log file (default: {DEFAULT_LOG_PATH})",
    )

    subparsers = parser.add_subparsers(dest="command", required=True)

    subparsers.add_parser("sessions", help="List all session ids in the log.")

    show = subparsers.add_parser("show", help="Print all entries for a session.")
    show.add_argument("session_id")

    verify = subparsers.add_parser("verify", help="Check a session's hash chain for tampering.")
    verify.add_argument("session_id")

    export = subparsers.add_parser("export", help="Export a session as a JSON audit report.")
    export.add_argument("session_id")
    export.add_argument("out_path")

    return parser


def _format_timestamp(ts: float) -> str:
    return datetime.fromtimestamp(ts, tz=timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")


def cmd_sessions(tracer: Tracer) -> int:
    sessions = tracer.store.all_sessions()
    if not sessions:
        print("No sessions found.")
        return 0
    for sid in sessions:
        count = len(tracer.store.get_session(sid))
        print(f"{sid}  ({count} entries)")
    return 0


def cmd_show(tracer: Tracer, session_id: str) -> int:
    entries = tracer.store.get_session(session_id)
    if not entries:
        print(f"No entries found for session '{session_id}'.", file=sys.stderr)
        return 1
    for entry in entries:
        print(f"[{_format_timestamp(entry.timestamp)}] {entry.event_type}")
        for key, value in entry.data.items():
            print(f"    {key}: {value}")
        print(f"    hash: {entry.hash[:12]}...")
    return 0


def cmd_verify(tracer: Tracer, session_id: str) -> int:
    try:
        tracer.assert_valid(session_id)
    except SessionNotFoundError as exc:
        print(str(exc), file=sys.stderr)
        return 1
    except ChainIntegrityError as exc:
        print(f"TAMPERING DETECTED: {exc}", file=sys.stderr)
        return 1

    entry_count = len(tracer.store.get_session(session_id))
    print(f"Chain valid: {entry_count} entries, no tampering detected.")
    return 0


def cmd_export(tracer: Tracer, session_id: str, out_path: str) -> int:
    try:
        report = tracer.export_report(session_id, out_path)
    except SessionNotFoundError as exc:
        print(str(exc), file=sys.stderr)
        return 1

    status = "valid" if report["chain_valid"] else "TAMPERED"
    print(f"Exported {report['entry_count']} entries to {out_path} (chain: {status}).")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)
    tracer = Tracer(log_path=args.log)

    try:
        if args.command == "sessions":
            return cmd_sessions(tracer)
        if args.command == "show":
            return cmd_show(tracer, args.session_id)
        if args.command == "verify":
            return cmd_verify(tracer, args.session_id)
        if args.command == "export":
            return cmd_export(tracer, args.session_id, args.out_path)
    except VerityLedgerError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1

    parser.print_help()
    return 1


if __name__ == "__main__":
    sys.exit(main())
