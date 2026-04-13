// Shared render helpers + DOM utilities.

export const $  = (sel, root = document) => root.querySelector(sel);
export const $$ = (sel, root = document) => Array.from(root.querySelectorAll(sel));

/** Create a DOM element with attrs and children.
 *  h("div", {class: "card"}, [h("h2", {}, ["Title"])])
 */
export function h(tag, attrs = {}, children = []) {
  const el = document.createElement(tag);
  for (const [k, v] of Object.entries(attrs || {})) {
    if (v == null || v === false) continue;
    if (k === "class") el.className = v;
    else if (k === "html") el.innerHTML = v;
    else if (k.startsWith("on") && typeof v === "function") el.addEventListener(k.slice(2), v);
    else if (k === "style" && typeof v === "object") Object.assign(el.style, v);
    else el.setAttribute(k, v);
  }
  const arr = Array.isArray(children) ? children : [children];
  for (const c of arr) {
    if (c == null || c === false) continue;
    el.appendChild(typeof c === "string" ? document.createTextNode(c) : c);
  }
  return el;
}

// --- Icons (inline SVG, 18x18) ---
const ic = (d) =>
  `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round" width="18" height="18">${d}</svg>`;

export const icons = {
  home:       ic('<path d="M3 10.5 12 3l9 7.5V21a1 1 0 0 1-1 1h-5v-7h-6v7H4a1 1 0 0 1-1-1z"/>'),
  track:      ic('<path d="M22 12h-4l-3 9L9 3l-3 9H2"/>'),
  bookmark:   ic('<path d="M19 21l-7-5-7 5V5a2 2 0 0 1 2-2h10a2 2 0 0 1 2 2z"/>'),
  idea:       ic('<path d="M9 21h6M10 17h4M7 13a5 5 0 1 1 10 0c0 2-1 3-1 4H8c0-1-1-2-1-4z"/>'),
  title:      ic('<path d="M4 7h16M4 12h10M4 17h16"/>'),
  thumb:      ic('<rect x="3" y="4" width="18" height="14" rx="2"/><path d="M8 10l4 4 4-4"/>'),
  winner:     ic('<path d="M8 21h8M12 17v4M6 4h12v4a6 6 0 1 1-12 0zM4 4h2v3a3 3 0 0 0 3 3M20 4h-2v3a3 3 0 0 1-3 3"/>'),
  settings:   ic('<circle cx="12" cy="12" r="3"/><path d="M19.4 15a1.65 1.65 0 0 0 .3 1.8l.1.1a2 2 0 1 1-2.8 2.8l-.1-.1a1.65 1.65 0 0 0-1.8-.3 1.65 1.65 0 0 0-1 1.5V21a2 2 0 0 1-4 0v-.1a1.65 1.65 0 0 0-1-1.5 1.65 1.65 0 0 0-1.8.3l-.1.1a2 2 0 1 1-2.8-2.8l.1-.1a1.65 1.65 0 0 0 .3-1.8 1.65 1.65 0 0 0-1.5-1H3a2 2 0 0 1 0-4h.1a1.65 1.65 0 0 0 1.5-1 1.65 1.65 0 0 0-.3-1.8l-.1-.1a2 2 0 1 1 2.8-2.8l.1.1a1.65 1.65 0 0 0 1.8.3h.1a1.65 1.65 0 0 0 1-1.5V3a2 2 0 0 1 4 0v.1a1.65 1.65 0 0 0 1 1.5 1.65 1.65 0 0 0 1.8-.3l.1-.1a2 2 0 1 1 2.8 2.8l-.1.1a1.65 1.65 0 0 0-.3 1.8v.1a1.65 1.65 0 0 0 1.5 1H21a2 2 0 0 1 0 4h-.1a1.65 1.65 0 0 0-1.5 1z"/>'),
  help:       ic('<circle cx="12" cy="12" r="10"/><path d="M9.1 9a3 3 0 0 1 5.8 1c0 2-3 3-3 3M12 17v.01"/>'),
  search:     ic('<circle cx="11" cy="11" r="8"/><path d="M21 21l-4.35-4.35"/>'),
  spark:      ic('<path d="M12 3v3M12 18v3M3 12h3M18 12h3M5.6 5.6l2.1 2.1M16.3 16.3l2.1 2.1M5.6 18.4l2.1-2.1M16.3 7.7l2.1-2.1"/>'),
  plus:       ic('<path d="M12 5v14M5 12h14"/>'),
  x:          ic('<path d="M18 6L6 18M6 6l12 12"/>'),
  sparkle:    ic('<path d="M12 2l2.4 7.6L22 12l-7.6 2.4L12 22l-2.4-7.6L2 12l7.6-2.4z"/>'),
  download:   ic('<path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4M7 10l5 5 5-5M12 15V3"/>'),
  refine:     ic('<path d="M12 20h9M16.5 3.5a2.1 2.1 0 1 1 3 3L7 19l-4 1 1-4z"/>'),
  folder:     ic('<path d="M22 19a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5l2 3h9a2 2 0 0 1 2 2z"/>'),
  bell:       ic('<path d="M6 8a6 6 0 0 1 12 0c0 7 3 9 3 9H3s3-2 3-9M14 21a2 2 0 0 1-4 0"/>'),
  book:       ic('<path d="M4 19.5A2.5 2.5 0 0 1 6.5 17H20M6.5 2H20v20H6.5A2.5 2.5 0 0 1 4 19.5v-15A2.5 2.5 0 0 1 6.5 2z"/>'),
  random:     ic('<polyline points="16 3 21 3 21 8"/><line x1="4" y1="20" x2="21" y2="3"/><polyline points="21 16 21 21 16 21"/><line x1="15" y1="15" x2="21" y2="21"/><line x1="4" y1="4" x2="9" y2="9"/>'),
  filter:     ic('<polygon points="22 3 2 3 10 12.46 10 19 14 21 14 12.46 22 3"/>'),
  trash:      ic('<polyline points="3 6 5 6 21 6"/><path d="M19 6l-1 14a2 2 0 0 1-2 2H8a2 2 0 0 1-2-2L5 6M10 11v6M14 11v6M9 6V4a2 2 0 0 1 2-2h2a2 2 0 0 1 2 2v2"/>'),
  eye:        ic('<path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"/><circle cx="12" cy="12" r="3"/>'),
  check:      ic('<path d="M20 6L9 17l-5-5"/>'),
  copy:       ic('<rect x="9" y="9" width="13" height="13" rx="2"/><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"/>'),
  pin:        ic('<path d="M12 17v5M9 10V3h6v7M5 10h14l-2 7H7z"/>'),
  folderNew:  ic('<path d="M22 19a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5l2 3h9a2 2 0 0 1 2 2zM12 11v6M9 14h6"/>'),
};

