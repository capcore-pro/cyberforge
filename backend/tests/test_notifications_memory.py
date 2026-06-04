"""Tests notifications système en mémoire."""

import pytest

from api.notifications_memory import NotificationMemoryStore, notify


@pytest.mark.asyncio
async def test_list_unread_and_mark_read() -> None:
    store = NotificationMemoryStore()
    await store.add(title="A", type="test", level="info")
    row_b = await store.add(title="B", type="test", level="warning")

    unread = await store.list_items(unread_only=True)
    assert len(unread) == 2

    marked = await store.mark_read(row_b.id)
    assert marked is not None
    assert marked.read is True

    assert await store.unread_count() == 1
    unread_after = await store.list_items(unread_only=True)
    assert len(unread_after) == 1
    assert unread_after[0].title == "A"


@pytest.mark.asyncio
async def test_mark_all_read_and_clear() -> None:
    store = NotificationMemoryStore()
    await store.add(title="One", type="t", level="info")
    await store.add(title="Two", type="t", level="error")

    assert await store.mark_all_read() == 2
    assert await store.unread_count() == 0

    assert await store.clear() == 2
    assert await store.list_items() == []


@pytest.mark.asyncio
async def test_notify_helper() -> None:
    row = await notify(
        "Déploiement OK",
        "deploy",
        level="success",
        message="URL publiée",
        project_name="Client Test",
    )
    assert row.id
    assert row.read is False
    assert row.level == "success"
    assert row.project_name == "Client Test"
