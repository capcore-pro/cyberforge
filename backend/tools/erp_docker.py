"""
Générateur Docker Compose et orchestration ERP (Odoo, ERPNext, Custom).
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import re
import shutil
import subprocess
from collections.abc import AsyncIterator, Callable
from pathlib import Path
from typing import Any

import httpx

logger = logging.getLogger(__name__)


class ErpDockerError(Exception):
    """Erreur lors d'une opération Docker ERP."""


def get_erp_build_root(project_id: str) -> Path:
    base = Path(os.getenv("ERP_BUILD_ROOT", os.path.join(os.path.tempdir(), "erp_builds")))
    root = base / project_id
    root.mkdir(parents=True, exist_ok=True)
    return root


def _slug(value: str, fallback: str = "erp") -> str:
    s = re.sub(r"[^a-z0-9-]", "-", (value or fallback).lower())
    return re.sub(r"-+", "-", s).strip("-")[:40] or fallback


def _port_for_project(project: dict[str, Any], base: int, index: int = 0) -> int:
    if project.get("port"):
        return int(project["port"])
    pid = str(project.get("id") or "")
    offset = sum(ord(c) for c in pid[:8]) % 200 if pid else index
    return base + offset


def generate_odoo_compose(project: dict[str, Any]) -> tuple[str, int, str]:
    """Génère docker-compose.yml pour Odoo 17."""
    project_id = str(project.get("id") or "odoo")
    name = _slug(str(project.get("name") or "odoo"), "odoo")
    container = f"cyberforge-odoo-{name}"
    port = _port_for_project(project, 8069)
    admin_email = str(project.get("admin_email") or "admin@cyberforge.local")
    admin_password = str(project.get("admin_password") or "CyberForge2026!")
    db_password = f"odoo_{project_id[:8]}"

    compose = f"""services:
  db:
    image: postgres:15
    container_name: {container}-db
    environment:
      POSTGRES_DB: postgres
      POSTGRES_USER: odoo
      POSTGRES_PASSWORD: {db_password}
    volumes:
      - odoo-db-{name}:/var/lib/postgresql/data
    restart: unless-stopped

  odoo:
    image: odoo:17
    container_name: {container}
    depends_on:
      - db
    ports:
      - "{port}:8069"
    environment:
      HOST: db
      USER: odoo
      PASSWORD: {db_password}
    volumes:
      - odoo-web-{name}:/var/lib/odoo
    restart: unless-stopped

volumes:
  odoo-db-{name}:
  odoo-web-{name}:
"""
    return compose, port, container


def generate_erpnext_compose(project: dict[str, Any]) -> tuple[str, int, str]:
    """Génère docker-compose.yml pour ERPNext 15 (stack simplifiée)."""
    project_id = str(project.get("id") or "erpnext")
    name = _slug(str(project.get("name") or "erpnext"), "erpnext")
    container = f"cyberforge-erpnext-{name}"
    port = _port_for_project(project, 8080)
    admin_password = str(project.get("admin_password") or "CyberForge2026!")
    db_root = f"root_{project_id[:8]}"

    compose = f"""services:
  mariadb:
    image: mariadb:10.6
    container_name: {container}-db
    command: --character-set-server=utf8mb4 --collation-server=utf8mb4_unicode_ci
    environment:
      MYSQL_ROOT_PASSWORD: {db_root}
    volumes:
      - erpnext-db-{name}:/var/lib/mysql
    restart: unless-stopped

  redis:
    image: redis:7-alpine
    container_name: {container}-redis
    restart: unless-stopped

  erpnext:
    image: frappe/erpnext:v15.0.0
    container_name: {container}
    depends_on:
      - mariadb
      - redis
    ports:
      - "{port}:8080"
    environment:
      DB_HOST: mariadb
      DB_PORT: 3306
      REDIS_CACHE: redis:6379
      REDIS_QUEUE: redis:6379
      REDIS_SOCKETIO: redis:6379
      ADMIN_PASSWORD: {admin_password}
    volumes:
      - erpnext-sites-{name}:/home/frappe/frappe-bench/sites
    restart: unless-stopped

volumes:
  erpnext-db-{name}:
  erpnext-sites-{name}:
"""
    return compose, port, container


