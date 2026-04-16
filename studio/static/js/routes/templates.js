/**
 * My Templates — content format template library
 * Pattern: mirrors random_channels.js with template-specific customizations
 */

import { api } from "../api.js";
import { h, icons, pageHeader, emptyState, toast, $ } from "../components.js";
import { navigate } from "../router.js";

// ── UI Status Badges ──────────────────────────────────────────────────────
const STATUS_BADGE = {
  draft: { label: "Draft", cls: "badge-neutral" },
  analyzing: { label: "Analyzing", cls: "badge-warning", animated: true },
  ready: { label: "Ready", cls: "badge-success" },
  error: { label: "Error", cls: "badge-danger" },
};

// ── CSS Injection ─────────────────────────────────────────────────────────
function injectCSS() {
  const id = "template-styles";
  if (document.getElementById(id)) return;

  const style = document.createElement("style");
  style.id = id;
  style.textContent = `
    .tpl-card {
      background: var(--surface);
      border: 1px solid var(--line);
      border-radius: var(--r-5, 14px);
      padding: 28px 24px;
      display: flex;
      flex-direction: column;
      gap: 12px;
      min-height: 180px;
      cursor: pointer;
      transition: transform .12s ease, border-color .12s ease, box-shadow .12s ease;
    }
    .tpl-card:hover { border-color: var(--accent, #2d5bff); box-shadow: 0 6px 22px rgba(45,91,255,.10); transform: translateY(-2px); }
    .tpl-card-head { display: flex; align-items: flex-start; justify-content: space-between; gap: 12px; }
    .tpl-card-title { font-size: 22px; font-weight: 800; letter-spacing: -0.01em; color: var(--ink-900,#141414); line-height: 1.2; }
    .tpl-card-desc { font-size: 14px; color: var(--ink-500,#6b7280); line-height: 1.55; flex: 1; }
    .tpl-card-foot { display: flex; justify-content: space-between; align-items: center; gap: 8px; margin-top: auto; }
    .tpl-card-meta { font-size: 12px; color: var(--ink-400,#9ca3af); }
    .tpl-badge-animated { animation: tpl-dots-pulse 1.4s infinite; }
    @keyframes tpl-dots-pulse { 0%,100% { opacity: 1; } 50% { opacity: 0.55; } }

    /* Create card */
    .tpl-card-create {
      background: linear-gradient(135deg, rgba(45,91,255,.08), rgba(139,92,246,.08));
      border: 1.5px dashed var(--accent,#2d5bff);
      align-items: flex-start;
    }
    .tpl-card-create .tpl-card-title { color: var(--accent,#2d5bff); }

    /* Overlay panel content */
    .tpl-ov-panel {
      background: var(--surface);
      border: 1px solid var(--line);
      border-radius: var(--r-6, 18px);
      box-shadow: var(--shadow-3);
      width: 100%;
      max-width: 640px;
      max-height: 85vh;
      overflow-y: auto;
      padding: 28px;
    }
    .tpl-ov-header { display: flex; justify-content: space-between; align-items: flex-start; gap: 16px; margin-bottom: 20px; }
    .tpl-ov-title { font-size: 26px; font-weight: 800; letter-spacing: -0.02em; color: var(--ink-900,#141414); line-height: 1.15; margin-bottom: 6px; }
    .tpl-ov-desc { font-size: 14px; color: var(--ink-500,#6b7280); line-height: 1.6; }
    .tpl-ov-section { border-top: 1px solid var(--line); padding: 18px 0; }
    .tpl-ov-section-label { font-size: 11px; font-weight: 700; text-transform: uppercase; letter-spacing: 0.08em; margin-bottom: 10px; color: var(--ink-400,#9ca3af); }
    .tpl-ov-item { margin-bottom: 10px; padding: 10px 14px; background: var(--surface-2,#f6f7f9); border-radius: 8px; font-size: 13px; color: var(--ink-700,#374151); }
    .tpl-ov-hook { font-family: var(--font-mono, monospace); background: var(--surface-2,#f6f7f9); padding: 10px 14px; margin-bottom: 8px; border-radius: 6px; word-break: break-word; font-size: 13px; }
    .tpl-ov-script {
      background: #0f1115; color: #e5e7eb;
      padding: 18px 20px; border-radius: 10px;
      font-family: var(--font-mono, monospace); font-size: 13px; line-height: 1.7;
      white-space: pre-wrap;
    }
    .tpl-ov-pill { display: inline-block; background: var(--accent-soft,#eef2ff); color: var(--accent,#2d5bff); padding: 4px 10px; border-radius: 99px; font-size: 12px; margin-right: 6px; margin-bottom: 6px; font-weight: 600; }
    .tpl-ov-list { list-style: none; padding: 0; margin: 0; }
    .tpl-ov-list li { padding: 6px 0; font-size: 13px; line-height: 1.5; color: var(--ink-700,#374151); }
    .tpl-ov-list li::before { content: "→"; color: var(--accent,#2d5bff); margin-right: 8px; font-weight: 700; }

    /* Create modal */
    .tpl-modal-panel {
      background: var(--surface);
      border: 1px solid var(--line);
      border-radius: var(--r-5, 14px);
      box-shadow: var(--shadow-3);
      width: 100%;
      max-width: 520px;
      padding: 28px;
    }
    .tpl-modal-title { font-size: 22px; font-weight: 800; margin-bottom: 6px; }
    .tpl-modal-sub { font-size: 13px; color: var(--ink-500,#6b7280); margin-bottom: 18px; }
    .tpl-modal-field { margin-bottom: 14px; display: block; }
    .tpl-modal-field label { font-size: 12px; font-weight: 600; color: var(--ink-700,#374151); display: block; margin-bottom: 6px; }
    .tpl-modal-field input, .tpl-modal-field textarea {
      width: 100%; padding: 10px 12px; border: 1.5px solid var(--line,#e5e7eb); border-radius: 10px;
      font-size: 14px; background: var(--surface); outline: none; font-family: inherit;
    }
    .tpl-modal-field input:focus, .tpl-modal-field textarea:focus { border-color: var(--accent,#2d5bff); }
    .tpl-modal-actions { display: flex; gap: 10px; justify-content: flex-end; margin-top: 10px; }

    /* Example videos grid */
    .tpl-ov-meta { font-size: 13px; color: var(--ink-500,#6b7280); }
    .tpl-ov-meta-dot { color: var(--ink-400,#9ca3af); }
    .tpl-ex-grid {
      display: grid;
      grid-template-columns: repeat(auto-fill, minmax(180px, 1fr));
      gap: 12px;
    }
    .tpl-ex-card {
      display: block;
      text-decoration: none;
      color: inherit;
      background: var(--surface-2,#f6f7f9);
      border: 1px solid var(--line,#e5e7eb);
      border-radius: 10px;
      overflow: hidden;
      transition: transform .12s ease, border-color .12s ease, box-shadow .12s ease;
    }
    .tpl-ex-card:hover {
      border-color: var(--accent,#2d5bff);
      box-shadow: 0 4px 14px rgba(45,91,255,.12);
      transform: translateY(-1px);
    }
    .tpl-ex-thumb-wrap { position: relative; aspect-ratio: 16/9; background: #000; }
    .tpl-ex-thumb { width: 100%; height: 100%; object-fit: cover; display: block; }
    .tpl-ex-play {
      position: absolute; inset: 0;
      display: flex; align-items: center; justify-content: center;
      font-size: 28px; color: #fff;
      text-shadow: 0 2px 8px rgba(0,0,0,.6);
      opacity: 0;
      transition: opacity .15s ease;
      background: rgba(0,0,0,.25);
    }
    .tpl-ex-card:hover .tpl-ex-play { opacity: 1; }
    .tpl-ex-meta { padding: 10px 12px; }
    .tpl-ex-channel { font-size: 13px; font-weight: 600; color: var(--ink-900,#141414); overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
    .tpl-ex-id { font-size: 11px; color: var(--ink-400,#9ca3af); font-family: var(--font-mono, monospace); margin-top: 2px; }
  `;
  document.head.appendChild(style);
}

