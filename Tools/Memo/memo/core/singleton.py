"""Single-instance machinery — second launches wake the existing tray
instead of starting a duplicate.

Uses :mod:`multiprocessing.connection` rather than ``QtNetwork``: it is
stdlib only (no extra Qt module to bundle), and ``Listener`` / ``Client``
work cross-platform via ``AF_UNIX`` on POSIX and named pipes on Windows.

Address layout:
    Linux/macOS:   <data_dir>/memo.sock
    Windows:       \\\\.\\pipe\\memo-singleton-<user>

Stale-socket recovery: on POSIX, if the previous primary crashed without
unlinking the socket file, our ``bind`` will fail with ``EADDRINUSE``.
Before binding we therefore try to *connect* to the address — if the
connect fails the socket is dead and we unlink it before retrying the
bind. If it succeeds the existing primary gets the wake-up message.
"""

from __future__ import annotations

import os
import sys
import threading
from multiprocessing.connection import Client, Listener
from typing import Callable

from memo.core import paths


_AUTH_KEY = b"memo-local-only"


def _address() -> str:
    if sys.platform == "win32":
        try:
            user = os.getlogin()
        except OSError:
            user = os.environ.get("USERNAME", "default")
        return r"\\.\pipe\memo-singleton-" + user
    return str(paths.data_dir() / "memo.sock")


def acquire_or_signal_running() -> "Singleton | None":
    """Return a :class:`Singleton` if we're the primary process, or ``None``
    after waking the existing instance. Caller exits cleanly on ``None``."""
    addr = _address()

    # POSIX: probe stale socket file *before* trying to bind.
    if not sys.platform.startswith("win") and os.path.exists(addr):
        if _try_signal(addr):
            return None
        # connect failed → socket file is stale; remove and retry bind.
        try:
            os.unlink(addr)
        except OSError:
            pass

    try:
        listener = Listener(addr, authkey=_AUTH_KEY)
    except (OSError, PermissionError):
        # Most likely on Windows: the named pipe is already in use by
        # another live primary. Signal it and bow out.
        if _try_signal(addr):
            return None
        return None

    return Singleton(listener, addr)


def _try_signal(addr: str) -> bool:
    try:
        client = Client(addr, authkey=_AUTH_KEY)
    except (ConnectionRefusedError, FileNotFoundError, OSError):
        return False
    try:
        client.send("show")
    finally:
        try:
            client.close()
        except OSError:
            pass
    return True


class Singleton:
    """Owns the listener + background accept thread for the primary
    instance. Call :meth:`serve` to wire a callback, :meth:`stop` to
    release the address before quitting."""

    def __init__(self, listener: Listener, addr: str) -> None:
        self._listener = listener
        self._addr = addr
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None
        self._on_signal: Callable[[], None] | None = None

    def serve(self, on_signal: Callable[[], None]) -> None:
        """Start the accept loop. ``on_signal`` is called from a worker
        thread whenever a second launch sends a wake message — it MUST
        be thread-safe (e.g. emit a queued Qt signal)."""
        self._on_signal = on_signal
        t = threading.Thread(target=self._loop, name="memo-singleton", daemon=True)
        t.start()
        self._thread = t

    def stop(self) -> None:
        self._stop.set()
        try:
            self._listener.close()
        except OSError:
            pass
        if not sys.platform.startswith("win"):
            try:
                if os.path.exists(self._addr):
                    os.unlink(self._addr)
            except OSError:
                pass

    def _loop(self) -> None:
        while not self._stop.is_set():
            try:
                conn = self._listener.accept()
            except OSError:
                return
            try:
                msg = conn.recv()
            except (EOFError, OSError):
                msg = None
            finally:
                try:
                    conn.close()
                except OSError:
                    pass
            if msg == "show" and self._on_signal is not None:
                try:
                    self._on_signal()
                except Exception:
                    # never let a UI hiccup kill the listener
                    pass
