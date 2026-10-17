"""Build a print-ready summary (bullet or mind map) and render it to PDF with whatever engine exists."""
import base64
import mimetypes
from html import escape
from pathlib import Path

from build_html import font_css
from schema import validate_content
from theme import ensure_contrast

ASSETS = Path(__file__).resolve().parent.parent / "assets"
ENGINES = ["playwright", "weasyprint", "print-html"]
PAPERS = {"A4": (210, 297), "B5": (176, 250), "mobile": (90, 160), "desktop": (167, 297)}
STYLES = ("bullet", "mindmap")


def page_size_mm(paper: str, orientation: str, custom=None) -> tuple:
    if paper == "custom":
        if not custom or len(custom) != 2 or min(custom) <= 0:
            raise ValueError("custom paper needs (width_mm, height_mm)")
        w, h = custom
    elif paper in PAPERS:
        w, h = PAPERS[paper]
    else:
        raise ValueError(f"unknown paper '{paper}', use one of {', '.join(PAPERS)} or custom")
    if orientation not in ("portrait", "landscape"):
        raise ValueError("orientation must be portrait or landscape")
    if orientation == "landscape":
        w, h = h, w
    return (w, h)


def _image_src(img: dict, base_dir: Path) -> str:
    path = Path(img["path"])
    if not path.is_absolute():
        path = base_dir / path
    mime = mimetypes.guess_type(path.name)[0] or "image/png"
    return f"data:{mime};base64,{base64.b64encode(path.read_bytes()).decode()}"


def _section_bullet(s: dict, depth: int, images: dict) -> str:
    tag = f"h{min(2 + depth, 4)}"
    parts = [f'<div class="{"child " if depth else ""}{"focused" if s.get("focused") else ""}">',
             f"<{tag}>{escape(s['title'])}</{tag}>"]
    if s.get("summary"):
        parts.append(f"<p>{escape(s['summary'])}</p>")
    if s.get("points"):
        parts.append("<ul>" + "".join(f"<li>{escape(p)}</li>" for p in s["points"]) + "</ul>")
    for block in s.get("code") or []:
        parts.append(f"<pre>{escape(block['code'])}</pre>")
    for ref in s.get("image_ids") or []:
        img = images.get(ref)
        if img:
            parts.append(f'<figure><img src="{img["src"]}" alt=""><figcaption>{escape(img.get("caption", ""))}</figcaption></figure>')
    parts.extend(_section_bullet(c, depth + 1, images) for c in s.get("children") or [])
    parts.append("</div>")
    return "".join(parts)


def _branch_items(s: dict) -> str:
    items = [f"<li>{escape(p)}</li>" for p in s.get("points") or []]
    for c in s.get("children") or []:
        items.append(f'<li><span class="sub">{escape(c["title"])}</span>{_branch_items(c)}</li>')
    return "<ul>" + "".join(items) + "</ul>" if items else ""


def _body(content: dict, style: str, images: dict) -> str:
    title = escape(content["title"])
    if style == "mindmap":
        branches = "".join(
            f'<div class="branch{" focused" if s.get("focused") else ""}"><h2>{escape(s["title"])}</h2>'
            f'{"<p>" + escape(s["summary"]) + "</p>" if s.get("summary") else ""}{_branch_items(s)}</div>'
            for s in content["sections"])
        body = f'<div class="mm-root"><span>{title}</span></div><div class="mm-grid">{branches}</div>'
    else:
        body = f'<h1>{title}</h1><div class="rule"></div>' + "".join(
            _section_bullet(s, 0, images) for s in content["sections"])
    glossary = content.get("glossary") or []
    if glossary:
        rows = "".join(f"<dt>{escape(g['term'])}</dt><dd>{escape(g['definition'])}</dd>" for g in glossary)
        body += f'<div class="glossary"><h2>คำศัพท์</h2><dl>{rows}</dl></div>'
    return body


def print_html(content: dict, theme: dict, size_mm: tuple, style: str, base_dir=None) -> str:
    if style not in STYLES:
        raise ValueError(f"style must be one of {', '.join(STYLES)}")
    t = ensure_contrast(theme, dark=False)
    w, h = size_mm
    base_pt = 9.5 if min(w, h) < 120 else 11
    margin = 7 if min(w, h) < 120 else 14
    images = {img["id"]: {**img, "src": _image_src(img, Path(base_dir) if base_dir else Path.cwd())}
              for img in content.get("images") or []}
    theme_vars = (
        f"--primary: {t['primary']}; --accent: {t['accent']}; --bg: {t['background']}; --text: {t['text']}; "
        f"--on-primary: #FFFFFF; --line: #D0D7DE; --muted: #57606A; --code-bg: #F3F4F6; --base: {base_pt}pt;"
    )
    page = (ASSETS / "print.html").read_text(encoding="utf-8")
    return (
        page.replace("/*__FONT__*/", font_css())
        .replace("/*__PAGE__*/", f"@page {{ size: {w}mm {h}mm; margin: {margin}mm; }}")
        .replace("/*__THEME__*/", theme_vars)
        .replace("__TITLE__", escape(content["title"]))
        .replace('<html lang="th"', f'<html lang="{escape(content.get("language") or "th")}"')
        .replace("<!--__BODY__-->", _body(content, style, images))
    )


def _render_playwright(html: str, out: Path) -> None:
    from playwright.sync_api import sync_playwright

    with sync_playwright() as p:
        browser = p.chromium.launch()
        try:
            page = browser.new_page()
            page.set_content(html, wait_until="load")
            page.pdf(path=str(out), prefer_css_page_size=True, print_background=True)
        finally:
            browser.close()


def _render_weasyprint(html: str, out: Path) -> None:
    import weasyprint

    weasyprint.HTML(string=html).write_pdf(str(out))


def _count_pages(path: Path) -> int:
    from pypdf import PdfReader

    return len(PdfReader(str(path)).pages)


def build_pdf(content: dict, theme: dict, out_path, paper: str, orientation: str, style: str,
              max_pages=None, custom_size=None, base_dir=None) -> dict:
    errors = validate_content(content)
    if errors:
        raise ValueError("invalid content:\n" + "\n".join(errors))
    html = print_html(content, theme, page_size_mm(paper, orientation, custom_size), style, base_dir)
    out = Path(out_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    renderers = {"playwright": _render_playwright, "weasyprint": _render_weasyprint}
    for engine in ENGINES:
        if engine == "print-html":
            html_out = out.with_suffix(".html")
            html_out.write_text(html, encoding="utf-8")
            return {"path": str(html_out), "pages": 0, "over_limit": False, "engine": engine}
        try:
            renderers[engine](html, out)
        except Exception:  # noqa: BLE001 - engine missing or broken: try the next one
            continue
        pages = _count_pages(out)
        return {"path": str(out), "pages": pages, "over_limit": bool(max_pages) and pages > max_pages, "engine": engine}
    raise RuntimeError("no PDF engine configured")
