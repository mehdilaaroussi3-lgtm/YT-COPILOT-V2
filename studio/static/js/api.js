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
  outliersRecent: (limit = 7, minScore = 2.0) =>
    request(`/api/outliers/recent?limit=${limit}&min_score=${minScore}`),
  outliersPremium: (limit = 10, faceless = 1) =>
    request(`/api/outliers/premium?limit=${limit}&faceless=${faceless}`),
  latestCreations: (limit = 4) =>
    request(`/api/home/latest-creations?limit=${limit}`),
  stylesList: () => request("/api/styles"),
  outliersStats: () => request("/api/outliers/stats"),
  outliersNicheStats: () => request("/api/outliers/niche-stats"),
  outliersStyleTags: () => request("/api/outliers/style-tags"),
  outliersNiches: () => request("/api/outliers/niches"),
  channelsRandom: (limit = 30, niche) => {
    const params = new URLSearchParams({ limit });
    if (niche) params.set("niche", niche);
    return request(`/api/outliers/channels-random?${params}`);
  },
  outliersByChannels: (ids, limit = 200) =>
    request(`/api/outliers/by-channels?ids=${ids.join(",")}&limit=${limit}`),
  smartFinds: () => request("/api/outliers/smart-finds"),

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

  // lab
  labSessions: () => request("/api/lab/sessions"),
  labSession: (sid) => request(`/api/lab/sessions/${sid}`),
  labReverse: (url) =>
    request("/api/lab", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ url }),
    }),
  labReverseStatus: (sid) => request(`/api/lab/${sid}/reverse/status`),
  labIdeas: (sid) =>
    request(`/api/lab/${sid}/ideas`, { method: "POST" }),
  labIdeasStatus: (sid) => request(`/api/lab/${sid}/ideas/status`),
  labVoices: () => request("/api/lab/voices"),
  labVoice: (sid, voiceId) =>
    request(`/api/lab/${sid}/voice`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ voice_id: voiceId }),
    }),
  elevenlabsVoices: () => request("/api/lab/voices"),
  labScript: (sid, sectionId) => request(`/api/lab/${sid}/section/${sectionId}/script`),
  labGetScript: (sid, sectionId) => request(`/api/lab/${sid}/section/${sectionId}/script`),
  labScriptStatus: (sid, sectionId) => request(`/api/lab/${sid}/section/${sectionId}/script/status`),
  labApproveScript: (sid, sectionId) =>
    request(`/api/lab/${sid}/section/${sectionId}/script/approve`, { method: "POST" }),
  labVoiceover: (sid, sectionId, voiceId) =>
    request(`/api/lab/${sid}/section/${sectionId}/voiceover`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ voice_id: voiceId }),
    }),
  labVoiceoverStatus: (sid, sectionId) => request(`/api/lab/${sid}/section/${sectionId}/voiceover/status`),
  labGenerateSectionImages: (sid, sectionId) =>
    request(`/api/lab/${sid}/section/${sectionId}/images`, { method: "POST" }),
  labSectionImagesStatus: (sid, sectionId) => request(`/api/lab/${sid}/section/${sectionId}/images/status`),
  labProduceSection: (sid, sectionId) =>
    request(`/api/lab/${sid}/section/${sectionId}/produce`, { method: "POST" }),
  labSectionStatus: (sid, sectionId) => request(`/api/lab/${sid}/section/${sectionId}/status`),
  labSections: (sid) => request(`/api/lab/${sid}/sections`),
  labAssemble: (sid) =>
    request(`/api/lab/${sid}/assemble`, { method: "POST" }),
  labAssembleStatus: (sid) => request(`/api/lab/${sid}/assemble/status`),
  labThumbnail: (sid) => request(`/api/lab/${sid}/thumbnail`),
  labThumbnailStatus: (sid) => request(`/api/lab/${sid}/thumbnail/status`),
  labIdeaSelect: (sid, ideaIndex) =>
    request(`/api/lab/${sid}/idea/${ideaIndex}`, { method: "POST" }),
  labCancel: (sid) =>
    request(`/api/lab/${sid}`, { method: "DELETE" }),
  labDeleteSession: (sid) =>
    request(`/api/lab/${sid}`, { method: "DELETE" }),

  // my channels
  myChannels: () => request("/api/my-channels"),
  myChannelCreate: (name, channelId) =>
    request("/api/my-channels", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ name, channel_id: channelId }),
    }),
  myChannelUpdate: (name, data) =>
    request(`/api/my-channels/${encodeURIComponent(name)}`, {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(data),
    }),
  myChannelDelete: (name) =>
    request(`/api/my-channels/${encodeURIComponent(name)}`, { method: "DELETE" }),
  myChannelVideos: (name) =>
    request(`/api/my-channels/${encodeURIComponent(name)}/videos`),
  myChannelVideoCreate: (name, videoId, title) =>
    request(`/api/my-channels/${encodeURIComponent(name)}/videos`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ video_id: videoId, title }),
    }),
  myChannelVideoUpdate: (name, videoId, data) =>
    request(`/api/my-channels/${encodeURIComponent(name)}/videos/${videoId}`, {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(data),
    }),
  myChannelVideoDelete: (name, videoId) =>
    request(`/api/my-channels/${encodeURIComponent(name)}/videos/${videoId}`, { method: "DELETE" }),
  myChannelScan: (name) =>
    request(`/api/my-channels/${encodeURIComponent(name)}/scan`, { method: "POST" }),
  myChannelScanStatus: (name) =>
    request(`/api/my-channels/${encodeURIComponent(name)}/scan/status`),
  myChannelScanAbort: (name) =>
    request(`/api/my-channels/${encodeURIComponent(name)}/scan/abort`, { method: "POST" }),
  myChannelDnaSummary: (name) =>
    request(`/api/my-channels/${encodeURIComponent(name)}/dna-summary`),
  myChannelIdeas: (name, count) =>
    request(`/api/my-channels/${encodeURIComponent(name)}/ideas`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ count: count || 6 }),
    }),
  myChannelIdeasStatus: (name, jobId) =>
    request(`/api/my-channels/${encodeURIComponent(name)}/ideas/status/${jobId}`),
  myChannelVideoTitles: (name, videoId) =>
    request(`/api/my-channels/${encodeURIComponent(name)}/videos/${videoId}/titles`, {
      method: "POST",
    }),
  myChannelVideoTitlesStatus: (name, videoId) =>
    request(`/api/my-channels/${encodeURIComponent(name)}/videos/${videoId}/titles/status`),
  myChannelVideoScript: (name, videoId) =>
    request(`/api/my-channels/${encodeURIComponent(name)}/videos/${videoId}/script`, { method: "POST" }),
  myChannelVideoScriptGet: (name, videoId) =>
    request(`/api/my-channels/${encodeURIComponent(name)}/videos/${videoId}/script`),
  myChannelVideoScriptSave: (name, videoId, scriptJson) =>
    request(`/api/my-channels/${encodeURIComponent(name)}/videos/${videoId}/script`, {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ script_json: scriptJson }),
    }),
  myChannelVideoScriptApprove: (name, videoId) =>
    request(`/api/my-channels/${encodeURIComponent(name)}/videos/${videoId}/script/approve`, { method: "POST" }),
  myChannelVideoScriptStatus: (name, videoId) =>
    request(`/api/my-channels/${encodeURIComponent(name)}/videos/${videoId}/script/status`),
  myChannelProduceSection: (name, videoId, sid) =>
    request(`/api/my-channels/${encodeURIComponent(name)}/videos/${videoId}/produce/section/${sid}`, { method: "POST" }),
  myChannelProduceSectionStatus: (name, videoId, sid) =>
    request(`/api/my-channels/${encodeURIComponent(name)}/videos/${videoId}/produce/section/${sid}/status`),
  myChannelProduceSectionRedo: (name, videoId, sid) =>
    request(`/api/my-channels/${encodeURIComponent(name)}/videos/${videoId}/produce/section/${sid}/redo`, { method: "POST" }),
  myChannelProduceSectionApprove: (name, videoId, sid) =>
    request(`/api/my-channels/${encodeURIComponent(name)}/videos/${videoId}/produce/section/${sid}/approve`, { method: "POST" }),
  myChannelProduceSections: (name, videoId) =>
    request(`/api/my-channels/${encodeURIComponent(name)}/videos/${videoId}/produce/sections`),
  myChannelProduceFinal: (name, videoId) =>
    request(`/api/my-channels/${encodeURIComponent(name)}/videos/${videoId}/produce/final`, { method: "POST" }),
  myChannelProduceFinalStatus: (name, videoId) =>
    request(`/api/my-channels/${encodeURIComponent(name)}/videos/${videoId}/produce/final/status`),
  myChannelLogoStatus: (name) =>
    request(`/api/my-channels/${encodeURIComponent(name)}/logo-status`),

  // templates
  templates: () => request("/api/templates"),
  templateCreate: (name, description) =>
    request("/api/templates", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ name, description: description || "" }),
    }),
  templateDetail: (id) => request(`/api/templates/${id}`),
  templateAnalyze: (id) =>
    request(`/api/templates/${id}/analyze`, { method: "POST" }),
  templateStatus: (id) => request(`/api/templates/${id}/status`),
  templateDelete: (id) => request(`/api/templates/${id}`, { method: "DELETE" }),
  templateDna: (id) => request(`/api/templates/${id}/dna`),
  labFromTemplate: (templateId, topic, voiceId) =>
    request("/api/lab/from-template", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        template_id: templateId,
        topic: topic || "",
        voice_id: voiceId || "",
      }),
    }),

  // styles — custom user styles
  stylesCustom: () => request("/api/styles/custom"),
  styleGeneratePreview: (uuid) =>
    request(`/api/styles/${uuid}/preview`, { method: "POST" }),
  stylePreviewStatus: (uuid, jobId) =>
    request(`/api/styles/${uuid}/preview/status?job_id=${jobId}`),
  stylePreviewImageUrl: (uuid) => `/api/styles/${uuid}/preview/image`,
  styleRefImageUrl: (uuid, n) => `/api/styles/${uuid}/ref/${n}`,
  styleGeneratePrompt: (uuid, topic) =>
    request(`/api/styles/${uuid}/generate-prompt`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ topic }),
    }),
  styleDelete: (uuid) => request(`/api/styles/${uuid}`, { method: "DELETE" }),
  labSetStyle: (sessionId, styleId) =>
    request("/api/lab/style", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ session_id: sessionId, style_id: styleId }),
    }),
};
