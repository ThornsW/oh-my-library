from __future__ import annotations

import os
import subprocess
import sys


def test_app_modules_import_without_display() -> None:
    env = os.environ.copy()
    env.pop("DISPLAY", None)
    env.pop("WAYLAND_DISPLAY", None)

    result = subprocess.run(
        [
            sys.executable,
            "-c",
            "import memo.app; import memo.ui.settings_dialog",
        ],
        cwd=os.getcwd(),
        env=env,
        text=True,
        capture_output=True,
        timeout=10,
    )

    assert result.returncode == 0, result.stderr
