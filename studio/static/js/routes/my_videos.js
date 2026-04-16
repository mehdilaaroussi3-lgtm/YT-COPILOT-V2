// My Videos — production-in-progress sessions

import { api } from "../api.js";
import { h, icons, pageHeader, emptyState } from "../components.js";
import { navigate } from "../router.js";

export async function mount(outlet) {
  const wrap = h("div", { class: "my-videos-wrap" });
  outlet.appendChild(wrap);

  // Inject CSS for my-videos
  (function injectCSS() {
    if (document.getElementById("my-videos-css")) return;
    const style = document.createElement("style");
    style.id = "my-videos-css";
    style.textContent = `
.my-videos-wrap { max-width: 1200px; margin: 0 auto; padding: 0 0 80px; }
.my-videos-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(240px, 1fr)); gap: 16px; margin-top: 32px; }
.my-video-card { background: white; border: 1.5px solid #e5e7eb; border-radius: 12px; overflow: hidden; cursor: pointer; transition: all .15s; }
.my-video-card:hover { border-color: #2d5bff; box-shadow: 0 4px 16px rgba(45,91,255,.12); }
.my-video-thumb { width: 100%; aspect-ratio: 16/9; background: #000; display: flex; align-items: center; justify-content: center; position: relative; overflow: hidden; }
.my-video-thumb img { width: 100%; height: 100%; object-fit: cover; display: block; }
.my-video-thumb-placeholder { font-size: 32px; color: #9ca3af; }
.my-video-meta { padding: 16px; }
.my-video-title { font-size: 14px; font-weight: 700; color: #141414; margin-bottom: 4px; line-height: 1.3; overflow: hidden; text-overflow: ellipsis; display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical; }
.my-video-channel { font-size: 12px; color: #6b7280; margin-bottom: 8px; }
.my-video-footer { display: flex; align-items: center; justify-content: space-between; gap: 8px; }
.my-video-step-badge { font-size: 11px; font-weight: 600; color: white; background: #2d5bff; padding: 4px 10px; border-radius: 99px; text-transform: capitalize; }
.my-video-date { font-size: 11px; color: #9ca3af; }
.empty { text-align: center; padding: 80px 20px; }
.empty-icon { font-size: 60px; margin-bottom: 16px; }
.empty-title { font-size: 22px; font-weight: 700; color: #141414; margin-bottom: 8px; }
.empty-body { font-size: 14px; color: #6b7280; max-width: 400px; margin: 0 auto 24px; }
`;
    document.head.appendChild(style);
  })();

  // Page header
  wrap.appendChild(pageHeader({
    title: "My videos",
    subtitle: "Videos currently in production. Resume from where you left off.",
  }));

  const grid = h("div", { class: "my-videos-grid" });
  wrap.appendChild(grid);

  // Load sessions
  try {
    const r = await api.labSessions();
    const items = r.items || [];

    if (!items.length) {
      grid.parentNode.innerHTML = "";
      grid.parentNode.appendChild(pageHeader({
        title: "My videos",
        subtitle: "Videos currently in production. Resume from where you left off.",
      }));
      grid.parentNode.appendChild(emptyState({
        iconHtml: "🎬",
        title: "No videos in production yet",
        body: "Start your first video in The Lab to see it here.",
        action: h("button", {
          class: "btn primary",
          onclick: () => navigate("/lab"),
        }, ["Go to The Lab"]),
      }));
      return;
    }

    // Render cards
    items.forEach((session) => {
      const card = h("div", { class: "my-video-card", onclick: () => {
        navigate("/lab", { resumeSessionId: session.id });
      } }, [
        h("div", { class: "my-video-thumb" }, [
          renderThumbnail(session.url),
        ]),
        h("div", { class: "my-video-meta" }, [
          h("div", { class: "my-video-title" }, [session.yt_title || "Untitled video"]),
          h("div", { class: "my-video-channel" }, [session.yt_channel || "Unknown channel"]),
          h("div", { class: "my-video-footer" }, [
            h("span", { class: "my-video-step-badge" }, [formatStep(session.step)]),
            h("span", { class: "my-video-date" }, [formatDate(session.created_at)]),
          ]),
        ]),
      ]);
      grid.appendChild(card);
    });
  } catch (err) {
    console.error("Failed to load sessions:", err);
    grid.parentNode.innerHTML = "";
    grid.parentNode.appendChild(pageHeader({
      title: "My videos",
      subtitle: "Videos currently in production. Resume from where you left off.",
    }));
    grid.parentNode.appendChild(emptyState({
      iconHtml: "⚠️",
      title: "Error loading videos",
      body: "Something went wrong. Please try again.",
    }));
  }

  return function unmount() {
    // cleanup
  };
}

function renderThumbnail(youtubeUrl) {
  try {
    const videoId = extractYoutubeId(youtubeUrl);
    if (videoId) {
      return h("img", {
        src: `https://img.youtube.com/vi/${videoId}/mqdefault.jpg`,
        alt: "Video thumbnail",
        loading: "lazy",
      });
    }
  } catch (e) {
    // Fall through to placeholder
  }
  return h("div", { class: "my-video-thumb-placeholder" }, ["🎥"]);
}

function extractYoutubeId(url) {
  if (!url) return null;
  // Handle youtube.com/watch?v=ID
  const match = url.match(/[?&]v=([^&]+)/);
  if (match) return match[1];
  // Handle youtu.be/ID
  const match2 = url.match(/youtu\.be\/([^?&]+)/);
  if (match2) return match2[1];
  return null;
}

function formatStep(step) {
  if (!step) return "—";
  return step
    .replace(/_/g, " ")
    .replace(/\b\w/g, (c) => c.toUpperCase())
    .replace(/Done$/, "Done")
    .replace(/Generating$/, "Generating");
}

function formatDate(isoDate) {
  if (!isoDate) return "—";
  const date = new Date(isoDate);
  const now = new Date();
  const diff = now - date;
  const days = Math.floor(diff / (1000 * 60 * 60 * 24));
  if (days === 0) return "Today";
  if (days === 1) return "Yesterday";
  if (days < 7) return `${days}d ago`;
  if (days < 30) return `${Math.floor(days / 7)}w ago`;
  return `${Math.floor(days / 30)}m ago`;
}