// ── Component: Create New Template Card ──────────────────────────────────
function createNewTemplateCard() {
  const card = h("div", { class: "tpl-card tpl-card-create" }, [
    h("div", { class: "tpl-card-head" }, [
      h("div", { class: "tpl-card-title" }, ["+ Create New Template"]),
    ]),
    h("div", { class: "tpl-card-desc" }, [
      "Capture a proven content format as a reusable template with Formula, DNA, and example videos.",
    ]),
    h("div", { class: "tpl-card-foot" }, [
      h("span", { class: "tpl-card-meta" }, ["Start by giving it a name"]),
      h("button", {
        class: "btn primary",
        onclick: (e) => {
          e.stopPropagation();
          newTemplateModal(async (res) => {
            await api.templateAnalyze(res.id);
            startPollingReload(res.id);
          });
        },
      }, ["Start Creating"]),
    ]),
  ]);
  card.addEventListener("click", (e) => {
    if (e.target.tagName === "BUTTON") return;
    newTemplateModal(async (res) => {
      await api.templateAnalyze(res.id);
      startPollingReload(res.id);
    });
  });
  return card;
}

// ── Component: Template Card (clean BIG TITLE + description) ─────────────
function templateCard(tpl) {
  const badge = STATUS_BADGE[tpl.status] || STATUS_BADGE.draft;
  const badgeAnimated = badge.animated ? " tpl-badge-animated" : "";
  const badgeLabel = tpl.stage && tpl.status === "analyzing" ? tpl.stage : badge.label;

  const exampleCount = (tpl.example_video_ids || []).length;
  const channelCount = (tpl.example_channels || []).length;

  const card = h("div", { class: "tpl-card" }, [
    h("div", { class: "tpl-card-head" }, [
      h("div", { class: "tpl-card-title" }, [tpl.name]),
      h("span", { class: `badge ${badge.cls}${badgeAnimated}` }, [badgeLabel]),
    ]),
    h("div", { class: "tpl-card-desc" }, [
      tpl.description || "No description yet.",
    ]),
    h("div", { class: "tpl-card-foot" }, [
      h("span", { class: "tpl-card-meta" }, [
        exampleCount ? `${exampleCount} example${exampleCount === 1 ? "" : "s"}` : "",
        exampleCount && channelCount ? " · " : "",
        channelCount ? `${channelCount} channel${channelCount === 1 ? "" : "s"}` : "",
      ]),
      tpl.status === "ready"
        ? h("button", {
            class: "btn primary",
            onclick: (e) => {
              e.stopPropagation();
              useInLabModal(tpl);
            },
          }, ["Use in Lab"])
        : h("button", { class: "btn", disabled: true }, ["Analyzing…"]),
    ]),
  ]);

  card.addEventListener("click", (e) => {
    if (e.target.tagName === "BUTTON") return;
    openTemplateOverlay(tpl);
  });

  return card;
}

