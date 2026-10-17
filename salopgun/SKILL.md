---
name: salopgun
description: Turn lecture slides or documents the user attaches into study material. Two outputs - an interactive HTML summary (mind map, quiz, glossary, flashcards), or a Claude Design pack (one markdown file holding the full dense summary plus a ready-to-paste prompt, with the slide images) that the user hands to Claude Design to lay out as PDF sheets. Optional two-host Thai podcast scripts for NotebookLM. Use when the user attaches a file and asks to summarise it, make a study sheet/สรุป/ชีท/เกร็งข้อสอบ, a mind map, flashcards, or a podcast script, or says "salopgun".
---

# SalopGun

You turn the attached document into study material. You write the content; the scripts in this
skill check it and package it. Speak to the user in their language (usually Thai). Ask questions in
short sets, never all at once.

`SKILL_DIR` below means the folder this SKILL.md is in. Work in a scratch folder; put every file you
hand to the user in the outputs folder your environment uses (on claude.ai: `/mnt/user-data/outputs/`).

## 1. Read first

Read the whole attached document before asking anything. Note its language, its chapters/topics in
order, which slides hold diagrams or equations, and whether it is mainly about code. If it is very
long, read it in parts; don't skip. If no file is attached, ask for one and stop.

## 2. Question set 1 (always)

Ask these three together. Use the clickable-choices tool if your environment has one; otherwise a
numbered list the user can answer by number.

1. **เนื้อหาที่อยากเน้น** (multiple choice allowed): 3–6 specific topics you found in the document,
   then `สรุปภาพรวมทั้งหมด` and `ระบุเอง`. If they pick `ระบุเอง`, ask what to focus on.
2. **รูปแบบผลลัพธ์**: `เว็บไซต์ HTML` or `ชีท PDF ผ่าน Claude Design` (you prepare a markdown file and
   a prompt; Claude Design makes the PDF).
3. **สคริปต์พอดแคสต์สำหรับ NotebookLM**: `เอา` or `ไม่เอา`.

## 3. Question set 2 (depends on the format)

**ชีท PDF ผ่าน Claude Design**
- ประเภทชีท (multiple choice allowed): `สรุปรวบรัด`, `ชีทสอน`, `เกร็งข้อสอบ`.
  If `สรุปรวบรัด`: จำนวนหน้า = `ให้ Claude Design กำหนดเอง` or a number.
- ขนาดกระดาษ: `A4`, `mobile`, `desktop`, `B5`, `ระบุเอง` (then ask width × height in mm)
- แนว: `แนวตั้ง` or `แนวนอน`
- ลักษณะสรุป: `bullet` or `mindmap`
- theme: `ตามไฟล์ที่ส่งมา` (default) or let them describe colours (turn them into hex codes)

**HTML**
- อยากได้หน้าการ์ดสำหรับทวนเร็วเพิ่มไหม: `เอา` or `ไม่เอา`
- theme: same as above

## 4. Question set 3 (only if they want the podcast)

- `สรุปภาพรวม` (1 episode) or `สรุปเน้นแยกตามบท` (several episodes, 1–2 chapters each).
  If by chapter and there will be more than 3 episodes, mention that NotebookLM free makes 3 per day.

## 5. Build

Run every command with `python SKILL_DIR/scripts/salopgun.py …`. A command that exits with code 2
prints what is wrong, one problem per line: fix your input and run it again.

### 5a. Both formats: theme and pictures

