"""
Templates MV3 par secteur extension (ecommerce-helper, productivite, seo-analytics).
"""

from __future__ import annotations

import html as html_lib
import json
from typing import Any


def _primary(brief: dict[str, Any], fallback: str = "#4f46e5") -> str:
    return str(brief.get("couleur_primaire") or brief.get("primary_color") or fallback).strip()


def _name(brief: dict[str, Any]) -> str:
    return str(brief.get("client_name") or brief.get("extension_name") or "Mon extension").strip()


def _desc(brief: dict[str, Any]) -> str:
    return (
        str(brief.get("description") or brief.get("prompt") or "Extension CyberForge")
        .strip()
        .replace("\n", " ")[:200]
    )


def _base_css(primary: str) -> str:
    return f"""
* {{ box-sizing: border-box; margin: 0; padding: 0; }}
html, body {{
  width: 380px; min-height: 500px; max-height: 500px; overflow: hidden;
  font-family: Inter, system-ui, sans-serif; font-size: 13px;
  color: #e2e8f0; background: #0f1117;
}}
.popup {{ display: flex; flex-direction: column; height: 500px; }}
.header {{ padding: 10px 14px; background: #161b27; border-bottom: 1px solid rgba(255,255,255,0.08); }}
.header h1 {{ font-size: 14px; font-weight: 600; }}
.tabs {{ display: flex; gap: 0; background: #161b27; border-bottom: 1px solid rgba(255,255,255,0.08); }}
.tab {{
  flex: 1; padding: 10px 6px; text-align: center; font-size: 11px; cursor: pointer;
  color: #8892a4; border-bottom: 2px solid transparent; background: none; border-top: none;
  border-left: none; border-right: none;
}}
.tab.active {{ color: {primary}; border-bottom-color: {primary}; }}
.body {{ flex: 1; overflow-y: auto; padding: 12px 14px; }}
.panel {{ display: none; }}
.panel.active {{ display: block; }}
.card {{
  background: #1e2535; border: 1px solid rgba(255,255,255,0.08);
  border-radius: 8px; padding: 10px; margin-bottom: 8px;
}}
.card h2 {{ font-size: 11px; text-transform: uppercase; letter-spacing: 0.05em; color: #8892a4; margin-bottom: 8px; }}
.btn {{
  display: inline-block; padding: 8px 14px; border-radius: 8px; border: none;
  background: {primary}; color: #fff; cursor: pointer; font: inherit; font-size: 12px;
}}
.btn.secondary {{ background: #161b27; border: 1px solid rgba(255,255,255,0.12); color: #e2e8f0; }}
input, select, textarea {{
  width: 100%; padding: 8px; border-radius: 8px; border: 1px solid rgba(255,255,255,0.12);
  background: #161b27; color: #e2e8f0; font: inherit; margin-bottom: 8px;
}}
label {{ display: block; font-size: 11px; color: #8892a4; margin-bottom: 4px; }}
.row {{ display: flex; justify-content: space-between; align-items: center; padding: 6px 0;
  border-bottom: 1px solid rgba(255,255,255,0.06); font-size: 12px; }}
.row:last-child {{ border-bottom: none; }}
.muted {{ color: #8892a4; font-size: 11px; }}
.badge {{ display: inline-block; padding: 2px 8px; border-radius: 999px; font-size: 10px; }}
.badge.ok {{ background: rgba(16,185,129,0.2); color: #34d399; }}
.badge.warn {{ background: rgba(245,158,11,0.2); color: #fbbf24; }}
.badge.err {{ background: rgba(239,68,68,0.2); color: #f87171; }}
.toggle {{ position: relative; width: 40px; height: 22px; }}
.toggle input {{ opacity: 0; width: 0; height: 0; }}
.toggle .slider {{
  position: absolute; inset: 0; background: #334155; border-radius: 22px; cursor: pointer; transition: 0.2s;
}}
.toggle .slider:before {{
  content: ""; position: absolute; height: 16px; width: 16px; left: 3px; bottom: 3px;
  background: #fff; border-radius: 50%; transition: 0.2s;
}}
.toggle input:checked + .slider {{ background: {primary}; }}
.toggle input:checked + .slider:before {{ transform: translateX(18px); }}
"""