// Parse JSON string safely — backend stores these as strings
function safeJson(s) {
  if (!s) return {};
  if (typeof s === "object") return s;
  try { return JSON.parse(s); } catch { return {}; }
}

// Small helper for post-create polling without card references
function startPollingReload(templateId) {
  const timer = setInterval(async () => {
    try {
      const status = await api.templateStatus(templateId);
      if (status.status === "ready" || status.status === "error") {
        clearInterval(timer);
        if (status.status === "ready") setTimeout(() => location.reload(), 600);
      }
    } catch {
      clearInterval(timer);
    }
  }, 2500);
}

// ── Component: New Template Modal ─────────────────────────────────────────
function newTemplateModal(onSuccess) {
  const nameInput = h("input", { type: "text", placeholder: "E.g. 'Your Life As A...'" });
  const descInput = h("textarea", { rows: 3, placeholder: "Optional description (2-3 sentences)" });

  const backdrop = h("div", { class: "ch-ov-backdrop" });
  const panel = h("div", { class: "tpl-modal-panel" }, [
    h("div", { class: "tpl-modal-title" }, ["New Template"]),
    h("div", { class: "tpl-modal-sub" }, ["Give it a name and we'll analyze the format via DNA + Reddit."]),
    h("label", { class: "tpl-modal-field" }, [
      h("label", {}, ["Name"]),
      nameInput,
    ]),
    h("label", { class: "tpl-modal-field" }, [
      h("label", {}, ["Description"]),
      descInput,
    ]),
    h("div", { class: "tpl-modal-actions" }, [
      h("button", {
        class: "btn ghost",
        onclick: () => backdrop.remove(),
      }, ["Cancel"]),
      h("button", {
        class: "btn primary",
        onclick: async (e) => {
          const name = nameInput.value.trim();
          if (!name) { toast("Template name required", { kind: "warning" }); return; }
          const desc = descInput.value.trim();
          e.target.disabled = true;
          e.target.textContent = "Creating…";
          try {
            const res = await api.templateCreate(name, desc);
            backdrop.remove();
            onSuccess(res);
          } catch (err) {
            toast(`Error: ${err.message}`, { kind: "error" });
            e.target.disabled = false;
            e.target.textContent = "Create & Analyze";
          }
        },
      }, ["Create & Analyze"]),
    ]),
  ]);
  backdrop.appendChild(panel);
  backdrop.onclick = (e) => { if (e.target === backdrop) backdrop.remove(); };
  document.body.appendChild(backdrop);
  setTimeout(() => nameInput.focus(), 50);
}

