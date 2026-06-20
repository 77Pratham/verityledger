import json

import pytest

from verityledger import ChainIntegrityError, SessionNotFoundError, Tracer


def test_session_records_start_and_end_events(tmp_path):
    tracer = Tracer(log_path=tmp_path / "log.jsonl")
    with tracer.session(agent="test-bot") as session:
        pass

    entries = tracer.store.get_session(session.id)
    assert entries[0].event_type == "session_start"
    assert entries[0].data == {"agent": "test-bot"}
    assert entries[-1].event_type == "session_end"


def test_session_without_metadata_has_no_start_event(tmp_path):
    tracer = Tracer(log_path=tmp_path / "log.jsonl")
    with tracer.session() as session:
        pass

    entries = tracer.store.get_session(session.id)
    assert len(entries) == 1
    assert entries[0].event_type == "session_end"


def test_log_decision(tmp_path):
    tracer = Tracer(log_path=tmp_path / "log.jsonl")
    with tracer.session() as session:
        session.log_decision("approve", reasoning="within policy", amount=42)

    entries = tracer.store.get_session(session.id)
    decision = next(e for e in entries if e.event_type == "decision")
    assert decision.data == {
        "decision": "approve",
        "reasoning": "within policy",
        "amount": 42,
    }


def test_log_model_call(tmp_path):
    tracer = Tracer(log_path=tmp_path / "log.jsonl")
    with tracer.session() as session:
        session.log_model_call(prompt="hi", response="hello", model="claude-sonnet-4-6")

    entries = tracer.store.get_session(session.id)
    call = next(e for e in entries if e.event_type == "model_call")
    assert call.data["prompt"] == "hi"
    assert call.data["response"] == "hello"
    assert call.data["model"] == "claude-sonnet-4-6"


def test_trace_tool_records_success(tmp_path):
    tracer = Tracer(log_path=tmp_path / "log.jsonl")
    with tracer.session() as session:

        @session.trace_tool
        def add(a, b):
            return a + b

        result = add(1, 2)
        assert result == 3

    entries = tracer.store.get_session(session.id)
    call = next(e for e in entries if e.event_type == "tool_call")
    assert call.data["tool"] == "add"
    assert call.data["args"] == [1, 2]
    assert call.data["result"] == 3
    assert call.data["status"] == "success"


def test_trace_tool_records_errors_and_reraises(tmp_path):
    tracer = Tracer(log_path=tmp_path / "log.jsonl")
    with tracer.session() as session:

        @session.trace_tool
        def divide(a, b):
            return a / b

        with pytest.raises(ZeroDivisionError):
            divide(1, 0)

    entries = tracer.store.get_session(session.id)
    call = next(e for e in entries if e.event_type == "tool_call")
    assert call.data["status"] == "error"
    assert call.data["error_type"] == "ZeroDivisionError"


def test_verify_returns_true_for_untouched_session(tmp_path):
    tracer = Tracer(log_path=tmp_path / "log.jsonl")
    with tracer.session() as session:
        session.log_decision("ok")

    valid, break_index = tracer.verify(session.id)
    assert valid is True
    assert break_index is None


def test_assert_valid_raises_for_unknown_session(tmp_path):
    tracer = Tracer(log_path=tmp_path / "log.jsonl")
    with pytest.raises(SessionNotFoundError):
        tracer.assert_valid("does-not-exist")


def test_assert_valid_raises_on_tampering(tmp_path):
    path = tmp_path / "log.jsonl"
    tracer = Tracer(log_path=path)
    with tracer.session() as session:
        session.log_decision("approve refund", amount=42)

    # Tamper with the file directly
    lines = path.read_text().strip().splitlines()
    tampered = []
    for line in lines:
        entry = json.loads(line)
        if entry["data"].get("decision") == "approve refund":
            entry["data"]["amount"] = 4200
        tampered.append(json.dumps(entry))
    path.write_text("\n".join(tampered) + "\n")

    with pytest.raises(ChainIntegrityError):
        tracer.assert_valid(session.id)


def test_export_report(tmp_path):
    tracer = Tracer(log_path=tmp_path / "log.jsonl")
    with tracer.session() as session:
        session.log_decision("ok")

    report_path = tmp_path / "report.json"
    report = tracer.export_report(session.id, str(report_path))

    assert report["session_id"] == session.id
    assert report["chain_valid"] is True
    assert report_path.exists()

    on_disk = json.loads(report_path.read_text())
    assert on_disk == report


def test_export_report_raises_for_unknown_session(tmp_path):
    tracer = Tracer(log_path=tmp_path / "log.jsonl")
    with pytest.raises(SessionNotFoundError):
        tracer.export_report("does-not-exist", str(tmp_path / "report.json"))


def test_unjsonable_args_are_safely_repr_d(tmp_path):
    tracer = Tracer(log_path=tmp_path / "log.jsonl")
    with tracer.session() as session:

        @session.trace_tool
        def takes_object(obj):
            return "ok"

        class Unserializable:
            def __repr__(self):
                return "<Unserializable>"

        takes_object(Unserializable())

    entries = tracer.store.get_session(session.id)
    call = next(e for e in entries if e.event_type == "tool_call")
    assert call.data["args"] == ["<Unserializable>"]
