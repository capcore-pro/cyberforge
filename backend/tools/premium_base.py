"""Styles et helpers partagés — templates premium CyberForge."""

from __future__ import annotations

from tools.demo_preview_html import escape_attr, escape_html

CYBERFORGE_PREVIEW_MARKER = "cf-preview:v4-premium"

PREMIUM_BASE_CSS = """
    *, *::before, *::after { box-sizing: border-box; }
    body {
      margin: 0;
      min-height: 100vh;
      font-family: "Segoe UI", system-ui, -apple-system, sans-serif;
      font-size: 14px;
      line-height: 1.5;
      color: #e2e8f0;
      background: #0b0f1a;
      -webkit-font-smoothing: antialiased;
    }
    a { color: #22d3ee; text-decoration: none; }
    a:hover { text-decoration: underline; }
    .cf-shell { min-height: 100vh; width: 100%; max-width: 100vw; overflow-x: hidden; }
    .cf-btn {
      display: inline-flex; align-items: center; justify-content: center; gap: 0.4rem;
      padding: 0.55rem 1.1rem; border-radius: 10px; font-weight: 600; font-size: 0.875rem;
      border: none; cursor: pointer; transition: transform 0.15s, box-shadow 0.15s;
    }
    .cf-btn-primary {
      background: linear-gradient(135deg, #6366f1, #4f46e5);
      color: #fff; box-shadow: 0 4px 18px rgba(99,102,241,0.4);
    }
    .cf-btn-primary:hover { transform: translateY(-1px); }
    .cf-btn-ghost {
      background: rgba(255,255,255,0.06); color: #e2e8f0;
      border: 1px solid rgba(255,255,255,0.12);
    }
    .cf-card {
      background: rgba(15,23,42,0.75);
      border: 1px solid rgba(255,255,255,0.08);
      border-radius: 14px;
      padding: 1.25rem;
    }
    .cf-logo {
      width: 40px; height: 40px; border-radius: 12px;
      background: linear-gradient(135deg, #6366f1, #22d3ee);
      display: flex; align-items: center; justify-content: center;
      font-weight: 800; font-size: 0.75rem; color: #fff;
    }
    @media (min-width: 900px) {
      .cf-menu-btn { display: none !important; }
      .cf-sidebar { transform: translateX(0) !important; display: flex !important; }
      .cf-sidebar-backdrop { display: none !important; }
      .cf-with-sidebar .cf-main { margin-left: min(260px, 28vw); }
    }
"""


def user_initials(name: str, fallback: str = "CF") -> str:
    parts = [p for p in name.split() if p.strip()]
    if len(parts) >= 2:
        return (parts[0][0] + parts[1][0]).upper()
    if parts:
        return parts[0][:2].upper()
    return fallback


def shell_nav_script(shell_id: str = "cf-shell") -> str:
    return f"""
  (function() {{
    var shell = document.getElementById("{shell_id}");
    if (!shell) return;
    var btn = shell.querySelector(".cf-menu-btn");
    var backdrop = shell.querySelector(".cf-sidebar-backdrop");
    function close() {{ shell.classList.remove("cf-nav-open"); }}
    function toggle() {{ shell.classList.toggle("cf-nav-open"); }}
    if (btn) btn.addEventListener("click", toggle);
    if (backdrop) backdrop.addEventListener("click", close);
  }})();
"""
