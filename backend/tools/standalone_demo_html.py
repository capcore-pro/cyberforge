"""
Démos client — conversion React (useState todo) → HTML autonome + JavaScript vanilla.
"""

from __future__ import annotations

import json
import re

from tools.demo_preview_html import (
    PreviewMockup,
    build_mockup_preview_html,
    escape_attr,
    escape_html,
    extract_preview_mockup,
)
# Marqueur de version — les démos sans ce tag sont régénérées à l'unlock
TASK_PREVIEW_MARKER = "cf-preview:v2-react-todo"

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
    return TASK_PREVIEW_MARKER in html and "function addTask" in html


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
    App todo autonome — UI SaaS moderne (HTML/CSS/JS vanilla, sans dépendance externe).
    """
    page_title = escape_html(title.strip() or "Gestion des tâches")
    page_subtitle = escape_html(
        (subtitle or _extract_subtitle(sources) or "Planifiez, priorisez et terminez vos actions en un seul endroit.").strip()
    )
    placeholder = escape_attr(_extract_input_placeholder(sources))
    add_label = escape_html(_extract_add_button_label(sources))
    done_field = _detect_done_field(sources)
    storage_slug = re.sub(r"[^a-zA-Z0-9_-]+", "_", (title or "demo").strip())[:36] or "demo"

    return f"""<!DOCTYPE html>
