from __future__ import annotations

import sys
import threading
from multiprocessing.connection import Client

import pytest

from memo.core import singleton

pytestmark = pytest.mark.skipif(sys.platform.startswith("win"), reason="POSIX socket path")


@pytest.fixture
def primary(tmp_path, monkeypatch):
    monkeypatch.setenv("MEMO_DATA_DIR", str(tmp_path))
    woke = threading.Event()
    inst = singleton.acquire_or_signal_running()
    assert inst is not None
    inst.serve(woke.set)
    yield inst, woke
    inst.stop()


def test_second_launch_wakes_the_primary(primary):
    _inst, woke = primary

    assert singleton.acquire_or_signal_running() is None
    assert woke.wait(2)


def test_pickled_payload_is_ignored(primary):
    """The listener reads raw bytes; a pickled message must not count as a wake-up."""
    _inst, woke = primary

    client = Client(singleton._address(), authkey=singleton._AUTH_KEY)
    client.send("show")
    client.close()

    assert not woke.wait(0.5)
