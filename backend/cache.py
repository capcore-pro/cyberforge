"""
Cache TTL simple en mémoire pour endpoints fréquemment sollicités.
"""

from __future__ import annotations

import time
from collections.abc import Callable, Coroutine
from functools import wraps
from typing import Any, ParamSpec, TypeVar

P = ParamSpec("P")
T = TypeVar("T")


def ttl_cache(*, seconds: float = 30.0) -> Callable[[Callable[P, Coroutine[Any, Any, T]]], Callable[P, Coroutine[Any, Any, T]]]:
    """Décorateur async — met en cache le résultat pendant `seconds` secondes."""

    def decorator(
        fn: Callable[P, Coroutine[Any, Any, T]],
    ) -> Callable[P, Coroutine[Any, Any, T]]:
        store: dict[str, tuple[float, T]] = {}

        def _cache_key(args: tuple[Any, ...], kwargs: dict[str, Any]) -> str:
            return repr((args, tuple(sorted(kwargs.items()))))

        @wraps(fn)
        async def wrapper(*args: P.args, **kwargs: P.kwargs) -> T:
            key = _cache_key(args, kwargs)
            now = time.monotonic()
            hit = store.get(key)
            if hit is not None and now < hit[0]:
                return hit[1]
            result = await fn(*args, **kwargs)
            store[key] = (now + seconds, result)
            return result

        def cache_clear() -> None:
            store.clear()

        wrapper.cache_clear = cache_clear  # type: ignore[attr-defined]
        return wrapper

    return decorator
