---
name: salopgun-probe
description: Diagnostic for the SalopGun skill. Use only when the user asks to "run the salopgun probe". Checks which Python packages and PDF tools exist in this sandbox.
---

# SalopGun sandbox probe

1. Copy `probe.py` and `Sarabun-Regular.ttf` from this skill's folder into the working directory.
2. Run `python probe.py` and show the user the full printed report in a code block.
3. Give the user every `probe-*.pdf` file that was created, so they can check the Thai text by eye.
