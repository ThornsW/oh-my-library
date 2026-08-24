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


def test_distro_fcitx5_plugin_is_never_bundled() -> None:
    """Qt requires an exact QT_VERSION match for QPA plugins, so a plugin
    built against the distro's Qt cannot load from our bundled Qt. Pulling it
    in only ships a file Qt will refuse — fcitx5 is reached over IBus."""
    spec = (ROOT / "Memo.spec").read_text(encoding="utf-8")

    assert "/usr/lib/x86_64-linux-gnu/qt6/plugins" not in spec
    assert '"libfcitx5platforminputcontextplugin"' not in spec


def test_ibus_input_context_plugin_survives_binary_filter() -> None:
    """The bundle's own ibus plugin is what carries Chinese input."""
    spec = (ROOT / "Memo.spec").read_text(encoding="utf-8")

    assert '"libibusplatforminputcontextplugin"' in spec
    assert '"libcomposeplatforminputcontextplugin"' in spec
    assert '"platforminputcontexts"' in spec


def test_linux_hotkey_backend_dependencies_are_collected() -> None:
    spec = (ROOT / "Memo.spec").read_text(encoding="utf-8")

    assert '"Xlib"' in spec
    assert '"evdev"' in spec
    assert '"pynput.keyboard._xorg"' in spec
    assert '"pynput.mouse._xorg"' in spec
    assert '"pynput._util.xorg"' in spec
