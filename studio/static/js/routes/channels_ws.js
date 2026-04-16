// My Channels Workspace — End-to-end production hub.
// Flow: Create channel (questionnaire + voice) → DNA scan → Ideas/Direct title
//       → Thumbnail → Script review → Gated section production → Final MP4

import { api } from "../api.js";
import { h, icons, toast, channelPicker } from "../components.js";
import { navigate } from "../router.js";
import { streamJob } from "../lib/sse.js";
import { openSketchPad } from "../components/sketch_pad.js";

// ── Helpers ───────────────────────────────────────────────────────────────────

function avatarEl(ch) {
  const el = h("div", { class: "ch-avatar" }, [(ch.name || "?").slice(0, 2).toUpperCase()]);
  if (ch.avatar_color) el.style.background = ch.avatar_color;
  return el;
}

function dnaBadge(ch) {
  if (ch.dna_path) {
    return h("span", { class: "pill active", style: { background: "var(--success-subtle,#d1fae5)", color: "var(--success,#10b981)", border: "1px solid var(--success,#10b981)" } }, ["DNA Ready"]);
  }
  return h("span", { class: "pill", style: { color: "var(--ink-500,#6b7280)" } }, ["No DNA"]);
}

function statusPill(status) {
  const map = {
    idea:      { label: "Idea",       bg: "var(--surface-2)", color: "var(--ink-500)" },
    thumbnail: { label: "Thumbnail",  bg: "#ede9fe", color: "#7c3aed" },
    scripted:  { label: "Scripted",   bg: "#dbeafe", color: "#1d4ed8" },
    producing: { label: "Producing",  bg: "#fef3c7", color: "#b45309" },
    done:      { label: "Done",       bg: "#d1fae5", color: "#10b981" },
  };
  const m = map[status] || map.idea;
  return h("span", { class: "pill", style: { background: m.bg, color: m.color, fontWeight: 600 } }, [m.label]);
}

// ── Curated ElevenLabs voices (no API call needed) ───────────────────────────

const CURATED_VOICES = [
  { id: "21m00Tcm4TlvDq8ikWAM", name: "Rachel",   tag: "Calm narrator · American" },
  { id: "pNInz6obpgDQGcFmaJgB", name: "Adam",     tag: "Deep narrator · American" },
  { id: "TxGEqnHWrfWFTfGW9XjX", name: "Josh",     tag: "Deep · American" },
  { id: "yoZ06aMxZJJ28mfd3POQ", name: "Sam",      tag: "Powerful · American" },
  { id: "AZnzlk1XvdvUeBnXmlld", name: "Domi",     tag: "Energetic · American" },
  { id: "EXAVITQu4vr4xnSDxMaL", name: "Bella",    tag: "Warm · American" },
  { id: "ErXwobaYiN019PkySvjV", name: "Antoni",   tag: "Smooth · American" },
  { id: "VR6AewLTigWG4xSOukaG", name: "Arnold",   tag: "Crisp · American" },
  { id: "MF3mGyEYCl7XYWbV9V6O", name: "Elli",     tag: "Emotional · American" },
  { id: "ThT5KcBeYPX3keUQqHPh", name: "Dorothy",  tag: "Warm · British" },
  { id: "IKne3meq5aSn9XLyUdCD", name: "Charlie",  tag: "Natural · Australian" },
  { id: "GBv7mTt0atIp3Br8iCZE", name: "Thomas",   tag: "Calm · American" },
  { id: "N2lVS1w4EtoT3dr4eOWO", name: "Callum",   tag: "Intense · Transatlantic" },
  { id: "TX3LPaxmHKxFdv7VOFE1", name: "Liam",     tag: "Articulate · American" },
  { id: "flq6f7yd4j25CU8A1bgZ", name: "Michael",  tag: "Orotund · American" },
];

// ── Voice section — now embedded in the wizard (mountDetail step 2) ──────────

function _buildVoiceSection_unused(channel, onSave) {
  let selectedId = channel.voice_id || "";
  const wrap = h("div", { class: "card", style: { marginBottom: "32px" } });

  function render(voices) {
    wrap.innerHTML = "";
    const cards = voices.map((v) => {
      const isSelected = v.id === selectedId;
      const card = h("div", {
        style: {
          padding: "10px 14px", borderRadius: "8px", cursor: "pointer",
          border: `2px solid ${isSelected ? "var(--accent,#6366f1)" : "var(--border)"}`,
          background: isSelected ? "var(--accent-subtle,#ede9fe)" : "var(--surface)",
          transition: "all 150ms",
        },
      }, [
        h("div", { style: { fontWeight: 700, fontSize: "13px", color: isSelected ? "var(--accent)" : "var(--ink-900)" } }, [v.name]),
        h("div", { class: "caption", style: { marginTop: "2px" } }, [v.tag]),
      ]);
      card.onclick = () => { selectedId = v.id; render(voices); };
      return card;
    });

    const pasteInput = h("input", { type: "text", placeholder: "Or paste any ElevenLabs voice ID…", value: selectedId && !voices.find((v) => v.id === selectedId) ? selectedId : "" });
    pasteInput.oninput = () => { if (pasteInput.value.trim()) selectedId = pasteInput.value.trim(); };

    const loadMoreBtn = h("button", { class: "btn ghost sm", html: `${icons.sparkle}<span>Load from API</span>` });
    loadMoreBtn.onclick = async () => {
      loadMoreBtn.disabled = true;
      try {
        const { voices: apiVoices, error } = await api.elevenlabsVoices();
        if (error || !apiVoices?.length) { toast(error || "No voices returned. Check API key.", { kind: "error" }); return; }
        const merged = [...voices];
        apiVoices.forEach((av) => {
          const tag = [av.labels?.accent, av.labels?.["use case"]].filter(Boolean).join(" · ");
          if (!merged.find((m) => m.id === av.id)) merged.push({ id: av.id, name: av.name, tag: tag || "—" });
        });
        render(merged);
      } catch (e) { toast(e.message, { kind: "error" }); }
      loadMoreBtn.disabled = false;
    };

    const saveBtn = h("button", {
      class: "btn primary sm",
      html: `${icons.check}<span>Save Voice</span>`,
      disabled: !selectedId,
    });
    saveBtn.onclick = async () => {
      if (!selectedId) return;
      saveBtn.disabled = true;
      try {
        await api.myChannelUpdate(channel.name, { voice_id: selectedId });
        channel.voice_id = selectedId;
        toast(`Voice saved.`);
        if (onSave) onSave(selectedId);
      } catch (e) { toast(e.message || "Save failed.", { kind: "error" }); }
      saveBtn.disabled = false;
    };

    const currentLabel = selectedId
      ? h("span", { style: { fontWeight: 600, color: "var(--accent)" } }, [voices.find((v) => v.id === selectedId)?.name || selectedId])
      : h("span", { class: "caption" }, ["None selected"]);

    wrap.appendChild(h("div", {}, [
      h("div", { style: { display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: "12px" } }, [
        h("div", { class: "field-label" }, ["Voice"]),
        h("div", { style: { display: "flex", alignItems: "center", gap: "8px" } }, [currentLabel, saveBtn]),
      ]),
      h("div", { style: { display: "grid", gridTemplateColumns: "repeat(auto-fill,minmax(160px,1fr))", gap: "8px", marginBottom: "12px" } }, cards),
      pasteInput,
      h("div", { style: { marginTop: "8px" } }, [loadMoreBtn]),
    ]));
  }

  render(CURATED_VOICES);
  return wrap;
}

// ── Channel list view ─────────────────────────────────────────────────────────

async function mountList(outlet, onSelectChannel) {
  outlet.innerHTML = "";

  outlet.appendChild(h("header", { class: "page-header" }, [
    h("h1", { class: "page-title" }, ["My Channels"]),
    h("div", { class: "page-subtitle" }, ["Create a channel, absorb a reference channel's DNA, then produce videos in that exact formula."]),
  ]));

  // ── Load trackers ─────────────────────────────────────────────────────────
  let trackers = [];
  try { trackers = (await api.trackers()).items || []; } catch { /* ignore */ }

  const defaultTracker = trackers.find((t) => t.is_default);
  const picker  = channelPicker({ items: trackers, selected: defaultTracker?.channel_id || "" });

  const nameInput  = h("input", { type: "text", placeholder: "Your channel name — e.g. OnlyGta6" });
  const nicheInput = h("input", { class: "input", type: "text", placeholder: "Your niche — e.g. GTA 6 gameplay & lore", style: { marginTop: "10px" } });
  const addBtn = h("button", { class: "btn primary", html: `${icons.plus}<span>Create</span>` });
  const errEl  = h("div", { class: "caption", style: { color: "var(--danger)", minHeight: "16px", marginTop: "6px" } });

  addBtn.onclick = async () => {
    errEl.textContent = "";
    const name  = nameInput.value.trim();
    const niche = nicheInput.value.trim();
    if (!name)  { errEl.textContent = "Channel name is required."; return; }
    if (!niche) { errEl.textContent = "Niche is required."; return; }

    const ref = trackers.find((t) => t.channel_id === picker.getValue());
    addBtn.disabled = true;
    try {
      await api.myChannelCreate({
        name, niche,
        reference_channel_id:   ref?.channel_id   || "",
        reference_channel_name: ref?.name         || "",
        reference_yt_url:       ref?.handle ? `https://youtube.com/@${ref.handle}` : "",
      });
      toast(`Channel "${name}" created.`);
      mountList(outlet, onSelectChannel);
    } catch (e) {
      errEl.textContent = e.message || "Failed to create channel.";
      addBtn.disabled = false;
    }
  };

  outlet.appendChild(h("div", { class: "card", style: { marginBottom: "40px" } }, [
    h("label", { class: "field-label" }, ["Reference channel (DNA source)"]),
    h("div", { style: { marginBottom: "12px" } }, [picker.el]),
    h("label", { class: "field-label" }, ["Your channel name"]),
    h("div", { class: "pill-input" }, [
      h("span", { class: "pi-icon", html: icons.track }),
      nameInput,
      addBtn,
    ]),
    nicheInput,
    errEl,
  ]));

  // ── Channel grid ──────────────────────────────────────────────────────────
  const gridWrap = h("div");
  outlet.appendChild(gridWrap);

  let channels = [];
  try { channels = (await api.myChannels()).items || []; } catch { toast("Could not load channels."); return; }

  if (!channels.length) {
    gridWrap.appendChild(h("div", { class: "empty" }, [
      h("div", { class: "empty-icon", html: icons.track }),
      h("div", { class: "empty-title" }, ["No channels yet"]),
      h("div", { class: "empty-body" }, ["Create your first channel above."]),
    ]));
    return;
  }

  const grid = h("div", { class: "thumb-grid" });
  const logoPollers = [];

  channels.forEach((ch) => {
    const card = h("div", { class: "thumb-card" });

    // Banner
    const bannerWrap = h("div", { style: { position: "relative" } });

    function renderBanner(logoPath, generating) {
      bannerWrap.innerHTML = "";
      if (logoPath) {
        const img = h("img", {
          class: "thumb-img",
          src: `/channel-logos/${encodeURIComponent(ch.name)}/logo.png`,
          alt: ch.name,
          style: { aspectRatio: "1 / 1", objectFit: "cover" },
        });
        img.onerror = () => renderBanner("", false);
        bannerWrap.appendChild(img);
      } else {
        const placeholder = h("div", {
          style: {
            width: "100%", aspectRatio: "16 / 9",
            background: ch.avatar_color || "#6366f1",
            display: "flex", alignItems: "center", justifyContent: "center",
            flexDirection: "column", gap: "8px",
            fontSize: "40px", fontWeight: "700",
            color: "rgba(255,255,255,0.9)", letterSpacing: "2px", userSelect: "none",
          },
        }, [
          (ch.name || "?").slice(0, 2).toUpperCase(),
          generating && h("div", { class: "caption", style: { fontSize: "11px", color: "rgba(255,255,255,0.7)", fontWeight: 400 } }, ["Generating logo…"]),
        ].filter(Boolean));
        bannerWrap.appendChild(placeholder);
      }
    }

    renderBanner(ch.logo_path, false);
    if (!ch.logo_path) {
      renderBanner("", true);
      const poller = setInterval(async () => {
        try {
          const s = await api.myChannelLogoStatus(ch.name);
          if (s.logo_path)             { clearInterval(poller); renderBanner(s.logo_path, false); }
          else if (s.status === "error") { clearInterval(poller); renderBanner("", false); }
        } catch { clearInterval(poller); }
      }, 3000);
      logoPollers.push(poller);
    }
    card.appendChild(bannerWrap);

    // Delete button
    const deleteBtn = document.createElement("button");
    deleteBtn.innerHTML = icons.trash;
    deleteBtn.style.cssText = "margin-left:auto;flex-shrink:0;background:none;border:none;cursor:pointer;padding:4px;color:var(--ink-400);line-height:1;";
    deleteBtn.onclick = async function(e) {
      e.stopPropagation(); e.preventDefault();
      logoPollers.forEach(clearInterval);
      this.disabled = true;
      await api.myChannelDelete(ch.name);
      toast(`"${ch.name}" deleted.`);
      mountList(outlet, onSelectChannel);
    };

    const meta = h("div", { class: "thumb-meta", style: { textAlign: "center", padding: "12px 10px 10px" } }, [
      h("div", { style: { display: "flex", alignItems: "flex-start", gap: "6px" } }, [
        h("div", {
          style: {
            flex: "1", fontSize: "17px", fontWeight: "700",
            letterSpacing: "0.06em", textTransform: "uppercase",
            color: "var(--ink-900,#111)", lineHeight: "1.2",
            textAlign: "center", wordBreak: "break-word",
          },
        }, [ch.name]),
        deleteBtn,
      ]),
      h("div", { class: "thumb-sub", style: { marginTop: "4px", textAlign: "center" } }, [ch.niche || "—"]),
      h("div", { style: { display: "flex", gap: "6px", flexWrap: "wrap", marginTop: "8px", alignItems: "center", justifyContent: "center" } }, [
        dnaBadge(ch),
        ch.reference_channel_name ? h("span", { class: "pill" }, [`via ${ch.reference_channel_name}`]) : null,
        h("span", { class: "pill" }, [`${ch.video_count || 0} video${ch.video_count !== 1 ? "s" : ""}`]),
      ].filter(Boolean)),
    ]);
    card.appendChild(meta);

    card.addEventListener("click", (e) => {
      if (deleteBtn.contains(e.target)) return;
      logoPollers.forEach(clearInterval);
      onSelectChannel(ch);
    });
    grid.appendChild(card);
  });
  gridWrap.appendChild(grid);
}