// --- Toast ---
export function toast(message, { kind = "default", timeout = 3200 } = {}) {
  let stack = $(".toast-stack");
  if (!stack) {
    stack = h("div", { class: "toast-stack" });
    document.body.appendChild(stack);
  }
  const el = h("div", { class: `toast ${kind}` }, [message]);
  stack.appendChild(el);
  setTimeout(() => {
    el.style.opacity = "0";
    el.style.transform = "translateY(8px)";
    el.style.transition = "opacity 200ms, transform 200ms";
    setTimeout(() => el.remove(), 220);
  }, timeout);
}

// --- Channel picker ---
// Single classy selector matching the 1of10 reference screenshot.
// Searchable list of tracked channels + a "Manage channels" footer.
//
// Usage:
//   const picker = channelPicker({ selected: "UC...", onChange: (id) => {} });
//   picker.getValue();   // current channel_id, or "" if none
//   form.appendChild(picker.el);
export function channelPicker({ items = [], selected = "", onChange } = {}) {
  let value = selected || "";
  let open = false;

  const current = () => items.find((c) => c.channel_id === value);
  const labelFor = (c) => (c ? `@${c.handle || c.name}` : "Select a channel");

  const caret = `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round" width="16" height="16"><polyline points="6 9 12 15 18 9"/></svg>`;

  const trigger = h("button", {
    type: "button", class: "ch-picker-trigger",
    onclick: (e) => { e.stopPropagation(); toggle(); },
  }, [
    h("span", { class: "ch-picker-label" }, [labelFor(current())]),
    h("span", { class: "ch-picker-caret", html: caret }),
  ]);

  const searchInput = h("input", {
    type: "text", class: "ch-picker-search", placeholder: "Search a managed channel…",
  });
  const list = h("div", { class: "ch-picker-list" });
  const manageBtn = h("button", {
    type: "button", class: "ch-picker-manage",
    onclick: () => { window.location.hash = "/trackers"; },
  }, [
    h("span", { class: "ch-picker-manage-icon", html: icons.settings }),
    h("span", {}, ["Manage channels"]),
  ]);

  const menu = h("div", { class: "ch-picker-menu hidden" }, [
    h("div", { class: "ch-picker-search-wrap" }, [
      h("span", { class: "ch-picker-search-icon", html: icons.search }),
      searchInput,
    ]),
    list,
    manageBtn,
  ]);

  const wrap = h("div", { class: "ch-picker" }, [trigger, menu]);

  function renderList() {
    const q = searchInput.value.trim().toLowerCase();
    list.innerHTML = "";
    const filtered = q
      ? items.filter((c) =>
          (c.handle || "").toLowerCase().includes(q) ||
          (c.name || "").toLowerCase().includes(q))
      : items;
    if (!filtered.length) {
      list.appendChild(h("div", { class: "ch-picker-empty" }, ["No channels tracked yet."]));
      return;
    }
    for (const c of filtered) {
      const isActive = c.channel_id === value;
      const row = h("button", {
        type: "button",
        class: `ch-picker-item${isActive ? " active" : ""}`,
        onclick: () => { set(c.channel_id); close(); },
      }, [
        h("span", { class: "ch-picker-item-label" }, [`@${c.handle || c.name}`]),
        isActive && h("span", { class: "ch-picker-item-check", html: icons.check }),
      ].filter(Boolean));
      list.appendChild(row);
    }
  }

  function set(v) {
    value = v;
    trigger.querySelector(".ch-picker-label").textContent = labelFor(current());
    onChange && onChange(value);
    renderList();
  }
  function openMenu() { open = true; menu.classList.remove("hidden"); renderList(); setTimeout(() => searchInput.focus(), 0); }
  function close() { open = false; menu.classList.add("hidden"); }
  function toggle() { open ? close() : openMenu(); }

  searchInput.addEventListener("input", renderList);
  document.addEventListener("click", (e) => { if (open && !wrap.contains(e.target)) close(); });

  renderList();

  return {
    el: wrap,
    getValue: () => value,
    setItems: (next) => { items = next; renderList(); },
  };
}