def _popup_shell(
    name: str,
    primary: str,
    tabs: list[tuple[str, str]],
    panels: list[str],
) -> str:
    safe = html_lib.escape(name)
    tab_btns = "".join(
        f'<button type="button" class="tab{" active" if i == 0 else ""}" data-tab="{tid}">{label}</button>'
        for i, (tid, label) in enumerate(tabs)
    )
    panel_html = "".join(
        f'<div class="panel{" active" if i == 0 else ""}" id="panel-{tid}">{body}</div>'
        for i, ((tid, _), body) in enumerate(zip(tabs, panels))
    )
    return f"""<!DOCTYPE html>
<html lang="fr">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=380, initial-scale=1" />
  <title>{safe}</title>
  <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600&display=swap" rel="stylesheet" />
  <style>{_base_css(primary)}</style>
</head>
<body>
  <div class="popup">
    <header class="header"><h1>{safe}</h1></header>
    <nav class="tabs">{tab_btns}</nav>
    <div class="body">{panel_html}</div>
  </div>
  <script src="popup.js"></script>
</body>
</html>"""


def _manifest_base(name: str, description: str, permissions: list[str], *, extra: dict | None = None) -> dict:
    m: dict[str, Any] = {
        "manifest_version": 3,
        "name": name,
        "version": "1.0.0",
        "description": description,
        "action": {"default_title": name, "default_popup": "popup.html"},
        "permissions": sorted(set(permissions)),
        "host_permissions": ["<all_urls>"],
        "background": {"service_worker": "background.js"},
        "content_scripts": [
            {"matches": ["<all_urls>"], "js": ["content.js"], "run_at": "document_idle"}
        ],
    }
    if extra:
        m.update(extra)
    return m


def _tab_js() -> str:
    return """
document.querySelectorAll('.tab').forEach(function(btn) {
  btn.addEventListener('click', function() {
    var id = btn.getAttribute('data-tab');
    document.querySelectorAll('.tab').forEach(function(b) { b.classList.remove('active'); });
    document.querySelectorAll('.panel').forEach(function(p) { p.classList.remove('active'); });
    btn.classList.add('active');
    var panel = document.getElementById('panel-' + id);
    if (panel) panel.classList.add('active');
    chrome.action.setBadgeText({ text: '' });
  });
});
"""


