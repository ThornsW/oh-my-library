from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_qtawesome_is_not_a_runtime_dependency() -> None:
    files = [
        ROOT / "pyproject.toml",
        ROOT / "Memo.spec",
        ROOT / "memo" / "ui" / "main_window.py",
    ]

    for path in files:
        text = path.read_text(encoding="utf-8")
        assert "qtawesome" not in text
        assert "qta." not in text


def test_fcitx_plugin_is_bundled_by_default() -> None:
    spec = (ROOT / "Memo.spec").read_text(encoding="utf-8")

    assert "MEMO_BUNDLE_FCITX" not in spec
    assert "libfcitx5platforminputcontextplugin.so" in spec
    assert "if sys.platform.startswith(\"linux\"):" in spec


def test_fcitx_plugin_survives_binary_filter() -> None:
    spec = (ROOT / "Memo.spec").read_text(encoding="utf-8")

    assert '"libfcitx5platforminputcontextplugin"' in spec


def test_linux_hotkey_backend_dependencies_are_collected() -> None:
    spec = (ROOT / "Memo.spec").read_text(encoding="utf-8")

    assert '"Xlib"' in spec
    assert '"evdev"' in spec
    assert '"pynput.keyboard._xorg"' in spec
    assert '"pynput.mouse._xorg"' in spec
    assert '"pynput._util.xorg"' in spec