// ── DNA status section — now embedded in mountDetail wizard (step 1) ─────────

function _buildDnaSection_unused(channel, intervals) {
  const wrap = h("div", { class: "card", style: { marginBottom: "32px" } });
  const dnaReady = !!channel.dna_path;

  function renderIdle(refName) {
    wrap.innerHTML = "";
    wrap.appendChild(h("div", { style: { display: "flex", alignItems: "center", justifyContent: "space-between", gap: "12px", flexWrap: "wrap" } }, [
      h("div", {}, [
        h("div", { class: "field-label", style: { marginBottom: "4px" } }, ["Production DNA"]),
        h("div", { class: "caption" }, [
          dnaReady
            ? `DNA Ready — built from ${refName ? `@${refName}` : "reference channel"}.`
            : `Scan 3 top videos from ${refName ? `@${refName}` : "the reference channel"} to extract its production formula.`,
        ]),
      ]),
      h("div", { style: { display: "flex", gap: "8px", alignItems: "center" } }, [
        dnaReady && h("span", { style: { display: "inline-flex", alignItems: "center", gap: "6px", color: "var(--success,#10b981)", fontSize: "13px", fontWeight: 600 }, html: `${icons.check}<span>DNA Ready</span>` }),
        h("button", {
          class: "btn primary sm",
          html: `${icons.sparkle}<span>${dnaReady ? "Re-scan" : "Build DNA"}</span>`,
          onclick: () => startScan(),
        }),
      ].filter(Boolean)),
    ]));
  }

  function renderScanning(job) {
    wrap.innerHTML = "";
    const pct = job.total > 0 ? Math.round((job.progress / job.total) * 100) : 0;
    wrap.appendChild(h("div", {}, [
      h("div", { style: { display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: "10px" } }, [
        h("div", { class: "field-label" }, ["Building DNA…"]),
        h("span", { class: "caption" }, [`${job.progress || 0} / ${job.total || 3} videos`]),
      ]),
      h("div", { style: { height: "8px", borderRadius: "4px", background: "var(--surface-2,#f3f4f6)", overflow: "hidden", marginBottom: "8px" } }, [
        h("div", { style: { height: "100%", width: `${pct}%`, background: "var(--accent,#6366f1)", borderRadius: "4px", transition: "width 400ms ease" } }),
      ]),
      h("div", { class: "caption", style: { color: "var(--ink-500,#6b7280)" } }, [job.current || "Working…"]),
    ]));
  }

  function renderError(msg) {
    wrap.innerHTML = "";
    wrap.appendChild(h("div", { style: { display: "flex", alignItems: "center", justifyContent: "space-between", gap: "12px", flexWrap: "wrap" } }, [
      h("div", {}, [
        h("div", { class: "field-label", style: { color: "var(--danger)" } }, ["DNA Scan Failed"]),
        h("div", { class: "caption", style: { color: "var(--danger)" } }, [msg || "Unknown error."]),
      ]),
      h("button", { class: "btn ghost sm", html: `${icons.sparkle}<span>Retry</span>`, onclick: () => startScan() }),
    ]));
  }

  async function startScan() {
    try { await api.myChannelScan(channel.name); }
    catch (e) { toast(e.message || "Failed to start scan.", { kind: "error" }); return; }
    pollScan();
  }

  function pollScan() {
    if (intervals.scan) clearInterval(intervals.scan);
    intervals.scan = setInterval(async () => {
      if (!outlet.isConnected) { clearInterval(intervals.scan); intervals.scan = null; return; }
      let job;
      try { job = await api.myChannelScanStatus(channel.name); } catch { return; }
      if (job.status === "scanning") {
        renderScanning(job);
      } else if (job.status === "done") {
        clearInterval(intervals.scan); intervals.scan = null;
        channel.dna_path = "set";
        renderIdle("");
        if (intervals.onDnaReady) intervals.onDnaReady();
        toast("DNA built successfully!", { kind: "success" });
      } else if (job.status === "error") {
        clearInterval(intervals.scan); intervals.scan = null;
        renderError(job.error);
      }
    }, 2000);
  }

  (async () => {
    let refName = "";
    try {
      const trackers = (await api.trackers()).items || [];
      const ref = trackers.find((t) => t.channel_id === channel.reference_channel_id);
      refName = ref?.handle || ref?.name || channel.reference_channel_name || "";
    } catch { /* ignore */ }

    let job;
    try { job = await api.myChannelScanStatus(channel.name); } catch { job = { status: "idle" }; }

    if (job.status === "scanning") { renderScanning(job); pollScan(); }
    else if (job.status === "error") renderError(job.error);
    else renderIdle(refName);
  })();

  return wrap;
}

// ── Video workspace (full production flow for one video) ──────────────────────

