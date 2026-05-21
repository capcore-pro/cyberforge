"""Tests conversion TSX → HTML statique pour démos client."""

from tools.demo_preview_html import build_demo_preview_html, extract_preview_mockup


def test_build_from_tsx_contains_title_and_banner():
    files = [
        {
            "path": "src/App.tsx",
            "content": """
export default function App() {
  return (
    <main className="min-h-screen bg-slate-950 text-cyan-400">
      <h1>Restaurant Le Neon</h1>
      <p>Menu du jour et réservations en ligne.</p>
      <section>
        <h2>Nos plats</h2>
        <p>Carte saisonnière.</p>
      </section>
      <button>Réserver une table</button>
    </main>
  );
}
""",
        }
    ]
    html = build_demo_preview_html(files, title="Ma démo")
    assert "<!DOCTYPE html>" in html
    assert "Restaurant Le Neon" in html
    assert "CyberForge" in html
    assert "Réserver" in html or "réserver" in html.lower()


def test_complete_html_passthrough():
    raw = "<!DOCTYPE html><html><body><h1>Page brute</h1></body></html>"
    html = build_demo_preview_html([{"path": "index.html", "content": raw}])
    assert "Page brute" in html


def test_map_loop_expanded_without_jsx_artifacts():
    tsx = """
export default function App() {
  return (
    <section className="py-20 bg-amber-100">
      <div className="max-w-4xl mx-auto px-4 grid md:grid-cols-3 gap-8">
        {[
          { name: 'Espresso', desc: 'Intense', price: '2,50€' },
          { name: 'Latte', desc: 'Crémeux', price: '3,50€' },
        ].map((item) => (
          <div key={item.name} className="bg-white rounded-xl p-6 shadow-md">
            <h3 className="text-2xl font-semibold">{item.name}</h3>
            <p className="text-amber-700">{item.desc}</p>
            <p className="text-xl font-bold">{item.price}</p>
          </div>
        ))}
      </div>
    </section>
  );
}
"""
    html = build_demo_preview_html([{"path": "src/App.tsx", "content": tsx}], title="Café")
    assert "Espresso" in html
    assert "Latte" in html
    assert ".map" not in html
    assert "}}}" not in html
    assert "=>" not in html


def test_task_tsx_uses_standalone_not_jsx_conversion():
    """Une app todo React source ne doit plus passer par la conversion JSX."""
    tsx = """
export default function App() {
  const [tasks, setTasks] = useState([]);
  return (
    <div>
      <h1>Tâches</h1>
      <button onClick={addTask}>Ajouter</button>
    </div>
  );
}
"""
    html = build_demo_preview_html(
        [{"path": "src/App.tsx", "content": tsx}],
        title="Gestion de tâches",
    )
    assert "task-list" in html
    assert "cf-demo-root" not in html
    assert "void(0)" not in html
