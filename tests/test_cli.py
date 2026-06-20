import json

from verityledger import Tracer
from verityledger.cli import main


def _make_session(tmp_path):
    log_path = tmp_path / "log.jsonl"
    tracer = Tracer(log_path=log_path)
    with tracer.session(agent="cli-test") as session:
        session.log_decision("approve", reasoning="within policy")
    return log_path, session.id


def test_sessions_command_lists_session_ids(tmp_path, capsys):
    log_path, session_id = _make_session(tmp_path)

    exit_code = main(["--log", str(log_path), "sessions"])

    out = capsys.readouterr().out
    assert exit_code == 0
    assert session_id in out


def test_sessions_command_handles_empty_log(tmp_path, capsys):
    log_path = tmp_path / "empty.jsonl"
    Tracer(log_path=log_path)  # creates the file

    exit_code = main(["--log", str(log_path), "sessions"])

    out = capsys.readouterr().out
    assert exit_code == 0
    assert "No sessions found" in out


def test_show_command_prints_entries(tmp_path, capsys):
    log_path, session_id = _make_session(tmp_path)

    exit_code = main(["--log", str(log_path), "show", session_id])

    out = capsys.readouterr().out
    assert exit_code == 0
    assert "decision" in out
    assert "approve" in out


def test_show_command_unknown_session_returns_error(tmp_path, capsys):
    log_path = tmp_path / "log.jsonl"
    Tracer(log_path=log_path)

    exit_code = main(["--log", str(log_path), "show", "nonexistent"])

    err = capsys.readouterr().err
    assert exit_code == 1
    assert "No entries found" in err


def test_verify_command_passes_for_clean_chain(tmp_path, capsys):
    log_path, session_id = _make_session(tmp_path)

    exit_code = main(["--log", str(log_path), "verify", session_id])

    out = capsys.readouterr().out
    assert exit_code == 0
    assert "Chain valid" in out


def test_verify_command_detects_tampering(tmp_path, capsys):
    log_path, session_id = _make_session(tmp_path)

    lines = log_path.read_text().strip().splitlines()
    tampered = []
    for line in lines:
        entry = json.loads(line)
        if entry["data"].get("decision") == "approve":
            entry["data"]["decision"] = "DENY"
        tampered.append(json.dumps(entry))
    log_path.write_text("\n".join(tampered) + "\n")

    exit_code = main(["--log", str(log_path), "verify", session_id])

    err = capsys.readouterr().err
    assert exit_code == 1
    assert "TAMPERING DETECTED" in err


def test_verify_command_unknown_session_returns_error(tmp_path, capsys):
    log_path = tmp_path / "log.jsonl"
    Tracer(log_path=log_path)

    exit_code = main(["--log", str(log_path), "verify", "nonexistent"])

    assert exit_code == 1


def test_export_command_writes_report(tmp_path, capsys):
    log_path, session_id = _make_session(tmp_path)
    out_path = tmp_path / "report.json"

    exit_code = main(["--log", str(log_path), "export", session_id, str(out_path)])

    out = capsys.readouterr().out
    assert exit_code == 0
    assert "Exported" in out
    assert out_path.exists()

    report = json.loads(out_path.read_text())
    assert report["session_id"] == session_id
    assert report["chain_valid"] is True


def test_export_command_unknown_session_returns_error(tmp_path, capsys):
    log_path = tmp_path / "log.jsonl"
    Tracer(log_path=log_path)
    out_path = tmp_path / "report.json"

    exit_code = main(["--log", str(log_path), "export", "nonexistent", str(out_path)])

    assert exit_code == 1
    assert not out_path.exists()
