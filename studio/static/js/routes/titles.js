// Title Generator.

import { api } from "../api.js";
import { h, icons, pageHeader, toast, $, groupByDate, formatRelative, copyToClipboard, channelPicker } from "../components.js";
import { navigate } from "../router.js";

export async function mount(outlet, { state }) {
  outlet.appendChild(h("div", { class: "page-center" }, [
    h("h1", { class: "page-title" }, ["Title Generator"]),
    h("div", { class: "page-subtitle" }, ["Six emotionally distinct title variants per generation, applying the 5-word / 30-char sweet spot and the negative-framing rule (+22% views)."]),
  ]));

  const trackers = (await api.trackers()).items;
  const defaultTracker = trackers.find((t) => t.is_default);
  const prefillIdea = state?.prefill_idea || "";
  const prefillChannel = state?.channel || "";
  const picker = channelPicker({
    items: trackers,
    selected: (prefillChannel && prefillChannel.startsWith("UC")) ? prefillChannel : (defaultTracker?.channel_id || ""),
  });

  const ideaTextarea = h("textarea", { class: "textarea", id: "idea", rows: 4, placeholder: "Write the title you have in mind OR what the video is about" }, [prefillIdea]);
  const charCounter = h("span", { class: "char-counter" }, ["0 / 1000"]);
  const genBtn = h("button", { class: "btn huge", id: "gen", html: `${icons.sparkle}<span>Generate</span><span class="hot-badge">×1 call</span>` });

  const form = h("div", { class: "card", style: { marginBottom: "32px" } }, [
    h("label", { class: "field-label" }, ["Channel"]),
    h("div", { style: { marginBottom: "16px" } }, [picker.el]),
    h("label", { class: "field-label" }, ["Idea / working title"]),
    ideaTextarea,
    h("div", { class: "flex between center", style: { marginTop: "8px", marginBottom: "20px" } }, [
      h("span", { class: "caption" }, ["Tip: include numbers and money — they survive into the hook"]),
      charCounter,
    ]),
    genBtn,
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

  genBtn.addEventListener("click", async () => {
    const idea = ideaTextarea.value.trim();
    const channel = picker.getValue();
    if (!channel) { toast("Pick a channel first", { kind: "error" }); return; }
    if (!idea) { toast("Write an idea first", { kind: "error" }); return; }
    genBtn.disabled = true;
    genBtn.innerHTML = `${icons.sparkle}<span>Generating…</span>`;
    results.innerHTML = "";
    try {
      const r = await api.titlesGenerate(channel, idea);
      if (r.error) { toast(r.error, { kind: "error" }); return; }
      renderTitles(results, r.items, channel);
      renderHistory();
    } catch (e) {
      toast(e.message, { kind: "error" });
    } finally {
      genBtn.disabled = false;
      genBtn.innerHTML = `${icons.sparkle}<span>Generate</span><span class="hot-badge">×1 call</span>`;
    }
  });

  function renderTitles(wrap, items, channel) {
    wrap.appendChild(h("div", { class: "section-head" }, [
      h("div", { class: "section-title" }, ["Variants"]),
      h("div", { class: "section-sub" }, [`${items.length} generated`]),
    ]));
    const grid = h("div", { style: { display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(380px, 1fr))", gap: "10px" } });
    for (const t of items) grid.appendChild(titleCard(t, channel));
    wrap.appendChild(grid);
  }

  function titleCard(t, channel) {
    const charBadge = h("span", { class: "caption", style: { fontFamily: "var(--font-mono)" } }, [`${t.char_count} chars`]);
    if (t.char_count > 30) charBadge.classList.add("warn");
    return h("div", { class: "card sm", style: { padding: "16px 18px" } }, [
      h("div", { class: "flex between center", style: { marginBottom: "8px" } }, [
        t.angle && h("div", { class: "badge neutral" }, [t.angle]),
        charBadge,
      ].filter(Boolean)),
      h("div", { style: { fontSize: "15px", fontWeight: 500, marginBottom: "12px" } }, [t.title]),
      h("div", { class: "flex gap-2 wrap" }, [
        h("button", { class: "btn ghost sm", html: `${icons.copy}<span>Copy</span>`, onclick: () => copyToClipboard(t.title) }),
        h("button", { class: "btn sm primary", onclick: () => navigate("/thumbnails", { prefill_title: t.title, channel: channel || t.channel }) }, ["Use for thumbnail"]),
      ]),
    ]);
  }

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
          h("div", { class: "caption" }, [`${first.channel}  —  ${first.source_idea.slice(0, 80)}${first.source_idea.length > 80 ? "…" : ""}`]),
          h("div", { class: "caption" }, [formatRelative(first.created_at)]),
        ]),
        h("div", { style: { display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(380px, 1fr))", gap: "8px" } },
          rows.map((t) => titleCard(t, first.channel))),
      ]));
    }
  }
  renderHistory();
}
