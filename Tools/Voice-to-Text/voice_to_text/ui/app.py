"""Wires the pipeline, main window and floating window together."""

from __future__ import annotations

import os
import signal
import socket

from gi.repository import GLib, Gtk

from ..config import Config
from ..log import log
from ..pipeline import Pipeline, State
from .floating import FloatingWindow
from .main_window import MainWindow
from .settings import SettingsDialog
from .style import install_css, text_of, xid


def _toplevels() -> list[Gtk.Window]:
    return [w for w in Gtk.Window.list_toplevels() if isinstance(w, Gtk.Window)]


def own_windows() -> set[int]:
    return {i for w in _toplevels() if w.get_visible() and (i := xid(w))}


def ours_active() -> bool:
    return any(w.is_active() for w in _toplevels())


def _single_instance(on_activate) -> socket.socket | None:
    """Return a listening socket when we are the first instance. Otherwise ask
    the running instance to show its window and return None. The socket lives
    in the abstract namespace, so no file is created."""
    name = f"\0voice-to-text-{os.getuid()}"
    server = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    try:
        server.bind(name)
    except OSError:
        server.close()
        try:
            with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as client:
                client.connect(name)
        except OSError:
            pass
        return None
    server.listen(1)

    def on_connect(*_args) -> bool:
        conn, _ = server.accept()
        conn.close()
        on_activate()
        return True

    GLib.io_add_watch(server.fileno(), GLib.PRIORITY_DEFAULT, GLib.IOCondition.IN, on_connect)
    return server


def run_gui(cfg: Config, warning: str | None) -> int:
    # Double-clicking the program again just brings the running window forward.
    server = _single_instance(lambda: main.present())
    if server is None:
        log.info("already running; asked the running instance to show its window")
        return 0
    GLib.set_prgname("voice-to-text")
    GLib.set_application_name("Voice-to-Text")
    install_css(int(cfg["font_pt"]))

    pipeline = Pipeline(cfg, own_windows, ours_active)
    main: MainWindow
    floating: FloatingWindow

    def open_settings() -> None:
        if SettingsDialog(cfg, main).run_and_save():
            main.refresh_target()
            main.set_status("ok", f"设置已保存，当前识别服务：{cfg['active_provider']}")

    def show_main() -> None:
        main.present()

    def floating_closed() -> None:
        cfg["floating_visible"] = False
        cfg.save()

    def toggle_floating() -> None:
        if floating.get_visible():
            floating.close_floating()
        else:
            floating.show_all()
            cfg["floating_visible"] = True
            cfg.save()

    main = MainWindow(pipeline, open_settings, toggle_floating)
    floating = FloatingWindow(pipeline, show_main, floating_closed)
    main.status_changed.connect(floating.set_status)
    floating.set_status("info", "空闲")
    editor = pipeline.load_pending()
    if editor:
        main.set_editor_text(editor)

    def quit_app(*_args) -> bool:
        pipeline.save_editor(text_of(main.editor))
        pipeline.shutdown()
        log.info("quit")
        Gtk.main_quit()
        return False

    main.connect("delete-event", quit_app)
    main.show_all()
    main.refresh_target()  # show_all() re-shows the bind button; hide it again in follow mode
    if cfg["floating_visible"]:
        floating.show_all()
    if warning:
        main.set_status("warn", warning)
    elif any(u.state == State.PENDING for u in pipeline.items.values()):
        main.set_status("warn", "有上次没发送的文字，在下方历史里，可点「发送选中」")

    # Ctrl+C / kill in the launching terminal quits cleanly.
    GLib.unix_signal_add(GLib.PRIORITY_DEFAULT, signal.SIGINT, quit_app)
    GLib.unix_signal_add(GLib.PRIORITY_DEFAULT, signal.SIGTERM, quit_app)
    Gtk.main()
    return 0
