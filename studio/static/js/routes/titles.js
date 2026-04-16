// Title Generator — outputs text titles OR direct thumbnails, based on toggle.

import { api } from "../api.js";
import { h, icons, toast, $, groupByDate, formatRelative, copyToClipboard, channelPicker } from "../components.js";
import { streamJob } from "../lib/sse.js";
import { navigate } from "../router.js";

export async function mount(outlet, { state }) {
  outlet.appendChild(h("div", { class: "page-center" }, [
    h("h1", { class: "page-title" }, ["Title Generator"]),
    h("div", { class: "page-subtitle" }, ["Six emotionally distinct title variants per generation, applying the 5-word / 30-char sweet spot and the negative-framing rule (+22% views)."]),
  ]));

  const trackers = (await api.trackers()).items;
  const defaultTracker = trackers.find((t) => t.is_default);

  // Build channel_id → @handle / name lookup for history display
  const channelLookup = {};
  for (const t of trackers) {
    const pretty = t.handle ? `@${t.handle}` : (t.name || "");
    channelLookup[t.channel_id] = pretty;
    if (t.handle) channelLookup[t.handle] = `@${t.handle}`;
  }
  function prettyChannel(c) {
    if (!c) return "Unknown channel";
    if (channelLookup[c]) return channelLookup[c];
    if (typeof c === "string" && c.startsWith("@")) return c;
    if (typeof c === "string" && c.startsWith("UC")) return "Unknown channel";
    return c;
  }

  const prefillIdea = state?.prefill_idea || "";
  const prefillChannel = state?.channel || "";
  const picker = channelPicker({
    items: trackers,
    selected: (prefillChannel && prefillChannel.startsWith("UC")) ? prefillChannel : (defaultTracker?.channel_id || ""),
  });

  const ideaTextarea = h("textarea", { class: "textarea", id: "idea", rows: 4, placeholder: "Write the title you have in mind OR what the video is about" }, [prefillIdea]);
  const charCounter = h("span", { class: "char-counter" }, ["0 / 1000"]);
  const countSelect = h("select", { class: "select count-select", id: "titles-count", title: "Titles per source (channel DNA + outliers)" }, [
    h("option", { value: "5" }, ["5"]),
    h("option", { value: "10", selected: "selected" }, ["10"]),
    h("option", { value: "15" }, ["15"]),
    h("option", { value: "20" }, ["20"]),
  ]);
  const genBtn = h("button", { class: "btn huge grow", id: "gen", html: `${icons.sparkle}<span>Generate</span>` });
  const genRow = h("div", { class: "gen-row" }, [
    h("span", { class: "count-label" }, ["Per column"]),
    countSelect,
    genBtn,
  ]);

  // Thumbnail-mode controls
  const thumbToggle = h("input", { type: "checkbox", id: "titles-gen-thumbs" });
  const modelSelect = h("select", { class: "select", id: "titles-model", style: { minWidth: "100px" } }, [
    h("option", { value: "gen-2.5" }, ["Gen-2.5"]),
    h("option", { value: "gen-3" }, ["Gen-3 Pro"]),
  ]);
  const timeLabel = h("span", { class: "time-estimate" }, ["~2 minutes"]);

  const thumbRow = h("div", { class: "thumb-mode-row" }, [
    h("label", { class: "toggle" }, [
      thumbToggle,
      h("span", { class: "toggle-switch" }),
      "Generate thumbnails",
    ]),
    modelSelect,
    h("div", { class: "grow" }),
    timeLabel,
  ]);
  const syncThumbRow = () => {
    const on = thumbToggle.checked;
    modelSelect.classList.toggle("hidden", !on);
    timeLabel.classList.toggle("hidden", !on);
  };
  thumbToggle.addEventListener("change", syncThumbRow);
  syncThumbRow();

  const form = h("div", { class: "card", style: { marginBottom: "32px" } }, [
    h("label", { class: "field-label" }, ["Channel"]),
    h("div", { style: { marginBottom: "16px" } }, [picker.el]),
    h("label", { class: "field-label" }, ["Idea / working title"]),
    ideaTextarea,
    h("div", { class: "flex between center", style: { marginTop: "8px", marginBottom: "16px" } }, [
      h("span", { class: "caption" }, ["Tip: include numbers and money — they survive into the hook"]),
      charCounter,
    ]),
    genRow,
    thumbRow,
  ]);
  outlet.appendChild(form);

  const results = h("div", { id: "results" });
  outlet.appendChild(results);

  const historyWrap = h("div", { id: "history", style: { marginTop: "56px" } });
  outlet.appendChild(historyWrap);

  function updateCounter() {
    const len = ideaTextarea.value.length;
    charCounter.textContent = `${len} / 1000`;
    charCounter.classList.toggle("warn", len > 800);
    charCounter.classList.toggle("over", len > 1000);
  }
  ideaTextarea.addEventListener("input", updateCounter);
  updateCounter();

  const resetBtn = () => {
    genBtn.disabled = false;
    genBtn.innerHTML = `${icons.sparkle}<span>Generate</span>`;
  };

  const JOB_KEY = "titles_active_job";
  const saveActiveJob = (jobId, channel, alsoThumbs, startedAt) =>
    sessionStorage.setItem(JOB_KEY, JSON.stringify({ jobId, channel, alsoThumbs, startedAt: startedAt || Date.now() }));
  const clearActiveJob = () => sessionStorage.removeItem(JOB_KEY);

  let runningBanner = null;
  let runningTimerInterval = null;
  function showRunningBanner(message, startedAt) {
    hideRunningBanner();
    const timerSpan = h("span", { class: "timer" }, ["0s"]);
    runningBanner = h("div", { class: "reconnect-banner" }, [
      h("span", { class: "spinner-ink" }),
      h("span", {}, [message]),
      timerSpan,
    ]);
    results.parentElement.insertBefore(runningBanner, results);
    const t0 = startedAt || Date.now();
    const tick = () => { timerSpan.textContent = `${Math.floor((Date.now() - t0) / 1000)}s`; };
    tick();
    runningTimerInterval = setInterval(tick, 1000);
  }
  function hideRunningBanner() {
    if (runningBanner) { runningBanner.remove(); runningBanner = null; }
    if (runningTimerInterval) { clearInterval(runningTimerInterval); runningTimerInterval = null; }
  }

  async function pollTitlesJob(jobId) {
    while (true) {
      const r = await api.titlesStatus(jobId);
      if (r.status === "done") return {
        channelTitles: r.channel_titles || [],
        outlierTitles: r.outlier_titles || [],
      };
      if (r.status === "error") throw new Error(r.error || "generation failed");
      if (r.status === "unknown") throw new Error("job not found (server may have restarted)");
      await new Promise((res) => setTimeout(res, 1200));
    }
  }

  function showTitlesSkeleton() {
    results.innerHTML = "";
    const skel = h("div", { class: "loading-skel" });
    for (let i = 0; i < 6; i++) {
      skel.appendChild(h("div", { class: "loading-skel-card" }, [
        h("div", { class: "loading-skel-line lg" }),
        h("div", { class: "loading-skel-line sm" }),
      ]));
    }
    results.appendChild(skel);
  }

  async function afterTitles(channelTitles, outlierTitles, channel, alsoThumbs) {
    if (!outlet.isConnected) return; // completed in background — preserve job state for return
    results.innerHTML = "";
    if (!alsoThumbs) {
      renderDualTitles(results, channelTitles, outlierTitles, channel);
      renderHistory();
      resetBtn();
      clearActiveJob();
      return;
    }
    const titles = [...channelTitles, ...outlierTitles];
    results.appendChild(h("div", { class: "section-head" }, [
      h("div", { class: "section-title" }, ["Thumbnails"]),
      h("div", { class: "section-sub" }, [`Rendering ${titles.length} thumbnails in the channel's style…`]),
    ]));
    const grid = h("div", { class: "thumb-gen-grid" });
    const tiles = titles.map((t) => {
      const tile = h("div", { class: "variant-tile loading thumb-gen-tile" }, [
        h("div", { class: "variant-spinner" }),
        h("div", { class: "thumb-gen-caption" }, [t.title || ""]),
      ]);
      grid.appendChild(tile);
      return tile;
    });
    results.appendChild(grid);

    genBtn.innerHTML = `<span class="spinner-sm"></span><span>Rendering thumbnails…</span>`;
    await Promise.all(titles.map((t, i) => renderThumbnailTile(t, i, channel, tiles[i])));

    if (!outlet.isConnected) return;
    renderHistory();
    resetBtn();
    clearActiveJob();
  }

  // Reconnect to an active job if we left and came back.
  (async () => {
    const saved = sessionStorage.getItem(JOB_KEY);
    if (!saved) return;
    try {
      const { jobId, channel, alsoThumbs, startedAt } = JSON.parse(saved);
      genBtn.disabled = true;
      genBtn.innerHTML = `<span class="spinner-sm"></span><span>Reconnecting to your generation…</span>`;
      showTitlesSkeleton();
      showRunningBanner("Your previous generation is still running in the background — reconnected.", startedAt);
      const { channelTitles, outlierTitles } = await pollTitlesJob(jobId);
      hideRunningBanner();
      await afterTitles(channelTitles, outlierTitles, channel, alsoThumbs);
    } catch (e) {
      hideRunningBanner();
      clearActiveJob();
      resetBtn();
      results.innerHTML = "";
      toast(`Previous generation couldn't resume: ${e.message}`, { kind: "error" });
    }
  })();

  genBtn.addEventListener("click", async () => {
    const idea = ideaTextarea.value.trim();
    const channel = picker.getValue();
    if (!channel) { toast("Pick a channel first", { kind: "error" }); return; }
    if (!idea) { toast("Write an idea first", { kind: "error" }); return; }
    const alsoThumbs = thumbToggle.checked;
    const count = parseInt(countSelect.value, 10) || 10;

    genBtn.disabled = true;
    genBtn.innerHTML = `<span class="spinner-sm"></span><span>${alsoThumbs ? "Generating titles + thumbnails…" : "Generating titles…"}</span>`;
    showTitlesSkeleton();

    const startedAt = Date.now();
    showRunningBanner("Generating titles in the background — it's safe to leave this page.", startedAt);

    let channelTitles = [];
    let outlierTitles = [];
    try {
      const r = await api.titlesGenerate(channel, idea, count);
      if (r.error) throw new Error(r.error);
      if (!r.job_id) throw new Error("no job id returned");
      saveActiveJob(r.job_id, channel, alsoThumbs, startedAt);
      const res = await pollTitlesJob(r.job_id);
      channelTitles = res.channelTitles;
      outlierTitles = res.outlierTitles;
    } catch (e) {
      hideRunningBanner();
      results.innerHTML = "";
      toast(e.message, { kind: "error" });
      clearActiveJob();
      resetBtn();
      return;
    }

    hideRunningBanner();
    await afterTitles(channelTitles, outlierTitles, channel, alsoThumbs);
  });

  async function renderThumbnailTile(title, idx, channel, tile) {
    const text = title.title || "";
    const fd = new FormData();
    fd.append("title", text);
    fd.append("channel", channel);
    fd.append("style_channel_id", channel);
    fd.append("variants", "1");
    try {
      const { job_id, error } = await api.generate(fd);
      if (error) throw new Error(error);
      await streamJob(`/api/progress/${job_id}`, {
        onVariant: (d) => {
          if (!d.url) return;
          fillTileWithImage(tile, d.url, text, channel);
        },
      });
    } catch (e) {
      tile.classList.remove("loading");
      tile.classList.add("error");
      tile.innerHTML = "";
      tile.appendChild(h("div", { class: "variant-err" }, [e.message || "Generation failed"]));
    }
  }

  function fillTileWithImage(tile, url, title, channel) {
    tile.classList.remove("loading");
    tile.innerHTML = "";
    const img = h("img", { class: "variant-img", src: url, alt: "", loading: "lazy" });
    img.addEventListener("click", () => navigate("/thumbnails", { prefill_title: title, channel }));
    tile.appendChild(img);
    tile.appendChild(h("div", { class: "thumb-gen-caption" }, [title]));
  }

  function renderDualTitles(wrap, channelItems, outlierItems, channel) {
    const dual = h("div", { class: "titles-dual" }, [
      renderColumn("Inspired By Your Channel Titles", channelItems, channel),
      renderColumn("Inspired By Top Outliers", outlierItems, channel),
    ]);
    wrap.appendChild(dual);
  }

  function renderColumn(heading, items, channel) {
    const col = h("div", { class: "titles-col" }, [
      h("div", { class: "titles-col-head" }, [heading]),
    ]);
    if (!items.length) {
      col.appendChild(h("div", { class: "titles-empty" }, ["— no titles generated for this source —"]));
      return col;
    }
    const list = h("div", { class: "titles-list" });
    for (const t of items) list.appendChild(titleRow(t, channel));
    col.appendChild(list);
    return col;
  }

  function titleRow(t, channel) {
    const charBadge = h("span", { class: "titles-row-chars" }, [`${t.char_count} characters`]);
    if (t.char_count > 30) charBadge.classList.add("warn");

    const dots = `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="currentColor" width="18" height="18"><circle cx="5" cy="12" r="2"/><circle cx="12" cy="12" r="2"/><circle cx="19" cy="12" r="2"/></svg>`;
    const menuBtn = h("button", {
      class: "titles-row-menu-btn", title: "More", html: dots,
      onclick: (e) => { e.stopPropagation(); openRowMenu(e.currentTarget, t, channel); },
    });

    const row = h("div", { class: "titles-row" }, [
      h("div", { class: "titles-row-text" }, [t.title]),
      h("div", { class: "titles-row-right" }, [charBadge, menuBtn]),
    ]);
    return row;
  }

  function openRowMenu(anchor, t, channel) {
    document.querySelectorAll(".tile-menu").forEach((m) => m.remove());
    const menu = h("div", { class: "tile-menu" }, [
      menuItem(icons.copy, "Copy title", () => copyToClipboard(t.title)),
      menuItem(icons.sparkle, "Use for thumbnail", () => navigate("/thumbnails", { prefill_title: t.title, channel: channel || t.channel })),
    ]);
    document.body.appendChild(menu);
    const r = anchor.getBoundingClientRect();
    menu.style.top = `${r.bottom + window.scrollY + 6}px`;
    menu.style.left = `${r.right + window.scrollX - menu.offsetWidth}px`;
    const close = (ev) => { if (!menu.contains(ev.target)) { menu.remove(); document.removeEventListener("click", close); } };
    setTimeout(() => document.addEventListener("click", close), 0);
  }

  function menuItem(iconHtml, label, onclick) {
    return h("button", {
      class: "tile-menu-item", onclick,
    }, [h("span", { class: "tile-menu-icon", html: iconHtml }), h("span", {}, [label])]);
  }

  // Kept for the thumbnail-mode tile caption
  function titleCard(t, channel) { return titleRow(t, channel); }

  async function renderHistory() {
    const r = await api.titlesHistory();
    historyWrap.innerHTML = "";
    if (!r.items.length) return;
    historyWrap.appendChild(h("div", { class: "section-head" }, [
      h("div", { class: "section-title" }, ["History"]),
      h("div", { class: "section-sub" }, [`${r.items.length} titles across batches`]),
    ]));
    const byBatch = {};
    for (const row of r.items) (byBatch[row.batch_id] ||= []).push(row);
    for (const [bid, rows] of Object.entries(byBatch).slice(0, 8)) {
      const first = rows[0];
      historyWrap.appendChild(h("div", { style: { marginBottom: "32px" } }, [
        h("div", { class: "flex between center", style: { marginBottom: "10px" } }, [
          h("div", { class: "caption" }, [`${prettyChannel(first.channel)}  —  ${first.source_idea.slice(0, 80)}${first.source_idea.length > 80 ? "…" : ""}`]),
          h("div", { class: "caption" }, [formatRelative(first.created_at)]),
        ]),
        h("div", { style: { display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(380px, 1fr))", gap: "8px" } },
          rows.map((t) => titleCard(t, first.channel))),
      ]));
    }
  }
  renderHistory();

  return function unmount() {
    hideRunningBanner(); // stops the timer interval immediately
  };
}
