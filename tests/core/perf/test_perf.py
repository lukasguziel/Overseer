from overseer.core.perf import logic as perf_logic


def _e(name, ms, guid=0):
    return {"guid": guid, "name": name, "type": "Cloner", "ms": ms, "polygons": 0}


def test_rank_sorts_slowest_first_and_shares_add_up():
    # do it
    out = perf_logic.rank([_e("a", 10.0, 1), _e("b", 30.0, 2), _e("c", 60.0, 3)])

    # postcondition
    assert [r["name"] for r in out["entries"]] == ["c", "b", "a"]
    assert abs(sum(r["share"] for r in out["entries"]) - 1.0) < 1e-9
    assert out["summary"]["total_ms"] == 100.0


def test_dominant_object_is_named_as_the_bottleneck():
    # do it
    out = perf_logic.rank([_e("heavy", 90.0), _e("cheap", 10.0)])

    # postcondition
    assert out["summary"]["slowest"] == "heavy"
    assert out["summary"]["heavy"] == 1
    assert out["entries"][0]["level"] == "heavy"
    assert out["entries"][1]["level"] == "mid"  # 10 of 100 ms is not "light"


def test_even_scene_has_no_bottleneck_to_name():
    # do it
    out = perf_logic.rank([_e("a", 20.0), _e("b", 20.0), _e("c", 20.0),
                           _e("d", 20.0), _e("e", 20.0)])

    # postcondition
    assert out["summary"]["slowest"] == ""
    assert out["summary"]["heavy"] == 0


def test_timer_noise_never_counts_as_a_cost():
    # do it
    out = perf_logic.rank([_e("blip", 0.1), _e("blip2", 0.1)])

    # postcondition: each holds 50% of the total, but 0.1 ms is jitter
    assert [r["level"] for r in out["entries"]] == ["light", "light"]
    assert out["summary"]["measured"] == 0
    assert out["summary"]["slowest"] == ""


def test_negative_and_missing_measurements_are_clamped():
    # do it
    out = perf_logic.rank([{"guid": 1, "name": "x", "type": "T", "ms": -3.0},
                           {"guid": 2, "name": "y", "type": "T"}])

    # postcondition
    assert all(r["ms"] == 0.0 for r in out["entries"])
    assert out["summary"]["total_ms"] == 0.0
    assert all(r["share"] == 0.0 for r in out["entries"])


def test_empty_input():
    # do it
    out = perf_logic.rank([])

    # postcondition
    assert out["entries"] == []
    assert out["summary"]["total"] == 0
    assert out["summary"]["slowest"] == ""
