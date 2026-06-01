"""
Démos client — conversion React (useState todo) → HTML autonome + JavaScript vanilla.
"""

from __future__ import annotations

import json
import logging
import re

from tools.demo_preview_html import (
    PreviewMockup,
    build_mockup_preview_html,
    escape_attr,
    escape_html,
    extract_preview_mockup,
)
logger = logging.getLogger(__name__)

# Marqueur de version — les démos sans ce tag sont régénérées à l'unlock
TASK_PREVIEW_MARKER = "cf-preview:v2-react-todo"
PREMIUM_PREVIEW_MARKER = "cf-preview:v3-premium-saas"
STATIC_VANILLA_PREVIEW_MARKER = "cf-preview:v4-static-vanilla"

_TASK_HINTS = re.compile(
    r"(tâche|taches|todo|todos|task|tasks|checklist|to-do|gestionnaire\s+de\s+tâches|"
    r"liste\s+de\s+tâches|ajouter.*tâche|supprimer.*tâche|cocher)",
    re.I,
)
_REACT_TASK_MARKERS = re.compile(
    r"(useState\s*\(|addTask|toggleTask|deleteTask|removeTask|setTasks|"
    r"tasks\.map|task\.completed|completed\s*:)",
    re.I,
)


def is_fresh_task_preview_html(html: str | None) -> bool:
    if not html:
        return False
    return (
        PREMIUM_PREVIEW_MARKER in html or TASK_PREVIEW_MARKER in html
    ) and "function addTask" in html


def is_react_task_app(sources: str) -> bool:
    """Détecte une app React todo (useState + add/toggle/delete)."""
    if not re.search(r"useState", sources):
        return False
    has_tasks = bool(
        re.search(
            r"useState\s*\(\s*\[\s*|"
            r"\[\s*tasks\s*,\s*setTasks|"
            r"const\s*\[\s*tasks\s*,",
            sources,
            re.I,
        )
    )
    has_add = bool(re.search(r"\baddTask\b", sources))
    has_list = bool(re.search(r"tasks\.map\s*\(", sources))
    has_toggle = bool(
        re.search(r"\b(toggleTask|toggleComplete|toggleDone)\b", sources)
        or re.search(r"task\.completed|\.done", sources)
    )
    has_delete = bool(re.search(r"\b(deleteTask|removeTask)\b", sources))
    return has_tasks and has_add and has_list and (has_toggle or has_delete)


def classify_demo_kind(sources: str, title: str = "") -> str:
    blob = f"{title}\n{sources}"
    if is_react_task_app(sources) or _TASK_HINTS.search(blob) or _REACT_TASK_MARKERS.search(sources):
        return "tasks"
    return "showcase"


def _extract_task_title(sources: str, fallback: str) -> str:
    match = re.search(r"<h1[^>]*>([\s\S]*?)</h1>", sources, re.I)
    if match:
        text = re.sub(r"<[^>]+>", "", match.group(1)).strip()
        if text and len(text) < 80:
            return text
    return fallback


def _extract_subtitle(sources: str) -> str | None:
    for pattern in (
        r"<p[^>]*>([^<]{8,120})</p>",
        r"subtitle[\"']?\s*:\s*[\"']([^\"']+)[\"']",
    ):
        match = re.search(pattern, sources, re.I)
        if match:
            return match.group(1).strip()
    return None


def _extract_input_placeholder(sources: str) -> str:
    match = re.search(
        r"<input[^>]*placeholder\s*=\s*(?:\"([^\"]+)\"|'([^']+)'|\{`([^`]+)`\})",
        sources,
        re.I,
    )
    if match:
        return (match.group(1) or match.group(2) or match.group(3) or "").strip()
    return "Nouvelle tâche…"


def _extract_add_button_label(sources: str) -> str:
    match = re.search(
        r"<button[^>]*(?:onClick\s*=\s*\{?\s*addTask|type\s*=\s*[\"']submit[\"'])[^>]*>"
        r"([\s\S]*?)</button>",
        sources,
        re.I,
    )
    if match:
        label = re.sub(r"<[^>]+>", "", match.group(1)).strip()
        if label and len(label) < 40:
            return label
    return "Ajouter"


def _detect_done_field(sources: str) -> str:
    if re.search(r"task\.completed|completed\s*:|completed\s*\?", sources):
        return "completed"
    return "done"


