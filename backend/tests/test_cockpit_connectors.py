"""Tests connecteurs cockpit — repli sans clés API."""

from cockpit_connectors import CONNECTORS, get_connector
from cockpit_connectors.manual import ManualConnector
from cockpit_db import add_service, delete_service, init_db, set_balance


def test_get_connector_unknown_returns_none() -> None:
    assert get_connector("unknown_vendor", "key") is None


def test_manual_connector_uses_sqlite_balance() -> None:
    init_db()
    sid = add_service(
        name="Test Manual",
        api_key_env="TEST_MANUAL_KEY",
        connector="manual",
        service_id="test-manual-connector",
    )
    try:
        set_balance(sid, 42.5)
        conn = get_connector("manual", "", service_id=sid)
        assert isinstance(conn, ManualConnector)
        assert conn.get_balance() == 42.5
        assert conn.ping() is True
        usage = conn.get_usage()
        assert usage["source"] == "manual"
    finally:
        delete_service(sid)


def test_registry_includes_api_connectors() -> None:
    assert "anthropic" in CONNECTORS
    assert "deepseek" in CONNECTORS
    assert CONNECTORS["railway"] is ManualConnector
