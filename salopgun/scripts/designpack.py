"""Package a written summary (md) with a ready-to-paste prompt and its images, to hand to Claude Design."""
import re
import shutil
import zipfile
from pathlib import Path

KINDS = ("concise", "teaching", "exam")
STYLES = ("bullet", "mindmap")
PAPERS = {"A4": (210, 297), "B5": (176, 250), "mobile": (90, 160), "desktop": (167, 297)}
IMAGE_EXTS = (".png", ".jpg", ".jpeg", ".gif", ".webp")

FENCE = re.compile(r"^```.*?^```[^\n]*$", re.S | re.M)
IMAGE_LINK = re.compile(r"!\[[^\]]*\]\(\s*<?([^)\s>]+)")
SCHEME = re.compile(r"^[a-z][a-z0-9+.-]*:", re.I)


def _num(x) -> str:
    return f"{x:g}"


def _size_mm(paper: str, orientation: str, size) -> tuple:
    if paper == "custom":
        if not size or len(size) != 2 or min(size) <= 0:
            raise ValueError("size: custom paper needs (width_mm, height_mm)")
        w, h = size
    elif paper in PAPERS:
        w, h = PAPERS[paper]
    else:
        raise ValueError(f"paper: unknown '{paper}', use one of {', '.join(PAPERS)} or custom")
    if orientation not in ("portrait", "landscape"):
        raise ValueError("orientation: must be portrait or landscape")
    return (h, w) if orientation == "landscape" else (w, h)


def _check_options(kinds, paper, orientation, pages, style, size) -> tuple:
    if not kinds:
        raise ValueError(f"kinds: choose at least one of {', '.join(KINDS)}")
    for kind in kinds:
        if kind not in KINDS:
            raise ValueError(f"kinds: unknown '{kind}', use {', '.join(KINDS)}")
    if style not in STYLES:
        raise ValueError(f"style: must be one of {', '.join(STYLES)}")
    if pages is not None and (not isinstance(pages, int) or isinstance(pages, bool) or pages < 1):
        raise ValueError("pages: must be a whole number from 1, or left out")
    return _size_mm(paper, orientation, size)


def _paper_phrase(paper: str, dims: tuple, orientation: str) -> str:
    w, h = (_num(d) for d in dims)
    direction = "แนวตั้ง" if orientation == "portrait" else "แนวนอน"
    if paper in ("A4", "B5"):
        return f"สร้างไฟล์ {paper} PDF {direction}"
    if paper == "mobile":
        return f"สร้างไฟล์ PDF ขนาดหน้าจอมือถือ {w}×{h} มม. {direction}"
    if paper == "desktop":
        return f"สร้างไฟล์ PDF ขนาดหน้าจอคอมพิวเตอร์ {w}×{h} มม. {direction}"
    return f"สร้างไฟล์ PDF ขนาด {w}×{h} มม. {direction}"


def _theme_line(theme) -> str:
    if not theme or theme.get("source") == "neutral":
        return "* โทนสี: ใช้สีและรูปแบบตามสไลด์ต้นฉบับ"
    colors = f"สีหลัก {theme['primary']}, สีรอง {theme['secondary']}, สีเน้น {theme['accent']}"
    if theme.get("source") == "user":
        return f"* โทนสี: ตามที่ผู้ใช้ระบุ ({colors})"
    return f"* โทนสี: ตามสไลด์ต้นฉบับ ({colors})"


