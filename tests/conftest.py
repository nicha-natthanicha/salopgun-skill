import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
FIXTURES = Path(__file__).resolve().parent / "fixtures"
sys.path.insert(0, str(ROOT / "salopgun" / "scripts"))


def load(name: str) -> dict:
    return json.loads((FIXTURES / name).read_text(encoding="utf-8"))


import re
import zipfile

import pytest


@pytest.fixture(scope="session")
def blue_pptx(tmp_path_factory) -> str:
    """A one-slide deck whose theme accent1 is #1E5AA8 and accent2 is #F2A541."""
    from pptx import Presentation

    raw = tmp_path_factory.mktemp("pptx") / "raw.pptx"
    prs = Presentation()
    prs.slides.add_slide(prs.slide_layouts[0]).shapes.title.text = "บทที่ 1"
    prs.save(raw)
    out = raw.with_name("blue_theme.pptx")
    with zipfile.ZipFile(raw) as src, zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as dst:
        for item in src.infolist():
            data = src.read(item.filename)
            if item.filename == "ppt/theme/theme1.xml":
                xml = data.decode("utf-8")
                xml = re.sub(r'(<a:accent1>\s*<a:srgbClr val=")[0-9A-Fa-f]{6}', r"\g<1>1E5AA8", xml)
                xml = re.sub(r'(<a:accent2>\s*<a:srgbClr val=")[0-9A-Fa-f]{6}', r"\g<1>F2A541", xml)
                data = xml.encode("utf-8")
            dst.writestr(item, data)
    return str(out)


@pytest.fixture(scope="session")
def plain_pdf(tmp_path_factory) -> str:
    """Black text on white only: no theme colour to extract."""
    import pymupdf

    out = tmp_path_factory.mktemp("pdf") / "plain.pdf"
    doc = pymupdf.open()
    page = doc.new_page()
    page.insert_text((72, 72), "Plain lecture notes, black on white.", fontsize=14)
    doc.save(out)
    return str(out)


@pytest.fixture(scope="session")
def colored_pdf(tmp_path_factory) -> str:
    """A slide-like PDF with a big teal header bar."""
    import pymupdf

    out = tmp_path_factory.mktemp("pdf") / "colored.pdf"
    doc = pymupdf.open()
    page = doc.new_page()
    page.draw_rect(pymupdf.Rect(0, 0, page.rect.width, 150), color=None, fill=(0 / 255, 128 / 255, 128 / 255))
    page.insert_text((72, 300), "Body text", fontsize=14)
    doc.save(out)
    return str(out)
