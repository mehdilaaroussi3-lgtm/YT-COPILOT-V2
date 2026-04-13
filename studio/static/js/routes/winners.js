// Thumbnail Winners — indexed style-tagged outliers.

import { api } from "../api.js";
import { h, icons, pageHeader, emptyState } from "../components.js";

export async function mount(outlet) {
  outlet.appendChild(pageHeader({
    kicker: "Analyze",
    title: "Thumbnail Winners",
    subtitle: "Outlier thumbnails with a full Vision-derived style profile — dominant colors, composition, mood, text amount. Click any to see siblings with overlapping style.",
    action: h("div", { class: "badge beta" }, ["Beta"]),
  }));

  const { items } = await api.winners();
  if (!items.length) {
    outlet.appendChild(emptyState({
      iconHtml: icons.winner,
      title: "Nothing indexed yet",
      body: "Run `thumbcraft index --niche <niche>` or scan a tracked channel, then the Vision-described thumbnails show up here.",
    }));
    return;
  }

  const grid = h("div", { class: "thumb-grid" });
  for (const w of items) grid.appendChild(winnerCard(w));
  outlet.appendChild(grid);
}

function winnerCard(w) {
  return h("div", { class: "thumb-card", onclick: () => openDetail(w) }, [
    h("div", { class: "outlier-badge high" }, [`${(w.outlier_score || 0).toFixed(1)}x`]),
    h("img", { class: "thumb-img", src: w.thumb_url, loading: "lazy" }),
    h("div", { class: "thumb-meta" }, [
      h("div", { class: "thumb-title" }, [w.title || "—"]),
      h("div", { class: "flex wrap gap-1", style: { marginTop: "4px" } },
        (w.tags_list || []).slice(0, 3).map((t) => h("span", { class: "badge neutral" }, [t])),
      ),
    ]),
  ]);
}

async function openDetail(w) {
  const backdrop = h("div", { class: "modal-backdrop", onclick: (e) => { if (e.target === backdrop) backdrop.remove(); } });
  const { items: similar } = await api.winnersSimilar(w.video_id);
  const modalEl = h("div", { class: "modal", style: { maxWidth: "720px" } }, [
    h("div", { class: "modal-title" }, [w.title || "Style profile"]),
    h("img", { src: w.thumb_url, style: { width: "100%", borderRadius: "8px", marginBottom: "20px" } }),
    h("div", { class: "flex wrap gap-1", style: { marginBottom: "16px" } },
      (w.tags_list || []).map((t) => h("span", { class: "badge neutral" }, [t])),
    ),
    h("div", { class: "flex wrap gap-2", style: { marginBottom: "16px" } },
      (w.colors_list || []).map((c) => h("div", { style: { display: "flex", alignItems: "center", gap: "6px" } }, [
        h("span", { style: { width: "14px", height: "14px", borderRadius: "4px", background: c, border: "1px solid var(--line)" } }),
        h("span", { class: "caption mono" }, [c]),
      ])),
    ),
    h("div", { class: "body-s", style: { marginBottom: "20px" } }, [w.description || ""]),
    h("div", { class: "eyebrow", style: { marginBottom: "8px" } }, [`${similar.length} similar thumbnails`]),
    h("div", { style: { display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(140px, 1fr))", gap: "8px" } },
      similar.slice(0, 8).map((s) => h("img", { src: s.thumb_url, style: { width: "100%", aspectRatio: "16/9", objectFit: "cover", borderRadius: "6px" } })),
    ),
    h("div", { class: "modal-actions", style: { marginTop: "20px" } }, [
      h("button", { class: "btn ghost", onclick: () => backdrop.remove() }, ["Close"]),
    ]),
  ]);
  backdrop.appendChild(modalEl);
  document.body.appendChild(backdrop);
}
