// Entry point: builds shell (sidebar), registers routes, starts router.

import { api } from "./api.js";
import { h, icons, $ } from "./components.js";
import { register, start } from "./router.js";

import * as homeNew        from "./routes/home_new.js";
import * as home            from "./routes/home.js";
import * as randomChannels  from "./routes/random_channels.js";
import * as trackers        from "./routes/trackers.js";
import * as bookmarks       from "./routes/bookmarks.js";
import * as ideas           from "./routes/ideas.js";
import * as titles          from "./routes/titles.js";
import * as thumbnails      from "./routes/thumbnails.js";

import * as settings        from "./routes/settings.js";
import * as archive         from "./routes/archive.js";
import * as smartFinds      from "./routes/smart_finds.js";
import * as channelsWs      from "./routes/channels_ws.js";
import * as lab             from "./routes/lab.js";
import * as myVideos        from "./routes/my_videos.js";
import * as templates       from "./routes/templates.js";
import * as myStyles        from "./routes/my_styles.js";

register("/home",             homeNew);
register("/outliers",         home);
register("/random-channels",  randomChannels);
register("/trackers",         trackers);
register("/bookmarks",        bookmarks);
register("/ideas",            ideas);
register("/titles",           titles);
register("/thumbnails",       thumbnails);
register("/archive",          archive);
register("/smart-finds",      smartFinds);

register("/my-channels",      channelsWs);
register("/my-videos",        myVideos);
register("/my-styles",        myStyles);
register("/lab",              lab);
register("/templates",        templates);
register("/settings",         settings);

const NAV = [
  { section: "Outliers", items: [
    { path: "/home",            label: "Home",            icon: icons.home   },
    { path: "/outliers",        label: "Random Outliers", icon: icons.random },
    { path: "/random-channels", label: "Random Channels", icon: icons.track  },
    { path: "/trackers",        label: "Channels",        icon: icons.track  },
    { path: "/smart-finds",     label: "Smart Finds",     icon: icons.search },
    { path: "/bookmarks",       label: "Bookmarks",       icon: icons.bookmark },
  ]},
  { section: "Create", items: [
    { path: "/ideas",      label: "Idea Generator",      icon: icons.idea },
    { path: "/titles",     label: "Title Generator",     icon: icons.title },
    { path: "/thumbnails", label: "Thumbnail Generator", icon: icons.thumb },
  ]},
  { section: "My Studio", items: [
    { path: "/my-channels", label: "My Channels", icon: icons.track },
    { path: "/my-videos",   label: "My videos",   icon: icons.film || icons.idea },
    { path: "/my-styles",   label: "My Styles",   icon: icons.sparkle },
    { path: "/templates",   label: "My Templates", icon: icons.title },
    { path: "/lab",         label: "The Lab",     icon: icons.idea },
  ]},
  { section: "Library", items: [
    { path: "/archive",    label: "Archive",             icon: icons.folder || icons.bookmark },
  ]},

];

function buildSidebar() {
  const sidebar = h("aside", { class: "sidebar" }, [
    h("a", { class: "brand", href: "#/home" }, [
      h("img", { class: "brand-logo", src: "/static/img/logo.png", alt: "YTcopilot" }),
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

let _creditsPollId = null;
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
  if (_creditsPollId !== null) clearInterval(_creditsPollId);
  _creditsPollId = setInterval(tick, 5000);
}

init();
