"""Regression tests for the final-review fix pass."""
import builtins
import json
import subprocess
import sys
from pathlib import Path

import pytest

from conftest import FIXTURES, ROOT, load
from theme import _readable, contrast_ratio, neutral_theme, palette

CLI = ROOT / "salopgun" / "scripts" / "salopgun.py"
LONG_URL = "https://example.com/" + "abcdefghij" * 16 + ".html"

THEMES = {
    "neutral": neutral_theme(),
    "inverted": {**neutral_theme(), "background": "#000000", "text": "#FFFFFF", "primary": "#4FC3F7", "source": "extracted"},
    "grey_dk1": {**neutral_theme(), "text": "#595959", "source": "extracted"},
    "dark_grey_dk1": {**neutral_theme(), "text": "#404040", "source": "extracted"},
    "pale_accent": {**neutral_theme(), "accent": "#FFE680", "primary": "#CCCCCC", "source": "extracted"},
}


@pytest.mark.parametrize("name", THEMES)
@pytest.mark.parametrize("dark", [False, True])
def test_every_text_role_readable(name, dark):
    p = palette(THEMES[name], dark)
    for role in ("text", "primary", "muted", "accent_text"):
        assert contrast_ratio(p[role], p["background"]) >= 4.5, (name, dark, role)
    assert contrast_ratio(p["on_primary"], p["primary"]) >= 4.5
    assert contrast_ratio(p["text"], p["code_bg"]) >= 4.5


def test_light_mode_background_is_light_for_inverted_deck():
    from theme import _luminance
    assert _luminance(palette(THEMES["inverted"], dark=False)["background"]) > 0.5


def test_readable_tries_both_directions():
    assert contrast_ratio(_readable("#808080", "#777777"), "#777777") >= 4.5


def _page(path, width=375):
    from playwright.sync_api import sync_playwright
    p = sync_playwright().start()
    b = p.chromium.launch()
    page = b.new_page(viewport={"width": width, "height": 800})
    page.goto(Path(path).as_uri())
    page.wait_for_selector("#mindmap .mm-node")
    return p, b, page


def test_long_url_does_not_scroll_page_on_phone(tmp_path):
    from build_html import build_html
    c = load("content_min.json")
    c["sections"][0]["points"].append(LONG_URL)
    p, b, page = _page(build_html(c, neutral_theme(), tmp_path / "u.html", False))
    try:
        assert page.evaluate("document.documentElement.scrollWidth") <= 375
    finally:
        b.close(); p.stop()


def test_long_url_stays_inside_mobile_pdf(tmp_path):
    from build_pdf import build_pdf
    from test_build_pdf import text_boxes_inside_page
    c = load("content_min.json")
    c["sections"][0]["points"].append(LONG_URL)
    r = build_pdf(c, neutral_theme(), tmp_path / "u.pdf", "mobile", "portrait", "bullet")
    assert text_boxes_inside_page(r["path"])
    import pymupdf
    with pymupdf.open(r["path"]) as doc:
        visible = "".join(page.get_text() for page in doc).replace("\n", "")
    assert "abcdefghij.html" in visible


def test_page_count_without_pypdf(tmp_path, monkeypatch):
    import build_pdf as mod
    real_import = builtins.__import__

    def no_pypdf(name, *a, **k):
        if name == "pypdf":
            raise ImportError("blocked")
        return real_import(name, *a, **k)

    monkeypatch.setattr(builtins, "__import__", no_pypdf)
    r = mod.build_pdf(load("content_min.json"), neutral_theme(), tmp_path / "o.pdf", "A4", "portrait", "bullet", max_pages=1)
    assert r["pages"] >= 1