def build_task_manager_standalone_html(
    *,
    title: str = "Gestion des tâches",
    subtitle: str | None = None,
    sources: str = "",
) -> str:
    """
    App todo autonome — UI SaaS premium (sidebar, header, tâches seed).
    """
    from tools.premium_task_saas_html import build_premium_task_manager_html

    html_out = build_premium_task_manager_html(
        title=title,
        subtitle=subtitle,
        sources=sources,
    )
    _log_html_structure("build_task_manager_standalone_html", html_out)
    return html_out


def _looks_like_react_source(sources: str) -> bool:
    return bool(
        re.search(
            r"(import\s+[\w{]|export\s+(default\s+)?(function|const)|"
            r"useState\s*\(|useEffect\s*\(|className\s*=)",
            sources,
        )
    )


def _is_usable_static_vanilla_html(html: str) -> bool:
    """HTML autonome exploitable (pas de JSX/React visible, contenu suffisant)."""
    if not html or len(html) < 600:
        return False
    lower = html.lower()
    if "<html" not in lower or "<body" not in lower:
        return False
    if re.search(r"\b(import\s+|export\s+default|useState\s*\()", html):
        return False
    if re.search(r"id=[\"']cf-demo-root[\"']", html, re.I):
        inner = re.search(
            r'id=["\']cf-demo-root["\']>([\s\S]*?)</div>',
            html,
            re.I,
        )
        if inner and len(inner.group(1).strip()) < 40:
            return False
    return True


def build_showcase_standalone_html(
    sources: str,
    *,
    title: str = "Démo CyberForge",
) -> str:
    """
    Convertit le TSX en HTML statique ; repli UI premium si la conversion échoue.
    Ne jamais afficher le code source React brut dans l'aperçu.
    """
    if _looks_like_react_source(sources):
        try:
            from tools.tsx_static_html import build_static_site_html

            static_html = build_static_site_html(sources, title=title)
            if _is_usable_static_vanilla_html(static_html):
                if STATIC_VANILLA_PREVIEW_MARKER not in static_html:
                    static_html = static_html.replace(
                        "<body>",
                        f"<body><!-- {STATIC_VANILLA_PREVIEW_MARKER} -->",
                        1,
                    )
                _log_html_structure("build_showcase_static_vanilla", static_html)
                return static_html
        except Exception:
            logger.exception(
                "[standalone_demo_html] conversion TSX→HTML échouée, repli premium"
            )

    from tools.premium_task_saas_html import build_premium_task_manager_html

    html_out = build_premium_task_manager_html(
        title=title,
        subtitle=_extract_subtitle(sources),
        sources=sources,
    )
    _log_html_structure("build_showcase_premium_fallback", html_out)
    return html_out


def _extract_head_inner_html(html: str) -> str:
    """Contenu intérieur de <head> (meta, title, style, etc.)."""
    match = re.search(r"<head[^>]*>([\s\S]*?)</head>", html, re.I)
    if match:
        return match.group(1).strip()
    return ""


def _extract_head_styles(html: str) -> str:
    """Blocs <style> du document source — à réinjecter dans le gate mot de passe."""
    head_inner = _extract_head_inner_html(html)
    if not head_inner:
        return ""
    blocks = re.findall(r"<style[^>]*>[\s\S]*?</style>", head_inner, re.I)
    return "\n".join(blocks)


def _extract_body_inner_html(html: str) -> str:
    """Contenu intérieur de <body> pour intégration inline (scripts inclus)."""
    match = re.search(r"<body[^>]*>([\s\S]*)</body>", html, re.I)
    if match:
        return match.group(1).strip()
    return html.strip()


def _log_html_structure(context: str, html: str, *, max_chars: int = 3500) -> None:
    """Log la structure du HTML généré (diagnostic CSS / head / body)."""
    head_block = re.search(r"<head[^>]*>[\s\S]*?</head>", html, re.I)
    body_block = re.search(r"<body[^>]*>[\s\S]*?</body>", html, re.I)
    style_in_head = bool(
        head_block and re.search(r"<style", head_block.group(0), re.I)
    )
    style_after_body = bool(re.search(r"</body>\s*<style", html, re.I))
    style_count = len(re.findall(r"<style", html, re.I))
    logger.info(
        "[standalone_demo_html] %s | len=%s | <style> count=%s | style_in_head=%s | "
        "style_after_body=%s | has_doctype=%s",
        context,
        len(html),
        style_count,
        style_in_head,
        style_after_body,
        html.lstrip().lower().startswith("<!doctype"),
    )
    if head_block:
        snippet = head_block.group(0)
        if len(snippet) > max_chars:
            snippet = snippet[:max_chars] + "\n... [head tronqué]"
        logger.info("[standalone_demo_html] %s | <head>:\n%s", context, snippet)
    if body_block:
        snippet = body_block.group(0)
        if len(snippet) > max_chars:
            snippet = snippet[:max_chars] + "\n... [body tronqué]"
        logger.info("[standalone_demo_html] %s | <body>:\n%s", context, snippet)


