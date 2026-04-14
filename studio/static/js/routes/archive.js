// Archive — unified history of every idea / title / thumbnail generation.
// Each entry shows: input, channel, when, and the full output.

import { api } from "../api.js";
import { h, icons, toast, formatRelative, copyToClipboard } from "../components.js";
import { navigate } from "../router.js";

export async function mount(outlet) {
  outlet.appendChild(h("div", { class: "page-center" }, [
    h("h1", { class: "page-title" }, ["Archive"]),
    h("div", { class: "page-subtitle" }, ["Every generation you've run — ideas, titles, thumbnails — with the exact inputs, channel, and timestamps. Nothing is ever lost."]),
  ]));

  // Load trackers once so we can resolve channel IDs into clean @handles
  let channelLookup = {};
  try {
    const tr = (await api.trackers()).items || [];
    for (const t of tr) {
      const pretty = t.handle ? `@${t.handle}` : (t.name || "");
      channelLookup[t.channel_id] = pretty;
      if (t.handle) channelLookup[t.handle] = `@${t.handle}`;
    }
  } catch { /* offline is fine, fallback handles it */ }

  // Tab bar
  const TABS = [
    { key: "thumbnails", label: "Thumbnails" },
    { key: "titles",     label: "Titles" },
    { key: "ideas",      label: "Ideas" },
  ];
  const tabBar = h("div", { class: "archive-tabs" });
  const content = h("div", { class: "archive-content" });

  outlet.appendChild(tabBar);
  outlet.appendChild(content);

  let activeTab = "thumbnails";
  function renderTabs() {
    tabBar.innerHTML = "";
    for (const t of TABS) {
      const btn = h("button", {
        class: `archive-tab${t.key === activeTab ? " active" : ""}`,
        onclick: () => { activeTab = t.key; renderTabs(); renderTab(); },
      }, [t.label]);
      tabBar.appendChild(btn);
    }
  }

  async function renderTab() {
    content.innerHTML = "";
    content.appendChild(h("div", { class: "archive-loading" }, [
      h("span", { class: "spinner-ink" }),
      h("span", {}, ["Loading archive…"]),
    ]));
    try {
      if (activeTab === "ideas")      await renderIdeas();
      if (activeTab === "titles")     await renderTitles();
      if (activeTab === "thumbnails") await renderThumbnails();
    } catch (e) {
      content.innerHTML = "";
      content.appendChild(h("div", { class: "archive-empty" }, [`Failed to load: ${e.message}`]));
    }
  }

  renderTabs();
  renderTab();

  // ── Ideas ────────────────────────────────────────────────
  async function renderIdeas() {
    const r = await api.ideasHistory();
    content.innerHTML = "";
    if (!r.items?.length) {
      content.appendChild(emptyState("No ideas generated yet."));
      return;
    }
    // Group by batch_id
    const byBatch = {};
    for (const row of r.items) (byBatch[row.batch_id] ||= []).push(row);
    const batches = Object.values(byBatch).sort((a, b) =>
      b[0].created_at.localeCompare(a[0].created_at),
    );
    for (const rows of batches) content.appendChild(ideaBatchCard(rows));
  }

  function buildCardHead({ type, channel, input, inputLabel, count, createdAt }) {
    const channelPretty = prettyChannel(channel);
    return h("div", { class: "archive-card-head" }, [
      h("div", { class: "archive-card-head-top" }, [
        h("div", { class: "archive-card-type" }, [type]),
        h("div", { class: "archive-card-time" }, [
          h("span", { class: "archive-card-time-rel" }, [formatRelative(createdAt)]),
          h("span", { class: "archive-card-time-abs" }, [formatAbs(createdAt)]),
        ]),
      ]),
      h("div", { class: "archive-card-head-body" }, [
        h("div", { class: "archive-kv" }, [
          h("div", { class: "archive-kv-label" }, ["Channel"]),
          h("div", { class: "archive-kv-value channel" }, [channelPretty]),
        ]),
        input && h("div", { class: "archive-kv" }, [
          h("div", { class: "archive-kv-label" }, [inputLabel || "Input"]),
          h("div", { class: "archive-kv-value" }, [input]),
        ]),
        count && h("div", { class: "archive-kv" }, [
          h("div", { class: "archive-kv-label" }, ["Result"]),
          h("div", { class: "archive-kv-value" }, [count]),
        ]),
      ].filter(Boolean)),
    ]);
  }

  function ideaBatchCard(rows) {
    const first = rows[0];
    const head = buildCardHead({
      type: "Idea batch",
      channel: first.channel,
      input: first.topic || "—",
      inputLabel: "Topic",
      count: `${rows.length} ${rows.length === 1 ? "idea" : "ideas"}`,
      createdAt: first.created_at,
    });

    const list = h("div", { class: "archive-inline-list" });
    for (const r of rows) {
      list.appendChild(h("div", { class: "archive-inline-row" }, [
        h("div", { class: "archive-inline-text" }, [
          h("div", { class: "archive-inline-title" }, [r.idea_title || r.title || "—"]),
          (r.idea_description || r.description) && h("div", { class: "archive-inline-sub" }, [r.idea_description || r.description]),
        ].filter(Boolean)),
        h("div", { class: "archive-inline-actions" }, [
          h("button", {
            class: "btn ghost sm",
            onclick: () => navigate("/titles", { prefill_idea: r.idea_title || r.title, channel: r.channel }),
          }, ["→ Titles"]),
          h("button", {
            class: "btn sm primary",
            onclick: () => navigate("/thumbnails", { prefill_title: r.idea_title || r.title, channel: r.channel }),
          }, ["→ Thumbnail"]),
        ]),
      ]));
    }

    return h("div", { class: "archive-card" }, [head, list]);
  }

  // ── Titles ───────────────────────────────────────────────
  async function renderTitles() {
    const r = await api.titlesHistory();
    content.innerHTML = "";
    if (!r.items?.length) {
      content.appendChild(emptyState("No titles generated yet."));
      return;
    }
    const byBatch = {};
    for (const row of r.items) (byBatch[row.batch_id] ||= []).push(row);
    const batches = Object.values(byBatch).sort((a, b) =>
      b[0].created_at.localeCompare(a[0].created_at),
    );
    for (const rows of batches) content.appendChild(titleBatchCard(rows));
  }

  function titleBatchCard(rows) {
    const first = rows[0];
    const head = buildCardHead({
      type: "Title batch",
      channel: first.channel,
      input: clip(first.source_idea, 120),
      inputLabel: "Idea",
      count: `${rows.length} ${rows.length === 1 ? "title" : "titles"}`,
      createdAt: first.created_at,
    });

    // Split by source if present (channel vs outlier)
    const bySource = { channel: [], outlier: [], _: [] };
    for (const r of rows) (bySource[r.source || "_"] ||= []).push(r);

    const cols = h("div", { class: "archive-title-cols" });
    if (bySource.channel?.length || bySource.outlier?.length) {
      if (bySource.channel?.length) cols.appendChild(titleCol("From the channel's voice", bySource.channel));
      if (bySource.outlier?.length) cols.appendChild(titleCol("From outlier formulas", bySource.outlier));
    } else {
      cols.appendChild(titleCol("All titles", rows));
    }

    return h("div", { class: "archive-card" }, [head, cols]);
  }

  function titleCol(heading, rows) {
    const col = h("div", { class: "archive-title-col" }, [
      h("div", { class: "archive-title-col-head" }, [heading]),
    ]);
    const list = h("div", { class: "archive-inline-list" });
    for (const r of rows) {
      list.appendChild(h("div", { class: "archive-inline-row" }, [
        h("div", { class: "archive-inline-text" }, [
          h("div", { class: "archive-inline-title" }, [r.title]),
          h("div", { class: "archive-inline-sub" }, [`${r.char_count} characters`]),
        ]),
        h("div", { class: "archive-inline-actions" }, [
          h("button", {
            class: "btn ghost sm", html: `${icons.copy}`,
            title: "Copy title",
            onclick: () => copyToClipboard(r.title),
          }),
          h("button", {
            class: "btn sm primary",
            onclick: () => navigate("/thumbnails", { prefill_title: r.title, channel: r.channel }),
          }, ["→ Thumbnail"]),
        ]),
      ]));
    }
    col.appendChild(list);
    return col;
  }

  // ── Thumbnails ───────────────────────────────────────────
  async function renderThumbnails() {
    const r = await api.thumbnailsHistory();
    content.innerHTML = "";
    if (!r.items?.length) {
      content.appendChild(emptyState("No thumbnails generated yet."));
      return;
    }
    // Group by (title + created_at minute bucket) as a proxy for a generation session
    const groups = {};
    for (const row of r.items) {
      const bucket = `${row.title || ""}::${(row.created_at || "").slice(0, 16)}`;
      (groups[bucket] ||= []).push(row);
    }
    const sorted = Object.values(groups).sort((a, b) =>
      (b[0].created_at || "").localeCompare(a[0].created_at || ""),
    );
    for (const rows of sorted) content.appendChild(thumbBatchCard(rows));
  }

  function thumbBatchCard(rows) {
    const first = rows[0];
    const head = buildCardHead({
      type: "Thumbnail generation",
      channel: first.channel || first.niche,
      input: clip(first.title || "—", 120),
      inputLabel: "Title",
      count: `${rows.length} ${rows.length === 1 ? "thumbnail" : "thumbnails"}`,
      createdAt: first.created_at,
    });

    const grid = h("div", { class: "archive-thumb-grid" });
    for (const r of rows) {
      const img = h("img", {
        class: "archive-thumb-img",
        src: r.url, alt: "", loading: "lazy",
      });
      const tile = h("div", { class: "archive-thumb-tile" }, [img]);
      img.addEventListener("click", () => navigate("/thumbnails", {
        prefill_title: first.title, channel: first.channel,
      }));
      grid.appendChild(tile);
    }

    const regenBtn = h("button", {
      class: "btn primary sm archive-regen-btn",
      onclick: () => navigate("/thumbnails", {
        prefill_title: first.title, channel: first.channel,
      }),
    }, [
      h("span", { class: "icon", html: icons.refine }),
      h("span", {}, ["Regenerate in Thumbnail Generator"]),
    ]);

    return h("div", { class: "archive-card" }, [
      head,
      h("div", { class: "archive-card-body" }, [regenBtn, grid]),
    ]);
  }

  // ── Helpers ──────────────────────────────────────────────
  function emptyState(msg) {
    return h("div", { class: "archive-empty" }, [
      h("div", { class: "archive-empty-icon", html: icons.sparkle }),
      h("div", {}, [msg]),
    ]);
  }
  function clip(s, n) { s = String(s || ""); return s.length > n ? s.slice(0, n - 1) + "…" : s; }
  function prettyChannel(c) {
    if (!c) return "Unknown channel";
    if (channelLookup[c]) return channelLookup[c];
    if (typeof c === "string" && c.startsWith("@")) return c;
    if (typeof c === "string" && c.startsWith("UC")) {
      // Unresolved channel ID — show a friendly placeholder instead of raw ID
      return "Unknown channel";
    }
    return c;
  }
  function formatAbs(iso) {
    if (!iso) return "";
    try {
      const d = new Date(iso);
      return d.toLocaleString(undefined, {
        year: "numeric", month: "short", day: "numeric",
        hour: "2-digit", minute: "2-digit",
      });
    } catch { return iso; }
  }
}