// --- Modal ---
export function modal({ title, body, confirmText = "Confirm", onConfirm, onCancel }) {
  const close = () => backdrop.remove();
  const backdrop = h("div", { class: "modal-backdrop", onclick: (e) => { if (e.target === backdrop) close(); } });
  const inputs = typeof body === "function" ? body() : null;
  const modalEl = h("div", { class: "modal" }, [
    h("div", { class: "modal-title" }, [title]),
    h("div", { class: "modal-body" }, [
      typeof body === "string" ? body : (inputs || ""),
    ]),
    h("div", { class: "modal-actions" }, [
      h("button", { class: "btn ghost", onclick: () => { close(); onCancel && onCancel(); } }, ["Cancel"]),
      h("button", { class: "btn primary", onclick: () => {
        const ok = onConfirm && onConfirm(modalEl);
        if (ok !== false) close();
      }}, [confirmText]),
    ]),
  ]);
  backdrop.appendChild(modalEl);
  document.body.appendChild(backdrop);
  return backdrop;
}

// --- Thumbnail card ---
export function thumbCard(item, {
  onClick, onBookmark, onUseAsReference, showActions = true,
} = {}) {
  const score = item.outlier_score || 0;
  const badge = score >= 5 ? "high" : "";
  const views = formatViews(item.views);

  const el = h("div", { class: "thumb-card", onclick: () => onClick && onClick(item) }, [
    h("div", { class: `outlier-badge ${badge}` }, [`${score.toFixed(1)}x`]),
    showActions && h("div", { class: "thumb-actions" }, [
      onBookmark && h("button", { class: "icon-btn", title: "Bookmark", onclick: (e) => { e.stopPropagation(); onBookmark(item); }, html: icons.bookmark }),
      onUseAsReference && h("button", { class: "icon-btn", title: "Use as reference", onclick: (e) => { e.stopPropagation(); onUseAsReference(item); }, html: icons.spark }),
    ].filter(Boolean)),
    h("img", { class: "thumb-img", src: item.thumb_url || "", loading: "lazy", alt: item.title || "" }),
    h("div", { class: "thumb-meta" }, [
      h("div", { class: "thumb-title" }, [item.title || "—"]),
      h("div", { class: "thumb-sub" }, [
        item.channel_name || "Unknown channel",
        " · ",
        views,
      ]),
    ]),
  ]);
  return el;
}

