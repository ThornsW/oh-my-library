"""Shared CSS and small widget helpers."""

from __future__ import annotations

from gi.repository import Gdk, Gtk

STATUS_KINDS = ("info", "rec", "busy", "ok", "warn", "error")

CSS = """
.status { border-radius: 10px; padding: 10px; font-size: 15pt; }
.st-info  { background-color: #e8eaed; color: #202124; }
.st-rec   { background-color: #d93025; color: #ffffff; }
.st-busy  { background-color: #1a73e8; color: #ffffff; }
.st-ok    { background-color: #188038; color: #ffffff; }
.st-warn  { background-color: #f9ab00; color: #202124; }
.st-error { background-color: #c5221f; color: #ffffff; }
.status-small { border-radius: 6px; padding: 4px; }

button.talk { background-image: none; border: none; box-shadow: none; border-radius: 14px; }
button.talk label { color: #ffffff; font-weight: bold; }
button.talk-idle { background-color: #1a73e8; }
button.talk-rec  { background-color: #d93025; }

#floating { background-color: #202124; }
#floating .handle { color: #bdc1c6; padding: 4px; }
#floating button.small { background-image: none; background-color: #3c4043; border: none; box-shadow: none; }
#floating button.small label { color: #ffffff; }

.hint { color: #5f6368; }
.error-text { color: #c5221f; font-weight: bold; }
"""


def install_css(font_pt: int) -> None:
    provider = Gtk.CssProvider()
    provider.load_from_data((CSS + f"\nwindow, dialog {{ font-size: {font_pt}pt; }}\n").encode())
    Gtk.StyleContext.add_provider_for_screen(Gdk.Screen.get_default(), provider,
                                             Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)


def set_status_style(label: Gtk.Label, kind: str) -> None:
    ctx = label.get_style_context()
    for k in STATUS_KINDS:
        ctx.remove_class(f"st-{k}")
    ctx.add_class(f"st-{kind if kind in STATUS_KINDS else 'info'}")


def button(text: str, height: int = 48, on_click=None) -> Gtk.Button:
    b = Gtk.Button(label=text)
    b.set_size_request(-1, height)
    b.set_can_focus(False)
    if on_click:
        b.connect("clicked", lambda _b: on_click())
    return b


def hbox(*widgets, spacing: int = 6, homogeneous: bool = False) -> Gtk.Box:
    box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=spacing)
    box.set_homogeneous(homogeneous)
    for w in widgets:
        box.pack_start(w, True, True, 0)
    return box


def text_of(view: Gtk.TextView) -> str:
    buf = view.get_buffer()
    return buf.get_text(buf.get_start_iter(), buf.get_end_iter(), False)


def text_view(text: str = "", height: int = 80) -> tuple[Gtk.ScrolledWindow, Gtk.TextView]:
    view = Gtk.TextView()
    view.set_wrap_mode(Gtk.WrapMode.WORD_CHAR)
    view.get_buffer().set_text(text)
    scroll = Gtk.ScrolledWindow()
    scroll.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
    scroll.set_shadow_type(Gtk.ShadowType.IN)
    scroll.set_size_request(-1, height)
    scroll.add(view)
    return scroll, view


def xid(window: Gtk.Window) -> int | None:
    gdk_window = window.get_window()
    return gdk_window.get_xid() if gdk_window is not None and hasattr(gdk_window, "get_xid") else None
