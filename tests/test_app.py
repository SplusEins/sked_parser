from sked_parser.app import deduplicate_ids


def table(sked_id, path):
    return dict(id=sked_id, timetablePath=path)


def test_deduplicate_ids_leaves_unique_ids_alone():
    tables = [table("v_egt_1_ws26", "b.html"), table("v_ge_1_ws26", "a.html")]
    deduplicate_ids(tables)
    assert [t["id"] for t in tables] == ["v_egt_1_ws26", "v_ge_1_ws26"]


def test_deduplicate_ids_suffixes_collisions():
    """The plan with the alphabetically first URL keeps the plain ID, the others get a counter"""
    tables = [table("v_egt_1_ws26", "b.html"), table("v_egt_1_ws26", "a.html"), table("v_egt_1_ws26", "c.html")]
    deduplicate_ids(tables)
    assert [t["id"] for t in tables] == ["v_egt_1_ws26_2", "v_egt_1_ws26", "v_egt_1_ws26_3"]


def test_deduplicate_ids_is_independent_of_input_order():
    ids = []
    for paths in (["a.html", "b.html"], ["b.html", "a.html"]):
        tables = [table("v_egt_1_ws26", path) for path in paths]
        deduplicate_ids(tables)
        ids.append({t["timetablePath"]: t["id"] for t in tables})
    assert ids[0] == ids[1]


def test_deduplicate_ids_skips_suffix_taken_by_another_plan():
    """A generated suffix must never steal an ID that some other plan already has"""
    tables = [table("v_egt_1_ws26", "a.html"), table("v_egt_1_ws26", "b.html"), table("v_egt_1_ws26_2", "c.html")]
    deduplicate_ids(tables)
    ids = [t["id"] for t in tables]
    assert ids == ["v_egt_1_ws26", "v_egt_1_ws26_2", "v_egt_1_ws26_2_2"]
    assert len(set(ids)) == len(ids)
