"""Tests démos HTML autonomes (vanilla JS, sans conversion JSX)."""

from tools.demo_preview_html import build_demo_preview_html
from tools.standalone_demo_html import (
    build_standalone_demo_html,
    build_task_manager_standalone_html,
    classify_demo_kind,
)


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
    tsx = """
    // App gestion de tâches — React source (non rendue telle quelle)
    export default function App() {
      const [tasks, setTasks] = useState([]);
      return (
        <div>
          <h1>Ma liste de tâches</h1>
          <input onChange={(e) => setText(e.target.value)} />
          <button onClick={addTask}>Ajouter une tâche</button>
          {tasks.map((task) => (
            <div key={task.id}>
              <input type="checkbox" checked={task.done} onChange={() => toggle(task.id)} />
              <button onClick={() => removeTask(task.id)}>Supprimer</button>
            </div>
          ))}
        </div>
      );
    }
    """
    html = build_demo_preview_html(
        [{"path": "src/App.tsx", "content": tsx}],
        title="Gestion de tâches",
    )
    assert "<!DOCTYPE html>" in html
    assert "task-form" in html
    assert "addEventListener" in html
    assert "localStorage" in html
    assert "Ma liste de tâches" in html or "Gestion de tâches" in html
    assert "onclick=" not in html.lower()
    assert "onchange=" not in html.lower()
    assert "onClick" not in html
    assert "void(0)" not in html
    assert "className" not in html
    assert "React" not in html


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


def test_task_manager_direct_has_controls() -> None:
    html = build_task_manager_standalone_html(title="Todo démo")
    assert 'id="task-input"' in html
    assert "Supprimer" in html
    assert "filter-btn" in html
