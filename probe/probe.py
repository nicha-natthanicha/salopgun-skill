"""Probe the claude.ai code sandbox: which packages exist and which tool renders Thai PDFs.

Run: python probe.py  (writes probe-*.pdf next to the current directory and prints a report)
"""
import base64
import importlib
import platform
import shutil
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
FONT = HERE / "Sarabun-Regular.ttf"
THAI = (
    "การเรียนรู้ของเครื่องเป็นสาขาหนึ่งของปัญญาประดิษฐ์ที่ศึกษาวิธีทำให้คอมพิวเตอร์เรียนรู้จากข้อมูล"
    "โดยไม่ต้องเขียนโปรแกรมกำหนดกฎทุกข้อไว้ล่วงหน้า ตัวอย่างเช่น การจำแนกอีเมลขยะ การแนะนำสินค้า "
) * 6


def html() -> str:
    font = base64.b64encode(FONT.read_bytes()).decode() if FONT.exists() else ""
    return f"""<!doctype html><html lang="th"><meta charset="utf-8"><style>
@font-face {{ font-family: Sarabun; src: url(data:font/ttf;base64,{font}); }}
@page {{ size: 90mm 160mm; margin: 8mm; }}
body {{ font-family: Sarabun; font-size: 11pt; line-break: auto; word-break: normal; }}
</style><h1>ทดสอบภาษาไทย ปู่ ปี้ ก่ำ ญิ๋ง</h1><p>{THAI}</p></html>"""


def try_import(name: str) -> str:
    try:
        mod = importlib.import_module(name)
        return getattr(mod, "__version__", "ok")
    except Exception as exc:  # noqa: BLE001 - report every failure kind
        return f"MISSING ({type(exc).__name__})"


def render_playwright(out: Path) -> str:
    from playwright.sync_api import sync_playwright

    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page()
        page.set_content(html())
        page.pdf(path=str(out), prefer_css_page_size=True)
        browser.close()
    return "ok"


def render_weasyprint(out: Path) -> str:
    import weasyprint

    weasyprint.HTML(string=html()).write_pdf(str(out))
    return "ok"


def main() -> None:
    print("python", sys.version.split()[0], platform.platform())
    for name in ["playwright", "weasyprint", "fitz", "pypdf", "pptx", "PIL", "reportlab", "markdown"]:
        print(f"import {name}: {try_import(name)}")
    for binary in ["chromium", "chromium-browser", "google-chrome", "wkhtmltopdf", "libreoffice", "soffice"]:
        print(f"binary {binary}: {shutil.which(binary) or 'MISSING'}")
    for engine, fn in [("playwright", render_playwright), ("weasyprint", render_weasyprint)]:
        out = Path.cwd() / f"probe-{engine}.pdf"
        try:
            print(f"render {engine}: {fn(out)} -> {out}")
        except Exception as exc:  # noqa: BLE001
            print(f"render {engine}: FAILED {type(exc).__name__}: {exc}"[:300])


if __name__ == "__main__":
    main()