def build_ecommerce_helper(brief: dict[str, Any]) -> dict[str, str]:
    primary = _primary(brief, "#f59e0b")
    name = _name(brief)
    desc = _desc(brief)
    popup_html = _popup_shell(
        name,
        primary,
        [
            ("compare", "Comparateur"),
            ("alerts", "Alertes"),
            ("history", "Historique"),
        ],
        [
            """
<div class="card">
  <h2>Comparer un produit</h2>
  <label for="productUrl">URL produit</label>
  <input id="productUrl" type="url" placeholder="https://..." />
  <button type="button" class="btn" id="btnCompare">Comparer</button>
  <div id="compareResults" style="margin-top:10px"></div>
</div>
""",
            """
<div class="card">
  <h2>Alertes promos</h2>
  <div class="row"><span>Alertes promos actives</span>
    <label class="toggle"><input type="checkbox" id="alertToggle" checked /><span class="slider"></span></label>
  </div>
  <label for="alertThreshold">Seuil de réduction (%)</label>
  <input id="alertThreshold" type="number" value="15" min="1" max="90" />
</div>
""",
            """
<div class="card"><h2>5 derniers produits</h2><div id="historyList"><p class="muted">Aucun historique</p></div></div>
""",
        ],
    )
    popup_js = (
        _tab_js()
        + """
const SITES = ['Amazon', 'Fnac', 'Cdiscount'];
function fakePrices(url) {
  var base = 49.99 + (url.length % 37);
  return SITES.map(function(s, i) {
    return { site: s, price: (base + i * 7.5).toFixed(2) };
  });
}
document.getElementById('btnCompare').addEventListener('click', async function() {
  var url = document.getElementById('productUrl').value.trim();
  if (!url) { alert('URL requise'); return; }
  var prices = fakePrices(url);
  var html = prices.map(function(p) {
    return '<div class="row"><span>' + p.site + '</span><strong>' + p.price + ' €</strong></div>';
  }).join('');
  document.getElementById('compareResults').innerHTML = html;
  var hist = (await chrome.storage.local.get({ cf_history: [] })).cf_history || [];
  hist.unshift({ url: url, title: 'Produit', at: Date.now() });
  hist = hist.slice(0, 5);
  await chrome.storage.local.set({ cf_history: hist });
  renderHistory(hist);
  chrome.action.setBadgeText({ text: String(hist.length) });
});
async function renderHistory(items) {
  var el = document.getElementById('historyList');
  if (!items.length) { el.innerHTML = '<p class="muted">Aucun historique</p>'; return; }
  el.innerHTML = items.map(function(it) {
    return '<div class="row"><span>' + (it.title || it.url) + '</span><span class="muted">' + new Date(it.at).toLocaleDateString('fr') + '</span></div>';
  }).join('');
}
document.getElementById('alertToggle').addEventListener('change', async function(e) {
  await chrome.storage.local.set({ cf_alert_on: e.target.checked });
});
document.getElementById('alertThreshold').addEventListener('change', async function(e) {
  await chrome.storage.local.set({ cf_alert_threshold: parseInt(e.target.value, 10) || 15 });
});
chrome.storage.local.get({ cf_history: [], cf_alert_on: true, cf_alert_threshold: 15 }, function(d) {
  document.getElementById('alertToggle').checked = d.cf_alert_on;
  document.getElementById('alertThreshold').value = d.cf_alert_threshold;
  renderHistory(d.cf_history);
  if (d.cf_history.length) chrome.action.setBadgeText({ text: String(d.cf_history.length) });
});
"""
    )
    content_js = """
function extractProduct() {
  var title = document.title || '';
  var priceEl = document.querySelector('[itemprop=price], .price, [class*=price]');
  var price = priceEl ? priceEl.textContent.trim() : '';
  return { title: title.slice(0, 120), price: price };
}
chrome.runtime.onMessage.addListener(function(msg, _s, sendResponse) {
  if (msg && msg.type === 'cf_get_page_product') {
    sendResponse({ ok: true, data: extractProduct() });
  }
  return true;
});
"""
    background_js = """
chrome.runtime.onInstalled.addListener(function() {
  chrome.action.setBadgeBackgroundColor({ color: '#f59e0b' });
  chrome.action.setBadgeText({ text: '' });
});
chrome.runtime.onMessage.addListener(function(msg, sender, sendResponse) {
  if (msg && msg.type === 'cf_page_product_saved') {
    chrome.storage.local.get({ cf_history: [] }, function(d) {
      var hist = d.cf_history || [];
      hist.unshift(msg.item);
      chrome.storage.local.set({ cf_history: hist.slice(0, 5) });
      chrome.action.setBadgeText({ text: String(Math.min(hist.length, 5)) });
    });
    sendResponse({ ok: true });
  }
  return true;
});
"""
    manifest = _manifest_base(name, desc, ["activeTab", "scripting", "storage"])
    return _pack(name, manifest, popup_html, popup_js, background_js, content_js)


