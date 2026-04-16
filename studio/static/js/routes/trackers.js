// Manage channels — matches the user's reference screenshot.

import { api } from "../api.js";
import { h, icons, toast, formatRelative, $ } from "../components.js";
import { streamJob } from "../lib/sse.js";

const PERSON_PLUS_ICON = `
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64" fill="none"
     stroke="#6b7280" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round"
     width="64" height="64">
  <circle cx="26" cy="20" r="10"/>
  <path d="M10 54c0-8.8 7.2-16 16-16s16 7.2 16 16"/>
  <path d="M46 14v14M39 21h14"/>
</svg>`;

export async function mount(outlet) {
  // Track active scan streams so we can abort them on navigation
  const activeAborts = new Set();

  outlet.appendChild(h("header", { class: "page-header" }, [
    h("h1", { class: "page-title" }, ["Manage channels"]),
    h("div", { class: "page-subtitle" }, ["Connect your YouTube channels."]),
  ]));

  // Hero add-card (centered)
  const input = h("input", { type: "text", placeholder: "@handle", id: "addHandle" });
  const addBtn = h("button", { class: "btn primary", html: `${icons.plus}<span>Add</span>` });

  const addCard = h("section", { class: "card hero", style: { marginBottom: "48px" } }, [
    h("div", { style: { color: "var(--ink-500)", display: "flex", justifyContent: "center", marginBottom: "16px" }, html: PERSON_PLUS_ICON }),
    h("div", { class: "display-s", style: { color: "var(--ink-600)", fontWeight: 500, marginBottom: "8px" } }, ["Add your channel handle. (e.g. @DigitalCrimeScene1)"]),
    h("div", { class: "caption", style: { marginBottom: "24px" } }, ["Unlimited channels. Added locally — no SaaS limits."]),
    h("div", { style: { display: "flex", justifyContent: "center" } }, [
      h("div", { class: "pill-input", style: { width: "min(560px, 100%)" } }, [
        h("span", { class: "pi-icon", html: icons.idea.replace("width=\"18\" height=\"18\"", "width=\"18\" height=\"18\"") }),
        input,
        addBtn,
      ]),
    ]),
  ]);
  outlet.appendChild(addCard);

  // Table
  const tableWrap = h("div", { id: "table-wrap" });
  outlet.appendChild(tableWrap);

  async function refresh() {
    if (!outlet.isConnected) return;
    const { items } = await api.trackers();
    if (!outlet.isConnected) return;
    tableWrap.innerHTML = "";
    if (!items.length) {
      tableWrap.appendChild(h("div", { class: "empty" }, [
        h("div", { class: "empty-icon", html: icons.track }),
        h("div", { class: "empty-title" }, ["No channels tracked yet"]),
        h("div", { class: "empty-body" }, ["Add a YouTube handle above to start building your style reference library."]),
      ]));
      return;
    }

    const table = h("table", { class: "data-table" }, [
      h("thead", {}, [
        h("tr", {}, [
          h("th", {}, ["Channel"]),
          h("th", {}, ["Status"]),
          h("th", {}, ["About"]),
          h("th", {}, ["Date added"]),
          h("th", { style: { width: "48px" } }, [""]),
        ]),
      ]),
      h("tbody", {}, items.map(rowFor)),
    ]);
    tableWrap.appendChild(table);
  }

  function rowFor(row) {
    const initial = (row.name || row.handle || "?").charAt(0).toUpperCase();
    const avatar = row.avatar_url
      ? h("div", { class: "ch-avatar" }, [h("img", { src: row.avatar_url, alt: "" })])
      : h("div", { class: "ch-avatar" }, [initial]);

    const chCell = h("td", {}, [
      h("div", { class: "ch-cell" }, [
        avatar,
        h("div", {}, [
          h("div", { style: { display: "flex", alignItems: "center", gap: "8px" } }, [
            h("span", { class: "ch-handle" }, [row.handle ? `@${row.handle}` : row.name]),
            row.is_default && h("span", { class: "pill default" }, ["Default Channel"]),
          ].filter(Boolean)),
          h("div", { class: "ch-sub" }, [
            row.name && row.name !== row.handle ? row.name : "",
            row.subs ? `  ·  ${row.subs.toLocaleString()} subs` : "",
          ]),
        ]),
      ]),
    ]);

    const statusCell = h("td", {}, [h("span", { class: "pill active" }, ["Active"])]);

    const aiSummary = (row.ai_summary || "").trim();
    const rawDesc = (row.description || "").trim();
    let aboutContent;
    if (aiSummary) {
      aboutContent = h("div", {}, [
        h("div", { class: "about-cell" }, [aiSummary]),
        h("div", { style: { marginTop: "6px", display: "flex", alignItems: "center", gap: "6px" } }, [
          h("span", { class: "badge neutral", html: `${icons.sparkle}<span style="margin-left:4px">AI-generated</span>` }),
        ]),
      ]);
    } else if (rawDesc) {
      aboutContent = h("div", { class: "about-cell" }, [rawDesc.slice(0, 360)]);
    } else {
      aboutContent = h("div", { class: "about-cell" }, [
        h("span", { class: "muted", style: { fontStyle: "italic" } }, ["Generating smart summary…"]),
      ]);
    }
    const aboutCell = h("td", {}, [aboutContent]);

    const dateCell = h("td", {}, [h("div", { class: "date-cell" }, [formatDate(row.added_at)])]);

    const menuCell = h("td", {}, [
      h("div", { class: "menu-dots", onclick: (e) => openMenu(e, row), html: '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="currentColor" width="18" height="18"><circle cx="12" cy="5" r="2"/><circle cx="12" cy="12" r="2"/><circle cx="12" cy="19" r="2"/></svg>' }),
    ]);

    return h("tr", {}, [chCell, statusCell, aboutCell, dateCell, menuCell]);
  }

  function openMenu(event, row) {
    event.stopPropagation();
    // simple drop-in popover
    const existing = document.querySelector(".row-menu");
    if (existing) existing.remove();

    const menu = h("div", { class: "row-menu", style: {
      position: "absolute", zIndex: 50, right: "48px", background: "white",
      border: "1px solid var(--line)", borderRadius: "10px",
      boxShadow: "var(--shadow-3)", padding: "6px", display: "flex", flexDirection: "column", minWidth: "200px",
    }});
    const addItem = (label, onclick) => {
      menu.appendChild(h("button", {
        onclick, class: "btn ghost sm",
        style: { justifyContent: "flex-start", padding: "8px 10px", textAlign: "left" },
      }, [label]));
    };
    addItem(row.is_default ? "Already default" : "Set as default", async () => {
      menu.remove();
      if (!row.is_default) { await api.trackerSetDefault(row.channel_id); refresh(); }
    });
    addItem("Regenerate AI summary", async () => {
      menu.remove();
      toast("Regenerating summary…");
      const r = await api.trackerResummarize(row.channel_id);
      if (r.ai_summary) { toast("Summary refreshed", { kind: "success" }); refresh(); }
      else toast("Summary could not be generated", { kind: "error" });
    });
    addItem("Scan for outliers", async () => {
      menu.remove();
      const { job_id, error } = await api.trackerRefresh(row.channel_id);
      if (error) return toast(error, { kind: "error" });
      toast(`Scanning ${row.handle || row.name}…`);
      const abort = new AbortController();
      activeAborts.add(abort);
      streamJob(`/api/trackers/scan/${job_id}`, { onMessage: (d) => d.msg && toast(d.msg), signal: abort.signal })
        .then((r) => { activeAborts.delete(abort); toast(`${r?.outliers ?? 0} outliers cached`, { kind: "success" }); })
        .catch(() => { activeAborts.delete(abort); if (!abort.signal.aborted) toast("Scan failed", { kind: "error" }); });
    });
    addItem("Remove", async () => {
      menu.remove();
      if (!confirm(`Remove @${row.handle || row.name}?`)) return;
      await api.trackerRemove(row.channel_id);
      refresh();
    });

    document.body.appendChild(menu);
    const rect = event.currentTarget.getBoundingClientRect();
    menu.style.top = `${rect.bottom + window.scrollY + 4}px`;
    menu.style.left = `${rect.right + window.scrollX - 200}px`;

    const closer = (ev) => {
      if (!menu.contains(ev.target)) { menu.remove(); document.removeEventListener("click", closer); }
    };
    setTimeout(() => document.addEventListener("click", closer), 0);
  }

  addBtn.addEventListener("click", submit);
  input.addEventListener("keydown", (e) => { if (e.key === "Enter") submit(); });

  async function submit() {
    const handle = input.value.trim();
    if (!handle) return toast("Type a @handle or URL", { kind: "error" });
    addBtn.disabled = true;
    addBtn.innerHTML = `${icons.sparkle}<span>Adding…</span>`;

    let addedItem = null;
    try {
      const r = await api.trackerAdd(handle);
      if (r.error) { toast(r.error, { kind: "error" }); return; }
      addedItem = r.item;
      toast(`Added ${r.item.name || r.item.handle}`, { kind: "success" });
      input.value = "";
      refresh();
    } catch (e) {
      toast(e.message, { kind: "error" });
    } finally {
      addBtn.disabled = false;
      addBtn.innerHTML = `${icons.plus}<span>Add</span>`;
    }

    // Background scan — completely detached, never surfaces an error toast
    if (!addedItem) return;
    try {
      const sc = await api.trackerRefresh(addedItem.channel_id);
      if (sc?.job_id) {
        const abort = new AbortController();
        activeAborts.add(abort);
        streamJob(`/api/trackers/scan/${sc.job_id}`, {
          onMessage: (d) => d.msg && console.info("[scan]", d.msg),
          signal: abort.signal,
        }).then((res) => {
          activeAborts.delete(abort);
          if (!abort.signal.aborted)
            toast(`${res?.outliers ?? 0} outliers indexed for @${addedItem.handle || addedItem.name}`, { kind: "success" });
        }).catch(() => { activeAborts.delete(abort); });
      }
    } catch { /* scan kick-off failure is non-fatal — never surface to user */ }
  }

  refresh();

  return function unmount() {
    for (const abort of activeAborts) abort.abort();
    activeAborts.clear();
  };
}

function formatDate(iso) {
  if (!iso) return "—";
  const d = new Date(iso);
  return d.toLocaleDateString("en-US", { weekday: "short", month: "short", day: "2-digit", year: "numeric" });
}
