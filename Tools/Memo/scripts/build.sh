#!/usr/bin/env bash
# Linux/macOS: bundle Memo into a single executable in ./dist/Memo
set -euo pipefail
cd "$(dirname "$0")/.."

# Build with whatever environment is already active; fall back to the `memo`
# env the README sets up. The bundled Qt no longer has to match the desktop's
# Qt (input goes through IBus), so any env with PySide6 + PyInstaller works.
if command -v pyinstaller >/dev/null 2>&1; then
    pyinstaller --clean --noconfirm Memo.spec
else
    mamba run -n memo pyinstaller --clean --noconfirm Memo.spec
fi

echo
echo "Build complete:"
ls -lh dist/Memo
