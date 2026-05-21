"""Tests démos HTML autonomes (vanilla JS, sans conversion JSX)."""

from tools.demo_preview_html import build_demo_preview_html
from tools.standalone_demo_html import (
    TASK_PREVIEW_MARKER,
    build_standalone_demo_html,
    build_task_manager_standalone_html,
    classify_demo_kind,
    is_fresh_task_preview_html,
    is_react_task_app,
    wrap_with_password_gate,
)

REACT_TODO_TSX = """
export default function App() {
  const [tasks, setTasks] = useState([]);
  const [input, setInput] = useState("");

  const addTask = () => {
    if (!input.trim()) return;
    setTasks([...tasks, { id: Date.now(), text: input.trim(), completed: false }]);
    setInput("");
  };

  const toggleTask = (id) => {
    setTasks(tasks.map((t) => (t.id === id ? { ...t, completed: !t.completed } : t)));
  };

  const deleteTask = (id) => {
    setTasks(tasks.filter((t) => t.id !== id));
  };

  return (
    <main className="min-h-screen bg-slate-950 text-slate-100 p-8">
      <h1 className="text-2xl font-bold text-cyan-400">Mes tâches</h1>
      <div className="flex gap-2 mt-4">
        <input
          className="flex-1 rounded-lg border border-slate-700 bg-slate-900 px-3 py-2"
          placeholder="Ajouter une tâche"
          value={input}
          onChange={(e) => setInput(e.target.value)}
        />
        <button
          type="button"
          className="rounded-lg bg-violet-600 px-4 py-2 font-semibold"
          onClick={addTask}
        >
          Ajouter
        </button>
      </div>
      <ul className="mt-6 space-y-2">
        {tasks.map((task) => (
          <li
            key={task.id}
            className="flex items-center gap-3 rounded-lg border border-slate-700 bg-slate-900 p-4"
          >
            <input
              type="checkbox"
              checked={task.completed}
              onChange={() => toggleTask(task.id)}
            />
            <span className={task.completed ? "line-through opacity-60" : ""}>{task.text}</span>
            <button
              type="button"
              className="text-red-400 hover:text-red-300"
              onClick={() => deleteTask(task.id)}
            >
              Supprimer
            </button>
          </li>
        ))}
      </ul>
    </main>
  );
}
"""


def test_detect_react_task_app() -> None:
    assert is_react_task_app(REACT_TODO_TSX)
    assert classify_demo_kind(REACT_TODO_TSX, "Todo") == "tasks"


def test_classify_gestion_taches() -> None:
    sources = """
    export default function TaskApp() {
      const [tasks, setTasks] = useState([]);
      const addTask = () => { ... };
      return tasks.map((task) => <li key={task.id}>...</li>);
    }
    """
    assert classify_demo_kind(sources, "Gestion de tâches") == "tasks"


def test_task_demo_is_interactive_standalone() -> None:
    html = build_demo_preview_html(
        [{"path": "src/App.tsx", "content": REACT_TODO_TSX}],
        title="Gestion de tâches",
    )
    assert TASK_PREVIEW_MARKER in html
    assert is_fresh_task_preview_html(html)
    assert "function addTask" in html
    assert "task-delete" in html
    assert "addEventListener" in html
    assert "task-add-btn" in html
    assert "replaceChildren" in html
    assert "Mes tâches" in html
    assert "Ajouter une tâche" in html
    assert "<style>" in html
    assert "saas-shell" in html
    assert "saas-sidebar" in html
    assert "task-check" in html
    assert "btn-add" in html
    assert "onclick=" not in html.lower()
    assert "onchange=" not in html.lower()
    assert "onClick" not in html
    assert "void(0)" not in html
    assert "React" not in html
    assert "useState" not in html


def test_showcase_fallback_for_landing() -> None:
    tsx = """
    export default function App() {
      return (
        <main className="min-h-screen bg-slate-950">
          <h1>Café du port</h1>
          <p>Menu et terrasse.</p>
        </main>
      );
    }
    """
    html = build_standalone_demo_html(tsx, title="Café du port")
    assert classify_demo_kind(tsx, "Café") == "showcase"
    assert "mock-hero" in html or "mock-section" in html
    assert "onclick=" not in html.lower()


def test_password_gate_wraps_demo_inline() -> None:
    inner = build_task_manager_standalone_html(title="Todo", sources=REACT_TODO_TSX)
    html = build_standalone_demo_html(REACT_TODO_TSX, title="Todo", password="soleil-bateau-rouge")
    assert "cf-login-screen" in html
    assert 'id="cf-demo-content"' in html
    assert "display: none" in html or "display:none" in html
    assert "soleil-bateau-rouge" in html
    assert "task-input" in html
    assert "<!DOCTYPE html>" in inner
    assert ".saas-shell" in inner
    wrapped = wrap_with_password_gate(inner, "secret-demo")
    assert "cf-login-error" in wrapped
    assert "EXPECTED" in wrapped
    head_part = wrapped[: wrapped.lower().find("</head>")]
    assert ".composer-input" in head_part
    assert ".btn-add" in head_part
    assert ".composer-input" in head_part


def test_task_manager_direct_has_controls() -> None:
    html = build_task_manager_standalone_html(
        title="Todo démo",
        sources=REACT_TODO_TSX,
    )
    assert 'id="task-input"' in html
    assert 'id="task-add-btn"' in html
    assert "Supprimer" in html
    assert "function addTask" in html
    assert "saas-topbar" in html
    assert "Alex Martin" in html
    assert "SEED_TASKS" in html
    assert "Finaliser la proposition client Acme Corp" in html
