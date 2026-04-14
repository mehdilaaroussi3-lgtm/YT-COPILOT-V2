// Sketch pad — 1280×720 drawing canvas that exports PNG for the generation
// pipeline. Your sketch becomes the LAYOUT blueprint; the channel reference
// handles style. Two blueprints, one thumbnail.

const W = 1280;
const H = 720;

const COLORS = [
  "#000000", "#1f2937", "#4b5563", "#9ca3af", "#e5e7eb",
  "#ef4444", "#f97316", "#eab308", "#22c55e", "#3b82f6",
  "#8b5cf6", "#ec4899",
];

const SIZES = [2, 5, 10, 18]; // stroke widths in canvas units

const SVG = {
  pen:     `<svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="M12 19l7-7 3 3-7 7-3-3z"/><path d="M18 13l-1.5-7.5L2 2l3.5 14.5L13 18l5-5z"/><path d="M2 2l7.586 7.586"/><circle cx="11" cy="11" r="2"/></svg>`,
  eraser:  `<svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="M20 20H7l-4-4a2 2 0 010-2.83l9-9a2 2 0 012.83 0l6 6a2 2 0 010 2.83l-9 9"/><path d="M6 11l7 7"/></svg>`,
  text:    `<svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="M4 7V4h16v3"/><path d="M9 20h6"/><path d="M12 4v16"/></svg>`,
  move:    `<svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><polyline points="5 9 2 12 5 15"/><polyline points="9 5 12 2 15 5"/><polyline points="15 19 12 22 9 19"/><polyline points="19 9 22 12 19 15"/><line x1="2" y1="12" x2="22" y2="12"/><line x1="12" y1="2" x2="12" y2="22"/></svg>`,
  shape:   `<svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><circle cx="8" cy="15" r="5"/><rect x="12" y="3" width="8" height="8" rx="1"/><path d="M6 3h6l-3 5z"/></svg>`,
  undo:    `<svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><polyline points="9 14 4 9 9 4"/><path d="M20 20v-7a4 4 0 00-4-4H4"/></svg>`,
  redo:    `<svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><polyline points="15 14 20 9 15 4"/><path d="M4 20v-7a4 4 0 014-4h12"/></svg>`,
  trash:   `<svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><polyline points="3 6 5 6 21 6"/><path d="M19 6l-1 14a2 2 0 01-2 2H8a2 2 0 01-2-2L5 6"/><path d="M10 11v6M14 11v6"/></svg>`,
  close:   `<svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="M18 6L6 18M6 6l12 12"/></svg>`,
  // shape submenu icons
  rect:     `<svg viewBox="0 0 24 24" width="14" height="14" fill="none" stroke="currentColor" stroke-width="1.8"><rect x="4" y="5" width="16" height="14" rx="1"/></svg>`,
  circle:   `<svg viewBox="0 0 24 24" width="14" height="14" fill="none" stroke="currentColor" stroke-width="1.8"><circle cx="12" cy="12" r="8"/></svg>`,
  arrow:    `<svg viewBox="0 0 24 24" width="14" height="14" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><line x1="5" y1="19" x2="19" y2="5"/><polyline points="10 5 19 5 19 14"/></svg>`,
  line:     `<svg viewBox="0 0 24 24" width="14" height="14" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round"><line x1="5" y1="19" x2="19" y2="5"/></svg>`,
  triangle: `<svg viewBox="0 0 24 24" width="14" height="14" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linejoin="round"><polygon points="12 4 21 20 3 20"/></svg>`,
};

const SHAPE_LABELS = {
  rectangle: "Rectangle", circle: "Circle", arrow: "Arrow",
  line: "Straight line", triangle: "Triangle",
};

function el(tag, attrs = {}, children = []) {
  const e = document.createElement(tag);
  for (const [k, v] of Object.entries(attrs)) {
    if (k === "html") e.innerHTML = v;
    else if (k === "style" && typeof v === "object") Object.assign(e.style, v);
    else if (k.startsWith("on") && typeof v === "function") e.addEventListener(k.slice(2).toLowerCase(), v);
    else if (v === true) e.setAttribute(k, "");
    else if (v !== false && v != null) e.setAttribute(k, v);
  }
  for (const c of [].concat(children)) {
    if (c == null || c === false) continue;
    e.appendChild(typeof c === "string" ? document.createTextNode(c) : c);
  }
  return e;
}

