// Random Channels — shuffled channel discovery grid with mini-thumb strips.

import { api } from "../api.js";
import { h, icons, emptyState, pageHeader, toast } from "../components.js";
import { navigate } from "../router.js";

function formatSubs(n) {
  if (!n) return "—";
  if (n >= 1_000_000) return (n / 1_000_000).toFixed(1).replace(/\.0$/, "") + "M";
  if (n >= 1_000) return (n / 1_000).toFixed(1).replace(/\.0$/, "") + "K";
  return `${n}`;
}

function formatViews(n) {
  if (!n) return "—";
  if (n >= 1_000_000) return (n / 1_000_000).toFixed(1).replace(/\.0$/, "") + "M views";
  if (n >= 1_000) return (n / 1_000).toFixed(1).replace(/\.0$/, "") + "K views";
  return `${n} views`;
}

// ── Channel detail overlay ───────────────────────────────────────────────────

function openChannelOverlay(ch) {
  const initial = (ch.name || "?").charAt(0).toUpperCase();
  const niche   = ch.niche || "";
  const ytUrl   = `https://www.youtube.com/channel/${ch.channel_id}`;

  // Avatar (with fallback if URL is broken)
  const avatarEl = ch.avatar_url
    ? h("img", {
        class: "ch-ov-avatar-img",
        src: ch.avatar_url,
        alt: "",
        onerror: `this.style.display='none';this.nextSibling.style.display='flex'`,
      })
    : null;
  const avatarFallback = h("div", {
    class: "ch-ov-avatar-fallback",
    style: ch.avatar_url ? "display:none" : "",
  }, [initial]);

  // Stats pills
  const score = ch.top_score || 0;
  const statItems = [
    { val: formatSubs(ch.subs),              label: "subscribers" },
    { val: `${ch.outlier_count || 0}`,       label: "outliers"    },
    ch.median_views
      ? { val: formatViews(ch.median_views), label: "median views" }
      : null,
    score >= 1
      ? { val: `${score.toFixed(1)}x`,       label: "best score", accent: true }
      : null,
    ch.is_monetized_likely
      ? { val: "$",                          label: "YPP", monetized: true }
      : null,
  ].filter(Boolean);

  const statsRow = h("div", { class: "ch-ov-stats" },
    statItems.map(s =>
      h("div", { class: `ch-ov-stat${s.monetized ? " ch-ov-stat-ypp" : ""}` }, [
        h("div", { class: `ch-ov-stat-val${s.accent ? " accent" : ""}${s.monetized ? " ypp" : ""}` }, [s.val]),
        h("div", { class: "ch-ov-stat-label" }, [s.label]),
      ]),
    ),
  );

  // Niche tags
  const niches = ch.niches || (niche ? [niche] : []);
  const nicheTags = niches.length
    ? h("div", { class: "ch-card-niches" }, niches.map(n => h("span", { class: "ch-niche-tag" }, [n])))
    : null;

  // Description
  const desc = ch.ai_summary || ch.description || "";

  // Videos section (loaded async)
  const videosSection = h("div", { class: "ch-ov-videos" }, [
    h("div", { class: "ch-ov-videos-label" }, ["Top Outlier Videos"]),
    h("div", { class: "ch-ov-videos-grid", id: "ch-ov-vgrid" }, [
      h("div", { class: "ch-ov-loading" }, ["Loading videos…"]),
    ]),
  ]);

  // Add to Channels button
  let addBtn;
  if (!ch.is_tracked) {
    addBtn = h("button", {
      class: "btn primary",
      onclick: async (e) => {
        try {
          await api.trackerAdd(`https://www.youtube.com/channel/${ch.channel_id}`, niche);
          toast(`Added ${ch.name || "channel"} to My Channels`, { kind: "success" });
          e.target.textContent = "✓ In My Channels";
          e.target.disabled = true;
          e.target.classList.remove("primary");
        } catch (err) {
          toast(err.message || "Could not add channel", { kind: "error" });
        }
      },
    }, ["Add to My Channels"]);
  } else {
    addBtn = h("button", { class: "btn", disabled: true }, ["✓ In My Channels"]);
  }

  const panel = h("div", { class: "ch-ov-panel", onclick: (e) => e.stopPropagation() }, [
    // Header
    h("div", { class: "ch-ov-header" }, [
      h("div", { class: "ch-ov-avatar" }, [avatarEl, avatarFallback].filter(Boolean)),
      h("div", { class: "ch-ov-identity" }, [
        h("div", { class: "ch-ov-name" }, [ch.name || "Unknown"]),
        ch.handle && h("div", { class: "ch-ov-handle" }, [`@${ch.handle}`]),
      ].filter(Boolean)),
      h("div", { class: "ch-ov-header-actions" }, [
        h("a", {
          class: "btn ghost",
          href: ytUrl,
          target: "_blank",
          rel: "noopener",
          html: `${icons.search}<span>Open on YouTube</span>`,
        }),
        addBtn,
        h("button", {
          class: "btn ghost ch-ov-close",
          html: icons.close || "✕",
          onclick: () => backdrop.remove(),
        }),
      ]),
    ]),
    statsRow,
    nicheTags,
    desc && h("p", { class: "ch-ov-desc" }, [desc]),
    videosSection,
  ].filter(Boolean));

  const backdrop = h("div", { class: "ch-ov-backdrop", onclick: () => backdrop.remove() }, [panel]);
  document.body.appendChild(backdrop);

  // Load videos async
  api.outliersByChannels([ch.channel_id], 30).then(r => {
    const vgrid = backdrop.querySelector("#ch-ov-vgrid");
    if (!vgrid) return;
    const videos = r.items || [];
    if (!videos.length) {
      vgrid.innerHTML = `<p class="ch-ov-empty">No outlier videos scanned yet for this channel.</p>`;
      return;
    }
    vgrid.innerHTML = "";
    for (const v of videos) {
      const url = v.thumbnail_url || v.thumbnail_path
        || `https://img.youtube.com/vi/${v.video_id}/hqdefault.jpg`;
      const tile = h("div", {
        class: "ch-ov-thumb-tile",
        onclick: () => navigate("/thumbnails", { reference: v }),
      }, [
        h("img", { src: url, alt: "", loading: "lazy", onerror: "this.style.opacity='.3'" }),
        h("div", { class: "ch-ov-thumb-score" }, [`${(v.outlier_score || 0).toFixed(1)}x`]),
        h("div", { class: "ch-ov-thumb-title" }, [v.title || ""]),
      ]);
      vgrid.appendChild(tile);
    }
  }).catch(() => {
    const vgrid = backdrop.querySelector("#ch-ov-vgrid");
    if (vgrid) vgrid.innerHTML = `<p class="ch-ov-empty">Could not load videos.</p>`;
  });

  // Close on Escape
  const onKey = (e) => { if (e.key === "Escape") { backdrop.remove(); document.removeEventListener("keydown", onKey); } };
  document.addEventListener("keydown", onKey);
}

