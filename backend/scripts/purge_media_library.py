"""Vide la médiathèque — fichiers locaux + entrées SQLite."""

from __future__ import annotations

import sqlite3
import sys
from pathlib import Path

_BACKEND = Path(__file__).resolve().parent.parent
if str(_BACKEND) not in sys.path:
    sys.path.insert(0, str(_BACKEND))

import media_db as db
from cockpit_db import _connect, _lock, init_db
from media_storage import delete_local, media_root


def main() -> None:
    init_db()
    db.init_media_db()

    assets = db.list_assets(limit=1000)
    deleted_files = 0
    deleted_rows = 0

    for asset in assets:
        local_path = str(asset.get("local_path") or "")
        if local_path:
            try:
                if delete_local(local_path):
                    deleted_files += 1
            except OSError as exc:
                print(f"  (ignoré, fichier verrouillé) {local_path}: {exc}")
        if db.delete_asset(str(asset["id"])):
            deleted_rows += 1

    with _lock:
        conn = _connect()
        try:
            conn.execute("DELETE FROM project_cover_images")
            conn.commit()
        finally:
            conn.close()

    # Nettoyer les fichiers orphelins restants dans media/images
    images_dir = media_root() / "images"
    orphan = 0
    orphan_failed = 0
    if images_dir.is_dir():
        for path in images_dir.iterdir():
            if not path.is_file():
                continue
            try:
                path.unlink(missing_ok=True)
                orphan += 1
            except OSError as exc:
                orphan_failed += 1
                print(f"  (orphelin verrouillé) {path.name}: {exc}")

    print(f"Assets supprimés (DB): {deleted_rows}")
    print(f"Fichiers supprimés (via DB): {deleted_files}")
    print(f"Fichiers orphelins supprimés (images/): {orphan}")
    if orphan_failed:
        print(f"Fichiers orphelins non supprimés (verrouillés): {orphan_failed}")
    print("Couvertures projet: table vidée")


if __name__ == "__main__":
    main()
