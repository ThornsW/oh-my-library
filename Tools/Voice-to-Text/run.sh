#!/bin/sh
# Start Voice-to-Text with the system Python (it ships python3-gi + GTK 3 on Ubuntu).
# Set VTT_PYTHON to use another interpreter that can import gi (PyGObject).
DIR="$(cd "$(dirname "$0")" && pwd)"
PYTHONPATH="$DIR${PYTHONPATH:+:$PYTHONPATH}" exec "${VTT_PYTHON:-/usr/bin/python3}" -B -m voice_to_text "$@"
