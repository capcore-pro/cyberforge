"""Tests normalisation UTF-8 des secrets."""

from security.secret_encoding import (
    normalize_secret_map,
    normalize_secret_text,
    secret_for_http_header,
)


def test_normalize_secret_strips_bom() -> None:
    assert normalize_secret_text("\ufeffsk-test") == "sk-test"


def test_normalize_secret_bytes_utf8() -> None:
    assert normalize_secret_text(b"sk-abc123") == "sk-abc123"


def test_secret_for_http_header_ascii() -> None:
    assert secret_for_http_header("sk-12345") == "sk-12345"


def test_secret_for_http_header_strips_non_ascii_after_repair() -> None:
    # Caractère latin-1 isolé (souvent une erreur d'encodage sur une clé ASCII)
    result = secret_for_http_header("sk-valid\xe9")
    assert "\xe9" not in result.encode("ascii", errors="ignore").decode() or result == "sk-valid"
    result.encode("ascii")


def test_normalize_secret_map() -> None:
    out = normalize_secret_map(
        {"DEEPSEEK_API_KEY": " sk-1 ", "EMPTY": "", "BAD": 12}
    )
    assert out == {"DEEPSEEK_API_KEY": "sk-1"}
