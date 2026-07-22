import math

from overseer.core.tags.audit import TagsAudit

POINT, POLY, EDGE = 5674, 5673, 5701
KINDS = {POINT: "point", POLY: "polygon", EDGE: "edge"}


def _entry(type_id, label, objects):
    count = sum(len(o["tags"]) for o in objects)
    return {"type_id": type_id, "label": label, "count": count,
            "objects": objects}


def test_deg_from_rad_rounds_to_tenth():
    # do it
    result = TagsAudit.deg_from_rad(math.radians(40.0))

    # postcondition
    assert result == 40.0


def test_dominant_angle_picks_most_common():
    # setup
    counts = {40.0: 3, 60.0: 1, 80.0: 3}

    # do it: ties break on the larger angle
    result = TagsAudit.dominant_angle(counts)

    # postcondition
    assert result == 80.0


def test_dominant_angle_empty_is_none():
    # do it / postcondition
    assert TagsAudit.dominant_angle({}) is None


def test_merge_folds_selection_types_into_one_entry():
    # setup: polygon + edge selections, plus an unrelated Phong entry
    types = [
        _entry(5612, "Phong", [
            {"guid": 1, "name": "Cube", "tags": [{"name": "Phong"}]}]),
        _entry(POLY, "Polygon Selection", [
            {"guid": 1, "name": "Cube", "tags": [{"name": "TopFaces"}]}]),
        _entry(EDGE, "Edge Selection", [
            {"guid": 2, "name": "Frame", "tags": [{"name": "Bevel"}]}]),
    ]

    # do it
    result = TagsAudit.merge_selection_types(types, KINDS)

    # postcondition: one "Selection" entry carrying both source ids and kinds
    labels = [e["label"] for e in result]
    assert labels.count("Selection") == 1 and "Phong" in labels
    sel = next(e for e in result if e["label"] == "Selection")
    assert sel["type_ids"] == sorted([POLY, EDGE])
    assert sel["count"] == 2
    kinds = {t["kind"] for o in sel["objects"] for t in o["tags"]}
    assert kinds == {"polygon", "edge"}


def test_merge_groups_multi_tag_object_into_one_row():
    # setup: the same object carries a point AND two polygon selections
    types = [
        _entry(POINT, "Point Selection", [
            {"guid": 7, "name": "Sofa", "tags": [{"name": "Seams"}]}]),
        _entry(POLY, "Polygon Selection", [
            {"guid": 7, "name": "Sofa",
             "tags": [{"name": "Cushion"}, {"name": "Legs"}]}]),
    ]

    # do it
    sel = TagsAudit.merge_selection_types(types, KINDS)[0]

    # postcondition: ONE row for the object, all three tags with their kind
    assert len(sel["objects"]) == 1
    tags = sel["objects"][0]["tags"]
    assert [(t["name"], t["kind"]) for t in tags] == [
        ("Seams", "point"), ("Cushion", "polygon"), ("Legs", "polygon")]


def test_merge_without_selection_entries_is_a_no_op():
    # setup
    types = [_entry(5612, "Phong", [])]

    # do it / postcondition: untouched, same object
    assert TagsAudit.merge_selection_types(types, KINDS) is types


def test_merge_resorts_by_count_desc():
    # setup: selections outnumber the Phong tags after merging
    types = [
        _entry(5612, "Phong", [
            {"guid": 1, "name": "Cube", "tags": [{"name": "Phong"}]}]),
        _entry(POLY, "Polygon Selection", [
            {"guid": 2, "name": "Wall", "tags": [{"name": "A"}]}]),
        _entry(POINT, "Point Selection", [
            {"guid": 3, "name": "Rug", "tags": [{"name": "B"}]}]),
    ]

    # do it
    result = TagsAudit.merge_selection_types(types, KINDS)

    # postcondition: merged Selection (count 2) sorts before Phong (count 1)
    assert [e["label"] for e in result] == ["Selection", "Phong"]


def test_scan_result_shapes_the_tags_envelope():
    # setup: two attachment types with rows, one phong angle histogram
    types = {}
    e = TagsAudit.type_entry(5616, "Phong")
    e["count"] = 2
    e["objects"].append(TagsAudit.object_row(1, "Cube", [{"name": "Phong"}]))
    types[5616] = e
    small = TagsAudit.type_entry(5615, "Texture")
    small["count"] = 1
    types[5615] = small

    # do it
    out = TagsAudit.scan_result(types, [{"guid": 2, "name": "Plane"}], [],
                      {35.0: 2, 40.0: 1})

    # postcondition: sorted by count desc, totals derived from the entries
    assert out["ok"] is True and "phong" not in out
    assert [t["label"] for t in out["types"]] == ["Phong", "Texture"]
    assert out["summary"]["total_tags"] == 3
    assert out["summary"]["missing_phong"] == 1
    assert out["findings"]["phong_angles"]["dominant_angle"] == 35.0


def test_scan_result_phong_false_marks_hosts_without_phong():
    # do it
    out = TagsAudit.scan_result({}, [], [], {}, phong=False)

    # postcondition
    assert out["phong"] is False
