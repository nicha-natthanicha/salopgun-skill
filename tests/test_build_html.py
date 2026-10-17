import re

import pytest
from playwright.sync_api import sync_playwright

from build_html import build_html
from conftest import load
from theme import neutral_theme


def big_content() -> dict:
    """6 top-level topics, each with 5 children and 1 grandchild each: 66 nodes."""
    c = load("content_min.json")
    c["sections"] = [
        {"id": f"t{i}", "title": f"หัวข้อ {i}", "focused": False, "summary": "สรุป", "points": ["จุด"],
         "code": [], "image_ids": [], "children": [
             {"id": f"t{i}c{j}", "title": f"ย่อย {i}.{j}", "focused": False, "summary": "", "points": [],
              "code": [], "image_ids": [], "children": [
                  {"id": f"t{i}c{j}g", "title": "ลึก", "focused": False, "summary": "", "points": [],
                   "code": [], "image_ids": [], "children": []}]}
             for j in range(5)]}
        for i in range(6)]
    return c


@pytest.fixture(scope="module")
def browser():
    with sync_playwright() as p:
        b = p.chromium.launch()
        yield b
        b.close()


def open_page(browser, path, width=1280):
    page = browser.new_page(viewport={"width": width, "height": 900})
    errors = []
    page.on("pageerror", lambda e: errors.append(str(e)))
    page.goto(path.as_uri())
    page.wait_for_selector("#mindmap .mm-node")
    assert errors == [], errors
    return page


@pytest.fixture(scope="module")
def built(tmp_path_factory):
    return build_html(load("content_min.json"), neutral_theme(), tmp_path_factory.mktemp("h") / "o.html", True)


@pytest.fixture
def page(browser, built):
    p = open_page(browser, built)
    yield p
    p.close()


def test_returns_path_and_writes_file(built):
    assert built.exists() and built.suffix == ".html"


def test_no_external_urls(built):
    assert not re.search(r'(src|href)="https?://', built.read_text(encoding="utf-8"))


def test_script_tag_in_content_is_inert(browser, tmp_path):
    c = load("content_min.json")
    c["sections"][0]["summary"] = "</script><b>x</b>"
    p = open_page(browser, build_html(c, neutral_theme(), tmp_path / "o.html", False))
    assert "</script><b>x</b>" in p.inner_text("#sec-s1")
    assert p.locator("#sec-s1 b").count() == 0


def test_mindmap_click_scrolls_to_section(page):
    page.click("[data-node='s2'] > .mm-row .label")
    assert page.evaluate("location.hash") == "#sec-s2"


def test_mindmap_toggle_expands_children(page):
    assert not page.is_visible("[data-node='s1a']")
    page.click("[data-node='s1'] > .mm-row .toggle")
    assert page.is_visible("[data-node='s1a']")


def test_mindmap_starts_collapsed_beyond_first_level(browser, tmp_path):
    p = open_page(browser, build_html(big_content(), neutral_theme(), tmp_path / "big.html", False))
    assert p.locator(".mm-node:visible").count() <= 1 + 6


def test_every_section_has_back_to_mindmap(page):
    assert page.locator("section.topic").count() == page.locator("section.topic a.back[href='#mindmap']").count() == 4


def test_hide_reveal_points(page):
    assert page.is_visible("#sec-s2 ul.points")
    page.click("#sec-s2 .reveal")
    assert not page.is_visible("#sec-s2 ul.points li >> nth=0")
    page.click("#sec-s2 .reveal")
    assert page.is_visible("#sec-s2 ul.points li >> nth=0")


def test_cards_tab_only_when_requested(tmp_path):
    c = load("content_min.json")
    assert "data-tab='cards'" not in build_html(c, neutral_theme(), tmp_path / "a.html", False).read_text(encoding="utf-8")
    assert "data-tab='cards'" in build_html(c, neutral_theme(), tmp_path / "b.html", True).read_text(encoding="utf-8")


def test_cards_tab_switch_and_flip(page):
    page.click("button[data-tab='cards']")
    assert page.is_visible("#cards") and not page.is_visible("#summary")
    page.click("#cards .card >> nth=0")
    assert "flipped" in page.get_attribute("#cards .card >> nth=0", "class")


def test_glossary_term_has_tooltip(page):
    term = page.locator("abbr.term").first
    assert term.get_attribute("title")


def test_quiz_reveals_answer(page):
    page.click("#quiz .q >> nth=0 >> button >> nth=1")
    q = page.locator("#quiz .q").first
    assert "wrong" in q.locator("button").nth(1).get_attribute("class")
    assert "correct" in q.locator("button").nth(0).get_attribute("class")
    assert q.locator(".explain").is_visible()


def test_dark_toggle_switches_theme(page):
    before = page.evaluate("document.documentElement.dataset.theme")
    page.click("#theme-toggle")
    after = page.evaluate("document.documentElement.dataset.theme")
    assert {before, after} == {"light", "dark"}


def test_mobile_has_no_horizontal_scroll(browser, built):
    p = open_page(browser, built, width=375)
    assert p.evaluate("document.documentElement.scrollWidth") <= 375
    assert not p.is_visible("nav#toc") or p.is_visible("#menu-toggle")


def test_code_blocks_scroll_horizontally(page):
    assert page.eval_on_selector("#sec-s2 pre", "e => getComputedStyle(e).overflowX") == "auto"


def test_desktop_layout_flag(browser, tmp_path):
    c = load("content_min.json")
    c["layout"] = "desktop"
    p = open_page(browser, build_html(c, neutral_theme(), tmp_path / "d.html", False))
    assert p.evaluate("document.body.dataset.layout") == "desktop"


def test_images_are_embedded(browser, tmp_path):
    from PIL import Image

    img = tmp_path / "dot.png"
    Image.new("RGB", (4, 4), (255, 0, 0)).save(img)
    c = load("content_min.json")
    c["images"] = [{"id": "img1", "path": str(img), "caption": "จุดแดง"}]
    c["sections"][0]["image_ids"] = ["img1"]
    p = open_page(browser, build_html(c, neutral_theme(), tmp_path / "i.html", False))
    assert p.get_attribute("#sec-s1 img", "src").startswith("data:image/png;base64,")