def generate_custom_compose(project: dict[str, Any]) -> tuple[str, int, str]:
    """Génère docker-compose.yml ERP custom léger (FastAPI + PostgreSQL + React)."""
    name = _slug(str(project.get("name") or "custom"), "custom")
    container = f"cyberforge-custom-{name}"
    port = _port_for_project(project, 3000)
    api_port = port + 1000
    admin_email = str(project.get("admin_email") or "admin@cyberforge.local")
    admin_password = str(project.get("admin_password") or "CyberForge2026!")
    db_password = f"erp_{str(project.get('id') or 'x')[:8]}"

    compose = f"""services:
  db:
    image: postgres:15-alpine
    container_name: {container}-db
    environment:
      POSTGRES_DB: erp
      POSTGRES_USER: erp
      POSTGRES_PASSWORD: {db_password}
    volumes:
      - custom-db-{name}:/var/lib/postgresql/data
    restart: unless-stopped
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U erp"]
      interval: 5s
      timeout: 5s
      retries: 5

  api:
    image: python:3.11-slim
    container_name: {container}-api
    working_dir: /app
    depends_on:
      db:
        condition: service_healthy
    ports:
      - "{api_port}:8000"
    environment:
      DATABASE_URL: postgresql://erp:{db_password}@db:5432/erp
      ADMIN_EMAIL: {admin_email}
      ADMIN_PASSWORD: {admin_password}
    volumes:
      - ./api:/app
    command: sh -c "pip install -q fastapi uvicorn && uvicorn main:app --host 0.0.0.0 --port 8000"
    restart: unless-stopped

  web:
    image: nginx:alpine
    container_name: {container}
    depends_on:
      - api
    ports:
      - "{port}:80"
    volumes:
      - ./web:/usr/share/nginx/html:ro
    restart: unless-stopped

volumes:
  custom-db-{name}:
"""
    return compose, port, container


def generate_compose_for_project(project: dict[str, Any]) -> tuple[str, int, str]:
    erp_type = str(project.get("erp_type") or "custom")
    if erp_type == "odoo":
        return generate_odoo_compose(project)
    if erp_type == "erpnext":
        return generate_erpnext_compose(project)
    return generate_custom_compose(project)


def _docker_compose_cmd() -> list[str]:
    if shutil.which("docker"):
        return ["docker", "compose"]
    if shutil.which("docker-compose"):
        return ["docker-compose"]
    raise ErpDockerError(
        "Docker non disponible. Vérifiez que Docker Desktop est installé et démarré."
    )


def _check_docker_daemon() -> None:
    try:
        proc = subprocess.run(
            ["docker", "info"],
            capture_output=True,
            text=True,
            timeout=15,
        )
    except FileNotFoundError as exc:
        raise ErpDockerError("Docker CLI introuvable. Installez Docker Desktop.") from exc
    except subprocess.TimeoutExpired as exc:
        raise ErpDockerError("Docker ne répond pas (timeout).") from exc
    if proc.returncode != 0:
        err = (proc.stderr or proc.stdout or "").lower()
        if "cannot connect" in err or "daemon" in err:
            raise ErpDockerError(
                "Le daemon Docker n'est pas démarré. Lancez Docker Desktop puis réessayez."
            )
        raise ErpDockerError(f"Docker indisponible : {(proc.stderr or proc.stdout)[-500:]}")


def _write_custom_api(root: Path, project: dict[str, Any]) -> None:
    api_dir = root / "api"
    api_dir.mkdir(exist_ok=True)
    name = str(project.get("name") or "ERP Custom")
    main_py = f'''"""ERP Custom CapCore — API minimale."""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="{name}")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

@app.get("/health")
def health():
    return {{"status": "ok", "erp": "custom"}}

@app.get("/api/info")
def info():
    return {{"name": "{name}", "version": "1.0.0"}}
'''
    (api_dir / "main.py").write_text(main_py, encoding="utf-8")


def _write_web_placeholder(root: Path, project: dict[str, Any], port: int) -> None:
    web = root / "web"
    web.mkdir(exist_ok=True)
    name = str(project.get("name") or "ERP Custom")
    primary = str(project.get("primary_color") or "#0f1117")
    html = f"""<!DOCTYPE html>
<html lang="fr"><head><meta charset="UTF-8"><title>{name}</title>
<style>body{{margin:0;font-family:system-ui;background:{primary};color:#fff;
display:flex;align-items:center;justify-content:center;min-height:100vh}}
.card{{background:#1a1d27;padding:2rem;border-radius:16px;text-align:center}}
</style></head><body><div class="card"><h1>{name}</h1>
<p>ERP Custom CapCore — port {port}</p></div></body></html>"""
    (web / "index.html").write_text(html, encoding="utf-8")


