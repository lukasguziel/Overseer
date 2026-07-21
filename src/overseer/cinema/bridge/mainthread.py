from __future__ import annotations

import queue
import threading
import traceback

from .reload import reload_all


class MainThreadRequest:
    __slots__ = ("payload", "event", "result", "error")

    def __init__(self, payload):
        self.payload = payload
        self.event = threading.Event()
        self.result = None
        self.error = None


class MainThreadQueue:

    def __init__(self):
        self._queue: queue.Queue = queue.Queue()

    def submit(self, payload, timeout=300):
        req = MainThreadRequest(payload)
        self._queue.put(req)

        if not req.event.wait(timeout):
            raise TimeoutError("Main-thread timeout (keep the server dialog open)")
        if req.error:
            raise RuntimeError(req.error)
        return req.result

    def drain(self):
        while True:
            try:
                req = self._queue.get_nowait()
            except queue.Empty:
                return

            try:
                req.result = self._dispatch(req.payload)
            except Exception:
                req.error = traceback.format_exc()
            finally:
                req.event.set()

    def _dispatch(self, payload):
        dropped = reload_all()
        from .. import webapi
        if payload.get("op") == "reload":
            try:
                import overseer
                getattr(overseer, "_scene_cache", {}).clear()
            except Exception:
                pass
            return {"ok": True, "reloaded": dropped}
        return webapi.handle(payload)
