"""Pull embedded pictures out of a pptx or pdf so the summary can reuse them."""
import re
import zipfile
from pathlib import Path

MIN_SIDE = 120  # px: skip icons, bullets and logos


def _big_enough(path: Path) -> bool:
    try:
        from PIL import Image
    except ImportError:
        return path.stat().st_size > 8_000
    try:
        with Image.open(path) as im:
            return min(im.size) >= MIN_SIDE
    except OSError:
        return False


def _slide_order(z: zipfile.ZipFile) -> list[str]:
    """Media files in the order their slides use them."""
    slides = sorted((n for n in z.namelist() if re.fullmatch(r"ppt/slides/slide\d+\.xml", n)),
                    key=lambda n: int(re.search(r"(\d+)", n.rsplit("/", 1)[1]).group(1)))
    order: list[str] = []
    for slide in slides:
        rels = slide.replace("slides/", "slides/_rels/") + ".rels"
        if rels not in z.namelist():
            continue
        for target in re.findall(r'Target="\.\./media/([^"]+)"', z.read(rels).decode("utf-8", "replace")):
            name = f"ppt/media/{target}"
            if name not in order:
                order.append(name)
    return order


def extract_images(source: str, out_dir: str) -> list[dict]:
    src, out = Path(source), Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    found: list[dict] = []

    def keep(data: bytes, ext: str) -> None:
        path = out / f"img{len(found) + 1}.{ext}"
        path.write_bytes(data)
        if _big_enough(path):
            found.append({"id": f"img{len(found) + 1}", "path": str(path.resolve()), "caption": ""})
        else:
            path.unlink()

    suffix = src.suffix.lower()
    if suffix == ".pptx":
        with zipfile.ZipFile(src) as z:
            for name in _slide_order(z):
                ext = name.rsplit(".", 1)[-1].lower()
                if ext in ("png", "jpg", "jpeg", "gif"):
                    keep(z.read(name), ext)
    elif suffix == ".pdf":
        try:
            import pymupdf
        except ImportError:
            return []
        with pymupdf.open(src) as doc:
            seen = set()
            for page in doc:
                for xref, *_ in page.get_images(full=True):
                    if xref in seen:
                        continue
                    seen.add(xref)
                    info = doc.extract_image(xref)
                    if info and info.get("ext") in ("png", "jpeg", "jpg"):
                        keep(info["image"], info["ext"])
    return found
