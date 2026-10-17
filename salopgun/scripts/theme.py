"""Theme colours: pull them from the source file, fall back to neutral, keep text readable."""
import colorsys
import re
import zipfile
from collections import Counter
from pathlib import Path

DARK_BACKGROUND = "#121417"
MIN_CONTRAST = 4.5


def neutral_theme() -> dict:
    return {
        "primary": "#2F5D8A",
        "secondary": "#6B7A8F",
        "accent": "#E0A100",
        "background": "#FFFFFF",
        "text": "#1F2328",
        "source": "neutral",
    }


def _rgb(hex_color: str) -> tuple[int, int, int]:
    h = hex_color.lstrip("#")
    return int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)


def _hex(rgb) -> str:
    return "#" + "".join(f"{max(0, min(255, round(c))):02X}" for c in rgb)


def _luminance(hex_color: str) -> float:
    def channel(c: int) -> float:
        s = c / 255
        return s / 12.92 if s <= 0.03928 else ((s + 0.055) / 1.055) ** 2.4

    r, g, b = (channel(c) for c in _rgb(hex_color))
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def contrast_ratio(fg: str, bg: str) -> float:
    a, b = sorted((_luminance(fg), _luminance(bg)), reverse=True)
    return (a + 0.05) / (b + 0.05)


def _toward(hex_color: str, target: tuple[int, int, int], amount: float) -> str:
    r, g, b = _rgb(hex_color)
    return _hex((r + (target[0] - r) * amount, g + (target[1] - g) * amount, b + (target[2] - b) * amount))


def _readable(color: str, bg: str) -> str:
    if contrast_ratio(color, bg) >= MIN_CONTRAST:
        return color
    targets = sorted([(0, 0, 0), (255, 255, 255)], key=lambda t: -contrast_ratio(_hex(t), bg))
    for target in targets:
        for step in range(1, 21):
            candidate = _toward(color, target, step / 20)
            if contrast_ratio(candidate, bg) >= MIN_CONTRAST:
                return candidate
    return _hex(targets[0])


def palette(theme: dict, dark: bool) -> dict:
    """Every colour a template needs, with each text role checked against its background."""
    bg = DARK_BACKGROUND if dark else theme["background"]
    if not dark and _luminance(bg) < 0.5:
        bg = "#FFFFFF"  # light mode always gets a light page, even for dark slide decks
    text = _readable("#E6E8EB" if dark else theme["text"], bg)
    primary = _readable(theme["primary"], bg)
    muted = _readable(_toward(text, _rgb(bg), 0.3), bg)
    code_bg = _toward(bg, _rgb(text), 0.05)
    if contrast_ratio(text, code_bg) < MIN_CONTRAST:
        code_bg = bg
    on_primary = max(("#FFFFFF", "#000000"), key=lambda c: contrast_ratio(c, primary))
    return {
        "background": bg, "text": text, "primary": primary, "muted": muted,
        "accent": theme["accent"], "accent_text": _readable(theme["accent"], bg),
        "on_primary": on_primary, "code_bg": code_bg,
    }


def ensure_contrast(theme: dict, dark: bool) -> dict:
    fixed = dict(theme)
    if dark:
        fixed["background"] = DARK_BACKGROUND
        fixed["text"] = "#E6E8EB"
    bg = fixed["background"]
    for key in ("text", "primary"):
        fixed[key] = _readable(fixed[key], bg)
    return fixed


def _pptx_theme(path: Path) -> dict | None:
    with zipfile.ZipFile(path) as z:
        names = sorted(n for n in z.namelist() if re.fullmatch(r"ppt/theme/theme\d+\.xml", n))
        if not names:
            return None
        xml = z.read(names[0]).decode("utf-8", "replace")

    def slot(name: str) -> str | None:
        m = re.search(rf"<a:{name}>\s*<a:(?:srgbClr val|sysClr [^>]*?lastClr)=\"([0-9A-Fa-f]{{6}})\"", xml)
        return f"#{m.group(1).upper()}" if m else None

    primary = slot("accent1")
    if not primary:
        return None
    base = neutral_theme()
    return {
        "primary": primary,
        "secondary": slot("accent2") or base["secondary"],
        "accent": slot("accent3") or base["accent"],
        "background": slot("lt1") or base["background"],
        "text": slot("dk1") or base["text"],
        "source": "extracted",
    }


def _pdf_theme(path: Path) -> dict | None:
    try:
        import pymupdf
    except ImportError:
        return None
    counts: Counter = Counter()
    total = 0
    with pymupdf.open(path) as doc:
        for page in list(doc)[:3]:
            pix = page.get_pixmap(dpi=24, colorspace=pymupdf.csRGB, alpha=False)
            data = pix.samples
            for i in range(0, len(data), 3):
                r, g, b = data[i], data[i + 1], data[i + 2]
                total += 1
                _, light, sat = colorsys.rgb_to_hls(r / 255, g / 255, b / 255)
                if sat < 0.25 or light < 0.12 or light > 0.92:
                    continue  # white, black or grey
                counts[(r // 16 * 16 + 8, g // 16 * 16 + 8, b // 16 * 16 + 8)] += 1
    common = [c for c, n in counts.most_common(2) if n >= total * 0.01]
    if not common:
        return None
    base = neutral_theme()
    return {
        **base,
        "primary": _hex(common[0]),
        "secondary": _hex(common[1]) if len(common) > 1 else base["secondary"],
        "source": "extracted",
    }


def extract_theme(path: str) -> dict:
    p = Path(path)
    suffix = p.suffix.lower()
    found = None
    try:
        if suffix == ".pptx":
            found = _pptx_theme(p)
        elif suffix == ".pdf":
            found = _pdf_theme(p)
    except (zipfile.BadZipFile, OSError, RuntimeError, ValueError):
        found = None
    return found or neutral_theme()
