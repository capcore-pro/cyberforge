"""
Tampon circulaire des dernières lignes de log backend.
"""

from __future__ import annotations

import collections
import logging
from logging import Handler, LogRecord

_BUFFER: collections.deque[str] = collections.deque(maxlen=300)


class RingBufferHandler(Handler):
    def emit(self, record: LogRecord) -> None:
        try:
            _BUFFER.append(self.format(record))
        except Exception:
            self.handleError(record)


def attach_ring_buffer_handler() -> None:
    handler = RingBufferHandler()
    handler.setLevel(logging.INFO)
    handler.setFormatter(
        logging.Formatter("%(asctime)s [%(levelname)s] %(name)s — %(message)s")
    )
    root = logging.getLogger()
    if not any(isinstance(h, RingBufferHandler) for h in root.handlers):
        root.addHandler(handler)


def get_recent_lines(limit: int = 5) -> list[str]:
    n = max(1, min(limit, len(_BUFFER)))
    return list(_BUFFER)[-n:]


def export_all_lines() -> str:
    return "\n".join(_BUFFER)
