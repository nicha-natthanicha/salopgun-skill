import json
import subprocess
import sys
from pathlib import Path

import pymupdf
import pytest
from PIL import Image
from pptx import Presentation
from pptx.util import Inches

import images
from build_pdf import build_pdf, print_html
from conftest import FIXTURES, ROOT, load
from schema import validate_content
from theme import neutral_theme

CLI = ROOT / "salopgun" / "scripts" / "salopgun.py"


def png(path: Path, color) -> Path:
    Image.new("RGB", (240, 180), color).save(path)
    return path


def make_deck(tmp_path: Path, slides: list) -> Path:
    """slides: list of lists of picture paths per slide."""
    prs = Presentation()
    for pics in slides:
        slide = prs.slides.add_slide(prs.slide_layouts[6])
        for i, pic in enumerate(pics):
            slide.shapes.add_picture(str(pic), Inches(0.5 + i * 3), Inches(1))
    out = tmp_path / "deck.pptx"
    prs.save(out)
    return out


def make_pdf(tmp_path: Path, spec: list) -> Path:
    """spec: per page, a dict with optional 'pic' path, 'rects' count, 'text'."""
    doc = pymupdf.open()
    for page_spec in spec:
        page = doc.new_page()
        page.insert_text((72, 72), page_spec.get("text", "slide"), fontsize=14)
        if page_spec.get("pic"):
            page.insert_image(pymupdf.Rect(72, 100, 312, 280), filename=str(page_spec["pic"]))
        for i in range(page_spec.get("rects", 0)):
            page.draw_rect(pymupdf.Rect(40 + i * 20, 400, 55 + i * 20, 430), fill=(0.2, 0.4, 0.8))
    out = tmp_path / "deck.pdf"
    doc.save(out)
    return out


def run_cli(*args):
    return subprocess.run([sys.executable, str(CLI), *map(str, args)], capture_output=True, text=True)


# ---- embedded pictures ----

def test_pptx_pictures_report_slide_numbers(tmp_path):
    a, b = png(tmp_path / "a.png", (200, 30, 30)), png(tmp_path / "b.png", (30, 200, 30))
    found = images.extract_images(str(make_deck(tmp_path, [[], [a], [b]])), str(tmp_path / "out"))
    assert [(f["slide"], f["kind"]) for f in found] == [(2, "picture"), (3, "picture")]
    assert [f["id"] for f in found] == ["img1", "img2"] and all(Path(f["path"]).exists() for f in found)


def test_logo_repeated_on_three_slides_is_skipped(tmp_path):
    logo, chart = png(tmp_path / "logo.png", (10, 10, 10)), png(tmp_path / "chart.png", (20, 120, 220))
    found = images.extract_images(str(make_deck(tmp_path, [[logo], [logo, chart], [logo], []])), str(tmp_path / "out"))
    assert [f["slide"] for f in found] == [2]


def test_picture_on_two_slides_is_kept_once_at_first_slide(tmp_path):
    p = png(tmp_path / "p.png", (90, 90, 200))
    found = images.extract_images(str(make_deck(tmp_path, [[], [p], [p]])), str(tmp_path / "out"))
    assert [f["slide"] for f in found] == [2]


def test_pptx_slide_order_follows_presentation_not_file_names(tmp_path):
    a, b = png(tmp_path / "a.png", (200, 30, 30)), png(tmp_path / "b.png", (30, 200, 30))
    prs = Presentation(str(make_deck(tmp_path, [[a], [b]])))
    lst = prs.slides._sldIdLst
    first = lst[0]
    lst.remove(first)
    lst.append(first)  # slide1.xml is now shown second
    prs.save(tmp_path / "reordered.pptx")
    found = images.extract_images(str(tmp_path / "reordered.pptx"), str(tmp_path / "out"))
    colors = {f["slide"]: Image.open(f["path"]).getpixel((5, 5)) for f in found}
    assert colors[1] == (30, 200, 30) and colors[2] == (200, 30, 30)


def test_pdf_pictures_report_page_numbers(tmp_path):
    a = png(tmp_path / "a.png", (200, 30, 30))
    found = images.extract_images(str(make_pdf(tmp_path, [{}, {"pic": a}, {}])), str(tmp_path / "out"))
    assert [(f["slide"], f["kind"]) for f in found] == [(2, "picture")]


