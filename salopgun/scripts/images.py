"""Get pictures out of a pptx or pdf, tell which slides are worth a snapshot, and render slide snapshots."""
import hashlib
import re
import shutil
import subprocess
import tempfile
import xml.etree.ElementTree as ET
import zipfile
from pathlib import Path

MIN_SIDE = 120          # px: skip icons and bullets
DECORATIVE_PAGES = 3    # the same picture on this many slides is a logo or background, not content
PICTURE_EXTS = ("png", "jpg", "jpeg", "gif")
VISUAL_DRAWINGS = 10    # pdf: this many vector shapes on a page suggests a diagram

NS = {
    "a": "http://schemas.openxmlformats.org/drawingml/2006/main",
    "p": "http://schemas.openxmlformats.org/presentationml/2006/main",
    "r": "http://schemas.openxmlformats.org/officeDocument/2006/relationships",
    "m": "http://schemas.openxmlformats.org/officeDocument/2006/math",
    "c": "http://schemas.openxmlformats.org/drawingml/2006/chart",
    "rel": "http://schemas.openxmlformats.org/package/2006/relationships",
}


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


# ---- pptx structure (zip + XML only, no python-pptx needed) ----

def _rels(z: zipfile.ZipFile, name: str) -> dict:
    path = str(Path(name).parent / "_rels" / (Path(name).name + ".rels"))
    if path not in z.namelist():
        return {}
    root = ET.fromstring(z.read(path))
    return {r.get("Id"): r.get("Target") for r in root.findall("rel:Relationship", NS)}


def _resolve(base: str, target: str) -> str:
    parts = (Path(base).parent / target).parts
    out: list[str] = []
    for part in parts:
        if part == "..":
            out and out.pop()
        elif part != ".":
            out.append(part)
    return "/".join(out)


def _slides(z: zipfile.ZipFile) -> list:
    """(slide number, slide xml path) in the order the presentation shows them."""
    pres = "ppt/presentation.xml"
    rels = _rels(z, pres)
    root = ET.fromstring(z.read(pres))
    rid = f"{{{NS['r']}}}id"
    found = []
    for n, sld in enumerate(root.findall("p:sldIdLst/p:sldId", NS), start=1):
        target = rels.get(sld.get(rid))
        if target:
            found.append((n, _resolve(pres, target)))
    return found


def _slide_pictures(z: zipfile.ZipFile, slide_path: str) -> list:
    """Embedded picture files used by one slide, in document order."""
    rels = _rels(z, slide_path)
    embed = f"{{{NS['r']}}}embed"
    names = []
    for blip in ET.fromstring(z.read(slide_path)).iter(f"{{{NS['a']}}}blip"):
        target = rels.get(blip.get(embed))
        if target:
            names.append(_resolve(slide_path, target))
    return names


def _extract_pptx(src: Path, keep) -> None:
    with zipfile.ZipFile(src) as z:
        seen_on: dict = {}   # sha1 -> slide numbers
        order: list = []     # (sha1, first slide, ext, bytes)
        for number, slide_path in _slides(z):
            for name in _slide_pictures(z, slide_path):
                ext = name.rsplit(".", 1)[-1].lower()
                if ext not in PICTURE_EXTS:
                    continue
                data = z.read(name)
                digest = hashlib.sha1(data).hexdigest()
                if digest not in seen_on:
                    order.append((digest, number, ext, data))
                seen_on.setdefault(digest, set()).add(number)
        for digest, number, ext, data in order:
            if len(seen_on[digest]) < DECORATIVE_PAGES:
                keep(data, ext, number)


def _pptx_info(src: Path) -> list:
    info = []
    with zipfile.ZipFile(src) as z:
        for number, slide_path in _slides(z):
            root = ET.fromstring(z.read(slide_path))
            texts = "".join(t.text or "" for t in root.iter(f"{{{NS['a']}}}t"))
            pictures = len(list(root.iter(f"{{{NS['a']}}}blip")))
            charts = len(list(root.iter(f"{{{NS['c']}}}chart")))
            connectors = len(root.findall(".//p:cxnSp", NS))
            shapes = 0
            for sp in root.findall(".//p:sp", NS):
                is_text = sp.find("p:nvSpPr/p:nvPr/p:ph", NS) is not None or sp.find("p:nvSpPr/p:cNvSpPr", NS).get("txBox") == "1"
                shapes += 0 if is_text else 1
            equations = len(list(root.iter(f"{{{NS['m']}}}oMath")))
            info.append({"page": number, "text_chars": len(texts), "pictures": pictures + charts,
                         "drawings": shapes + connectors, "equations": equations,
                         "visual": bool(pictures or charts or connectors >= 2 or shapes >= 6)})
    return info


# ---- pdf ----

