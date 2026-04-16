// Random Outliers — shuffled discovery feed (registered at /outliers).

import { api } from "../api.js";
import { h, icons, thumbCard, emptyState, pageHeader, toast, pickFolder, $ } from "../components.js";
import { navigate } from "../router.js";

export async function mount(outlet) {
  outlet.appendChild(pageHeader({
    kicker: "Outliers",
    title: "Random Outliers",
    subtitle: "Top-performing thumbnails from seed channels + your tracked channels. Click any card to use it as a style reference.",
  }));

  // ── Scan status banner ─────────────────────────────────────────────────────
  const scanBanner = h("div", { class: "scan-banner hidden", id: "scan-banner" });
  outlet.appendChild(scanBanner);

  // ── Topbar ─────────────────────────────────────────────────────────────────
  const nicheSelect = h("select", { class: "input niche-select", id: "niche-filter" }, [
    h("option", { value: "" }, ["All niches"]),
  ]);
  const topbar = h("div", { class: "topbar" }, [
    nicheSelect,
    h("div", { class: "search grow" }, [
      h("span", { class: "search-icon", html: icons.search }),
      h("input", { id: "q", class: "input", placeholder: "Search outlier titles..." }),
    ]),
    h("button", { class: "btn primary", id: "random", html: `${icons.random}<span>Random</span>` }),
    h("button", {
      class: "btn ghost",
      id: "smart-btn",
      title: "Find channels by describing what you're looking for",
      html: `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="15" height="15"><circle cx="11" cy="11" r="8"/><path d="m21 21-4.35-4.35"/><path d="M11 8v6M8 11h6"/></svg><span>Smart Find</span>`,
    }),
    h("button", {
      class: "btn ghost",
      id: "scan-btn",
      title: "Discover ~100 top-performing channels across 10 niches and scan them all",
      html: `${icons.refresh || `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="15" height="15"><polyline points="23 4 23 10 17 10"/><path d="M20.49 15a9 9 0 1 1-2.12-9.36L23 10"/></svg>`}<span>Discover Channels</span>`,
    }),
  ]);
  outlet.appendChild(topbar);

  // ── Smart Find panel ───────────────────────────────────────────────────────
  const smartPanel = h("div", { class: "smart-panel hidden", id: "smart-panel" }, [
    h("div", { class: "smart-panel-inner" }, [
      h("textarea", {
        id: "smart-q",
        class: "input smart-textarea",
        placeholder: "Describe the kind of channel you're looking for…\n\nExamples:\n• documentary channels with 2D low-poly animated thumbnails\n• dark cinematic true crime with red accent text\n• minimal clean tech review, black background, product-only shots",
        rows: "4",
      }),
      h("div", { class: "smart-panel-actions" }, [
        h("span", { class: "smart-hint" }, ["Claude will suggest 10 matching channels, resolve them, and scan their top videos."]),
        h("button", { class: "btn primary", id: "smart-submit" }, ["Find Channels"]),
      ]),
    ]),
  ]);
  outlet.appendChild(smartPanel);

  // ── Smart Find results header (shown after a smart search completes) ────────
  const smartResultHeader = h("div", { class: "smart-result-header hidden" }, [
    h("div", { class: "smart-result-info" }, [
      h("span", { class: "smart-result-label" }, ["Smart Find"]),
      h("span", { class: "smart-result-desc", id: "smart-result-desc" }),
      h("span", { class: "smart-result-count", id: "smart-result-count" }),
    ]),
    h("button", { class: "btn ghost", id: "smart-back" }, ["← Back to library"]),
  ]);
  outlet.appendChild(smartResultHeader);

  const grid = h("div", { class: "thumb-grid", id: "grid" });
  outlet.appendChild(grid);

  // ── Helpers ────────────────────────────────────────────────────────────────
  function makeCardHandlers() {
    return {
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
      onAddChannel: async (it) => {
        if (!it.channel_id) return;
        try {
          // Pass as a full channel URL so _resolve_handle() resolves by ID directly
          await api.trackerAdd(`https://www.youtube.com/channel/${it.channel_id}`, it.niche || "");
          toast(`Tracking ${it.channel_name || "channel"}`, { kind: "success" });
        } catch (e) {
          toast(e.message || "Could not add channel", { kind: "error" });
        }
      },
    };
  }

  function showLibraryMode() {
    smartResultHeader.classList.add("hidden");
    grid.classList.remove("smart-find-grid");
  }

  function load(items) {
    grid.innerHTML = "";
    if (!items || !items.length) {
      grid.appendChild(emptyState({
        iconHtml: icons.sparkle,
        title: "No outliers yet — scanning now…",
        body: "First-run scan is populating the index from seed channels. This takes ~30 seconds. Refresh in a moment.",
        action: h("button", { class: "btn primary", onclick: () => navigate("/trackers") }, ["Or add a channel manually"]),
      }));
      return;
    }
    const handlers = makeCardHandlers();
    for (const item of items) {
      grid.appendChild(thumbCard(item, handlers));
    }
  }

  async function loadRandom() {
    showLibraryMode();
    const niche = nicheSelect.value || "";
    const r = niche
      ? await api.outliersSearch("", niche, null, 100)
      : await api.outliersRandom(100);
    load(r.items);
  }

  async function loadSmartResults(channelIds, description, channelNames) {
    const r = await api.outliersByChannels(channelIds);
    const items = r.items || [];

    // Show the result header
    $("#smart-result-desc", smartResultHeader).textContent = `"${description}"`;
    $("#smart-result-count", smartResultHeader).textContent =
      `${items.length} top videos · ${channelIds.length} channels`;
    smartResultHeader.classList.remove("hidden");
    grid.classList.add("smart-find-grid");

    // Group by channel
    grid.innerHTML = "";
    const handlers = makeCardHandlers();
    const byChannel = new Map();
    for (const item of items) {
      const k = item.channel_id || "__unknown__";
      if (!byChannel.has(k)) byChannel.set(k, []);
      byChannel.get(k).push(item);
    }

    if (byChannel.size === 0) {
      grid.appendChild(emptyState({
        iconHtml: icons.sparkle,
        title: "No results yet",
        body: "The channels were scanned but no videos met the outlier threshold. Try a broader description.",
      }));
      return;
    }

    for (const [, channelItems] of byChannel) {
      const name = channelItems[0].channel_name || "Unknown Channel";
      const niche = channelItems[0].niche || "";
      grid.appendChild(h("div", { class: "channel-group-header" }, [
        h("span", { class: "channel-group-name" }, [name]),
        niche ? h("span", { class: "channel-group-niche" }, [niche]) : null,
      ].filter(Boolean)));
      for (const item of channelItems) {
        grid.appendChild(thumbCard(item, handlers));
      }
    }
  }

  // ── Scan banner polling ────────────────────────────────────────────────────
  let _scanPollTimeout = null;
  async function pollScan() {
    if (!outlet.isConnected) return; // stop recursion when navigated away
    try {
      const s = await api.outliersScanStatus();
      if (s.status === "running") {
        scanBanner.classList.remove("hidden", "done");
        const last = s.events && s.events.length ? s.events[s.events.length - 1] : "Scanning channels…";
        scanBanner.innerHTML = `<span class="spinner-sm"></span><span>${last}</span>`;
        _scanPollTimeout = setTimeout(pollScan, 2000);
      } else if (s.status === "done" && s.result) {
        scanBanner.classList.remove("hidden");
        if (s.result.error) {
          scanBanner.style.borderColor = "#e53e3e44";
          scanBanner.style.background = "#e53e3e0d";
          scanBanner.style.color = "#e53e3e";
          scanBanner.textContent = `Error: ${s.result.error}`;
          setTimeout(() => { scanBanner.classList.add("hidden"); scanBanner.removeAttribute("style"); }, 12000);
        } else if (s.result.source === "smart_search" && s.result.channel_ids?.length) {
          scanBanner.classList.add("hidden");
          navigate("/smart-finds");
        } else {
          scanBanner.classList.add("done");
          scanBanner.textContent = `Done — ${s.result.channels_scanned} channels, ${s.result.total_outliers} outliers indexed.`;
          loadRandom();
          setTimeout(() => scanBanner.classList.add("hidden"), 6000);
        }
      }
    } catch { /* ignore */ }
  }

  // ── Wire events ────────────────────────────────────────────────────────────
  $("#random", topbar).addEventListener("click", loadRandom);
  $("#smart-back", smartResultHeader).addEventListener("click", loadRandom);

  // Smart Find toggle
  const smartBtn = $("#smart-btn", topbar);
  smartBtn.addEventListener("click", () => {
    smartPanel.classList.toggle("hidden");
    if (!smartPanel.classList.contains("hidden")) {
      $("#smart-q", smartPanel).focus();
    }
  });

  // Smart Find submit
  const smartSubmitBtn = $("#smart-submit", smartPanel);
  smartSubmitBtn.addEventListener("click", async () => {
    const desc = $("#smart-q", smartPanel).value.trim();
    if (!desc) {
      toast("Describe what you're looking for first", { kind: "error" });
      return;
    }
    try {
      smartSubmitBtn.disabled = true;
      smartSubmitBtn.textContent = "Finding…";
      await api.outliersSmartSearch(desc);
      smartPanel.classList.add("hidden");
      toast("Smart search started — Claude is finding matching channels…", { kind: "success" });
      scanBanner.classList.remove("hidden", "done");
      scanBanner.innerHTML = `<span class="spinner-sm"></span><span>Claude is finding matching channels…</span>`;
      pollScan();
    } catch (e) {
      toast(e.message || "Smart search failed", { kind: "error" });
    } finally {
      smartSubmitBtn.disabled = false;
      smartSubmitBtn.textContent = "Find Channels";
    }
  });

  // Allow Ctrl+Enter to submit from textarea
  $("#smart-q", smartPanel).addEventListener("keydown", (e) => {
    if (e.key === "Enter" && (e.ctrlKey || e.metaKey)) {
      smartSubmitBtn.click();
    }
  });

  $("#scan-btn", topbar).addEventListener("click", async () => {
    try {
      await api.outliersEnrich(true);
      toast("Discovering channels — resolving ~100 handles across 10 niches…", { kind: "success" });
      scanBanner.classList.remove("hidden", "done");
      scanBanner.innerHTML = `<span class="spinner-sm"></span><span>Resolving channel handles via YouTube API…</span>`;
      pollScan();
    } catch (e) {
      toast(e.message || "Enrichment failed to start", { kind: "error" });
    }
  });

  const qEl = $("#q", topbar);
  let debounce;
  qEl.addEventListener("input", () => {
    clearTimeout(debounce);
    debounce = setTimeout(async () => {
      const q = qEl.value.trim();
      if (!q) {
        loadRandom();
      } else {
        const r = await api.outliersSearch(q);
        load(r.items);
      }
    }, 250);
  });

  // ── Niche filter ────────────────────────────────────────────────────────────
  api.outliersNiches().then((r) => {
    for (const niche of (r.niches || [])) {
      nicheSelect.appendChild(h("option", { value: niche }, [niche]));
    }
  }).catch(() => { /* niches are optional — ignore */ });

  nicheSelect.addEventListener("change", () => {
    // Clear search query when niche changes
    const qEl2 = $("#q", topbar);
    if (qEl2) qEl2.value = "";
    loadRandom();
  });

  // ── Initial load ───────────────────────────────────────────────────────────
  await loadRandom();
  pollScan(); // catch any scan already running from server startup

  return function unmount() {
    if (_scanPollTimeout !== null) { clearTimeout(_scanPollTimeout); _scanPollTimeout = null; }
  };
}
