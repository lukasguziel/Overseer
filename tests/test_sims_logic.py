from overseer.core import sims_logic as sl


def _hit(**kw):
    base = dict(guid=0, object="obj", carrier="tag", kind="dynamics",
                label="Dynamics Body")
    base.update(kw)
    return sl.SimHit(**base)


def test_active_hidden_finding_flags_enabled_sim_on_hidden_object():
    # setup
    hits = [
        _hit(guid=1, enabled=True, hidden=True),
        _hit(guid=2, enabled=True, hidden=False),
        _hit(guid=3, enabled=False, hidden=True),
    ]

    # do it
    findings = sl.compute_findings(hits)

    # postcondition: only the enabled sim on a hidden object is flagged
    assert [h["guid"] for h in findings["active_hidden"]] == [1]


def test_unbaked_only_when_cached_is_knowably_false_and_not_disabled():
    # setup
    hits = [
        _hit(guid=1, enabled=True, cached=False),
        _hit(guid=2, enabled=True, cached=True),
        _hit(guid=3, enabled=True, cached=None),
        _hit(guid=4, enabled=False, cached=False),
    ]

    # do it
    findings = sl.compute_findings(hits)

    # postcondition: unknown cache (None) and disabled sims never count as unbaked
    assert [h["guid"] for h in findings["unbaked"]] == [1]


def test_disabled_leftovers_are_only_explicitly_disabled_sims():
    # setup
    hits = [
        _hit(guid=1, enabled=False),
        _hit(guid=2, enabled=True),
        _hit(guid=3, enabled=None),
    ]

    # do it
    findings = sl.compute_findings(hits)

    # postcondition
    assert [h["guid"] for h in findings["disabled_leftovers"]] == [1]


def test_summary_counts_totals_and_per_kind():
    # setup
    hits = [
        _hit(kind="dynamics", enabled=True, hidden=True),
        _hit(kind="dynamics", enabled=False),
        _hit(kind="cloth", enabled=True, cached=False),
    ]

    # do it
    summary = sl.summarize(hits)

    # postcondition
    assert summary["total"] == 3
    assert summary["by_kind"] == {"dynamics": 2, "cloth": 1}
    assert summary["active_hidden"] == 1
    assert summary["unbaked"] == 1
    assert summary["disabled"] == 1


def test_scan_result_shape_is_stable_for_empty_scene():
    # do it
    res = sl.scan_result([])

    # postcondition
    assert res == {
        "ok": True,
        "hits": [],
        "findings": {"active_hidden": [], "unbaked": [], "disabled_leftovers": []},
        "summary": {"total": 0, "by_kind": {}, "active_hidden": 0,
                    "unbaked": 0, "disabled": 0},
    }
