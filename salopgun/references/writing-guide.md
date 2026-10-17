# Writing the summary (content.json)

The reader is a student reviewing a lecture, often on a phone, often the night before an exam.

## Sections
- Follow the document's own order and chapter structure. One top-level section per chapter or
  major topic; sub-topics go in `children` (max depth 3).
- `title`: short, as the lecture names it.
- `summary`: 1–2 sentences that say what the topic is and why it matters.
- `points`: 2–6 points, one idea each, short enough to read in one breath. Keep numbers, formulas,
  definitions and names exactly as the source states them.
- **Focused topics** (`focused: true`): more points, an example, and the common mistake or exam
  trap if the source suggests one. **Other topics**: keep, but trim to the essentials.
- `code`: copy short, important code from the source; don't write new code that isn't there.

## Glossary
- 5–15 key terms that actually appear in the summary text, spelled the same way, so the tooltip
  can find them. Definitions: one plain sentence.

## Quiz
- 5–10 questions spread over all top-level topics, more on focused ones.
- Exactly 4 choices; wrong choices are plausible, not silly. Vary `answer_index`.
- `explanation`: one sentence on why the answer is right.

## Cards (only if requested)
- 8–20 cards. `front` = a term or question, `back` = a short answer. One concept per card.

## Equations
- Every formula the lecture teaches should appear, as LaTeX in `equations` with a caption saying
  what it means (the HTML shows the LaTeX source); explain the symbols in a point.
- Keep the source's notation and symbols exactly.

## Images
- Include the lecture's own diagrams, charts and figures wherever they explain a topic, at
  least one per topic that has one in the source. Skip decoration, logos and stock photos.
- Attach each to the section it explains with `image_ids` (a section may have several) and write a
  short `caption` that says what to notice, not just what it is.
- A `kind: "slide"` snapshot shows the whole slide with its slide number; use it when the figure
  only exists as shapes on the slide.
