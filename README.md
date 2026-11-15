# SalopGun

A skill for Claude that turns lecture slides or documents into study material.
Attach a PDF or PowerPoint, answer a few questions, and get back:

- **Claude Design pack**: one dense markdown summary plus a ready-to-paste prompt and the
  slide images, which you give to Claude Design to lay out as PDF sheets
  (concise summary, teaching sheet, or exam cram sheet)
- **Interactive HTML summary**: mind map, quiz, glossary and flashcards in a single page
- **Podcast scripts** (optional): two-host Thai scripts to paste into NotebookLM

สกิลสำหรับ Claude ที่เปลี่ยนสไลด์หรือเอกสารเลคเชอร์ให้เป็นสื่อสำหรับอ่านสอบ
ส่งไฟล์ PDF/PowerPoint แล้วตอบคำถามสั้นๆ ก็ได้ชีทสรุป เว็บ HTML หรือสคริปต์พอดแคสต์

## Install

1. Zip the skill folder:
   ```bash
   bash package.sh        # creates dist/salopgun.zip
   ```
2. On claude.ai go to **Settings → Capabilities → Skills**, upload `dist/salopgun.zip`,
   and turn on code execution.
3. In a chat, attach your slides and say "salopgun", or ask for a study sheet, mind map,
   flashcards or podcast script.

## What is in this repo

| Path | What it is |
|---|---|
| `salopgun/` | The skill itself (`SKILL.md`, scripts, references, Sarabun font) |
| `salopgun/scripts/` | Python helpers that validate the content Claude writes and build the outputs |
| `probe/` | A tiny diagnostic skill that reports which tools exist in the claude.ai sandbox |
| `tests/` | pytest suite for the scripts |
| `docs/` | Notes on the sandbox probe |

## Sandbox requirements

The scripts use the Python standard library. Two optional tools unlock extra features:

- **PyMuPDF**: slide hints, snapshots and theme colours from PDF files
- **LibreOffice (`soffice`)**: snapshots from `.pptx` files (without it, export the slides as PDF)

## Development

```bash
python -m venv .venv && source .venv/bin/activate
pip install pytest
pytest
```

## Credits and license

Code is released under the [MIT License](LICENSE).

The bundled Thai font [Sarabun](https://github.com/cadsondemak/Sarabun) is licensed under the
SIL Open Font License 1.1 (see `salopgun/assets/fonts/OFL.txt`).