def build_productivite(brief: dict[str, Any]) -> dict[str, str]:
    primary = _primary(brief, "#8b5cf6")
    name = _name(brief)
    desc = _desc(brief)
    popup_html = _popup_shell(
        name,
        primary,
        [("timer", "Timer"), ("tasks", "Tâches"), ("block", "Blocage")],
        [
            """
<div class="card" style="text-align:center">
  <h2>Pomodoro 25 min</h2>
  <svg width="120" height="120" viewBox="0 0 120 120" style="margin:8px auto;display:block">
    <circle cx="60" cy="60" r="52" fill="none" stroke="#334155" stroke-width="8"/>
    <circle id="pomoArc" cx="60" cy="60" r="52" fill="none" stroke="""
            + primary
            + """ stroke-width="8" stroke-dasharray="327" stroke-dashoffset="0"
      transform="rotate(-90 60 60)" stroke-linecap="round"/>
  </svg>
  <p id="pomoTime" style="font-size:28px;font-weight:600;margin:8px 0">25:00</p>
  <button type="button" class="btn" id="pomoStart">Démarrer</button>
  <button type="button" class="btn secondary" id="pomoPause">Pause</button>
  <button type="button" class="btn secondary" id="pomoReset">Reset</button>
</div>
""",
            """
<div class="card">
  <h2>Tâches</h2>
  <input id="taskInput" type="text" placeholder="Nouvelle tâche..." />
  <button type="button" class="btn" id="taskAdd">Ajouter</button>
  <div id="taskList" style="margin-top:8px"></div>
</div>
""",
            """
<div class="card">
  <h2>Sites bloqués</h2>
  <div class="row"><span>Blocage actif</span>
    <label class="toggle"><input type="checkbox" id="blockToggle" /><span class="slider"></span></label>
  </div>
  <input id="blockSite" type="text" placeholder="exemple.com" />
  <button type="button" class="btn" id="blockAdd">Ajouter</button>
  <div id="blockList" style="margin-top:8px"></div>
</div>
""",
        ],
    )
    popup_js = (
        _tab_js()
        + """
var pomoTotal = 25 * 60, pomoLeft = pomoTotal, pomoTimer = null, pomoRunning = false;
function fmt(s) { var m = Math.floor(s/60), ss = s%60; return m + ':' + String(ss).padStart(2,'0'); }
function updatePomoUI() {
  document.getElementById('pomoTime').textContent = fmt(pomoLeft);
  var arc = document.getElementById('pomoArc');
  var pct = 1 - (pomoLeft / pomoTotal);
  arc.setAttribute('stroke-dashoffset', String(327 * pct));
}
function pomoTick() {
  if (pomoLeft <= 0) {
    clearInterval(pomoTimer); pomoRunning = false;
    try { var ctx = new (window.AudioContext || window.webkitAudioContext)();
      var o = ctx.createOscillator(); o.connect(ctx.destination); o.frequency.value = 880;
      o.start(); setTimeout(function(){ o.stop(); }, 400); } catch(e) {}
    chrome.notifications && chrome.notifications.create({ type: 'basic', iconUrl: 'icon.png', title: 'Pomodoro', message: 'Session terminée !' });
    return;
  }
  pomoLeft--; updatePomoUI();
}
document.getElementById('pomoStart').addEventListener('click', function() {
  if (pomoRunning) return;
  pomoRunning = true;
  pomoTimer = setInterval(pomoTick, 1000);
  chrome.alarms.create('cf_pomodoro', { delayInMinutes: pomoLeft / 60 });
});
document.getElementById('pomoPause').addEventListener('click', function() {
  clearInterval(pomoTimer); pomoRunning = false; chrome.alarms.clear('cf_pomodoro');
});
document.getElementById('pomoReset').addEventListener('click', function() {
  clearInterval(pomoTimer); pomoRunning = false; pomoLeft = pomoTotal;
  updatePomoUI(); chrome.alarms.clear('cf_pomodoro');
});
updatePomoUI();
async function loadTasks() {
  var d = await chrome.storage.sync.get({ cf_tasks: [] });
  var el = document.getElementById('taskList');
  el.innerHTML = (d.cf_tasks || []).map(function(t, i) {
    return '<div class="row"><label><input type="checkbox" data-i="'+i+'" '+(t.done?'checked':'')+'> '+t.text+'</label><button type="button" data-del="'+i+'" class="btn secondary" style="padding:4px 8px">✕</button></div>';
  }).join('') || '<p class="muted">Aucune tâche</p>';
}
document.getElementById('taskAdd').addEventListener('click', async function() {
  var text = document.getElementById('taskInput').value.trim();
  if (!text) return;
  var d = await chrome.storage.sync.get({ cf_tasks: [] });
  d.cf_tasks.push({ text: text, done: false });
  await chrome.storage.sync.set({ cf_tasks: d.cf_tasks });
  document.getElementById('taskInput').value = '';
  loadTasks();
});
document.getElementById('taskList').addEventListener('click', async function(e) {
  var del = e.target.getAttribute('data-del');
  if (del != null) {
    var d = await chrome.storage.sync.get({ cf_tasks: [] });
    d.cf_tasks.splice(parseInt(del, 10), 1);
    await chrome.storage.sync.set({ cf_tasks: d.cf_tasks });
    loadTasks();
  }
});
document.getElementById('taskList').addEventListener('change', async function(e) {
  var i = e.target.getAttribute('data-i');
  if (i == null) return;
  var d = await chrome.storage.sync.get({ cf_tasks: [] });
  d.cf_tasks[parseInt(i, 10)].done = e.target.checked;
  await chrome.storage.sync.set({ cf_tasks: d.cf_tasks });
});
async function loadBlocks() {
  var d = await chrome.storage.local.get({ cf_blocks: [], cf_block_on: false });
  document.getElementById('blockToggle').checked = d.cf_block_on;
  var el = document.getElementById('blockList');
  el.innerHTML = (d.cf_blocks || []).map(function(s) {
    return '<div class="row"><span>'+s+'</span></div>';
  }).join('') || '<p class="muted">Aucun site</p>';
  chrome.runtime.sendMessage({ type: 'cf_sync_block_rules', on: d.cf_block_on, sites: d.cf_blocks });
}
document.getElementById('blockAdd').addEventListener('click', async function() {
  var site = document.getElementById('blockSite').value.trim();
  if (!site) return;
  var d = await chrome.storage.local.get({ cf_blocks: [] });
  d.cf_blocks.push(site);
  await chrome.storage.local.set({ cf_blocks: d.cf_blocks });
  loadBlocks();
});
document.getElementById('blockToggle').addEventListener('change', async function(e) {
  await chrome.storage.local.set({ cf_block_on: e.target.checked });
  loadBlocks();
});
loadTasks(); loadBlocks();
"""
    )
    background_js = """
chrome.runtime.onInstalled.addListener(function() {
  chrome.action.setBadgeBackgroundColor({ color: '#8b5cf6' });
});
chrome.alarms.onAlarm.addListener(function(alarm) {
  if (alarm.name === 'cf_pomodoro') {
    chrome.action.setBadgeText({ text: '!' });
  }
});
function applyBlockRules(on, sites) {
  if (!chrome.declarativeNetRequest) return;
  var rules = (sites || []).map(function(host, i) {
    return {
      id: i + 1,
      priority: 1,
      action: { type: 'block' },
      condition: { urlFilter: '||' + host.replace(/^https?:\\/\\//, '') + '/', resourceTypes: ['main_frame'] }
    };
  });
  chrome.declarativeNetRequest.updateDynamicRules({
    removeRuleIds: Array.from({length: 50}, function(_, i) { return i + 1; }),
    addRules: on ? rules : []
  });
}
chrome.runtime.onMessage.addListener(function(msg, _s, sendResponse) {
  if (msg && msg.type === 'cf_sync_block_rules') {
    applyBlockRules(msg.on, msg.sites || []);
    sendResponse({ ok: true });
  }
  return true;
});
"""
    content_js = "// Productivité — content script minimal\n"
    manifest = _manifest_base(
        name,
        desc,
        ["activeTab", "storage", "alarms", "declarativeNetRequest"],
        extra={"declarative_net_request": {"rule_resources": []}},
    )
    return _pack(name, manifest, popup_html, popup_js, background_js, content_js)


