"""
Démos client — conversion React (useState todo) → HTML autonome + JavaScript vanilla.
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
from tools.tailwind_inline import inline_style, pick_class

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


def _default_theme() -> dict[str, str]:
    return {
        "page": "min-height:100vh;background:#020617;color:#e2e8f0;font-family:system-ui,-apple-system,'Segoe UI',sans-serif;line-height:1.5",
        "shell": "max-width:36rem;margin:0 auto;padding:2rem 1.5rem 3rem",
        "heading": "font-size:1.75rem;font-weight:800;color:#22d3ee;margin-bottom:0.35rem",
        "subtitle": "color:#94a3b8;font-size:0.9rem;margin-bottom:1.5rem",
        "composer": "display:flex;gap:0.5rem;margin-bottom:1.25rem",
        "input": "flex:1;padding:0.65rem 0.85rem;border-radius:0.5rem;border:1px solid rgba(148,163,184,0.25);background:#0f172a;color:#f1f5f9;font-size:0.95rem",
        "add_btn": "padding:0.65rem 1rem;border-radius:0.5rem;border:none;font-weight:700;font-size:0.85rem;cursor:pointer;background:linear-gradient(90deg,#7c3aed,#06b6d4);color:#0a0a0f",
        "list": "list-style:none;display:flex;flex-direction:column;gap:0.5rem",
        "row": "display:flex;align-items:center;gap:0.65rem;padding:0.75rem 0.85rem;border-radius:0.6rem;background:rgba(15,23,42,0.75);border:1px solid rgba(148,163,184,0.15)",
        "label": "flex:1;font-size:0.95rem;word-break:break-word",
        "label_done": "text-decoration:line-through;color:#64748b;opacity:0.65",
        "delete_btn": "padding:0.4rem 0.7rem;border-radius:0.5rem;border:1px solid rgba(248,113,113,0.35);background:rgba(248,113,113,0.12);color:#fca5a5;font-size:0.8rem;cursor:pointer",
        "checkbox": "width:1.15rem;height:1.15rem;accent-color:#06b6d4;cursor:pointer;flex-shrink:0",
        "empty": "text-align:center;padding:2rem 1rem;color:#64748b;font-size:0.9rem;border:1px dashed rgba(148,163,184,0.2);border-radius:0.6rem",
    }


def _theme_from_react_source(sources: str) -> dict[str, str]:
    theme = _default_theme()
    page_cls = pick_class(sources, "min-h-screen", "bg-slate-950", "bg-gray-900")
    shell_cls = pick_class(sources, "max-w-", "mx-auto", "p-8", "px-4")
    heading_cls = pick_class(sources, "text-2xl", "text-3xl", "font-bold", "text-cyan")
    input_cls = pick_class(sources, "rounded", "border", "px-", "py-", fallback="")
    row_cls = pick_class(sources, "rounded", "flex", "items-center", "gap-", "p-4", "border")
    delete_cls = pick_class(sources, "text-red", "rose", "bg-red", "border-red")
    done_label_cls = pick_class(sources, "line-through", "opacity-")

    if page_cls:
        extra = inline_style(sources, "min-h-screen", "bg-slate-950")
        if extra:
            theme["page"] = f"{extra};{theme['page']}"
    if shell_cls:
        extra = inline_style(sources, "max-w-", "mx-auto")
        if extra:
            theme["shell"] = extra
    if heading_cls:
        extra = inline_style(sources, "text-2xl", "text-3xl", "font-bold")
        if extra:
            theme["heading"] = extra
    if input_cls:
        extra = inline_style(sources, "rounded", "border", "px-3", "py-2", "w-full")
        if extra:
            theme["input"] = f"flex:1;{extra}"
    if row_cls:
        extra = inline_style(sources, "rounded", "flex", "items-center", "gap-2", "border")
        if extra:
            theme["row"] = extra
    if delete_cls:
        extra = inline_style(sources, "text-red", "rose", "rounded")
        if extra:
            theme["delete_btn"] = f"{extra};cursor:pointer"
    if done_label_cls:
        extra = inline_style(sources, "line-through", "opacity-")
        if extra:
            theme["label_done"] = f"{theme['label']};{extra}"

    return theme


def build_task_manager_standalone_html(
    *,
    title: str = "Gestion des tâches",
    subtitle: str | None = None,
    sources: str = "",
) -> str:
    """
    HTML + JS vanilla reproduisant une app React todo (useState, addTask, toggle, delete).
    Styles extraits des className Tailwind du source React.
    """
    page_title = escape_html(title.strip() or "Gestion des tâches")
    page_subtitle = escape_html(
        (subtitle or _extract_subtitle(sources) or "Organisez et suivez vos tâches au quotidien.").strip()
    )
    placeholder = escape_attr(_extract_input_placeholder(sources))
    add_label = escape_html(_extract_add_button_label(sources))
    done_field = _detect_done_field(sources)
    storage_slug = re.sub(r"[^a-zA-Z0-9_-]+", "_", (title or "demo").strip())[:36] or "demo"
    theme = _theme_from_react_source(sources) if sources.strip() else _default_theme()

    return f"""<!DOCTYPE html>
