from __future__ import annotations

import threading


class ProgressState:

    def __init__(self):
        self._lock = threading.Lock()
        self._state = {"active": False, "phase": "", "current": 0,
                       "total": 0, "detail": ""}

    def set(self, phase, current=0, total=0, detail=""):
        with self._lock:
            self._state.update(active=True, phase=str(phase),
                               current=int(current), total=int(total),
                               detail=str(detail))

    def clear(self):
        with self._lock:
            self._state.update(active=False, phase="", current=0, total=0,
                               detail="")

    def snapshot(self) -> dict:
        with self._lock:
            return dict(self._state)
