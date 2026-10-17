import json
import subprocess
import sys
import zipfile
from pathlib import Path

import pytest
from PIL import Image

from conftest import ROOT
from designpack import build_pack, build_prompt
from theme import neutral_theme

CLI = ROOT / "salopgun" / "scripts" / "salopgun.py"

MD = """# Quiz 2 · Embedded System

## A · Communication Protocol [p.2–11] ★
**UART** ใช้ baud ตกลงกันก่อน · ★ SPI 4 สาย [p.12]

![ลำดับสัญญาณ UART](images/p03-slide.jpg)

| โปรโตคอล | สาย |
|---|---|
| SPI | 4 |

อัตรา $B = 1/100$ และสมการหลัก

$$
\\theta_{t+1} = \\theta_t - \\eta \\nabla L
$$
"""

ALL = ["concise", "teaching", "exam"]


def opts(**over):
    base = dict(kinds=ALL, paper="A4", orientation="portrait", pages=2, style="bullet", theme=None, size=None)
    base.update(over)
    return base


@pytest.fixture
def images_dir(tmp_path):
    d = tmp_path / "src-images"
    d.mkdir()
    Image.new("RGB", (300, 200), (10, 120, 200)).save(d / "p03-slide.jpg")
    Image.new("RGB", (300, 200), (200, 120, 10)).save(d / "p07-img1.png")
    return d


def pack(tmp_path, images_dir, md=MD, **over):
    return build_pack(md, tmp_path / "out", images_dir=images_dir, name="quiz2", **opts(**over))


# ---- prompt ----

def test_prompt_lists_only_chosen_kinds():
    one = build_prompt(**opts(kinds=["concise"], pages=3))
    assert "ไฟล์สรุปรวบรัดภายใน 3 หน้า 1 ไฟล์" in one
    assert "ชีทสอน" not in one and "เกร็งข้อสอบ" not in one
    everything = build_prompt(**opts())
    for line in ("ไฟล์สรุปรวบรัดภายใน 2 หน้า 1 ไฟล์", "ไฟล์ชีทสอน 1 ไฟล์", "ไฟล์เกร็งข้อสอบ 1 ไฟล์"):
        assert line in everything


def test_concise_without_page_limit_has_no_page_number():
    p = build_prompt(**opts(kinds=["concise"], pages=None))
    assert "ไฟล์สรุปรวบรัด 1 ไฟล์" in p and "ภายใน" not in p


def test_prompt_core_conditions_always_present():
    p = build_prompt(**opts())
    for needle in ("ห้ามตัดเนื้อหาสำคัญ", "นำรูปจากสไลด์", "[p.", "★", "LaTeX", "images/"):
        assert needle in p


@pytest.mark.parametrize("paper,orientation,size,expected", [
    ("A4", "portrait", None, "สร้างไฟล์ A4 PDF แนวตั้ง"),
    ("B5", "landscape", None, "สร้างไฟล์ B5 PDF แนวนอน"),
    ("mobile", "portrait", None, "90×160 มม."),
    ("desktop", "landscape", None, "297×167 มม."),
    ("custom", "portrait", (100, 150), "100×150 มม."),
])
def test_prompt_paper_and_orientation(paper, orientation, size, expected):
    assert expected in build_prompt(**opts(paper=paper, orientation=orientation, size=size))


def test_prompt_style_lines():
    assert "bullet" in build_prompt(**opts(style="bullet"))
    assert "mindmap" in build_prompt(**opts(style="mindmap"))


def test_prompt_theme_lines():
    default = build_prompt(**opts(theme=None))
    assert "ตามสไลด์" in default
    extracted = build_prompt(**opts(theme={**neutral_theme(), "primary": "#1E5AA8", "source": "extracted"}))
    assert "#1E5AA8" in extracted and "ตามสไลด์" in extracted
    user = build_prompt(**opts(theme={**neutral_theme(), "primary": "#B00020", "source": "user"}))
    assert "#B00020" in user and "ตามที่ผู้ใช้ระบุ" in user
    neutral = build_prompt(**opts(theme=neutral_theme()))
    assert "ตามสไลด์" in neutral and "#" not in neutral.split("โทนสี")[1].split("\n")[0]


# ---- pack ----

def test_md_has_prompt_then_content(tmp_path, images_dir):
    r = pack(tmp_path, images_dir)
    text = Path(r["md_path"]).read_text(encoding="utf-8")
    assert Path(r["md_path"]).name == "quiz2.md"
    assert text.index("## Prompt") < text.index("## เนื้อหา") and MD.strip() in text
    assert "```text" in text  # prompt sits in a code block so it copies cleanly
    assert build_prompt(**opts()) in text


def test_images_are_copied_and_zipped(tmp_path, images_dir):
    r = pack(tmp_path, images_dir)
    out = tmp_path / "out"
    assert (out / "images" / "p03-slide.jpg").exists() and (out / "images" / "p07-img1.png").exists()
    names = zipfile.ZipFile(r["zip_path"]).namelist()
    assert "quiz2.md" in names and "images/p03-slide.jpg" in names
    assert r["images_copied"] == 2 and r["images_used"] == ["p03-slide.jpg"]


