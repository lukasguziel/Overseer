from overseer.core.settings import logic as uisl


def test_slug_is_stable_and_project_specific():
    # setup: two projects that share a basename but live in different folders
    a = uisl.project_slug("D:/proj/one", "scene.c4d")
    b = uisl.project_slug("D:/proj/two", "scene.c4d")

    # postcondition: same identity -> same slug, different path -> different slug
    assert a == uisl.project_slug("D:/proj/one", "scene.c4d")
    assert a != b
    assert a.startswith("scene-c4d-")


def test_unsaved_document_has_no_slug():
    # postcondition: no path and no name -> empty slug (persistence skipped)
    assert uisl.project_slug("", "") == ""
    assert uisl.project_slug("", "Untitled 1") != ""


def test_sanitize_keeps_only_known_keys_with_correct_types():
    # setup: a payload mixing valid values, wrong types and unknown keys
    raw = {
        "casing": "PascalCase",
        "applyCasing": True,
        "numberPad": 3,
        "dedupe": "yes",        # wrong type -> dropped
        "language": "de",
        "scope": True,          # not persisted -> dropped
        "translateEngine": "google",
        "includeHidden": False,
    }

    clean = uisl.sanitize_ui(raw)

    # postcondition: only well-typed persisted keys survive
    assert clean == {
        "casing": "PascalCase",
        "applyCasing": True,
        "numberPad": 3,
        "language": "de",
        "translateEngine": "google",
        "includeHidden": False,
    }


def test_sanitize_rejects_bool_for_int_and_non_dict():
    # postcondition: booleans never satisfy the int slot; non-dicts yield {}
    assert "numberPad" not in uisl.sanitize_ui({"numberPad": True})
    assert uisl.sanitize_ui(None) == {}
    assert uisl.sanitize_ui([1, 2]) == {}


def test_sanitize_global_keeps_deduped_string_areas_only():
    # setup: duplicates, non-strings and empties mixed into the hidden list
    raw = {"hiddenAreas": ["tags", "sims", "tags", "", 7, None, "files"],
           "casing": "PascalCase"}  # per-project key -> not global

    clean = uisl.sanitize_global_ui(raw)

    # postcondition: order-preserving dedupe, strings only, no foreign keys
    assert clean == {"hiddenAreas": ["tags", "sims", "files"]}


def test_sanitize_global_tolerates_garbage():
    # postcondition: non-dict input and a non-list hiddenAreas yield {}
    assert uisl.sanitize_global_ui(None) == {}
    assert uisl.sanitize_global_ui({"hiddenAreas": "tags"}) == {}