def build_seo_analytics(brief: dict[str, Any]) -> dict[str, str]:
    primary = _primary(brief, "#06b6d4")
    name = _name(brief)
    desc = _desc(brief)
    popup_html = _popup_shell(
        name,
        primary,
        [("meta", "Méta"), ("score", "Score"), ("links", "Liens")],
        [
            """
<div class="card"><h2>Métadonnées page</h2><div id="metaPanel"><p class="muted">Ouvrez un onglet puis actualisez</p></div>
<button type="button" class="btn" id="btnRefreshMeta">Actualiser</button></div>
""",
            """
<div class="card" style="text-align:center">
  <h2>Score lisibilité</h2>
  <svg width="100" height="100" viewBox="0 0 100 100">
    <circle cx="50" cy="50" r="42" fill="none" stroke="#334155" stroke-width="10"/>
    <circle id="scoreArc" cx="50" cy="50" r="42" fill="none" stroke="""
            + primary
            + """ stroke-width="10" stroke-dasharray="264" stroke-dashoffset="66"
      transform="rotate(-90 50 50)"/>
  </svg>
  <p id="scoreVal" style="font-size:32px;font-weight:700;margin-top:-62px">—</p>
  <p class="muted" id="scoreHint">Analyse en attente</p>
</div>
""",
            """
<div class="card"><h2>Liens</h2><div id="linksSummary" class="muted">—</div><div id="linksList" style="margin-top:8px"></div></div>
""",
        ],
    )
    popup_js = (
        _tab_js()
        + """
function renderMeta(data) {
  var el = document.getElementById('metaPanel');
  if (!data) { el.innerHTML = '<p class="muted">Aucune donnée</p>'; return; }
  el.innerHTML = ['title','description','ogImage','canonical'].map(function(k) {
    var labels = {title:'Title',description:'Description',ogImage:'og:image',canonical:'Canonical'};
    return '<div class="row"><span>'+labels[k]+'</span><span style="max-width:200px;overflow:hidden;text-overflow:ellipsis">'+((data[k]||'—')+'')+'</span></div>';
  }).join('');
}
function renderScore(score) {
  document.getElementById('scoreVal').textContent = score;
  var arc = document.getElementById('scoreArc');
  arc.setAttribute('stroke-dashoffset', String(264 * (1 - score / 100)));
  document.getElementById('scoreHint').textContent = score >= 70 ? 'Bonne lisibilité' : 'À améliorer';
}
function renderLinks(data) {
  document.getElementById('linksSummary').textContent =
    'Internes: ' + data.internal + ' | Externes: ' + data.external + ' | Cassés: ' + data.broken;
  document.getElementById('linksList').innerHTML = (data.items || []).map(function(l) {
    var cls = l.broken ? 'err' : (l.external ? 'warn' : 'ok');
    return '<div class="row"><span class="badge '+cls+'">'+(l.external?'ext':'int')+'</span><span style="overflow:hidden;text-overflow:ellipsis;max-width:260px">'+l.href+'</span></div>';
  }).join('');
}
async function queryTab() {
  var tabs = await chrome.tabs.query({ active: true, currentWindow: true });
  var tab = tabs[0];
  if (!tab || !tab.id) return null;
  return chrome.tabs.sendMessage(tab.id, { type: 'cf_seo_analyze' });
}
document.getElementById('btnRefreshMeta').addEventListener('click', async function() {
  var res = await queryTab();
  if (res && res.ok) {
    renderMeta(res.meta);
    renderScore(res.score);
    renderLinks(res.links);
    chrome.action.setBadgeText({ text: String(res.score) });
  }
});
queryTab().then(function(res) {
  if (res && res.ok) { renderMeta(res.meta); renderScore(res.score); renderLinks(res.links); }
});
"""
    )
    content_js = """
function analyzePage() {
  var title = document.title || '';
  var desc = (document.querySelector('meta[name=description]') || {}).content || '';
  var og = (document.querySelector('meta[property="og:image"]') || {}).content || '';
  var canonical = (document.querySelector('link[rel=canonical]') || {}).href || '';
  var text = (document.body && document.body.innerText) || '';
  var sentences = text.split(/[.!?]+/).filter(function(s) { return s.trim().length > 10; });
  var words = text.toLowerCase().split(/\\s+/).filter(Boolean);
  var avgLen = sentences.length ? sentences.reduce(function(a,s){return a+s.split(/\\s+/).length;},0)/sentences.length : 0;
  var common = ['le','la','les','de','du','des','un','une','et','en','pour','sur','avec'];
  var commonRatio = words.length ? words.filter(function(w){return common.indexOf(w)>=0;}).length/words.length : 0;
  var score = Math.max(0, Math.min(100, Math.round(100 - Math.abs(avgLen-15)*3 - Math.abs(commonRatio-0.35)*80)));
  var origin = location.origin;
  var anchors = Array.from(document.querySelectorAll('a[href]')).slice(0, 50);
  var internal = 0, external = 0, broken = 0, items = [];
  anchors.forEach(function(a) {
    var href = a.getAttribute('href') || '';
    var ext = href.startsWith('http') && href.indexOf(origin) !== 0;
    if (ext) external++; else internal++;
    var bad = !href || href === '#';
    if (bad) broken++;
    if (items.length < 10) items.push({ href: href.slice(0, 80), external: ext, broken: bad });
  });
  return {
    meta: { title: title, description: desc, ogImage: og, canonical: canonical },
    score: score,
    links: { internal: internal, external: external, broken: broken, items: items }
  };
}
chrome.runtime.onMessage.addListener(function(msg, _s, sendResponse) {
  if (msg && msg.type === 'cf_seo_analyze') {
    sendResponse({ ok: true, ...analyzePage() });
  }
  return true;
});
"""
    background_js = """
chrome.runtime.onInstalled.addListener(function() {
  chrome.action.setBadgeBackgroundColor({ color: '#06b6d4' });
});
"""
    manifest = _manifest_base(name, desc, ["activeTab", "scripting", "storage"])
    return _pack(name, manifest, popup_html, popup_js, background_js, content_js)


def _pack(
    name: str,
    manifest: dict,
    popup_html: str,
    popup_js: str,
    background_js: str,
    content_js: str,
) -> dict[str, str]:
    readme = f"""# {name}

Extension Chrome Manifest V3 — CyberForge.

## Installation
1. `chrome://extensions` → Mode développeur
2. Charger l'extension non empaquetée (dossier dézippé)

## Fichiers
manifest.json, popup.html, popup.js, background.js, content.js
"""
    return {
        "manifest.json": json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
        "popup.html": popup_html,
        "popup.js": popup_js,
        "background.js": background_js,
        "content.js": content_js,
        "README.md": readme,
    }