# ---- slide info (which slides are worth a snapshot) ----

def test_pdf_slide_info_flags_diagram_pages(tmp_path):
    a = png(tmp_path / "a.png", (200, 30, 30))
    info = images.slide_info(str(make_pdf(tmp_path, [{"text": "only text"}, {"rects": 14}, {"pic": a}])))
    assert [i["page"] for i in info] == [1, 2, 3]
    assert [i["visual"] for i in info] == [False, True, True]
    assert info[2]["pictures"] == 1 and info[0]["text_chars"] > 0


def test_pptx_slide_info_counts_pictures_and_equations(tmp_path):
    a = png(tmp_path / "a.png", (200, 30, 30))
    prs = Presentation(str(make_deck(tmp_path, [[], [a]])))
    xml = prs.slides[0].shapes._spTree
    from lxml import etree
    omml = etree.fromstring(
        '<a:p xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main" '
        'xmlns:m="http://schemas.openxmlformats.org/officeDocument/2006/math"><m:oMath><m:r><m:t>x</m:t></m:r></m:oMath></a:p>')
    xml.append(omml)
    prs.save(tmp_path / "eq.pptx")
    info = images.slide_info(str(tmp_path / "eq.pptx"))
    assert info[0]["equations"] == 1 and info[0]["visual"] is False
    assert info[1]["pictures"] == 1 and info[1]["visual"] is True


# ---- snapshots ----

def test_parse_pages():
    assert images.parse_pages("3,5,7-9", 10) == [3, 5, 7, 8, 9]
    for bad in ("0", "11", "4-2", "a"):
        with pytest.raises(ValueError):
            images.parse_pages(bad, 10)


def test_snapshots_from_pdf(tmp_path):
    shots = images.snapshots(str(make_pdf(tmp_path, [{}, {"rects": 5}, {}])), [2], str(tmp_path / "shots"), dpi=100)
    assert [(s["id"], s["kind"], s["slide"]) for s in shots] == [("slide2", "slide", 2)]
    with Image.open(shots[0]["path"]) as im:
        assert im.format == "JPEG" and abs(im.width - 595 * 100 / 72) < 3


def test_snapshots_pptx_needs_libreoffice(tmp_path, monkeypatch):
    deck = make_deck(tmp_path, [[]])
    monkeypatch.setattr(images, "find_soffice", lambda: None)
    with pytest.raises(ValueError, match="soffice"):
        images.snapshots(str(deck), [1], str(tmp_path / "s"))


def test_snapshots_pptx_converts_through_libreoffice(tmp_path, monkeypatch):
    deck = make_deck(tmp_path, [[], []])
    ready = make_pdf(tmp_path, [{}, {"rects": 3}])
    calls = []

    def fake_run(cmd, **kw):
        calls.append(cmd)
        outdir = Path(cmd[cmd.index("--outdir") + 1])
        (outdir / "deck.pdf").write_bytes(ready.read_bytes())
        return subprocess.CompletedProcess(cmd, 0, "", "")

    monkeypatch.setattr(images, "find_soffice", lambda: "/fake/soffice")
    monkeypatch.setattr(images.subprocess, "run", fake_run)
    shots = images.snapshots(str(deck), [2], str(tmp_path / "s"))
    assert shots[0]["slide"] == 2 and Path(shots[0]["path"]).exists()
    assert calls[0][:3] == ["/fake/soffice", "--headless", "--convert-to"] and str(deck) in calls[0]


# ---- cli ----

def test_cli_slides_and_snapshots_roundtrip(tmp_path):
    pdf = make_pdf(tmp_path, [{}, {"rects": 14}])
    r = run_cli("slides", "--source", pdf)
    assert r.returncode == 0 and json.loads(r.stdout)[1]["visual"] is True
    r = run_cli("snapshots", "--source", pdf, "--pages", "1-2", "--out-dir", tmp_path / "shots")
    assert r.returncode == 0 and [s["id"] for s in json.loads(r.stdout)] == ["slide1", "slide2"]


def test_cli_snapshot_page_out_of_range_exits_2(tmp_path):
    r = run_cli("snapshots", "--source", make_pdf(tmp_path, [{}]), "--pages", "5", "--out-dir", tmp_path / "s")
    assert r.returncode == 2 and "5" in r.stderr