async def run_docker_compose(
    project_id: str,
    compose_content: str,
    project: dict[str, Any],
    on_log: Callable[[str], None] | None = None,
) -> dict[str, Any]:
    """
    Écrit docker-compose.yml, lance docker compose up -d,
    streame les logs et vérifie les containers.
    """
    _check_docker_daemon()
    root = get_erp_build_root(project_id)
    compose_path = root / "docker-compose.yml"
    compose_path.write_text(compose_content, encoding="utf-8")

    erp_type = str(project.get("erp_type") or "custom")
    if erp_type == "custom":
        port = int(project.get("port") or _port_for_project(project, 3000))
        _write_web_placeholder(root, project, port)
        _write_custom_api(root, project)

    cmd_base = _docker_compose_cmd()
    env = {**os.environ, "COMPOSE_PROJECT_NAME": f"cyberforge-erp-{project_id[:8]}"}

    def log(msg: str) -> None:
        logger.info(msg)
        if on_log:
            on_log(msg)

    log("Génération docker-compose terminée.")

    up_cmd = [*cmd_base, "-f", str(compose_path), "up", "-d", "--remove-orphans"]
    log(f"Commande : {' '.join(up_cmd)}")

    proc = await asyncio.create_subprocess_exec(
        *up_cmd,
        cwd=str(root),
        env=env,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.STDOUT,
    )
    output_lines: list[str] = []
    assert proc.stdout is not None
    while True:
        line = await proc.stdout.readline()
        if not line:
            break
        text = line.decode("utf-8", errors="replace").rstrip()
        output_lines.append(text)
        log(text)

    await proc.wait()
    full_output = "\n".join(output_lines)
    if proc.returncode != 0:
        if "port is already allocated" in full_output.lower() or "bind" in full_output.lower():
            raise ErpDockerError(
                "Port déjà utilisé. Modifiez le port dans la configuration et réessayez."
            )
        if "pull" in full_output.lower() and ("not found" in full_output.lower() or "manifest" in full_output.lower()):
            raise ErpDockerError(
                "Image Docker introuvable. Vérifiez votre connexion internet et réessayez."
            )
        raise ErpDockerError(f"docker compose up a échoué :\n{full_output[-2000:]}")

    port = int(project.get("port") or 8080)
    url = f"http://localhost:{port}"
    admin_email = str(project.get("admin_email") or "admin@cyberforge.local")
    admin_password = str(project.get("admin_password") or "CyberForge2026!")

    # Vérification santé (best-effort)
    healthy = False
    for attempt in range(12):
        await asyncio.sleep(5)
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                resp = await client.get(url)
                if resp.status_code < 500:
                    healthy = True
                    break
        except httpx.HTTPError:
            log(f"Vérification santé… tentative {attempt + 1}/12")

    log("Vérification santé terminée." if healthy else "Services démarrés (santé non confirmée).")

    return {
        "url": url,
        "admin_email": admin_email,
        "admin_password": admin_password,
        "logs": full_output,
        "healthy": healthy,
    }


async def stop_erp(project_id: str) -> None:
    """Arrête les containers du projet."""
    root = get_erp_build_root(project_id)
    compose_path = root / "docker-compose.yml"
    if not compose_path.exists():
        raise ErpDockerError("Aucune installation Docker trouvée pour ce projet.")
    cmd_base = _docker_compose_cmd()
    env = {**os.environ, "COMPOSE_PROJECT_NAME": f"cyberforge-erp-{project_id[:8]}"}
    proc = await asyncio.create_subprocess_exec(
        *cmd_base,
        "-f",
        str(compose_path),
        "down",
        cwd=str(root),
        env=env,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.STDOUT,
    )
    await proc.communicate()
    if proc.returncode != 0:
        raise ErpDockerError("docker compose down a échoué.")