async function mountVideoWorkspace(outlet, channel, video, onBack) {
  outlet.innerHTML = "";
  const ivals = {};

  function cleanup() {
    Object.values(ivals).forEach((id) => id && clearInterval(id));
  }

  const backBtn = h("button", {
    class: "btn ghost sm", style: { marginBottom: "28px" },
    html: `${icons.x}<span>Back to channel</span>`,
  });
  backBtn.onclick = () => { cleanup(); onBack(); };
  outlet.appendChild(backBtn);

  // Header
  outlet.appendChild(h("header", { class: "page-header", style: { marginBottom: "32px" } }, [
    h("h1", { class: "page-title plain", style: { fontSize: "22px", lineHeight: "1.25" } }, [video.topic]),
    h("div", { style: { display: "flex", gap: "8px", alignItems: "center", marginTop: "8px" } }, [
      statusPill(video.status),
      h("span", { class: "caption" }, [`${channel.name} · ${channel.niche}`]),
    ]),
  ]));

  const stagesWrap = h("div");
  outlet.appendChild(stagesWrap);

  // Reload video from DB to get latest state
  async function freshVideo() {
    try {
      const vids = (await api.myChannelVideos(channel.name)).items || [];
      return vids.find((v) => v.id === video.id) || video;
    } catch { return video; }
  }

  // ── Step router — shows ONE step at a time ───────────────────────────────
  // Status progression: idea → titled → thumbnail → scripted → producing → done
  function currentStep(v) {
    const s = v.status || "idea";
    if (!v.topic)                                              return "titles";
    // status "idea" with a topic = came from idea picker, title already set → skip titles
    if (s === "idea" || s === "titled")                        return "thumbnail";
    if (s === "thumbnail" || s === "scripted")                 return "script";
    if (s === "approved" || s === "producing" || s === "done") return "production";
    return "titles";
  }

  function stepBar(step) {
    const steps = [
      { key: "titles",     label: "Title",      svgIcon: icons.title    },
      { key: "thumbnail",  label: "Thumbnail",  svgIcon: icons.thumb    },
      { key: "script",     label: "Script",     svgIcon: icons.sparkle  },
      { key: "production", label: "Production", svgIcon: icons.idea     },
    ];
    const order = steps.map((s) => s.key);
    const cur   = order.indexOf(step);

    return h("div", {
      style: {
        display: "flex", gap: "4px", marginBottom: "36px",
        background: "var(--surface-2)", borderRadius: "var(--r-full)",
        padding: "5px",
      },
    }, steps.map((s, i) => {
      const done   = i < cur;
      const active = i === cur;
      const pill = h("div", {
        style: {
          flex: "1", padding: "11px 0", textAlign: "center",
          fontSize: "13px", fontWeight: active ? "700" : "500",
          borderRadius: "var(--r-full)",
          background:  active ? "var(--accent)" : "transparent",
          color:       active ? "#fff" : done ? "var(--ink-700)" : "var(--ink-400)",
          cursor:      done ? "pointer" : "default",
          transition:  "all 160ms var(--ease-out)",
          userSelect:  "none",
          display: "flex", alignItems: "center", justifyContent: "center", gap: "6px",
          boxShadow:   active ? "var(--shadow-2)" : "none",
        },
      }, [
        done
          ? h("span", { style: { fontSize: "12px", lineHeight: "1" } }, ["✓"])
          : h("span", { html: s.svgIcon, style: { lineHeight: "1", display: "flex", alignItems: "center" } }),
        h("span", {}, [s.label]),
      ]);
      return pill;
    }));
  }

  async function render() {
    const v = await freshVideo();
    stagesWrap.innerHTML = "";
    const step = currentStep(v);
    stagesWrap.appendChild(stepBar(step));

    // ── STEP: Titles ──────────────────────────────────────────────────────────
    if (step === "titles") {
      const card = h("div", { class: "card", style: { padding: "40px 40px 36px" } });
      card.appendChild(h("div", { style: { display: "flex", alignItems: "flex-start", gap: "18px", marginBottom: "28px" } }, [
        h("div", { style: {
          width: "52px", height: "52px", borderRadius: "14px", flexShrink: "0",
          background: "var(--accent-soft, #e7edff)",
          display: "flex", alignItems: "center", justifyContent: "center",
          color: "var(--accent)",
        }, html: icons.title }),
        h("div", {}, [
          h("div", { style: { fontWeight: "700", fontSize: "18px", color: "var(--ink-900)", lineHeight: "1.2" } }, ["Generate Title"]),
          h("div", { class: "caption", style: { marginTop: "5px", fontSize: "13px" } }, ["Generate title variants in your reference channel's exact voice, then pick one."]),
        ]),
      ]));

      const titlesJob = await api.myChannelVideoTitlesStatus(channel.name, v.id).catch(() => ({ status: "idle" }));
      const resultsWrap = h("div", { style: { marginTop: "16px" } });

      async function pollTitles() {
        if (ivals.titles) clearInterval(ivals.titles);
        ivals.titles = setInterval(async () => {
          if (!outlet.isConnected) { clearInterval(ivals.titles); ivals.titles = null; return; }
          const s = await api.myChannelVideoTitlesStatus(channel.name, v.id).catch(() => null);
          if (s && (s.status === "done" || s.status === "error")) {
            clearInterval(ivals.titles); ivals.titles = null;
            renderTitleResults(s);
          }
        }, 2000);
      }

      function renderTitleResults(job) {
        resultsWrap.innerHTML = "";
        if (job.error) { resultsWrap.appendChild(h("div", { class: "caption", style: { color: "var(--danger)" } }, [job.error])); return; }
        const groups = [
          { key: "channel_titles", label: `In ${channel.reference_channel_name || "reference channel"}'s voice` },
          { key: "outlier_titles", label: "Outlier / viral formulas" },
        ];
        groups.forEach(({ key, label }) => {
          const items = job[key] || [];
          if (!items.length) return;
          resultsWrap.appendChild(h("div", { class: "field-label", style: { margin: "12px 0 8px" } }, [label]));
          items.forEach((t) => {
            const row = h("div", {
              class: "iri-card",
              style: {
                padding: "10px 14px", borderRadius: "8px", cursor: "pointer", marginBottom: "6px",
                border: "1px solid var(--border)", background: "var(--surface)",
                display: "flex", justifyContent: "space-between", alignItems: "center",
              },
            }, [
              h("div", {}, [
                h("div", { style: { fontWeight: 600, fontSize: "14px" } }, [t.title]),
                h("div", { class: "caption", style: { marginTop: "2px" } }, [`${t.angle || ""} · ${t.char_count || t.title.length} chars`]),
              ]),
              h("button", { class: "btn primary sm", html: `${icons.check || ""}<span>Use</span>` }),
            ]);
            row.querySelector("button").addEventListener("click", async (e) => {
              e.stopPropagation();
              const btn = e.currentTarget;
              btn.disabled = true;
              try {
                await api.myChannelVideoUpdate(channel.name, v.id, { topic: t.title, status: "titled" });
                toast("Title set — moving to Thumbnail step.");
                render();
              } catch (ee) { toast(ee.message, { kind: "error" }); btn.disabled = false; }
            });
            resultsWrap.appendChild(row);
          });
        });
      }

      const genBtn = h("button", { class: "btn primary", html: `${icons.sparkle}<span>Generate Titles</span>` });
      genBtn.addEventListener("click", async () => {
        genBtn.disabled = true;
        genBtn.innerHTML = `<span class="spinner-sm"></span><span>Generating…</span>`;
        resultsWrap.innerHTML = "";
        try {
          await api.myChannelVideoTitles(channel.name, v.id);
          pollTitles();
        } catch (e) { toast(e.message, { kind: "error" }); }
        finally { genBtn.disabled = false; genBtn.innerHTML = `${icons.sparkle}<span>Generate Titles</span>`; }
      });

      // If titles already generated, show them immediately
      if (titlesJob.status === "done") renderTitleResults(titlesJob);
      else if (titlesJob.status === "running") { resultsWrap.appendChild(h("div", { class: "caption" }, ["Generating…"])); pollTitles(); }

      // Keep topic editable — user can also just type a title and continue
      const manualInput = h("input", { type: "text", placeholder: "Or type a title manually…", value: v.topic || "" });
      const manualBtn = h("button", { class: "btn ghost sm", html: `<span>Use this title →</span>` });
      manualBtn.addEventListener("click", async () => {
        const t = manualInput.value.trim();
        if (!t) return toast("Enter a title first.", { kind: "error" });
        manualBtn.disabled = true;
        try {
          await api.myChannelVideoUpdate(channel.name, v.id, { topic: t, status: "titled" });
          render();
        } catch (e) { toast(e.message, { kind: "error" }); manualBtn.disabled = false; }
      });

      card.appendChild(h("div", { style: { marginBottom: "12px" } }, [genBtn]));
      card.appendChild(resultsWrap);
      stagesWrap.appendChild(card);
      return; // ← only this step rendered
    }

    // ── STEP: Thumbnail — full generator ─────────────────────────────────────
    if (step !== "thumbnail") { renderScriptOrProduction(v, step); return; }

    const thumbStage = h("div", { class: "card", style: { marginBottom: "20px", padding: "40px 40px 36px" } });
    thumbStage.appendChild(h("div", { style: { display: "flex", alignItems: "flex-start", gap: "18px", marginBottom: "28px" } }, [
      h("div", { style: {
        width: "52px", height: "52px", borderRadius: "14px", flexShrink: "0",
        background: "#ede9fe",
        display: "flex", alignItems: "center", justifyContent: "center",
        color: "#7c3aed",
      }, html: icons.thumb }),
      h("div", {}, [
        h("div", { style: { fontWeight: "700", fontSize: "18px", color: "var(--ink-900)", lineHeight: "1.2" } }, ["Generate Thumbnail"]),
        h("div", { class: "caption", style: { marginTop: "5px", fontSize: "13px" } }, ["Generate a thumbnail in your reference channel's visual DNA. Pick a variant to continue."]),
      ]),
    ]));

    // Title input — pre-filled, editable
    const titleEl = h("textarea", {
      class: "textarea", rows: 2,
      placeholder: "Video title",
    }, [v.topic || ""]);

    // Hook preview
    const hookEl    = h("span", { class: "value", id: "vthook" }, ["—"]);
    const pairingEl = h("span", { class: "score", id: "vtpairing" }, [""]);

    // Sketch
    let sketchFile = null, sketchHelp = "";
    const sketchChip = h("button", { type: "button", class: "file-chip" }, [h("span", { html: icons.refine }), " Sketch"]);
    const sketchInput = {
      get files() { return sketchFile ? [sketchFile] : []; },
      clear() { sketchFile = null; sketchHelp = ""; sketchChip.classList.remove("has-file"); },
    };
    sketchChip.addEventListener("click", (e) => {
      e.preventDefault();
      openSketchPad({
        initialBlob: sketchFile || null,
        onUse: (file, helpText) => {
          sketchFile = file; sketchHelp = helpText || "";
          sketchChip.classList.add("has-file");
          toast("Sketch saved.", { kind: "success" });
        },
      });
    });

    const refInput = h("input", { type: "file", accept: "image/*" });
    const refChip  = h("label", { class: "file-chip" }, [h("span", { html: icons.plus }), " Reference image", refInput]);
    refInput.addEventListener("change", () => refChip.classList.toggle("has-file", !!refInput.files[0]));

    const noTextToggle = h("label", { class: "toggle" }, [
      h("input", { type: "checkbox", id: "vtnotext" }),
      h("span", { class: "toggle-switch" }),
      "No text",
    ]);

    const countSel = h("select", { class: "select count-select" }, [
      h("option", { value: "1" }, ["1"]),
      h("option", { value: "2", selected: "selected" }, ["2"]),
      h("option", { value: "4" }, ["4"]),
    ]);

    // Channel picker — pre-selected to reference channel
    let trackers = [];
    try { trackers = (await api.trackers()).items || []; } catch { /* ignore */ }
    const picker = channelPicker({
      items: trackers,
      selected: channel.reference_channel_id || "",
      onChange: () => refreshHookPreview(),
    });

    const genBtn = h("button", { class: "btn huge" }, [
      h("span", { html: icons.sparkle }), h("span", {}, ["Generate"]),
    ]);

    thumbStage.appendChild(h("div", {}, [
      h("div", { style: { display: "flex", alignItems: "center", gap: "8px", marginBottom: "14px" } }, [
        h("span", { class: "caption" }, ["Style channel:"]),
        h("span", { style: { fontSize: "13px", fontWeight: 600, color: "var(--ink-700)" } }, [channel.reference_channel_name || "reference channel"]),
      ]),
      picker.el,
      h("div", { style: { height: "16px" } }),
      titleEl,
      h("div", { class: "hook-preview", style: { marginTop: "8px", marginBottom: "16px" } }, [
        h("span", { class: "label" }, ["Auto hook"]), hookEl, pairingEl,
      ]),
      h("div", { class: "form-row", style: { marginBottom: "20px", alignItems: "center" } }, [
        sketchChip, refChip, noTextToggle,
        h("div", { class: "grow" }),
        countSel, genBtn,
      ]),
    ]));

    const progressPanel = h("div", { class: "progress-panel hidden" });
    thumbStage.appendChild(progressPanel);

    const variantGrid = h("div");
    thumbStage.appendChild(variantGrid);

    stagesWrap.appendChild(thumbStage);

    // Hook preview debounce
    let hookDebounce;
    const refreshHookPreview = () => {
      clearTimeout(hookDebounce);
      hookDebounce = setTimeout(async () => {
        const title = titleEl.value.trim();
        if (!title) { hookEl.textContent = "—"; pairingEl.textContent = ""; return; }
        try {
          const r = await api.hook(title, picker.getValue());
          const lines = (r.hook || "").split("\n").filter(Boolean);
          hookEl.textContent = lines[0] || "—";
          pairingEl.textContent = `${r.smart ? "channel-DNA · " : ""}pairing ${r.pairing.score}/10`;
          pairingEl.classList.toggle("good", r.pairing.score >= 7);
          pairingEl.classList.toggle("bad",  r.pairing.score < 4);
        } catch { /* ignore */ }
      }, 400);
    };
    titleEl.addEventListener("input", refreshHookPreview);
    if (v.topic) titleEl.dispatchEvent(new Event("input"));

    // Skeleton tiles
    function renderSkeletons(n) {
      variantGrid.innerHTML = "";
      const cols = n === 1 ? 1 : 2;
      const grid = h("div", { class: "variant-grid", style: { "--cols": String(cols) } });
      for (let i = 0; i < n; i++) {
        grid.appendChild(h("div", { class: "variant-tile loading", "data-variant": String(i + 1) }, [
          h("div", { class: "variant-spinner" }),
          h("div", { class: "variant-timer", "data-start": String(Date.now()) }, ["0s"]),
        ]));
      }
      variantGrid.appendChild(grid);
      const iv = setInterval(() => {
        if (!grid.isConnected) return clearInterval(iv);
        grid.querySelectorAll(".variant-tile.loading .variant-timer").forEach((t) => {
          t.textContent = `${Math.floor((Date.now() - parseInt(t.dataset.start, 10)) / 1000)}s`;
        });
      }, 500);
    }

    // Open AI editor (same as main generator)
    function openEditor(imageUrl, parentTile) {
      const storageKey = `editor_versions::${imageUrl}`;
      let versions;
      try { versions = JSON.parse(sessionStorage.getItem(storageKey) || "null"); } catch { versions = null; }
      if (!versions?.length) versions = [{ url: imageUrl, label: "Original", instruction: "" }];
      let currentIdx = versions.length - 1;
      const persist = () => { try { sessionStorage.setItem(storageKey, JSON.stringify(versions)); } catch {} };
      const backdrop = h("div", { class: "editor-backdrop", onclick: (e) => { if (e.target === backdrop) backdrop.remove(); } });
      const stageImg = h("img", { class: "editor-img", src: versions[currentIdx].url, alt: "" });
      const versionList = h("div", { class: "editor-versions" });
      const renderVersions = () => {
        versionList.innerHTML = "";
        versions.forEach((vv, i) => {
          const chip = h("button", {
            class: `editor-version-chip${i === currentIdx ? " active" : ""}`,
            onclick: () => { currentIdx = i; stageImg.src = vv.url; renderVersions(); },
          }, [h("img", { src: vv.url, class: "editor-version-thumb", alt: "" }), h("span", { class: "editor-version-label" }, [vv.label])]);
          versionList.appendChild(chip);
        });
      };
      renderVersions();
      const promptBox = h("textarea", { class: "editor-prompt", placeholder: "Describe the edit…", rows: 5 });
      const addImgInput = h("input", { type: "file", accept: "image/*" });
      const addImgChip  = h("label", { class: "file-chip" }, [h("span", { html: icons.plus }), " Add reference image", addImgInput]);
      addImgInput.addEventListener("change", () => addImgChip.classList.toggle("has-file", !!addImgInput.files[0]));
      const submit = h("button", { class: "btn primary", html: `${icons.refine}<span>Generate edit</span>` });
      const statusLine = h("div", { class: "editor-status" });
      submit.addEventListener("click", async () => {
        const instr = promptBox.value.trim();
        if (!instr) { toast("Write what to change", { kind: "error" }); return; }
        submit.disabled = true;
        submit.innerHTML = `<span class="spinner-sm"></span><span>Generating edit…</span>`;
        statusLine.textContent = "Refining…";
        try {
          const fd = new FormData();
          fd.append("image_url", versions[currentIdx].url);
          fd.append("instruction", instr);
          if (addImgInput.files[0]) fd.append("reference", addImgInput.files[0]);
          const r = await api.refine(fd);
          if (r.error) { toast(r.error, { kind: "error" }); return; }
          versions.push({ url: r.url, label: `Edit ${versions.length}`, instruction: instr });
          currentIdx = versions.length - 1;
          stageImg.src = r.url;
          renderVersions(); persist();
          promptBox.value = ""; statusLine.textContent = `Edit ${versions.length - 1} ready.`;
        } catch (e) { toast(e.message, { kind: "error" }); }
        finally { submit.disabled = false; submit.innerHTML = `${icons.refine}<span>Generate edit</span>`; }
      });
      const applyBtn = h("button", { class: "btn primary", html: `${icons.check || ""}<span>Apply to thumbnail</span>` });
      applyBtn.addEventListener("click", () => {
        if (parentTile) {
          parentTile.dataset.url = versions[currentIdx].url;
          const img = parentTile.querySelector(".variant-img");
          if (img) img.src = versions[currentIdx].url;
          toast("Applied.", { kind: "success" });
        }
        backdrop.remove();
      });
      const dlBtn = h("a", { class: "btn sm", href: versions[currentIdx].url, download: "", html: `${icons.download}<span>Download</span>` });
      stageImg.addEventListener("load", () => { dlBtn.href = versions[currentIdx].url; });
      backdrop.appendChild(h("div", { class: "editor-panel" }, [
        h("div", { class: "editor-stage" }, [stageImg]),
        h("div", { class: "editor-sidebar" }, [
          h("div", { class: "editor-title" }, ["Edit Thumbnail"]),
          h("div", { class: "editor-label" }, ["Versions"]),
          versionList,
          h("div", { class: "editor-label", style: { marginTop: "16px" } }, ["Your prompt"]),
          promptBox,
          h("div", { style: { marginTop: "12px", marginBottom: "14px" } }, [addImgChip]),
          submit, statusLine,
          h("div", { class: "editor-actions-row" }, [applyBtn, dlBtn]),
        ]),
        h("button", { class: "editor-close", onclick: () => backdrop.remove(), html: icons.x }),
      ]));
      document.body.appendChild(backdrop);
      setTimeout(() => promptBox.focus(), 50);
    }

    // Fill a variant tile when it arrives
    function fillVariant(data) {
      const grid = variantGrid.querySelector(".variant-grid");
      if (!grid) return;
      const tile = grid.querySelector(`.variant-tile[data-variant="${data.variant}"]`);
      if (!tile) return;
      tile.classList.remove("loading");
      tile.innerHTML = "";
      if (data.error || !data.url) {
        tile.classList.add("error");
        tile.appendChild(h("div", { class: "variant-err" }, [data.error || "Failed"]));
        return;
      }
      tile.dataset.url = data.url;
      const img = h("img", { class: "variant-img", src: data.url, alt: "", loading: "eager" });
      img.addEventListener("click", () => openEditor(tile.dataset.url, tile));

      // "Use this" button — saves to the video and re-renders to unlock script
      const useBtn = h("button", {
        class: "btn primary sm",
        style: { position: "absolute", bottom: "8px", left: "50%", transform: "translateX(-50%)", whiteSpace: "nowrap" },
        html: `${icons.check || ""}<span>Use this</span>`,
      });
      useBtn.addEventListener("click", async (e) => {
        e.stopPropagation();
        useBtn.disabled = true;
        useBtn.innerHTML = `<span class="spinner-sm"></span><span>Saving…</span>`;
        try {
          // Save the URL as the video's thumbnail_path via a PATCH
          await api.myChannelVideoUpdate(channel.name, v.id, { thumbnail_path: tile.dataset.url, status: "thumbnail" });
          toast("Thumbnail saved — moving to Script step.", { kind: "success" });
          render();
        } catch (ee) {
          toast(ee.message || "Save failed.", { kind: "error" });
          useBtn.disabled = false;
          useBtn.innerHTML = `${icons.check || ""}<span>Use this</span>`;
        }
      });

      const dots = `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="currentColor" width="18" height="18"><circle cx="5" cy="12" r="2"/><circle cx="12" cy="12" r="2"/><circle cx="19" cy="12" r="2"/></svg>`;
      const menuBtn = h("button", {
        class: "variant-menu-btn", title: "More",
        onclick: (e) => {
          e.stopPropagation();
          document.querySelectorAll(".tile-menu").forEach((m) => m.remove());
          const menu = h("div", { class: "tile-menu" }, [
            h("button", { class: "tile-menu-item", onclick: () => { const a = document.createElement("a"); a.href = tile.dataset.url; a.download = ""; a.click(); } },
              [h("span", { class: "tile-menu-icon", html: icons.download }), h("span", {}, ["Download"])]),
            h("button", { class: "tile-menu-item", onclick: () => openEditor(tile.dataset.url, tile) },
              [h("span", { class: "tile-menu-icon", html: icons.refine }), h("span", {}, ["Edit with AI"])]),
          ]);
          document.body.appendChild(menu);
          const r2 = e.currentTarget.getBoundingClientRect();
          menu.style.top = `${r2.bottom + window.scrollY + 6}px`;
          menu.style.left = `${r2.right + window.scrollX - menu.offsetWidth}px`;
          setTimeout(() => document.addEventListener("click", () => menu.remove(), { once: true }), 0);
        },
        html: dots,
      });
      tile.style.position = "relative";
      tile.appendChild(img);
      tile.appendChild(menuBtn);
      tile.appendChild(useBtn);
    }

    // Generate button
    let activeAbort = null, activeJobId = null;
    genBtn.addEventListener("click", async () => {
      if (genBtn.classList.contains("stop")) {
        if (activeJobId) try { await fetch(`/api/generate/${activeJobId}/cancel`, { method: "POST" }); } catch {}
        if (activeAbort) activeAbort.abort();
        return;
      }
      const title = titleEl.value.trim();
      if (!title) return toast("Enter a title", { kind: "error" });
      const ch = picker.getValue();
      if (!ch) return toast("Pick a channel first", { kind: "error" });

      const nVar = parseInt(countSel.value, 10) || 2;
      const fd = new FormData();
      fd.append("title", title);
      fd.append("channel", ch);
      fd.append("style_channel_id", ch);
      fd.append("no_text", thumbStage.querySelector("#vtnotext")?.checked ? "true" : "false");
      fd.append("variants", String(nVar));
      if (sketchInput.files[0]) fd.append("sketch", sketchInput.files[0]);
      if (sketchHelp) fd.append("sketch_help", sketchHelp);
      if (refInput.files[0]) fd.append("reference", refInput.files[0]);

      genBtn.innerHTML = `<span class="spinner-sm"></span><span>Stop</span>`;
      genBtn.classList.add("stop");
      progressPanel.classList.remove("hidden");
      progressPanel.innerHTML = "";
      renderSkeletons(nVar);

      const log = (msg, cls) => {
        progressPanel.appendChild(h("div", { class: `progress-line ${cls || ""}` }, [msg]));
        progressPanel.scrollTop = progressPanel.scrollHeight;
      };
      log("Starting pipeline…");
      activeAbort = new AbortController();
      try {
        const { job_id, error } = await api.generate(fd);
        if (error) throw new Error(error);
        activeJobId = job_id;
        await streamJob(`/api/progress/${job_id}`, {
          onMessage: (d) => d.msg && log(d.msg),
          onVariant: (d) => fillVariant(d),
          signal: activeAbort.signal,
        });
        log("Done.", "done");
      } catch (e) {
        if (e.name !== "AbortError") { log(`Failed: ${e.message}`, "error"); toast("Generation failed", { kind: "error" }); }
        else log("Stopped.", "error");
      } finally {
        activeJobId = null; activeAbort = null;
        genBtn.innerHTML = `<span>${icons.sparkle}</span><span>Generate</span>`;
        genBtn.classList.remove("stop");
      }
    });

    // Thumbnail step done — render script/production on next render() call
    // (the "Use this" button saves status:"thumbnail" and calls render())
  } // end of render()

  // ── Script + Production steps ─────────────────────────────────────────────
  async function renderScriptOrProduction(v, step) {
    if (step === "script") {
      const scriptStage = h("div", { class: "card", style: { marginBottom: "20px", padding: "40px 40px 36px" } });
      scriptStage.appendChild(h("div", { style: { display: "flex", alignItems: "flex-start", gap: "18px", marginBottom: "28px" } }, [
        h("div", { style: {
          width: "52px", height: "52px", borderRadius: "14px", flexShrink: "0",
          background: "#dbeafe",
          display: "flex", alignItems: "center", justifyContent: "center",
          color: "#1d4ed8",
        }, html: icons.sparkle }),
        h("div", {}, [
          h("div", { style: { fontWeight: "700", fontSize: "18px", color: "var(--ink-900)", lineHeight: "1.2" } }, ["Script"]),
          h("div", { class: "caption", style: { marginTop: "5px", fontSize: "13px" } }, ["Claude writes a full script using channel DNA formula, hook patterns and VO style. Review, edit, then approve to unlock production."]),
        ]),
      ]));
      const scriptJob   = await api.myChannelVideoScriptStatus(channel.name, v.id).catch(() => ({ status: "idle" }));
      const scriptReady = v.script_status === "ready" || v.script_status === "approved";
      const approved    = v.script_status === "approved";

    if (scriptJob.status === "generating") {
      // Inject the writing-dots keyframe once
      if (!document.getElementById("_kf_writing")) {
        const s = document.createElement("style");
        s.id = "_kf_writing";
        s.textContent = `
          @keyframes writingDots {
            0%,20%  { content:"." }
            40%     { content:".." }
            60%,100%{ content:"..." }
          }
          .writing-dots::after {
            content: "...";
            animation: writingDots 1.4s steps(1,end) infinite;
          }
          @keyframes writingPulse {
            0%,100% { opacity: 1; }
            50%     { opacity: 0.45; }
          }
          .writing-pulse { animation: writingPulse 2s ease-in-out infinite; }
        `;
        document.head.appendChild(s);
      }
      const loader = h("div", { style: { display: "flex", flexDirection: "column", alignItems: "center", gap: "20px", padding: "48px 24px" } }, [
        h("div", { style: { display: "flex", gap: "10px" } }, [1,2,3].map((i) =>
          h("div", { style: {
            width: "12px", height: "12px", borderRadius: "50%",
            background: "var(--accent,#6366f1)",
            animation: `writingPulse 1.4s ease-in-out ${(i-1)*0.22}s infinite`,
          }})
        )),
        h("div", { style: { fontWeight: 700, fontSize: "16px", color: "var(--ink)" } }, [
          h("span", {}, ["Writing your script"]),
          h("span", { class: "writing-dots" }),
        ]),
        h("div", { class: "caption", style: { textAlign: "center", maxWidth: "360px" } }, [
          "Claude is crafting a full script using the channel DNA formula, hook patterns, and VO style. ~30–60 seconds.",
        ]),
      ]);
      scriptStage.appendChild(loader);
      pollScript();
    } else if (scriptReady) {
      // Show editable script
      let scriptData = null;
      try {
        const res = await api.myChannelVideoScriptGet(channel.name, v.id);
        scriptData = res.script;
      } catch { /* ignore */ }

      const scriptJson = JSON.stringify(scriptData, null, 2);
      // Hidden textarea — used only for save/approve, never shown
      const textarea = h("textarea", { style: { display: "none" } });
      textarea.value = scriptJson;

      // ── Narration reader (default view) ──────────────────────────────────
      const narrationView = h("div", {
        style: {
          maxHeight: "600px", overflowY: "auto", padding: "12px 4px 20px",
        },
      });

      const buildNarration = () => {
        narrationView.innerHTML = "";
        (scriptData?.sections || []).forEach((sec, si) => {
          if (si > 0) {
            narrationView.appendChild(h("hr", {
              style: { border: "none", borderTop: "1px solid var(--border)", margin: "28px 0" },
            }));
          }
          narrationView.appendChild(h("div", {
            style: {
              fontSize: "10px", fontWeight: 700, letterSpacing: "0.12em",
              textTransform: "uppercase", color: "var(--accent)",
              marginBottom: "18px",
            },
          }, [sec.label || sec.id]));
          (sec.scenes || []).forEach((sc) => {
            const sceneWrap = h("div", { style: { marginBottom: "22px" } }, [
              h("div", {
                style: {
                  fontSize: "10px", fontWeight: 600, letterSpacing: "0.06em",
                  textTransform: "uppercase", color: "var(--ink-400)",
                  marginBottom: "6px",
                },
              }, [`Scene ${sc.idx}`]),
              h("div", {
                style: {
                  fontFamily: "'Bricolage Grotesque', var(--font-sans)",
                  fontSize: "20px", fontWeight: 500, lineHeight: 1.55,
                  color: "var(--ink-900)", letterSpacing: "-0.01em",
                },
              }, [sc.vo || ""]),
            ]);
            narrationView.appendChild(sceneWrap);
          });
        });
      };
      buildNarration();

      // ── Prompt sheet (toggle view) ────────────────────────────────────────
      const promptSheet = h("div", { style: { display: "none", maxHeight: "600px", overflowY: "auto", padding: "12px 4px 20px" } });

      const buildPromptSheet = () => {
        promptSheet.innerHTML = "";
        (scriptData?.sections || []).forEach((sec) => {
          promptSheet.appendChild(h("div", { style: { marginBottom: "20px" } }, [
            h("div", {
              style: {
                fontSize: "10px", fontWeight: 700, letterSpacing: "0.12em",
                textTransform: "uppercase", color: "var(--accent)", marginBottom: "10px",
              },
            }, [sec.label || sec.id]),
            ...((sec.scenes || []).map((sc) =>
              h("div", {
                style: {
                  padding: "10px 12px", background: "var(--surface-2)", borderRadius: "8px",
                  marginBottom: "8px", borderLeft: "3px solid var(--accent)",
                },
              }, [
                h("div", {
                  style: {
                    display: "flex", gap: "8px", alignItems: "center",
                    marginBottom: "6px",
                  },
                }, [
                  h("span", { style: { fontWeight: 700, fontSize: "11px", color: "var(--ink-900)" } }, [`Scene ${sc.idx}`]),
                  h("span", {
                    style: {
                      fontSize: "10px", fontWeight: 600, letterSpacing: "0.06em",
                      textTransform: "uppercase", color: "var(--ink-400)",
                      background: "var(--surface-3, var(--surface-2))",
                      padding: "1px 6px", borderRadius: "4px",
                    },
                  }, [sc.camera_move || "static"]),
                ]),
                h("div", { style: { fontSize: "12px", color: "var(--ink-600)", marginBottom: "6px", fontStyle: "italic" } }, [sc.vo || ""]),
                h("div", { style: { fontSize: "12px", color: "var(--ink-500)" } }, [sc.image_prompt || ""]),
              ])
            )),
          ]));
        });
      };

      // ── View toggle ───────────────────────────────────────────────────────
      let showingPromptSheet = false;
      const promptToggle = h("button", {
        class: "btn ghost sm",
        html: `${icons.sparkle}<span>Prompt Sheet</span>`,
      });
      promptToggle.onclick = () => {
        showingPromptSheet = !showingPromptSheet;
        if (showingPromptSheet) {
          narrationView.style.display = "none";
          promptSheet.style.display = "block";
          promptToggle.innerHTML = `${icons.sparkle}<span>Audio Script</span>`;
          if (!promptSheet.children.length) buildPromptSheet();
        } else {
          promptSheet.style.display = "none";
          narrationView.style.display = "block";
          promptToggle.innerHTML = `${icons.sparkle}<span>Prompt Sheet</span>`;
        }
      };

      const saveBtn = h("button", { class: "btn ghost sm", html: `${icons.check}<span>Save edits</span>` });
      saveBtn.onclick = async () => {
        saveBtn.disabled = true;
        try {
          await api.myChannelVideoScriptSave(channel.name, v.id, textarea.value);
          toast("Script saved.");
        } catch (e) { toast(e.message || "Save failed.", { kind: "error" }); }
        saveBtn.disabled = false;
      };

      const approveBtn = h("button", { class: "btn primary", html: `${icons.check}<span>Approve Script → Start Production</span>`, disabled: approved });
      approveBtn.onclick = async () => {
        approveBtn.disabled = true;
        try {
          await api.myChannelVideoScriptSave(channel.name, v.id, textarea.value);
          await api.myChannelVideoScriptApprove(channel.name, v.id);
          await api.myChannelVideoUpdate(channel.name, v.id, { status: "producing" });
          toast("Script approved! Starting production.");
          render();
        } catch (e) { toast(e.message || "Approve failed.", { kind: "error" }); approveBtn.disabled = false; }
      };

      // Inline regenerate bar (replaces native prompt())
      const regenBar = h("div", {
        style: {
          display: "none", alignItems: "center", gap: "8px",
          marginTop: "10px", padding: "10px 12px",
          background: "var(--surface-2)", borderRadius: "8px",
          border: "1px solid var(--border)",
        },
      });
      const regenDurInput = h("input", {
        type: "text",
        class: "input",
        style: { width: "96px", flexShrink: 0 },
        value: channel.default_duration || "10min",
        placeholder: "10min",
      });
      const regenConfirmBtn = h("button", { class: "btn primary sm", html: `${icons.sparkle}<span>Regenerate</span>` });
      const regenCancelBtn  = h("button", { class: "btn ghost sm",   html: `${icons.x}<span>Cancel</span>` });
      regenBar.appendChild(h("span", { style: { fontSize: "13px", color: "var(--ink-600)", flexShrink: 0 } }, ["Duration:"]));
      regenBar.appendChild(regenDurInput);
      regenBar.appendChild(regenConfirmBtn);
      regenBar.appendChild(regenCancelBtn);

      regenConfirmBtn.onclick = async () => {
        regenConfirmBtn.disabled = true;
        const dur = regenDurInput.value.trim() || "10min";
        try {
          await api.myChannelVideoScript(channel.name, v.id, { duration_hint: dur });
          await api.myChannelVideoUpdate(channel.name, v.id, { script_status: "none" });
          render();
        } catch (e) { toast(e.message || "Failed.", { kind: "error" }); regenConfirmBtn.disabled = false; }
      };
      regenCancelBtn.onclick = () => {
        regenBar.style.display = "none";
        rejectBtn.style.display = "";
      };

      const rejectBtn = h("button", {
        class: "btn ghost sm",
        html: `${icons.x}<span>Reject & Regenerate</span>`,
      });
      rejectBtn.onclick = () => {
        rejectBtn.style.display = "none";
        regenBar.style.display = "flex";
        regenDurInput.focus();
        regenDurInput.select();
      };

      scriptStage.appendChild(h("div", {}, [
        h("div", { style: { display: "flex", alignItems: "center", justifyContent: "flex-end", marginBottom: "16px" } }, [
          approved && h("span", { style: { fontSize: "13px", color: "var(--positive, #10b981)", fontWeight: 600, marginRight: "auto" } }, ["✓ Approved"]),
          promptToggle,
        ].filter(Boolean)),
        narrationView,
        promptSheet,
        textarea,
        h("div", { style: { display: "flex", gap: "8px", marginTop: "16px", flexWrap: "wrap" } }, [
          approveBtn, !approved && rejectBtn,
        ].filter(Boolean)),
        !approved && regenBar,
      ]));
    } else {
      // Ready to generate script
      const durSelect = h("select", { class: "select" }, [
        h("option", { value: "5min" },  ["5 minutes"]),
        h("option", { value: "10min", selected: "selected" }, ["10 minutes"]),
        h("option", { value: "20min" }, ["20 minutes"]),
      ]);
      // Set default from channel
      if (channel.default_duration) durSelect.value = channel.default_duration;

      const scriptBtn = h("button", { class: "btn primary", html: `${icons.sparkle}<span>Generate Script</span>` });
      scriptBtn.onclick = async () => {
        scriptBtn.disabled = true;
        try {
          await api.myChannelVideoScript(channel.name, v.id, { duration_hint: durSelect.value });
          render();
        } catch (e) { toast(e.message || "Failed.", { kind: "error" }); scriptBtn.disabled = false; }
      };
      scriptStage.appendChild(h("div", {}, [
        h("div", { class: "field-label", style: { marginBottom: "8px" } }, ["Script"]),
        h("div", { class: "caption", style: { marginBottom: "10px" } }, ["Claude will write a full script using the channel DNA formula."]),
        h("label", { class: "field-label", style: { fontSize: "12px" } }, ["Duration:"]),
        durSelect,
        h("div", { style: { marginTop: "10px" } }, [scriptBtn]),
        scriptJob.error ? h("div", { class: "caption", style: { color: "var(--danger)", marginTop: "8px" } }, [scriptJob.error]) : null,
      ].filter(Boolean)));
    }
      stagesWrap.appendChild(scriptStage);
      return; // only script step shown
    }

    // ── STEP: Production ───────────────────────────────────────────────────
    const approved = v.script_status === "approved" || v.status === "approved";
    if (approved || v.status === "producing" || v.status === "done") {
      const prodStage = h("div", { class: "card", style: { padding: "40px 40px 36px" } });
      prodStage.appendChild(h("div", { style: { display: "flex", alignItems: "flex-start", gap: "18px", marginBottom: "32px" } }, [
        h("div", { style: {
          width: "52px", height: "52px", borderRadius: "14px", flexShrink: "0",
          background: "#d1fae5",
          display: "flex", alignItems: "center", justifyContent: "center",
          color: "#10b981",
        }, html: icons.idea }),
        h("div", {}, [
          h("div", { style: { fontWeight: "700", fontSize: "18px", color: "var(--ink-900)", lineHeight: "1.2" } }, ["Section Production"]),
          h("div", { class: "caption", style: { marginTop: "5px", fontSize: "13px" } }, ["Produce each section in sequence. Approve each one to unlock the next. Redo any section if needed."]),
        ]),
      ]));

      let sectionsData = [];
      try {
        sectionsData = (await api.myChannelProduceSections(channel.name, v.id)).sections || [];
      } catch { /* ignore */ }

      if (!sectionsData.length) {
        prodStage.appendChild(h("div", { style: { padding: "32px 0", textAlign: "center" } }, [
          h("div", { style: { fontSize: "32px", marginBottom: "12px" } }, ["🎬"]),
          h("div", { style: { fontWeight: 700, fontSize: "15px", marginBottom: "6px" } }, ["Script Approved — Ready to Produce"]),
          h("div", { class: "caption", style: { maxWidth: "340px", margin: "0 auto" } }, [
            "Your script sections will appear here. Approve the script above to unlock production.",
          ]),
        ]));
      } else {
        // Determine active section — strict sequential gate:
        // A section unlocks only when all previous are "approved".
        // "produced" = done but waiting for user approval.
        // "approved" = user explicitly approved, next unlocks.
        const activeIdx = sectionsData.findIndex(
          (s) => s.status !== "approved"
        );
        const allApproved = activeIdx === -1;

        sectionsData.forEach((sec, idx) => {
          const isActive  = idx === activeIdx;
          const isLocked  = activeIdx !== -1 && idx > activeIdx;
          const secStatus = sec.status; // pending | produced | approved
          const job       = sec.job || {};
          const isRunning = job.status === "producing";
          const isProduced = secStatus === "produced" || (job.status === "done" && job.mp4_url);
          const isApproved = secStatus === "approved";

          const secCard = h("div", {
            style: {
              border: `1px solid ${isActive && isProduced ? "var(--accent,#6366f1)" : "var(--line)"}`,
              borderRadius: "14px", padding: "24px 28px", marginBottom: "16px",
              opacity: isLocked ? "0.4" : "1",
              transition: "opacity 200ms",
              background: isApproved ? "var(--surface-2)" : "var(--surface)",
            },
          });

          // Header row
          const statusTag = isApproved
            ? h("span", { style: { fontSize: "12px", color: "var(--success,#10b981)", fontWeight: 600 } }, ["✓ Approved"])
            : isProduced
              ? h("span", { style: { fontSize: "12px", color: "var(--accent)", fontWeight: 600 } }, ["Waiting for approval"])
              : isRunning
                ? h("span", { class: "caption" }, ["Producing…"])
                : isLocked
                  ? h("span", { class: "caption" }, ["🔒 Locked"])
                  : h("span", { class: "caption" }, ["Ready"]);

          secCard.appendChild(h("div", { style: { display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: "12px" } }, [
            h("div", {}, [
              h("div", { style: { fontWeight: 700, fontSize: "14px" } }, [sec.label]),
              h("div", { style: { display: "flex", gap: "8px", alignItems: "center", marginTop: "4px" } }, [
                h("div", { class: "caption" }, [`${sec.scene_count} scene${sec.scene_count !== 1 ? "s" : ""}`]),
                statusTag,
              ]),
            ]),
            !isLocked && h("div", { style: { display: "flex", gap: "8px" } }, [
              // Produce button — only for active section, not yet produced
              isActive && !isProduced && !isRunning && h("button", {
                class: "btn primary sm",
                html: `${icons.sparkle}<span>Produce</span>`,
                onclick: async (e) => {
                  e.target.closest("button").disabled = true;
                  try {
                    await api.myChannelProduceSection(channel.name, v.id, sec.id);
                    pollSection(sec.id, secCard, () => render());
                  } catch (err) { toast(err.message || "Failed.", { kind: "error" }); e.target.closest("button").disabled = false; }
                },
              }),
              // Approve button — shown after produced, before approved
              isActive && isProduced && !isApproved && h("button", {
                class: "btn primary sm",
                html: `${icons.check}<span>Approve → Next</span>`,
                onclick: async (e) => {
                  e.target.closest("button").disabled = true;
                  try {
                    await api.myChannelProduceSectionApprove(channel.name, v.id, sec.id);
                    render();
                  } catch (err) { toast(err.message || "Failed.", { kind: "error" }); e.target.closest("button").disabled = false; }
                },
              }),
              // Redo — available after produced
              isProduced && h("button", {
                class: "btn ghost sm",
                html: `${icons.sparkle}<span>Redo</span>`,
                onclick: async (e) => {
                  e.target.closest("button").disabled = true;
                  try {
                    await api.myChannelProduceSectionRedo(channel.name, v.id, sec.id);
                    pollSection(sec.id, secCard, () => render());
                  } catch (err) { toast(err.message || "Failed.", { kind: "error" }); e.target.closest("button").disabled = false; }
                },
              }),
            ].filter(Boolean)),
          ]));

          // Progress bar while producing
          if (isRunning) {
            secCard.appendChild(h("div", { class: "caption", style: { marginBottom: "8px", color: "var(--ink-500)" } }, [job.current || "Working…"]));
            pollSection(sec.id, secCard, () => render());
          }

          // MP4 player — shown once produced (even before approval)
          if ((isProduced || isApproved) && job.mp4_url) {
            const player = h("video", { controls: "controls", style: { width: "100%", borderRadius: "12px", marginBottom: "14px", maxHeight: "440px" } });
            player.src = job.mp4_url;
            secCard.appendChild(player);
            secCard.appendChild(h("div", { style: { display: "flex", gap: "8px" } }, [
              h("a", { href: job.mp4_url, download: `${sec.id}.mp4`, class: "btn ghost sm", html: `${icons.check}<span>Download</span>` }),
            ]));
          }

          if (job.status === "error") {
            secCard.appendChild(h("div", { class: "caption", style: { color: "var(--danger)", marginTop: "8px" } }, [job.error || "Production failed."]));
          }

          prodStage.appendChild(secCard);
        });

        // Final assembly — only after ALL sections approved
        const finalJob = await api.myChannelProduceFinalStatus(channel.name, v.id).catch(() => ({ status: "idle" }));
        const finalCard = h("div", { style: { borderTop: "1px solid var(--border)", paddingTop: "16px", marginTop: "8px" } });

        if (finalJob.status === "done" && finalJob.output_url) {
          finalCard.appendChild(h("div", { style: { marginBottom: "12px", fontWeight: 700, fontSize: "15px" } }, ["Final Video Ready"]));
          const fp = h("video", { controls: "controls", style: { width: "100%", borderRadius: "8px", marginBottom: "10px" } });
          fp.src = finalJob.output_url;
          finalCard.appendChild(fp);
          finalCard.appendChild(h("a", { href: finalJob.output_url, download: "final.mp4", class: "btn primary", html: `${icons.check}<span>Download Final MP4</span>` }));
        } else if (finalJob.status === "assembling") {
          finalCard.appendChild(h("div", { class: "caption" }, ["Assembling final video… " + (finalJob.current || "")]));
          if (!ivals.final) {
            ivals.final = setInterval(async () => {
              if (!outlet.isConnected) { clearInterval(ivals.final); ivals.final = null; return; }
              const fj = await api.myChannelProduceFinalStatus(channel.name, v.id).catch(() => null);
              if (fj && (fj.status === "done" || fj.status === "error")) {
                clearInterval(ivals.final); ivals.final = null; render();
              }
            }, 3000);
          }
        } else if (allApproved) {
          const assembleBtn = h("button", { class: "btn primary", html: `${icons.sparkle}<span>Assemble Final Video</span>` });
          assembleBtn.onclick = async () => {
            assembleBtn.disabled = true;
            try { await api.myChannelProduceFinal(channel.name, v.id); render(); }
            catch (e) { toast(e.message || "Failed.", { kind: "error" }); assembleBtn.disabled = false; }
          };
          finalCard.appendChild(assembleBtn);
          if (finalJob.error) finalCard.appendChild(h("div", { class: "caption", style: { color: "var(--danger)", marginTop: "8px" } }, [finalJob.error]));
        } else {
          finalCard.appendChild(h("div", { class: "caption", style: { color: "var(--ink-400)" } }, ["Approve all sections to unlock final assembly."]));
        }
        prodStage.appendChild(finalCard);
      }
      stagesWrap.appendChild(prodStage);
    }
  } // end renderScriptOrProduction

  function pollScript() {
    if (ivals.script) clearInterval(ivals.script);
    ivals.script = setInterval(async () => {
      if (!outlet.isConnected) { clearInterval(ivals.script); ivals.script = null; return; }
      try {
        const s = await api.myChannelVideoScriptStatus(channel.name, video.id);
        if (s.status === "done" || s.status === "error") {
          clearInterval(ivals.script); ivals.script = null;
          render();
        }
      } catch { clearInterval(ivals.script); ivals.script = null; }
    }, 3000);
  }

  function pollSection(sid, secCard, onDone) {
    const key = `section_${sid}`;
    if (ivals[key]) clearInterval(ivals[key]);
    ivals[key] = setInterval(async () => {
      if (!outlet.isConnected) { clearInterval(ivals[key]); ivals[key] = null; return; }
      try {
        const s = await api.myChannelProduceSectionStatus(channel.name, video.id, sid);
        if (s.status === "done" || s.status === "error") {
          clearInterval(ivals[key]); ivals[key] = null;
          onDone();
        }
      } catch { clearInterval(ivals[key]); ivals[key] = null; }
    }, 3000);
  }

  await render();
}

