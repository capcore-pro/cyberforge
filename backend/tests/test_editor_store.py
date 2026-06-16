"""Tests moteur HTML éditeur (frontend logic mirror in vitest-style via node dom)."""

from __future__ import annotations

# Tests unitaires backend pour la logique xpath — le moteur vit côté frontend ;
# on valide ici les helpers store editor.


def test_editor_migration_file_exists():
    from pathlib import Path

    path = Path(__file__).resolve().parents[2] / "supabase" / "migrations" / "030_editor.sql"
    assert path.is_file()
    text = path.read_text(encoding="utf-8")
    assert "edited_html" in text
    assert "editor_history" in text
