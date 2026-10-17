import copy
from pathlib import Path

from build_podcast import PROMPT, build_podcast
from conftest import load
from schema import validate_dialogue


def test_valid_dialogues_pass():
    content = load("content_min.json")
    assert validate_dialogue(load("dialogue_ok.json"), content) == []
    assert validate_dialogue(load("dialogue_by_chapter.json"), content) == []


def test_missing_section_rejected():
    d = load("dialogue_ok.json")
    d["episodes"][0]["lines"] = [l for l in d["episodes"][0]["lines"] if l["section_id"] != "s2"]
    assert any("s2" in e for e in validate_dialogue(d, load("content_min.json")))


def test_section_missing_from_all_episodes_rejected():
    d = load("dialogue_by_chapter.json")
    del d["episodes"][1]
    assert any("s3" in e for e in validate_dialogue(d, load("content_min.json")))


def test_out_of_order_rejected():
    d = load("dialogue_ok.json")
    d["episodes"][0]["lines"].reverse()
    assert any("order" in e for e in validate_dialogue(d, load("content_min.json")))


def test_by_chapter_max_two_sections_per_episode():
    d = load("dialogue_by_chapter.json")
    d["episodes"][0]["section_ids"].append("s3")
    assert validate_dialogue(d, load("content_min.json"))


def test_overview_must_be_one_episode():
    d = load("dialogue_by_chapter.json")
    d["mode"] = "overview"
    assert any("overview" in e for e in validate_dialogue(d, load("content_min.json")))


def test_bad_speaker_rejected():
    d = load("dialogue_ok.json")
    d["episodes"][0]["lines"][0]["speaker"] = "C"
    assert any("speaker" in e for e in validate_dialogue(d, load("content_min.json")))


def test_files_have_topics_dialogue_checklist(tmp_path):
    paths = build_podcast(load("dialogue_by_chapter.json"), load("content_min.json"), tmp_path)
    md = Path(paths[0]).read_text(encoding="utf-8")
    assert md.index("## หัวข้อที่ต้องพูดถึง") < md.index("**พิธีกร A:**") < md.index("## Checklist")
    assert "- [ ] Machine Learning คืออะไร" in md and "- [ ] Overfitting" in md
    assert (tmp_path / "notebooklm-prompt.txt").exists()
    assert [Path(p).name for p in paths] == ["podcast-01.md", "podcast-02.md"]


def test_focused_topics_marked_and_subtopics_listed(tmp_path):
    paths = build_podcast(load("dialogue_ok.json"), load("content_min.json"), tmp_path)
    md = Path(paths[0]).read_text(encoding="utf-8")
    topics = md.split("## หัวข้อที่ต้องพูดถึง")[1].split("---")[0]
    assert "Machine Learning คืออะไร [เน้น]" in topics
    assert "Supervised learning" in topics


def test_prompt_text(tmp_path):
    build_podcast(load("dialogue_ok.json"), load("content_min.json"), tmp_path)
    text = (tmp_path / "notebooklm-prompt.txt").read_text(encoding="utf-8")
    assert PROMPT in text and "Longer" in text


def test_invalid_dialogue_raises(tmp_path):
    d = load("dialogue_ok.json")
    d["episodes"] = []
    try:
        build_podcast(d, load("content_min.json"), tmp_path)
    except ValueError:
        return
    raise AssertionError("expected ValueError")
