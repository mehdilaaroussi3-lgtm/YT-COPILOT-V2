// Smart Finds — persistent history of every Smart Find search.
// Each entry is a block card with inline thumbnail preview strip + overlay for full browse.

import { api } from "../api.js";
import { h, icons, thumbCard, pageHeader, toast, pickFolder } from "../components.js";
import { navigate } from "../router.js";

export async function mount(outlet) {
  outlet.appendChild(pageHeader({
    kicker: "Smart Find",
    title: "Smart Find History",
    subtitle: "Every channel search you've run. Click any block to browse its thumbnails.",
  }));

  const grid = h("div", { class: "sf-blocks-grid", id: "sf-content" });
  outlet.appendChild(grid);

  await render(grid);
}

async function render(grid) {
  grid.innerHTML = "";
  grid.appendChild(h("div", { class: "sf-loading" }, [
    h("span", { class: "spinner-ink" }),
    h("span", {}, ["Loading…"]),
  ]));

  let finds;
  try {
    finds = (await api.smartFinds()).items || [];
  } catch (e) {
    grid.innerHTML = "";
    grid.appendChild(h("div", { class: "archive-empty" }, [`Failed to load: ${e.message}`]));
    return;
  }

  grid.innerHTML = "";

  if (!finds.length) {
    grid.appendChild(h("div", { class: "archive-empty" }, [
      h("div", { class: "archive-empty-icon", html: icons.sparkle }),
      h("div", {}, ["No Smart Finds yet."]),
      h("div", { class: "archive-empty-sub" }, ["Go to Home and use Smart Find to discover channels by description."]),
    ]));
    return;
  }

  for (const find of finds) {
    grid.appendChild(findBlock(find));
  }
}

// ── Block card ───────────────────────────────────────────────────────────────

function findBlock(find) {
  const names      = find.channel_names || [];
  const channelIds = find.channel_ids   || [];
  const date = find.created_at
    ? new Date(find.created_at).toLocaleString(undefined, {
        month: "short", day: "numeric", hour: "2-digit", minute: "2-digit",
      })
    : "";

  // Stats
  const statsRow = h("div", { class: "sf-block-stats" }, [
    h("span", {}, [`${find.channels_scanned || 0} channels`]),
    h("span", { class: "sf-dot" }, ["·"]),
    h("span", {}, [`${find.total_outliers || 0} outliers`]),
    h("span", { class: "sf-dot" }, ["·"]),
    h("span", { class: "sf-date" }, [date]),
  ]);

  // Channel chips (max 8 visible)
  const visible = names.slice(0, 8);
  const extra   = names.length > 8
    ? h("span", { class: "sf-chip-more" }, [`+${names.length - 8} more`])
    : null;
  const chips = visible.length
    ? h("div", { class: "sf-channel-list" }, [
        ...visible.map(n => h("span", { class: "sf-channel-chip" }, [n])),
        extra,
      ].filter(Boolean))
    : null;

  // Thumbnail preview strip — lazy loaded via IntersectionObserver
  const stripInner = h("div", { class: "sf-block-strip-inner" }, [
    h("div", { class: "sf-strip-placeholder" }),
    h("div", { class: "sf-strip-placeholder" }),
    h("div", { class: "sf-strip-placeholder" }),
    h("div", { class: "sf-strip-placeholder" }),
    h("div", { class: "sf-strip-placeholder" }),
  ]);
  const strip = h("div", { class: "sf-block-strip" }, [stripInner]);

  let stripLoaded = false;
  const obs = new IntersectionObserver((entries) => {
    if (entries[0].isIntersecting && !stripLoaded) {
      stripLoaded = true;
      obs.disconnect();
      loadStrip(stripInner, channelIds);
    }
  }, { rootMargin: "300px" });
  obs.observe(strip);

  const card = h("div", { class: "sf-block" }, [
    h("div", { class: "sf-block-body" }, [
      h("div", { class: "sf-block-desc" }, [find.description || "—"]),
      statsRow,
      chips,
    ].filter(Boolean)),
    strip,
    h("div", { class: "sf-block-footer" }, [
      h("span", { class: "sf-block-cta" }, ["Browse all thumbnails →"]),
    ]),
  ]);

  card.addEventListener("click", () => openOverlay(find, channelIds));

  return card;
}

// ── Strip loader ─────────────────────────────────────────────────────────────

