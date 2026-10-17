#!/usr/bin/env bash
# Zip the skill folder into dist/salopgun.zip for upload to claude.ai.
set -euo pipefail
cd "$(dirname "$0")"
mkdir -p dist
rm -f dist/salopgun.zip
zip -qr dist/salopgun.zip salopgun -x '*/__pycache__/*' '*.pyc' '*/.DS_Store'
echo "dist/salopgun.zip"
