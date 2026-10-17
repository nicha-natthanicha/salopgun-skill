"""Write NotebookLM-ready podcast scripts: topic list, two-host dialogue, checklist, plus a Customize prompt."""
from pathlib import Path

from schema import validate_dialogue

PROMPT = (
    'สนทนาเป็นภาษาไทยระหว่างพิธีกรสองคน พูดครบทุกหัวข้อในส่วน "หัวข้อที่ต้องพูดถึง" ตามลำดับ '
    "ห้ามข้ามหรือย่อหัวข้อใด ให้เวลากับหัวข้อที่ทำเครื่องหมาย [เน้น] มากกว่า"
)
SPEAKERS = {"A": "พิธีกร A", "B": "พิธีกร B"}


def _topic_lines(section: dict, depth: int = 0) -> list[str]:
    mark = " [เน้น]" if section.get("focused") else ""
    out = [f"{'  ' * depth}- {section['title']}{mark}"]
    for child in section.get("children") or []:
        out.extend(_topic_lines(child, depth + 1))
    return out


def _episode_md(ep: dict, number: int, total: int, content: dict) -> str:
    by_id = {s["id"]: s for s in content["sections"]}
    sections = [by_id[sid] for sid in ep["section_ids"]]
    parts = [f"# {content['title']} — ตอนที่ {number}/{total}: {ep['title']}", "", "## หัวข้อที่ต้องพูดถึง", ""]
    for s in sections:
        parts.extend(_topic_lines(s))
    parts += ["", "---", "", "## บทสนทนา", ""]
    current = None
    for line in ep["lines"]:
        if line["section_id"] in by_id and line["section_id"] != current:
            current = line["section_id"]
            parts += [f"### {by_id[current]['title']}", ""]
        parts += [f"**{SPEAKERS[line['speaker']]}:** {line['text']}", ""]
    parts += ["---", "", "## Checklist", "", "ฟังแล้วติ๊กว่าพอดแคสต์พูดถึงหัวข้อเหล่านี้ครบไหม", ""]
    for s in sections:
        parts.append(f"- [ ] {s['title']}")
        parts.extend(f"  - [ ] {c['title']}" for c in s.get("children") or [])
    return "\n".join(parts) + "\n"


def build_podcast(dialogue: dict, content: dict, out_dir) -> list[str]:
    errors = validate_dialogue(dialogue, content)
    if errors:
        raise ValueError("invalid dialogue:\n" + "\n".join(errors))
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    episodes = dialogue["episodes"]
    paths = []
    for n, ep in enumerate(episodes, start=1):
        path = out / f"podcast-{n:02d}.md"
        path.write_text(_episode_md(ep, n, len(episodes), content), encoding="utf-8")
        paths.append(str(path))
    tips = [
        "วิธีใช้กับ NotebookLM",
        "1. สร้าง notebook ใหม่ แล้วอัปโหลดไฟล์ podcast-XX.md ทีละตอน (หนึ่ง notebook ต่อหนึ่งตอน)",
        "2. กด Audio Overview > Customize แล้ววางข้อความด้านล่าง",
        "3. เลือกความยาว Longer แล้วกด Generate",
        "",
        PROMPT,
    ]
    if len(episodes) > 3:
        tips.insert(4, f"หมายเหตุ: มี {len(episodes)} ตอน แต่ NotebookLM รุ่นฟรีสร้างเสียงได้วันละ 3 ตอน")
    (out / "notebooklm-prompt.txt").write_text("\n".join(tips) + "\n", encoding="utf-8")
    return paths