def build_prompt(kinds, paper, orientation, pages, style, theme, size=None) -> str:
    dims = _check_options(kinds, paper, orientation, pages, style, size)
    lines = [
        f'{_paper_phrase(paper, dims, orientation)} ตามเนื้อหาในส่วน "เนื้อหา" ด้านล่างของไฟล์ md นี้',
        "โดยนำรูปจากสไลด์ในโฟลเดอร์ images/ ที่แนบมาประกอบชีทด้วย "
        "(ไฟล์ชื่อ pNN-… คือรูปจากสไลด์หน้า NN ตรงกับป้าย [p.NN] ในเนื้อหา) โดยมีเงื่อนไขดังนี้",
        "",
    ]
    if "concise" in kinds:
        limit = f"ภายใน {pages} หน้า" if pages else ""
        lines.append(f"* ไฟล์สรุปรวบรัด{limit} 1 ไฟล์ (แต่ห้ามตัดเนื้อหาสำคัญ และสรุปให้สมบูรณ์ไม่ตัดเนื้อหา) "
                     "โดยนำรูปจากสไลด์มาประกอบชีทด้วย")
    if "teaching" in kinds:
        lines.append("* ไฟล์ชีทสอน 1 ไฟล์ โดยนำรูปจากสไลด์มาประกอบชีทด้วย")
    if "exam" in kinds:
        lines.append("* ไฟล์เกร็งข้อสอบ 1 ไฟล์")
    style_text = ("bullet (หัวข้อหลักแล้วตามด้วยข้อย่อยเรียงต่อกัน)" if style == "bullet"
                  else "mindmap (แผนผังความคิด แตกกิ่งจากหัวข้อกลาง)")
    lines += [
        "",
        "รูปแบบและข้อกำหนดเพิ่มเติม:",
        f"* จัดเนื้อหาแบบ {style_text}",
        _theme_line(theme),
        "* คงป้ายอ้างอิงสไลด์ [p.x] และดาว ★ (จุดที่ต้องเน้น) ไว้ในชีท",
        "* สมการที่เขียนเป็น LaTeX ($…$ และ $$…$$) ให้จัดหน้าเป็นสมการที่อ่านง่าย",
        "* ห้ามตัดเนื้อหาสำคัญออกจากทุกไฟล์ ถ้าที่ไม่พอให้ย่อถ้อยคำ ไม่ใช่ตัดหัวข้อ",
    ]
    return "\n".join(lines)


def _check_markdown(md: str, images_dir) -> list:
    if not md.strip():
        raise ValueError("md: the summary is empty")
    body = FENCE.sub("", md)
    if body.count("$$") % 2:
        raise ValueError("md: an unclosed $$ display equation (the number of $$ is odd)")
    used: list = []
    for link in IMAGE_LINK.findall(body):
        if SCHEME.match(link):
            continue
        if not link.startswith("images/") or ".." in link:
            raise ValueError(f"md: image '{link}' must be inside images/ (e.g. images/p03-slide.jpg)")
        name = link[len("images/"):]
        if images_dir is None or not (Path(images_dir) / name).is_file():
            raise ValueError(f"md: image file not found: {name}")
        if name not in used:
            used.append(name)
    return used


def _title(md: str, fallback: str) -> str:
    m = re.search(r"^#\s+(.+)$", FENCE.sub("", md), re.M)
    return m.group(1).strip() if m else fallback


def build_pack(md: str, out_dir, images_dir=None, name: str = "summary", *, kinds, paper, orientation,
               pages, style, theme=None, size=None) -> dict:
    if not name or re.search(r"[\\/\x00]", name) or name.startswith("."):
        raise ValueError("name: use a plain file name without slashes")
    prompt = build_prompt(kinds, paper, orientation, pages, style, theme, size)
    used = _check_markdown(md, images_dir)

    out = Path(out_dir)
    (out / "images").mkdir(parents=True, exist_ok=True)
    copied = []
    if images_dir is not None:
        for f in sorted(Path(images_dir).iterdir()):
            if f.is_file() and f.suffix.lower() in IMAGE_EXTS:
                shutil.copy2(f, out / "images" / f.name)
                copied.append(f.name)

    document = "\n".join([
        f"# {_title(md, name)} — ชุดส่งต่อให้ Claude Design",
        "",
        "## วิธีใช้",
        "",
        f"1. เปิด Claude Design แล้วแนบไฟล์นี้ (`{name}.md`) พร้อมรูปทั้งหมดในโฟลเดอร์ `images/`",
        "2. วาง Prompt ด้านล่างลงในช่องพิมพ์ (หรือสั่งให้ทำตามส่วน Prompt ในไฟล์นี้)",
        "3. ถ้าผลลัพธ์ตัดเนื้อหาหรือไม่มีรูป ให้พิมพ์สั่งแก้ต่อได้เลย",
        "",
        "## Prompt",
        "",
        "```text",
        prompt,
        "```",
        "",
        "---",
        "",
        "## เนื้อหา",
        "",
        md.strip(),
        "",
    ])
    md_path = out / f"{name}.md"
    md_path.write_text(document, encoding="utf-8")

    zip_path = out / f"{name}.zip"
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as z:
        z.write(md_path, f"{name}.md")
        for image in copied:
            z.write(out / "images" / image, f"images/{image}")

    warnings = []
    if not used:
        warnings.append("ไม่มีรูปในเนื้อหาเลย (ไม่มีลิงก์ ![..](images/..)) ทั้งที่ prompt ให้นำรูปจากสไลด์มาประกอบ "
                        "(no images are linked in the md)")
    return {"md_path": str(md_path), "zip_path": str(zip_path), "images_copied": len(copied),
            "images_used": used, "warnings": warnings}
