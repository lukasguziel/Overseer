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