// --- Empty state ---
export function emptyState({ iconHtml, title, body, action }) {
  return h("div", { class: "empty" }, [
    h("div", { class: "empty-icon", html: iconHtml || icons.sparkle }),
    h("div", { class: "empty-title" }, [title]),
    body && h("div", { class: "empty-body" }, [body]),
    action && h("div", {}, [action]),
  ].filter(Boolean));
}

// --- Page header ---
export function pageHeader({ kicker, title, subtitle, action }) {
  return h("header", { class: "page-header flex between center wrap gap-4" }, [
    h("div", {}, [
      kicker && h("div", { class: "page-kicker" }, [kicker]),
      h("h1", { class: "page-title" }, [title]),
      subtitle && h("div", { class: "page-subtitle" }, [subtitle]),
    ].filter(Boolean)),
    action,
  ].filter(Boolean));
}

// --- Formatters ---
export function formatViews(n) {
  if (!n) return "0 views";
  if (n >= 1_000_000) return (n / 1_000_000).toFixed(1).replace(/\.0$/, "") + "M views";
  if (n >= 1_000) return (n / 1_000).toFixed(1).replace(/\.0$/, "") + "K views";
  return `${n} views`;
}

export function formatRelative(isoString) {
  if (!isoString) return "";
  const t = new Date(isoString).getTime();
  const d = Date.now() - t;
  const day = 86400_000;
  if (d < 3600_000) return Math.max(1, Math.floor(d / 60_000)) + "m ago";
  if (d < day) return Math.floor(d / 3600_000) + "h ago";
  if (d < day * 14) return Math.floor(d / day) + "d ago";
  if (d < day * 60) return Math.floor(d / (day * 7)) + "w ago";
  if (d < day * 365) return Math.floor(d / (day * 30)) + "mo ago";
  return Math.floor(d / (day * 365)) + "y ago";
}

export function groupByDate(rows, getDate = (r) => r.created_at) {
  const groups = {};
  for (const r of rows) {
    const d = (getDate(r) || "").slice(0, 10) || "—";
    (groups[d] ||= []).push(r);
  }
  return Object.entries(groups).sort((a, b) => (a[0] < b[0] ? 1 : -1));
}

export function copyToClipboard(text) {
  navigator.clipboard.writeText(text).then(
    () => toast("Copied to clipboard", { kind: "success", timeout: 1500 }),
    () => toast("Copy failed", { kind: "error" }),
  );
}

export function pickFolder(folders, onPick) {
  return modal({
    title: "Save to folder",
    body: () => {
      const wrap = h("div", { class: "flex flex-col gap-2" });
      for (const f of folders) {
        wrap.appendChild(h("button", {
          class: "chip",
          style: { justifyContent: "flex-start", width: "100%" },
          onclick: () => {
            onPick(f.id);
            wrap.closest(".modal-backdrop").remove();
          },
        }, [
          h("span", { style: { width: "8px", height: "8px", borderRadius: "50%", background: f.color, display: "inline-block" } }),
          h("span", {}, [f.name]),
          h("span", { class: "caption", style: { marginLeft: "auto" } }, [`${f.item_count} items`]),
        ]));
      }
      if (!folders.length) wrap.appendChild(h("div", { class: "caption" }, ["No folders yet. Create one from Bookmarks."]));
      return wrap;
    },
    confirmText: "Cancel",
    onConfirm: () => true,
  });
}
