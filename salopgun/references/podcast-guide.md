# Writing the podcast dialogue (dialogue.json)

NotebookLM rewrites whatever it is given and tends to shorten it. Your script is its source, so the
more complete and clearly ordered it is, the less gets cut. Goals, in order:

1. **Cover everything.** Every `point`, every child topic and every `code`/term worth knowing gets
   said out loud. Never summarise a point away. If a topic is `focused`, go deeper: add an example,
   a "why it matters", and a common mistake.
2. **Keep the order** of `sections`. Finish one topic before starting the next.
3. **Two hosts, Thai, natural.** `A` (พิธีกร A) is curious and asks; `B` (พิธีกร B) explains.
   Alternate A/B. A asks a short question or reacts, B answers in 1–4 sentences. Use everyday
   Thai; keep English technical terms as they are, and have B explain each one the first time.
4. **Signpost.** At each new topic A names it ("ต่อไปเรื่อง …"). At the end of each episode A
   recaps the topics in one line.

Rules the validator checks:
- `section_id` on every line (a child id is fine; it counts for its top-level topic).
- Every top-level topic in the episode has at least one line, and lines never go back to an
  earlier topic.
- `overview`: 1 episode with every top-level topic.
- `by_chapter`: 1–2 top-level topics per episode, all topics covered once, in order.
  Group short neighbouring topics together; give a long topic its own episode.

Length guide: roughly 6–12 lines per point-heavy topic; more for focused topics.
