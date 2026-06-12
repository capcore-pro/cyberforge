"""
Exécution parallèle de coroutines avec gestion d'erreurs individuelle.
"""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Coroutine
from typing import Any

logger = logging.getLogger(__name__)


class ParallelExecutor:
    """
    Exécute des coroutines en parallèle avec gestion d'erreurs individuelle.
    Si une coroutine échoue → None pour ce résultat, les autres continuent.
    """

    async def run_parallel(self, tasks: dict[str, Coroutine[Any, Any, Any]]) -> dict[str, Any]:
        if not tasks:
            return {}

        names = list(tasks.keys())
        coros = list(tasks.values())

        results = await asyncio.gather(*coros, return_exceptions=True)

        output: dict[str, Any] = {}
        for name, result in zip(names, results):
            if isinstance(result, Exception):
                logger.warning("Parallel task %s failed: %s", name, result)
                output[name] = None
            else:
                output[name] = result

        return output


parallel_executor = ParallelExecutor()
