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
    assert "Démo client" in html
    assert "Réserver" in html or "réserver" in html.lower()


def test_complete_html_passthrough():
    raw = "<!DOCTYPE html><html><body><h1>Page brute</h1></body></html>"
    html = build_demo_preview_html([{"path": "index.html", "content": raw}])
    assert "Page brute" in html
