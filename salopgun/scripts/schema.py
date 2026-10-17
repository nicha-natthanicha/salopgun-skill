"""Validators for content.json and dialogue.json. Stdlib only; each returns a list of errors."""

LAYOUTS = ("mobile", "desktop")
QUIZ_MIN, QUIZ_MAX = 5, 10


def _is_str(value) -> bool:
    return isinstance(value, str) and value.strip() != ""


def _walk(sections, path="sections"):
    for i, sec in enumerate(sections):
        yield f"{path}[{i}]", sec
        if isinstance(sec, dict):
            yield from _walk(sec.get("children") or [], f"{path}[{i}].children")


def validate_content(data: dict) -> list[str]:
    if not isinstance(data, dict):
        return ["content must be a JSON object"]
    errors: list[str] = []

    if not _is_str(data.get("title")):
        errors.append("title: required non-empty string")
    if data.get("layout") not in LAYOUTS:
        errors.append(f"layout: must be one of {', '.join(LAYOUTS)}")

    sections = data.get("sections")
    if not isinstance(sections, list) or not sections:
        errors.append("sections: required non-empty list")
        sections = []

    images = data.get("images") or []
    image_ids = {img.get("id") for img in images if isinstance(img, dict)}
    for i, img in enumerate(images):
        if not isinstance(img, dict) or not _is_str(img.get("id")) or not _is_str(img.get("path")):
            errors.append(f"images[{i}]: needs id and path")
        elif img.get("caption") is not None and not isinstance(img.get("caption"), str):
            errors.append(f"images[{i}].caption: must be a string")
        elif img.get("kind") not in (None, "picture", "slide"):
            errors.append(f"images[{i}].kind: must be picture or slide")
        elif img.get("slide") is not None and (not isinstance(img["slide"], int) or isinstance(img["slide"], bool) or img["slide"] < 1):
            errors.append(f"images[{i}].slide: must be a whole number from 1")

    seen: set[str] = set()
    for where, sec in _walk(sections):
        if not isinstance(sec, dict):
            errors.append(f"{where}: must be an object")
            continue
        sid = sec.get("id")
        if not _is_str(sid):
            errors.append(f"{where}.id: required non-empty string")
        elif sid in seen:
            errors.append(f"{where}.id: duplicate id '{sid}'")
        else:
            seen.add(sid)
        if not _is_str(sec.get("title")):
            errors.append(f"{where}.title: required non-empty string")
        points = sec.get("points") or []
        if not isinstance(points, list) or not all(isinstance(p, str) for p in points):
            errors.append(f"{where}.points: must be a list of strings")
        if sec.get("summary") is not None and not isinstance(sec.get("summary"), str):
            errors.append(f"{where}.summary: must be a string")
        equations = sec.get("equations")
        if equations is not None and not isinstance(equations, list):
            errors.append(f"{where}.equations: must be a list")
        for k, eq in enumerate(equations if isinstance(equations, list) else []):
            if not isinstance(eq, dict) or not _is_str(eq.get("latex")):
                errors.append(f"{where}.equations[{k}].latex: required non-empty string")
            elif eq.get("caption") is not None and not isinstance(eq["caption"], str):
                errors.append(f"{where}.equations[{k}].caption: must be a string")
        for j, block in enumerate(sec.get("code") or []):
            if not isinstance(block, dict) or not isinstance(block.get("code"), str):
                errors.append(f"{where}.code[{j}]: needs a code string")
        for ref in sec.get("image_ids") or []:
            if ref not in image_ids:
                errors.append(f"{where}.image_ids: unknown image id '{ref}'")

    for i, entry in enumerate(data.get("glossary") or []):
        if not isinstance(entry, dict) or not _is_str(entry.get("term")) or not _is_str(entry.get("definition")):
            errors.append(f"glossary[{i}]: needs term and definition")

    quiz = data.get("quiz")
    if not isinstance(quiz, list) or not QUIZ_MIN <= len(quiz) <= QUIZ_MAX:
        errors.append(f"quiz: needs {QUIZ_MIN}-{QUIZ_MAX} questions")
        quiz = quiz if isinstance(quiz, list) else []
    for i, q in enumerate(quiz):
        if not isinstance(q, dict) or not _is_str(q.get("question")):
            errors.append(f"quiz[{i}].question: required non-empty string")
            continue
        choices = q.get("choices")
        if not isinstance(choices, list) or len(choices) != 4:
            errors.append(f"quiz[{i}].choices: needs exactly 4 choices")
        idx = q.get("answer_index")
        if not isinstance(idx, int) or isinstance(idx, bool) or not 0 <= idx <= 3:
            errors.append(f"quiz[{i}].answer_index: must be 0-3")

    for i, card in enumerate(data.get("cards") or []):
        if not isinstance(card, dict) or not _is_str(card.get("front")) or not _is_str(card.get("back")):
            errors.append(f"cards[{i}]: needs front and back")

    return errors