// ── Component: Use in Lab Modal ───────────────────────────────────────────
function useInLabModal(tpl) {
  const topicInput = h("input", { type: "text", placeholder: "Enter your video topic (optional)" });

  const backdrop = h("div", { class: "ch-ov-backdrop" });
  const panel = h("div", { class: "tpl-modal-panel" }, [
    h("div", { class: "tpl-modal-title" }, [`Use '${tpl.name}' in Lab`]),
    h("div", { class: "tpl-modal-sub" }, ["A new Lab session will be primed with this template's DNA and formula."]),
    h("label", { class: "tpl-modal-field" }, [
      h("label", {}, ["Topic"]),
      topicInput,
    ]),
    h("div", { class: "tpl-modal-actions" }, [
      h("button", {
        class: "btn ghost",
        onclick: () => backdrop.remove(),
      }, ["Cancel"]),
      h("button", {
        class: "btn primary",
        onclick: async (e) => {
          e.target.disabled = true;
          e.target.textContent = "Starting…";
          try {
            const res = await api.labFromTemplate(tpl.id, topicInput.value.trim());
            backdrop.remove();
            navigate("/lab", { templateSessionId: res.session_id });
          } catch (err) {
            toast(`Error: ${err.message}`, { kind: "error" });
            e.target.disabled = false;
            e.target.textContent = "Start Lab Session";
          }
        },
      }, ["Start Lab Session"]),
    ]),
  ]);
  backdrop.appendChild(panel);
  backdrop.onclick = (e) => { if (e.target === backdrop) backdrop.remove(); };
  document.body.appendChild(backdrop);
  setTimeout(() => topicInput.focus(), 50);
}

// ── Component: Template Overlay Panel ─────────────────────────────────────
async function openTemplateOverlay(tpl) {
  const backdrop = h("div", { class: "ch-ov-backdrop" });
  const panel = h("div", { class: "tpl-ov-panel" }, [
    h("div", { class: "tpl-ov-section-label" }, ["Loading…"]),
  ]);
  backdrop.appendChild(panel);
  backdrop.onclick = (e) => { if (e.target === backdrop) backdrop.remove(); };
  document.body.appendChild(backdrop);

  let detail;
  try {
    detail = await api.templateDetail(tpl.id);
  } catch (err) {
    panel.innerHTML = "";
    panel.appendChild(h("div", {}, [`Failed to load template: ${err.message}`]));
    return;
  }

  const badge = STATUS_BADGE[detail.status] || STATUS_BADGE.draft;
  // Dedupe video IDs defensively
  const videoIds = [...new Set(detail.example_video_ids || [])];
  const channels = detail.example_channels || [];

  panel.innerHTML = "";

  // Header — big title + description + actions
  panel.appendChild(
    h("div", { class: "tpl-ov-header" }, [
      h("div", { style: "flex:1; min-width:0;" }, [
        h("div", { class: "tpl-ov-title" }, [detail.name]),
        h("div", { class: "tpl-ov-desc" }, [detail.description || "No description yet."]),
        h("div", { style: "margin-top:12px; display:flex; gap:6px; align-items:center; flex-wrap:wrap;" }, [
          h("span", { class: `badge ${badge.cls}` }, [badge.label]),
          channels.length > 0 ? h("span", { class: "tpl-ov-meta-dot" }, ["·"]) : null,
          channels.length > 0 ? h("span", { class: "tpl-ov-meta" }, [`Based on ${channels.length} channel${channels.length === 1 ? "" : "s"}`]) : null,
          videoIds.length > 0 ? h("span", { class: "tpl-ov-meta-dot" }, ["·"]) : null,
          videoIds.length > 0 ? h("span", { class: "tpl-ov-meta" }, [`${videoIds.length} example${videoIds.length === 1 ? "" : "s"}`]) : null,
        ].filter(Boolean)),
      ]),
      h("div", { style: "display:flex; gap:8px; flex-shrink:0;" }, [
        detail.status === "ready"
          ? h("button", {
              class: "btn primary",
              onclick: () => { backdrop.remove(); useInLabModal(detail); },
            }, ["Use in Lab"])
          : null,
        h("button", {
          class: "btn ghost",
          onclick: () => backdrop.remove(),
        }, ["Close"]),
      ].filter(Boolean)),
    ])
  );

  // Example Videos — thumbnail grid, clickable to YouTube
  if (videoIds.length > 0) {
    const grid = h("div", { class: "tpl-ex-grid" });
    videoIds.forEach((vid, i) => {
      const channel = channels[i] || channels[i % channels.length] || {};
      const link = h("a", {
        class: "tpl-ex-card",
        href: `https://www.youtube.com/watch?v=${vid}`,
        target: "_blank",
        rel: "noopener",
        title: "Open on YouTube",
      }, [
        h("div", { class: "tpl-ex-thumb-wrap" }, [
          h("img", {
            class: "tpl-ex-thumb",
            src: `https://img.youtube.com/vi/${vid}/hqdefault.jpg`,
            loading: "lazy",
            alt: `Example ${i + 1}`,
          }),
          h("div", { class: "tpl-ex-play" }, ["▶"]),
        ]),
        h("div", { class: "tpl-ex-meta" }, [
          h("div", { class: "tpl-ex-channel" }, [channel.name || "YouTube video"]),
          h("div", { class: "tpl-ex-id" }, [vid]),
        ]),
      ]);
      grid.appendChild(link);
    });
    panel.appendChild(
      h("div", { class: "tpl-ov-section" }, [
        h("div", { class: "tpl-ov-section-label" }, ["Example Videos"]),
        grid,
      ])
    );
  }

  const onKey = (e) => {
    if (e.key === "Escape") { backdrop.remove(); document.removeEventListener("keydown", onKey); }
  };
  document.addEventListener("keydown", onKey);
}

