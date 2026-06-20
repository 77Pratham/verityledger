from verityledger.chain import GENESIS_HASH, Entry, make_entry, verify_chain


def test_make_entry_sets_hash_and_links_to_previous():
    entry = make_entry("s1", "decision", {"x": 1}, GENESIS_HASH)
    assert entry.previous_hash == GENESIS_HASH
    assert entry.hash == entry.content_hash
    assert len(entry.hash) == 64  # sha256 hex digest


def test_chain_of_entries_is_valid():
    e1 = make_entry("s1", "decision", {"x": 1}, GENESIS_HASH)
    e2 = make_entry("s1", "decision", {"x": 2}, e1.hash)
    e3 = make_entry("s1", "decision", {"x": 3}, e2.hash)

    valid, break_index = verify_chain([e1, e2, e3])

    assert valid is True
    assert break_index is None


def test_empty_chain_is_valid():
    valid, break_index = verify_chain([])
    assert valid is True
    assert break_index is None


def test_first_entry_must_link_to_genesis():
    bad_first = make_entry("s1", "decision", {"x": 1}, "not-genesis")
    valid, break_index = verify_chain([bad_first])
    assert valid is False
    assert break_index == 0


def test_tampering_with_entry_data_breaks_chain():
    e1 = make_entry("s1", "decision", {"amount": 42}, GENESIS_HASH)
    e2 = make_entry("s1", "decision", {"amount": 1}, e1.hash)

    # Simulate an attacker editing e1's data without recomputing its hash
    tampered_e1 = Entry(**{**e1.to_dict(), "data": {"amount": 4200}})

    valid, break_index = verify_chain([tampered_e1, e2])

    assert valid is False
    assert break_index == 0


def test_reordering_entries_breaks_chain():
    e1 = make_entry("s1", "decision", {"x": 1}, GENESIS_HASH)
    e2 = make_entry("s1", "decision", {"x": 2}, e1.hash)

    valid, break_index = verify_chain([e2, e1])

    assert valid is False
    assert break_index == 0


def test_entry_round_trips_through_dict():
    entry = make_entry("s1", "decision", {"x": 1}, GENESIS_HASH)
    restored = Entry.from_dict(entry.to_dict())
    assert restored == entry
    assert restored.content_hash == entry.content_hash
