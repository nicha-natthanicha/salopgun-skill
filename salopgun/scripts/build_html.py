"""Build the single-file interactive HTML summary from content.json and a theme."""
import base64
import copy
import json
import mimetypes
from pathlib import Path

from schema import validate_content
from theme import ensure_contrast

ASSETS = Path(__file__).resolve().parent.parent / "assets"

TABS = (
    "<nav class='tabs' role='tablist'>"
    "<button data-tab='summary' role='tab' aria-selected='true'>สรุป</button>"
    "<button data-tab='cards' role='tab' aria-selected='false'>การ์ด</button>"
    "</nav>"
)
CARDS = "<div id='cards' hidden></div>"


def font_css() -> str:
    rules = []
    for weight, name in ((400, "Sarabun-Regular.ttf"), (700, "Sarabun-Bold.ttf")):
        data = base64.b64encode((ASSETS / "fonts" / name).read_bytes()).decode()
        rules.append(
            f"@font-face {{ font-family: Sarabun; font-weight: {weight}; "
            f"src: url(data:font/ttf;base64,{data}) format('truetype'); }}"
        )
    return "\n".join(rules)


def _vars(theme: dict) -> str:
    return (
        f"--primary: {theme['primary']}; --secondary: {theme['secondary']}; "
        f"--bg: {theme['background']}; --text: {theme['text']};"
    )


def theme_css(theme: dict) -> str:
    light = ensure_contrast(theme, dark=False)
    dark = ensure_contrast(theme, dark=True)
    return (
        ":root, [data-theme='light'] { " + _vars(light) +
        " --surface: color-mix(in srgb, var(--bg) 94%, var(--primary)); --line: color-mix(in srgb, var(--text) 15%, var(--bg));"
        " --muted: color-mix(in srgb, var(--text) 70%, var(--bg)); --code-bg: color-mix(in srgb, var(--text) 6%, var(--bg));"
        " --on-primary: #FFFFFF; --accent-text: #8A6100; --ok: #1A7F37; --ok-bg: #DAFBE1; --bad: #CF222E; --bad-bg: #FFEBE9; }\n"
        "[data-theme='dark'] { " + _vars(dark) +
        " --surface: #1B1F24; --line: #30363D; --muted: #9DA5AE; --code-bg: #0D1117;"
        " --on-primary: #121417; --accent-text: #E3B341; --ok: #3FB950; --ok-bg: #12261E; --bad: #F85149; --bad-bg: #2D1517; }"
    )


def _embed_json(data: dict) -> str:
    text = json.dumps(data, ensure_ascii=False)
    return (
        text.replace("<", "\\u003c").replace(">", "\\u003e").replace("&", "\\u0026")
        .replace("\u2028", "\\u2028").replace("\u2029", "\\u2029")
    )


def _with_image_data(content: dict, base_dir: Path) -> dict:
    data = copy.deepcopy(content)
    for img in data.get("images") or []:
        path = Path(img["path"])
        if not path.is_absolute():
            path = base_dir / path
        mime = mimetypes.guess_type(path.name)[0] or "image/png"
        img["src"] = f"data:{mime};base64,{base64.b64encode(path.read_bytes()).decode()}"
        del img["path"]
    return data


def build_html(content: dict, theme: dict, out_path, with_cards: bool, base_dir=None) -> Path:
    errors = validate_content(content)
    if errors:
        raise ValueError("invalid content:\n" + "\n".join(errors))
    data = _with_image_data(content, Path(base_dir) if base_dir else Path.cwd())
    page = (ASSETS / "summary.html").read_text(encoding="utf-8")
    page = (
        page.replace("/*__FONT__*/", font_css())
        .replace("/*__THEME__*/", theme_css(theme))
        .replace("<!--__TABS__-->", TABS if with_cards else "")
        .replace("<!--__CARDS__-->", CARDS if with_cards else "")
        .replace('<html lang="th"', f'<html lang="{content.get("language") or "th"}"')
        .replace("__CONTENT_JSON__", _embed_json(data))
    )
    out = Path(out_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(page, encoding="utf-8")
    return out