def wrap_with_password_gate(demo_html: str, password: str, *, title: str = "Démo CyberForge") -> str:
    """
    Enveloppe le livrable dans un écran de login cyber (validation JS côté client).
    La démo reste inline (display:none jusqu'à mot de passe correct).
    """
    secret = json.dumps(password, ensure_ascii=False)
    page_title = escape_html(title.strip() or "Démo CyberForge")
    demo_styles = _extract_head_styles(demo_html)
    demo_inner = _extract_body_inner_html(demo_html)

    _log_html_structure("wrap_with_password_gate:input", demo_html)
    logger.info(
        "[standalone_demo_html] wrap_with_password_gate | demo_styles_bytes=%s | "
        "demo_inner_bytes=%s | styles_preserved=%s",
        len(demo_styles.encode("utf-8")),
        len(demo_inner.encode("utf-8")),
        bool(demo_styles.strip()),
    )
    if not demo_styles.strip():
        logger.warning(
            "[standalone_demo_html] wrap_with_password_gate: aucun <style> extrait du "
            "<head> source — la démo sera sans CSS embarqué."
        )

    out = f"""<!DOCTYPE html>
<html lang="fr">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>{page_title} · Accès sécurisé</title>
  <style>
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      min-height: 100vh;
      background: #020617;
      color: #e2e8f0;
      font-family: system-ui, -apple-system, "Segoe UI", sans-serif;
    }}
    #cf-login-screen {{
      min-height: 100vh;
      display: flex;
      align-items: center;
      justify-content: center;
      padding: 2rem 1.25rem;
      background:
        radial-gradient(ellipse 80% 50% at 50% -20%, rgba(124, 58, 237, 0.35), transparent),
        radial-gradient(ellipse 60% 40% at 100% 50%, rgba(6, 182, 212, 0.12), transparent),
        #020617;
    }}
    .cf-login-card {{
      width: 100%;
      max-width: 22rem;
      padding: 2rem 1.75rem;
      border-radius: 0.85rem;
      border: 1px solid rgba(34, 211, 238, 0.35);
      background: rgba(15, 23, 42, 0.92);
      box-shadow: 0 0 40px rgba(124, 58, 237, 0.2), 0 0 80px rgba(6, 182, 212, 0.08);
    }}
    .cf-login-kicker {{
      font-size: 0.65rem;
      letter-spacing: 0.2em;
      text-transform: uppercase;
      color: #a78bfa;
      margin: 0 0 0.5rem;
    }}
    .cf-login-title {{
      font-size: 1.35rem;
      font-weight: 800;
      margin: 0 0 0.35rem;
      background: linear-gradient(90deg, #22d3ee, #a78bfa);
      -webkit-background-clip: text;
      background-clip: text;
      color: transparent;
    }}
    .cf-login-sub {{
      font-size: 0.85rem;
      color: #94a3b8;
      margin: 0 0 1.5rem;
      line-height: 1.45;
    }}
    .cf-login-label {{
      display: block;
      font-size: 0.75rem;
      color: #64748b;
      margin-bottom: 0.4rem;
    }}
    .cf-password-wrap {{
      position: relative;
      margin-bottom: 0.75rem;
    }}
    .cf-login-input {{
      width: 100%;
      padding: 0.7rem 2.75rem 0.7rem 0.9rem;
      border-radius: 0.5rem;
      border: 1px solid rgba(148, 163, 184, 0.3);
      background: #0f172a;
      color: #f1f5f9;
      font-size: 0.95rem;
      margin-bottom: 0;
    }}
    .cf-password-toggle {{
      position: absolute;
      right: 0.25rem;
      top: 50%;
      transform: translateY(-50%);
      display: flex;
      align-items: center;
      justify-content: center;
      width: 2.25rem;
      height: 2.25rem;
      border: none;
      border-radius: 0.35rem;
      background: rgba(15, 23, 42, 0.85);
      color: #94a3b8;
      cursor: pointer;
      padding: 0;
      z-index: 2;
    }}
    .cf-password-toggle:hover {{
      color: #22d3ee;
      background: rgba(34, 211, 238, 0.12);
    }}
    .cf-password-toggle svg {{
      width: 1.15rem;
      height: 1.15rem;
      display: block;
      pointer-events: none;
    }}
    .cf-password-toggle .cf-eye-off {{ display: none; }}
    .cf-password-toggle.cf-visible .cf-eye-on {{ display: none; }}
    .cf-password-toggle.cf-visible .cf-eye-off {{ display: block; }}
    .cf-login-input:focus {{
      outline: none;
      border-color: #22d3ee;
      box-shadow: 0 0 0 2px rgba(34, 211, 238, 0.25);
    }}
    .cf-login-btn {{
      width: 100%;
      padding: 0.75rem 1rem;
      border: none;
      border-radius: 0.5rem;
      font-weight: 700;
      font-size: 0.9rem;
      cursor: pointer;
      background: linear-gradient(90deg, #7c3aed, #06b6d4);
      color: #0a0a0f;
    }}
    .cf-login-btn:hover {{ filter: brightness(1.08); }}
    .cf-login-error {{
      display: none;
      margin-top: 0.85rem;
      padding: 0.65rem 0.75rem;
      border-radius: 0.45rem;
      font-size: 0.85rem;
      color: #fecaca;
      background: rgba(239, 68, 68, 0.15);
      border: 1px solid rgba(248, 113, 113, 0.45);
    }}
    .cf-login-error.cf-visible {{ display: block; }}
    #cf-demo-content {{ display: none; min-height: 100vh; position: relative; }}
    #cf-demo-content.cf-unlocked {{ display: block; }}
    .cf-lock-btn {{
      display: none;
      position: fixed;
      top: 0.65rem;
      right: 0.65rem;
      z-index: 10000;
      align-items: center;
      gap: 0.35rem;
      padding: 0.4rem 0.7rem;
      border-radius: 999px;
      border: 1px solid rgba(148, 163, 184, 0.35);
      background: rgba(15, 23, 42, 0.88);
      color: #94a3b8;
      font-size: 0.72rem;
      font-weight: 600;
      letter-spacing: 0.02em;
      cursor: pointer;
      backdrop-filter: blur(8px);
      box-shadow: 0 4px 16px rgba(0, 0, 0, 0.35);
    }}
    .cf-lock-btn:hover {{
      color: #e2e8f0;
      border-color: rgba(34, 211, 238, 0.45);
      background: rgba(30, 41, 59, 0.95);
    }}
    #cf-demo-content.cf-unlocked .cf-lock-btn {{ display: inline-flex; }}
  </style>
{demo_styles}
  <style id="cf-gate-overrides">
    #cf-login-screen .cf-password-wrap {{ position: relative; overflow: visible; }}
    #cf-login-screen #cf-password-toggle {{
      display: flex !important;
      visibility: visible !important;
      opacity: 1 !important;
    }}
    #cf-login-screen .cf-login-input {{
      padding-right: 2.75rem !important;
    }}
  </style>
</head>
<body>
  <div id="cf-login-screen" role="main" aria-label="Accès démo">
    <div class="cf-login-card">
      <p class="cf-login-kicker">// CYBERFORGE</p>
      <h1 class="cf-login-title">Démo protégée</h1>
      <p class="cf-login-sub">Saisissez le mot de passe fourni pour afficher le livrable client.</p>
      <form id="cf-login-form" autocomplete="off">
        <label class="cf-login-label" for="cf-password-input">Mot de passe</label>
        <div class="cf-password-wrap">
          <input
            id="cf-password-input"
            class="cf-login-input"
            type="password"
            placeholder="ex. soleil-bateau-rouge"
            required
            autofocus
          />
          <button
            type="button"
            class="cf-password-toggle"
            id="cf-password-toggle"
            aria-label="Afficher le mot de passe"
            title="Afficher le mot de passe"
          >
            <svg class="cf-eye-on" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true">
              <path d="M1 12s4-7 11-7 11 7 11 7-4 7-11 7-11-7-11-7z"/>
              <circle cx="12" cy="12" r="3"/>
            </svg>
            <svg class="cf-eye-off" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true">
              <path d="M17.94 17.94A10.07 10.07 0 0112 20c-7 0-11-8-11-8a18.45 18.45 0 015.06-5.94"/>
              <path d="M9.9 4.24A9.12 9.12 0 0112 4c7 0 11 8 11 8a18.5 18.5 0 01-2.16 3.19"/>
              <line x1="1" y1="1" x2="23" y2="23"/>
            </svg>
          </button>
        </div>
        <button type="submit" class="cf-login-btn">Accéder à la démo</button>
      </form>
      <p id="cf-login-error" class="cf-login-error" role="alert">Mot de passe incorrect.</p>
    </div>
  </div>
  <div id="cf-demo-content" aria-hidden="true">
    <button type="button" id="cf-lock-btn" class="cf-lock-btn" title="Verrouiller et effacer les données locales">
      Verrouiller
    </button>
{demo_inner}
  </div>
  <script>
(function () {{
  var EXPECTED = {secret};
  var form = document.getElementById("cf-login-form");
  var input = document.getElementById("cf-password-input");
  var togglePwd = document.getElementById("cf-password-toggle");
  var err = document.getElementById("cf-login-error");
  var login = document.getElementById("cf-login-screen");
  var demo = document.getElementById("cf-demo-content");
  var lockBtn = document.getElementById("cf-lock-btn");

  if (togglePwd && input) {{
    togglePwd.addEventListener("click", function () {{
      var visible = input.type === "text";
      input.type = visible ? "password" : "text";
      togglePwd.classList.toggle("cf-visible", !visible);
      togglePwd.setAttribute("aria-label", visible ? "Afficher le mot de passe" : "Masquer le mot de passe");
      togglePwd.setAttribute("title", visible ? "Afficher le mot de passe" : "Masquer le mot de passe");
    }});
  }}

  function showError() {{
    if (err) err.classList.add("cf-visible");
    if (input) {{
      input.focus();
      input.select();
    }}
  }}

  function clearDemoLocalStorage() {{
    try {{
      var toRemove = [];
      for (var i = 0; i < localStorage.length; i++) {{
        var key = localStorage.key(i);
        if (key && (key.indexOf("cf_tasks_") === 0 || key.indexOf("cf_") === 0)) {{
          toRemove.push(key);
        }}
      }}
      toRemove.forEach(function (key) {{ localStorage.removeItem(key); }});
    }} catch (e) {{}}
  }}

  function lock() {{
    clearDemoLocalStorage();
    if (demo) {{
      demo.classList.remove("cf-unlocked");
      demo.setAttribute("aria-hidden", "true");
    }}
    if (login) login.style.display = "";
    if (err) err.classList.remove("cf-visible");
    if (input) {{
      input.value = "";
      input.type = "password";
      if (togglePwd) togglePwd.classList.remove("cf-visible");
      input.focus();
    }}
  }}

  function unlock() {{
    if (login) login.style.display = "none";
    if (demo) {{
      demo.classList.add("cf-unlocked");
      demo.removeAttribute("aria-hidden");
    }}
    if (err) err.classList.remove("cf-visible");
  }}

  function isCyberforgeInternalPreview() {{
    try {{
      var q = (window.location && window.location.search) || "";
      return q.indexOf("preview=cyberforge_internal") >= 0;
    }} catch (e) {{
      return false;
    }}
  }}

  if (isCyberforgeInternalPreview()) {{
    unlock();
    return;
  }}

  if (lockBtn) lockBtn.addEventListener("click", lock);

  if (form) {{
    form.addEventListener("submit", function (e) {{
      e.preventDefault();
      var value = (input && input.value ? input.value : "").trim();
      if (value === EXPECTED) {{
        unlock();
      }} else {{
        showError();
      }}
    }});
  }}
}})();
  </script>
</body>
</html>"""
    _log_html_structure("wrap_with_password_gate:output", out)
    return out


def build_standalone_demo_html(
    sources: str,
    *,
    title: str = "Démo CyberForge",
    password: str | None = None,
) -> str:
    kind = classify_demo_kind(sources, title)
    if kind == "tasks":
        inner = build_task_manager_standalone_html(
            title=_extract_task_title(sources, title),
            subtitle=_extract_subtitle(sources),
            sources=sources,
        )
    else:
        inner = build_showcase_standalone_html(sources, title=title)
    if password and password.strip():
        wrapped = wrap_with_password_gate(inner, password.strip(), title=title)
        _log_html_structure("build_standalone_demo_html:wrapped", wrapped)
        return wrapped
    _log_html_structure("build_standalone_demo_html:plain", inner)
    return inner
