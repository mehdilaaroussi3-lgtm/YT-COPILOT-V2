// Idea Generator.

import { api } from "../api.js";
import { h, icons, pageHeader, toast, $, groupByDate, formatRelative, channelPicker } from "../components.js";
import { navigate } from "../router.js";

export async function mount(outlet) {
  outlet.appendChild(h("div", { class: "page-center" }, [
    h("h1", { class: "page-title" }, ["Idea Generator"]),
    h("div", { class: "page-subtitle" }, ["Feeds your channel's niche and real outlier titles into the model so ideas stay anchored in what's already working on YouTube."]),
  ]));

  const trackers = (await api.trackers()).items;
  const defaultTracker = trackers.find((t) => t.is_default);
  const picker = channelPicker({
    items: trackers,
    selected: defaultTracker?.channel_id || "",
  });

  const topicWrap = h("div", { class: "hidden flex flex-col gap-2", id: "topic-wrap" }, [
    h("input", { class: "input", id: "topic-input", placeholder: "Add a topic direction — e.g. 'AI heists', 'underrated history'" }),
  ]);

  const genBtn = h("button", { class: "btn huge", id: "gen", html: `${icons.sparkle}<span>Generate Ideas</span><span class="hot-badge">×3 calls</span>` });

  const form = h("div", { class: "card", style: { marginBottom: "32px" } }, [
    h("label", { class: "field-label" }, ["Channel"]),
    h("div", { style: { marginBottom: "16px" } }, [picker.el]),
    h("button", {
      class: "btn ghost sm", style: { marginBottom: "12px", alignSelf: "flex-start" },
      onclick: () => topicWrap.classList.toggle("hidden"),
      html: `${icons.plus}<span>Add a topic direction</span>`,
    }),
    topicWrap,
    h("div", { style: { marginTop: "20px" } }, [genBtn]),
  ]);
  outlet.appendChild(form);

  const results = h("div", { id: "results" });
  outlet.appendChild(results);

  const historyWrap = h("div", { id: "history", style: { marginTop: "56px" } });
  outlet.appendChild(historyWrap);

  genBtn.addEventListener("click", async () => {
    const channel = picker.getValue();
    if (!channel) { toast("Pick a channel first", { kind: "error" }); return; }
    const topic = $("#topic-input", form)?.value?.trim() || "";
    genBtn.disabled = true;
    genBtn.innerHTML = `${icons.sparkle}<span>Generating…</span>`;
    results.innerHTML = "";
    try {
      const r = await api.ideasGenerate(channel, topic);
      if (r.error) { toast(r.error, { kind: "error" }); return; }
      renderIdeas(results, r.items, channel);
      renderHistory();
    } catch (e) {
      toast(e.message, { kind: "error" });
    } finally {
      genBtn.disabled = false;
      genBtn.innerHTML = `${icons.sparkle}<span>Generate Ideas</span><span class="hot-badge">×3 calls</span>`;
    }
  });

  async function renderHistory() {
    const r = await api.ideasHistory();
    historyWrap.innerHTML = "";
    if (!r.items.length) return;
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
              `${first.channel}${first.topic ? ` · ${first.topic}` : ""}`,
            ]),
            h("div", { class: "caption" }, [formatRelative(first.created_at)]),
          ]),
          h("div", { style: { display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(340px, 1fr))", gap: "12px" } },
            batchRows.map(ideaCard)),
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

  function ideaCard(idea, channel) {
    return h("div", { class: "card sm", style: { padding: "18px" } }, [
      h("div", { style: { fontWeight: 600, fontSize: "14.5px", marginBottom: "6px" } }, [idea.idea_title || idea.title]),
      h("div", { class: "body-s", style: { marginBottom: "12px" } }, [idea.idea_description || idea.description || ""]),
      idea.angle && h("div", { class: "badge neutral", style: { marginBottom: "12px" } }, [idea.angle]),
      h("div", { class: "flex gap-2 wrap" }, [
        h("button", { class: "btn sm", onclick: () => navigate("/titles", { prefill_idea: idea.idea_title || idea.title, channel: channel || idea.channel }) }, ["Use for title"]),
        h("button", { class: "btn sm primary", onclick: () => navigate("/thumbnails", { prefill_title: idea.idea_title || idea.title, channel: channel || idea.channel }) }, ["Use for thumbnail"]),
      ].filter(Boolean)),
    ].filter(Boolean));
  }
}
