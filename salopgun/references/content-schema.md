# content.json and dialogue.json

Every output (HTML, PDF, podcast) is built from these files. Write them, then run the CLI;
it validates first and prints one error per line if something is wrong. Fix and re-run.

## content.json

```json
{
  "title": "Lecture title",
  "language": "th",
  "layout": "mobile",
  "sections": [
    {
      "id": "s1",
      "title": "Topic title",
      "focused": true,
      "summary": "One or two sentences",
      "points": ["Key point", "Key point"],
      "code": [{"lang": "python", "code": "print('hi')"}],
      "image_ids": ["img1"],
      "children": []
    }
  ],
  "glossary": [{"term": "overfitting", "definition": "Short plain definition"}],
  "quiz": [
    {"question": "…", "choices": ["A", "B", "C", "D"], "answer_index": 0, "explanation": "Why"}
  ],
  "cards": [{"front": "Concept", "back": "Explanation"}],
  "images": [{"id": "img1", "path": "img1.png", "caption": "Caption"}]
}
```

| Field | Rule |
|---|---|
| `title` | Required. |
| `language` | Language of the source document, e.g. `th`, `en`. Write the summary in this language. |
| `layout` | `desktop` when the content is mainly about code; otherwise `mobile`. |
| `sections` | Required, non-empty, in the source document's order. Top-level sections are the chapters/topics; `children` nest sub-topics (keep depth ≤ 3). |
| `id` | Unique across the whole tree (`s1`, `s1a`, `s2` …). Used for links and podcast coverage. |
| `focused` | `true` for topics the user chose to focus on: write them in more depth. Others stay, but shorter. |
| `summary` / `points` | Plain text only. Never put HTML in any field; it is shown as text. |
| `code` | Optional code blocks shown under the section. |
| `image_ids` | Must match an `id` in `images`. Only include images that explain something (diagrams, charts). |
| `glossary` | Key terms that appear in the text. Each term gets a tooltip wherever it appears. |
| `quiz` | 5–10 questions, exactly 4 choices, `answer_index` 0–3, with an explanation. |
| `cards` | Only when the user asked for the card page. One concept per card. |
| `images` | `path` is relative to the working directory (extract images from the source first). |

## dialogue.json (only when the user wants a podcast script)

```json
{
  "mode": "overview",
  "episodes": [
    {
      "title": "Episode title",
      "section_ids": ["s1", "s2", "s3"],
      "lines": [
        {"speaker": "A", "section_id": "s1", "text": "…"},
        {"speaker": "B", "section_id": "s1", "text": "…"}
      ]
    }
  ]
}
```

| Field | Rule |
|---|---|
| `mode` | `overview` = exactly 1 episode covering every top-level section. `by_chapter` = several episodes, 1–2 top-level sections each. |
| `section_ids` | Top-level section ids this episode covers, in content order. Every top-level section appears in exactly one episode. |
| `lines` | Speaker `A` or `B`. Every `section_id` of the episode needs at least one line, and lines follow the section order. |
