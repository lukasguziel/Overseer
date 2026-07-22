from overseer.core.organize import journal


def _entry(eid, ts, items, reverted=False):
    return {"id": eid, "ts": ts, "items": list(items), "reverted": reverted,
            "revertible": bool(items)}


def _item(field="name", before="a", after="b", reverted=False):
    return {"sid": 1, "name": after, "field": field,
            "before": before, "after": after, "reverted": reverted}


def test_normalize_backfills_item_reverted_flags():
    # setup: a legacy entry whose items predate per-op reverts
    e = {"id": "1", "ts": 1, "items": [{"field": "name", "before": "a", "after": "b"}]}

    # do it
    out = journal.normalize_entry(e)

    # postcondition
    assert out["items"][0]["reverted"] is False
    assert out["revertible"] is True


def test_merge_journals_unions_by_id_newest_wins():
    # setup: same id, the container copy is older than the sidecar copy
    old = _entry("1", 10, [_item()])
    new = _entry("1", 20, [_item(reverted=True)])
    other = _entry("2", 15, [_item()])

    # do it
    merged = journal.merge_journals([old, other], [new])

    # postcondition: one entry per id, the newer "1" wins, sorted by ts
    assert [e["id"] for e in merged] == ["2", "1"]
    one = next(e for e in merged if e["id"] == "1")
    assert one["items"][0]["reverted"] is True


def test_items_to_revert_whole_run_skips_already_reverted():
    # setup
    e = _entry("1", 1, [_item(reverted=True), _item(), _item()])

    # do it
    pairs = journal.items_to_revert(e)

    # postcondition: the already-reverted op is not offered again
    assert [i for i, _ in pairs] == [1, 2]


def test_items_to_revert_selective_indices():
    # setup
    e = _entry("1", 1, [_item(), _item(), _item()])

    # do it: caller picks a single op, an out-of-range index is ignored
    pairs = journal.items_to_revert(e, indices=[2, 99])

    # postcondition
    assert [i for i, _ in pairs] == [2]


def test_mark_reverted_marks_run_when_all_items_done():
    # setup
    e = _entry("1", 1, [_item(), _item()])

    # do it: revert the two ops one at a time
    journal.mark_reverted(e, [0])
    partial = e["reverted"]
    journal.mark_reverted(e, [1])

    # postcondition: run flips to reverted only once every op is reverted
    assert partial is False
    assert e["reverted"] is True


def test_set_entry_replaces_by_id():
    # setup
    entries = [_entry("1", 1, [_item()]), _entry("2", 2, [_item()])]
    updated = _entry("2", 2, [_item(reverted=True)])

    # do it
    journal.set_entry(entries, updated)

    # postcondition
    assert entries[1]["items"][0]["reverted"] is True


def test_change_item_is_the_canonical_journal_row():
    # do it
    item = journal.change_item(41, "Cube", "name", "Cube", "PropsCube")

    # postcondition: exactly the shape revert() consumes on every host
    assert item == {"sid": 41, "name": "Cube", "field": "name",
                    "before": "Cube", "after": "PropsCube"}