// ── Mount ────────────────────────────────────────────────────────────────────

export async function mount(outlet) {
  outlet.appendChild(pageHeader({
    kicker: "Outliers",
    title: "Random Channels",
    subtitle: "Curated seed channels + your tracked channels. Every load shows a different mix.",
  }));

  // ── Topbar ──────────────────────────────────────────────────────────────────
  const shuffleBtn = h("button", {
    class: "btn primary",
    id: "shuffle-btn",
    html: `${icons.random}<span>Shuffle</span>`,
  });
  const topbar = h("div", { class: "topbar" }, [shuffleBtn]);
  outlet.appendChild(topbar);

  // ── Grid ────────────────────────────────────────────────────────────────────
  const grid = h("div", { class: "channel-cards-grid", id: "ch-grid" });
  outlet.appendChild(grid);

  // ── Helpers ─────────────────────────────────────────────────────────────────
  async function loadChannels() {
    grid.innerHTML = `<div class="spinner-lg"></div>`;
    try {
      const r = await api.channelsRandom(40);
      renderGrid(r.items || []);
    } catch (e) {
      grid.innerHTML = "";
      grid.appendChild(emptyState({
        iconHtml: icons.spark,
        title: "Could not load channels",
        body: e.message || "Check the server is running.",
      }));
    }
  }

  function renderGrid(items) {
    grid.innerHTML = "";
    if (!items.length) {
      grid.appendChild(emptyState({
        iconHtml: icons.track,
        title: "No channels found",
        body: "Try a different niche or run a channel scan first.",
      }));
      return;
    }
    for (const ch of items) {
      grid.appendChild(channelCard(ch));
    }
  }

  function channelCard(ch) {
    const initial = (ch.name || "?").charAt(0).toUpperCase();
    const score   = ch.top_score || 0;
    const niche   = ch.niche || "";
    const desc    = ch.ai_summary || ch.description || "";

    // Avatar — with onerror fallback (no dead broken slot ever)
    const avatarInner = ch.avatar_url
      ? h("img", {
          class: "ch-card-avatar-img",
          src: ch.avatar_url,
          alt: "",
          onerror: `this.style.display='none';this.nextSibling.style.display='flex'`,
        })
      : null;
    const avatarFallback = h("div", {
      class: "ch-card-avatar-fallback",
      style: ch.avatar_url ? "display:none" : "",
    }, [initial]);

    // Stats pills
    const statItems = [
      { val: formatSubs(ch.subs),              label: "subs"     },
      { val: `${ch.outlier_count || 0}`,       label: "outliers" },
      ch.median_views
        ? { val: formatViews(ch.median_views), label: "median"   }
        : null,
      score >= 1
        ? { val: `${score.toFixed(1)}x`,       label: "best",  accent: true }
        : null,
      ch.is_monetized_likely
        ? { val: "$",                          label: "YPP",   monetized: true }
        : null,
    ].filter(Boolean);

    const statsRow = h("div", { class: "ch-card-stats-row" },
      statItems.map(s =>
        h("div", { class: `ch-stat${s.monetized ? " ch-stat-ypp" : ""}` }, [
          h("span", { class: `ch-stat-val${s.accent ? " ch-stat-accent" : ""}${s.monetized ? " ch-stat-ypp-val" : ""}` }, [s.val]),
          h("span", { class: "ch-stat-label" }, [s.label]),
        ]),
      ),
    );

    // Niche tags
    const niches = ch.niches || (niche ? [niche] : []);
    const nicheTags = niches.length
      ? h("div", { class: "ch-card-niches" },
          niches.map(n => h("span", { class: "ch-niche-tag" }, [n])),
        )
      : null;

    // Thumbnail strip
    const thumbUrls = ch.top_thumb_urls || [];
    const thumbStrip = thumbUrls.length
      ? h("div", { class: "ch-card-thumbs" }, [
          h("div", { class: "ch-thumbs-label" }, ["Recent Videos"]),
          h("div", { class: "ch-thumbs-row" },
            thumbUrls.map(url =>
              h("img", {
                class: "ch-thumb",
                src: url, alt: "", loading: "lazy",
                onerror: "this.parentElement.removeChild(this)",
              }),
            ),
          ),
        ])
      : (desc ? h("p", { class: "ch-card-desc" }, [desc]) : null);

    // CTA button
    const addBtn = !ch.is_tracked
      ? h("button", {
          class: "btn primary ch-add-btn",
          onclick: async (e) => {
            e.stopPropagation();
            try {
              await api.trackerAdd(`https://www.youtube.com/channel/${ch.channel_id}`, niche);
              toast(`Added ${ch.name || "channel"} to My Channels`, { kind: "success" });
              e.target.textContent = "✓ Added";
              e.target.disabled = true;
              e.target.classList.remove("primary");
            } catch (err) {
              toast(err.message || "Could not add channel", { kind: "error" });
            }
          },
        }, ["Add to My Channels"])
      : h("button", { class: "btn ch-add-btn", disabled: true }, ["✓ In My Channels"]);

    const card = h("div", { class: "ch-card" }, [
      h("div", { class: "ch-card-avatar" }, [avatarInner, avatarFallback].filter(Boolean)),
      h("div", { class: "ch-card-identity" }, [
        h("div", { class: "ch-card-name" }, [ch.name || "Unknown"]),
        ch.handle
          ? h("div", { class: "ch-card-handle" }, [`@${ch.handle}`])
          : (niche ? h("div", { class: "ch-card-handle" }, [niche]) : null),
      ].filter(Boolean)),
      statsRow,
      nicheTags,
      thumbStrip,
      h("div", { class: "ch-card-actions" }, [addBtn]),
    ].filter(Boolean));

    // Click card body (not the button) → open overlay
    card.style.cursor = "pointer";
    card.addEventListener("click", () => openChannelOverlay(ch));

    return card;
  }

  // ── Wire events ─────────────────────────────────────────────────────────────
  shuffleBtn.addEventListener("click", loadChannels);

  // Initial load
  await loadChannels();
}