// ── Polling for Analyzing Status ──────────────────────────────────────────
const pollTimers = new Map();

function startPolling(templateId, cardElement) {
  if (pollTimers.has(templateId)) return;

  const timer = setInterval(async () => {
    try {
      const status = await api.templateStatus(templateId);

      // Update card badge
      const badge = cardElement.querySelector(".badge");
      if (badge) {
        const badgeData = STATUS_BADGE[status.status];
        if (badgeData) {
          badge.className = `badge ${badgeData.cls}`;
          if (status.stage && status.status === "analyzing") {
            badge.textContent = status.stage;
          } else {
            badge.textContent = badgeData.label;
          }
        }
      }

      // Stop polling if done or error
      if (status.status === "ready" || status.status === "error") {
        clearInterval(timer);
        pollTimers.delete(templateId);

        // Reload the page to show updated template
        if (status.status === "ready") {
          setTimeout(() => location.reload(), 1000);
        }
      }
    } catch (e) {
      console.error("Poll error:", e);
      clearInterval(timer);
      pollTimers.delete(templateId);
    }
  }, 2000);

  pollTimers.set(templateId, timer);
}

// ── Main Mount ────────────────────────────────────────────────────────────
export async function mount(outlet, { state } = {}) {
  injectCSS();

  const page = h("div", { class: "page" }, [
    pageHeader({
      kicker: "My Studio",
      title: "My Templates",
      subtitle: "Build a library of proven content format templates. Each template captures formula, DNA, and example thumbnails. Create once, reuse forever.",
    }),
    h("div", { class: "channel-cards-grid", id: "templates-grid" }),
  ]);

  outlet.appendChild(page);
  const templatesGrid = $("#templates-grid");

  // Load templates
  try {
    const { templates } = await api.templates();
    templatesGrid.innerHTML = "";

    // Always show the "Create New Template" card first
    templatesGrid.appendChild(createNewTemplateCard());

    if (templates.length === 0) {
      // No need for another empty state — the create card is the CTA
      return;
    }

    // Dedupe by id (defensive — backend seeding can emit dupes)
    const seen = new Set();
    const uniq = templates.filter((t) => {
      if (!t || !t.id || seen.has(t.id)) return false;
      seen.add(t.id);
      return true;
    });

    for (const tpl of uniq) {
      templatesGrid.appendChild(templateCard(tpl));
      if (tpl.status === "analyzing") startPollingReload(tpl.id);
    }
    return;

    // (legacy empty state below kept for reference, never reached)
    if (false) {
      templatesGrid.appendChild(
        h("div", { style: "grid-column: 1/-1; text-align: center; padding: 60px 40px;" },
          h("p", { style: "font-size: 15px; color: var(--text-secondary); margin-bottom: 20px;" },
            "No templates yet. Create your first template to get started."
          ),
          h("p", { style: "font-size: 13px; color: var(--text-secondary); max-width: 50ch; margin: 0 auto; line-height: 1.6;" },
            "Templates capture proven YouTube content formulas (hook patterns, pacing, voice style). Once created, use them in The Lab to skip video reversal and jump straight to script generation."
          )
        )
      );
    } else {
      templates.forEach(tpl => {
        const card = templateCard(tpl);
        const cardWrapper = h("div", {}, card);
        templatesGrid.appendChild(cardWrapper);

        // Start polling if analyzing
        if (tpl.status === "analyzing") {
          startPolling(tpl.id, cardWrapper);
        }
      });
    }
  } catch (e) {
    templatesGrid.appendChild(
      h("div", { style: "grid-column: 1/-1; color: var(--text-danger); padding: 20px; text-align: center;" },
        `Error loading templates: ${e.message}`)
    );
  }
}
