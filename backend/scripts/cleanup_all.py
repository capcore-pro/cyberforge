"""
Orchestrateur de nettoyage — exécute tous les scripts de cleanup en une commande.

Ordre:
  1) Supabase (cleanup_test_data.py)
  2) Cloudflare (cleanup_cloudflare.py)
  3) Vercel (cleanup_vercel.py)
  4) Railway + SQLite (cleanup_railway_sqlite.py)
"""

from __future__ import annotations

import importlib.util
import sys
import traceback
from pathlib import Path
from typing import Callable

from dotenv import load_dotenv


def _print_step_header(step_idx: int, total: int, title: str) -> None:
    print("\n" + "=" * 50)
    print(f"ÉTAPE {step_idx}/{total} — Nettoyage {title}")
    print("=" * 50 + "\n")


def _load_module_from_path(module_name: str, path: Path):
    spec = importlib.util.spec_from_file_location(module_name, str(path))
    if spec is None or spec.loader is None:
        raise ImportError(f"Impossible d'importer le module depuis {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _run_step(fn: Callable[[], int]) -> tuple[bool, str | None]:
    try:
        code = fn()
        # Convention: main() retourne 0 si succès
        if isinstance(code, int) and code != 0:
            return False, f"Code de sortie non nul: {code}"
        return True, None
    except SystemExit as exc:
        # Certains scripts peuvent faire raise SystemExit(main())
        code = exc.code
        if code in (None, 0):
            return True, None
        return False, f"SystemExit: {code}"
    except Exception as exc:
        return False, f"{type(exc).__name__}: {exc}"


def main() -> int:
    # Charge automatiquement le .env du backend
    load_dotenv(dotenv_path="backend/.env")

    root = Path(__file__).resolve().parents[2]  # .../cyberforge
    scripts_dir = root / "backend" / "scripts"

    steps = [
        ("Supabase", scripts_dir / "cleanup_test_data.py", "cleanup_test_data", "main"),
        ("Cloudflare", scripts_dir / "cleanup_cloudflare.py", "cleanup_cloudflare", "main"),
        ("Vercel", scripts_dir / "cleanup_vercel.py", "cleanup_vercel", "main"),
        (
            "Railway + SQLite",
            scripts_dir / "cleanup_railway_sqlite.py",
            "cleanup_railway_sqlite",
            "main",
        ),
    ]

    results: dict[str, bool] = {}
    errors: dict[str, str] = {}

    total = len(steps)
    for idx, (label, path, module_name, fn_name) in enumerate(steps, start=1):
        _print_step_header(idx, total, label)
        try:
            if not path.exists():
                raise FileNotFoundError(str(path))
            mod = _load_module_from_path(module_name, path)
            fn = getattr(mod, fn_name, None)
            if not callable(fn):
                raise AttributeError(f"Fonction {fn_name}() introuvable dans {path.name}")
            ok, err = _run_step(fn)
            results[label] = ok
            if not ok and err:
                errors[label] = err
                print(f"[ERREUR] {label}: {err}", file=sys.stderr)
                traceback.print_exc()
        except Exception as exc:
            results[label] = False
            errors[label] = f"{type(exc).__name__}: {exc}"
            print(f"[ERREUR] {label}: {errors[label]}", file=sys.stderr)
            traceback.print_exc()
            # continue

    def status(label: str) -> str:
        return "OK" if results.get(label) else "ERREUR"

    print("\n✅ Nettoyage terminé")
    print(f"  Supabase : {status('Supabase')}")
    print(f"  Cloudflare : {status('Cloudflare')}")
    print(f"  Vercel : {status('Vercel')}")
    print(f"  Railway + SQLite : {status('Railway + SQLite')}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())

