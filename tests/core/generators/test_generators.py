from overseer.core.generators.audit import GeneratorsAudit as gens_logic


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


def test_generator_rows_and_scan_result_envelope():
    # setup
    entries = [gens_logic.value_entry(1, "Cloner", 3),
               gens_logic.value_entry(2, "Cloner.1", 5)]
    summary = gens_logic.summarize(entries)
    param = gens_logic.param_row("mode", "Clone mode", "int", {}, summary)
    small = gens_logic.type_row("sds", "Subdivision Surface", 1007455, 1, [])
    big = gens_logic.type_row("cloner", "Cloner", 1018544, 2, [param])

    # do it
    out = gens_logic.scan_result([small, big], 3, 1)

    # postcondition: sorted by member count, summary counts the inputs
    assert param["values"] == summary["values"] and param["kind"] == "int"
    assert [t["key"] for t in out["types"]] == ["cloner", "sds"]
    assert out["summary"] == {"total_generators": 3, "types_found": 2,
                              "non_uniform_params": 1}
