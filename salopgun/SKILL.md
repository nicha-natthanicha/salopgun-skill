---
name: salopgun
description: Turn lecture slides or documents the user attaches into a designed study summary (interactive HTML with mind map, quiz, glossary and flashcards, or a PDF in bullet or mind-map style) plus optional two-host Thai podcast scripts for NotebookLM. Use when the user attaches a file and asks to summarise it, make a study sheet/สรุป/ชีท, a mind map, flashcards, or a podcast script, or says "salopgun".
---

# SalopGun

You turn the attached document into a summary the user can read or listen to. You write the
content; the scripts in this skill check it and do the layout. Speak to the user in their language
(usually Thai). Ask questions in short sets, never all at once.

`SKILL_DIR` below means the folder this SKILL.md is in. Work in a scratch folder; put every file you
hand to the user in the outputs folder your environment uses (on claude.ai: `/mnt/user-data/outputs/`).

## 1. Read first

Read the whole attached document before asking anything. Note its language, its chapters/topics in
order, and whether it is mainly about code. If it is very long, read it in parts; don't skip.
If no file is attached, ask for one and stop.

## 2. Question set 1 (always)

Ask these three together. Use the clickable-choices tool if your environment has one; otherwise a
numbered list the user can answer by number.

1. **เนื้อหาที่อยากเน้น** (multiple choice allowed): 3–6 specific topics you found in the document,
   then `สรุปภาพรวมทั้งหมด` and `ระบุเอง`. If they pick `ระบุเอง`, ask what to focus on.
2. **รูปแบบผลลัพธ์**: `เว็บไซต์ HTML` or `PDF`.
3. **สคริปต์พอดแคสต์สำหรับ NotebookLM**: `เอา` or `ไม่เอา`.

## 3. Question set 2 (depends on the format)

**PDF**
- ลักษณะสรุป: `bullet` or `mindmap`
- ขนาดกระดาษ: `A4`, `mobile`, `desktop`, `B5`, `ระบุเอง` (then ask width × height in mm)
- แนว: `แนวตั้ง` or `แนวนอน`
- จำนวนหน้า: `ให้ Claude กำหนดเอง` (default) or a number
- theme: `ตามไฟล์ที่ส่งมา` (default) or let them describe colours (turn them into hex codes)

**HTML**
- อยากได้หน้าการ์ดสำหรับทวนเร็วเพิ่มไหม: `เอา` or `ไม่เอา`
- theme: same as PDF

## 4. Question set 3 (only if they want the podcast)

- `สรุปภาพรวม` (1 episode) or `สรุปเน้นแยกตามบท` (several episodes, 1–2 chapters each).
  If by chapter and there will be more than 3 episodes, mention that NotebookLM free makes 3 per day.

## 5. Build

Run every command with `python SKILL_DIR/scripts/salopgun.py …`. A command that exits with code 2
prints what is wrong, one problem per line: fix your JSON and run it again.

1. **Theme:** `theme --source <attached file> [--user-theme '{"primary": "#RRGGBB"}'] --out theme.json`
2. **Pictures from the slides** (pptx/pdf only). Use them: a summary with its diagrams is worth
   far more than text alone.
   1. `slides --source <attached file>` lists every slide with `pictures`, `drawings`, `equations`
      (pptx only) and a `visual` hint. Slides marked `visual: true` probably hold a diagram, chart
      or figure; slides with `equations > 0` hold math.
   2. `images --source <attached file> --out-dir images` extracts the embedded pictures (`kind:
      "picture"`, with the `slide` they came from). Logos and backgrounds repeated on many slides
      are skipped. Look at them and keep the ones that explain something.
   3. Many diagrams are drawn with shapes, not embedded pictures, so they are not in step 2.
      For those slides, and for slides whose math you need to read, run
      `snapshots --source <attached file> --pages 3,5,7-9 --out-dir images` (whole slide as a
      JPEG, `kind: "slide"`). Pick pages deliberately (diagram or figure slides, normally at most
      about 10) and look at them. If it exits with code 2 saying LibreOffice is missing for a
      .pptx, ask the user to export the slides as a PDF and run it on that file.
   4. Put every image you keep in `content.json` → `images` (copy the entries the commands
      printed, write a `caption`) and attach it to the section it explains with `image_ids`.
      Prefer the clean embedded picture; use a slide snapshot when the figure only exists there.
3. **content.json:** write it following `references/content-schema.md` and
   `references/writing-guide.md`. Write math as LaTeX (see "Equations" below). Set `layout` to `desktop` if the document is mainly about code,
   otherwise `mobile`. Mark the chosen focus topics `"focused": true`. Add `cards` only if they
   asked for the card page.
4. **Output:**
   - HTML: `html --content content.json --theme theme.json [--cards] --out <outputs>/<name>.html`
   - PDF: `pdf --content content.json --theme theme.json --paper A4 --orientation portrait --style bullet [--max-pages N] --out <outputs>/<name>.pdf`.
     For `ระบุเอง` use `--paper custom --size WxH` (mm, e.g. `100x150`).
     It prints JSON. If `over_limit` is true, shorten the topics that are **not** focused first,
     then rebuild; at most 3 tries, then tell the user how many pages it came to.
     `math_errors` lists LaTeX that failed to typeset; fix each one in content.json and rebuild
     (repeat until it is empty). Math is only typeset by the `playwright` engine.
     If `engine` is `print-html`, no PDF tool exists here: you got a print-ready HTML file
     instead and `pages` is 0, so the page count was not checked; don't claim one. Tell the user
     to open it in a browser and choose Print → Save as PDF, and that the page count may differ.
5. **Podcast** (if wanted): write `dialogue.json` following `references/podcast-guide.md`, then
   `podcast --content content.json --dialogue dialogue.json --out-dir <outputs>/podcast`.

## Equations

Whenever the source has math (formulas, equations, a derivation), write it as LaTeX so the PDF
typesets it properly:
- A displayed equation goes in the section's `equations`: `{"latex": "\\frac{a}{b}", "caption": "…"}`.
  Use it for anything important or longer than a few symbols.
- A short formula inside a sentence is wrapped in dollar signs in `summary`, `points`, titles and
  glossary definitions: `ค่าเฉลี่ยคือ $\\bar{x}=\\frac{1}{n}\\sum x_i$`. A real dollar sign must be
  written `\\$`; text like `$5 and $10` is left alone.
- LaTeX goes into the JSON as normal text, so every backslash is doubled in JSON (`"\\frac"`).
- If a slide shows an equation as a picture, read it (take a snapshot of that slide) and
  re-type it as LaTeX. Don't paste the picture of an equation.
- Never put an equation into `code`. The HTML output shows equations as LaTeX source (typeset
  equations are PDF only), so tell the user that if they chose HTML and the document has math.

## 6. Hand over

Give the user the files. In two or three lines tell them:
- HTML: open it in a browser; tap the mind map to jump to a topic.
- Podcast: what `notebooklm-prompt.txt` is for (paste into Audio Overview → Customize, choose
  Longer), one notebook per episode, and to tick the checklist at the end of each script while
  listening.

## 7. Changes

If they ask for changes, edit the existing `content.json` (or `dialogue.json`) and re-run the
same command. Don't rewrite everything from scratch.

## Rules

- Never invent content that isn't in the document. If something is unclear in the source, say so
  in the summary rather than guessing.
- All JSON fields are plain text. Never put HTML or Markdown inside them.
- Fonts: the scripts embed the Thai font Sarabun; you don't need to do anything for Thai text.
