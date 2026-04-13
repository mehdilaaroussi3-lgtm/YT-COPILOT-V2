// Thumbnail Generator — single output, follows referenced channel's style.

import { api } from "../api.js";
import { h, icons, toast, $, formatRelative, channelPicker } from "../components.js";
import { streamJob } from "../lib/sse.js";

export async function mount(outlet, { state }) {
  outlet.appendChild(h("div", { class: "page-center" }, [
    h("h1", { class: "page-title" }, ["Thumbnail Generator"]),
    h("div", { class: "page-subtitle" }, ["One generation per run, in the artistic style of any channel you've added."]),
  ]));

  const trackers = (await api.trackers()).items;
  const defaultTracker = trackers.find((t) => t.is_default);

  const prefillTitle = state?.prefill_title || "";
  const prefillChannel = state?.channel || "default";

  const titleEl = h("textarea", {
    class: "textarea", id: "title", rows: 3,
    placeholder: "Write the title you have in mind OR what the video is about",
  }, [prefillTitle]);
  const hookEl = h("span", { class: "value", id: "hook" }, ["—"]);
  const pairingEl = h("span", { class: "score", id: "pairing" }, [""]);

  const sketchInput = h("input", { type: "file", accept: "image/*" });
  const sketchChip = h("label", { class: "file-chip" }, [h("span", { html: icons.refine }), " Sketch", sketchInput]);
  sketchInput.addEventListener("change", () => sketchChip.classList.toggle("has-file", !!sketchInput.files[0]));

  const refInput = h("input", { type: "file", accept: "image/*" });
  const refChip = h("label", { class: "file-chip" }, [h("span", { html: icons.plus }), " Reference image", refInput]);
  refInput.addEventListener("change", () => refChip.classList.toggle("has-file", !!refInput.files[0]));

  const noTextToggle = h("label", { class: "toggle" }, [
    h("input", { type: "checkbox", id: "notext" }),
    h("span", { class: "toggle-switch" }),
    "No text",
  ]);

  const countSel = h("select", { class: "select count-select", id: "varCount" }, [
    h("option", { value: "1" }, ["1"]),
    h("option", { value: "2", selected: "selected" }, ["2"]),
    h("option", { value: "4" }, ["4"]),
    h("option", { value: "8" }, ["8"]),
  ]);

  const picker = channelPicker({
    items: trackers,
    selected: (prefillChannel && prefillChannel.startsWith("UC")) ? prefillChannel : (defaultTracker?.channel_id || ""),
    onChange: () => refreshHook(),
  });

  const genBtn = h("button", { class: "btn huge" }, [
    h("span", { html: icons.sparkle }),
    h("span", {}, ["Generate"]),
  ]);

  const form = h("div", { class: "card", style: { marginBottom: "24px" } }, [
    h("label", { class: "field-label" }, ["Channel"]),
    picker.el,
    h("div", { class: "caption", style: { marginTop: "8px", marginBottom: "20px" } }, [
      "Thumbnails will be generated in this channel's visual style — palette, composition, lighting — adapted to your title.",
    ]),

    h("label", { class: "field-label" }, ["Video title"]),
    titleEl,
    h("div", { class: "hook-preview", style: { marginTop: "12px" } }, [
      h("span", { class: "label" }, ["Auto hook"]),
      hookEl,
      pairingEl,
    ]),

    h("div", { class: "form-row", style: { marginTop: "20px", marginBottom: "20px", alignItems: "center" } }, [
      sketchChip, refChip, noTextToggle,
      h("div", { class: "grow" }),
      countSel,
      genBtn,
    ]),
  ]);
  outlet.appendChild(form);

  const progressPanel = h("div", { class: "progress-panel hidden", id: "progress" });
  outlet.appendChild(progressPanel);

  const resultsWrap = h("div", { id: "results", style: { marginTop: "32px" } });
  outlet.appendChild(resultsWrap);

  const historyWrap = h("div", { id: "history", style: { marginTop: "56px" } });
  outlet.appendChild(historyWrap);

  // Auto-hook preview — uses channel's text DNA when available.
  let hookDebounce;
  const refreshHook = () => {
    clearTimeout(hookDebounce);
    hookDebounce = setTimeout(async () => {
      const title = titleEl.value.trim();
      if (!title) { hookEl.textContent = "—"; pairingEl.textContent = ""; return; }
      const ch = picker.getValue();
      try {
        const r = await api.hook(title, ch);
        // Multi-line hooks: show the first line in preview with a "+N" badge
        const lines = (r.hook || "").split("\n").filter(Boolean);
        hookEl.textContent = lines[0] || "—";
        if (lines.length > 1) hookEl.textContent += `  +${lines.length - 1} line`;
        const p = r.pairing;
        pairingEl.textContent =
          `${r.smart ? "channel-DNA  ·  " : ""}pairing ${p.score}/10` +
          (p.issues.length ? " — " + p.issues[0] : "");
        pairingEl.classList.toggle("good", p.score >= 7);
        pairingEl.classList.toggle("bad", p.score < 4);
      } catch { /* ignore */ }
    }, 400);
  };
  titleEl.addEventListener("input", refreshHook);
  // Channel changes are wired via channelPicker({ onChange }) above.
  if (prefillTitle) titleEl.dispatchEvent(new Event("input"));

  let activeAbort = null;
  let activeJobId = null;

  function setGenerating(on) {
    if (on) {
      genBtn.innerHTML = `<span class="spinner-sm"></span><span>Stop Generation</span>`;
      genBtn.classList.add("stop");
    } else {
      genBtn.innerHTML = `<span>${icons.sparkle}</span><span>Generate</span>`;
      genBtn.classList.remove("stop");
    }
  }

  function renderSkeletons(n) {
    resultsWrap.innerHTML = "";
    const cols = n === 1 ? 1 : n === 8 ? 4 : 2;
    const grid = h("div", {
      class: "variant-grid",
      id: "variant-grid",
      style: { "--cols": String(cols) },
    });
    for (let i = 0; i < n; i++) {
      const tile = h("div", { class: "variant-tile loading", "data-variant": String(i + 1) }, [
        h("div", { class: "variant-spinner" }),
        h("div", { class: "variant-timer", "data-start": String(Date.now()) }, ["0s"]),
      ]);
      grid.appendChild(tile);
    }
    resultsWrap.appendChild(grid);

    // Tick timers
    const tick = () => {
      const tiles = grid.querySelectorAll(".variant-tile.loading .variant-timer");
      tiles.forEach((t) => {
        const start = parseInt(t.getAttribute("data-start"), 10);
        t.textContent = `${Math.max(0, Math.floor((Date.now() - start) / 1000))}s`;
      });
    };
    const interval = setInterval(() => {
      if (!grid.isConnected) return clearInterval(interval);
      tick();
    }, 500);
  }

  function fillVariant(data) {
    const grid = document.getElementById("variant-grid");
    if (!grid) return;
    const tile = grid.querySelector(`.variant-tile[data-variant="${data.variant}"]`);
    if (!tile) return;
    tile.classList.remove("loading");
    tile.innerHTML = "";
    if (data.error || !data.url) {
      tile.classList.add("error");
      tile.appendChild(h("div", { class: "variant-err" }, [data.error || "Generation failed"]));
      return;
    }
    // Store current URL on the tile so the editor can mutate it safely across edits.
    tile.dataset.url = data.url;
    tile.dataset.originalUrl = data.url;
    const img = h("img", { class: "variant-img", src: data.url, alt: "", loading: "eager" });
    img.addEventListener("click", () => openEditor(tile.dataset.url, tile));

    const dots = `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="currentColor" width="18" height="18"><circle cx="5" cy="12" r="2"/><circle cx="12" cy="12" r="2"/><circle cx="19" cy="12" r="2"/></svg>`;
    const menuBtn = h("button", {
      class: "variant-menu-btn", title: "More",
      onclick: (e) => { e.stopPropagation(); openTileMenu(e.currentTarget, tile.dataset.url, tile); },
      html: dots,
    });
    tile.appendChild(img);
    tile.appendChild(menuBtn);
  }

  function openTileMenu(anchor, url, tile) {
    document.querySelectorAll(".tile-menu").forEach((m) => m.remove());
    const menu = h("div", { class: "tile-menu" }, [
      menuItem(icons.download, "Download", () => {
        const a = document.createElement("a");
        a.href = url; a.download = ""; a.click();
      }),
      menuItem(icons.sparkle, "Inspiration", () => {
        window.open(url, "_blank");
      }),
      menuItem(icons.folder, "Save to folder", () => {
        toast("Saved to output folder", { kind: "success" });
      }),
      h("div", { class: "tile-menu-sep" }),
      menuItem(icons.refine, "Edit with AI", () => openEditor(url, tile)),
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

  function openEditor(imageUrl, parentTile) {
    // Version history persists across refines within this editor session.
    // Persist to sessionStorage keyed by the ORIGINAL url so versions survive
    // navigation away and back.
    const storageKey = `editor_versions::${imageUrl}`;
    let versions;
    try {
      versions = JSON.parse(sessionStorage.getItem(storageKey) || "null");
    } catch { versions = null; }
    if (!versions || !versions.length) {
      versions = [{ url: imageUrl, label: "Original", instruction: "" }];
    }
    let currentIdx = versions.length - 1;

    const persist = () => {
      try { sessionStorage.setItem(storageKey, JSON.stringify(versions)); } catch {}
    };

    const backdrop = h("div", { class: "editor-backdrop", onclick: (e) => { if (e.target === backdrop) close(); } });
    const close = () => backdrop.remove();

    const stageImg = h("img", { class: "editor-img", src: versions[currentIdx].url, alt: "" });
    const stage = h("div", { class: "editor-stage" }, [stageImg]);

    const versionList = h("div", { class: "editor-versions" });
    const renderVersions = () => {
      versionList.innerHTML = "";
      versions.forEach((v, i) => {
        const chip = h("button", {
          class: `editor-version-chip${i === currentIdx ? " active" : ""}`,
          title: v.instruction || v.label,
          onclick: () => { currentIdx = i; stageImg.src = v.url; renderVersions(); },
        }, [
          h("img", { src: v.url, class: "editor-version-thumb", alt: "" }),
          h("span", { class: "editor-version-label" }, [v.label]),
        ]);
        versionList.appendChild(chip);
      });
    };
    renderVersions();

    const promptBox = h("textarea", {
      class: "editor-prompt",
      placeholder: "Describe how to refine this thumbnail — e.g. 'darker palette, push subject right, remove the text'",
      rows: 5,
    });
    const addImgInput = h("input", { type: "file", accept: "image/*" });
    const addImgChip = h("label", { class: "file-chip" }, [h("span", { html: icons.plus }), " Add reference image", addImgInput]);
    addImgInput.addEventListener("change", () => addImgChip.classList.toggle("has-file", !!addImgInput.files[0]));

    const submit = h("button", { class: "btn primary", html: `${icons.refine}<span>Generate edit</span>` });
    const statusLine = h("div", { class: "editor-status" });

    submit.addEventListener("click", async () => {
      const instr = promptBox.value.trim();
      if (!instr) { toast("Write what to change", { kind: "error" }); return; }
      submit.disabled = true;
      submit.innerHTML = `<span class="spinner-sm"></span><span>Generating edit…</span>`;
      statusLine.textContent = "Refining with Gemini…";
      try {
        const fd = new FormData();
        // Always refine from the CURRENTLY shown version so edits can chain.
        fd.append("image_url", versions[currentIdx].url);
        fd.append("instruction", instr);
        if (addImgInput.files[0]) fd.append("reference", addImgInput.files[0]);
        const r = await api.refine(fd);
        if (r.error) { toast(r.error, { kind: "error" }); return; }
        versions.push({
          url: r.url,
          label: `Edit ${versions.length}`,
          instruction: instr,
        });
        currentIdx = versions.length - 1;
        stageImg.src = r.url;
        renderVersions();
        persist();
        promptBox.value = "";
        addImgInput.value = "";
        addImgChip.classList.remove("has-file");
        statusLine.textContent = `Edit ${versions.length - 1} ready. Switch between versions in the strip above.`;
      } catch (e) {
        toast(e.message, { kind: "error" });
      } finally {
        submit.disabled = false;
        submit.innerHTML = `${icons.refine}<span>Generate edit</span>`;
      }
    });

    const applyBtn = h("button", {
      class: "btn primary", title: "Replace the thumbnail in the grid with the selected version",
      html: `${icons.check || ""}<span>Apply to thumbnail</span>`,
    });
    applyBtn.addEventListener("click", () => {
      const chosenUrl = versions[currentIdx].url;
      if (parentTile) {
        parentTile.dataset.url = chosenUrl;
        const tileImg = parentTile.querySelector(".variant-img, .thumb-img");
        if (tileImg) tileImg.src = chosenUrl;
        toast("Applied to grid", { kind: "success" });
      } else {
        toast("No grid tile to apply to — download the image instead", { kind: "info" });
      }
      close();
    });

    const dlBtn = h("a", {
      class: "btn sm",
      href: versions[currentIdx].url, download: "",
      html: `${icons.download}<span>Download</span>`,
    });
    // Keep download button pointing at the currently-selected version
    const refreshDL = () => { dlBtn.href = versions[currentIdx].url; };
    stageImg.addEventListener("load", refreshDL);

    const closeBtn = h("button", { class: "editor-close", onclick: close, html: icons.x });

    const versionHeader = h("div", { class: "editor-label" }, [
      h("span", {}, ["Versions"]),
      h("span", { class: "editor-hint" }, ["— click to switch, nothing is ever lost"]),
    ]);

    const sidebar = h("div", { class: "editor-sidebar" }, [
      h("div", { class: "editor-title" }, ["Edit Thumbnail"]),
      versionHeader,
      versionList,
      h("div", { class: "editor-label", style: { marginTop: "16px" } }, ["Your prompt"]),
      promptBox,
      h("div", { style: { marginTop: "12px", marginBottom: "14px" } }, [addImgChip]),
      submit,
      statusLine,
      h("div", { class: "editor-actions-row" }, [applyBtn, dlBtn]),
    ]);

    const panel = h("div", { class: "editor-panel" }, [stage, sidebar, closeBtn]);
    backdrop.appendChild(panel);
    document.body.appendChild(backdrop);
    setTimeout(() => promptBox.focus(), 50);
  }

  async function stopGeneration() {
    if (!activeJobId) return;
    try { await fetch(`/api/generate/${activeJobId}/cancel`, { method: "POST" }); } catch {}
    if (activeAbort) activeAbort.abort();
  }

  function saveJobState(jobId, nVar) {
    sessionStorage.setItem("thumbnail_active_job", jobId);
    sessionStorage.setItem("thumbnail_active_variants", String(nVar));
  }

  function clearJobState() {
    sessionStorage.removeItem("thumbnail_active_job");
    sessionStorage.removeItem("thumbnail_active_variants");
  }

  async function reconnectToJob(jobId, nVar) {
    setGenerating(true);
    progressPanel.classList.remove("hidden");
    progressPanel.innerHTML = "";
    renderSkeletons(nVar);

    const log = (msg, cls) => {
      progressPanel.appendChild(h("div", { class: `progress-line ${cls || ""}` }, [msg]));
      progressPanel.scrollTop = progressPanel.scrollHeight;
    };
    log("Reconnecting to active generation…");

    activeAbort = new AbortController();
    activeJobId = jobId;
    try {
      const result = await streamJob(`/api/progress/${jobId}`, {
        onMessage: (d) => d.msg && log(d.msg),
        onVariant: (d) => fillVariant(d),
        signal: activeAbort.signal,
      });
      log("Done.", "done");
      historyWrap.innerHTML = "";
    } catch (e) {
      if (e.name === "AbortError") {
        log("Stopped.", "error");
      } else {
        log(`Failed: ${e.message}`, "error");
      }
    } finally {
      activeJobId = null;
      activeAbort = null;
      setGenerating(false);
      clearJobState();
    }
  }

  // Check for active job on mount
  const savedJobId = sessionStorage.getItem("thumbnail_active_job");
  const savedVariants = parseInt(sessionStorage.getItem("thumbnail_active_variants") || "0", 10);
  if (savedJobId && savedVariants > 0) {
    setTimeout(() => reconnectToJob(savedJobId, savedVariants), 100);
  }

  genBtn.addEventListener("click", async () => {
    if (genBtn.classList.contains("stop")) {
      stopGeneration();
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
    fd.append("no_text", $("#notext", form).checked ? "true" : "false");
    fd.append("variants", String(nVar));
    if (sketchInput.files[0]) fd.append("sketch", sketchInput.files[0]);
    if (refInput.files[0]) fd.append("reference", refInput.files[0]);

    setGenerating(true);
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
      saveJobState(job_id, nVar);
      const result = await streamJob(`/api/progress/${job_id}`, {
        onMessage: (d) => d.msg && log(d.msg),
        onVariant: (d) => fillVariant(d),
        signal: activeAbort.signal,
      });
      log("Done.", "done");
      historyWrap.innerHTML = "";
    } catch (e) {
      if (e.name === "AbortError") {
        log("Stopped.", "error");
      } else {
        log(`Failed: ${e.message}`, "error");
        toast("Generation failed", { kind: "error" });
      }
    } finally {
      activeJobId = null;
      activeAbort = null;
      setGenerating(false);
      clearJobState();
    }
  });

  async function renderHistory() {
    const r = await api.thumbnailsHistory();
    historyWrap.innerHTML = "";
    if (!r.items.length) return;
    historyWrap.appendChild(h("div", { class: "section-head" }, [
      h("div", { class: "section-title" }, ["History"]),
      h("div", { class: "section-sub" }, ["Hover over any image to refine it with AI"]),
    ]));
    const grid = h("div", { class: "thumb-grid" });
    for (const gen of r.items.slice(0, 18)) grid.appendChild(historyCard(gen));
    historyWrap.appendChild(grid);
  }

  function historyCard(gen) {
    const url = gen.url;
    const dots = `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="currentColor" width="18" height="18"><circle cx="5" cy="12" r="2"/><circle cx="12" cy="12" r="2"/><circle cx="19" cy="12" r="2"/></svg>`;
    const img = h("img", { class: "thumb-img", src: url, loading: "lazy" });
    const card = h("div", { class: "thumb-card" });
    card.dataset.url = url;
    img.addEventListener("click", () => openEditor(card.dataset.url, card));
    const menuBtn = h("button", {
      class: "variant-menu-btn history-menu-btn", title: "More",
      onclick: (e) => { e.stopPropagation(); openTileMenu(e.currentTarget, card.dataset.url, card); },
      html: dots,
    });
    const imgWrap = h("div", { class: "thumb-img-wrap" }, [img, menuBtn]);
    card.appendChild(imgWrap);
    card.appendChild(h("div", { class: "thumb-meta" }, [
      h("div", { class: "thumb-title" }, [gen.title || "—"]),
      h("div", { class: "thumb-sub" }, [formatRelative(gen.created_at)]),
    ]));
    return card;
  }
  renderHistory();
}
