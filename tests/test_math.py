import json
import subprocess
import sys

import pymupdf
import pytest

from build_pdf import build_pdf, print_html
from conftest import FIXTURES, ROOT, load
from schema import validate_content
from test_build_pdf import font_names
from theme import neutral_theme

CLI = ROOT / "salopgun" / "scripts" / "salopgun.py"


def with_math(**extra) -> dict:
    c = load("content_min.json")
    c["sections"][1]["summary"] = "ความเร็วแสงเกี่ยวข้องกับ $E=mc^2$ เสมอ"
    c["sections"][1]["equations"] = [{"latex": r"\frac{a}{b}+\sum_{i=1}^{n} x_i", "caption": "สมการตัวอย่าง"}]
    c.update(extra)
    return c


def html_for(content, style="bullet") -> str:
    return print_html(content, neutral_theme(), (210, 297), style)


def test_inline_dollar_math_is_wrapped_and_escaped():
    html = html_for(with_math())
    assert '<span class="tex">E=mc^2</span>' in html


def test_prices_are_not_math():
    c = load("content_min.json")
    c["sections"][0]["summary"] = "ราคา $5 และ $10 ต่อชิ้น"
    assert 'class="tex"' not in html_for(c)


def test_escaped_dollar_is_literal():
    c = load("content_min.json")
    c["sections"][0]["summary"] = r"ใช้ \$a+b\$ เป็นข้อความ"
    html = html_for(c)
    assert 'class="tex"' not in html and "$a+b$" in html


def test_block_equation_with_caption():
    html = html_for(with_math())
    assert '<div class="tex display">\\frac{a}{b}+\\sum_{i=1}^{n} x_i</div>' in html
    assert "สมการตัวอย่าง" in html


def test_math_markup_in_latex_is_inert():
    c = with_math()
    c["sections"][1]["equations"] = [{"latex": "</script><img src=x onerror=alert(1)>"}]
    html = html_for(c)
    assert "<img src=x" not in html and "&lt;/script&gt;" in html


def test_katex_only_bundled_when_math_present():
    plain = html_for(load("content_min.json"))
    withmath = html_for(with_math())
    for marker in ("katex.render", "KaTeX_Main"):
        assert marker not in plain and marker in withmath
    assert len(withmath) > len(plain) + 400_000


def test_equations_render_with_katex_fonts_in_pdf(tmp_path):
    r = build_pdf(with_math(), neutral_theme(), tmp_path / "m.pdf", "A4", "portrait", "bullet")
    assert r["math_errors"] == []
    assert any("KaTeX" in n for n in font_names(r["path"]))
    with pymupdf.open(r["path"]) as doc:
        text = "".join(p.get_text() for p in doc)
    assert "\\frac" not in text and "$" not in text


@pytest.mark.parametrize("style", ["bullet", "mindmap"])
def test_math_in_both_styles(tmp_path, style):
    r = build_pdf(with_math(), neutral_theme(), tmp_path / f"{style}.pdf", "A4", "landscape", style)
    assert r["math_errors"] == [] and any("KaTeX" in n for n in font_names(r["path"]))


def test_invalid_latex_is_reported_but_pdf_still_builds(tmp_path):
    c = with_math()
    c["sections"][1]["equations"] = [{"latex": r"\frac{1"}]
    r = build_pdf(c, neutral_theme(), tmp_path / "bad.pdf", "A4", "portrait", "bullet")
    assert r["pages"] >= 1
    assert len(r["math_errors"]) == 1 and r"\frac{1" in r["math_errors"][0]


def test_math_result_key_present_without_math(tmp_path):
    r = build_pdf(load("content_min.json"), neutral_theme(), tmp_path / "p.pdf", "A4", "portrait", "bullet")
    assert r["math_errors"] == []


def test_print_html_fallback_still_typesets_in_a_browser(tmp_path, monkeypatch):
    import build_pdf as mod
    monkeypatch.setattr(mod, "ENGINES", ["print-html"])
    r = mod.build_pdf(with_math(), neutral_theme(), tmp_path / "x.pdf", "A4", "portrait", "bullet")
    assert "katex.render" in open(r["path"], encoding="utf-8").read()


def test_equation_schema_validation():
    c = with_math()
    assert validate_content(c) == []
    c["sections"][1]["equations"] = [{"latex": ""}]
    assert any("equations" in e for e in validate_content(c))
    c["sections"][1]["equations"] = [{"latex": "x", "caption": 5}]
    assert any("caption" in e for e in validate_content(c))
    c["sections"][1]["equations"] = "x=1"
    assert any("equations" in e for e in validate_content(c))


def test_cli_pdf_prints_math_errors(tmp_path):
    (tmp_path / "t.json").write_text(json.dumps(neutral_theme()))
    c = with_math()
    c["sections"][1]["equations"] = [{"latex": r"\badmacro{x}"}]
    (tmp_path / "c.json").write_text(json.dumps(c, ensure_ascii=False), encoding="utf-8")
    r = subprocess.run([sys.executable, str(CLI), "pdf", "--content", str(tmp_path / "c.json"), "--theme", str(tmp_path / "t.json"),
                        "--paper", "A4", "--orientation", "portrait", "--style", "bullet", "--out", str(tmp_path / "o.pdf")],
                       capture_output=True, text=True)
    assert r.returncode == 0, r.stderr
    assert json.loads(r.stdout)["math_errors"]


def test_katex_css_has_no_external_urls():
    from build_pdf import katex_css
    css = katex_css()
    assert "url(fonts/" not in css and "data:font/woff2;base64," in css


def test_wide_equation_scales_to_fit_mobile_page(tmp_path):
    from test_build_pdf import text_boxes_inside_page
    c = load("content_min.json")
    c["sections"][0]["equations"] = [{"latex": "+".join(f"a_{{{i}}}x^{{{i}}}" for i in range(1, 30))}]
    r = build_pdf(c, neutral_theme(), tmp_path / "w.pdf", "mobile", "portrait", "bullet")
    assert r["math_errors"] == [] and text_boxes_inside_page(r["path"])


def test_weasyprint_is_skipped_when_math_present(tmp_path, monkeypatch):
    import build_pdf as mod
    called = []
    monkeypatch.setattr(mod, "ENGINES", ["weasyprint", "print-html"])
    def fake_weasyprint(html, out):
        called.append(1)
        doc = pymupdf.open()
        doc.new_page()
        doc.save(out)
        return []

    monkeypatch.setitem(mod.RENDERERS, "weasyprint", fake_weasyprint)
    assert mod.build_pdf(with_math(), neutral_theme(), tmp_path / "a.pdf", "A4", "portrait", "bullet")["engine"] == "print-html"
    assert called == []
    mod.build_pdf(load("content_min.json"), neutral_theme(), tmp_path / "b.pdf", "A4", "portrait", "bullet")
    assert called == [1]


def test_html_summary_keeps_equations_as_latex_text(tmp_path):
    from build_html import build_html
    from playwright.sync_api import sync_playwright
    out = build_html(with_math(), neutral_theme(), tmp_path / "s.html", False)
    with sync_playwright() as p:
        b = p.chromium.launch()
        page = b.new_page()
        page.goto(out.as_uri())
        page.wait_for_selector("#mindmap .mm-node")
        text = page.inner_text("#sec-s2")
        b.close()
    assert r"\frac{a}{b}+\sum_{i=1}^{n} x_i" in text and "สมการตัวอย่าง" in text
