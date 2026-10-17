"""SalopGun command line: theme, images, html, pdf, podcast. Exit code 2 = fix your input and re-run."""
import argparse
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from build_html import build_html  # noqa: E402
from build_pdf import build_pdf  # noqa: E402
from build_podcast import build_podcast  # noqa: E402
from images import extract_images  # noqa: E402
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
    if errors:
        raise InputError("\n".join(errors))
    return content


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


def cmd_html(a) -> None:
    content = load_content(a.content)
    out = build_html(content, read_json(a.theme), a.out, a.cards, base_dir=Path(a.content).resolve().parent)
    print(out)


def cmd_pdf(a) -> None:
    content = load_content(a.content)
    custom = None
    if a.paper == "custom":
        m = re.fullmatch(r"(\d+(?:\.\d+)?)x(\d+(?:\.\d+)?)", a.size or "")
        if not m:
            raise InputError("--size: use WIDTHxHEIGHT in mm, e.g. 100x150")
        custom = (float(m.group(1)), float(m.group(2)))
    result = build_pdf(content, read_json(a.theme), a.out, a.paper, a.orientation, a.style,
                       max_pages=a.max_pages, custom_size=custom, base_dir=Path(a.content).resolve().parent)
    print(json.dumps(result, ensure_ascii=False))


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
    h = sub.add_parser("html", help="build the interactive HTML summary")
    h.add_argument("--content", required=True)
    h.add_argument("--theme", required=True)
    h.add_argument("--cards", action="store_true")
    h.add_argument("--out", required=True)
    h.set_defaults(fn=cmd_html)
    d = sub.add_parser("pdf", help="build the PDF summary")
    d.add_argument("--content", required=True)
    d.add_argument("--theme", required=True)
    d.add_argument("--paper", required=True, choices=["A4", "B5", "mobile", "desktop", "custom"])
    d.add_argument("--size", help="custom size in mm, WIDTHxHEIGHT")
    d.add_argument("--orientation", required=True, choices=["portrait", "landscape"])
    d.add_argument("--style", required=True, choices=["bullet", "mindmap"])
    d.add_argument("--max-pages", type=int)
    d.add_argument("--out", required=True)
    d.set_defaults(fn=cmd_pdf)
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
    except (InputError, ValueError) as exc:
        print(str(exc), file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