export function openSketchPad({ onUse, initialBlob } = {}) {
  const state = {
    tool: "pen",         // pen | eraser | text | move | shape
    shape: "rectangle",  // rectangle | circle | arrow | line | triangle
    color: COLORS[0],
    sizeIndex: 1,
    objects: [],
    undo: [],
    redo: [],
    selectedIdx: -1,
    dragOffset: null,
    draft: null,
    textEditor: null,    // {x, y, input, color, size}
  };

  // ── Build DOM ──────────────────────────────────────────
  const canvas = el("canvas", { class: "sketch-canvas", width: W, height: H });
  const ctx = canvas.getContext("2d");

  const toolBtn = (tool, icon, title) => {
    const b = el("button", { class: "sketch-tool-btn", title, html: icon, "data-tool": tool });
    b.addEventListener("click", () => { state.tool = tool; refreshToolbar(); });
    return b;
  };

  const penBtn    = toolBtn("pen", SVG.pen, "Pen");
  const eraserBtn = toolBtn("eraser", SVG.eraser, "Eraser");
  const textBtn   = toolBtn("text", SVG.text, "Text");
  const moveBtn   = toolBtn("move", SVG.move, "Move");

  // Shape button with dropdown
  const shapeBtn = el("button", { class: "sketch-tool-btn", title: "Shapes", html: SVG.shape, "data-tool": "shape" });
  const shapeMenu = el("div", { class: "sketch-shape-menu hidden" });
  const shapeEntries = [
    ["rectangle", SVG.rect], ["circle", SVG.circle], ["arrow", SVG.arrow],
    ["line", SVG.line], ["triangle", SVG.triangle],
  ];
  for (const [key, icon] of shapeEntries) {
    const item = el("button", { class: "sketch-shape-item", "data-shape": key }, [
      el("span", { html: icon }),
      el("span", {}, [SHAPE_LABELS[key]]),
    ]);
    item.addEventListener("click", (e) => {
      e.stopPropagation();
      state.tool = "shape"; state.shape = key;
      shapeMenu.classList.add("hidden");
      refreshToolbar();
    });
    shapeMenu.appendChild(item);
  }
  shapeBtn.addEventListener("click", (e) => {
    e.stopPropagation();
    state.tool = "shape"; refreshToolbar();
    shapeMenu.classList.toggle("hidden");
  });

  const shapeWrap = el("div", { class: "sketch-shape-wrap" }, [shapeBtn, shapeMenu]);

  // Size buttons
  const sizeBtns = SIZES.map((px, i) => {
    const b = el("button", { class: "sketch-size-btn", title: `Size ${i + 1}`, "data-size": i }, [
      el("span", { class: "sketch-size-dot", style: { width: `${Math.max(4, px)}px`, height: `${Math.max(4, px)}px` } }),
    ]);
    b.addEventListener("click", () => { state.sizeIndex = i; refreshToolbar(); });
    return b;
  });

  // Color buttons
  const colorBtns = COLORS.map((c) => {
    const b = el("button", { class: "sketch-color-btn", title: c, "data-color": c });
    b.style.background = c;
    b.addEventListener("click", () => { state.color = c; refreshToolbar(); });
    return b;
  });

  // Actions
  const undoBtn = el("button", { class: "sketch-action-btn", title: "Undo", html: SVG.undo });
  const redoBtn = el("button", { class: "sketch-action-btn", title: "Redo", html: SVG.redo });
  const clearBtn = el("button", { class: "sketch-action-btn danger", title: "Clear", html: SVG.trash });
  undoBtn.addEventListener("click", doUndo);
  redoBtn.addEventListener("click", doRedo);
  clearBtn.addEventListener("click", () => {
    if (!state.objects.length) return;
    pushUndo();
    state.objects = [];
    state.selectedIdx = -1;
    render();
  });

  const toolbar = el("div", { class: "sketch-toolbar" }, [
    el("div", { class: "sketch-tool-group" }, [penBtn, eraserBtn, textBtn, moveBtn, shapeWrap]),
    el("div", { class: "sketch-sep" }),
    el("div", { class: "sketch-size-group" }, sizeBtns),
    el("div", { class: "sketch-color-group" }, colorBtns),
    el("div", { class: "sketch-action-group" }, [undoBtn, redoBtn, clearBtn]),
  ]);

  const closeBtn = el("button", { class: "sketch-close", title: "Close", html: SVG.close });
  const header = el("div", { class: "sketch-header" }, [
    el("div", { class: "sketch-title" }, ["Draw your sketch"]),
    closeBtn,
  ]);

  const canvasWrap = el("div", { class: "sketch-canvas-wrap" }, [canvas]);

  const cancelBtn = el("button", { class: "btn" }, ["Cancel"]);
  const useBtn = el("button", { class: "btn primary" }, ["Use Sketch"]);
  const footer = el("div", { class: "sketch-footer" }, [
    el("div", { class: "sketch-footer-hint" }, ["This sketch tells Gemini WHERE things go. The channel reference controls HOW it looks."]),
    el("div", { class: "grow" }),
    cancelBtn, useBtn,
  ]);

  const panel = el("div", { class: "sketch-panel" }, [header, toolbar, canvasWrap, footer]);
  const backdrop = el("div", { class: "sketch-backdrop" }, [panel]);

  const close = () => {
    document.removeEventListener("keydown", onKey);
    document.removeEventListener("mousedown", onDocClick);
    backdrop.remove();
  };
  closeBtn.addEventListener("click", close);
  cancelBtn.addEventListener("click", close);
  backdrop.addEventListener("mousedown", (e) => { if (e.target === backdrop) close(); });

  // Close shape menu on outside click
  const onDocClick = (e) => {
    if (!shapeMenu.classList.contains("hidden") && !shapeWrap.contains(e.target)) {
      shapeMenu.classList.add("hidden");
    }
  };
  document.addEventListener("mousedown", onDocClick);

  useBtn.addEventListener("click", () => {
    commitTextEditor();
    canvas.toBlob((blob) => {
      if (!blob) return;
      const file = new File([blob], "sketch.png", { type: "image/png" });
      onUse && onUse(file);
      close();
    }, "image/png");
  });

  // Keyboard shortcuts
  const onKey = (e) => {
    if (state.textEditor) return; // typing inside text input
    if ((e.ctrlKey || e.metaKey) && e.key === "z") { e.preventDefault(); doUndo(); return; }
    if ((e.ctrlKey || e.metaKey) && (e.key === "y" || (e.shiftKey && e.key === "Z"))) { e.preventDefault(); doRedo(); return; }
    if (e.key === "Escape") { close(); return; }
    if (e.key === "Delete" || e.key === "Backspace") {
      if (state.selectedIdx >= 0) {
        pushUndo();
        state.objects.splice(state.selectedIdx, 1);
        state.selectedIdx = -1;
        render();
      }
    }
    // Tool shortcuts
    if (e.key === "p") { state.tool = "pen"; refreshToolbar(); }
    if (e.key === "e") { state.tool = "eraser"; refreshToolbar(); }
    if (e.key === "t") { state.tool = "text"; refreshToolbar(); }
    if (e.key === "v") { state.tool = "move"; refreshToolbar(); }
    if (e.key === "r") { state.tool = "shape"; state.shape = "rectangle"; refreshToolbar(); }
  };
  document.addEventListener("keydown", onKey);

  // ── Drawing logic ──────────────────────────────────────
  function pushUndo() {
    state.undo.push(JSON.stringify(state.objects));
    if (state.undo.length > 50) state.undo.shift();
    state.redo = [];
  }
  function doUndo() {
    if (!state.undo.length) return;
    state.redo.push(JSON.stringify(state.objects));
    state.objects = JSON.parse(state.undo.pop());
    state.selectedIdx = -1;
    render();
  }
  function doRedo() {
    if (!state.redo.length) return;
    state.undo.push(JSON.stringify(state.objects));
    state.objects = JSON.parse(state.redo.pop());
    state.selectedIdx = -1;
    render();
  }

  function getPos(e) {
    const rect = canvas.getBoundingClientRect();
    const scaleX = canvas.width / rect.width;
    const scaleY = canvas.height / rect.height;
    const pt = e.touches ? e.touches[0] : e;
    return { x: (pt.clientX - rect.left) * scaleX, y: (pt.clientY - rect.top) * scaleY };
  }

  function hitTest(p) {
    // Iterate topmost first
    for (let i = state.objects.length - 1; i >= 0; i--) {
      const o = state.objects[i];
      if (hitTestObject(p, o)) return i;
    }
    return -1;
  }
  function hitTestObject(p, o) {
    const pad = Math.max(8, o.size || 4);
    if (o.type === "rect") {
      return p.x >= Math.min(o.x, o.x + o.w) - pad && p.x <= Math.max(o.x, o.x + o.w) + pad &&
             p.y >= Math.min(o.y, o.y + o.h) - pad && p.y <= Math.max(o.y, o.y + o.h) + pad;
    }
    if (o.type === "circle") {
      const d = Math.hypot(p.x - o.cx, p.y - o.cy);
      return d <= o.r + pad;
    }
    if (o.type === "arrow" || o.type === "line") {
      return distToSegment(p, { x: o.x1, y: o.y1 }, { x: o.x2, y: o.y2 }) <= pad;
    }
    if (o.type === "triangle") {
      const [a, b, c] = [[o.x1, o.y1], [o.x2, o.y2], [o.x3, o.y3]];
      return pointInTriangle(p, a, b, c) ||
             distToSegment(p, { x: a[0], y: a[1] }, { x: b[0], y: b[1] }) <= pad ||
             distToSegment(p, { x: b[0], y: b[1] }, { x: c[0], y: c[1] }) <= pad ||
             distToSegment(p, { x: c[0], y: c[1] }, { x: a[0], y: a[1] }) <= pad;
    }
    if (o.type === "stroke") {
      for (const pt of o.points) {
        if (Math.hypot(pt.x - p.x, pt.y - p.y) <= pad) return true;
      }
      return false;
    }
    if (o.type === "text") {
      const tw = (o.text.length || 1) * o.size * 0.6;
      const th = o.size * 1.2;
      return p.x >= o.x && p.x <= o.x + tw && p.y >= o.y - th && p.y <= o.y;
    }
    return false;
  }
  function distToSegment(p, a, b) {
    const dx = b.x - a.x, dy = b.y - a.y;
    const len2 = dx*dx + dy*dy;
    if (!len2) return Math.hypot(p.x - a.x, p.y - a.y);
    let t = ((p.x - a.x) * dx + (p.y - a.y) * dy) / len2;
    t = Math.max(0, Math.min(1, t));
    return Math.hypot(p.x - (a.x + t * dx), p.y - (a.y + t * dy));
  }
  function sign(p, a, b) { return (p.x - b.x) * (a.y - b.y) - (a.x - b.x) * (p.y - b.y); }
  function pointInTriangle(p, a, b, c) {
    const d1 = sign(p, { x: a[0], y: a[1] }, { x: b[0], y: b[1] });
    const d2 = sign(p, { x: b[0], y: b[1] }, { x: c[0], y: c[1] });
    const d3 = sign(p, { x: c[0], y: c[1] }, { x: a[0], y: a[1] });
    const hasNeg = d1 < 0 || d2 < 0 || d3 < 0;
    const hasPos = d1 > 0 || d2 > 0 || d3 > 0;
    return !(hasNeg && hasPos);
  }

  function translateObject(o, dx, dy) {
    if (o.type === "rect") { o.x += dx; o.y += dy; }
    else if (o.type === "circle") { o.cx += dx; o.cy += dy; }
    else if (o.type === "arrow" || o.type === "line") { o.x1 += dx; o.y1 += dy; o.x2 += dx; o.y2 += dy; }
    else if (o.type === "triangle") { o.x1 += dx; o.y1 += dy; o.x2 += dx; o.y2 += dy; o.x3 += dx; o.y3 += dy; }
    else if (o.type === "stroke") { for (const p of o.points) { p.x += dx; p.y += dy; } }
    else if (o.type === "text") { o.x += dx; o.y += dy; }
  }

  // Pointer handlers
  let isDragging = false;
  let dragStart = null;

  canvas.addEventListener("mousedown", onDown);
  canvas.addEventListener("mousemove", onMove);
  window.addEventListener("mouseup", onUp);
  canvas.addEventListener("touchstart", (e) => { e.preventDefault(); onDown(e); });
  canvas.addEventListener("touchmove", (e) => { e.preventDefault(); onMove(e); });
  window.addEventListener("touchend", onUp);

  function onDown(e) {
    commitTextEditor();
    const p = getPos(e);
    const size = SIZES[state.sizeIndex];

    if (state.tool === "move") {
      const idx = hitTest(p);
      state.selectedIdx = idx;
      if (idx >= 0) {
        pushUndo();
        isDragging = true;
        dragStart = p;
      }
      render();
      return;
    }

    if (state.tool === "text") {
      openTextEditor(p, state.color, size);
      return;
    }

    if (state.tool === "pen") {
      pushUndo();
      state.draft = { type: "stroke", points: [p], color: state.color, size };
      isDragging = true; return;
    }

    if (state.tool === "eraser") {
      const idx = hitTest(p);
      if (idx >= 0) {
        pushUndo();
        state.objects.splice(idx, 1);
        render();
      }
      isDragging = true; // keep erasing while dragging
      return;
    }

    if (state.tool === "shape") {
      pushUndo();
      if (state.shape === "rectangle") state.draft = { type: "rect", x: p.x, y: p.y, w: 0, h: 0, color: state.color, size };
      else if (state.shape === "circle") state.draft = { type: "circle", cx: p.x, cy: p.y, r: 0, color: state.color, size };
      else if (state.shape === "arrow") state.draft = { type: "arrow", x1: p.x, y1: p.y, x2: p.x, y2: p.y, color: state.color, size };
      else if (state.shape === "line") state.draft = { type: "line", x1: p.x, y1: p.y, x2: p.x, y2: p.y, color: state.color, size };
      else if (state.shape === "triangle") state.draft = { type: "triangle", x1: p.x, y1: p.y, x2: p.x, y2: p.y, x3: p.x, y3: p.y, color: state.color, size, _start: p };
      isDragging = true; dragStart = p;
      return;
    }
  }

  function onMove(e) {
    if (!isDragging) {
      // Update cursor hint on hover
      return;
    }
    const p = getPos(e);

    if (state.tool === "move" && state.selectedIdx >= 0 && dragStart) {
      const o = state.objects[state.selectedIdx];
      translateObject(o, p.x - dragStart.x, p.y - dragStart.y);
      dragStart = p;
      render();
      return;
    }

    if (state.tool === "pen" && state.draft) {
      state.draft.points.push(p);
      render();
      return;
    }

    if (state.tool === "eraser") {
      const idx = hitTest(p);
      if (idx >= 0) {
        state.objects.splice(idx, 1);
        render();
      }
      return;
    }

    if (state.tool === "shape" && state.draft) {
      const d = state.draft;
      if (d.type === "rect") { d.w = p.x - d.x; d.h = p.y - d.y; }
      else if (d.type === "circle") { d.r = Math.hypot(p.x - d.cx, p.y - d.cy); }
      else if (d.type === "arrow" || d.type === "line") { d.x2 = p.x; d.y2 = p.y; }
      else if (d.type === "triangle") {
        // Equilateral-ish: start = bottom-left, drag defines opposite vertex
        const s = d._start;
        d.x1 = s.x; d.y1 = p.y;
        d.x3 = p.x; d.y3 = p.y;
        d.x2 = (s.x + p.x) / 2; d.y2 = s.y - Math.abs(p.x - s.x) * 0.5;
      }
      render();
      return;
    }
  }

  function onUp() {
    if (!isDragging) return;
    isDragging = false;
    dragStart = null;

    if (state.draft) {
      // Drop degenerate shapes (too small to be intentional)
      const d = state.draft;
      const minSize = 3;
      let keep = true;
      if (d.type === "rect" && (Math.abs(d.w) < minSize || Math.abs(d.h) < minSize)) keep = false;
      if (d.type === "circle" && d.r < minSize) keep = false;
      if ((d.type === "arrow" || d.type === "line") && Math.hypot(d.x2 - d.x1, d.y2 - d.y1) < minSize) keep = false;
      if (d.type === "stroke" && d.points.length < 2) keep = false;
      if (d.type === "triangle" && Math.hypot(d.x3 - d.x1, d.y3 - d.y1) < minSize) keep = false;
      if (d.type === "triangle") delete d._start;
      if (keep) state.objects.push(d);
      state.draft = null;
      render();
    }
  }

  // Text editor (inline input overlay on canvas)
  function openTextEditor(p, color, size) {
    commitTextEditor();
    const rect = canvas.getBoundingClientRect();
    const scaleX = rect.width / canvas.width;
    const scaleY = rect.height / canvas.height;
    const input = el("input", {
      type: "text", class: "sketch-text-input",
      placeholder: "type…",
    });
    input.style.left = `${p.x * scaleX}px`;
    input.style.top = `${(p.y - size * 1.2) * scaleY}px`;
    input.style.color = color;
    input.style.fontSize = `${size * 2 * scaleY}px`;
    canvasWrap.appendChild(input);
    state.textEditor = { x: p.x, y: p.y, color, size: size * 2, input };
    setTimeout(() => input.focus(), 10);
    input.addEventListener("keydown", (e) => {
      if (e.key === "Enter" || e.key === "Escape") { e.preventDefault(); commitTextEditor(); }
    });
    input.addEventListener("blur", () => commitTextEditor());
  }
  function commitTextEditor() {
    const te = state.textEditor;
    if (!te) return;
    const text = te.input.value.trim();
    te.input.remove();
    state.textEditor = null;
    if (text) {
      pushUndo();
      state.objects.push({ type: "text", x: te.x, y: te.y, text, color: te.color, size: te.size });
      render();
    }
  }

  // ── Rendering ──────────────────────────────────────────
  function drawObject(c, o) {
    c.strokeStyle = o.color;
    c.fillStyle = o.color;
    c.lineWidth = o.size;
    c.lineCap = "round";
    c.lineJoin = "round";

    if (o.type === "stroke") {
      if (o.points.length < 2) {
        c.beginPath(); c.arc(o.points[0].x, o.points[0].y, o.size / 2, 0, Math.PI * 2); c.fill();
        return;
      }
      c.beginPath();
      c.moveTo(o.points[0].x, o.points[0].y);
      for (let i = 1; i < o.points.length; i++) c.lineTo(o.points[i].x, o.points[i].y);
      c.stroke();
    }
    else if (o.type === "rect") {
      c.strokeRect(o.x, o.y, o.w, o.h);
    }
    else if (o.type === "circle") {
      c.beginPath(); c.arc(o.cx, o.cy, o.r, 0, Math.PI * 2); c.stroke();
    }
    else if (o.type === "line") {
      c.beginPath(); c.moveTo(o.x1, o.y1); c.lineTo(o.x2, o.y2); c.stroke();
    }
    else if (o.type === "arrow") {
      c.beginPath(); c.moveTo(o.x1, o.y1); c.lineTo(o.x2, o.y2); c.stroke();
      // arrowhead
      const angle = Math.atan2(o.y2 - o.y1, o.x2 - o.x1);
      const head = Math.max(12, o.size * 3);
      c.beginPath();
      c.moveTo(o.x2, o.y2);
      c.lineTo(o.x2 - head * Math.cos(angle - Math.PI / 7), o.y2 - head * Math.sin(angle - Math.PI / 7));
      c.lineTo(o.x2 - head * Math.cos(angle + Math.PI / 7), o.y2 - head * Math.sin(angle + Math.PI / 7));
      c.closePath(); c.fill();
    }
    else if (o.type === "triangle") {
      c.beginPath();
      c.moveTo(o.x1, o.y1); c.lineTo(o.x2, o.y2); c.lineTo(o.x3, o.y3);
      c.closePath(); c.stroke();
    }
    else if (o.type === "text") {
      c.font = `${o.size}px Inter, system-ui, -apple-system, sans-serif`;
      c.textBaseline = "alphabetic";
      c.fillText(o.text, o.x, o.y);
    }
  }

  function drawSelection(c, o) {
    c.save();
    c.strokeStyle = "#3b82f6";
    c.setLineDash([6, 4]);
    c.lineWidth = 2;
    const b = bounds(o);
    if (b) c.strokeRect(b.x - 6, b.y - 6, b.w + 12, b.h + 12);
    c.restore();
  }
  function bounds(o) {
    if (o.type === "rect") return { x: Math.min(o.x, o.x + o.w), y: Math.min(o.y, o.y + o.h), w: Math.abs(o.w), h: Math.abs(o.h) };
    if (o.type === "circle") return { x: o.cx - o.r, y: o.cy - o.r, w: o.r * 2, h: o.r * 2 };
    if (o.type === "arrow" || o.type === "line") return { x: Math.min(o.x1, o.x2), y: Math.min(o.y1, o.y2), w: Math.abs(o.x2 - o.x1), h: Math.abs(o.y2 - o.y1) };
    if (o.type === "triangle") {
      const xs = [o.x1, o.x2, o.x3], ys = [o.y1, o.y2, o.y3];
      return { x: Math.min(...xs), y: Math.min(...ys), w: Math.max(...xs) - Math.min(...xs), h: Math.max(...ys) - Math.min(...ys) };
    }
    if (o.type === "stroke") {
      const xs = o.points.map(p => p.x), ys = o.points.map(p => p.y);
      return { x: Math.min(...xs), y: Math.min(...ys), w: Math.max(...xs) - Math.min(...xs), h: Math.max(...ys) - Math.min(...ys) };
    }
    if (o.type === "text") {
      const tw = (o.text.length || 1) * o.size * 0.6;
      return { x: o.x, y: o.y - o.size, w: tw, h: o.size * 1.2 };
    }
    return null;
  }

  function render() {
    ctx.fillStyle = "#ffffff";
    ctx.fillRect(0, 0, W, H);
    for (const o of state.objects) drawObject(ctx, o);
    if (state.draft) drawObject(ctx, state.draft);
    if (state.tool === "move" && state.selectedIdx >= 0) {
      drawSelection(ctx, state.objects[state.selectedIdx]);
    }
    refreshActions();
  }

  function refreshToolbar() {
    for (const b of toolbar.querySelectorAll("[data-tool]")) {
      b.classList.toggle("active", b.dataset.tool === state.tool);
    }
    for (const b of toolbar.querySelectorAll("[data-size]")) {
      b.classList.toggle("active", parseInt(b.dataset.size, 10) === state.sizeIndex);
    }
    for (const b of toolbar.querySelectorAll("[data-color]")) {
      b.classList.toggle("active", b.dataset.color === state.color);
    }
    // Update cursor on canvas
    canvas.style.cursor = state.tool === "move" ? "grab"
      : state.tool === "text" ? "text"
      : state.tool === "eraser" ? "cell"
      : "crosshair";
  }
  function refreshActions() {
    undoBtn.disabled = state.undo.length === 0;
    redoBtn.disabled = state.redo.length === 0;
    clearBtn.disabled = state.objects.length === 0;
  }

  // ── Init ───────────────────────────────────────────────
  document.body.appendChild(backdrop);
  refreshToolbar();
  render();

  // Load initial image if provided (e.g. editing a previous sketch)
  if (initialBlob) {
    const img = new Image();
    img.onload = () => {
      ctx.drawImage(img, 0, 0, W, H);
      // We don't have vector objects from a bitmap, so stash as a single stroke-like object is impossible.
      // Just draw it on the background. User can add shapes on top.
    };
    img.src = URL.createObjectURL(initialBlob);
  }

  return { close };
}
