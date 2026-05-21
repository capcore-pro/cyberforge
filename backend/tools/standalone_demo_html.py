"""
Démos client — pages HTML autonomes avec JavaScript vanilla (sans conversion JSX).
"""

from __future__ import annotations

import re

from tools.demo_preview_html import (
    PreviewMockup,
    build_mockup_preview_html,
    escape_attr,
    escape_html,
    extract_preview_mockup,
)

# Mots-clés / motifs pour détecter une app de gestion de tâches
_TASK_HINTS = re.compile(
    r"(tâche|taches|todo|todos|task|tasks|checklist|to-do|gestionnaire\s+de\s+tâches|"
    r"liste\s+de\s+tâches|ajouter.*tâche|supprimer.*tâche|cocher)",
    re.I,
)
_TASK_CODE_HINTS = re.compile(
    r"(useState\s*\(\s*\[\s*\]|addTask|removeTask|toggleTask|setTasks|"
    r"tasks\.map|task\.completed|type=[\"']checkbox[\"'])",
    re.I,
)


def classify_demo_kind(sources: str, title: str = "") -> str:
    """
    Retourne « tasks » pour une app todo, sinon « showcase » (maquette extraite du texte).
    """
    blob = f"{title}\n{sources}"
    if _TASK_HINTS.search(blob) or _TASK_CODE_HINTS.search(sources):
        return "tasks"
    return "showcase"


def _extract_task_title(sources: str, fallback: str) -> str:
    match = re.search(r"<h1[^>]*>([\s\S]*?)</h1>", sources, re.I)
    if match:
        text = re.sub(r"<[^>]+>", "", match.group(1)).strip()
        if text and len(text) < 80:
            return text
    return fallback


def _extract_subtitle(sources: str, title: str) -> str:
    for pattern in (
        r"<p[^>]*>([^<]{8,120})</p>",
        r"subtitle[\"']?\s*:\s*[\"']([^\"']+)[\"']",
    ):
        match = re.search(pattern, sources, re.I)
        if match:
            return match.group(1).strip()
    return "Organisez et suivez vos tâches au quotidien."


