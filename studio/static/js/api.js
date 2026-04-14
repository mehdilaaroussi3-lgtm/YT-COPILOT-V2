// Typed fetch wrapper. All backend calls go through here.

async function request(url, opts = {}) {
  const res = await fetch(url, opts);
  if (!res.ok) {
    const text = await res.text().catch(() => "");
    throw new Error(`HTTP ${res.status} ${url}: ${text.slice(0, 200)}`);
  }
  const ct = res.headers.get("content-type") || "";
  if (ct.includes("application/json")) return res.json();
  return res.text();
}

export const api = {
  // core
  health:   () => request("/api/health"),
  stats:    () => request("/api/stats"),
  channels: () => request("/api/channels"),
  niches:   () => request("/api/niches"),
  hook:     (title, channel) => {
    const params = new URLSearchParams({ title });
    if (channel) params.set("channel", channel);
    return request(`/api/hook?${params}`);
  },
  settings: () => request("/api/settings"),
  openOutput: () => request("/api/settings/open-output", { method: "POST" }),

  // outliers
  outliersRandom: (limit = 12, minScore = 2) =>
    request(`/api/outliers/random?limit=${limit}&min_score=${minScore}`),
  outliersSearch: (q, niche, channelId) => {
    const params = new URLSearchParams();
    if (q) params.set("q", q);
    if (niche) params.set("niche", niche);
    if (channelId) params.set("channel_id", channelId);
    return request(`/api/outliers/search?${params}`);
  },
  outlierDetail: (videoId) => request(`/api/outliers/${videoId}`),

  // trackers
  trackers: () => request("/api/trackers"),
  trackerAdd: (handle, niche) =>
    request("/api/trackers", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ handle, niche_override: niche || "" }),
    }),
  trackerRemove: (channelId) =>
    request(`/api/trackers/${channelId}`, { method: "DELETE" }),
  trackerRefresh: (channelId) =>
    request(`/api/trackers/${channelId}/refresh`, { method: "POST" }),
  trackerSetDefault: (channelId) =>
    request(`/api/trackers/${channelId}/default`, { method: "PATCH" }),
  trackerResummarize: (channelId) =>
    request(`/api/trackers/${channelId}/resummarize`, { method: "POST" }),

  styleChannels: () => request("/api/style-channels"),

  // folders + bookmarks
  folders: () => request("/api/folders"),
  folderCreate: (name, color) =>
    request("/api/folders", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ name, color }),
    }),
  folderDelete: (id) => request(`/api/folders/${id}`, { method: "DELETE" }),
  folderRename: (id, name) =>
    request(`/api/folders/${id}`, {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ name }),
    }),
  bookmarks: (folderId) => request(`/api/bookmarks?folder_id=${folderId}`),
  bookmarkAdd: (payload) =>
    request("/api/bookmarks", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    }),
  bookmarkRemove: (id) => request(`/api/bookmarks/${id}`, { method: "DELETE" }),

  // ideas
  ideasGenerate: (channel, topic, count = 6) =>
    request("/api/ideas", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ channel, topic, count }),
    }),
  ideasStatus: (jobId) => request(`/api/ideas/status/${jobId}`),
  ideasHistory: (channel) => {
    const q = channel ? `?channel=${encodeURIComponent(channel)}` : "";
    return request(`/api/ideas/history${q}`);
  },

  // titles
  titlesGenerate: (channel, idea, count = 6) =>
    request("/api/titles", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ channel, idea, count }),
    }),
  titlesStatus: (jobId) => request(`/api/titles/status/${jobId}`),
  titlesHistory: (channel) => {
    const q = channel ? `?channel=${encodeURIComponent(channel)}` : "";
    return request(`/api/titles/history${q}`);
  },
  titlePin: (id) => request(`/api/titles/${id}/pin`, { method: "POST" }),

  // thumbnails
  generate: (formData) =>
    fetch("/api/generate", { method: "POST", body: formData }).then((r) => r.json()),
  refine: (formData) =>
    fetch("/api/refine", { method: "POST", body: formData }).then((r) => r.json()),
  thumbnailsHistory: (channel) => {
    const q = channel ? `?channel=${encodeURIComponent(channel)}` : "";
    return request(`/api/thumbnails/history${q}`);
  },

  // winners
  winners: (niche) => {
    const q = niche ? `?niche=${encodeURIComponent(niche)}` : "";
    return request(`/api/winners${q}`);
  },
  winnersSimilar: (videoId) => request(`/api/winners/similar/${videoId}`),
};