# ---- schema + output ----

def content_with_image(tmp_path, kind="picture", slide=3):
    c = load("content_min.json")
    img = png(tmp_path / "pic.png", (50, 120, 200))
    c["images"] = [{"id": "img1", "path": str(img), "caption": "รูปประกอบ", "kind": kind, "slide": slide}]
    c["sections"][1]["image_ids"] = ["img1"]
    return c


def test_image_kind_and_slide_validated(tmp_path):
    c = content_with_image(tmp_path)
    assert validate_content(c) == []
    c["images"][0]["kind"] = "gif"
    assert any("kind" in e for e in validate_content(c))
    c["images"][0]["kind"] = "slide"
    c["images"][0]["slide"] = 0
    assert any("slide" in e for e in validate_content(c))


@pytest.mark.parametrize("style", ["bullet", "mindmap"])
def test_images_appear_in_both_pdf_styles(tmp_path, style):
    r = build_pdf(content_with_image(tmp_path), neutral_theme(), tmp_path / f"{style}.pdf", "A4", "landscape", style)
    with pymupdf.open(r["path"]) as doc:
        assert sum(len(p.get_images()) for p in doc) == 1
        assert "รูปประกอบ" in "".join(p.get_text() for p in doc)


def test_slide_snapshots_get_their_own_frame_and_label(tmp_path):
    html = print_html(content_with_image(tmp_path, kind="slide", slide=3), neutral_theme(), (210, 297), "bullet")
    assert '<figure class="slide">' in html and "สไลด์ที่ 3" in html
    plain = print_html(content_with_image(tmp_path, kind="picture", slide=3), neutral_theme(), (210, 297), "bullet")
    assert '<figure class="slide">' not in plain


def test_two_images_in_one_section_both_render(tmp_path):
    c = content_with_image(tmp_path)
    c["images"].append({**c["images"][0], "id": "img2", "caption": "รูปที่สอง"})
    c["sections"][1]["image_ids"] = ["img1", "img2"]
    r = build_pdf(c, neutral_theme(), tmp_path / "two.pdf", "A4", "portrait", "bullet")
    with pymupdf.open(r["path"]) as doc:
        assert "รูปที่สอง" in "".join(p.get_text() for p in doc)


def test_skill_md_documents_slides_snapshots_and_math():
    text = (ROOT / "salopgun" / "SKILL.md").read_text(encoding="utf-8")
    for needle in ("`slides --source", "`snapshots --source", "math_errors", "equations", "\\\\$"):
        assert needle in text


def test_mindmap_with_big_slide_snapshots_does_not_leave_first_page_empty(tmp_path):
    big = tmp_path / "slide.jpg"
    Image.new("RGB", (794, 1123), (230, 240, 255)).save(big, quality=80)
    c = load("content_min.json")
    c["images"] = [{"id": "slide1", "path": str(big), "caption": "ภาพสไลด์", "kind": "slide", "slide": 2},
                   {"id": "slide2", "path": str(big), "caption": "ภาพสไลด์อีกใบ", "kind": "slide", "slide": 3}]
    c["sections"][0]["image_ids"] = ["slide1"]
    c["sections"][1]["image_ids"] = ["slide2"]
    r = build_pdf(c, neutral_theme(), tmp_path / "mm.pdf", "A4", "landscape", "mindmap")
    with pymupdf.open(r["path"]) as doc:
        assert "Machine Learning คืออะไร" in doc[0].get_text()
        assert r["pages"] <= 2


def test_bullet_figures_are_capped_in_height(tmp_path):
    big = tmp_path / "tall.png"
    Image.new("RGB", (400, 1200), (200, 220, 240)).save(big)
    c = content_with_image(tmp_path)
    c["images"][0]["path"] = str(big)
    r = build_pdf(c, neutral_theme(), tmp_path / "b.pdf", "A4", "portrait", "bullet")
    with pymupdf.open(r["path"]) as doc:
        rects = [rect for p in doc for info in p.get_image_info() for rect in [pymupdf.Rect(info["bbox"])]]
    assert rects and max(rc.height for rc in rects) <= 95 * 72 / 25.4
