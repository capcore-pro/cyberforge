/**
 * CyberForge CMS Panel — édition client in-page (vanilla JS, zéro dépendance).
 * S'active avec ?cms=1 ou cookie cms_token.
 */
(function () {
  "use strict";

  var CMS_TOKEN_COOKIE = "cms_token";
  var CMS_QUERY = "cms";

  function getCookie(name) {
    var match = document.cookie.match(new RegExp("(?:^|; )" + name + "=([^;]*)"));
    return match ? decodeURIComponent(match[1]) : "";
  }

  function setCookie(name, value, days) {
    var maxAge = days ? "; max-age=" + days * 86400 : "";
    document.cookie =
      name + "=" + encodeURIComponent(value) + "; path=/" + maxAge + "; SameSite=Lax";
  }

  function clearCookie(name) {
    document.cookie = name + "=; path=/; max-age=0; SameSite=Lax";
  }

  function shouldActivate() {
    try {
      var params = new URLSearchParams(window.location.search);
      if (params.get(CMS_QUERY) === "1") return true;
    } catch (e) {
      /* ignore */
    }
    return Boolean(getCookie(CMS_TOKEN_COOKIE));
  }

  if (!shouldActivate()) return;

  var scriptEl =
    document.currentScript ||
    document.querySelector('script[src*="cms/panel.js"]');

  function resolveApiBase() {
    var meta = document.querySelector('meta[name="cyberforge-cms-api"]');
    if (meta && meta.getAttribute("content")) {
      return meta.getAttribute("content").replace(/\/$/, "");
    }
    if (scriptEl && scriptEl.src) {
      return scriptEl.src.replace(/\/cms\/panel\.js.*$/, "") + "/api";
    }
    return "/api";
  }

  function resolveProjectId() {
    var meta = document.querySelector('meta[name="cyberforge-cms-project-id"]');
    if (meta && meta.getAttribute("content")) {
      return meta.getAttribute("content").trim();
    }
    if (document.body && document.body.dataset.cmsProjectId) {
      return document.body.dataset.cmsProjectId.trim();
    }
    return "";
  }

  var state = {
    apiBase: resolveApiBase(),
    projectId: resolveProjectId(),
    token: getCookie(CMS_TOKEN_COOKIE) || "",
    open: false,
    busy: false,
    statusMsg: "",
    statusType: "",
    initialSnapshot: [],
    blocks: [],
  };

  function authHeaders() {
    var h = { "Content-Type": "application/json" };
    if (state.token) h.Authorization = "Bearer " + state.token;
    return h;
  }

  function labelFromKey(key) {
    if (!key) return "Bloc";
    return key
      .split(".")
      .pop()
      .replace(/([A-Z])/g, " $1")
      .replace(/_/g, " ")
      .replace(/^\w/, function (c) {
        return c.toUpperCase();
      });
  }

  function collectDomBlocks() {
    var nodes = document.querySelectorAll("[data-cms][data-cms-key]");
    var list = [];
    nodes.forEach(function (el, index) {
      var type = (el.getAttribute("data-cms") || "text").toLowerCase();
      var key = el.getAttribute("data-cms-key") || "block." + index;
      var label = el.getAttribute("data-cms-label") || labelFromKey(key);
      list.push({ el: el, type: type, key: key, label: label });
    });
    return list;
  }

  function slugKey(key) {
    return String(key || "block").replace(/[^a-z0-9]+/gi, "-");
  }

  function imageElement(el) {
    if (el.tagName === "IMG") return el;
    return el.querySelector("img");
  }

  function readValue(entry) {
    var el = entry.el;
    var type = entry.type;
    if (type === "image") {
      var img = imageElement(el);
      if (img) {
        return { url: img.getAttribute("src") || "", alt: img.getAttribute("alt") || "" };
      }
      var bg = window.getComputedStyle(el).backgroundImage;
      var url = "";
      if (bg && bg !== "none") {
        var m = bg.match(/url\(["']?([^"')]+)["']?\)/);
        url = m ? m[1] : "";
      }
      return { url: url, alt: el.getAttribute("aria-label") || "" };
    }
    if (type === "color") {
      var stored = el.getAttribute("data-cms-value");
      if (stored && stored.startsWith("#")) return stored;
      var cssVar = el.getAttribute("data-cms-css-var");
      if (cssVar) {
        var raw = window.getComputedStyle(document.documentElement).getPropertyValue(cssVar).trim();
        if (raw.startsWith("#")) return raw;
      }
      return "#0284c7";
    }
    return (el.textContent || "").trim();
  }

  function applyValue(entry, value) {
    var el = entry.el;
    var type = entry.type;
    if (type === "image") {
      var url = typeof value === "object" && value ? value.url : String(value || "");
      var alt = typeof value === "object" && value ? value.alt || "" : "";
      var img = imageElement(el);
      if (img) {
        img.setAttribute("src", url);
        if (alt) img.setAttribute("alt", alt);
      } else if (url) {
        el.style.backgroundImage = 'url("' + url.replace(/"/g, '\\"') + '")';
      }
      return;
    }
    if (type === "color") {
      var hex = String(value || "").trim();
      var cssVar = el.getAttribute("data-cms-css-var");
      if (cssVar && hex) {
        document.documentElement.style.setProperty(cssVar, hex);
      }
      if (hex.startsWith("#")) {
        el.setAttribute("data-cms-value", hex);
      }
      return;
    }
    el.textContent = String(value || "");
  }

  function takeSnapshot() {
    return collectDomBlocks().map(function (entry) {
      return {
        key: entry.key,
        type: entry.type,
        label: entry.label,
        value: readValue(entry),
      };
    });
  }

  function restoreSnapshot(snapshot) {
    var map = {};
    snapshot.forEach(function (b) {
      map[b.key] = b;
    });
    collectDomBlocks().forEach(function (entry) {
      var saved = map[entry.key];
      if (saved) applyValue(entry, saved.value);
    });
  }

  function injectStyles() {
    if (document.getElementById("cf-cms-styles")) return;
    var css =
      "#cf-cms-fab{position:fixed;bottom:24px;right:24px;z-index:99998;" +
      "padding:12px 18px;border:none;border-radius:999px;cursor:pointer;" +
      "font:600 14px system-ui,sans-serif;color:#0a0a0a;background:linear-gradient(135deg,#d4af37,#f5d76e);" +
      "box-shadow:0 8px 24px rgba(0,0,0,.35);transition:transform .15s}" +
      "#cf-cms-fab:hover{transform:scale(1.04)}" +
      "#cf-cms-overlay{position:fixed;inset:0;background:rgba(0,0,0,.45);z-index:99998;opacity:0;" +
      "pointer-events:none;transition:opacity .25s}" +
      "#cf-cms-overlay.cf-open{opacity:1;pointer-events:auto}" +
      "#cf-cms-panel{position:fixed;top:0;right:0;width:320px;max-width:100vw;height:100%;z-index:99999;" +
      "background:#111827;color:#e5e7eb;display:flex;flex-direction:column;" +
      "transform:translateX(100%);transition:transform .28s ease;box-shadow:-8px 0 32px rgba(0,0,0,.4)}" +
      "#cf-cms-panel.cf-open{transform:translateX(0)}" +
      ".cf-cms-header{padding:16px;border-bottom:1px solid #374151;display:flex;align-items:center;gap:10px}" +
      ".cf-cms-logo{width:32px;height:32px;border-radius:8px;background:linear-gradient(135deg,#d4af37,#92700c);" +
      "display:flex;align-items:center;justify-content:center;font-weight:800;font-size:11px;color:#111}" +
      ".cf-cms-title{flex:1;font:600 15px system-ui,sans-serif}" +
      ".cf-cms-close{background:none;border:none;color:#9ca3af;font-size:22px;cursor:pointer;line-height:1}" +
      ".cf-cms-body{flex:1;overflow-y:auto;padding:12px 16px}" +
      ".cf-cms-section{margin-bottom:16px}" +
      ".cf-cms-section h3{margin:0 0 8px;font:600 11px system-ui,sans-serif;text-transform:uppercase;" +
      "letter-spacing:.06em;color:#d4af37}" +
      ".cf-cms-field{margin-bottom:12px}" +
      ".cf-cms-field label{display:block;font:500 11px system-ui;color:#9ca3af;margin-bottom:4px}" +
      ".cf-cms-field input[type=text],.cf-cms-field textarea,.cf-cms-field input[type=email]," +
      ".cf-cms-field input[type=password]{width:100%;box-sizing:border-box;padding:8px 10px;border-radius:8px;" +
      "border:1px solid #374151;background:#1f2937;color:#f3f4f6;font:400 13px system-ui}" +
      ".cf-cms-field textarea{min-height:72px;resize:vertical}" +
      ".cf-cms-field input[type=color]{width:100%;height:36px;border:1px solid #374151;border-radius:8px;" +
      "background:#1f2937;cursor:pointer;padding:2px}" +
      ".cf-cms-img-preview{width:100%;height:80px;object-fit:cover;border-radius:8px;border:1px solid #374151;" +
      "margin-bottom:6px;background:#1f2937}" +
      ".cf-cms-btn-sm{padding:6px 10px;border-radius:6px;border:1px solid #4b5563;background:#1f2937;" +
      "color:#e5e7eb;font:500 12px system-ui;cursor:pointer}" +
      ".cf-cms-footer{padding:12px 16px;border-top:1px solid #374151;display:flex;flex-direction:column;gap:8px}" +
      ".cf-cms-btn-primary{padding:10px;border:none;border-radius:8px;cursor:pointer;font:600 13px system-ui;" +
      "background:linear-gradient(135deg,#d4af37,#c9a227);color:#111}" +
      ".cf-cms-btn-primary:disabled{opacity:.5;cursor:not-allowed}" +
      ".cf-cms-btn-ghost{padding:10px;border-radius:8px;cursor:pointer;font:500 13px system-ui;" +
      "background:transparent;border:1px solid #4b5563;color:#d1d5db}" +
      ".cf-cms-status{font:400 12px system-ui;padding:8px;border-radius:8px;margin-top:4px}" +
      ".cf-cms-status.ok{background:#064e3b;color:#6ee7b7}" +
      ".cf-cms-status.err{background:#7f1d1d;color:#fca5a5}" +
      ".cf-cms-status.info{background:#1e3a5f;color:#93c5fd}" +
      ".cf-cms-login{padding:8px 0}";
    var style = document.createElement("style");
    style.id = "cf-cms-styles";
    style.textContent = css;
    document.head.appendChild(style);
  }

  var overlay, panel, fab, bodyEl, footerEl, statusEl;

  function setStatus(msg, type) {
    state.statusMsg = msg;
    state.statusType = type || "info";
    if (statusEl) {
      statusEl.textContent = msg;
      statusEl.className = "cf-cms-status " + (type || "info");
      statusEl.style.display = msg ? "block" : "none";
    }
  }

  function openPanel() {
    state.open = true;
    overlay.classList.add("cf-open");
    panel.classList.add("cf-open");
    renderPanelBody();
  }

  function closePanel() {
    state.open = false;
    overlay.classList.remove("cf-open");
    panel.classList.remove("cf-open");
  }

  function renderLogin() {
    bodyEl.innerHTML =
      '<div class="cf-cms-login">' +
      '<p style="font:400 13px system-ui;color:#9ca3af;margin:0 0 12px">' +
      "Connectez-vous avec l'email et le mot de passe définis dans CyberForge.</p>" +
      '<div class="cf-cms-field"><label>Email</label><input type="email" id="cf-cms-email" autocomplete="username" /></div>' +
      '<div class="cf-cms-field"><label>Mot de passe</label><input type="password" id="cf-cms-pass" autocomplete="current-password" /></div>' +
      '<button type="button" class="cf-cms-btn-primary" id="cf-cms-login-btn">Se connecter</button>' +
      "</div>";
    document.getElementById("cf-cms-login-btn").onclick = function () {
      var email = document.getElementById("cf-cms-email").value.trim();
      var password = document.getElementById("cf-cms-pass").value;
      if (!email || !password) {
        setStatus("Email et mot de passe requis.", "err");
        return;
      }
      login(email, password);
    };
  }

  function renderEditors() {
    var domBlocks = collectDomBlocks();
    if (!domBlocks.length) {
      bodyEl.innerHTML =
        '<p style="font:400 13px system-ui;color:#9ca3af">Aucun bloc <code>data-cms</code> détecté sur cette page.</p>';
      return;
    }

    var groups = { text: [], image: [], color: [] };
    domBlocks.forEach(function (b) {
      var t = groups[b.type] ? b.type : "text";
      if (!groups[t]) groups[t] = [];
      groups[t].push(b);
    });

    var html = "";
    ["text", "image", "color"].forEach(function (type) {
      var items = groups[type];
      if (!items || !items.length) return;
      var title = type === "text" ? "Textes" : type === "image" ? "Images" : "Couleurs";
      html += '<div class="cf-cms-section"><h3>' + title + "</h3>";
      items.forEach(function (entry) {
        var id = "cf-cms-" + slugKey(entry.key);
        html += '<div class="cf-cms-field" data-cf-key="' + entry.key + '">';
        html += "<label>" + entry.label + "</label>";
        if (type === "text") {
          var val = readValue(entry);
          var multiline = String(val).length > 80;
          if (multiline) {
            html +=
              '<textarea id="' +
              id +
              '" data-cf-type="text">' +
              escapeHtml(String(val)) +
              "</textarea>";
          } else {
            html +=
              '<input type="text" id="' +
              id +
              '" data-cf-type="text" value="' +
              escapeAttr(String(val)) +
              '" />';
          }
        } else if (type === "image") {
          var imgVal = readValue(entry);
          var url = typeof imgVal === "object" ? imgVal.url : String(imgVal);
          html +=
            '<img class="cf-cms-img-preview" src="' +
            escapeAttr(url) +
            '" alt="" id="' +
            id +
            '-preview" />';
          html +=
            '<input type="text" id="' +
            id +
            '" data-cf-type="image-url" placeholder="URL de l\'image" value="' +
            escapeAttr(url) +
            '" />';
          html +=
            '<button type="button" class="cf-cms-btn-sm" style="margin-top:6px" data-cf-replace="' +
            id +
            '">Remplacer (URL)</button>';
        } else {
          var colorVal = readValue(entry);
          var hex = normalizeHex(String(colorVal));
          html +=
            '<input type="color" id="' +
            id +
            '" data-cf-type="color" value="' +
            escapeAttr(hex) +
            '" />';
        }
        html += "</div>";
      });
      html += "</div>";
    });
    bodyEl.innerHTML = html;

    bodyEl.querySelectorAll(".cf-cms-field").forEach(function (wrap) {
      var key = wrap.getAttribute("data-cf-key");
      var entry = domBlocks.find(function (b) {
        return b.key === key;
      });
      if (!entry) return;
      var input = wrap.querySelector("[data-cf-type]");
      if (!input) return;
      var inputType = input.getAttribute("data-cf-type");
      input.addEventListener("input", function () {
        if (inputType === "text") {
          applyValue(entry, input.value);
        } else if (inputType === "image-url") {
          applyValue(entry, { url: input.value, alt: "" });
          var prev = wrap.querySelector(".cf-cms-img-preview");
          if (prev) prev.setAttribute("src", input.value);
        } else if (inputType === "color") {
          applyValue(entry, input.value);
        }
      });
      var replaceBtn = wrap.querySelector("[data-cf-replace]");
      if (replaceBtn) {
        replaceBtn.addEventListener("click", function () {
          var url = window.prompt("URL de la nouvelle image :", input.value);
          if (url === null) return;
          input.value = url;
          applyValue(entry, { url: url, alt: "" });
          var prev = wrap.querySelector(".cf-cms-img-preview");
          if (prev) prev.setAttribute("src", url);
        });
      }
    });
  }

  function escapeHtml(s) {
    return s
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;");
  }

  function escapeAttr(s) {
    return escapeHtml(s).replace(/'/g, "&#39;");
  }

  function normalizeHex(c) {
    if (/^#[0-9A-Fa-f]{6}$/.test(c)) return c;
    return "#0284c7";
  }

  function renderPanelBody() {
    if (!state.token) {
      renderLogin();
      return;
    }
    renderEditors();
  }

  function buildPatchPayload() {
    return collectDomBlocks().map(function (entry) {
      return {
        block_key: entry.key,
        block_type: entry.type,
        value: readValue(entry),
      };
    });
  }

  function login(email, password) {
    state.busy = true;
    setStatus("Connexion…", "info");
    fetch(state.apiBase + "/cms/login", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ email: email, password: password }),
    })
      .then(function (res) {
        return res.json().then(function (data) {
          return { ok: res.ok, data: data };
        });
      })
      .then(function (result) {
        state.busy = false;
        if (!result.ok || !result.data || !result.data.token) {
          setStatus(
            (result.data && result.data.detail) || "Identifiants invalides.",
            "err"
          );
          return;
        }
        state.token = result.data.token;
        if (result.data.project_id) state.projectId = result.data.project_id;
        setCookie(CMS_TOKEN_COOKIE, state.token, 7);
        setStatus("Connecté.", "ok");
        state.initialSnapshot = takeSnapshot();
        renderPanelBody();
      })
      .catch(function () {
        state.busy = false;
        setStatus("Erreur réseau.", "err");
      });
  }

  function publish() {
    if (!state.token || !state.projectId) {
      setStatus("Projet ou session manquant.", "err");
      return;
    }
    state.busy = true;
    setStatus("Enregistrement…", "info");
    var blocks = buildPatchPayload();
    fetch(state.apiBase + "/cms/" + encodeURIComponent(state.projectId) + "/content", {
      method: "PATCH",
      headers: authHeaders(),
      body: JSON.stringify({ blocks: blocks }),
    })
      .then(function (res) {
        return res.json().then(function (data) {
          return { ok: res.ok, data: data };
        });
      })
      .then(function (patchResult) {
        if (!patchResult.ok) {
          throw new Error(
            (patchResult.data && patchResult.data.detail) || "Sauvegarde impossible."
          );
        }
        setStatus("Publication en cours…", "info");
        return fetch(
          state.apiBase + "/cms/" + encodeURIComponent(state.projectId) + "/publish",
          { method: "POST", headers: authHeaders() }
        );
      })
      .then(function (res) {
        return res.json().then(function (data) {
          return { ok: res.ok, data: data };
        });
      })
      .then(function (pubResult) {
        state.busy = false;
        if (!pubResult.ok) {
          throw new Error(
            (pubResult.data && pubResult.data.detail) || "Publication impossible."
          );
        }
        var jobId = pubResult.data.job_id || pubResult.data.run_id;
        setStatus("Publication en cours — redéploiement du site…", "ok");
        if (jobId) watchPublish(jobId);
        state.initialSnapshot = takeSnapshot();
      })
      .catch(function (err) {
        state.busy = false;
        setStatus(err.message || "Erreur.", "err");
      });
  }

  function watchPublish(jobId) {
    if (!window.EventSource) return;
    var url =
      state.apiBase +
      "/cms/publish/" +
      encodeURIComponent(jobId) +
      "/stream?token=" +
      encodeURIComponent(state.token);
    try {
      var es = new EventSource(url);
      es.onmessage = function (ev) {
        try {
          var payload = JSON.parse(ev.data);
          if (payload.type === "result") {
            setStatus("Site publié avec succès.", "ok");
            es.close();
          } else if (payload.type === "error") {
            setStatus(payload.detail || "Échec publication.", "err");
            es.close();
          } else if (payload.type === "step_done" && payload.message) {
            setStatus(payload.message, payload.ok ? "ok" : "info");
          }
        } catch (e) {
          /* ignore */
        }
      };
      es.onerror = function () {
        es.close();
      };
    } catch (e) {
      /* ignore SSE errors */
    }
  }

  function cancelEdits() {
    restoreSnapshot(state.initialSnapshot);
    setStatus("Modifications annulées.", "info");
    renderPanelBody();
  }

  function mountUi() {
    injectStyles();

    overlay = document.createElement("div");
    overlay.id = "cf-cms-overlay";
    overlay.addEventListener("click", closePanel);

    panel = document.createElement("aside");
    panel.id = "cf-cms-panel";
    panel.setAttribute("aria-label", "Mode édition CyberForge");
    panel.innerHTML =
      '<div class="cf-cms-header">' +
      '<div class="cf-cms-logo">CF</div>' +
      '<span class="cf-cms-title">Mode édition</span>' +
      '<button type="button" class="cf-cms-close" aria-label="Fermer">&times;</button>' +
      "</div>" +
      '<div class="cf-cms-body" id="cf-cms-body"></div>' +
      '<div class="cf-cms-footer" id="cf-cms-footer">' +
      '<div id="cf-cms-status" class="cf-cms-status" style="display:none"></div>' +
      '<button type="button" class="cf-cms-btn-primary" id="cf-cms-publish">Publier les modifications</button>' +
      '<button type="button" class="cf-cms-btn-ghost" id="cf-cms-cancel">Annuler</button>' +
      "</div>";

    fab = document.createElement("button");
    fab.id = "cf-cms-fab";
    fab.type = "button";
    fab.textContent = "✏️ Modifier";
    fab.addEventListener("click", openPanel);

    document.body.appendChild(overlay);
    document.body.appendChild(panel);
    document.body.appendChild(fab);

    bodyEl = document.getElementById("cf-cms-body");
    footerEl = document.getElementById("cf-cms-footer");
    statusEl = document.getElementById("cf-cms-status");

    panel.querySelector(".cf-cms-close").addEventListener("click", closePanel);
    document.getElementById("cf-cms-publish").addEventListener("click", publish);
    document.getElementById("cf-cms-cancel").addEventListener("click", cancelEdits);

    if (state.token) {
      fetch(state.apiBase + "/cms/me", { headers: authHeaders() })
        .then(function (res) {
          if (!res.ok) {
            state.token = "";
            clearCookie(CMS_TOKEN_COOKIE);
            return null;
          }
          return res.json();
        })
        .then(function (me) {
          if (me && me.project_id) state.projectId = me.project_id;
          state.initialSnapshot = takeSnapshot();
        })
        .catch(function () {
          /* ignore */
        });
    }
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", mountUi);
  } else {
    mountUi();
  }
})();
