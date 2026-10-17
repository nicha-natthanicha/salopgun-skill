import json
import subprocess
import sys
from pathlib import Path

from conftest import FIXTURES, ROOT

CLI = ROOT / "salopgun" / "scripts" / "salopgun.py"


def run_cli(*args):
    return subprocess.run([sys.executable, str(CLI), *map(str, args)], capture_output=True, text=True)


def neutral_json(tmp_path) -> Path:
    out = tmp_path / "theme.json"
    assert run_cli("theme", "--source", tmp_path / "none.txt", "--out", out).returncode == 0
    return out


def test_invalid_content_exits_2(tmp_path):
    bad = tmp_path / "c.json"
    bad.write_text("{}")
    r = run_cli("html", "--content", bad, "--theme", neutral_json(tmp_path), "--out", tmp_path / "o.html")
    assert r.returncode == 2 and "sections" in r.stderr


def test_broken_json_exits_2(tmp_path):
    bad = tmp_path / "c.json"
    bad.write_text("{not json")
    r = run_cli("html", "--content", bad, "--theme", neutral_json(tmp_path), "--out", tmp_path / "o.html")
    assert r.returncode == 2 and "c.json" in r.stderr


def test_user_theme_overrides_extracted(tmp_path, blue_pptx):
    run_cli("theme", "--source", blue_pptx, "--user-theme", '{"primary": "#B00020"}', "--out", tmp_path / "t.json")
    t = json.loads((tmp_path / "t.json").read_text())
    assert t["primary"] == "#B00020" and t["source"] == "user" and t["secondary"] == "#F2A541"


def test_bad_user_color_exits_2(tmp_path, blue_pptx):
    r = run_cli("theme", "--source", blue_pptx, "--user-theme", '{"primary": "red"}', "--out", tmp_path / "t.json")
    assert r.returncode == 2 and "primary" in r.stderr


def test_html_pdf_podcast_end_to_end(tmp_path):
    theme = neutral_json(tmp_path)
    content = FIXTURES / "content_min.json"
    r = run_cli("html", "--content", content, "--theme", theme, "--cards", "--out", tmp_path / "s.html")
    assert r.returncode == 0, r.stderr
    assert "data-tab='cards'" in (tmp_path / "s.html").read_text(encoding="utf-8")
    r = run_cli("pdf", "--content", content, "--theme", theme, "--paper", "B5", "--orientation", "portrait",
                "--style", "mindmap", "--max-pages", "3", "--out", tmp_path / "s.pdf")
    assert r.returncode == 0, r.stderr
    result = json.loads(r.stdout)
    assert result["pages"] >= 1 and result["over_limit"] is False
    r = run_cli("podcast", "--content", content, "--dialogue", FIXTURES / "dialogue_by_chapter.json", "--out-dir", tmp_path / "pod")
    assert r.returncode == 0, r.stderr
    assert sorted(p.name for p in (tmp_path / "pod").iterdir()) == ["notebooklm-prompt.txt", "podcast-01.md", "podcast-02.md"]


def test_pdf_custom_size(tmp_path):
    r = run_cli("pdf", "--content", FIXTURES / "content_min.json", "--theme", neutral_json(tmp_path), "--paper", "custom",
                "--size", "100x150", "--orientation", "portrait", "--style", "bullet", "--out", tmp_path / "c.pdf")
    assert r.returncode == 0, r.stderr


def test_images_extracted_from_pptx(tmp_path):
    from PIL import Image
    from pptx import Presentation
    from pptx.util import Inches

    pic = tmp_path / "chart.png"
    Image.new("RGB", (400, 300), (30, 90, 168)).save(pic)
    prs = Presentation()
    prs.slides.add_slide(prs.slide_layouts[6]).shapes.add_picture(str(pic), Inches(1), Inches(1))
    deck = tmp_path / "deck.pptx"
    prs.save(deck)
    r = run_cli("images", "--source", deck, "--out-dir", tmp_path / "imgs")
    assert r.returncode == 0, r.stderr
    listed = json.loads(r.stdout)
    assert len(listed) == 1 and Path(listed[0]["path"]).exists() and listed[0]["id"] == "img1"


def test_skill_md_frontmatter():
    head = (ROOT / "salopgun" / "SKILL.md").read_text(encoding="utf-8").split("---")[1]
    assert "name: salopgun" in head and "description:" in head


def test_package_script_builds_zip(tmp_path):
    r = subprocess.run(["bash", str(ROOT / "package.sh")], capture_output=True, text=True, cwd=ROOT)
    assert r.returncode == 0, r.stderr
    import zipfile
    names = zipfile.ZipFile(ROOT / "dist" / "salopgun.zip").namelist()
    assert "salopgun/SKILL.md" in names and "salopgun/scripts/salopgun.py" in names
    assert not any("__pycache__" in n for n in names)
