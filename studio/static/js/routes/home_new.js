// Home — logo + animated catchphrase + three auto-scrolling marquees.

import { api } from "../api.js";
import { h } from "../components.js";
import { navigate } from "../router.js";

const CATCHPHRASES = [
  "Decode what's winning. Build what's next.",
  "Your AI co-pilot for viral YouTube growth.",
  "Reverse-engineer virality. Ship faster.",
];

export async function mount(outlet) {
  // ── HERO: logo + animated catchphrase ──────────────────────────────────────
  outlet.appendChild(
    h("div", { class: "home-hero" }, [
      h("img", { class: "home-logo", src: "/static/img/logo.png", alt: "YTcopilot" }),
      h("div", { class: "home-catchphrase", id: "catchphrase" }, [CATCHPHRASES[0]]),
    ]),
  );
  startCatchphraseRotator();

  // ── Section 1 — THUMBNAILS ────────────────────────────────────────────────
  outlet.appendChild(makeSection({
    title: "Create thumbnails",
    subtitle: "Premium outliers from top faceless channels. Click any to use as reference.",
    onTitleClick: () => navigate("/thumbnails"),
    trackId: "thumb-track",
    klass: "thumb-marquee",
  }));

  // ── Section 2 — CHANNELS ───────────────────────────────────────────────────
  outlet.appendChild(makeSection({
    title: "Copy Any Channel",
    subtitle: "Browse creators whose style you can replicate end-to-end.",
    onTitleClick: () => navigate("/random-channels"),
    trackId: "chan-track",
    klass: "channel-marquee",
  }));

  // ── Section 3 — STYLES ─────────────────────────────────────────────────────
  outlet.appendChild(makeSection({
    title: "Create with the style you want",
    subtitle: "Pick a visual style and generate videos that match it.",
    onTitleClick: () => navigate("/lab"),
    trackId: "style-track",
    klass: "style-marquee",
  }));

  // ── Load all data in parallel ──────────────────────────────────────────────
  const [premRes, chRes, styleRes] = await Promise.all([
    api.outliersPremium(30, 1).catch(() => ({ items: [] })),
    api.channelsRandom(24).catch(() => ({ items: [] })),
    fetch("/api/styles/custom").then((r) => r.json()).catch(() => ({ items: [] })),
  ]);

  renderThumbTrack(premRes.items || []);
  renderChannelTrack(chRes.items || []);
  renderStyleTrack(styleRes.items || []);
}

// ── Catchphrase rotator ──────────────────────────────────────────────────────

function startCatchphraseRotator() {
  const el = document.getElementById("catchphrase");
  if (!el) return;
  let i = 0;
  setInterval(() => {
    i = (i + 1) % CATCHPHRASES.length;
    el.classList.remove("fade-in");
    void el.offsetWidth; // force reflow so animation replays
    el.textContent = CATCHPHRASES[i];
    el.classList.add("fade-in");
  }, 4500);
}

// ── Section helper ───────────────────────────────────────────────────────────

function makeSection({ title, subtitle, onTitleClick, trackId, klass }) {
  return h("div", { class: "home-marquee-section" }, [
    h("div", { class: "marquee-heading clickable", onclick: onTitleClick }, [
      h("h2", { class: "marquee-title" }, [title]),
      h("div", { class: "marquee-subtitle" }, [subtitle]),
    ]),
    h("div", { class: `marquee ${klass}` }, [
      h("div", { class: "marquee-track", id: trackId }),
    ]),
  ]);
}

// ── Thumbnail marquee (premium outliers only — no user creations) ────────────

function renderThumbTrack(items) {
  const track = document.getElementById("thumb-track");
  if (!track) return;
  if (!items.length) {
    track.appendChild(h("div", { class: "marquee-empty" }, ["No premium thumbnails yet — run a scan."]));
    return;
  }
  // Duplicate for seamless loop
  const doubled = [...items, ...items];
  for (const it of doubled) track.appendChild(thumbSlide(it));
}

function thumbSlide(it) {
  const score = it.outlier_score || 0;
  return h("div", {
    class: "slide thumb-slide",
    title: it.title || "",
  }, [
    h("img", {
      class: "slide-img",
      src: it.thumb_url || it.yt_thumb_url || "",
      alt: it.title || "",
      loading: "lazy",
    }),
    score ? h("div", { class: "slide-badge" }, [`${score.toFixed(1)}x`]) : null,
  ].filter(Boolean));
}

// ── Channel marquee ──────────────────────────────────────────────────────────

function renderChannelTrack(channels) {
  const track = document.getElementById("chan-track");
  if (!track) return;
  const quality = channels.filter((c) => c.name && (c.avatar_url || c.outlier_count > 0));
  const pool = quality.length ? quality : channels;
  if (!pool.length) {
    track.appendChild(h("div", { class: "marquee-empty" }, ["No channels yet — add some in Trackers."]));
    return;
  }
  const doubled = [...pool, ...pool];
  for (const ch of doubled) track.appendChild(channelSlide(ch));
}

function channelSlide(ch) {
  const initials = (ch.name || "?").trim().charAt(0).toUpperCase();
  const avatar = ch.avatar_url
    ? h("img", { class: "chan-avatar-img", src: ch.avatar_url, alt: ch.name, loading: "lazy" })
    : h("div", { class: "chan-avatar-fallback" }, [initials]);
  return h("div", {
    class: "slide chan-slide",
    title: ch.name,
  }, [
    h("div", { class: "chan-avatar" }, [avatar]),
    h("div", { class: "chan-name" }, [ch.name]),
    ch.niche ? h("div", { class: "chan-niche" }, [ch.niche]) : null,
  ].filter(Boolean));
}

// ── Style marquee ────────────────────────────────────────────────────────────

function renderStyleTrack(styles) {
  const track = document.getElementById("style-track");
  if (!track) return;
  // Only styles with preview images, to keep the slider visual
  const pool = styles.filter((s) => s.preview_image_path || s.uuid);
  if (!pool.length) {
    track.appendChild(h("div", { class: "marquee-empty" }, ["No styles yet — create some in Lab."]));
    return;
  }
  const doubled = [...pool, ...pool];
  for (const s of doubled) track.appendChild(styleSlide(s));
}

function styleSlide(s) {
  // Preview URL: preview_image_path is like "data/custom_styles/<slug>/preview.png"
  // We mounted /data static → strip the leading "data/" and prefix "/data/"
  let previewUrl = "";
  if (s.preview_image_path) {
    const p = s.preview_image_path.replace(/\\/g, "/");
    previewUrl = "/" + p.replace(/^\.?\/?/, "");
    if (!previewUrl.startsWith("/data/")) previewUrl = "/" + p;
  } else if (s.uuid) {
    previewUrl = `/data/custom_styles/${s.uuid}/preview.png`;
  }
  return h("div", {
    class: "slide style-slide",
    title: s.name || "",
  }, [
    h("img", { class: "slide-img", src: previewUrl, alt: s.name || "", loading: "lazy" }),
    h("div", { class: "style-name" }, [s.name || ""]),
  ]);
}
