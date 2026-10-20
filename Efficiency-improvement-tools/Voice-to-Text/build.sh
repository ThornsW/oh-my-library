#!/bin/sh
# Build the single-file program ./voice-to-text:
# a small C launcher (gcc) with the Python package appended as a zip archive.
# Output: ./voice-to-text (next to config.json). No other files are left behind.
set -eu
DIR="$(cd "$(dirname "$0")" && pwd)"
PY="${VTT_PYTHON:-/usr/bin/python3}"
OUT="$DIR/voice-to-text"
TMP="$OUT.tmp"

# -no-pie: GNOME Files treats PIE programs as "shared libraries" and will not
# start them on double-click.
gcc -O2 -no-pie -s -o "$TMP" "$DIR/launcher/launcher.c"

"$PY" -B - "$DIR" "$TMP" <<'EOF'
import sys
import zipfile
from pathlib import Path

src, out = Path(sys.argv[1]), sys.argv[2]
# Mode "a" on a non-zip file appends a new archive after the launcher.
with zipfile.ZipFile(out, "a", compression=zipfile.ZIP_DEFLATED) as z:
    z.writestr("__main__.py", "import sys\nfrom voice_to_text.__main__ import main\nsys.exit(main())\n")
    for f in sorted((src / "voice_to_text").rglob("*.py")):
        z.write(f, f.relative_to(src).as_posix())
EOF

chmod 755 "$TMP"
mv -f "$TMP" "$OUT"
echo "built $OUT v$("$OUT" --version) ($(wc -c < "$OUT") bytes)"
