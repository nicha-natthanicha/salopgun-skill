# Sandbox probe results

## Local dev machine (2026-10-17)
- Python 3.14.7, macOS arm64
- Available: playwright (+ chromium headless shell), pymupdf 1.28.2, pypdf 6.21.0, python-pptx 1.0.2, Pillow 13.0.0
- Missing: weasyprint, reportlab
- Thai render (playwright, Sarabun embedded, 90x160 mm): correct vowel/tone placement, wraps at word boundaries. PASS.

## claude.ai sandbox
PENDING — needs a manual run: zip `probe/`, upload under Settings → Capabilities → Skills,
enable code execution, then ask in chat "run the salopgun probe" and paste the report here.

## PDF_ENGINE
Chosen at runtime by `build_pdf` in this order: playwright → weasyprint → print-html
(see ledger ruling). The claude.ai result above decides which one users actually get.
