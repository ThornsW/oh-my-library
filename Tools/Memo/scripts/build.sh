#!/usr/bin/env bash
# Linux/macOS: bundle Memo into a single executable in ./dist/Memo
set -euo pipefail
cd "$(dirname "$0")/.."

mamba run -n memo pyinstaller --clean Memo.spec

echo
echo "Build complete:"
ls -lh dist/Memo