def _extract_pdf(src: Path, keep) -> None:
    import pymupdf

    with pymupdf.open(src) as doc:
        pages_of: dict = {}
        for number, page in enumerate(doc, start=1):
            for xref, *_ in page.get_images(full=True):
                pages_of.setdefault(xref, []).append(number)
        for xref, pages in pages_of.items():
            if len(pages) >= DECORATIVE_PAGES:
                continue
            info = doc.extract_image(xref)
            if info and info.get("ext") in ("png", "jpeg", "jpg"):
                keep(info["image"], info["ext"], pages[0])


def _pdf_info(src: Path) -> list:
    import pymupdf

    info = []
    with pymupdf.open(src) as doc:
        for number, page in enumerate(doc, start=1):
            pictures, drawings = len(page.get_images()), len(page.get_drawings())
            info.append({"page": number, "text_chars": len(page.get_text().strip()), "pictures": pictures,
                         "drawings": drawings, "equations": 0, "visual": bool(pictures or drawings >= VISUAL_DRAWINGS)})
    return info


# ---- public api ----

def extract_images(source: str, out_dir: str) -> list:
    src, out = Path(source), Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    found: list = []

    def keep(data: bytes, ext: str, slide: int) -> None:
        on_slide = sum(1 for f in found if f["slide"] == slide) + 1
        path = out / f"p{slide:02d}-img{on_slide}.{ext}"
        path.write_bytes(data)
        if _big_enough(path):
            found.append({"id": f"img{len(found) + 1}", "path": str(path.resolve()), "caption": "",
                          "kind": "picture", "slide": slide})
        else:
            path.unlink()

    suffix = src.suffix.lower()
    if suffix == ".pptx":
        _extract_pptx(src, keep)
    elif suffix == ".pdf":
        try:
            _extract_pdf(src, keep)
        except ImportError:
            return []
    return found


def slide_info(source: str) -> list:
    src = Path(source)
    if src.suffix.lower() == ".pptx":
        return _pptx_info(src)
    if src.suffix.lower() == ".pdf":
        try:
            return _pdf_info(src)
        except ImportError as exc:
            raise ValueError("reading PDF pages needs PyMuPDF, which is not installed here") from exc
    raise ValueError("slides: use a .pptx or .pdf file")


def parse_pages(spec: str, count: int) -> list:
    pages: list = []
    for part in spec.split(","):
        m = re.fullmatch(r"\s*(\d+)(?:\s*-\s*(\d+))?\s*", part)
        if not m:
            raise ValueError(f"--pages: cannot read '{part.strip()}', use e.g. 3,5,7-9")
        first, last = int(m.group(1)), int(m.group(2) or m.group(1))
        if first < 1 or last < first or last > count:
            raise ValueError(f"--pages: {part.strip()} is outside 1-{count}")
        pages.extend(p for p in range(first, last + 1) if p not in pages)
    return pages


def find_soffice():
    for name in ("soffice", "libreoffice"):
        found = shutil.which(name)
        if found:
            return found
    mac = Path("/Applications/LibreOffice.app/Contents/MacOS/soffice")
    return str(mac) if mac.exists() else None


def _pptx_to_pdf(src: Path, workdir: Path) -> Path:
    soffice = find_soffice()
    if not soffice:
        raise ValueError("snapshots of a .pptx need LibreOffice (soffice), which is not installed here. "
                         "Ask the user to export the slides as a PDF and use that file instead.")
    cmd = [soffice, "--headless", "--convert-to", "pdf", "--outdir", str(workdir), str(src)]
    try:
        subprocess.run(cmd, check=True, capture_output=True, timeout=180)
    except (subprocess.SubprocessError, OSError) as exc:
        raise ValueError(f"LibreOffice could not convert the slides ({exc}). Ask the user for a PDF export.") from exc
    pdf = workdir / (src.stem + ".pdf")
    if not pdf.exists():
        raise ValueError("LibreOffice produced no PDF. Ask the user for a PDF export.")
    return pdf


def snapshots(source: str, pages: list, out_dir: str, dpi: int = 110) -> list:
    try:
        import pymupdf
    except ImportError as exc:
        raise ValueError("snapshots need PyMuPDF, which is not installed here") from exc
    src, out = Path(source), Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    if src.suffix.lower() not in (".pdf", ".pptx"):
        raise ValueError("snapshots: use a .pptx or .pdf file")
    with tempfile.TemporaryDirectory() as tmp:
        pdf = src if src.suffix.lower() == ".pdf" else _pptx_to_pdf(src, Path(tmp))
        shots = []
        with pymupdf.open(pdf) as doc:
            for number in pages:
                if not 1 <= number <= len(doc):
                    raise ValueError(f"--pages: {number} is outside 1-{len(doc)}")
                path = out / f"p{number:02d}-slide.jpg"
                doc[number - 1].get_pixmap(dpi=dpi, alpha=False).save(str(path), jpg_quality=82)
                shots.append({"id": f"slide{number}", "path": str(path.resolve()), "caption": "",
                              "kind": "slide", "slide": number})
    return shots