async def restart_erp(project_id: str, project: dict[str, Any]) -> dict[str, Any]:
    """Redémarre les containers."""
    root = get_erp_build_root(project_id)
    compose_path = root / "docker-compose.yml"
    if not compose_path.exists():
        content = project.get("docker_compose_content")
        if not content:
            raise ErpDockerError("Compose introuvable. Relancez l'installation.")
        compose_path.write_text(str(content), encoding="utf-8")

    cmd_base = _docker_compose_cmd()
    env = {**os.environ, "COMPOSE_PROJECT_NAME": f"cyberforge-erp-{project_id[:8]}"}
    proc = await asyncio.create_subprocess_exec(
        *cmd_base,
        "-f",
        str(compose_path),
        "restart",
        cwd=str(root),
        env=env,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.STDOUT,
    )
    await proc.communicate()
    return await get_erp_status(project_id, project)


async def get_erp_status(project_id: str, project: dict[str, Any] | None = None) -> dict[str, Any]:
    """Vérifie si les containers tournent et retourne stats basiques."""
    container_name = ""
    if project:
        container_name = str(project.get("container_name") or "")
    root = get_erp_build_root(project_id)
    compose_path = root / "docker-compose.yml"

    running = False
    stats: dict[str, Any] = {"cpu_percent": None, "mem_usage": None, "mem_limit": None}
    logs_tail: list[str] = []

    if not compose_path.exists():
        return {
            "status": "stopped",
            "running": False,
            "url": project.get("url") if project else None,
            "stats": stats,
            "logs_tail": logs_tail,
        }

    try:
        _check_docker_daemon()
        cmd_base = _docker_compose_cmd()
        env = {**os.environ, "COMPOSE_PROJECT_NAME": f"cyberforge-erp-{project_id[:8]}"}
        ps_proc = await asyncio.create_subprocess_exec(
            *cmd_base,
            "-f",
            str(compose_path),
            "ps",
            "--format",
            "json",
            cwd=str(root),
            env=env,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, _ = await ps_proc.communicate()
        ps_out = stdout.decode("utf-8", errors="replace")
        running = "running" in ps_out.lower() or '"running"' in ps_out.lower()

        if container_name:
            stats_proc = await asyncio.create_subprocess_exec(
                "docker",
                "stats",
                container_name,
                "--no-stream",
                "--format",
                "{{.CPUPerc}}|{{.MemUsage}}|{{.MemPerc}}",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            st_out, _ = await stats_proc.communicate()
            parts = st_out.decode().strip().split("|")
            if len(parts) >= 2:
                stats["cpu_percent"] = parts[0].strip()
                stats["mem_usage"] = parts[1].strip()
                if len(parts) >= 3:
                    stats["mem_limit"] = parts[2].strip()

        log_proc = await asyncio.create_subprocess_exec(
            *cmd_base,
            "-f",
            str(compose_path),
            "logs",
            "--tail",
            "20",
            cwd=str(root),
            env=env,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.STDOUT,
        )
        log_out, _ = await log_proc.communicate()
        logs_tail = [
            ln for ln in log_out.decode("utf-8", errors="replace").splitlines() if ln.strip()
        ][-20:]
    except ErpDockerError:
        return {
            "status": "error",
            "running": False,
            "url": project.get("url") if project else None,
            "stats": stats,
            "logs_tail": logs_tail,
            "error": "Docker indisponible",
        }

    status = "running" if running else "stopped"
    if project and project.get("status") == "installing":
        status = "installing"

    return {
        "status": status,
        "running": running,
        "url": project.get("url") if project else None,
        "stats": stats,
        "logs_tail": logs_tail,
    }


async def stream_install_logs(
    project_id: str,
    compose_content: str,
    project: dict[str, Any],
) -> AsyncIterator[dict[str, Any]]:
    """Générateur d'événements pour l'installation SSE."""
    events: list[tuple[str, dict[str, Any]]] = []

    def capture(msg: str) -> None:
        events.append(("log", {"message": msg}))

    yield {"event": "step", "message": "Génération docker-compose..."}
    yield {"event": "step", "message": "Téléchargement images Docker..."}

    try:
        result = await run_docker_compose(
            project_id,
            compose_content,
            project,
            on_log=capture,
        )
        for _, data in events:
            yield {"event": "log", **data}

        yield {"event": "step", "message": "Démarrage des services..."}
        yield {"event": "step", "message": "Vérification santé..."}
        yield {
            "event": "done",
            "url": result["url"],
            "admin_email": result["admin_email"],
            "admin_password": result["admin_password"],
            "healthy": result.get("healthy", False),
            "logs": result.get("logs", ""),
        }
    except ErpDockerError as exc:
        yield {"event": "error", "message": str(exc)}