<html lang="fr">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>{page_title}</title>
  <!-- {TASK_PREVIEW_MARKER} -->
</head>
<body style="{theme["page"]}">
  <main class="todo-app" id="task-app" style="{theme["shell"]}">
    <header>
      <h1 style="{theme["heading"]}">{page_title}</h1>
      <p style="{theme["subtitle"]}">{page_subtitle}</p>
    </header>
    <div style="{theme["composer"]}">
      <input
        id="task-input"
        type="text"
        style="{theme["input"]}"
        placeholder="{placeholder}"
        maxlength="200"
        autocomplete="off"
      />
      <button type="button" id="task-add-btn" style="{theme["add_btn"]}">{add_label}</button>
    </div>
    <ul id="task-list" style="{theme["list"]}"></ul>
  </main>
  <script>
(function () {{
  var MARKER = "{TASK_PREVIEW_MARKER}";
  var STORAGE_KEY = "cf_demo_tasks_{storage_slug}";
  var DONE_KEY = "{done_field}";
  var tasks = [];

  var input = document.getElementById("task-input");
  var addBtn = document.getElementById("task-add-btn");
  var listEl = document.getElementById("task-list");

  var THEME = {{
    row: "{escape_attr(theme["row"])}",
    label: "{escape_attr(theme["label"])}",
    labelDone: "{escape_attr(theme["label_done"])}",
    deleteBtn: "{escape_attr(theme["delete_btn"])}",
    checkbox: "{escape_attr(theme["checkbox"])}",
    empty: "{escape_attr(theme["empty"])}"
  }};

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
    li.style.cssText = THEME.row;
    if (task[DONE_KEY]) li.style.opacity = "0.85";
    li.dataset.id = task.id;

    var check = document.createElement("input");
    check.type = "checkbox";
    check.style.cssText = THEME.checkbox;
    check.checked = !!task[DONE_KEY];
    check.setAttribute("aria-label", "Marquer terminée");
    check.addEventListener("change", function () {{
      toggleTask(task.id);
    }});

    var label = document.createElement("span");
    label.style.cssText = task[DONE_KEY] ? THEME.labelDone : THEME.label;
    label.textContent = task.text;

    var del = document.createElement("button");
    del.type = "button";
    del.style.cssText = THEME.deleteBtn;
    del.textContent = "Supprimer";
    del.setAttribute("aria-label", "Supprimer la tâche");
    del.addEventListener("click", function () {{
      deleteTask(task.id);
    }});

    li.appendChild(check);
    li.appendChild(label);
    li.appendChild(del);
    return li;
  }}

  function render() {{
    if (!listEl) return;
    var fragment = document.createDocumentFragment();
    if (!tasks.length) {{
      var empty = document.createElement("li");
      empty.style.cssText = THEME.empty;
      empty.textContent = "Aucune tâche — ajoutez-en une ci-dessus.";
      fragment.appendChild(empty);
    }} else {{
      tasks.forEach(function (task) {{
        fragment.appendChild(buildTaskRow(task));
      }});
    }}
    listEl.replaceChildren(fragment);
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


def build_standalone_demo_html(
    sources: str,
    *,
    title: str = "Démo CyberForge",
) -> str:
    kind = classify_demo_kind(sources, title)
    if kind == "tasks":
        return build_task_manager_standalone_html(
            title=_extract_task_title(sources, title),
            subtitle=_extract_subtitle(sources),
            sources=sources,
        )
    return build_showcase_standalone_html(sources, title=title)
