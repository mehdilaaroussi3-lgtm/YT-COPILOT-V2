// Entry point: builds shell (sidebar), registers routes, starts router.

import { api } from "./api.js";
import { h, icons, $ } from "./components.js";
import { register, start } from "./router.js";

import * as home from "./routes/home.js";
import * as trackers from "./routes/trackers.js";
import * as bookmarks from "./routes/bookmarks.js";
import * as ideas from "./routes/ideas.js";
import * as titles from "./routes/titles.js";
import * as thumbnails from "./routes/thumbnails.js";
import * as winners from "./routes/winners.js";
import * as settings from "./routes/settings.js";
import * as archive from "./routes/archive.js";

register("/home",       home);
register("/trackers",   trackers);
register("/bookmarks",  bookmarks);
register("/ideas",      ideas);
register("/titles",     titles);
register("/thumbnails", thumbnails);
register("/archive",    archive);
register("/winners",    winners);
register("/settings",   settings);

const NAV = [
  { section: "Outliers", items: [
    { path: "/home",       label: "Home",       icon: icons.home },
    { path: "/trackers",   label: "Channels",   icon: icons.track },
    { path: "/bookmarks",  label: "Bookmarks",  icon: icons.bookmark },
  ]},
  { section: "Create", items: [
    { path: "/ideas",      label: "Idea Generator",      icon: icons.idea },
    { path: "/titles",     label: "Title Generator",     icon: icons.title },
    { path: "/thumbnails", label: "Thumbnail Generator", icon: icons.thumb },
  ]},
  { section: "Library", items: [
    { path: "/archive",    label: "Archive",             icon: icons.folder || icons.bookmark },
  ]},
  { section: "Analyze", items: [
    { path: "/winners",    label: "Thumbnail Winners",   icon: icons.winner, badge: "Beta" },
  ]},
];

function buildSidebar() {
  const sidebar = h("aside", { class: "sidebar" }, [
    h("a", { class: "brand", href: "#/home" }, [
      h("span", { class: "brand-mark" }, ["YT"]),
      h("span", { class: "brand-text" }, ["YTcopilot"]),
    ]),

    h("div", { class: "credits" }, [
      h("span", { class: "credits-icon", html: icons.sparkle }),
      h("span", { class: "credits-label" }, ["Session"]),
      h("span", { class: "credits-value", id: "credits-value" }, ["0 calls"]),
    ]),

    ...NAV.flatMap((s) => [
      h("div", { class: "nav-section" }, [
        h("div", { class: "nav-section-label" }, [s.section]),
        ...s.items.map((it) =>
          h("a", {
            class: "nav-item",
            href: `#${it.path}`,
            "data-route": it.path,
          }, [
            h("span", { class: "nav-icon", html: it.icon }),
            h("span", {}, [it.label]),
            it.badge && h("span", { class: "nav-badge" }, [it.badge]),
          ].filter(Boolean)),
        ),
      ]),
    ]),

    h("div", { class: "sidebar-spacer" }),

    h("div", { class: "nav-footer" }, [
      h("a", { class: "nav-item", href: "#/settings", "data-route": "/settings" }, [
        h("span", { class: "nav-icon", html: icons.settings }),
        h("span", {}, ["Settings"]),
      ]),
      h("a", { class: "nav-item", href: "https://github.com/anthropics/claude-code", target: "_blank", rel: "noopener" }, [
        h("span", { class: "nav-icon", html: icons.help }),
        h("span", {}, ["Help & resources"]),
      ]),
    ]),

    h("div", { class: "profile" }, [
      h("div", { class: "profile-avatar" }),
      h("div", {}, [
        h("div", { class: "profile-name" }, ["Local User"]),
        h("div", { class: "profile-sub" }, ["Everything unlocked"]),
      ]),
    ]),
  ]);
  return sidebar;
}

function init() {
  const app = document.getElementById("app");
  app.appendChild(buildSidebar());
  app.appendChild(h("main", { class: "content", id: "outlet" }));
  start();
  pollCredits();
}

async function pollCredits() {
  const el = document.getElementById("credits-value");
  const tick = async () => {
    try {
      const s = await api.stats();
      const calls = s.session.total_calls;
      const cost = s.session.estimated_cost_usd;
      el.textContent = `${calls} · $${cost.toFixed(2)}`;
    } catch { /* ignore */ }
  };
  tick();
  setInterval(tick, 5000);
}

init();