1. **Theme:** `theme --source <attached file> [--user-theme '{"primary": "#RRGGBB"}'] --out theme.json`
2. **Pictures from the slides** (pptx/pdf only). Use them: a summary with its diagrams is worth far
   more than text alone.
   1. `slides --source <attached file>` lists every slide with `pictures`, `drawings`, `equations`
      (pptx only) and a `visual` hint. Slides marked `visual: true` probably hold a diagram, chart
      or figure; slides with `equations > 0` hold math.
   2. `images --source <attached file> --out-dir images` extracts the embedded pictures (named
      `pNN-imgK.ext`, where NN is the slide number; logos and backgrounds repeated on many slides are
      skipped). Look at them and keep the ones that explain something.
   3. Many diagrams are drawn with shapes, not embedded pictures, so they are not in step 2. For
      those slides, and for slides whose math you need to read, run
      `snapshots --source <attached file> --pages 3,5,7-9 --out-dir images` (whole slide as
      `pNN-slide.jpg`). Pick pages deliberately (diagram or figure slides, normally at most about
      15) and look at them. If it exits with code 2 saying LibreOffice is missing for a .pptx, ask
      the user to export the slides as a PDF and run it on that file.

### 5b. Claude Design pack (ชีท PDF)

1. Write `summary.md` following `references/md-guide.md`: the **full** content, dense, with `[p.N]`
   slide tags, ★ on the focus topics, tables, math as LaTeX, and the pictures you kept linked as
   `![caption](images/p07-slide.jpg)`.
2. Package it:

   `designpack --md summary.md --images-dir images --kinds concise,teaching,exam --paper A4 --orientation portrait --style bullet [--pages N] [--theme theme.json] --name <name> --out-dir <outputs>/pack`

   - `--kinds`: only the ones the user picked (`concise` = สรุปรวบรัด, `teaching` = ชีทสอน,
     `exam` = เกร็งข้อสอบ). `--pages` only applies to `concise`.
   - For `ระบุเอง` paper use `--paper custom --size WxH` (mm, e.g. `100x150`).
   - It writes `<name>.md` (the prompt on top, the content below), the `images/` folder and
     `<name>.zip` with both, and prints a JSON summary. Read its `warnings` and fix them (for
     example "no images are linked").
3. You cannot run Claude Design from here; the user does that step.

### 5c. HTML

Write `content.json` following `references/content-schema.md` and `references/writing-guide.md`.
Set `layout` to `desktop` if the document is mainly about code, otherwise `mobile`. Mark the chosen
focus topics `"focused": true`. Add `cards` only if they asked for the card page. Put every picture
you kept in `images` (copy the entries the commands printed, write a `caption`) and attach it to its
section with `image_ids`. Then:

`html --content content.json --theme theme.json [--cards] --out <outputs>/<name>.html`

Equations: write them as LaTeX in the section's `equations` (`{"latex": "…", "caption": "…"}`; every
backslash is doubled in JSON). The HTML shows them as LaTeX source, not typeset math; tell the user
that if the document has math. Never paste a picture of an equation; re-type it.

### 5d. Podcast (if wanted)

The podcast is built from `content.json` too, so write it even for the Claude Design route (it may be
shorter than `summary.md`, but must list every top-level topic in the same order). Write
`dialogue.json` following `references/podcast-guide.md`, then
`podcast --content content.json --dialogue dialogue.json --out-dir <outputs>/podcast`.

## 6. Hand over

Give the user the files. In two or three lines tell them:
- Claude Design pack: open Claude Design, attach `<name>.md` and the images from `images/` (or the
  zip contents), and paste the prompt that is in the md under "Prompt". Each sheet type they chose
  comes back as its own file; if anything is cut or an image is missing, tell Claude Design to fix it.
- HTML: open it in a browser; tap the mind map to jump to a topic.
- Podcast: what `notebooklm-prompt.txt` is for (paste into Audio Overview → Customize, choose
  Longer), one notebook per episode, and to tick the checklist at the end of each script while
  listening.

## 7. Changes

If they ask for changes, edit the existing `summary.md`, `content.json` or `dialogue.json` and re-run
the same command. Don't rewrite everything from scratch.

## Rules

- Never invent content that isn't in the document. If something is unclear in the source, say so
  in the summary rather than guessing.
- In `content.json` every field is plain text: no HTML or Markdown. (`summary.md` is Markdown.)
- Fonts: the HTML embeds the Thai font Sarabun; you don't need to do anything for Thai text.
