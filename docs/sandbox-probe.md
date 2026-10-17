# Sandbox probe results

The skill no longer renders PDFs itself (Claude Design does), so the probe only checks what the
slide helpers need: PyMuPDF (slide hints, snapshots from PDF, theme colours from PDF) and
LibreOffice (`soffice`, snapshots from .pptx).

## claude.ai sandbox
PENDING: upload `docs/salopgun-probe.zip` under Settings → Capabilities → Skills, enable code
execution, ask in chat "run the salopgun probe", and paste the report here.

What a missing piece costs:
- no PyMuPDF: `slides`, `snapshots` on PDF and PDF colour extraction stop working (pptx hints,
  embedded pictures and pptx colours still work, they only need the standard library)
- no `soffice`: `snapshots` on .pptx exits with code 2; the user exports the slides as PDF instead