def test_child_id_lines_get_their_topic_heading(tmp_path):
    from build_podcast import build_podcast
    d = load("dialogue_ok.json")
    for line in d["episodes"][0]["lines"]:
        if line["section_id"] == "s1":
            line["section_id"] = "s1a"
    md = Path(build_podcast(d, load("content_min.json"), tmp_path)[0]).read_text(encoding="utf-8")
    dialogue = md.split("## บทสนทนา")[1]
    assert dialogue.index("### Machine Learning คืออะไร") < dialogue.index("**พิธีกร A:** วันนี้")


def test_non_string_points_rejected():
    from schema import validate_content
    c = load("content_min.json")
    c["sections"][0]["points"] = ["ok", None]
    assert any("points" in e for e in validate_content(c))


def test_null_caption_and_summary_are_fine(tmp_path):
    from PIL import Image
    from build_pdf import build_pdf
    from schema import validate_content
    img = tmp_path / "dot.png"
    Image.new("RGB", (200, 200), (255, 0, 0)).save(img)
    c = load("content_min.json")
    c["images"] = [{"id": "img1", "path": str(img), "caption": None}]
    c["sections"][0]["image_ids"] = ["img1"]
    c["sections"][1]["summary"] = None
    assert validate_content(c) == []
    assert build_pdf(c, neutral_theme(), tmp_path / "n.pdf", "A4", "portrait", "bullet")["pages"] >= 1


def run_cli(*args):
    return subprocess.run([sys.executable, str(CLI), *map(str, args)], capture_output=True, text=True)


def test_missing_image_file_exits_2(tmp_path):
    c = load("content_min.json")
    c["images"] = [{"id": "img1", "path": "nope.png", "caption": ""}]
    c["sections"][0]["image_ids"] = ["img1"]
    (tmp_path / "c.json").write_text(json.dumps(c, ensure_ascii=False), encoding="utf-8")
    (tmp_path / "t.json").write_text(json.dumps(neutral_theme()))
    r = run_cli("html", "--content", tmp_path / "c.json", "--theme", tmp_path / "t.json", "--out", tmp_path / "o.html")
    assert r.returncode == 2 and "nope.png" in r.stderr


def test_relative_image_path_resolves_from_content_folder(tmp_path):
    from PIL import Image
    Image.new("RGB", (200, 200), (0, 0, 255)).save(tmp_path / "pic.png")
    c = load("content_min.json")
    c["images"] = [{"id": "img1", "path": "pic.png", "caption": "x"}]
    c["sections"][0]["image_ids"] = ["img1"]
    (tmp_path / "c.json").write_text(json.dumps(c, ensure_ascii=False), encoding="utf-8")
    (tmp_path / "t.json").write_text(json.dumps(neutral_theme()))
    r = run_cli("html", "--content", tmp_path / "c.json", "--theme", tmp_path / "t.json", "--out", tmp_path / "o.html")
    assert r.returncode == 0, r.stderr


def test_incomplete_theme_json_exits_2(tmp_path):
    (tmp_path / "t.json").write_text('{"primary": "#123456"}')
    r = run_cli("pdf", "--content", FIXTURES / "content_min.json", "--theme", tmp_path / "t.json", "--paper", "A4",
                "--orientation", "portrait", "--style", "bullet", "--out", tmp_path / "o.pdf")
    assert r.returncode == 2 and "background" in r.stderr


def test_size_without_custom_paper_exits_2(tmp_path):
    (tmp_path / "t.json").write_text(json.dumps(neutral_theme()))
    r = run_cli("pdf", "--content", FIXTURES / "content_min.json", "--theme", tmp_path / "t.json", "--paper", "A4",
                "--size", "100x150", "--orientation", "portrait", "--style", "bullet", "--out", tmp_path / "o.pdf")
    assert r.returncode == 2 and "custom" in r.stderr


def test_skill_md_documents_custom_size_and_print_html_pages():
    text = (ROOT / "salopgun" / "SKILL.md").read_text(encoding="utf-8")
    assert "--paper custom --size" in text
    assert "pages" in text.split("print-html")[1][:400]
