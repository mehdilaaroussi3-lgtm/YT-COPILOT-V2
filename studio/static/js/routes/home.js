// Home — Random Outliers grid.

import { api } from "../api.js";
import { h, icons, thumbCard, emptyState, pageHeader, toast, pickFolder, $ } from "../components.js";
import { navigate } from "../router.js";

export async function mount(outlet) {
  outlet.appendChild(pageHeader({
    kicker: "Outliers",
    title: "Random Outliers",
    subtitle: "Thumbnails from 2×+ outlier videos across tracked channels and the seed registry. Click any card to use it as a reference for new generations.",
  }));

  const topbar = h("div", { class: "topbar" }, [
    h("div", { class: "search grow" }, [
      h("span", { class: "search-icon", html: icons.search }),
      h("input", { id: "q", class: "input", placeholder: "Search outlier titles..." }),
    ]),
    h("button", { class: "btn primary", id: "random", html: `${icons.random}<span>Random</span>` }),
    h("button", { class: "btn ghost", id: "filters", html: `${icons.filter}<span>Filters</span>` }),
  ]);
  outlet.appendChild(topbar);

  const grid = h("div", { class: "thumb-grid", id: "grid" });
  outlet.appendChild(grid);

  async function load(items) {
    grid.innerHTML = "";
    if (!items || !items.length) {
      grid.appendChild(emptyState({
        iconHtml: icons.sparkle,
        title: "No outliers in your index yet",
        body: "Add a channel from the Trackers page, or run `thumbcraft discover <topic>` from the CLI to populate the index.",
        action: h("button", { class: "btn primary", onclick: () => navigate("/trackers") }, ["Go to Trackers"]),
      }));
      return;
    }
    for (const item of items) {
      grid.appendChild(thumbCard(item, {
        onClick: (it) => navigate("/thumbnails", { reference_video: it }),
        onBookmark: async (it) => {
          const folders = (await api.folders()).items;
          if (!folders.length) {
            toast("Create a folder first (Bookmarks tab)", { kind: "error" });
            return;
          }
          pickFolder(folders, async (folderId) => {
            await api.bookmarkAdd({ folder_id: folderId, source: "reference", video_id: it.video_id });
            toast("Bookmarked", { kind: "success" });
          });
        },
        onUseAsReference: (it) => navigate("/thumbnails", { reference_video: it }),
      }));
    }
  }

  // Initial load
  const res = await api.outliersRandom(24);
  load(res.items);

  $("#random", topbar).addEventListener("click", async () => {
    const r = await api.outliersRandom(24);
    load(r.items);
  });

  const qEl = $("#q", topbar);
  let debounce;
  qEl.addEventListener("input", () => {
    clearTimeout(debounce);
    debounce = setTimeout(async () => {
      const q = qEl.value.trim();
      if (!q) {
        const r = await api.outliersRandom(24);
        load(r.items);
      } else {
        const r = await api.outliersSearch(q);
        load(r.items);
      }
    }, 250);
  });
}
