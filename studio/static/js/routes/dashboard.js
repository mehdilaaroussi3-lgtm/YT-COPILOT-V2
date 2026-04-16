// Dashboard — Library intelligence: score tiers, niche coverage, style tags, top channels.

import { api } from "../api.js";
import { h, icons, emptyState, pageHeader, formatRelative } from "../components.js";
import { navigate } from "../router.js";

function daysSince(isoString) {
  if (!isoString) return null;
  return Math.max(0, Math.floor((Date.now() - new Date(isoString).getTime()) / 86_400_000));
}

export async function mount(outlet) {
  outlet.appendChild(pageHeader({
    kicker: "Analytics",
    title: "Dashboard",
    subtitle: "Understand what's in your outlier index.",
  }));

  // ── Placeholders (filled after data loads) ──────────────────────────────────
  const tiersRow    = h("div", { class: "dashboard-tiers-row" });
  const nicheSection = h("div", { class: "dashboard-section" });
  const tagsSection  = h("div", { class: "dashboard-section" });
  const topChSection = h("div", { class: "dashboard-section" });

  outlet.appendChild(tiersRow);
  outlet.appendChild(nicheSection);
  outlet.appendChild(tagsSection);
  outlet.appendChild(topChSection);

  // ── Load all in parallel ────────────────────────────────────────────────────
  const [tiersRes, nicheRes, tagsRes] = await Promise.all([
    api.outliersStats().catch(() => null),
    api.outliersNicheStats().catch(() => ({ items: [] })),
    api.outliersStyleTags(15).catch(() => ({ tags: [] })),
  ]);

  // ── Score Tier Cards ────────────────────────────────────────────────────────
  const tiers = [
    { label: "Legendary", sublabel: "≥10x", key: "tier_10x", accent: "var(--c-gold, #f5a623)",   emoji: "🔥" },
    { label: "Elite",     sublabel: "5x–10x", key: "tier_5x",  accent: "var(--c-accent, #7c3aed)", emoji: "⚡" },
    { label: "Strong",    sublabel: "3x–5x",  key: "tier_3x",  accent: "var(--c-blue,  #2563eb)",  emoji: "✓" },
    { label: "Base",      sublabel: "2x–3x",  key: "tier_2x",  accent: "var(--c-muted, #6b7280)",  emoji: "○" },
  ];

  // Convert cumulative counts into tier-specific counts
  const t = tiersRes || {};
  const tierCounts = {
    tier_10x: t.tier_10x || 0,
    tier_5x:  Math.max(0, (t.tier_5x || 0)  - (t.tier_10x || 0)),
    tier_3x:  Math.max(0, (t.tier_3x || 0)  - (t.tier_5x  || 0)),
    tier_2x:  Math.max(0, (t.tier_2x || 0)  - (t.tier_3x  || 0)),
  };

  for (const tier of tiers) {
    const count = tierCounts[tier.key] ?? 0;
    tiersRow.appendChild(
      h("div", { class: "dashboard-tier-card card sm" }, [
        h("div", { class: "tier-emoji" }, [tier.emoji]),
        h("div", { class: "tier-count" }, [count.toLocaleString()]),
        h("div", { class: "tier-label" }, [tier.label]),
        h("div", { class: "tier-sub" }, [tier.sublabel + " outlier score"]),
      ]),
    );
  }

  // ── Niche Coverage Table ────────────────────────────────────────────────────
  const niches = (nicheRes && nicheRes.items) || [];

  nicheSection.appendChild(
    h("div", { class: "dashboard-section-header" }, ["Niche Coverage"]),
  );

  if (niches.length) {
    const tbody = h("tbody", {});
    for (const row of niches) {
      const stale = daysSince(row.last_scanned);
      const staleEl = stale !== null && stale > 14
        ? h("span", { class: "pill stale", title: `Last scanned ${stale}d ago` }, ["Stale"])
        : null;

      tbody.appendChild(
        h("tr", {
          class: "clickable-row",
          onclick: () => navigate(`/outliers?niche=${encodeURIComponent(row.niche)}`),
          title: `Browse ${row.niche} outliers`,
        }, [
          h("td", {}, [
            h("span", { class: "channel-group-niche" }, [row.niche]),
            staleEl,
          ].filter(Boolean)),
          h("td", {}, [row.channel_count]),
          h("td", {}, [row.video_count]),
          h("td", {}, [row.avg_score ? row.avg_score.toFixed(2) + "x" : "—"]),
          h("td", {}, [row.last_scanned ? formatRelative(row.last_scanned) : "Never"]),
        ]),
      );
    }

    nicheSection.appendChild(
      h("div", { class: "table-wrap" }, [
        h("table", { class: "data-table" }, [
          h("thead", {}, [
            h("tr", {}, [
              h("th", {}, ["Niche"]),
              h("th", {}, ["Channels"]),
              h("th", {}, ["Videos"]),
              h("th", {}, ["Avg Score"]),
              h("th", {}, ["Last Scanned"]),
            ]),
          ]),
          tbody,
        ]),
      ]),
    );
  } else {
    nicheSection.appendChild(
      emptyState({ iconHtml: icons.idea, title: "No niche data yet", body: "Run a scan to populate." }),
    );
  }

  // ── Style Tag Cloud ─────────────────────────────────────────────────────────
  const tags = (tagsRes && tagsRes.tags) || [];

  tagsSection.appendChild(
    h("div", { class: "dashboard-section-header" }, ["Visual Style Tags"]),
  );
  tagsSection.appendChild(
    h("div", { class: "dashboard-section-sub" }, [
      "Most frequent visual styles across all indexed thumbnails.",
    ]),
  );

  if (tags.length) {
    const maxCount = tags[0].count || 1;
    const cloud = h("div", { class: "style-tag-cloud" });
    for (const t of tags) {
      const size = 0.75 + (t.count / maxCount) * 0.75; // 0.75rem – 1.5rem
      cloud.appendChild(
        h("span", {
          class: "style-tag-pill",
          style: { fontSize: `${size.toFixed(2)}rem` },
          title: `${t.count} thumbnails`,
        }, [`${t.tag} (${t.count})`]),
      );
    }
    tagsSection.appendChild(cloud);
  } else {
    tagsSection.appendChild(
      emptyState({
        iconHtml: icons.eye,
        title: "No style tags yet",
        body: "Run thumbnail analysis (Gemini Vision) to generate tags.",
      }),
    );
  }

  // ── Top Channels by Outlier Count ──────────────────────────────────────────
  topChSection.appendChild(
    h("div", { class: "dashboard-section-header" }, ["Top Channels by Outlier Count"]),
  );

  // Build per-channel aggregates from niche stats by re-using outlier data
  // We fetch channels-random with a large limit to get counts for a leaderboard
  try {
    const chRes = await api.channelsRandom(100);
    const chItems = (chRes.items || [])
      .filter((c) => c.outlier_count > 0)
      .sort((a, b) => b.outlier_count - a.outlier_count)
      .slice(0, 10);

    if (chItems.length) {
      const tbody2 = h("tbody", {});
      chItems.forEach((ch, i) => {
        tbody2.appendChild(
          h("tr", {
            class: "clickable-row",
            onclick: () => navigate(`/outliers?channel_id=${ch.channel_id}`),
            title: `Browse ${ch.name} outliers`,
          }, [
            h("td", { class: "rank-cell" }, [`#${i + 1}`]),
            h("td", {}, [
              h("div", { class: "ch-name-cell" }, [
                ch.name,
                ch.niche ? h("span", { class: "channel-group-niche" }, [ch.niche]) : null,
              ].filter(Boolean)),
            ]),
            h("td", {}, [ch.outlier_count]),
            h("td", {}, [ch.top_score ? `${ch.top_score.toFixed(1)}x` : "—"]),
          ]),
        );
      });

      topChSection.appendChild(
        h("div", { class: "table-wrap" }, [
          h("table", { class: "data-table" }, [
            h("thead", {}, [
              h("tr", {}, [
                h("th", {}, ["Rank"]),
                h("th", {}, ["Channel"]),
                h("th", {}, ["Outliers"]),
                h("th", {}, ["Peak Score"]),
              ]),
            ]),
            tbody2,
          ]),
        ]),
      );
    } else {
      topChSection.appendChild(
        emptyState({ iconHtml: icons.track, title: "No channel data yet", body: "Scan channels to build the leaderboard." }),
      );
    }
  } catch {
    topChSection.appendChild(
      emptyState({ iconHtml: icons.track, title: "Could not load channel data", body: "" }),
    );
  }
}
