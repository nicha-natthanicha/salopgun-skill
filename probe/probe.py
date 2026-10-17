"""Probe the claude.ai code sandbox for what the SalopGun skill can use.

Run: python probe.py   (prints a report; nothing is written)
"""
import importlib
import platform
import shutil
import sys

# what the skill does with each, so the report says what is lost when one is missing
PACKAGES = {
    "pymupdf": "read PDF slides: slide hints, snapshots, colours, pictures",
    "fitz": "same as pymupdf (older import name)",
    "pptx": "not needed (pptx is read as plain zip/XML)",
    "PIL": "check picture sizes (optional)",
    "pypdf": "not needed",
}
BINARIES = {
    "soffice": "turn .pptx slides into images for snapshots",
    "libreoffice": "same as soffice",
}


def try_import(name: str) -> str:
    try:
        mod = importlib.import_module(name)
        return getattr(mod, "__version__", "ok")
    except Exception as exc:  # noqa: BLE001 - report every failure kind
        return f"MISSING ({type(exc).__name__})"


def main() -> None:
    print("python", sys.version.split()[0], platform.platform())
    for name, use in PACKAGES.items():
        print(f"import {name}: {try_import(name)}   [{use}]")
    for name, use in BINARIES.items():
        print(f"binary {name}: {shutil.which(name) or 'MISSING'}   [{use}]")


if __name__ == "__main__":
    main()
