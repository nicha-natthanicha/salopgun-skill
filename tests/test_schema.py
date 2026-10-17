import copy

from conftest import load
from schema import validate_content


def test_minimal_content_is_valid():
    assert validate_content(load("content_min.json")) == []


def test_quiz_count_out_of_range():
    data = load("content_min.json")
    data["quiz"] = data["quiz"][:4]
    assert any("quiz" in e for e in validate_content(data))


def test_quiz_needs_four_choices_and_valid_answer():
    data = load("content_min.json")
    data["quiz"][0]["answer_index"] = 4
    assert any("answer_index" in e for e in validate_content(data))


def test_duplicate_section_ids_in_nested_children():
    data = load("content_min.json")
    data["sections"][0]["children"] = [copy.deepcopy(data["sections"][1])]
    assert any("duplicate" in e for e in validate_content(data))


def test_unknown_image_id():
    data = load("content_min.json")
    data["sections"][0]["image_ids"] = ["nope"]
    assert any("nope" in e for e in validate_content(data))


def test_empty_object_reports_missing_sections():
    assert any("sections" in e for e in validate_content({}))


def test_bad_layout_rejected():
    data = load("content_min.json")
    data["layout"] = "tablet"
    assert any("layout" in e for e in validate_content(data))


def test_equation_schema_validation():
    c = load("content_min.json")
    c["sections"][1]["equations"] = [{"latex": r"\frac{a}{b}", "caption": "สมการ"}]
    assert validate_content(c) == []
    c["sections"][1]["equations"] = [{"latex": ""}]
    assert any("equations" in e for e in validate_content(c))
    c["sections"][1]["equations"] = [{"latex": "x", "caption": 5}]
    assert any("caption" in e for e in validate_content(c))
    c["sections"][1]["equations"] = "x=1"
    assert any("equations" in e for e in validate_content(c))
