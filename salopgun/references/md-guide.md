# Writing summary.md for Claude Design

Claude Design lays this out as dense A4-style study sheets (a 2-page crammer, a teaching sheet, an
exam sheet), so this file is the single source of truth: **everything that must appear on a sheet
has to be in it.** Claude Design can shorten wording to fit a page limit, but it cannot add what is
missing. Write for a student who will use the sheet to revise for an exam.

## Content
- **Complete.** Every topic, definition, formula, number, table and worked example the lecture
  teaches. Never drop a topic to save space; the page limit is Claude Design's job.
- **Dense but readable.** Short sentences and fragments, `·` or `|` between related facts on one
  line, bold for the key term. Keep the source's notation, symbols, values and units exactly.
- Follow the document's order. Use `#` for the document title, `##` for each major part (for example
  `## A · Communication Protocol [p.2–11]`), `###` for topics inside it.
- **Slide tags:** put `[p.N]` (or `[p.N–M]`) after every topic heading and after any fact that is
  easy to look up, where N is the slide number. The images are named after these numbers.
- **★ importance:** put `★` after topics the user chose to focus on, and `★★` / `★★★` on points that
  are likely exam material (the source stresses them, repeats them, or says "important").
- **Tables** (comparisons, parameter lists, protocol versus protocol) as Markdown tables.
- **Code** in fenced blocks with the language, only code that is in the source.
- **Math as LaTeX**: `$x_i$` inline, and display equations on their own lines between `$$` lines:

  ```
  $$
  \hat{\theta} = \arg\min_\theta \frac{1}{n}\sum_i (y_i - f_\theta(x_i))^2
  $$
  ```

  Re-type equations that appear as pictures (take a snapshot of the slide and read it). Write a
  literal dollar sign as `\$`. Every `$$` must be closed or the pack is rejected.
- Don't invent content. If something in the source is unclear or looks like a typo, say so in a
  short note instead of guessing.

## Pictures
- Link only pictures you actually kept: `![what to notice](images/p07-slide.jpg)`. The path must
  start with `images/` and the file must exist in the images folder, or the pack is rejected.
- Put each picture right after the text it explains, with a caption that says what to notice.
- Use a figure from the slide wherever the slide has one (circuit, timing diagram, block diagram,
  chart, table of values). Prefer the clean embedded picture (`pNN-imgK`); use the whole-slide
  snapshot (`pNN-slide.jpg`) when the figure only exists as shapes on the slide.
- Skip decoration, logos and photos that explain nothing.

## Focus
- Topics the user asked to focus on get more depth: add an example, why it matters, and the common
  mistake or exam trap if the source suggests one. Other topics stay complete but compact.
