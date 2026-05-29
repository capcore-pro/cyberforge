"""
Managed application_web service.

Split deploy model:
- GitHub: one branch per app (monorepo structure)
  - frontend/ (Next.js)
  - backend/  (FastAPI)
- Railway: deploy backend/ service from GitHub branch
- Vercel: deploy frontend/ from GitHub branch with env pointing to Railway backend URL
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import Any

from config import Settings, get_settings
from cost_tracker import maybe_track_cost
from db.managed_projects_store import ManagedProjectsStore
from tools.export_github import delete_github_branch, push_vitrine_site_to_github
from tools.export_railway import (
    RailwayExportError,
    delete_railway_service,
    deploy_github_backend_service,
)
from tools.vercel_api import (
    VercelError,
    delete_project,
    ensure_project_for_github_branch,
    wait_for_deployment_ready,
    trigger_git_deploy,
    delete_deployments_for_branch,
)

logger = logging.getLogger(__name__)


class ManagedApplicationWebError(Exception):
    pass


def _now() -> str:
    return datetime.now(tz=UTC).isoformat()


def _scaffold_files(prompt: str, slug: str) -> dict[str, str]:
    """
    Minimal monorepo scaffold (frontend Next.js + backend FastAPI).
    This keeps V1 deterministic; later iterations can call CoreMind generators.
    """
    safe_title = slug.replace("-", " ").title()
    frontend_pkg = f"""{{
  "name": "{slug}-frontend",
  "version": "0.1.0",
  "private": true,
  "scripts": {{
    "dev": "next dev",
    "build": "next build",
    "start": "next start",
    "lint": "next lint"
  }},
  "dependencies": {{
    "next": "^14.2.35",
    "react": "^18.3.1",
    "react-dom": "^18.3.1"
  }},
  "devDependencies": {{
    "@types/node": "^22.15.21",
    "@types/react": "^18.3.20",
    "@types/react-dom": "^18.3.7",
    "typescript": "^5.8.3"
  }}
}}
"""
    frontend_layout = f"""export default function RootLayout({{ children }}: {{ children: React.ReactNode }}) {{
  return (
    <html lang="fr">
      <body style={{{{ fontFamily: "system-ui", margin: 0, background: "#0a0a0f", color: "#e5e7eb" }}}}>
        <div style={{{{ padding: 24, maxWidth: 960, margin: "0 auto" }}}}>
          <div style={{{{ opacity: 0.8, fontSize: 12, letterSpacing: "0.12em", textTransform: "uppercase" }}}}>
            CyberForge · application_web
          </div>
          <h1 style={{{{ marginTop: 8 }}}}>{safe_title}</h1>
          <div style={{{{ opacity: 0.8, marginTop: 8 }}}}>{prompt.strip()[:220]}</div>
          <div style={{{{ marginTop: 16 }}}}>{{children}}</div>
        </div>
      </body>
    </html>
  );
}}
"""
    frontend_page = """async function getApiHealth() {
  const base = process.env.NEXT_PUBLIC_API_BASE_URL || "";
  if (!base) return { ok: false, error: "NEXT_PUBLIC_API_BASE_URL missing" };
  try {
    const r = await fetch(base.replace(/\\/$/, "") + "/health", { cache: "no-store" });
    const txt = await r.text();
    return { ok: r.ok, status: r.status, body: txt.slice(0, 400) };
  } catch (e: any) {
    return { ok: false, error: String(e?.message || e) };
  }
}

export default async function Page() {
  const health = await getApiHealth();
  return (
    <div style={{ display: "grid", gap: 12 }}>
      <div style={{ padding: 12, border: "1px solid rgba(255,255,255,0.12)", borderRadius: 8 }}>
        <div style={{ fontWeight: 600 }}>Backend health</div>
        <pre style={{ whiteSpace: "pre-wrap", margin: 0, marginTop: 8, opacity: 0.9 }}>
{JSON.stringify(health, null, 2)}
        </pre>
      </div>
    </div>
  );
}
"""
    frontend_next_config = """/** @type {import('next').NextConfig} */
