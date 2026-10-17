import pymupdf
import pytest
from pypdf import PdfReader

from build_pdf import build_pdf, page_size_mm, print_html
from conftest import load
from theme import neutral_theme


def font_names(pdf_path) -> list[str]:
    names = []
    for page in PdfReader(pdf_path).pages:
        for ref in page["/Resources"]["/Font"].values():
            names.append(str(ref.get_object()["/BaseFont"]))
    return names


def text_boxes_inside_page(pdf_path) -> bool:
    with pymupdf.open(pdf_path) as doc:
        for page in doc:
            area = page.rect
            for x0, y0, x1, y1, *_ in page.get_text("words", clip=pymupdf.INFINITE_RECT()):
                if x0 < area.x0 - 1 or y0 < area.y0 - 1 or x1 > area.x1 + 1 or y1 > area.y1 + 1:
                    return False
    return True


@pytest.mark.parametrize("paper,orient,expected", [
    ("A4", "portrait", (210, 297)), ("A4", "landscape", (297, 210)),
    ("B5", "portrait", (176, 250)), ("mobile", "portrait", (90, 160)),
    ("desktop", "landscape", (297, 167)), ("desktop", "portrait", (167, 297))])
def test_page_sizes(paper, orient, expected):
    assert page_size_mm(paper, orient) == expected


def test_custom_size():
    assert page_size_mm("custom", "portrait", (100, 200)) == (100, 200)
    assert page_size_mm("custom", "landscape", (100, 200)) == (200, 100)


def test_unknown_paper_rejected():
    with pytest.raises(ValueError):
        page_size_mm("A3", "portrait")


def test_pdf_page_size_and_thai_font(tmp_path):
    r = build_pdf(load("content_thai_long.json"), neutral_theme(), tmp_path / "o.pdf", "A4", "landscape", "bullet")
    page = PdfReader(r["path"]).pages[0]
    assert round(float(page.mediabox.width) * 25.4 / 72) == 297
    assert any("Sarabun" in n for n in font_names(r["path"]))


def test_thai_long_line_wraps_within_page(tmp_path):
    r = build_pdf(load("content_thai_long.json"), neutral_theme(), tmp_path / "o.pdf", "mobile", "portrait", "bullet")
    assert r["pages"] > 1
    assert text_boxes_inside_page(r["path"])


def test_over_limit_flag(tmp_path):
    r = build_pdf(load("content_thai_long.json"), neutral_theme(), tmp_path / "o.pdf", "mobile", "portrait", "bullet", max_pages=1)
    assert r["over_limit"] is True


def test_within_limit_flag(tmp_path):
    r = build_pdf(load("content_min.json"), neutral_theme(), tmp_path / "o.pdf", "A4", "portrait", "bullet", max_pages=5)
    assert r["over_limit"] is False


def test_mindmap_style_renders(tmp_path):
    r = build_pdf(load("content_min.json"), neutral_theme(), tmp_path / "m.pdf", "A4", "landscape", "mindmap")
    assert r["pages"] >= 1
    with pymupdf.open(r["path"]) as doc:
        text = "".join(p.get_text() for p in doc)
    assert "Supervised learning" in text and "Overfitting" in text


def test_print_html_escapes_markup():
    c = load("content_min.json")
    c["sections"][0]["summary"] = "<script>alert(1)</script>"
    html = print_html(c, neutral_theme(), (210, 297), "bullet")
    assert "<script>alert" not in html and "&lt;script&gt;" in html


def test_print_html_fallback_engine(tmp_path, monkeypatch):
    import build_pdf as mod
    monkeypatch.setattr(mod, "ENGINES", ["print-html"])
    r = build_pdf(load("content_min.json"), neutral_theme(), tmp_path / "o.pdf", "A4", "portrait", "bullet")
    assert r["path"].endswith(".html") and r["pages"] == 0 and r["engine"] == "print-html"
    assert "@page" in open(r["path"], encoding="utf-8").read()
