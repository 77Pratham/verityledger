import json

import pytest

from verityledger.chain import GENESIS_HASH, make_entry
from verityledger.exceptions import StorageError
from verityledger.storage import LocalStore


def test_append_and_get_session(tmp_path):
    store = LocalStore(tmp_path / "log.jsonl")
    e1 = make_entry("s1", "decision", {"x": 1}, GENESIS_HASH)
    e2 = make_entry("s1", "decision", {"x": 2}, e1.hash)
    e3 = make_entry("s2", "decision", {"x": 3}, GENESIS_HASH)

    store.append(e1)
    store.append(e2)
    store.append(e3)

    s1_entries = store.get_session("s1")
    assert [e.data["x"] for e in s1_entries] == [1, 2]

    s2_entries = store.get_session("s2")
    assert [e.data["x"] for e in s2_entries] == [3]


def test_latest_hash_returns_genesis_for_new_session(tmp_path):
    store = LocalStore(tmp_path / "log.jsonl")
    assert store.latest_hash("never-seen") == GENESIS_HASH


def test_latest_hash_returns_last_entry_hash(tmp_path):
    store = LocalStore(tmp_path / "log.jsonl")
    e1 = make_entry("s1", "decision", {"x": 1}, GENESIS_HASH)
    e2 = make_entry("s1", "decision", {"x": 2}, e1.hash)
    store.append(e1)
    store.append(e2)

    assert store.latest_hash("s1") == e2.hash


def test_all_sessions_preserves_first_seen_order(tmp_path):
    store = LocalStore(tmp_path / "log.jsonl")
    store.append(make_entry("a", "decision", {}, GENESIS_HASH))
    store.append(make_entry("b", "decision", {}, GENESIS_HASH))
    store.append(make_entry("a", "decision", {}, GENESIS_HASH))

    assert store.all_sessions() == ["a", "b"]


def test_creates_parent_directories(tmp_path):
    path = tmp_path / "nested" / "dir" / "log.jsonl"
    LocalStore(path)
    assert path.exists()


def test_corrupt_line_raises_storage_error(tmp_path):
    path = tmp_path / "log.jsonl"
    path.write_text("not valid json\n")

    store = LocalStore(path)
    with pytest.raises(StorageError):
        store.all_entries()


def test_entries_persisted_as_jsonl(tmp_path):
    path = tmp_path / "log.jsonl"
    store = LocalStore(path)
    store.append(make_entry("s1", "decision", {"x": 1}, GENESIS_HASH))

    lines = path.read_text().strip().splitlines()
    assert len(lines) == 1
    parsed = json.loads(lines[0])
    assert parsed["session_id"] == "s1"


def test_blank_lines_in_log_file_are_skipped(tmp_path):
    path = tmp_path / "log.jsonl"
    store = LocalStore(path)
    store.append(make_entry("s1", "decision", {"x": 1}, GENESIS_HASH))

    # Manually add trailing blank lines, as might happen with manual edits
    with open(path, "a") as f:
        f.write("\n\n")

    entries = store.all_entries()
    assert len(entries) == 1