const nextConfig = {};
export default nextConfig;
"""
    frontend_tsconfig = """{
  "compilerOptions": {
    "target": "ES2022",
    "lib": ["dom", "dom.iterable", "esnext"],
    "allowJs": true,
    "skipLibCheck": true,
    "strict": true,
    "noEmit": true,
    "esModuleInterop": true,
    "module": "esnext",
    "moduleResolution": "bundler",
    "resolveJsonModule": true,
    "isolatedModules": true,
    "jsx": "preserve",
    "incremental": true
  },
  "include": ["next-env.d.ts", "**/*.ts", "**/*.tsx"],
  "exclude": ["node_modules"]
}
"""
    backend_req = """fastapi==0.115.0
uvicorn[standard]==0.30.6
"""
    backend_main = """from fastapi import FastAPI

app = FastAPI(title="CyberForge App Backend")

@app.get("/health")
def health():
    return {"status": "ok"}
"""
    backend_dockerfile = """FROM python:3.11-slim
WORKDIR /app
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
COPY requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
CMD ["sh", "-c", "uvicorn main:app --host 0.0.0.0 --port ${PORT:-8000}"]
"""
    railway_json = """{
  "$schema": "https://railway.com/railway.schema.json",
  "build": { "builder": "NIXPACKS" }
}
"""
    return {
        # frontend
        "frontend/package.json": frontend_pkg,
        "frontend/next-env.d.ts": "/// <reference types=\"next\" />\n/// <reference types=\"next/image-types/global\" />\n",
        "frontend/next.config.mjs": frontend_next_config,
        "frontend/tsconfig.json": frontend_tsconfig,
        "frontend/app/layout.tsx": frontend_layout,
        "frontend/app/page.tsx": frontend_page,
        # backend
        "backend/requirements.txt": backend_req,
        "backend/main.py": backend_main,
        "backend/Dockerfile": backend_dockerfile,
        "backend/railway.json": railway_json,
        # repo meta
        "README.md": f"# {safe_title}\n\nGenerated by CyberForge.\n",
    }


async def provision_application_web(
    *,
    project_id: str,
    run_id: str,
    prompt: str,
    settings: Settings | None = None,
    store: ManagedProjectsStore,
) -> None:
    resolved = settings or get_settings()
    st = store
    project = await st.get_project(project_id)
    if not project:
        raise ManagedApplicationWebError("Projet introuvable.")

    await st.update_project(project_id, patch={"status": "building", "error_last": None})

    slug = project.github_branch
    github_repo = project.github_repo

    # 1) Generate and push sources to GitHub branch
    files = _scaffold_files(prompt, slug)
    await push_vitrine_site_to_github(branch_slug=slug, files=files, settings=resolved, repo=github_repo)
    maybe_track_cost(project_id, "github", {"requests": 1})

    # 2) Deploy backend to Railway
    try:
        shared_project_id = (getattr(resolved, "railway_shared_project_id", None) or "").strip() or None
        backend_url, railway_project_id, railway_service_id = await deploy_github_backend_service(
            project_name=slug,
            github_repo=github_repo,
            branch=slug,
            root_directory="backend",
            start_command=None,
            shared_project_id=shared_project_id,
            settings=resolved,
        )
    except RailwayExportError as exc:
        await st.update_project(project_id, patch={"status": "failed", "error_last": f"Railway: {exc}"})
        await st.finish_run(run_id, status="failed", error=str(exc))
        return

    maybe_track_cost(project_id, "railway", {"requests": 1})

    # 3) Deploy frontend to Vercel (Next.js)
    try:
        vercel_project_id = project.vercel_frontend_project_id or project.vercel_project_id
        vercel_project_id = vercel_project_id or await ensure_project_for_github_branch(
            project_name=slug,
            github_repo=github_repo,
            production_branch=slug,
            root_directory="frontend",
            env={
                "NEXT_PUBLIC_API_BASE_URL": backend_url,
                "NEXT_PUBLIC_APP_SLUG": slug,
            },
            settings=resolved,
        )
        org, repo_name = github_repo.split("/", 1)
        triggered = await trigger_git_deploy(
            project_name=slug,
            github_org=org,
            github_repo=repo_name,
            git_ref=slug,
            settings=resolved,
        )
        dep = await wait_for_deployment_ready(triggered.id, settings=resolved, timeout_seconds=420.0)
        url_preview = f"https://{dep.url}" if dep.url else None
        url_production = f"https://{slug}.vercel.app"
        status = "deployed" if dep.ready_state == "READY" else "failed"
        if status == "deployed":
            maybe_track_cost(project_id, "vercel", {"requests": 1})

        await st.update_project(
            project_id,
            patch={
                "title": project.title or slug,
                "prompt_last": prompt,
                "status": status,
                "vercel_project_id": vercel_project_id,
                "vercel_frontend_project_id": vercel_project_id,
                "vercel_deployment_id_last": dep.id,
                "url_preview": url_preview,
                "url_production": url_production if status == "deployed" else url_preview,
                "url_backend": backend_url,
                "railway_project_id": railway_project_id,
                "railway_service_id": railway_service_id,
                "error_last": None if status == "deployed" else "Vercel deployment failed",
            },
        )
        await st.finish_run(
            run_id,
            status="succeeded" if status == "deployed" else "failed",
            error=None if status == "deployed" else "Vercel deployment failed",
            artifacts={
                "railway_project_id": railway_project_id,
                "railway_service_id": railway_service_id,
                "backend_url": backend_url,
                "vercel_project_id": vercel_project_id,
                "vercel_deployment_id": dep.id,
            },
        )
    except (VercelError, Exception) as exc:
        await st.update_project(project_id, patch={"status": "failed", "error_last": f"Vercel: {exc}"})
        await st.finish_run(run_id, status="failed", error=str(exc))


async def update_application_web(
    *,
    project_id: str,
    prompt: str,
    settings: Settings | None = None,
    store: ManagedProjectsStore,
) -> None:
    resolved = settings or get_settings()
    st = store
    project = await st.get_project(project_id)
    if not project:
        raise ManagedApplicationWebError("Projet introuvable.")
    run = await st.create_run(project_id, action="update")
    await provision_application_web(project_id=project_id, run_id=run.id, prompt=prompt, settings=resolved, store=st)


async def hard_delete_application_web(
    *,
    project_id: str,
    settings: Settings | None = None,
    store: ManagedProjectsStore,
) -> None:
    resolved = settings or get_settings()
    st = store
    project = await st.get_project(project_id)
    if not project:
        return

    run = await st.create_run(project_id, action="delete")
    await st.update_project(project_id, patch={"status": "deleting", "error_last": None})

    artifacts: dict[str, Any] = {}

    # Vercel cleanup
    try:
        if project.vercel_frontend_project_id or project.vercel_project_id:
            pid = project.vercel_frontend_project_id or project.vercel_project_id
            if pid:
                await delete_deployments_for_branch(
                    branch=project.github_branch,
                    project_id=pid,
                    settings=resolved,
                    limit=20,
                )
                deleted = await delete_project(pid, settings=resolved)
                artifacts["vercel_project_deleted"] = deleted
    except Exception as exc:
        artifacts["vercel_error"] = str(exc)

    # Railway cleanup
    try:
        token = (getattr(resolved, "railway_api_key", None) or None)
        # resolved.railway_api_key is SecretStr; reuse deploy_railway's token extraction
        from config import plain_secret_str

        api_token = plain_secret_str(token)
        if api_token and project.railway_service_id:
            artifacts["railway_service_deleted"] = await delete_railway_service(
                service_id=project.railway_service_id,
                token=api_token,
            )
        # Option C: keep shared project, do not delete it.
    except Exception as exc:
        artifacts["railway_error"] = str(exc)

    # GitHub branch cleanup
    try:
        deleted_branch = await delete_github_branch(repo=project.github_repo, branch=project.github_branch, settings=resolved)
        artifacts["github_branch_deleted"] = deleted_branch
    except Exception as exc:
        artifacts["github_branch_error"] = str(exc)

    await st.update_project(project_id, patch={"status": "deleted", "deleted_at": _now()})
    await st.finish_run(run.id, status="succeeded", artifacts=artifacts)