// ── Channel detail view — 3-step wizard ──────────────────────────────────────
// STEP 01: Build DNA  →  STEP 02: Choose Voice  →  STEP 03: Produce Videos

async function mountDetail(outlet, channel, onBack) {
  async function showDetail() {
    outlet.innerHTML = "";
    const intervals = { scan: null };

    function cleanup() { if (intervals.scan) clearInterval(intervals.scan); }

    // Back button
    const backBtn = h("button", {
      class: "btn ghost sm", style: { marginBottom: "28px" },
      html: `${icons.x}<span>All Channels</span>`,
    });
    backBtn.onclick = () => { cleanup(); onBack(); };
    outlet.appendChild(backBtn);

    // Determine initial step
    const dnaReady = !!channel.dna_path;
    const voiceReady = !!channel.voice_id;
    let currentStep = dnaReady ? (voiceReady ? 3 : 2) : 1;

    // ── Step indicator bar ─────────────────────────────────────────────────
    const STEPS = [
      { num: "01", label: "Build DNA" },
      { num: "02", label: "Choose Voice" },
      { num: "03", label: "Produce Videos" },
    ];

    const stepBar = h("div", {
      style: {
        display: "flex", justifyContent: "center", alignItems: "stretch",
        marginBottom: "40px", borderBottom: "1px solid var(--border,#e5e7eb)",
      },
    });

    function renderStepBar() {
      stepBar.innerHTML = "";
      STEPS.forEach((s, i) => {
        const idx = i + 1;
        const isActive = idx === currentStep;
        const isDone = (idx === 1 && dnaReady) || (idx === 2 && voiceReady);
        const isAccessible = isDone || idx <= currentStep;

        const stepEl = h("div", {
          style: {
            textAlign: "center", padding: "0 36px 14px", cursor: isAccessible ? "pointer" : "default",
            borderBottom: isActive ? "3px solid var(--accent,#6366f1)" : isDone ? "3px solid var(--success,#10b981)" : "3px solid transparent",
            marginBottom: "-1px",
          },
        }, [
          h("div", {
            style: {
              fontSize: "42px", fontWeight: "900", lineHeight: "1", letterSpacing: "-0.02em",
              color: isActive ? "var(--accent,#6366f1)" : isDone ? "var(--success,#10b981)" : "var(--ink-200,#e5e7eb)",
            },
          }, [isDone && !isActive ? "✓" : s.num]),
          h("div", {
            style: {
              fontSize: "11px", fontWeight: "700", textTransform: "uppercase", letterSpacing: "0.1em", marginTop: "5px",
              color: isActive ? "var(--accent,#6366f1)" : isDone ? "var(--success,#10b981)" : "var(--ink-300,#d1d5db)",
            },
          }, [s.label]),
        ]);

        if (isAccessible) stepEl.onclick = () => { currentStep = idx; renderStep(); };
        stepBar.appendChild(stepEl);
      });
    }

    outlet.appendChild(stepBar);

    // ── Channel identity header (logo + name, centered) ────────────────────
    const logoWrap = h("div", { style: { width: "72px", height: "72px" } });

    // Always poll for the logo — covers both "not generated yet" and
    // "logo_path set but image temporarily unresolvable" cases.
    // Stops as soon as the img loads successfully.
    let _logoReady = false;

    function _renderLogoWrap(logoPath) {
      logoWrap.innerHTML = "";
      if (logoPath) {
        const img = h("img", {
          src: `/channel-logos/${encodeURIComponent(channel.name)}/logo.png?t=${Date.now()}`,
          alt: channel.name,
          style: { width: "72px", height: "72px", borderRadius: "14px", objectFit: "cover" },
        });
        img.onload  = () => { _logoReady = true; };
        img.onerror = () => { logoWrap.innerHTML = ""; logoWrap.appendChild(avatarEl(channel)); };
        logoWrap.appendChild(img);
      } else {
        logoWrap.appendChild(avatarEl(channel));
      }
    }

    _renderLogoWrap(channel.logo_path);

    const _logoPoller = setInterval(async () => {
      if (_logoReady) { clearInterval(_logoPoller); return; }
      try {
        const s = await api.myChannelLogoStatus(channel.name);
        if (s.logo_path)             { _renderLogoWrap(s.logo_path); }
        else if (s.status === "error") { clearInterval(_logoPoller); }
      } catch { clearInterval(_logoPoller); }
    }, 3000);

    const logoEl = logoWrap;

    const channelHeader = h("div", {
      style: {
        display: "flex", flexDirection: "column", alignItems: "center",
        textAlign: "center", gap: "10px", marginBottom: "36px",
      },
    }, [
      logoEl,
      h("div", {}, [
        h("div", {
          style: {
            fontSize: "26px", fontWeight: "800", letterSpacing: "0.06em",
            textTransform: "uppercase", color: "var(--ink-900)", lineHeight: "1.1",
          },
        }, [channel.name]),
        h("div", { class: "caption", style: { marginTop: "4px" } }, [channel.niche]),
        channel.reference_channel_name
          ? h("div", { class: "caption", style: { marginTop: "2px" } }, [`Reference: ${channel.reference_channel_name}`])
          : null,
      ].filter(Boolean)),
    ]);

    // ── Content area (max-width centered) ─────────────────────────────────
    const contentArea = h("div", { style: { maxWidth: "720px", margin: "0 auto" } });
    outlet.appendChild(contentArea);
    contentArea.appendChild(channelHeader);

    const stepContent = h("div");
    contentArea.appendChild(stepContent);

    async function renderStep() {
      renderStepBar();
      stepContent.innerHTML = "";
      if (currentStep === 1) await renderDnaStep();
      else if (currentStep === 2) await renderVoiceStep();
      else await renderVideosStep();
    }

    // ─────────────────────────────────────────────────────────────────────────
    // STEP 1 — BUILD DNA
    // ─────────────────────────────────────────────────────────────────────────
    async function renderDnaStep() {
      const wrap = h("div");
      stepContent.appendChild(wrap);

      let refName = channel.reference_channel_name || "";
      try {
        const trackers = (await api.trackers()).items || [];
        const ref = trackers.find((t) => t.channel_id === channel.reference_channel_id);
        refName = ref?.handle || ref?.name || refName;
      } catch { /* ignore */ }

      let selectedNumVideos = 3;

      function renderIdle() {
        wrap.innerHTML = "";
        if (!channel.reference_channel_id) {
          wrap.appendChild(h("div", { class: "card", style: { textAlign: "center", padding: "48px 24px" } }, [
            h("div", { style: { fontWeight: "700", fontSize: "18px", marginBottom: "8px", color: "var(--ink-700)" } }, ["No reference channel"]),
            h("div", { class: "caption" }, ["Go back to All Channels and set a reference channel to enable DNA scanning."]),
          ]));
          return;
        }

        // Video count selector — 1, 2, 5, 10
        const countOptions = [1, 2, 5, 10];
        const countBtns = countOptions.map((n) => {
          const btn = h("button", {
            class: "btn ghost sm",
            style: {
              minWidth: "48px",
              fontWeight: "700",
              background: selectedNumVideos === n ? "var(--accent,#6366f1)" : "",
              color: selectedNumVideos === n ? "#fff" : "",
              border: selectedNumVideos === n ? "2px solid var(--accent,#6366f1)" : "",
            },
          }, [String(n)]);
          btn.onclick = () => { selectedNumVideos = n; renderIdle(); };
          return btn;
        });

        const buildBtn = h("button", {
          class: "btn primary",
          style: { width: "100%", padding: "18px 24px", fontSize: "18px", borderRadius: "12px" },
          html: `${icons.sparkle}<span>Build DNA from @${refName || "reference channel"}</span>`,
          onclick: () => startScan(),
        });

        wrap.appendChild(h("div", { class: "card", style: { textAlign: "center", padding: "48px 28px" } }, [
          h("div", { style: { fontWeight: "800", fontSize: "22px", marginBottom: "10px" } }, ["Absorb Channel DNA"]),
          h("div", { class: "caption", style: { lineHeight: "1.7", maxWidth: "480px", margin: "0 auto 16px" } }, [
            `Reverse-engineer the top videos from ${refName ? "@" + refName : "the reference channel"} — hook pattern, tone, pacing, arc structure, scene composition.`,
          ]),
          h("div", { style: { display: "flex", alignItems: "center", justifyContent: "center", gap: "10px", marginBottom: "28px" } }, [
            h("span", { style: { fontSize: "13px", fontWeight: "600", color: "var(--ink-500)" } }, ["Videos to scan:"]),
            ...countBtns,
          ]),
          buildBtn,
        ]));
      }

      // URE stage pipeline — matches progress() messages from pipeline.py
      const URE_STAGES = [
        { key: "probing",           label: "Probe" },
        { key: "detecting scenes",  label: "Scenes" },
        { key: "sampling",          label: "Sampling" },
        { key: "extracting keyframe", label: "Keyframes" },
        { key: "analyzing motion",  label: "Motion" },
        { key: "gemini vision",     label: "Vision 🌐" },
        { key: "classifying",       label: "Classify" },
        { key: "transcribing",      label: "Transcript" },
        { key: "analyzing audio",   label: "Audio" },
        { key: "extracting script formula", label: "Formula 🌐" },
        { key: "assembling blueprint",      label: "Blueprint 🌐" },
      ];

      function stageIndex(msg) {
        const m = (msg || "").toLowerCase();
        for (let i = URE_STAGES.length - 1; i >= 0; i--) {
          if (m.includes(URE_STAGES[i].key.toLowerCase())) return i;
        }
        return -1;
      }

      function renderProgress(j) {
        wrap.innerHTML = "";
        const total = j.total || 3;
        const vidIdx = j.video_idx ?? 0;
        const vidsDone = j.progress || 0;
        const stage = j.stage || j.current || "";
        const activeStageIdx = stageIndex(stage);
        const isSynthesis = (stage || "").toLowerCase().includes("synthes");

        const abortBtn = h("button", {
          class: "btn ghost sm",
          style: { color: "var(--ink-400)", fontSize: "12px", marginTop: "4px" },
        }, ["Stop & use what's ready"]);
        abortBtn.onclick = async () => {
          abortBtn.disabled = true; abortBtn.textContent = "Stopping…";
          try {
            await api.myChannelScanAbort(channel.name);
            channel.dna_path = "set";
            clearInterval(intervals.scan); intervals.scan = null;
            await renderReady();
            toast("Scan stopped — DNA built from available data.", { kind: "success" });
          } catch (e) { toast(e.message || "Failed.", { kind: "error" }); abortBtn.disabled = false; }
        };

        // Video dots row
        const videoDots = h("div", { style: { display: "flex", gap: "10px", justifyContent: "center", marginBottom: "20px" } },
          Array.from({ length: total }, (_, i) => {
            const isDone = i < vidsDone;
            const isActive = i === vidIdx && !isSynthesis;
            return h("div", {
              style: {
                display: "flex", flexDirection: "column", alignItems: "center", gap: "5px",
                opacity: i > vidIdx && !isDone ? "0.35" : "1",
              },
            }, [
              h("div", {
                style: {
                  width: "32px", height: "32px", borderRadius: "50%",
                  background: isDone ? "var(--success,#10b981)" : isActive ? "var(--accent,#6366f1)" : "var(--surface-2)",
                  border: `2px solid ${isDone ? "var(--success,#10b981)" : isActive ? "var(--accent,#6366f1)" : "var(--border)"}`,
                  display: "flex", alignItems: "center", justifyContent: "center",
                  fontSize: "13px", fontWeight: "700", color: isDone || isActive ? "#fff" : "var(--ink-400)",
                  animation: isActive ? "pulse 1.5s ease-in-out infinite" : "none",
                },
              }, [isDone ? "✓" : String(i + 1)]),
              h("div", { style: { fontSize: "10px", fontWeight: "600", color: "var(--ink-400)", textTransform: "uppercase", letterSpacing: "0.05em" } }, [`Video ${i + 1}`]),
            ]);
          })
        );

        // Stage pipeline
        const stagePipeline = h("div", {
          style: { display: "flex", gap: "4px", flexWrap: "wrap", justifyContent: "center", marginBottom: "14px" },
        },
          URE_STAGES.map((s, i) => {
            const isDone = activeStageIdx > i || isSynthesis;
            const isActive = i === activeStageIdx && !isSynthesis;
            return h("div", {
              style: {
                padding: "4px 8px", borderRadius: "20px", fontSize: "11px", fontWeight: "600",
                background: isDone ? "var(--success-subtle,#d1fae5)" : isActive ? "var(--accent-subtle,#ede9fe)" : "var(--surface-2)",
                color: isDone ? "var(--success,#10b981)" : isActive ? "var(--accent,#6366f1)" : "var(--ink-300)",
                border: `1px solid ${isDone ? "var(--success,#10b981)" : isActive ? "var(--accent,#6366f1)" : "transparent"}`,
                transition: "all 300ms",
              },
            }, [s.label]);
          })
        );

        // Current message
        const currentMsg = isSynthesis
          ? "Merging all videos into DNA formula…"
          : (stage.startsWith("[URE]") ? stage.replace("[URE]", "").trim() : stage) || "Working…";

        wrap.appendChild(h("div", { class: "card", style: { padding: "28px 24px" } }, [
          h("div", { style: { fontWeight: "800", fontSize: "18px", marginBottom: "6px", textAlign: "center" } }, ["Absorbing DNA…"]),
          h("div", { class: "caption", style: { textAlign: "center", marginBottom: "24px" } }, [
            `${refName ? "@" + refName : "reference channel"} · ${vidsDone} of ${total} videos done`,
          ]),
          videoDots,
          stagePipeline,
          h("div", { style: { textAlign: "center", fontSize: "12px", color: "var(--ink-500)", padding: "8px 12px", background: "var(--surface-2)", borderRadius: "8px", marginBottom: "12px", fontFamily: "monospace" } }, [currentMsg]),
          h("div", { style: { textAlign: "center" } }, [abortBtn]),
        ]));
      }

      async function renderReady() {
        wrap.innerHTML = "";
        let summary = null;
        try { summary = await api.myChannelDnaSummary(channel.name); } catch { /* ignore */ }

        const summaryRows = [];
        if (summary) {
          const rows = [
            ["Videos analyzed", summary.num_videos],
            ["Hook pattern", summary.hook_pattern],
            ["Tone", summary.tone],
            ["VO style", summary.vo_style],
            ["Avg scene duration", summary.avg_scene_s ? `${summary.avg_scene_s}s` : "—"],
            ["Cuts per minute", summary.cuts_per_min || "—"],
            ["Scene count", summary.scene_count || "—"],
          ];
          rows.forEach(([lbl, val]) =>
            summaryRows.push(h("div", {
              style: { display: "flex", justifyContent: "space-between", alignItems: "flex-start", padding: "10px 0", borderBottom: "1px solid var(--border,#e5e7eb)" },
            }, [
              h("span", { style: { fontSize: "12px", fontWeight: "600", color: "var(--ink-500)", textTransform: "uppercase", letterSpacing: "0.05em" } }, [lbl]),
              h("span", { style: { fontSize: "14px", fontWeight: "700", color: "var(--ink-900)", textAlign: "right", maxWidth: "58%" } }, [String(val || "—")]),
            ]))
          );
          if (summary.arc_beats?.length) {
            summaryRows.push(h("div", { style: { padding: "12px 0" } }, [
              h("div", { style: { fontSize: "12px", fontWeight: "600", color: "var(--ink-500)", textTransform: "uppercase", letterSpacing: "0.05em", marginBottom: "8px" } }, ["Arc beats"]),
              h("div", { style: { display: "flex", flexWrap: "wrap", gap: "6px" } },
                summary.arc_beats.map((b) => h("span", { class: "pill", style: { background: "var(--accent-subtle,#ede9fe)", color: "var(--accent,#6366f1)", fontSize: "12px" } }, [b]))
              ),
            ]));
          }
        }

        const continueBtn = h("button", {
          class: "btn primary",
          style: { width: "100%", padding: "16px", fontSize: "16px", borderRadius: "12px", marginTop: "20px" },
          html: `${icons.check}<span>Continue → Choose Voice</span>`,
          onclick: () => { currentStep = 2; renderStep(); },
        });

        // Re-scan with same count selector
        const rescanCountBtns = [1, 2, 5, 10].map((n) => {
          const btn = h("button", {
            class: "btn ghost sm",
            style: {
              minWidth: "40px", fontWeight: "700",
              background: selectedNumVideos === n ? "var(--accent,#6366f1)" : "",
              color: selectedNumVideos === n ? "#fff" : "",
              border: selectedNumVideos === n ? "2px solid var(--accent,#6366f1)" : "",
            },
          }, [String(n)]);
          btn.onclick = () => { selectedNumVideos = n; wrap.querySelectorAll(".rescan-count-row").forEach(el => el.remove()); renderReady(); };
          return btn;
        });
        const rescanRow = h("div", { class: "rescan-count-row", style: { display: "flex", alignItems: "center", justifyContent: "center", gap: "8px", marginTop: "10px" } }, [
          h("span", { style: { fontSize: "12px", fontWeight: "600", color: "var(--ink-500)" } }, ["Re-scan:"]),
          ...rescanCountBtns,
          h("button", { class: "btn ghost sm", html: `${icons.sparkle}<span>Go</span>`, onclick: () => startScan() }),
        ]);
        const rescanBtn = rescanRow;

        wrap.appendChild(h("div", {}, [
          h("div", { style: { display: "flex", alignItems: "center", gap: "12px", marginBottom: "20px", padding: "14px 18px", background: "var(--success-subtle,#d1fae5)", borderRadius: "10px" } }, [
            h("div", { style: { flexShrink: "0", color: "var(--success,#10b981)" }, html: icons.check }),
            h("div", {}, [
              h("div", { style: { fontWeight: "800", fontSize: "17px", color: "var(--success,#10b981)" } }, ["DNA Absorbed"]),
              h("div", { class: "caption" }, [`From ${refName ? "@" + refName : "reference channel"}`]),
            ]),
          ]),
          summaryRows.length
            ? h("div", { class: "card", style: { padding: "0 20px", marginBottom: "0" } }, summaryRows)
            : null,
          continueBtn,
          rescanBtn,
        ].filter(Boolean)));
      }

      function renderError(msg) {
        wrap.innerHTML = "";
        wrap.appendChild(h("div", { class: "card", style: { textAlign: "center", padding: "32px" } }, [
          h("div", { style: { color: "var(--danger)", fontWeight: "700", fontSize: "16px", marginBottom: "8px" } }, ["DNA Scan Failed"]),
          h("div", { class: "caption", style: { color: "var(--danger)", marginBottom: "16px" } }, [msg || "Unknown error."]),
          h("button", { class: "btn ghost sm", html: `${icons.sparkle}<span>Retry</span>`, onclick: () => startScan() }),
        ]));
      }

      async function startScan() {
        try { await api.myChannelScan(channel.name, selectedNumVideos); } catch (e) { toast(e.message || "Failed.", { kind: "error" }); return; }
        renderProgress({ status: "scanning", progress: 0, total: selectedNumVideos, current: "Starting…" });
        pollScan();
      }

      function pollScan() {
        if (intervals.scan) clearInterval(intervals.scan);
        intervals.scan = setInterval(async () => {
          if (!outlet.isConnected) { clearInterval(intervals.scan); intervals.scan = null; return; }
          let j;
          try { j = await api.myChannelScanStatus(channel.name); } catch { return; }
          if (j.status === "scanning") {
            renderProgress(j);
          } else if (j.status === "done") {
            clearInterval(intervals.scan); intervals.scan = null;
            channel.dna_path = "set";
            await renderReady();
            toast("DNA absorbed!", { kind: "success" });
          } else if (j.status === "error") {
            clearInterval(intervals.scan); intervals.scan = null;
            renderError(j.error);
          }
        }, 2000);
      }

      let job = { status: "idle" };
      try { job = await api.myChannelScanStatus(channel.name); } catch { /* ignore */ }
      if (job.status === "scanning") { renderProgress(job); pollScan(); }
      else if (channel.dna_path) { await renderReady(); }
      else { renderIdle(); }
    }

    // ─────────────────────────────────────────────────────────────────────────
    // STEP 2 — CHOOSE VOICE
    // ─────────────────────────────────────────────────────────────────────────
    async function renderVoiceStep() {
      stepContent.appendChild(h("div", {
        style: { textAlign: "center", padding: "60px 24px", color: "var(--ink-400)" },
      }, [
        h("div", { style: { fontWeight: "700", fontSize: "18px", marginBottom: "8px", color: "var(--ink-700)" } }, ["Loading Voices…"]),
        h("div", { class: "caption" }, ["Fetching voices from ElevenLabs"]),
      ]));

      let voices = [];
      try {
        const { voices: apiVoices, error } = await api.elevenlabsVoices();
        if (!error && apiVoices?.length) {
          voices = apiVoices.map((v) => ({
            id: v.id,
            name: v.name,
            tag: [v.labels?.accent, v.labels?.["use case"]].filter(Boolean).join(" · ") || "—",
            preview_url: v.preview_url || "",
          }));
        }
      } catch { /* ignore */ }
      if (!voices.length) voices = CURATED_VOICES.map((v) => ({ ...v, preview_url: "" }));

      stepContent.innerHTML = "";
      let selectedId = channel.voice_id || "";

      function renderVoices() {
        stepContent.innerHTML = "";

        stepContent.appendChild(h("div", { style: { textAlign: "center", marginBottom: "24px" } }, [
          h("div", { style: { fontWeight: "700", fontSize: "17px", marginBottom: "4px" } }, ["Choose Your Voice"]),
          h("div", { class: "caption" }, ["Press play to preview · Click a card to select · Save and continue"]),
        ]));

        const grid = h("div", {
          style: { display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(200px, 1fr))", gap: "12px", marginBottom: "20px" },
        });

        voices.forEach((v) => {
          const isSelected = v.id === selectedId;
          const card = h("div", {
            class: "iri-card",
            style: {
              borderRadius: "12px", padding: "14px 14px 12px",
              border: `2px solid ${isSelected ? "var(--accent,#6366f1)" : "var(--border,#e5e7eb)"}`,
              background: isSelected ? "var(--accent-subtle,#ede9fe)" : "var(--surface)",
              cursor: "pointer", userSelect: "none",
            },
          });

          card.appendChild(h("div", {
            style: { fontWeight: "700", fontSize: "14px", marginBottom: "2px", color: isSelected ? "var(--accent,#6366f1)" : "var(--ink-900)" },
          }, [v.name]));
          card.appendChild(h("div", { class: "caption", style: { marginBottom: "8px", minHeight: "18px" } }, [v.tag]));

          if (v.preview_url) {
            const audioWrap = document.createElement("div");
            audioWrap.style.cssText = "margin-top:4px;";
            const audio = document.createElement("audio");
            audio.controls = true;
            audio.preload = "none";
            audio.src = v.preview_url;
            audio.style.cssText = "width:100%;height:28px;border-radius:6px;";
            audioWrap.appendChild(audio);
            audioWrap.addEventListener("click", (e) => e.stopPropagation());
            audioWrap.addEventListener("mousedown", (e) => e.stopPropagation());
            card.appendChild(audioWrap);
          }

          card.onclick = (e) => {
            if (e.target.closest("audio") || e.target.tagName === "AUDIO") return;
            selectedId = v.id;
            renderVoices();
          };

          grid.appendChild(card);
        });

        const selectedName = voices.find((v) => v.id === selectedId)?.name;
        const saveBtn = h("button", {
          class: "btn primary",
          style: { width: "100%", padding: "16px", fontSize: "16px", borderRadius: "12px" },
          disabled: !selectedId,
        }, [selectedName ? `Save "${selectedName}" & Continue → Production` : "Save Voice & Continue → Production"]);
        saveBtn.onclick = async () => {
          if (!selectedId) return;
          saveBtn.disabled = true;
          try {
            await api.myChannelUpdate(channel.name, { voice_id: selectedId });
            channel.voice_id = selectedId;
            toast("Voice saved!");
            currentStep = 3;
            renderStep();
          } catch (e) { toast(e.message || "Save failed.", { kind: "error" }); saveBtn.disabled = false; }
        };

        const skipBtn = h("button", {
          class: "btn ghost sm", style: { width: "100%", marginTop: "10px" },
        }, ["Skip for now → Go to Production"]);
        skipBtn.onclick = () => { currentStep = 3; renderStep(); };

        stepContent.appendChild(grid);
        stepContent.appendChild(saveBtn);
        stepContent.appendChild(skipBtn);
      }

      renderVoices();
    }

    // ─────────────────────────────────────────────────────────────────────────
    // STEP 3 — PRODUCE VIDEOS
    // ─────────────────────────────────────────────────────────────────────────
    async function renderVideosStep() {
      // Load my-channels list for the ideas picker
      let myChannels = [];
      try { myChannels = (await api.myChannels()).items || []; } catch { /* ignore */ }
      // Also load trackers (used elsewhere in this step)
      let trackers = [];
      try { trackers = (await api.trackers()).items || []; } catch { /* ignore */ }

      // ── New video: Ideas | Direct Title tabs ───────────────────────────────
      const newVideoCard = h("div", { class: "card", style: { marginBottom: "24px" } });

      let activeTab = "ideas";
      const ideasTab  = h("button", { class: "btn primary sm", style: { borderRadius: "20px" } }, ["Ideas"]);
      const directTab = h("button", { class: "btn ghost sm", style: { borderRadius: "20px" } }, ["Direct Title"]);
      const tabContent = h("div", { style: { marginTop: "14px" } });

      function setTab(tab) {
        activeTab = tab;
        ideasTab.className  = tab === "ideas"  ? "btn primary sm" : "btn ghost sm";
        directTab.className = tab === "direct" ? "btn primary sm" : "btn ghost sm";
        ideasTab.style.borderRadius = directTab.style.borderRadius = "20px";
        renderTabContent();
      }
      ideasTab.onclick  = () => setTab("ideas");
      directTab.onclick = () => setTab("direct");

      newVideoCard.appendChild(h("div", { class: "field-label", style: { marginBottom: "10px" } }, ["Add Video"]));
      newVideoCard.appendChild(h("div", { style: { display: "flex", gap: "8px" } }, [ideasTab, directTab]));
      newVideoCard.appendChild(tabContent);
      stepContent.appendChild(newVideoCard);

      let ideasJobId = null;

      function durationChips() {
        let dur = "10min";
        const chips = ["5min", "10min", "20min"].map((d) => {
          const btn = h("button", {
            class: d === "10min" ? "btn primary sm" : "btn ghost sm",
            style: { borderRadius: "20px", minWidth: "56px" },
          }, [d]);
          btn.onclick = () => {
            dur = d;
            chips.forEach((c, i) => {
              c.className = ["5min", "10min", "20min"][i] === dur ? "btn primary sm" : "btn ghost sm";
              c.style.borderRadius = "20px"; c.style.minWidth = "56px";
            });
          };
          return btn;
        });
        const el = h("div", { style: { display: "flex", gap: "6px", alignItems: "center", marginTop: "8px" } }, [
          h("span", { class: "caption" }, ["Duration:"]), ...chips,
        ]);
        return { el, getDuration: () => dur };
      }

      async function createAndOpenVideo(topic, brief, duration = "10min") {
        try {
          const newVideo = await api.myChannelVideoCreate(channel.name, { topic, brief, duration_hint: duration, status: "titled" });
          await mountVideoWorkspace(outlet, channel, newVideo, showDetail);
        } catch (e) { toast(e.message || "Failed to create video.", { kind: "error" }); }
      }

      function renderTabContent() {
        tabContent.innerHTML = "";
        if (activeTab === "ideas") {
          // ── Full Ideas Generator ────────────────────────────────────────────
          // Uses /my-channels/{name}/ideas so it gets the correct niche context
          // (Game of thrones, not default.yml). Channel picker lets the user
          // switch between their own channels. Cards call createAndOpenVideo.

          // Build picker from my-channels list; pre-select current channel
          const myChItems = myChannels.map((c) => ({
            channel_id: c.name,   // use name as key since these aren't tracker channels
            handle: c.name,
            name: c.name,
            niche: c.niche || "",
          }));
          // Add current channel if not already in list
          if (!myChItems.find((c) => c.channel_id === channel.name)) {
            myChItems.unshift({ channel_id: channel.name, handle: channel.name, name: channel.name });
          }
          const ideasPicker = channelPicker({ items: myChItems, selected: channel.name });

          const topicWrap = h("div", { class: "hidden", style: { marginTop: "6px", marginBottom: "6px" } }, [
            h("input", { class: "input", id: "ws-topic-input", placeholder: "Topic direction (optional) — e.g. 'the Red Wedding', 'forgotten lords'" }),
          ]);

          const countSelect = h("select", { class: "select count-select" }, [
            h("option", { value: "1" }, ["1"]),
            h("option", { value: "3" }, ["3"]),
            h("option", { value: "6", selected: "selected" }, ["6"]),
            h("option", { value: "9" }, ["9"]),
            h("option", { value: "12" }, ["12"]),
          ]);

          const genBtn = h("button", { class: "btn huge grow", html: `${icons.sparkle}<span>Generate Ideas</span>` });
          const results = h("div");

          // Running banner with elapsed timer
          let runningBanner = null, runningTimer = null;
          const showBanner = (startedAt) => {
            if (runningBanner) { runningBanner.remove(); runningBanner = null; }
            if (runningTimer) clearInterval(runningTimer);
            const timerSpan = h("span", { class: "timer" }, ["0s"]);
            runningBanner = h("div", { class: "reconnect-banner" }, [
              h("span", { class: "spinner-ink" }),
              h("span", {}, ["Generating ideas…"]),
              timerSpan,
            ]);
            tabContent.appendChild(runningBanner);
            const t0 = startedAt || Date.now();
            const tick = () => { timerSpan.textContent = `${Math.floor((Date.now() - t0) / 1000)}s`; };
            tick();
            runningTimer = setInterval(tick, 1000);
          };
          const hideBanner = () => {
            if (runningBanner) { runningBanner.remove(); runningBanner = null; }
            if (runningTimer) { clearInterval(runningTimer); runningTimer = null; }
          };

          const resetGenBtn = () => {
            genBtn.disabled = false;
            genBtn.innerHTML = `${icons.sparkle}<span>Generate Ideas</span>`;
          };

          const showSkeleton = () => {
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
          };

          const renderIdeas = (items) => {
            results.innerHTML = "";
            if (!items.length) {
              results.appendChild(h("div", { class: "caption", style: { padding: "16px 0" } }, ["No ideas returned — try adding a topic direction."]));
              return;
            }
            results.appendChild(h("div", { class: "section-head" }, [
              h("div", { class: "section-title" }, ["Fresh ideas"]),
              h("div", { class: "section-sub" }, [`${items.length} generated`]),
            ]));
            const grid = h("div", { style: { display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(300px, 1fr))", gap: "12px", marginTop: "12px" } });
            items.forEach((idea) => {
              const title = idea.idea_title || idea.title || "";
              const dur = durationChips();
              const produceBtn = h("button", { class: "btn sm primary" }, ["Produce"]);
              produceBtn.onclick = async (e) => {
                e.stopPropagation();
                produceBtn.disabled = true;
                produceBtn.textContent = "Opening…";
                await createAndOpenVideo(title, "", dur.getDuration());
              };
              grid.appendChild(h("div", { class: "card sm idea-card" }, [
                h("div", { class: "idea-card-body" }, [
                  h("div", { class: "idea-card-title" }, [title]),
                  h("div", { class: "idea-card-desc" }, [idea.idea_description || ""]),
                  idea.angle ? h("div", { class: "badge neutral", style: { marginBottom: "10px" } }, [idea.angle]) : null,
                  h("div", { class: "flex gap-2 wrap", style: { alignItems: "center" } }, [dur.el, produceBtn]),
                ].filter(Boolean)),
              ]));
            });
            results.appendChild(grid);
          };

          genBtn.addEventListener("click", async () => {
            const pickedChannel = ideasPicker.getValue();
            if (!pickedChannel) { toast("Pick a channel first", { kind: "error" }); return; }
            const topic = tabContent.querySelector("#ws-topic-input")?.value?.trim() || "";
            const count = parseInt(countSelect.value, 10) || 6;

            genBtn.disabled = true;
            genBtn.innerHTML = `<span class="spinner-sm"></span><span>Generating…</span>`;
            showSkeleton();
            showBanner(Date.now());

            try {
              // Use the my-channels endpoint — it knows the correct niche/context
              const r = await api.myChannelIdeas(pickedChannel, topic, count);
              if (!r.job_id) throw new Error("no job_id returned");
              while (true) {
                const s = await api.myChannelIdeasStatus(pickedChannel, r.job_id);
                if (s.status === "done") { hideBanner(); renderIdeas(s.items || []); resetGenBtn(); break; }
                if (s.status === "error") throw new Error(s.error || "generation failed");
                if (s.status === "unknown") throw new Error("job not found");
                await new Promise((res) => setTimeout(res, 1200));
              }
            } catch (e) {
              hideBanner();
              results.innerHTML = "";
              results.appendChild(h("div", { class: "caption", style: { color: "var(--danger)", padding: "12px 0" } }, [e.message]));
              resetGenBtn();
            }
          });

          tabContent.appendChild(h("div", { style: { marginBottom: "16px" } }, [
            myChItems.length > 1
              ? h("div", { style: { marginBottom: "12px" } }, [ideasPicker.el])
              : null,
            h("button", {
              class: "btn ghost sm", style: { marginBottom: "8px", alignSelf: "flex-start" },
              onclick: (e) => { e.preventDefault(); topicWrap.classList.toggle("hidden"); },
              html: `${icons.plus}<span>Add topic direction</span>`,
            }),
            topicWrap,
            h("div", { class: "gen-row", style: { marginTop: "12px" } }, [countSelect, genBtn]),
          ].filter(Boolean)));
          tabContent.appendChild(results);
        } else {
          const titleInput = h("input", { type: "text", placeholder: "Video title — e.g. Top 10 Most Dangerous Criminals Ever" });
          const dur = durationChips();
          const addBtn = h("button", { class: "btn primary sm", html: `${icons.plus}<span>Create</span>` });
          const errEl = h("div", { class: "caption", style: { color: "var(--danger)", marginTop: "6px" } });
          addBtn.onclick = async () => {
            const title = titleInput.value.trim();
            if (!title) { errEl.textContent = "Title is required."; return; }
            await createAndOpenVideo(title, "", dur.getDuration());
          };
          tabContent.appendChild(h("div", {}, [
            h("div", { class: "pill-input" }, [
              h("span", { class: "pi-icon", html: icons.track }), titleInput, addBtn,
            ]),
            dur.el, errEl,
          ]));
        }
      }

      setTab("ideas");

      // ── Video library ───────────────────────────────────────────────────────
      const videoWrap = h("div");
      stepContent.appendChild(videoWrap);

      async function refreshVideos() {
        videoWrap.innerHTML = "";
        let videos = [];
        try { videos = (await api.myChannelVideos(channel.name)).items || []; } catch { return; }

        if (!videos.length) {
          videoWrap.appendChild(h("div", { class: "empty", style: { paddingTop: "16px" } }, [
            h("div", { class: "empty-icon", html: icons.idea }),
            h("div", { class: "empty-title" }, ["No videos yet"]),
            h("div", { class: "empty-body" }, ["Use the Ideas or Direct Title tab above to add a video."]),
          ]));
          return;
        }

        videoWrap.appendChild(h("div", { class: "section-head", style: { marginBottom: "12px" } }, [
          h("span", { class: "section-title" }, ["Video Library"]),
        ]));

        const table = h("table", { class: "data-table" });
        table.appendChild(h("thead", {}, [h("tr", {}, [
          h("th", {}, ["Title"]),
          h("th", {}, ["Status"]),
          h("th", {}, ["Thumbnail"]),
          h("th", {}, ["Created"]),
          h("th", { style: { width: "80px" } }, [""]),
        ])]));
        const tbody = h("tbody");
        videos.forEach((v) => {
          const thumbUrl = v.thumbnail_path ? `/channel-thumbnails/${channel.name}/${v.id}.png` : null;
          const row = h("tr", { style: { cursor: "pointer" } }, [
            h("td", {}, [h("div", { class: "about-cell" }, [v.topic])]),
            h("td", {}, [statusPill(v.status)]),
            h("td", {}, [thumbUrl ? h("img", { src: thumbUrl, style: { width: "80px", borderRadius: "4px" } }) : h("span", { class: "caption" }, ["—"])]),
            h("td", { class: "date-cell" }, [v.created_at ? new Date(v.created_at).toLocaleDateString() : "—"]),
            h("td", {}, [h("button", {
              class: "btn ghost sm", html: `${icons.sparkle}<span>Open</span>`,
              onclick: (e) => { e.stopPropagation(); mountVideoWorkspace(outlet, channel, v, showDetail); },
            })]),
          ]);
          row.onclick = () => mountVideoWorkspace(outlet, channel, v, showDetail);
          tbody.appendChild(row);
        });
        table.appendChild(tbody);
        videoWrap.appendChild(table);
      }

      await refreshVideos();
    } // end renderVideosStep

    await renderStep();
  } // end showDetail

  await showDetail();
}

// ── Mount ─────────────────────────────────────────────────────────────────────

export async function mount(outlet) {
  function showList() {
    mountList(outlet, (ch) => mountDetail(outlet, ch, showList));
  }
  showList();

  // Return unmount so the router can stop any active polls/streams.
  // All intervals already guard with outlet.isConnected, but this ensures
  // immediate termination the moment the user navigates away.
  return function unmount() {
    // Detaching the outlet content causes every isConnected guard to fire false
    // on the very next interval tick — no dangling polls.
    outlet.innerHTML = "";
  };
}