<html lang="fr">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>{page_title}</title>
  <!-- {TASK_PREVIEW_MARKER} -->
  <style>
    *, *::before, *::after {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      min-height: 100vh;
      font-family: "Segoe UI", system-ui, -apple-system, sans-serif;
      font-size: 15px;
      line-height: 1.5;
      color: #e8ecf4;
      background:
        radial-gradient(1200px 600px at 10% -10%, rgba(99, 102, 241, 0.22), transparent 55%),
        radial-gradient(900px 500px at 100% 0%, rgba(14, 165, 233, 0.14), transparent 50%),
        #0c0f17;
      -webkit-font-smoothing: antialiased;
    }}
    .app {{
      max-width: 720px;
      margin: 0 auto;
      padding: 1.5rem 1.25rem 3rem;
    }}
    .app-header {{
      display: flex;
      align-items: center;
      gap: 1rem;
      margin-bottom: 1.75rem;
      padding-bottom: 1.25rem;
      border-bottom: 1px solid rgba(255, 255, 255, 0.06);
    }}
    .app-logo {{
      width: 48px;
      height: 48px;
      border-radius: 14px;
      background: linear-gradient(135deg, #6366f1 0%, #22d3ee 100%);
      box-shadow: 0 8px 24px rgba(99, 102, 241, 0.35);
      display: flex;
      align-items: center;
      justify-content: center;
      flex-shrink: 0;
    }}
    .app-logo svg {{ display: block; }}
    .app-brand {{ flex: 1; min-width: 0; }}
    .app-title {{
      margin: 0;
      font-size: 1.35rem;
      font-weight: 700;
      letter-spacing: -0.02em;
      color: #f8fafc;
    }}
    .app-subtitle {{
      margin: 0.2rem 0 0;
      font-size: 0.875rem;
      color: #94a3b8;
    }}
    .app-badge {{
      font-size: 0.7rem;
      font-weight: 600;
      text-transform: uppercase;
      letter-spacing: 0.08em;
      color: #a5b4fc;
      background: rgba(99, 102, 241, 0.15);
      border: 1px solid rgba(129, 140, 248, 0.25);
      padding: 0.35rem 0.65rem;
      border-radius: 999px;
    }}
    .stats {{
      display: grid;
      grid-template-columns: repeat(3, 1fr);
      gap: 0.75rem;
      margin-bottom: 1.25rem;
    }}
    .stat-card {{
      background: rgba(255, 255, 255, 0.03);
      border: 1px solid rgba(255, 255, 255, 0.06);
      border-radius: 12px;
      padding: 0.85rem 1rem;
      box-shadow: 0 4px 16px rgba(0, 0, 0, 0.2);
      transition: border-color 0.2s ease, transform 0.2s ease;
    }}
    .stat-card:hover {{
      border-color: rgba(129, 140, 248, 0.2);
      transform: translateY(-1px);
    }}
    .stat-label {{
      font-size: 0.7rem;
      text-transform: uppercase;
      letter-spacing: 0.06em;
      color: #64748b;
      margin: 0 0 0.25rem;
    }}
    .stat-value {{
      font-size: 1.25rem;
      font-weight: 700;
      color: #f1f5f9;
      margin: 0;
    }}
    .panel {{
      background: rgba(18, 22, 32, 0.85);
      border: 1px solid rgba(255, 255, 255, 0.07);
      border-radius: 16px;
      padding: 1.25rem;
      box-shadow:
        0 1px 0 rgba(255, 255, 255, 0.04) inset,
        0 20px 50px rgba(0, 0, 0, 0.35);
      margin-bottom: 1rem;
    }}
    .composer {{
      display: flex;
      gap: 0.65rem;
      align-items: stretch;
    }}
    .composer-input {{
      flex: 1;
      min-width: 0;
      padding: 0.75rem 1rem;
      font-size: 0.95rem;
      color: #f1f5f9;
      background: rgba(15, 18, 28, 0.9);
      border: 1px solid rgba(148, 163, 184, 0.2);
      border-radius: 10px;
      outline: none;
      transition: border-color 0.2s ease, box-shadow 0.2s ease;
    }}
    .composer-input::placeholder {{ color: #64748b; }}
    .composer-input:focus {{
      border-color: rgba(99, 102, 241, 0.6);
      box-shadow: 0 0 0 3px rgba(99, 102, 241, 0.2);
    }}
    .btn-add {{
      display: inline-flex;
      align-items: center;
      justify-content: center;
      gap: 0.4rem;
      padding: 0 1.15rem;
      font-size: 0.9rem;
      font-weight: 600;
      color: #fff;
      background: linear-gradient(180deg, #6366f1 0%, #4f46e5 100%);
      border: none;
      border-radius: 10px;
      cursor: pointer;
      box-shadow: 0 4px 14px rgba(79, 70, 229, 0.4);
      transition: transform 0.15s ease, box-shadow 0.2s ease, filter 0.2s ease;
      white-space: nowrap;
    }}
    .btn-add:hover {{
      filter: brightness(1.08);
      box-shadow: 0 6px 20px rgba(79, 70, 229, 0.5);
      transform: translateY(-1px);
    }}
    .btn-add:active {{ transform: translateY(0); }}
    .task-list {{
      list-style: none;
      margin: 0;
      padding: 0;
      display: flex;
      flex-direction: column;
      gap: 0.5rem;
    }}
    .task-row {{
      display: flex;
      align-items: center;
      gap: 0.85rem;
      padding: 0.9rem 1rem;
      background: rgba(255, 255, 255, 0.02);
      border: 1px solid rgba(255, 255, 255, 0.06);
      border-radius: 12px;
      box-shadow: 0 2px 8px rgba(0, 0, 0, 0.15);
      transition: background 0.2s ease, border-color 0.2s ease, opacity 0.25s ease;
    }}
    .task-row:hover {{
      background: rgba(255, 255, 255, 0.04);
      border-color: rgba(148, 163, 184, 0.15);
    }}
    .task-row.is-done {{
      opacity: 0.72;
      background: rgba(15, 18, 28, 0.5);
    }}
    .task-check {{
      position: relative;
      flex-shrink: 0;
      width: 22px;
      height: 22px;
      cursor: pointer;
    }}
    .task-check input {{
      position: absolute;
      opacity: 0;
      width: 0;
      height: 0;
    }}
    .task-check-box {{
      display: block;
      width: 22px;
      height: 22px;
      border-radius: 7px;
      border: 2px solid rgba(148, 163, 184, 0.45);
      background: rgba(15, 18, 28, 0.8);
      transition: border-color 0.2s ease, background 0.2s ease, box-shadow 0.2s ease;
    }}
    .task-check input:focus-visible + .task-check-box {{
      box-shadow: 0 0 0 3px rgba(99, 102, 241, 0.35);
    }}
    .task-check input:checked + .task-check-box {{
      border-color: #22d3ee;
      background: linear-gradient(135deg, #6366f1, #22d3ee);
      box-shadow: 0 2px 8px rgba(34, 211, 238, 0.35);
    }}
    .task-check input:checked + .task-check-box::after {{
      content: "";
      position: absolute;
      left: 7px;
      top: 4px;
      width: 5px;
      height: 10px;
      border: solid #0c0f17;
      border-width: 0 2px 2px 0;
      transform: rotate(45deg);
    }}
    .task-label {{
      flex: 1;
      min-width: 0;
      font-size: 0.95rem;
      color: #e2e8f0;
      word-break: break-word;
      transition: color 0.2s ease, text-decoration 0.2s ease;
    }}
    .task-row.is-done .task-label {{
      color: #64748b;
      text-decoration: line-through;
      text-decoration-color: rgba(100, 116, 139, 0.6);
    }}
    .btn-delete {{
      flex-shrink: 0;
      padding: 0.4rem 0.75rem;
      font-size: 0.8rem;
      font-weight: 500;
      color: #fca5a5;
      background: transparent;
      border: 1px solid rgba(248, 113, 113, 0.25);
      border-radius: 8px;
      cursor: pointer;
      opacity: 0.85;
      transition: opacity 0.2s ease, background 0.2s ease, border-color 0.2s ease;
    }}
    .btn-delete:hover {{
      opacity: 1;
      background: rgba(239, 68, 68, 0.12);
      border-color: rgba(248, 113, 113, 0.45);
    }}
    .task-empty {{
      text-align: center;
      padding: 2.5rem 1.5rem;
      color: #64748b;
      font-size: 0.9rem;
      border: 1px dashed rgba(148, 163, 184, 0.2);
      border-radius: 12px;
      background: rgba(255, 255, 255, 0.02);
    }}
    .task-empty strong {{ color: #94a3b8; display: block; margin-bottom: 0.35rem; }}
  </style>
</head>
<body>
  <div class="app" id="task-app">
    <header class="app-header">
      <div class="app-logo" aria-hidden="true">
        <svg width="26" height="26" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
          <path d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2" stroke="#0c0f17" stroke-width="1.75" stroke-linecap="round"/>
          <rect x="9" y="3" width="6" height="4" rx="1" fill="#0c0f17"/>
          <path d="M9 12l2 2 4-4" stroke="#0c0f17" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round"/>
        </svg>
      </div>
      <div class="app-brand">
        <h1 class="app-title">{page_title}</h1>
        <p class="app-subtitle">{page_subtitle}</p>
      </div>
      <span class="app-badge">SaaS</span>
    </header>

    <div class="stats" aria-label="Statistiques">
      <div class="stat-card">
        <p class="stat-label">Total</p>
        <p class="stat-value" id="stat-total">0</p>
      </div>
      <div class="stat-card">
        <p class="stat-label">En cours</p>
        <p class="stat-value" id="stat-active">0</p>
      </div>
      <div class="stat-card">
        <p class="stat-label">Terminées</p>
        <p class="stat-value" id="stat-done">0</p>
      </div>
    </div>

    <section class="panel" aria-label="Nouvelle tâche">
      <div class="composer">
        <input
          id="task-input"
          class="composer-input"
          type="text"
          placeholder="{placeholder}"
          maxlength="200"
          autocomplete="off"
        />
        <button type="button" id="task-add-btn" class="btn-add">
          <span aria-hidden="true">+</span> {add_label}
        </button>
      </div>
    </section>

    <section class="panel" aria-label="Liste des tâches">
      <ul id="task-list" class="task-list"></ul>
    </section>
  </div>
  <script>
(function () {{
  var MARKER = "{TASK_PREVIEW_MARKER}";
  var STORAGE_KEY = "cf_demo_tasks_{storage_slug}";
  var DONE_KEY = "{done_field}";
  var tasks = [];

  var input = document.getElementById("task-input");
  var addBtn = document.getElementById("task-add-btn");
  var listEl = document.getElementById("task-list");
  var statTotal = document.getElementById("stat-total");
  var statActive = document.getElementById("stat-active");
  var statDone = document.getElementById("stat-done");

  function uid() {{
    return "t-" + Date.now().toString(36) + "-" + Math.random().toString(36).slice(2, 7);
  }}

  function normalizeTasks(raw) {{
    if (!Array.isArray(raw)) return [];
    return raw
      .filter(function (t) {{ return t && typeof t.text === "string" && t.text.trim(); }})
      .map(function (t) {{
        var item = {{
          id: typeof t.id === "string" || typeof t.id === "number" ? String(t.id) : uid(),
          text: String(t.text).trim(),
        }};
        item[DONE_KEY] = Boolean(t[DONE_KEY] || t.done || t.completed);
        return item;
      }});
  }}

  function load() {{
    try {{
      var raw = localStorage.getItem(STORAGE_KEY);
      if (raw) tasks = normalizeTasks(JSON.parse(raw));
    }} catch (e) {{}}
  }}

  function save() {{
    try {{ localStorage.setItem(STORAGE_KEY, JSON.stringify(tasks)); }} catch (e) {{}}
  }}

  function updateStats() {{
    var done = tasks.filter(function (t) {{ return t[DONE_KEY]; }}).length;
    var total = tasks.length;
    if (statTotal) statTotal.textContent = String(total);
    if (statActive) statActive.textContent = String(total - done);
    if (statDone) statDone.textContent = String(done);
  }}

  function toggleTask(id) {{
    tasks = tasks.map(function (t) {{
      if (t.id !== id) return t;
      var next = {{ id: t.id, text: t.text }};
      next[DONE_KEY] = !t[DONE_KEY];
      return next;
    }});
    save();
    render();
  }}

  function deleteTask(id) {{
    tasks = tasks.filter(function (t) {{ return t.id !== id; }});
    save();
    render();
  }}

  function buildTaskRow(task) {{
    var li = document.createElement("li");
    li.setAttribute("class", "task-row" + (task[DONE_KEY] ? " is-done" : ""));
    li.dataset.id = task.id;

    var checkLabel = document.createElement("label");
    checkLabel.setAttribute("class", "task-check");
    var check = document.createElement("input");
    check.type = "checkbox";
    check.checked = !!task[DONE_KEY];
    check.setAttribute("aria-label", "Marquer terminée");
    check.addEventListener("change", function () {{ toggleTask(task.id); }});
    var checkBox = document.createElement("span");
    checkBox.setAttribute("class", "task-check-box");
    checkLabel.appendChild(check);
    checkLabel.appendChild(checkBox);

    var label = document.createElement("span");
    label.setAttribute("class", "task-label");
    label.textContent = task.text;

    var del = document.createElement("button");
    del.type = "button";
    del.setAttribute("class", "btn-delete");
    del.textContent = "Supprimer";
    del.setAttribute("aria-label", "Supprimer la tâche");
    del.addEventListener("click", function () {{ deleteTask(task.id); }});

    li.appendChild(checkLabel);
    li.appendChild(label);
    li.appendChild(del);
    return li;
  }}

  function render() {{
    if (!listEl) return;
    var fragment = document.createDocumentFragment();
    if (!tasks.length) {{
      var empty = document.createElement("li");
      empty.setAttribute("class", "task-empty");
      empty.innerHTML = "<strong>Aucune tâche pour le moment</strong>Ajoutez votre première action ci-dessus.";
      fragment.appendChild(empty);
    }} else {{
      tasks.forEach(function (task) {{
        fragment.appendChild(buildTaskRow(task));
      }});
    }}
    listEl.replaceChildren(fragment);
    updateStats();
  }}

  function addTask() {{
    var text = (input && input.value ? input.value : "").trim();
    if (!text.length) return;
    var item = {{ id: uid(), text: text }};
    item[DONE_KEY] = false;
    tasks.unshift(item);
    if (input) input.value = "";
    save();
    render();
    if (input) input.focus();
  }}

  if (addBtn) addBtn.addEventListener("click", addTask);
  if (input) {{
    input.addEventListener("keydown", function (e) {{
      if (e.key === "Enter") {{
        e.preventDefault();
        addTask();
      }}
    }});
  }}

  load();
  render();
}})();
  </script>
</body>
</html>"""


def build_showcase_standalone_html(
    sources: str,
    *,
    title: str = "Démo CyberForge",
) -> str:
    mockup = extract_preview_mockup(sources, default_title=title)
    return build_mockup_preview_html(mockup)


def _extract_body_inner_html(html: str) -> str:
    """Contenu intérieur de <body> pour intégration inline (scripts inclus)."""
    match = re.search(r"<body[^>]*>([\s\S]*)</body>", html, re.I)
    if match:
        return match.group(1).strip()
    return html.strip()


def wrap_with_password_gate(demo_html: str, password: str, *, title: str = "Démo CyberForge") -> str:
    """
    Enveloppe le livrable dans un écran de login cyber (validation JS côté client).
    La démo reste inline (display:none jusqu'à mot de passe correct).
    """
    secret = json.dumps(password, ensure_ascii=False)
    page_title = escape_html(title.strip() or "Démo CyberForge")
    demo_inner = _extract_body_inner_html(demo_html)

    return f"""<!DOCTYPE html>
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
    .cf-login-input {{
      width: 100%;
      padding: 0.7rem 0.9rem;
      border-radius: 0.5rem;
      border: 1px solid rgba(148, 163, 184, 0.3);
      background: #0f172a;
      color: #f1f5f9;
      font-size: 0.95rem;
      margin-bottom: 0.75rem;
    }}
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
    #cf-demo-content {{ display: none; min-height: 100vh; }}
    #cf-demo-content.cf-unlocked {{ display: block; }}
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
        <input
          id="cf-password-input"
          class="cf-login-input"
          type="password"
          placeholder="ex. soleil-bateau-rouge"
          required
          autofocus
        />
        <button type="submit" class="cf-login-btn">Accéder à la démo</button>
      </form>
      <p id="cf-login-error" class="cf-login-error" role="alert">Mot de passe incorrect.</p>
    </div>
  </div>
  <div id="cf-demo-content" aria-hidden="true">
{demo_inner}
  </div>
  <script>
(function () {{
  var EXPECTED = {secret};
  var form = document.getElementById("cf-login-form");
  var input = document.getElementById("cf-password-input");
  var err = document.getElementById("cf-login-error");
  var login = document.getElementById("cf-login-screen");
  var demo = document.getElementById("cf-demo-content");

  function showError() {{
    if (err) err.classList.add("cf-visible");
    if (input) {{
      input.focus();
      input.select();
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
        return wrap_with_password_gate(inner, password.strip(), title=title)
    return inner
