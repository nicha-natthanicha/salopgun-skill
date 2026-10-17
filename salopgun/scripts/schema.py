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
        if not isinstance(sec.get("points", []), list):
            errors.append(f"{where}.points: must be a list of strings")
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
