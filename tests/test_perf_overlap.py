from sceneorg.core import perf_logic


def test_isolated_costs_add_up_to_the_full_rebuild():
    # Flat scene: no nesting, so the parts ARE the whole.
    assert perf_logic.overlap_ratio(100.0, 100.0) == 1.0


def test_nested_generators_overcount():
    # Every child drags its parent along -> parts sum to more than the whole.
    assert perf_logic.overlap_ratio(300.0, 100.0) == 3.0


def test_unmeasurably_fast_scene_reports_no_overlap():
    assert perf_logic.overlap_ratio(0.2, 0.1) == 1.0
    assert perf_logic.overlap_ratio(0.0, 50.0) == 1.0


def test_median_ignores_a_single_hiccup():
    # Two clean runs at ~3 ms, one run stalled by something else on the box.
    assert perf_logic.median([3.0, 3.2, 99.0]) == 3.2
    # ... and an unlucky fast run cannot hide a real cost either.
    assert perf_logic.median([0.1, 3.0, 3.2]) == 3.0


def test_median_of_even_and_empty_samples():
    assert perf_logic.median([2.0, 4.0]) == 3.0
    assert perf_logic.median([]) == 0.0


def test_jitter_is_the_spread_between_fastest_and_slowest():
    assert perf_logic.jitter([3.0, 3.2, 99.0]) == 96.0
    assert perf_logic.jitter([5.0]) == 0.0
    assert perf_logic.jitter([]) == 0.0