def test_missing_image_reference_is_rejected(tmp_path, images_dir):
    with pytest.raises(ValueError, match="nope.jpg"):
        pack(tmp_path, images_dir, md=MD + "\n![x](images/nope.jpg)\n")


def test_image_outside_images_folder_is_rejected(tmp_path, images_dir):
    with pytest.raises(ValueError, match="images/"):
        pack(tmp_path, images_dir, md=MD + "\n![x](../secret.png)\n")


def test_remote_images_are_left_alone(tmp_path, images_dir):
    r = pack(tmp_path, images_dir, md=MD + "\n![x](https://example.com/a.png)\n")
    assert r["images_used"] == ["p03-slide.jpg"]


def test_unbalanced_display_math_is_rejected(tmp_path, images_dir):
    with pytest.raises(ValueError, match=r"\$\$"):
        pack(tmp_path, images_dir, md=MD + "\n$$\nx=1\n")


def test_dollar_signs_in_code_fences_are_ignored(tmp_path, images_dir):
    pack(tmp_path, images_dir, md=MD + "\n```bash\necho $$\n```\n")


def test_empty_md_is_rejected(tmp_path, images_dir):
    with pytest.raises(ValueError, match="empty"):
        pack(tmp_path, images_dir, md="  \n")


def test_warns_when_no_images_are_used(tmp_path, images_dir):
    r = pack(tmp_path, images_dir, md="# เรื่อง\n\nเนื้อหาล้วน\n")
    assert any("image" in w.lower() or "รูป" in w for w in r["warnings"])


def test_works_without_an_images_folder(tmp_path):
    r = build_pack("# เรื่อง\n\nเนื้อหา\n", tmp_path / "out", images_dir=None, name="x", **opts())
    assert Path(r["md_path"]).exists() and r["images_copied"] == 0


@pytest.mark.parametrize("bad", [dict(kinds=[]), dict(kinds=["poster"]), dict(style="radial"),
                                 dict(pages=0), dict(paper="A3"), dict(orientation="diagonal"),
                                 dict(paper="custom", size=None)])
def test_invalid_options_are_rejected(tmp_path, images_dir, bad):
    with pytest.raises(ValueError):
        pack(tmp_path, images_dir, **bad)


def test_name_cannot_escape_the_folder(tmp_path, images_dir):
    with pytest.raises(ValueError, match="name"):
        build_pack(MD, tmp_path / "out", images_dir=images_dir, name="../evil", **opts())


# ---- cli ----

def run_cli(*args):
    return subprocess.run([sys.executable, str(CLI), *map(str, args)], capture_output=True, text=True)


def test_cli_designpack_end_to_end(tmp_path, images_dir):
    (tmp_path / "s.md").write_text(MD, encoding="utf-8")
    (tmp_path / "t.json").write_text(json.dumps({**neutral_theme(), "primary": "#1E5AA8", "source": "extracted"}))
    r = run_cli("designpack", "--md", tmp_path / "s.md", "--images-dir", images_dir, "--kinds", "concise,exam",
                "--paper", "custom", "--size", "100x150", "--orientation", "landscape", "--pages", "2",
                "--style", "mindmap", "--theme", tmp_path / "t.json", "--name", "quiz2", "--out-dir", tmp_path / "pack")
    assert r.returncode == 0, r.stderr
    result = json.loads(r.stdout)
    text = Path(result["md_path"]).read_text(encoding="utf-8")
    assert "150×100 มม." in text and "เกร็งข้อสอบ" in text and "ชีทสอน" not in text and "#1E5AA8" in text
    assert Path(result["zip_path"]).exists()


def test_cli_designpack_bad_input_exits_2(tmp_path, images_dir):
    (tmp_path / "s.md").write_text(MD + "\n![x](images/nope.jpg)\n", encoding="utf-8")
    r = run_cli("designpack", "--md", tmp_path / "s.md", "--images-dir", images_dir, "--kinds", "concise",
                "--paper", "A4", "--orientation", "portrait", "--style", "bullet", "--out-dir", tmp_path / "pack")
    assert r.returncode == 2 and "nope.jpg" in r.stderr
    r = run_cli("designpack", "--md", tmp_path / "s.md", "--images-dir", images_dir, "--kinds", "poster",
                "--paper", "A4", "--orientation", "portrait", "--style", "bullet", "--out-dir", tmp_path / "pack")
    assert r.returncode == 2 and "poster" in r.stderr


def test_md_guide_and_skill_md_agree_on_the_rules():
    guide = (ROOT / "salopgun" / "references" / "md-guide.md").read_text(encoding="utf-8")
    skill = (ROOT / "salopgun" / "SKILL.md").read_text(encoding="utf-8")
    for needle in ("[p.N]", "★", "images/", "$$", "pNN-slide.jpg"):
        assert needle in guide
    for needle in ("สรุปรวบรัด", "ชีทสอน", "เกร็งข้อสอบ", "--kinds", "--style", "--paper", "Claude Design"):
        assert needle in skill
    assert "pdf --content" not in skill and "build_pdf" not in skill and "math_errors" not in skill
