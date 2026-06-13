"""
Notifications push Expo — envoi vers les tokens enregistrés.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any

logger = logging.getLogger(__name__)


def get_registered_tokens() -> list[str]:
    from api.routes.mobile import push_tokens

    return list(push_tokens)


async def send_push_notification(
    title: str,
    body: str,
    data: dict[str, Any] | None = None,
) -> None:
    tokens = get_registered_tokens()
    if not tokens:
        return

    payload = data or {}

    def _publish_all() -> None:
        try:
            from exponent_server_sdk import PushClient, PushMessage
        except ImportError:
            logger.warning("exponent-server-sdk non installé — push ignoré")
            return

        client = PushClient()
        for token in tokens:
            try:
                client.publish(
                    PushMessage(
                        to=token,
                        title=title,
                        body=body,
                        data=payload,
                        sound="default",
                    )
                )
            except Exception as exc:
                logger.warning("Push failed for token %s…: %s", token[:12], exc)

    await asyncio.to_thread(_publish_all)
