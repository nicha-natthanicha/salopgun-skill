"""SalopGun command line: theme, slides, images, snapshots, html, podcast, designpack. Exit code 2 = fix your input and re-run."""
import argparse
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from build_html import build_html  # noqa: E402
from build_podcast import build_podcast  # noqa: E402
from designpack import build_pack  # noqa: E402
from images import extract_images, parse_pages, slide_info, snapshots  # noqa: E402
from schema import validate_content, validate_dialogue  # noqa: E402
from theme import extract_theme  # noqa: E402

THEME_KEYS = ("primary", "secondary", "accent", "background", "text")


class InputError(Exception):
    pass


def read_json(path: str) -> dict:
    try:
        return json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise InputError(f"{path}: cannot read JSON ({exc})") from exc


def load_content(path: str) -> dict:
    content = read_json(path)
    errors = validate_content(content)
    base = Path(path).resolve().parent
    for img in content.get("images") or [] if not errors else []:
        target = Path(img["path"]) if Path(img["path"]).is_absolute() else base / img["path"]
        if not target.is_file():
            errors.append(f"images: file not found '{img['path']}' (paths are relative to {Path(path).name})")
    if errors:
        raise InputError("\n".join(errors))
    return content


def load_theme(path: str) -> dict:
    theme = read_json(path)
    errors = []
    for key in THEME_KEYS:
        value = theme.get(key) if isinstance(theme, dict) else None
        if not isinstance(value, str) or not re.fullmatch(r"#[0-9A-Fa-f]{6}", value):
            errors.append(f"{path}: {key} must look like #1E5AA8 (re-run the theme command)")
    if errors:
        raise InputError("\n".join(errors))
    return theme


def cmd_theme(a) -> None:
    theme = extract_theme(a.source)
    if a.user_theme:
        try:
            override = json.loads(a.user_theme)
        except json.JSONDecodeError as exc:
            raise InputError(f"--user-theme: not JSON ({exc})") from exc
        for key, value in override.items():
            if key not in THEME_KEYS:
                raise InputError(f"--user-theme: unknown key '{key}', use {', '.join(THEME_KEYS)}")
            if not isinstance(value, str) or not re.fullmatch(r"#[0-9A-Fa-f]{6}", value):
                raise InputError(f"--user-theme: {key} must look like #1E5AA8")
            theme[key] = value.upper()
        theme["source"] = "user"
    Path(a.out).write_text(json.dumps(theme, indent=2), encoding="utf-8")
    print(json.dumps(theme))


def cmd_images(a) -> None:
    print(json.dumps(extract_images(a.source, a.out_dir), ensure_ascii=False, indent=1))


def cmd_slides(a) -> None:
    print(json.dumps(slide_info(a.source), indent=1))


def cmd_snapshots(a) -> None:
    import pymupdf

    src = Path(a.source)
    count = None
    if src.suffix.lower() == ".pdf":
        with pymupdf.open(src) as doc:
            count = len(doc)
    else:
        count = len(slide_info(a.source))
    print(json.dumps(snapshots(a.source, parse_pages(a.pages, count), a.out_dir, a.dpi), ensure_ascii=False, indent=1))


def cmd_html(a) -> None:
    content = load_content(a.content)
    out = build_html(content, load_theme(a.theme), a.out, a.cards, base_dir=Path(a.content).resolve().parent)
    print(out)



def cmd_designpack(a) -> None:
    if a.size and a.paper != "custom":
        raise InputError("--size only works with --paper custom")
    size = None
    if a.paper == "custom":
        m = re.fullmatch(r"(\d+(?:\.\d+)?)x(\d+(?:\.\d+)?)", a.size or "")
        if not m:
            raise InputError("--size: use WIDTHxHEIGHT in mm, e.g. 100x150")
        size = (float(m.group(1)), float(m.group(2)))
    try:
        md = Path(a.md).read_text(encoding="utf-8")
    except OSError as exc:
        raise InputError(f"{a.md}: cannot read ({exc})") from exc
    result = build_pack(md, a.out_dir, images_dir=a.images_dir, name=a.name,
                        kinds=[k.strip() for k in a.kinds.split(",") if k.strip()], paper=a.paper,
                        orientation=a.orientation, pages=a.pages, style=a.style,
                        theme=load_theme(a.theme) if a.theme else None, size=size)
    print(json.dumps(result, ensure_ascii=False, indent=1))


def cmd_podcast(a) -> None:
    content = load_content(a.content)
    dialogue = read_json(a.dialogue)
    errors = validate_dialogue(dialogue, content)
    if errors:
        raise InputError("\n".join(errors))
    print(json.dumps(build_podcast(dialogue, content, a.out_dir), ensure_ascii=False))


def parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="salopgun")
    sub = p.add_subparsers(dest="cmd", required=True)
    t = sub.add_parser("theme", help="extract theme colours from the source file")
    t.add_argument("--source", required=True)
    t.add_argument("--user-theme", help='JSON overrides, e.g. {"primary": "#B00020"}')
    t.add_argument("--out", required=True)
    t.set_defaults(fn=cmd_theme)
    i = sub.add_parser("images", help="extract pictures from a pptx/pdf")
    i.add_argument("--source", required=True)
    i.add_argument("--out-dir", required=True)
    i.set_defaults(fn=cmd_images)
    s = sub.add_parser("slides", help="per-slide facts: pictures, shapes, equations, 'visual' hint")
    s.add_argument("--source", required=True)
    s.set_defaults(fn=cmd_slides)
    n = sub.add_parser("snapshots", help="render whole slides to JPEG images")
    n.add_argument("--source", required=True)
    n.add_argument("--pages", required=True, help="e.g. 3,5,7-9 (1-based)")
    n.add_argument("--out-dir", required=True)
    n.add_argument("--dpi", type=int, default=110)
    n.set_defaults(fn=cmd_snapshots)
    h = sub.add_parser("html", help="build the interactive HTML summary")
    h.add_argument("--content", required=True)
    h.add_argument("--theme", required=True)
    h.add_argument("--cards", action="store_true")
    h.add_argument("--out", required=True)
    h.set_defaults(fn=cmd_html)
    k = sub.add_parser("designpack", help="package the summary md + prompt + images for Claude Design")
    k.add_argument("--md", required=True, help="the summary you wrote, content only")
    k.add_argument("--images-dir", help="folder with the images the md links to as images/<file>")
    k.add_argument("--kinds", required=True, help="comma list of: concise,teaching,exam")
    k.add_argument("--paper", required=True, choices=["A4", "B5", "mobile", "desktop", "custom"])
    k.add_argument("--size", help="custom size in mm, WIDTHxHEIGHT")
    k.add_argument("--orientation", required=True, choices=["portrait", "landscape"])
    k.add_argument("--pages", type=int, help="page limit for the concise sheet")
    k.add_argument("--style", required=True, choices=["bullet", "mindmap"])
    k.add_argument("--theme", help="theme.json from the theme command")
    k.add_argument("--name", default="summary")
    k.add_argument("--out-dir", required=True)
    k.set_defaults(fn=cmd_designpack)
    c = sub.add_parser("podcast", help="write NotebookLM podcast scripts")
    c.add_argument("--content", required=True)
    c.add_argument("--dialogue", required=True)
    c.add_argument("--out-dir", required=True)
    c.set_defaults(fn=cmd_podcast)
    return p


def main(argv=None) -> int:
    args = parser().parse_args(argv)
    try:
        args.fn(args)
    except (InputError, ValueError, OSError) as exc:
        print(str(exc), file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