async function loadStrip(inner, channelIds) {
  if (!channelIds.length) {
    inner.innerHTML = `<span class="sf-empty">No channels indexed</span>`;
    return;
  }
  try {
    const r     = await api.outliersByChannels(channelIds, 10);
    const items = (r.items || []).slice(0, 7);
    inner.innerHTML = "";
    if (!items.length) {
      inner.innerHTML = `<span class="sf-empty">No thumbnails yet</span>`;
      return;
    }
    for (const item of items) {
      const url = item.thumbnail_url || item.thumbnail_path
        || `https://img.youtube.com/vi/${item.video_id}/hqdefault.jpg`;
      inner.appendChild(h("img", {
        class: "sf-strip-thumb",
        src: url, alt: "", loading: "lazy",
        onerror: "this.parentElement.removeChild(this)",
      }));
    }
  } catch {
    inner.innerHTML = `<span class="sf-empty">Could not load previews</span>`;
  }
}

// ── Overlay ──────────────────────────────────────────────────────────────────

function openOverlay(find, channelIds) {
  const names = find.channel_names || [];
  const date  = find.created_at
    ? new Date(find.created_at).toLocaleString(undefined, {
        month: "short", day: "numeric", hour: "2-digit", minute: "2-digit",
      })
    : "";

  const gridEl = h("div", { class: "sf-ov-grid" }, [
    h("div", { class: "sf-ov-loading" }, [
      h("span", { class: "spinner-ink" }),
      h("span", {}, ["Loading thumbnails…"]),
    ]),
  ]);

  const panel = h("div", { class: "sf-ov-panel", onclick: (e) => e.stopPropagation() }, [
    h("div", { class: "sf-ov-header" }, [
      h("div", { class: "sf-ov-header-left" }, [
        h("div", { class: "sf-ov-title" }, [find.description || "—"]),
        h("div", { class: "sf-block-stats" }, [
          h("span", {}, [`${find.channels_scanned || 0} channels`]),
          h("span", { class: "sf-dot" }, ["·"]),
          h("span", {}, [`${find.total_outliers || 0} outliers`]),
          h("span", { class: "sf-dot" }, ["·"]),
          h("span", { class: "sf-date" }, [date]),
        ]),
        names.length
          ? h("div", { class: "sf-channel-list" },
              names.map(n => h("span", { class: "sf-channel-chip" }, [n])))
          : null,
      ].filter(Boolean)),
      h("button", {
        class: "btn ghost",
        html: icons.close || "✕",
        onclick: () => backdrop.remove(),
      }),
    ]),
    gridEl,
  ]);

  const backdrop = h("div", { class: "ch-ov-backdrop", onclick: () => backdrop.remove() }, [panel]);
  document.body.appendChild(backdrop);

  // Load full grid
  api.outliersByChannels(channelIds).then(r => {
    const items = r.items || [];
    gridEl.innerHTML = "";
    if (!items.length) {
      gridEl.appendChild(h("div", { class: "sf-ov-empty" }, ["No thumbnails indexed yet for these channels."]));
      return;
    }

    const handlers = {
      onClick:          (it) => navigate("/thumbnails", { reference_video: it }),
      onUseAsReference: (it) => navigate("/thumbnails", { reference_video: it }),
      onBookmark: async (it) => {
        const folders = (await api.folders()).items;
        if (!folders.length) { toast("Create a folder first (Bookmarks tab)", { kind: "error" }); return; }
        pickFolder(folders, async (folderId) => {
          await api.bookmarkAdd({ folder_id: folderId, source: "reference", video_id: it.video_id });
          toast("Bookmarked", { kind: "success" });
        });
      },
    };

    // Group by channel
    const byChannel = new Map();
    for (const item of items) {
      const k = item.channel_id || "__unknown__";
      if (!byChannel.has(k)) byChannel.set(k, []);
      byChannel.get(k).push(item);
    }
    for (const [, channelItems] of byChannel) {
      const name  = channelItems[0].channel_name || "Unknown Channel";
      const niche = channelItems[0].niche || "";
      gridEl.appendChild(h("div", { class: "channel-group-header" }, [
        h("span", { class: "channel-group-name" }, [name]),
        niche ? h("span", { class: "channel-group-niche" }, [niche]) : null,
      ].filter(Boolean)));
      for (const item of channelItems) {
        gridEl.appendChild(thumbCard(item, handlers));
      }
    }
  }).catch(e => {
    gridEl.innerHTML = "";
    gridEl.appendChild(h("div", { class: "sf-ov-empty" }, [`Error: ${e.message}`]));
  });

  const onKey = (e) => {
    if (e.key === "Escape") { backdrop.remove(); document.removeEventListener("keydown", onKey); }
  };
  document.addEventListener("keydown", onKey);
}