DIALOGUE_MODES = ("overview", "by_chapter")


def _top_level_owner(content: dict) -> dict:
    """Map every section id (any depth) to the id of its top-level section."""
    owner = {}
    for top in content.get("sections") or []:
        for _, sec in _walk([top]):
            if isinstance(sec, dict) and sec.get("id"):
                owner[sec["id"]] = top.get("id")
    return owner


def validate_dialogue(dialogue: dict, content: dict) -> list[str]:
    if not isinstance(dialogue, dict):
        return ["dialogue must be a JSON object"]
    errors: list[str] = []
    mode = dialogue.get("mode")
    if mode not in DIALOGUE_MODES:
        errors.append(f"mode: must be one of {', '.join(DIALOGUE_MODES)}")
    episodes = dialogue.get("episodes")
    if not isinstance(episodes, list) or not episodes:
        return errors + ["episodes: required non-empty list"]
    if mode == "overview" and len(episodes) != 1:
        errors.append("mode overview: needs exactly 1 episode")

    top_ids = [s.get("id") for s in content.get("sections") or []]
    owner = _top_level_owner(content)
    covered: list[str] = []
    for i, ep in enumerate(episodes):
        where = f"episodes[{i}]"
        if not isinstance(ep, dict):
            errors.append(f"{where}: must be an object")
            continue
        if not isinstance(ep.get("title"), str) or not ep["title"].strip():
            errors.append(f"{where}.title: required non-empty string")
        ids = ep.get("section_ids") or []
        if mode == "by_chapter" and not 1 <= len(ids) <= 2:
            errors.append(f"{where}.section_ids: by_chapter episodes cover 1-2 sections")
        covered.extend(ids)
        lines = ep.get("lines") or []
        if not lines:
            errors.append(f"{where}.lines: required non-empty list")
        position = -1
        spoken = set()
        for j, line in enumerate(lines):
            if not isinstance(line, dict):
                errors.append(f"{where}.lines[{j}]: must be an object")
                continue
            if line.get("speaker") not in ("A", "B"):
                errors.append(f"{where}.lines[{j}].speaker: must be A or B")
            if not isinstance(line.get("text"), str) or not line["text"].strip():
                errors.append(f"{where}.lines[{j}].text: required non-empty string")
            sid = line.get("section_id")
            top = owner.get(sid) if isinstance(sid, str) else None
            if top not in ids:
                errors.append(f"{where}.lines[{j}].section_id: '{line.get('section_id')}' is not in this episode")
                continue
            spoken.add(top)
            if ids.index(top) < position:
                errors.append(f"{where}.lines[{j}]: section '{top}' is out of order")
            position = max(position, ids.index(top))
        for sid in ids:
            if sid not in spoken:
                errors.append(f"{where}: section '{sid}' has no lines")

    if covered != top_ids:
        missing = [s for s in top_ids if s not in covered]
        if missing:
            errors.append("episodes: sections not covered: " + ", ".join(missing))
        else:
            errors.append("episodes: section_ids must list every top-level section once, in content order")
    return errors
