// Settings — read-only config + stats.

import { api } from "../api.js";
import { h, icons, pageHeader, toast } from "../components.js";

export async function mount(outlet) {
  outlet.appendChild(pageHeader({
    kicker: "Config",
    title: "Settings",
    subtitle: "Read-only view of your ThumbCraft configuration. Edit config.yml at the repo root to change keys and model choices.",
  }));

  const [settings, stats] = await Promise.all([api.settings(), api.stats()]);

  outlet.appendChild(sectionModels(settings));
  outlet.appendChild(sectionKeys(settings));
  outlet.appendChild(sectionStats(stats));
  outlet.appendChild(sectionPaths(settings));
}

function section(title, rows, right) {
  return h("div", { class: "card", style: { marginBottom: "24px" } }, [
    h("div", { class: "flex between center", style: { marginBottom: "16px" } }, [
      h("div", { class: "display-s" }, [title]),
      right,
    ].filter(Boolean)),
    h("div", { style: { display: "grid", gridTemplateColumns: "1fr 2fr", gap: "12px 24px" } },
      rows.flatMap(([k, v]) => [
        h("div", { class: "eyebrow" }, [k]),
        h("div", { class: "mono", style: { wordBreak: "break-all" } }, [v || "—"]),
      ]),
    ),
  ]);
}

function sectionModels(s) {
  return section("Models", [
    ["Image model", s.models.image],
    ["Vision model", s.models.vision],
    ["Image size", s.models.image_size],
    ["Aspect ratio", s.models.aspect_ratio],
  ]);
}

function sectionKeys(s) {
  return section("API Keys", [
    ["Vertex", s.keys.vertex_masked],
    ["YouTube Data v3", s.keys.youtube_masked],
  ]);
}

function sectionStats(s) {
  const c = s.session.calls;
  const cost = s.session.estimated_cost_usd;
  return section("This session", [
    ["Image generations", `${c.image}  ·  ~$${(c.image * 0.134).toFixed(3)}`],
    ["Vision calls", `${c.vision}  ·  ~$${(c.vision * 0.005).toFixed(3)}`],
    ["Text calls", `${c.text}  ·  ~$${(c.text * 0.003).toFixed(3)}`],
    ["Estimated total", `$${cost.toFixed(3)}  (${s.session.total_calls} calls)`],
    ["Cache size", `${s.disk.cache_mb} MB`],
    ["Output size", `${s.disk.output_mb} MB`],
    ...Object.entries(s.db_rows).map(([k, v]) => [`DB · ${k}`, String(v)]),
  ]);
}

function sectionPaths(s) {
  return section("Paths", [
    ["Output", s.paths.output_dir],
    ["Cache", s.paths.cache_dir],
  ], h("button", {
    class: "btn sm",
    html: `${icons.folder}<span>Open output folder</span>`,
    onclick: async () => {
      const r = await api.openOutput();
      if (r.ok) toast("Opened in file explorer", { kind: "success" });
      else toast(r.error || "Failed to open", { kind: "error" });
    },
  }));
}
