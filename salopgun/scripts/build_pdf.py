"""Build a print-ready summary (bullet or mind map) and render it to PDF with whatever engine exists."""
import base64
import functools
import re
import mimetypes
from html import escape
from pathlib import Path

from build_html import font_css
from schema import validate_content
from theme import palette

ASSETS = Path(__file__).resolve().parent.parent / "assets"
ENGINES = ["playwright", "weasyprint", "print-html"]
PAPERS = {"A4": (210, 297), "B5": (176, 250), "mobile": (90, 160), "desktop": (167, 297)}
STYLES = ("bullet", "mindmap")
MATH = re.compile(r"(?<!\\)\$(?!\s)([^$\n]+?)(?<!\s)(?<!\\)\$(?!\d)")  # $...$ ; "$5 and $10" is not math


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


def _plain(text: str) -> str:
    return escape(text.replace("\\$", "$"))


def rich(text: str) -> str:
    """Escape text and mark $...$ spans as LaTeX for KaTeX. Use \\$ for a literal dollar sign."""
    out, pos = [], 0
    for m in MATH.finditer(text):
        out.append(_plain(text[pos:m.start()]))
        out.append(f'<span class="tex">{escape(m.group(1))}</span>')
        pos = m.end()
    out.append(_plain(text[pos:]))
    return "".join(out)


def _equations(s: dict) -> str:
    parts = []
    for eq in s.get("equations") or []:
        caption = f'<div class="eqcap">{rich(eq["caption"])}</div>' if eq.get("caption") else ""
        parts.append(f'<div class="eq"><div class="tex display">{escape(eq["latex"])}</div>{caption}</div>')
    return "".join(parts)


@functools.lru_cache(maxsize=1)
def katex_css() -> str:
    """katex.min.css with its fonts embedded, so the page needs no network."""
    folder = ASSETS / "katex"
    css = (folder / "katex.min.css").read_text(encoding="utf-8")

    def embed(m):
        data = base64.b64encode((folder / "fonts" / f"{m.group(1)}.woff2").read_bytes()).decode()
        return f"src:url(data:font/woff2;base64,{data}) format(\"woff2\")"

    return re.sub(r'src:url\(fonts/([A-Za-z0-9_-]+)\.woff2\) format\("woff2"\)(?:,url\([^)]*\) format\("[a-z]+"\))*', embed, css)


KATEX_RUN = """<script>
document.querySelectorAll('.tex').forEach(function (el) {
  var tex = el.textContent, display = el.classList.contains('display');
  try { katex.render(tex, el, { displayMode: display, throwOnError: true }); }
  catch (e) { el.className += ' tex-error'; el.setAttribute('data-error', tex + '  (' + e.message + ')'); el.textContent = tex; }
  if (display && el.scrollWidth > el.clientWidth + 1) { el.style.zoom = el.clientWidth / el.scrollWidth; }
});
</script>"""


def _katex_block() -> str:
    js = (ASSETS / "katex" / "katex.min.js").read_text(encoding="utf-8")
    return f"<script>{js}</script>{KATEX_RUN}"


def _image_src(img: dict, base_dir: Path) -> str:
    path = Path(img["path"])
    if not path.is_absolute():
        path = base_dir / path
    mime = mimetypes.guess_type(path.name)[0] or "image/png"
    return f"data:{mime};base64,{base64.b64encode(path.read_bytes()).decode()}"


def _section_bullet(s: dict, depth: int, images: dict) -> str:
    tag = f"h{min(2 + depth, 4)}"
    parts = [f'<div class="{"child " if depth else ""}{"focused" if s.get("focused") else ""}">',
             f"<{tag}>{rich(s['title'])}</{tag}>"]
    if s.get("summary"):
        parts.append(f"<p>{rich(s['summary'])}</p>")
    if s.get("points"):
        parts.append("<ul>" + "".join(f"<li>{rich(p)}</li>" for p in s["points"]) + "</ul>")
    parts.append(_equations(s))
    for block in s.get("code") or []:
        parts.append(f"<pre>{escape(block['code'])}</pre>")
    for ref in s.get("image_ids") or []:
        img = images.get(ref)
        if img:
            parts.append(f'<figure><img src="{img["src"]}" alt=""><figcaption>{escape(img.get("caption") or "")}</figcaption></figure>')
    parts.extend(_section_bullet(c, depth + 1, images) for c in s.get("children") or [])
    parts.append("</div>")
    return "".join(parts)


def _branch_items(s: dict) -> str:
    items = [f"<li>{rich(p)}</li>" for p in s.get("points") or []]
    for c in s.get("children") or []:
        items.append(f'<li><span class="sub">{rich(c["title"])}</span>{_branch_items(c)}{_equations(c)}</li>')
    return "<ul>" + "".join(items) + "</ul>" if items else ""


