"""
Interactions des templates app_* — modals CRUD, tri, navigation sidebar.
Injecté après ContentAI pour application_web.
"""

from __future__ import annotations

import re

_CF_APP_UI_SCRIPT = """
<script id="cf-app-ui">
(function () {
  function qs(sel, root) {
    return (root || document).querySelector(sel);
  }
  function qsa(sel, root) {
    return Array.prototype.slice.call((root || document).querySelectorAll(sel));
  }

  function showSection(id) {
    qsa("[data-cf-section]").forEach(function (sec) {
      var on = sec.getAttribute("data-cf-section") === id;
      sec.style.display = on ? "" : "none";
      sec.classList.toggle("cf-section-active", on);
    });
    qsa(".cf-nav-link, .sidebar-nav a[data-cf-section]").forEach(function (a) {
      var target = a.getAttribute("data-cf-section") || "";
      a.classList.toggle("active", target === id);
    });
  }

  qsa(".cf-nav-link, .sidebar-nav a[data-cf-section]").forEach(function (a) {
    a.addEventListener("click", function (ev) {
      var id = a.getAttribute("data-cf-section");
      if (!id) {
        return;
      }
      ev.preventDefault();
      showSection(id);
    });
  });

  var firstNav = qs(".cf-nav-link[data-cf-section], .sidebar-nav a[data-cf-section]");
  if (firstNav) {
    showSection(firstNav.getAttribute("data-cf-section"));
  }

  var modal = qs("#modalOverlay") || qs("#modalBg");
  var form = qs("#modalForm") || qs("#mForm");
  var tbody = qs("#tableBody") || qs("#tbody");
  if (!modal || !form || !tbody) {
    return;
  }

  var editId = qs("#editId") || qs("#eid");
  var f1 = qs("#fCol1") || qs("#c1");
  var f2 = qs("#fCol2") || qs("#c2");
  var f3 = qs("#fCol3") || qs("#c3");
  var titleEl = qs("#modalTitle") || qs("#mTitle");
  var nextId = 100;

  function cellText(td) {
    if (!td) {
      return "";
    }
    return (td.innerText || td.textContent || "").trim();
  }

  function openModal(title, row) {
    if (titleEl) {
      titleEl.textContent = title;
    }
    if (row) {
      editId.value = row.getAttribute("data-id") || "";
      if (f1) {
        f1.value = cellText(row.cells[0]);
      }
      if (f2) {
        f2.value = cellText(row.cells[1]);
      }
      if (f3) {
        f3.value = cellText(row.cells[2]);
      }
    } else {
      editId.value = "";
      form.reset();
    }
    modal.classList.add("open");
    if (modal.id === "modalBg") {
      modal.classList.add("show");
    }
  }

  function closeModal() {
    modal.classList.remove("open", "show");
  }

  var btnAdd = qs("#btnAdd") || qs("#addBtn");
  if (btnAdd) {
    btnAdd.addEventListener("click", function () {
      openModal(btnAdd.getAttribute("data-cf-add-label") || "Nouveau");
    });
  }

  var btnCancel = qs("#modalCancel") || qs("#cancel");
  if (btnCancel) {
    btnCancel.addEventListener("click", closeModal);
  }
  modal.addEventListener("click", function (e) {
    if (e.target === modal) {
      closeModal();
    }
  });

  form.addEventListener("submit", function (e) {
    e.preventDefault();
    var v1 = f1 ? f1.value : "";
    var v2 = f2 ? f2.value : "";
    var v3 = f3 ? f3.value : "";
    var id = editId ? editId.value : "";
    if (id) {
      var row = tbody.querySelector('tr[data-id="' + id + '"]');
      if (row) {
        row.cells[0].textContent = v1;
        if (row.cells[1].querySelector(".badge")) {
          row.cells[1].innerHTML = '<span class="badge">' + v2 + "</span>";
        } else {
          row.cells[1].textContent = v2;
        }
        row.cells[2].textContent = v3;
      }
    } else {
      var tr = document.createElement("tr");
      tr.setAttribute("data-id", String(nextId++));
      var useBadge = /CRM/i.test(document.title || "");
      var col2 = useBadge ? '<span class="badge">' + v2 + "</span>" : v2;
      tr.innerHTML =
        "<td>" +
        v1 +
        "</td><td>" +
        col2 +
        "</td><td>" +
        v3 +
        '</td><td class="actions"><button type="button" class="cf-edit-row edit-row edit">Modifier</button> <button type="button" class="cf-del-row del-row">Supprimer</button></td>';
      tbody.appendChild(tr);
    }
    closeModal();
  });

  tbody.addEventListener("click", function (e) {
    var t = e.target;
    if (!t || !t.closest) {
      return;
    }
    var editBtn = t.closest(".cf-edit-row, .edit-row, .edit");
    if (editBtn) {
      e.preventDefault();
      openModal("Modifier", editBtn.closest("tr"));
      return;
    }
    var delBtn = t.closest(".cf-del-row, .del-row");
    if (delBtn) {
      e.preventDefault();
      var row = delBtn.closest("tr");
      if (row && confirm("Supprimer cette ligne ?")) {
        row.remove();
      }
    }
  });

  var sortCol = -1;
  var sortDir = 1;
  qsa("#dataTable th[data-col], #tbl th[data-c], #dataTable th[data-c]").forEach(
    function (th) {
      th.addEventListener("click", function () {
        var col = parseInt(
          th.getAttribute("data-col") || th.getAttribute("data-c") || "0",
          10
        );
        sortDir = sortCol === col ? -sortDir : 1;
        sortCol = col;
        qsa("#dataTable th, #tbl th").forEach(function (h) {
          h.classList.remove("sorted-asc", "sorted-desc");
        });
        th.classList.add(sortDir === 1 ? "sorted-asc" : "sorted-desc");
        var rows = qsa("tr", tbody);
        rows.sort(function (a, b) {
          var av = cellText(a.cells[col]);
          var bv = cellText(b.cells[col]);
          var an = parseFloat(av.replace(/[^\\d.,]/g, "").replace(",", "."));
          var bn = parseFloat(bv.replace(/[^\\d.,]/g, "").replace(",", "."));
          if (!isNaN(an) && !isNaN(bn)) {
            return sortDir * (an - bn);
          }
          return sortDir * av.localeCompare(bv, "fr");
        });
        rows.forEach(function (r) {
          tbody.appendChild(r);
        });
      });
    }
  );

  var menuToggle = qs("#menuToggle") || qs("#burger");
  var sidebar = qs("#sidebar");
  var overlay = qs("#sidebarOverlay") || qs("#overlay");
  if (menuToggle && sidebar) {
    menuToggle.addEventListener("click", function () {
      sidebar.classList.toggle("open");
      if (overlay) {
        overlay.classList.toggle("open");
        overlay.classList.toggle("show");
      }
    });
  }
  if (overlay && sidebar) {
    overlay.addEventListener("click", function () {
      sidebar.classList.remove("open");
      overlay.classList.remove("open", "show");
    });
  }
  var notif = qs("#notifBtn") || qs("#notifs");
  if (notif) {
    notif.addEventListener("click", function () {
      alert("Notifications (démo interactive)");
    });
  }
})();
</script>
"""

_SECTION_STYLE = """
<style id="cf-app-sections">
[data-cf-section] { display: none; }
[data-cf-section].cf-section-active { display: block; }
</style>
"""


def enhance_app_template_html(html: str) -> str:
    """Ajoute styles sections + script interactions (idempotent)."""
    if not html or "product-card" in html:
        return html
    out = html
    if 'id="cf-app-sections"' not in out:
        if re.search(r"</head>", out, re.I):
            out = re.sub(
                r"</head>",
                lambda _m: _SECTION_STYLE + "\n</head>",
                out,
                count=1,
                flags=re.I,
            )
        else:
            out = _SECTION_STYLE + out
    if 'id="cf-app-ui"' not in out:
        if re.search(r"</body>", out, re.I):
            out = re.sub(
                r"</body>",
                lambda _m: _CF_APP_UI_SCRIPT + "\n</body>",
                out,
                count=1,
                flags=re.I,
            )
        else:
            out += _CF_APP_UI_SCRIPT
    return out
