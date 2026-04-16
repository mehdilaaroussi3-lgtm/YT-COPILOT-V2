// Idea Generator — outputs text ideas OR direct thumbnails, based on toggle.

import { api } from "../api.js";
import { h, icons, toast, $, groupByDate, formatRelative, channelPicker } from "../components.js";
import { streamJob } from "../lib/sse.js";
import { navigate } from "../router.js";

export async function mount(outlet) {
  outlet.appendChild(h("div", { class: "page-center" }, [
    h("h1", { class: "page-title" }, ["Idea Generator"]),
    h("div", { class: "page-subtitle" }, ["Feeds your channel's niche and real outlier titles into the model so ideas stay anchored in what's already working on YouTube."]),
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

  const picker = channelPicker({
    items: trackers,
    selected: defaultTracker?.channel_id || "",
  });

  const topicWrap = h("div", { class: "hidden", id: "topic-wrap", style: { marginTop: "6px", marginBottom: "6px" } }, [
    h("input", { class: "input", id: "topic-input", placeholder: "Add a topic direction — e.g. 'AI heists', 'underrated history'" }),
  ]);

  const countSelect = h("select", { class: "select count-select", id: "ideas-count" }, [
    h("option", { value: "1" }, ["1"]),
    h("option", { value: "3" }, ["3"]),
    h("option", { value: "6", selected: "selected" }, ["6"]),
    h("option", { value: "9" }, ["9"]),
    h("option", { value: "12" }, ["12"]),
    h("option", { value: "15" }, ["15"]),
  ]);
  const genBtn = h("button", { class: "btn huge grow", id: "gen", html: `${icons.sparkle}<span>Generate Ideas</span>` });
  const genRow = h("div", { class: "gen-row" }, [countSelect, genBtn]);

  // Thumbnail-mode controls
  const thumbToggle = h("input", { type: "checkbox", id: "gen-thumbs" });
  const modelSelect = h("select", { class: "select", id: "ideas-model", style: { minWidth: "100px" } }, [
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
  // Hide the model picker + time label when the toggle is off
  const syncThumbRow = () => {
    const on = thumbToggle.checked;
    modelSelect.classList.toggle("hidden", !on);
    timeLabel.classList.toggle("hidden", !on);
  };
  thumbToggle.addEventListener("change", syncThumbRow);
  syncThumbRow();

  const form = h("div", { class: "card", style: { marginBottom: "32px" } }, [
    h("label", { class: "field-label" }, ["Channel"]),
    h("div", { style: { marginBottom: "12px" } }, [picker.el]),
    h("button", {
      class: "btn ghost sm", style: { marginBottom: "8px", alignSelf: "flex-start" },
      onclick: () => topicWrap.classList.toggle("hidden"),
      html: `${icons.plus}<span>Add a topic direction</span>`,
    }),
    topicWrap,
    h("div", { style: { marginTop: "16px" } }, [genRow]),
    thumbRow,
  ]);
  outlet.appendChild(form);

  const results = h("div", { id: "results" });
  outlet.appendChild(results);

  const historyWrap = h("div", { id: "history", style: { marginTop: "56px" } });
  outlet.appendChild(historyWrap);

  const resetBtn = () => {
    genBtn.disabled = false;
    genBtn.innerHTML = `${icons.sparkle}<span>Generate Ideas</span>`;
  };

  const JOB_KEY = "ideas_active_job";
  const saveActiveJob = (jobId, channel, alsoThumbs, startedAt) =>
    sessionStorage.setItem(JOB_KEY, JSON.stringify({ jobId, channel, alsoThumbs, startedAt: startedAt || Date.now() }));
  const clearActiveJob = () => sessionStorage.removeItem(JOB_KEY);

  // Banner element that persists while a generation is running
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

  async function pollIdeasJob(jobId) {
    const MAX_ATTEMPTS = 900; // ~30 minutes at 1.2s intervals
    for (let attempt = 0; attempt < MAX_ATTEMPTS; attempt++) {
      const r = await api.ideasStatus(jobId);
      if (r.status === "done") return r.items || [];
      if (r.status === "error") throw new Error(r.error || "generation failed");
      if (r.status === "unknown") throw new Error("job not found (server may have restarted)");
      await new Promise((res) => setTimeout(res, 1200));
    }
    throw new Error("Generation timed out after 30 minutes");
  }

  function showIdeasSkeleton() {
    results.innerHTML = "";
    const skel = h("div", { class: "loading-skel" });
    for (let i = 0; i < 3; i++) {
      skel.appendChild(h("div", { class: "loading-skel-card" }, [
        h("div", { class: "loading-skel-line lg" }),
        h("div", { class: "loading-skel-line md" }),
        h("div", { class: "loading-skel-line sm" }),
      ]));
    }
    results.appendChild(skel);
  }

  async function afterIdeas(ideas, channel, alsoThumbs) {
    // If we completed in the background while the user navigated away,
    // don't clear job state — they need it to see results on return.
    if (!outlet.isConnected) return;
    results.innerHTML = "";
    if (!alsoThumbs) {
      renderIdeas(results, ideas, channel);
      renderHistory();
      resetBtn();
      clearActiveJob();
      return;
    }
    // Stage 2 — one thumbnail per idea
    results.appendChild(h("div", { class: "section-head" }, [
      h("div", { class: "section-title" }, ["Thumbnails"]),
      h("div", { class: "section-sub" }, [`Rendering ${ideas.length} thumbnails in the channel's style…`]),
    ]));
    const grid = h("div", { class: "thumb-gen-grid" });
    const tiles = ideas.map((idea) => {
      const tile = h("div", { class: "variant-tile loading thumb-gen-tile" }, [
        h("div", { class: "variant-spinner" }),
        h("div", { class: "thumb-gen-caption" }, [idea.idea_title || idea.title || ""]),
      ]);
      grid.appendChild(tile);
      return tile;
    });
    results.appendChild(grid);

    genBtn.innerHTML = `<span class="spinner-sm"></span><span>Rendering thumbnails…</span>`;
    await Promise.all(ideas.map((idea, i) => renderThumbnailTile(idea, i, channel, tiles[i])));

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
      showIdeasSkeleton();
      showRunningBanner("Your previous generation is still running in the background — reconnected.", startedAt);
      const ideas = await pollIdeasJob(jobId);
      hideRunningBanner();
      await afterIdeas(ideas, channel, alsoThumbs);
    } catch (e) {
      hideRunningBanner();
      clearActiveJob();
      resetBtn();
      results.innerHTML = "";
      toast(`Previous generation couldn't resume: ${e.message}`, { kind: "error" });
    }
  })();

  genBtn.addEventListener("click", async () => {
    const channel = picker.getValue();
    if (!channel) { toast("Pick a channel first", { kind: "error" }); return; }
    const topic = $("#topic-input", form)?.value?.trim() || "";
    const alsoThumbs = thumbToggle.checked;
    const count = parseInt(countSelect.value, 10) || 6;

    genBtn.disabled = true;
    genBtn.innerHTML = `<span class="spinner-sm"></span><span>${alsoThumbs ? "Generating ideas + thumbnails…" : "Generating ideas…"}</span>`;
    showIdeasSkeleton();

    const startedAt = Date.now();
    showRunningBanner("Generating ideas in the background — it's safe to leave this page.", startedAt);

    let ideas = [];
    try {
      const r = await api.ideasGenerate(channel, topic, count);
      if (r.error) throw new Error(r.error);
      if (!r.job_id) throw new Error("no job id returned");
      saveActiveJob(r.job_id, channel, alsoThumbs, startedAt);
      ideas = await pollIdeasJob(r.job_id);
    } catch (e) {
      hideRunningBanner();
      results.innerHTML = "";
      toast(e.message, { kind: "error" });
      clearActiveJob();
      resetBtn();
      return;
    }

    hideRunningBanner();
    await afterIdeas(ideas, channel, alsoThumbs);
  });

  async function renderThumbnailTile(idea, idx, channel, tile) {
    const title = idea.idea_title || idea.title || "";
    const fd = new FormData();
    fd.append("title", title);
    fd.append("channel", channel);
    fd.append("style_channel_id", channel);
    fd.append("variants", "1");
    try {
      const { job_id, error } = await api.generate(fd);
      if (error) throw new Error(error);
      await streamJob(`/api/progress/${job_id}`, {
        onVariant: (d) => {
          if (!d.url) return;
          fillTileWithImage(tile, d.url, title, channel);
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
    // Click → deep-link into the Thumbnail Generator with this title for full editing
    img.addEventListener("click", () => navigate("/thumbnails", { prefill_title: title, channel }));
    tile.appendChild(img);
    tile.appendChild(h("div", { class: "thumb-gen-caption" }, [title]));
  }

  // Build a title → latest-thumbnail-url map so we can show thumbnails
  // alongside the ideas that spawned them.
  async function fetchThumbnailIndex() {
    try {
      const r = await api.thumbnailsHistory();
      const idx = {};
      for (const row of r.items || []) {
        const key = (row.title || "").trim().toLowerCase();
        if (!key) continue;
        // Keep the NEWEST thumbnail per title
        if (!idx[key] || (row.created_at || "") > (idx[key].created_at || "")) {
          idx[key] = row;
        }
      }
      return idx;
    } catch { return {}; }
  }

  async function renderHistory() {
    const [r, thumbIdx] = await Promise.all([api.ideasHistory(), fetchThumbnailIndex()]);
    historyWrap.innerHTML = "";
    if (!r.items || !r.items.length) return;
    historyWrap.appendChild(h("div", { class: "section-head" }, [
      h("div", { class: "section-title" }, ["History"]),
      h("div", { class: "section-sub" }, [`${r.items.length} ideas across ${groupByDate(r.items).length} batches`]),
    ]));
    const groups = groupByDate(r.items);
    for (const [date, rows] of groups.slice(0, 10)) {
      const byBatch = {};
      for (const r of rows) (byBatch[r.batch_id] ||= []).push(r);
      for (const [bid, batchRows] of Object.entries(byBatch)) {
        const first = batchRows[0];
        historyWrap.appendChild(h("div", { style: { marginBottom: "24px" } }, [
          h("div", { class: "flex between center", style: { marginBottom: "12px" } }, [
            h("div", { class: "caption" }, [
              `${prettyChannel(first.channel)}${first.topic ? ` · ${first.topic}` : ""}`,
            ]),
            h("div", { class: "caption" }, [formatRelative(first.created_at)]),
          ]),
          h("div", { style: { display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(340px, 1fr))", gap: "12px" } },
            batchRows.map((row) => ideaCard(row, first.channel, thumbIdx))),
        ]));
      }
    }
  }
  renderHistory();

  function renderIdeas(wrap, items, channel) {
    wrap.appendChild(h("div", { class: "section-head" }, [
      h("div", { class: "section-title" }, ["Fresh ideas"]),
      h("div", { class: "section-sub" }, [`${items.length} generated`]),
    ]));
    const grid = h("div", { style: { display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(340px, 1fr))", gap: "12px" } });
    for (const i of items) grid.appendChild(ideaCard(i, channel));
    wrap.appendChild(grid);
  }

  function ideaCard(idea, channel, thumbIdx) {
    const title = idea.idea_title || idea.title || "";
    const thumb = thumbIdx ? thumbIdx[title.trim().toLowerCase()] : null;
    const children = [];

    // If a thumbnail was generated for this idea, show it FIRST, big.
    if (thumb && thumb.url) {
      const thumbImg = h("img", {
        class: "idea-card-thumb",
        src: thumb.url, alt: "", loading: "lazy",
      });
      thumbImg.addEventListener("click", () => navigate("/thumbnails", {
        prefill_title: title, channel: channel || idea.channel,
      }));
      children.push(thumbImg);
    }

    children.push(
      h("div", { class: "idea-card-body" }, [
        h("div", { class: "idea-card-title" }, [title]),
        h("div", { class: "idea-card-desc" }, [idea.idea_description || idea.description || ""]),
        idea.angle && h("div", { class: "badge neutral", style: { marginBottom: "10px" } }, [idea.angle]),
        h("div", { class: "flex gap-2 wrap" }, [
          h("button", { class: "btn sm", onclick: () => navigate("/titles", { prefill_idea: title, channel: channel || idea.channel }) }, ["Use for title"]),
          h("button", { class: "btn sm primary", onclick: () => navigate("/thumbnails", { prefill_title: title, channel: channel || idea.channel }) }, [thumb ? "Regenerate thumbnail" : "Use for thumbnail"]),
        ].filter(Boolean)),
      ].filter(Boolean)),
    );

    return h("div", { class: "card sm idea-card" + (thumb ? " has-thumb" : "") }, children);
  }

  return function unmount() {
    hideRunningBanner(); // stops the timer interval immediately
  };
}
