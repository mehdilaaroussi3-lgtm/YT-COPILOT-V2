// Bookmarks — unified folder system for references + generated thumbnails.

import { api } from "../api.js";
import { h, icons, pageHeader, emptyState, toast, modal, thumbCard, $ } from "../components.js";
import { navigate } from "../router.js";

export async function mount(outlet, { query }) {
  const folderId = query.folder ? parseInt(query.folder, 10) : null;
  if (folderId) return renderFolderDetail(outlet, folderId);
  return renderFolderList(outlet);
}

async function renderFolderList(outlet) {
  outlet.appendChild(pageHeader({
    kicker: "Library",
    title: "Bookmarks",
    subtitle: "Save outlier references and your own generations into topic folders. Both live side-by-side so you can curate inspiration and work together.",
    action: h("button", { class: "btn primary", html: `${icons.folderNew}<span>New folder</span>`, onclick: openNewFolder }),
  }));

  const wrap = h("div", { id: "folder-grid" });
  outlet.appendChild(wrap);

  async function refresh() {
    const { items } = await api.folders();
    wrap.innerHTML = "";
    if (!items.length) {
      wrap.appendChild(emptyState({
        iconHtml: icons.folder,
        title: "No folders yet",
        body: "Create a folder to start saving outlier references and your generated thumbnails.",
        action: h("button", { class: "btn primary", html: `${icons.folderNew}<span>New folder</span>`, onclick: openNewFolder }),
      }));
      return;
    }
    const grid = h("div", { style: { display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(260px, 1fr))", gap: "16px" } });
    for (const f of items) grid.appendChild(folderTile(f, refresh));
    wrap.appendChild(grid);
  }
  refresh();

  function folderTile(f, onRefresh) {
    return h("div", {
      class: "card sm",
      style: { cursor: "pointer", padding: "20px" },
      onclick: () => navigate(`/bookmarks?folder=${f.id}`),
    }, [
      h("div", { class: "flex center gap-3", style: { marginBottom: "16px" } }, [
        h("div", { style: { width: "40px", height: "40px", borderRadius: "10px", background: f.color, display: "grid", placeItems: "center", color: "white" }, html: icons.folder }),
        h("div", { style: { marginLeft: "auto" } }, [
          h("button", { class: "btn ghost sm", html: icons.trash,
            onclick: async (e) => {
              e.stopPropagation();
              if (!confirm(`Delete folder "${f.name}"?`)) return;
              await api.folderDelete(f.id);
              onRefresh();
            }
          }),
        ]),
      ]),
      h("div", { style: { fontSize: "15px", fontWeight: 600 } }, [f.name]),
      h("div", { class: "caption", style: { marginTop: "4px" } }, [`${f.item_count} item${f.item_count === 1 ? "" : "s"}`]),
    ]);
  }

  function openNewFolder() {
    modal({
      title: "New folder",
      body: () => {
        const input = h("input", { class: "input", placeholder: "e.g. Crime documentaries" });
        setTimeout(() => input.focus(), 50);
        return input;
      },
      confirmText: "Create",
      onConfirm: async (modalEl) => {
        const name = modalEl.querySelector("input").value.trim();
        if (!name) return false;
        await api.folderCreate(name);
        toast("Folder created", { kind: "success" });
        refresh();
      },
    });
  }
}

async function renderFolderDetail(outlet, folderId) {
  const folders = (await api.folders()).items;
  const f = folders.find((x) => x.id === folderId);

  // Build channel lookup for displaying pretty names on generated thumbnails
  const channelLookup = {};
  try {
    const trackers = (await api.trackers()).items || [];
    for (const t of trackers) {
      const pretty = t.handle ? `@${t.handle}` : (t.name || "");
      channelLookup[t.channel_id] = pretty;
      if (t.handle) channelLookup[t.handle] = `@${t.handle}`;
    }
  } catch { /* offline */ }
  function prettyChannel(c) {
    if (!c) return "";
    if (channelLookup[c]) return channelLookup[c];
    if (typeof c === "string" && c.startsWith("@")) return c;
    if (typeof c === "string" && c.startsWith("UC")) return "Your channel";
    return c;
  }
  if (!f) {
    outlet.appendChild(emptyState({ title: "Folder not found" }));
    return;
  }

  outlet.appendChild(pageHeader({
    kicker: "Library / Folder",
    title: f.name,
    subtitle: `${f.item_count} item${f.item_count === 1 ? "" : "s"}`,
    action: h("button", { class: "btn ghost", onclick: () => navigate("/bookmarks") }, ["← Back"]),
  }));

  const { items } = await api.bookmarks(folderId);
  const grid = h("div", { class: "thumb-grid" });
  if (!items.length) {
    outlet.appendChild(emptyState({
      iconHtml: icons.bookmark,
      title: "This folder is empty",
      body: "Bookmark outlier references from Home or save generations from the Thumbnail Generator.",
    }));
    return;
  }
  for (const b of items) {
    const item = b.source === "reference"
      ? {
          video_id: b.video_id,
          title: (b.video || {}).title || "—",
          thumb_url: b.thumb_url,
          channel_name: "Reference",
          views: (b.video || {}).views || 0,
          outlier_score: (b.video || {}).outlier_score || 0,
        }
      : {
          video_id: `gen_${b.generation_id}`,
          title: (b.generation || {}).title || "—",
          thumb_url: b.thumb_url,
          channel_name: `Your · ${prettyChannel((b.generation || {}).channel)}`,
          views: 0,
          outlier_score: 0,
        };
    const card = thumbCard(item, {
      showActions: true,
      onBookmark: null,
      onUseAsReference: null,
      onClick: () => {
        if (b.source === "reference") navigate("/thumbnails", { reference_video: item });
        else window.open(b.thumb_url, "_blank");
      },
    });
    // Inject a source badge
    const badge = h("div", {
      class: `badge ${b.source === "generated" ? "success" : "neutral"}`,
      style: { position: "absolute", top: "12px", right: "12px" },
    }, [b.source === "generated" ? "Generated" : "Reference"]);
    card.appendChild(badge);
    grid.appendChild(card);
  }
  outlet.appendChild(grid);
}
