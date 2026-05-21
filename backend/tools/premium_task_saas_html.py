"""
Template HTML premium — app SaaS fictive (sidebar, header utilisateur, tâches seed).
"""

from __future__ import annotations

from tools.demo_preview_html import escape_attr, escape_html
from tools.standalone_demo_html import (
    TASK_PREVIEW_MARKER,
    _detect_done_field,
    _extract_add_button_label,
    _extract_input_placeholder,
    _extract_subtitle,
)

PREMIUM_PREVIEW_MARKER = "cf-preview:v3-premium-saas"


def build_premium_task_manager_html(
    *,
    title: str = "Gestion des tâches",
    subtitle: str | None = None,
    sources: str = "",
) -> str:
    page_title = escape_html(title.strip() or "Gestion des tâches")
    page_subtitle = escape_html(
        (
            subtitle
            or _extract_subtitle(sources)
            or "Planifiez, priorisez et terminez vos actions en un seul endroit."
        ).strip()
    )
    placeholder = escape_attr(_extract_input_placeholder(sources))
    add_label = escape_html(_extract_add_button_label(sources))
    done_field = _detect_done_field(sources)
    storage_slug = __import__("re").sub(r"[^a-zA-Z0-9_-]+", "_", (title or "demo").strip())[:36] or "demo"

    return f"""<!DOCTYPE html>
<html lang="fr">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>{page_title}</title>
  <!-- {TASK_PREVIEW_MARKER} {PREMIUM_PREVIEW_MARKER} -->
  <style>
    *, *::before, *::after {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      min-height: 100vh;
      font-family: "Segoe UI", system-ui, -apple-system, sans-serif;
      font-size: 14px;
      line-height: 1.5;
      color: #e2e8f0;
      background: #0b0f1a;
      -webkit-font-smoothing: antialiased;
    }}
    .saas-shell {{ display: flex; min-height: 100vh; }}
    .saas-sidebar {{
      width: 248px;
      flex-shrink: 0;
      background: linear-gradient(180deg, #111827 0%, #0f172a 100%);
      border-right: 1px solid rgba(255,255,255,0.06);
      display: flex;
      flex-direction: column;
      padding: 1.25rem 0;
    }}
    .saas-brand {{
      display: flex;
      align-items: center;
      gap: 0.75rem;
      padding: 0 1.25rem 1.5rem;
      border-bottom: 1px solid rgba(255,255,255,0.06);
      margin-bottom: 1rem;
    }}
    .saas-logo {{
      width: 40px; height: 40px; border-radius: 12px;
      background: linear-gradient(135deg, #6366f1, #22d3ee);
      display: flex; align-items: center; justify-content: center;
      box-shadow: 0 6px 20px rgba(99,102,241,0.35);
    }}
    .saas-brand-name {{ font-weight: 700; font-size: 1rem; color: #f8fafc; letter-spacing: -0.02em; }}
    .saas-brand-tag {{ font-size: 0.7rem; color: #64748b; margin-top: 0.1rem; }}
    .saas-nav {{ flex: 1; padding: 0 0.75rem; }}
    .saas-nav-item {{
      display: flex; align-items: center; gap: 0.65rem;
      padding: 0.6rem 0.85rem; border-radius: 10px;
      color: #94a3b8; font-size: 0.875rem; font-weight: 500;
      margin-bottom: 0.2rem; cursor: default;
    }}
    .saas-nav-item.active {{
      background: rgba(99,102,241,0.18);
      color: #e0e7ff;
      border: 1px solid rgba(129,140,248,0.25);
    }}
    .saas-nav-dot {{
      width: 8px; height: 8px; border-radius: 50%;
      background: #6366f1; opacity: 0; flex-shrink: 0;
    }}
    .saas-nav-item.active .saas-nav-dot {{ opacity: 1; }}
    .saas-sidebar-foot {{
      padding: 1rem 1.25rem 0;
      border-top: 1px solid rgba(255,255,255,0.06);
      font-size: 0.75rem; color: #64748b;
    }}
    .saas-main {{ flex: 1; display: flex; flex-direction: column; min-width: 0; }}
    .saas-topbar {{
      height: 60px;
      display: flex; align-items: center; justify-content: space-between;
      padding: 0 1.75rem;
      background: rgba(15,23,42,0.85);
      border-bottom: 1px solid rgba(255,255,255,0.06);
      backdrop-filter: blur(12px);
    }}
    .saas-topbar-title {{ font-size: 1.05rem; font-weight: 600; color: #f1f5f9; }}
    .saas-topbar-right {{ display: flex; align-items: center; gap: 1rem; }}
    .saas-notif {{
      width: 36px; height: 36px; border-radius: 10px;
      background: rgba(255,255,255,0.04);
      border: 1px solid rgba(255,255,255,0.08);
      display: flex; align-items: center; justify-content: center;
      color: #94a3b8; font-size: 1rem;
    }}
    .saas-user {{
      display: flex; align-items: center; gap: 0.65rem;
      padding: 0.35rem 0.65rem 0.35rem 0.35rem;
      border-radius: 12px;
      background: rgba(255,255,255,0.04);
      border: 1px solid rgba(255,255,255,0.08);
    }}
    .saas-avatar {{
      width: 32px; height: 32px; border-radius: 50%;
      background: linear-gradient(135deg, #8b5cf6, #06b6d4);
      display: flex; align-items: center; justify-content: center;
      font-size: 0.75rem; font-weight: 700; color: #fff;
    }}
    .saas-user-name {{ font-size: 0.8rem; font-weight: 600; color: #f1f5f9; }}
    .saas-user-role {{ font-size: 0.7rem; color: #64748b; }}
    .saas-content {{
      flex: 1; overflow: auto;
      padding: 1.5rem 1.75rem 2.5rem;
      background:
        radial-gradient(900px 400px at 0% 0%, rgba(99,102,241,0.12), transparent 50%),
        #0b0f1a;
    }}
    .page-header {{ margin-bottom: 1.25rem; }}
    .page-title {{ margin: 0; font-size: 1.5rem; font-weight: 700; color: #f8fafc; letter-spacing: -0.02em; }}
    .page-subtitle {{ margin: 0.35rem 0 0; color: #94a3b8; font-size: 0.9rem; }}
    .stats {{
      display: grid; grid-template-columns: repeat(3, 1fr);
      gap: 0.75rem; margin-bottom: 1.25rem;
    }}
    .stat-card {{
      background: rgba(30,41,59,0.6);
      border: 1px solid rgba(255,255,255,0.06);
      border-radius: 14px; padding: 1rem 1.1rem;
    }}
    .stat-label {{ font-size: 0.7rem; text-transform: uppercase; letter-spacing: 0.06em; color: #64748b; }}
    .stat-value {{ font-size: 1.5rem; font-weight: 700; color: #f8fafc; margin-top: 0.25rem; }}
    .panel {{
      background: rgba(15,23,42,0.75);
      border: 1px solid rgba(255,255,255,0.07);
      border-radius: 16px;
      padding: 1.25rem;
      box-shadow: 0 12px 40px rgba(0,0,0,0.25);
    }}
    .composer {{
      display: flex; gap: 0.65rem; margin-bottom: 1.1rem;
    }}
    .composer-input {{
      flex: 1; padding: 0.7rem 1rem;
      border-radius: 12px;
      border: 1px solid rgba(148,163,184,0.25);
      background: rgba(15,23,42,0.9);
      color: #f1f5f9; font-size: 0.9rem;
    }}
    .composer-input:focus {{
      outline: none; border-color: #6366f1;
      box-shadow: 0 0 0 3px rgba(99,102,241,0.2);
    }}
    .btn-add {{
      padding: 0.7rem 1.25rem; border: none; border-radius: 12px;
      background: linear-gradient(135deg, #6366f1, #4f46e5);
      color: #fff; font-weight: 600; font-size: 0.875rem;
      cursor: pointer; white-space: nowrap;
      box-shadow: 0 4px 14px rgba(99,102,241,0.35);
    }}
    .btn-add:hover {{ filter: brightness(1.08); }}
    .task-list {{ list-style: none; margin: 0; padding: 0; }}
    .task-item {{
      display: flex; align-items: center; gap: 0.75rem;
      padding: 0.85rem 1rem;
      border-radius: 12px;
      background: rgba(30,41,59,0.45);
      border: 1px solid rgba(255,255,255,0.05);
      margin-bottom: 0.5rem;
      transition: background 0.15s;
    }}
    .task-item:hover {{ background: rgba(51,65,85,0.5); }}
    .task-check {{
      width: 20px; height: 20px; accent-color: #6366f1; cursor: pointer;
    }}
    .task-text {{ flex: 1; color: #e2e8f0; font-size: 0.9rem; }}
    .task-item.done .task-text {{
      text-decoration: line-through; color: #64748b; opacity: 0.75;
    }}
    .task-delete {{
      background: transparent; border: none;
      color: #f87171; font-size: 0.8rem; cursor: pointer;
      padding: 0.35rem 0.5rem; border-radius: 8px;
    }}
    .task-delete:hover {{ background: rgba(248,113,113,0.12); }}
    .empty-state {{
      text-align: center; padding: 2rem; color: #64748b; font-size: 0.9rem;
    }}
    @media (max-width: 900px) {{
      .saas-sidebar {{ width: 72px; }}
      .saas-brand-name, .saas-brand-tag, .saas-nav span:not(.saas-nav-dot),
      .saas-sidebar-foot {{ display: none; }}
      .saas-user-name, .saas-user-role {{ display: none; }}
    }}
  </style>
</head>
<body>
  <div class="saas-shell">
    <aside class="saas-sidebar" aria-label="Navigation">
      <div class="saas-brand">
        <div class="saas-logo" aria-hidden="true">
          <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="#fff" stroke-width="2"><path d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2"/><rect x="9" y="3" width="6" height="4" rx="1"/></svg>
        </div>
        <div>
          <div class="saas-brand-name">TaskFlow</div>
          <div class="saas-brand-tag">Workspace Pro</div>
        </div>
      </div>
      <nav class="saas-nav">
        <div class="saas-nav-item"><span class="saas-nav-dot"></span> Tableau de bord</div>
        <div class="saas-nav-item active"><span class="saas-nav-dot"></span> Tâches</div>
        <div class="saas-nav-item"><span class="saas-nav-dot"></span> Projets</div>
        <div class="saas-nav-item"><span class="saas-nav-dot"></span> Équipe</div>
        <div class="saas-nav-item"><span class="saas-nav-dot"></span> Paramètres</div>
      </nav>
      <div class="saas-sidebar-foot">Plan Pro · 12 sièges</div>
    </aside>
    <div class="saas-main">
      <header class="saas-topbar">
        <div class="saas-topbar-title">{page_title}</div>
        <div class="saas-topbar-right">
          <div class="saas-notif" title="Notifications">🔔</div>
          <div class="saas-user">
            <div class="saas-avatar">AM</div>
            <div>
              <div class="saas-user-name">Alex Martin</div>
              <div class="saas-user-role">Chef de projet</div>
            </div>
          </div>
        </div>
      </header>
      <main class="saas-content">
        <div class="page-header">
          <h1 class="page-title">{page_title}</h1>
          <p class="page-subtitle">{page_subtitle}</p>
        </div>
        <div class="stats">
          <div class="stat-card"><div class="stat-label">Total</div><div class="stat-value" id="stat-total">0</div></div>
          <div class="stat-card"><div class="stat-label">En cours</div><div class="stat-value" id="stat-active">0</div></div>
          <div class="stat-card"><div class="stat-label">Terminées</div><div class="stat-value" id="stat-done">0</div></div>
        </div>
        <div class="panel">
          <div class="composer">
            <input type="text" class="composer-input" id="task-input" placeholder="{placeholder}" autocomplete="off" />
            <button type="button" class="btn-add" id="task-add-btn">{add_label}</button>
          </div>
          <ul class="task-list" id="task-list"></ul>
          <p class="empty-state" id="task-empty" hidden>Aucune tâche — ajoutez-en une ci-dessus.</p>
        </div>
      </main>
    </div>
  </div>
  <script>
(function () {{
  var STORAGE_KEY = "cf_tasks_{storage_slug}";
  var DONE_KEY = "{done_field}";
  var SEED_TASKS = [
    {{ id: "seed-1", text: "Finaliser la proposition client Acme Corp", completed: false }},
    {{ id: "seed-2", text: "Revoir le planning sprint Q2 avec l'équipe produit", completed: false }},
    {{ id: "seed-3", text: "Préparer la démo investisseurs (jeudi 14h)", completed: true }},
    {{ id: "seed-4", text: "Valider les maquettes onboarding mobile", completed: false }},
    {{ id: "seed-5", text: "Envoyer le compte-rendu réunion partenaires", completed: false }}
  ];
  var tasks = [];
  var listEl = document.getElementById("task-list");
  var emptyEl = document.getElementById("task-empty");
  var input = document.getElementById("task-input");
  var addBtn = document.getElementById("task-add-btn");

  function uid() {{
    return "t-" + Date.now().toString(36) + "-" + Math.random().toString(36).slice(2, 8);
  }}

  function normalizeTasks(raw) {{
    if (!Array.isArray(raw)) return [];
    return raw.filter(function (t) {{ return t && typeof t.text === "string"; }}).map(function (t) {{
      var o = {{ id: String(t.id || uid()), text: String(t.text) }};
      o[DONE_KEY] = !!t[DONE_KEY] || !!t.completed || !!t.done;
      return o;
    }});
  }}

  function load() {{
    try {{
      var raw = localStorage.getItem(STORAGE_KEY);
      if (!raw) {{
        tasks = normalizeTasks(SEED_TASKS);
        save();
        return;
      }}
      tasks = normalizeTasks(JSON.parse(raw));
      if (!tasks.length) {{
        tasks = normalizeTasks(SEED_TASKS);
        save();
      }}
    }} catch (e) {{
      tasks = normalizeTasks(SEED_TASKS);
    }}
  }}

  function save() {{
    try {{ localStorage.setItem(STORAGE_KEY, JSON.stringify(tasks)); }} catch (e) {{}}
  }}

  function updateStats() {{
    var total = tasks.length;
    var done = tasks.filter(function (t) {{ return t[DONE_KEY]; }}).length;
    var elTotal = document.getElementById("stat-total");
    var elActive = document.getElementById("stat-active");
    var elDone = document.getElementById("stat-done");
    if (elTotal) elTotal.textContent = String(total);
    if (elActive) elActive.textContent = String(total - done);
    if (elDone) elDone.textContent = String(done);
  }}

  function render() {{
    if (!listEl) return;
    listEl.replaceChildren();
    if (!tasks.length) {{
      if (emptyEl) emptyEl.hidden = false;
      updateStats();
      return;
    }}
    if (emptyEl) emptyEl.hidden = true;
    tasks.forEach(function (task) {{
      var li = document.createElement("li");
      li.className = "task-item" + (task[DONE_KEY] ? " done" : "");
      li.dataset.id = task.id;
      var cb = document.createElement("input");
      cb.type = "checkbox";
      cb.className = "task-check";
      cb.checked = !!task[DONE_KEY];
      cb.addEventListener("change", function () {{
        task[DONE_KEY] = cb.checked;
        save();
        render();
      }});
      var span = document.createElement("span");
      span.className = "task-text";
      span.textContent = task.text;
      var del = document.createElement("button");
      del.type = "button";
      del.className = "task-delete";
      del.textContent = "Supprimer";
      del.addEventListener("click", function () {{
        tasks = tasks.filter(function (t) {{ return t.id !== task.id; }});
        save();
        render();
      }});
      li.appendChild(cb);
      li.appendChild(span);
      li.appendChild(del);
      listEl.appendChild(li);
    }});
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
      if (e.key === "Enter") {{ e.preventDefault(); addTask(); }}
    }});
  }}

  load();
  render();
}})();
  </script>
</body>
</html>"""