def build_task_manager_standalone_html(
    *,
    title: str = "Gestion des tâches",
    subtitle: str | None = None,
) -> str:
    """
    HTML complet : ajouter, cocher et supprimer des tâches (vanilla JS, aucun React).
    """
    page_title = escape_html(title.strip() or "Gestion des tâches")
    page_subtitle = escape_html(
        (subtitle or "Organisez et suivez vos tâches au quotidien.").strip()
    )
    storage_slug = re.sub(r"[^a-zA-Z0-9_-]+", "_", (title or "demo").strip())[:36] or "demo"

    return f"""<!DOCTYPE html>
<html lang="fr">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>{page_title}</title>
  <style>
    *,*::before,*::after{{box-sizing:border-box;margin:0;padding:0}}
    body{{
      font-family:system-ui,-apple-system,"Segoe UI",sans-serif;
      background:#0a0a0f;
      color:#e2e8f0;
      min-height:100vh;
      line-height:1.5;
    }}
    .app{{
      max-width:36rem;
      margin:0 auto;
      padding:2rem 1.5rem 3rem;
      min-height:100vh;
    }}
    .app-header{{margin-bottom:1.5rem}}
    .app-header h1{{
      font-size:1.75rem;
      font-weight:800;
      color:#22d3ee;
      text-shadow:0 0 20px rgba(34,211,238,.35);
      margin-bottom:.35rem;
    }}
    .app-header p{{color:#94a3b8;font-size:.9rem}}
    .composer{{
      display:flex;
      gap:.5rem;
      margin-bottom:1.25rem;
    }}
    .composer input{{
      flex:1;
      padding:.65rem .85rem;
      border-radius:.5rem;
      border:1px solid rgba(148,163,184,.25);
      background:rgba(15,23,42,.85);
      color:#f1f5f9;
      font-size:.95rem;
    }}
    .composer input:focus{{
      outline:none;
      border-color:#22d3ee;
      box-shadow:0 0 0 2px rgba(34,211,238,.2);
    }}
    .btn{{
      padding:.65rem 1rem;
      border-radius:.5rem;
      border:none;
      font-weight:700;
      font-size:.85rem;
      cursor:pointer;
      transition:opacity .15s,transform .1s;
    }}
    .btn:active{{transform:scale(.98)}}
    .btn-primary{{
      background:linear-gradient(90deg,#7c3aed,#06b6d4);
      color:#0a0a0f;
    }}
    .btn-ghost{{
      background:rgba(148,163,184,.12);
      color:#e2e8f0;
      border:1px solid rgba(148,163,184,.2);
    }}
    .btn-danger{{
      background:rgba(248,113,113,.12);
      color:#fca5a5;
      border:1px solid rgba(248,113,113,.3);
      padding:.4rem .7rem;
      font-size:.8rem;
    }}
    .btn-danger:hover{{background:rgba(248,113,113,.22)}}
    .stats{{
      display:flex;
      gap:1rem;
      font-size:.75rem;
      color:#64748b;
      margin-bottom:.75rem;
    }}
    .stats strong{{color:#94a3b8}}
    .task-list{{
      list-style:none;
      display:flex;
      flex-direction:column;
      gap:.5rem;
    }}
    .task-item{{
      display:flex;
      align-items:center;
      gap:.65rem;
      padding:.75rem .85rem;
      border-radius:.6rem;
      background:rgba(15,23,42,.75);
      border:1px solid rgba(148,163,184,.15);
      animation:fadeIn .2s ease;
    }}
    @keyframes fadeIn{{
      from{{opacity:0;transform:translateY(-4px)}}
      to{{opacity:1;transform:none}}
    }}
    .task-item.done{{
      opacity:.65;
      border-color:rgba(34,211,238,.15);
    }}
    .task-item.done .task-label{{
      text-decoration:line-through;
      color:#64748b;
    }}
    .task-check{{
      width:1.15rem;
      height:1.15rem;
      accent-color:#06b6d4;
      cursor:pointer;
      flex-shrink:0;
    }}
    .task-label{{
      flex:1;
      font-size:.95rem;
      word-break:break-word;
    }}
    .empty-row{{
      text-align:center;
      padding:2rem 1rem;
      color:#64748b;
      font-size:.9rem;
      border:1px dashed rgba(148,163,184,.2);
      border-radius:.6rem;
      list-style:none;
    }}
    .filters{{
      display:flex;
      gap:.5rem;
      margin-bottom:1rem;
      flex-wrap:wrap;
    }}
    .filter-btn.active{{
      border-color:#22d3ee;
      color:#22d3ee;
      background:rgba(34,211,238,.1);
    }}
  </style>
</head>
<body>
  <div class="app" id="task-app">
    <header class="app-header">
      <h1>{page_title}</h1>
      <p>{page_subtitle}</p>
    </header>
    <form id="task-form" class="composer" autocomplete="off">
      <input id="task-input" type="text" placeholder="Nouvelle tâche…" maxlength="200" />
      <button type="button" id="task-add-btn" class="btn btn-primary">Ajouter</button>
    </form>
    <div class="filters">
      <button type="button" class="btn btn-ghost filter-btn active" data-filter="all">Toutes</button>
      <button type="button" class="btn btn-ghost filter-btn" data-filter="active">Actives</button>
      <button type="button" class="btn btn-ghost filter-btn" data-filter="done">Terminées</button>
    </div>
    <p class="stats" id="task-stats"></p>
    <ul class="task-list" id="task-list"></ul>
  </div>
  <script>
(function () {{
  var STORAGE_KEY = "cf_demo_tasks_{storage_slug}";
  var tasks = [];
  var filter = "all";

  var form = document.getElementById("task-form");
  var input = document.getElementById("task-input");
  var addBtn = document.getElementById("task-add-btn");
  var listEl = document.getElementById("task-list");
  var statsEl = document.getElementById("task-stats");

  function uid() {{
    return "t-" + Date.now().toString(36) + "-" + Math.random().toString(36).slice(2, 7);
  }}

  function normalizeTasks(raw) {{
    if (!Array.isArray(raw)) return [];
    return raw
      .filter(function (t) {{ return t && typeof t.text === "string" && t.text.trim(); }})
      .map(function (t) {{
        return {{
          id: typeof t.id === "string" ? t.id : uid(),
          text: String(t.text).trim(),
          done: Boolean(t.done),
        }};
      }});
  }}

  function load() {{
    try {{
      var raw = localStorage.getItem(STORAGE_KEY);
      if (raw) tasks = normalizeTasks(JSON.parse(raw));
    }} catch (e) {{}}
  }}

  function setFilterAll() {{
    filter = "all";
    document.querySelectorAll(".filter-btn").forEach(function (btn) {{
      btn.classList.toggle("active", btn.getAttribute("data-filter") === "all");
    }});
  }}

  function save() {{
    try {{ localStorage.setItem(STORAGE_KEY, JSON.stringify(tasks)); }} catch (e) {{}}
  }}

  function visibleTasks() {{
    if (filter === "active") return tasks.filter(function (t) {{ return !t.done; }});
    if (filter === "done") return tasks.filter(function (t) {{ return t.done; }});
    return tasks;
  }}

  function updateStats() {{
    var total = tasks.length;
    var done = tasks.filter(function (t) {{ return t.done; }}).length;
    statsEl.innerHTML = "<strong>" + (total - done) + "</strong> active(s) · <strong>" +
      done + "</strong> terminée(s) · <strong>" + total + "</strong> au total";
  }}

  function buildTaskRow(task) {{
    var li = document.createElement("li");
    li.classList.add("task-item");
    if (task.done) li.classList.add("done");
    li.dataset.id = task.id;

    var check = document.createElement("input");
    check.type = "checkbox";
    check.classList.add("task-check");
    check.checked = task.done;
    check.setAttribute("aria-label", "Marquer terminée");
    check.addEventListener("change", function () {{
      task.done = check.checked;
      save();
      render();
    }});

    var label = document.createElement("span");
    label.classList.add("task-label");
    label.textContent = task.text;

    var del = document.createElement("button");
    del.type = "button";
    del.classList.add("btn", "btn-danger");
    del.textContent = "Supprimer";
    del.setAttribute("aria-label", "Supprimer la tâche");
    del.addEventListener("click", function () {{
      tasks = tasks.filter(function (t) {{ return t.id !== task.id; }});
      save();
      render();
    }});

    li.appendChild(check);
    li.appendChild(label);
    li.appendChild(del);
    return li;
  }}

  function render() {{
    if (!listEl) return;
    var items = visibleTasks();
    var fragment = document.createDocumentFragment();

    if (!items.length) {{
      var emptyRow = document.createElement("li");
      emptyRow.classList.add("empty-row");
      emptyRow.textContent = "Aucune tâche — ajoutez-en une ci-dessus.";
      fragment.appendChild(emptyRow);
    }} else {{
      items.forEach(function (task) {{
        fragment.appendChild(buildTaskRow(task));
      }});
    }}

    listEl.replaceChildren(fragment);
    if (statsEl) updateStats();
  }}

  function addTask() {{
    var text = (input.value || "").trim();
    if (text.length < 1) return;
    tasks.unshift({{ id: uid(), text: text, done: false }});
    input.value = "";
    setFilterAll();
    save();
    render();
    input.focus();
  }}

  if (form) {{
    form.addEventListener("submit", function (e) {{
      e.preventDefault();
      addTask();
    }});
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

  document.querySelectorAll(".filter-btn").forEach(function (btn) {{
    btn.addEventListener("click", function () {{
      filter = btn.getAttribute("data-filter") || "all";
      document.querySelectorAll(".filter-btn").forEach(function (b) {{
        b.classList.toggle("active", b === btn);
      }});
      render();
    }});
  }});

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
    """Maquette HTML lisible extraite du texte source (pas de JSX converti)."""
    mockup = extract_preview_mockup(sources, default_title=title)
    return build_mockup_preview_html(mockup)


def build_standalone_demo_html(
    sources: str,
    *,
    title: str = "Démo CyberForge",
) -> str:
    """
    Point d'entrée : HTML autonome selon le type d'app détecté.
    """
    kind = classify_demo_kind(sources, title)
    if kind == "tasks":
        return build_task_manager_standalone_html(
            title=_extract_task_title(sources, title),
            subtitle=_extract_subtitle(sources, title),
        )
    return build_showcase_standalone_html(sources, title=title)
