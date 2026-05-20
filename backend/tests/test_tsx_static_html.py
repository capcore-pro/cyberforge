from tools.tsx_static_html import build_static_site_html

SAMPLE = """
export default function App() {
  return (
    <main className="min-h-screen bg-slate-950 text-cyan-400 p-8">
      <h1 id="hero">Restaurant Neon</h1>
      <a href="#menu">Voir le menu</a>
      <section id="menu" className="mt-8">
        <h2>Carte</h2>
        <button type="button">Reserver</button>
      </section>
    </main>
  );
}
"""


def test_static_site_preserves_structure():
    html = build_static_site_html(SAMPLE, title="Restaurant Neon")
    assert "<!DOCTYPE html>" in html
    assert "Restaurant Neon" in html
    assert 'href="#menu"' in html
    assert "cf-demo-root" in html
    assert "<script>" in html