def _body(content: dict, style: str, images: dict) -> str:
    title = escape(content["title"])
    if style == "mindmap":
        branches = "".join(
            f'<div class="branch{" focused" if s.get("focused") else ""}"><h2>{rich(s["title"])}</h2>'
            f'{"<p>" + rich(s["summary"]) + "</p>" if s.get("summary") else ""}{_branch_items(s)}{_equations(s)}</div>'
            for s in content["sections"])
        body = f'<div class="mm-root"><span>{title}</span></div><div class="mm-grid">{branches}</div>'
    else:
        body = f'<h1>{title}</h1><div class="rule"></div>' + "".join(
            _section_bullet(s, 0, images) for s in content["sections"])
    glossary = content.get("glossary") or []
    if glossary:
        rows = "".join(f"<dt>{escape(g['term'])}</dt><dd>{rich(g['definition'])}</dd>" for g in glossary)
        body += f'<div class="glossary"><h2>คำศัพท์</h2><dl>{rows}</dl></div>'
    return body


def print_html(content: dict, theme: dict, size_mm: tuple, style: str, base_dir=None) -> str:
    if style not in STYLES:
        raise ValueError(f"style must be one of {', '.join(STYLES)}")
    t = palette(theme, dark=False)
    w, h = size_mm
    base_pt = 9.5 if min(w, h) < 120 else 11
    margin = 7 if min(w, h) < 120 else 14
    images = {img["id"]: {**img, "src": _image_src(img, Path(base_dir) if base_dir else Path.cwd())}
              for img in content.get("images") or []}
    theme_vars = (
        f"--primary: {t['primary']}; --accent: {t['accent']}; --accent-text: {t['accent_text']}; "
        f"--bg: {t['background']}; --text: {t['text']}; --on-primary: {t['on_primary']}; --line: #D0D7DE; "
        f"--muted: {t['muted']}; --code-bg: {t['code_bg']}; --base: {base_pt}pt;"
    )
    page = (ASSETS / "print.html").read_text(encoding="utf-8")
    body = _body(content, style, images)
    has_math = 'class="tex' in body
    return (
        page.replace("/*__FONT__*/", font_css() + (katex_css() if has_math else ""))
        .replace("/*__PAGE__*/", f"@page {{ size: {w}mm {h}mm; margin: {margin}mm; }}")
        .replace("/*__THEME__*/", theme_vars)
        .replace("__TITLE__", escape(content["title"]))
        .replace('<html lang="th"', f'<html lang="{escape(content.get("language") or "th")}"')
        .replace("<!--__KATEX__-->", _katex_block() if has_math else "")
        .replace("<!--__BODY__-->", body)
    )


def _render_playwright(html: str, out: Path) -> list:
    from playwright.sync_api import sync_playwright

    with sync_playwright() as p:
        browser = p.chromium.launch()
        try:
            page = browser.new_page()
            page.set_content(html, wait_until="load")
            page.evaluate("document.fonts.ready")
            math_errors = page.evaluate("[...document.querySelectorAll('.tex-error')].map(e => e.dataset.error)")
            page.pdf(path=str(out), prefer_css_page_size=True, print_background=True)
        finally:
            browser.close()
    return math_errors


def _render_weasyprint(html: str, out: Path) -> list:
    import weasyprint

    weasyprint.HTML(string=html).write_pdf(str(out))
    return []


RENDERERS = {"playwright": _render_playwright, "weasyprint": _render_weasyprint}


def _count_pages(path: Path):
    try:
        from pypdf import PdfReader

        return len(PdfReader(str(path)).pages)
    except ImportError:
        pass
    try:
        import pymupdf

        with pymupdf.open(path) as doc:
            return len(doc)
    except ImportError:
        pass
    count = len(re.findall(rb"/Type\s*/Page(?![a-zA-Z])", path.read_bytes()))
    return count or None


def build_pdf(content: dict, theme: dict, out_path, paper: str, orientation: str, style: str,
              max_pages=None, custom_size=None, base_dir=None) -> dict:
    errors = validate_content(content)
    if errors:
        raise ValueError("invalid content:\n" + "\n".join(errors))
    html = print_html(content, theme, page_size_mm(paper, orientation, custom_size), style, base_dir)
    out = Path(out_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    has_math = "katex.render" in html
    for engine in ENGINES:
        if engine == "print-html":
            html_out = out.with_suffix(".html")
            html_out.write_text(html, encoding="utf-8")
            return {"path": str(html_out), "pages": 0, "over_limit": False, "engine": engine, "math_errors": []}
        if engine == "weasyprint" and has_math:
            continue  # no JavaScript there, so equations would print as raw LaTeX
        try:
            math_errors = RENDERERS[engine](html, out)
        except Exception:  # noqa: BLE001 - engine missing or broken: try the next one
            continue
        pages = _count_pages(out)
        return {"path": str(out), "pages": pages, "over_limit": bool(max_pages and pages and pages > max_pages),
                "engine": engine, "math_errors": math_errors}
    raise RuntimeError("no PDF engine configured")
