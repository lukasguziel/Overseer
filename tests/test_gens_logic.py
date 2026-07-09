from sceneorg.core import gens_logic


def test_uniform_param_has_single_bucket_and_no_outliers():
    # setup
    entries = [{"guid": 1, "name": "a", "value": 2},
               {"guid": 2, "name": "b", "value": 2}]

    # do it
    result = gens_logic.summarize(entries)

    # postcondition
    assert result["uniform"] is True
    assert result["dominant"] == 2
    assert result["outliers"] == []
    assert result["distribution"] == [{"value": 2, "count": 2}]


def test_dominant_is_most_common_and_outliers_are_the_rest():
    # setup
    entries = [{"guid": i, "name": str(i), "value": v}
               for i, v in enumerate([2, 2, 2, 4, 6])]

    # do it
    result = gens_logic.summarize(entries)

    # postcondition
    assert result["uniform"] is False
    assert result["dominant"] == 2
    assert [o["value"] for o in result["outliers"]] == [4, 6]
    assert result["distribution"][0] == {"value": 2, "count": 3}


def test_list_values_are_hashed_and_grouped():
    # setup
    entries = [{"guid": 1, "name": "a", "value": [1, 0, 0]},
               {"guid": 2, "name": "b", "value": [1, 0, 0]},
               {"guid": 3, "name": "c", "value": [0, 1, 0]}]

    # do it
    result = gens_logic.summarize(entries)

    # postcondition
    assert result["dominant"] == [1, 0, 0]
    assert len(result["distribution"]) == 2
    assert [o["guid"] for o in result["outliers"]] == [3]


def test_bool_and_int_values_do_not_collide():
    # setup
    entries = [{"guid": 1, "name": "a", "value": True},
               {"guid": 2, "name": "b", "value": 1}]

    # do it
    result = gens_logic.summarize(entries)

    # postcondition
    assert len(result["distribution"]) == 2


def test_empty_input_is_safe():
    # do it
    result = gens_logic.summarize([])

    # postcondition
    assert result["uniform"] is True
    assert result["dominant"] is None
    assert result["outliers"] == []
