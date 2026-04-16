// The Lab — reverse-engineer a YouTube video and reproduce its formula for your topic.

import { api } from "../api.js";
import { h, icons, toast, $, channelPicker } from "../components.js";

// ── Step definitions ──────────────────────────────────────────────────────────
const STEPS = [
  { id: "reverse",   label: "Reverse"   },
  { id: "ideas",     label: "Ideas"     },
  { id: "voice",     label: "Voice"     },
  { id: "script",    label: "Script"    },
  { id: "voiceover", label: "Voiceover" },
  { id: "visuals",   label: "Visuals"   },
  { id: "assembly",  label: "Assembly"  },
  { id: "thumbnail", label: "Thumbnail" },
];
const STEP_IDS = STEPS.map((s) => s.id);

function sessionToUIStep(sessionStep) {
  const map = {
    reverse_done:       "ideas",
    idea_done:          "voice",
    voice_done:         "script",
    script_generating:  "script",
    script_done:        "script",
    script_approved:    "voiceover",
    voiceover_done:     "visuals",
    visuals_done:       "assembly",
    assembled:          "assembly",
    done:               "thumbnail",
  };
  return map[sessionStep] || "reverse";
}

// ── Inject Lab CSS once ───────────────────────────────────────────────────────
(function injectCSS() {
  if (document.getElementById("lab-css")) return;
  const style = document.createElement("style");
  style.id = "lab-css";
  style.textContent = `
.lab-wrap { max-width: 1140px; margin: 0 auto; padding: 0 0 80px; }
.lab-page-header { text-align: center; padding: 20px 0 40px; }
.lab-page-title { font-size: 52px; font-weight: 800; letter-spacing: -0.03em; color: var(--accent, #2d5bff); line-height: 1.05; margin-bottom: 14px; display: block; }
.lab-page-sub { font-size: 15px; color: var(--ink-500,#6b7280); line-height: 1.7; max-width: 52ch; margin: 0 auto; }

/* Module card — the whole Lab lives inside this */
.lab-module {
  background: var(--surface);
  border: 1px solid var(--line);
  border-radius: var(--r-5);
  box-shadow: var(--shadow-2);
  overflow: hidden;
  margin-bottom: 40px;
}

/* Tab strip at the top of the card */
.lab-step-bar {
  display: flex; align-items: flex-end; gap: 0;
  background: var(--surface-2);
  border-bottom: 1px solid var(--line);
  padding: 0;
}
.lab-step-pill { flex: 1; display: flex; align-items: center; justify-content: center; gap: 10px; padding: 22px 8px; font-size: 14px; font-weight: 500; color: var(--ink-400,#9ca3af); cursor: default; white-space: nowrap; border: none; background: none; border-bottom: 3px solid transparent; margin-bottom: -1px; transition: color .15s, border-color .15s, background .15s; }
.lab-step-pill.active { background: var(--surface); color: var(--ink-900,#141414); font-weight: 700; border-bottom-color: var(--accent,#2d5bff); }
.lab-step-pill.done { color: var(--ink-500,#6b7280); cursor: pointer; }
.lab-step-pill.done:hover { color: var(--ink-700,#374151); background: var(--surface-3); }
.lab-step-pill .pill-num { width: 26px; height: 26px; border-radius: 50%; background: var(--line); display: flex; align-items: center; justify-content: center; font-size: 12px; font-weight: 700; flex-shrink: 0; color: var(--ink-400); }
.lab-step-pill.active .pill-num { background: var(--accent,#2d5bff); color: white; }
.lab-step-pill.done .pill-num { background: #22c55e; color: white; }
.lab-step-sep { display: none; }

/* Content area inside the card */
.lab-content { padding: 48px; }

.lab-panel { animation: labFadeIn .22s ease; }
@keyframes labFadeIn { from { opacity:0; transform:translateY(5px); } to { opacity:1; transform:translateY(0); } }

.lab-hero-instruction { font-size: 15px; color: var(--ink-500,#6b7280); margin-bottom: 32px; line-height: 1.7; max-width: 68ch; }
.lab-url-row { display: flex; gap: 12px; }
.lab-url-input { flex: 1; padding: 16px 20px; border: 1.5px solid var(--line,#e5e7eb); border-radius: 12px; font-size: 15px; outline: none; transition: border-color .15s; background: var(--surface); }
.lab-url-input:focus { border-color: var(--accent,#2d5bff); }

.lab-progress-panel { margin-top: 20px; background: var(--surface-2,#f6f7f9); border-radius: 12px; padding: 20px; }
.lab-stage-item { display: flex; align-items: center; gap: 10px; padding: 6px 0; font-size: 13px; color: var(--ink-500,#6b7280); }
.lab-stage-item.done { color: var(--ink-700,#374151); }
.lab-stage-item .stage-icon { width: 18px; text-align: center; flex-shrink: 0; }

.lab-summary-card { background: white; border: 1.5px solid var(--line,#e5e7eb); border-radius: 14px; padding: 24px; margin-top: 24px; }
.lab-summary-title { font-size: 18px; font-weight: 700; color: var(--ink-700,#374151); margin-bottom: 4px; }
.lab-summary-channel { font-size: 13px; color: var(--ink-400,#9ca3af); margin-bottom: 20px; }
.lab-summary-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 16px; margin-bottom: 20px; }
.lab-summary-item { background: var(--surface-2,#f6f7f9); border-radius: 10px; padding: 14px; }
.lab-summary-label { font-size: 11px; font-weight: 600; text-transform: uppercase; letter-spacing: .06em; color: var(--ink-400,#9ca3af); margin-bottom: 5px; }
.lab-summary-value { font-size: 13px; color: var(--ink-700,#374151); line-height: 1.5; }
.lab-tags { display: flex; flex-wrap: wrap; gap: 6px; margin-top: 12px; }
.lab-tag { font-size: 12px; padding: 3px 10px; background: var(--accent-soft,#eef2ff); color: var(--accent,#6366f1); border-radius: 99px; }
.lab-must-keep { margin-top: 16px; }
.lab-must-item { display: flex; align-items: flex-start; gap: 8px; font-size: 13px; color: var(--ink-600,#4b5563); margin-bottom: 6px; }
.lab-must-item::before { content:"→"; color: var(--accent,#6366f1); flex-shrink:0; }

.lab-topic-area { margin-bottom: 20px; }
.lab-topic-divider { display: flex; align-items: center; gap: 12px; margin: 20px 0; color: var(--ink-400,#9ca3af); font-size: 13px; }
.lab-topic-divider::before,.lab-topic-divider::after { content:""; flex:1; height:1px; background:var(--line,#e5e7eb); }
.lab-ideas-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 12px; margin-top: 16px; }
.lab-idea-card { background: white; border: 1.5px solid var(--line,#e5e7eb); border-radius: 12px; padding: 16px; cursor: pointer; transition: border-color .15s, box-shadow .15s; }
.lab-idea-card:hover { border-color: var(--accent,#6366f1); box-shadow: 0 0 0 3px var(--accent-soft,#eef2ff); }
.lab-idea-card.selected { border-color: var(--accent,#6366f1); background: var(--accent-soft,#eef2ff); }
.lab-idea-title { font-size: 14px; font-weight: 600; color: var(--ink-700,#374151); margin-bottom: 6px; }
.lab-idea-desc { font-size: 12px; color: var(--ink-500,#6b7280); line-height: 1.5; margin-bottom: 8px; }
.lab-idea-angle { font-size: 11px; color: var(--accent,#6366f1); font-weight: 500; }

.lab-voice-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(220px, 1fr)); gap: 12px; margin-bottom: 24px; }
.lab-voice-card { background: white; border: 1.5px solid var(--line,#e5e7eb); border-radius: 12px; padding: 16px; cursor: pointer; transition: border-color .15s, box-shadow .15s; }
.lab-voice-card:hover { border-color: var(--accent,#6366f1); }
.lab-voice-card.selected { border-color: var(--accent,#6366f1); background: var(--accent-soft,#eef2ff); }
.lab-voice-name { font-size: 15px; font-weight: 700; color: var(--ink-700,#374151); margin-bottom: 4px; }
.lab-voice-meta { font-size: 12px; color: var(--ink-400,#9ca3af); }
.lab-voice-style { font-size: 12px; color: var(--ink-600,#4b5563); margin-top: 6px; }

.lab-duration-row { display: flex; gap: 8px; margin-bottom: 24px; }
.lab-dur-btn { padding: 8px 18px; border-radius: 99px; border: 1.5px solid var(--line,#e5e7eb); font-size: 13px; font-weight: 500; cursor: pointer; background: white; color: var(--ink-600,#4b5563); transition: all .15s; }
.lab-dur-btn.active { border-color: var(--accent,#6366f1); background: var(--accent-soft,#eef2ff); color: var(--accent,#6366f1); }

.lab-script-view { display: flex; flex-direction: column; gap: 16px; }
.lab-script-section { background: white; border: 1.5px solid var(--line,#e5e7eb); border-radius: 12px; overflow: hidden; }
.lab-section-header { display: flex; align-items: center; justify-content: space-between; padding: 14px 18px; background: var(--surface-2,#f6f7f9); border-bottom: 1px solid var(--line,#e5e7eb); }
.lab-section-label { font-size: 13px; font-weight: 700; color: var(--ink-700,#374151); }
.lab-section-count { font-size: 12px; color: var(--ink-400,#9ca3af); }
.lab-scene-row { padding: 14px 18px; border-bottom: 1px solid var(--line,#e5e7eb); }
.lab-scene-row:last-child { border-bottom: none; }
.lab-scene-vo { font-size: 13px; color: var(--ink-700,#374151); line-height: 1.6; margin-bottom: 8px; }
.lab-scene-meta { display: flex; gap: 10px; flex-wrap: wrap; }
.lab-scene-badge { font-size: 11px; padding: 2px 8px; border-radius: 6px; background: var(--surface-3,#f3f4f6); color: var(--ink-500,#6b7280); }

.lab-produce-list { display: flex; flex-direction: column; gap: 16px; }
.lab-section-box { background: white; border: 1.5px solid var(--line,#e5e7eb); border-radius: 14px; overflow: hidden; transition: border-color .2s; }
.lab-section-box.producing { border-color: var(--accent,#6366f1); }
.lab-section-box.done-approved { border-color: #22c55e; }
.lab-section-box.error { border-color: #ef4444; }
.lab-section-box-header { display: flex; align-items: center; justify-content: space-between; padding: 16px 20px; }
.lab-section-box-title { font-size: 15px; font-weight: 700; color: var(--ink-700,#374151); }
.lab-section-box-status { font-size: 12px; font-weight: 500; }
.lab-section-progress { padding: 0 20px 16px; font-size: 13px; color: var(--ink-500,#6b7280); display: flex; align-items: center; gap: 8px; }
.lab-section-player { margin: 0 20px 16px; }
.lab-section-player video { width: 100%; border-radius: 8px; background: #000; }
.lab-section-actions { display: flex; gap: 10px; padding: 0 20px 16px; }
.lab-feedback-area { padding: 0 20px 16px; }
.lab-feedback-input { width: 100%; padding: 10px 14px; border: 1.5px solid var(--line,#e5e7eb); border-radius: 10px; font-size: 13px; font-family: inherit; resize: vertical; outline: none; transition: border-color .15s; box-sizing: border-box; }
.lab-feedback-input:focus { border-color: var(--accent,#6366f1); }

.lab-final-player { background: #000; border-radius: 12px; overflow: hidden; margin-bottom: 20px; }
.lab-final-player video { width: 100%; max-height: 480px; display: block; }

.lab-music-stub { background: var(--surface-2,#f6f7f9); border: 2px dashed var(--line,#e5e7eb); border-radius: 14px; padding: 48px 32px; text-align: center; margin-bottom: 28px; }
.lab-music-stub-icon { font-size: 40px; margin-bottom: 12px; }
.lab-music-stub-title { font-size: 18px; font-weight: 700; color: var(--ink-600,#4b5563); margin-bottom: 6px; }
.lab-music-stub-sub { font-size: 14px; color: var(--ink-400,#9ca3af); }
.lab-soon-badge { display: inline-block; margin-top: 14px; padding: 4px 14px; background: #fef3c7; color: #92400e; border-radius: 99px; font-size: 12px; font-weight: 600; }

.lab-sessions-list { margin-top: 48px; border-top: 1px solid var(--line,#e5e7eb); padding-top: 28px; }
.lab-sessions-title { font-size: 13px; font-weight: 600; color: var(--ink-500,#6b7280); margin-bottom: 14px; text-transform: uppercase; letter-spacing: .05em; }
.lab-session-item { display: flex; align-items: center; gap: 14px; padding: 12px 0; border-bottom: 1px solid var(--line,#e5e7eb); }
.lab-session-info { flex: 1; min-width: 0; }
.lab-session-yt-title { font-size: 14px; font-weight: 600; color: var(--ink-700,#374151); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.lab-session-meta { font-size: 12px; color: var(--ink-400,#9ca3af); }
.lab-session-step-pill { font-size: 11px; padding: 3px 10px; border-radius: 99px; background: var(--accent-soft,#eef2ff); color: var(--accent,#6366f1); font-weight: 600; flex-shrink: 0; }

/* ── Ideas step ── */
.lab-ideas-hero { font-size: 22px; font-weight: 800; color: var(--ink-900,#141414); margin-bottom: 6px; }
.lab-ideas-sub { font-size: 14px; color: var(--ink-500); margin-bottom: 28px; }
.lab-topic-input-big { width: 100%; padding: 18px 22px; border: 2px solid var(--line,#e5e7eb); border-radius: 14px; font-size: 16px; outline: none; transition: border-color .15s, box-shadow .15s; background: var(--surface); box-sizing: border-box; }
.lab-topic-input-big:focus { border-color: var(--accent,#2d5bff); box-shadow: 0 0 0 4px rgba(45,91,255,.1); }
.lab-use-topic-btn { display: inline-flex; align-items: center; gap: 8px; margin-top: 12px; padding: 12px 24px; border-radius: 10px; border: none; background: var(--accent,#2d5bff); color: white; font-size: 14px; font-weight: 600; cursor: pointer; transition: all .15s; }
.lab-use-topic-btn:hover { background: #1a48e8; }
.lab-gen-ideas-btn { display: flex; align-items: center; gap: 10px; width: 100%; padding: 18px 24px; border-radius: 14px; border: none; background: linear-gradient(135deg, #667eea 0%, #764ba2 50%, #f093fb 100%); color: white; font-size: 16px; font-weight: 700; cursor: pointer; transition: all .2s; box-shadow: 0 4px 20px rgba(118,75,162,.35); justify-content: center; }
.lab-gen-ideas-btn:hover { transform: translateY(-2px); box-shadow: 0 8px 30px rgba(118,75,162,.5); }
.lab-gen-ideas-btn:disabled { opacity: .6; transform: none; cursor: default; }

/* ── Standard action button (blue, like TubeGen) ── */
.lab-action-btn { display: inline-flex; align-items: center; gap: 8px; padding: 13px 26px; border-radius: 10px; border: none; background: var(--accent,#2d5bff); color: white; font-size: 15px; font-weight: 600; cursor: pointer; transition: all .15s; box-shadow: 0 2px 8px rgba(45,91,255,.25); }
.lab-action-btn:hover { background: #1a48e8; box-shadow: 0 4px 16px rgba(45,91,255,.4); transform: translateY(-1px); }
.lab-action-btn:disabled { opacity: .55; transform: none; cursor: default; }
.lab-action-btn.lg { padding: 16px 32px; font-size: 16px; font-weight: 700; }

/* ── Voiceover step ── */
.lab-vo-module-header { display: flex; align-items: center; gap: 16px; margin-bottom: 24px; }
.lab-vo-icon { width: 52px; height: 52px; border-radius: 14px; background: #eff6ff; display: flex; align-items: center; justify-content: center; font-size: 22px; flex-shrink: 0; }
.lab-vo-title { font-size: 20px; font-weight: 800; color: var(--ink-900); }
.lab-vo-sub { font-size: 13px; color: var(--ink-500); margin-top: 2px; }
.lab-vo-script-preview { background: var(--surface-2); border: 1px solid var(--line); border-radius: 12px; padding: 16px 18px; font-size: 14px; color: var(--ink-700); line-height: 1.7; max-height: 140px; overflow: hidden; position: relative; margin-bottom: 10px; }
.lab-vo-script-preview::after { content:""; position:absolute; bottom:0; left:0; right:0; height:40px; background:linear-gradient(transparent,var(--surface-2)); }
.lab-vo-meta { font-size: 13px; color: var(--ink-400); margin-bottom: 20px; }
.lab-vo-player-wrap { background: var(--surface-2); border: 1px solid var(--line); border-radius: 12px; padding: 14px 18px; margin-bottom: 20px; }
.lab-vo-player-label { font-size: 13px; font-weight: 700; color: var(--ink-700); margin-bottom: 10px; }
.lab-vo-player-wrap audio { width: 100%; height: 40px; }
.lab-vo-progress { background: var(--surface-2); border-radius: 10px; padding: 16px 18px; margin-bottom: 20px; font-size: 13px; color: var(--ink-500); display: flex; align-items: center; gap: 10px; }

/* ── Visuals step ── */
.lab-visuals-header { display: flex; align-items: center; justify-content: space-between; margin-bottom: 24px; flex-wrap: wrap; gap: 14px; }
.lab-visuals-title-block { display: flex; align-items: center; gap: 14px; }
.lab-visuals-icon { width: 52px; height: 52px; border-radius: 14px; background: #f0f4ff; display: flex; align-items: center; justify-content: center; font-size: 22px; flex-shrink: 0; }
.lab-visuals-title { font-size: 20px; font-weight: 800; color: var(--ink-900); }
.lab-visuals-sub { font-size: 13px; color: var(--ink-500); margin-top: 2px; }
.lab-animate-toggle { display: flex; gap: 10px; margin-bottom: 20px; }
.lab-animate-opt { display: flex; align-items: center; gap: 8px; padding: 10px 18px; border-radius: 10px; border: 2px solid var(--line); font-size: 13px; font-weight: 600; cursor: pointer; transition: all .15s; background: white; color: var(--ink-600); }
.lab-animate-opt.active { border-color: var(--accent); background: var(--accent-soft); color: var(--accent); }
.lab-animate-opt .soon { font-size: 10px; padding: 2px 7px; background: #fef3c7; color: #92400e; border-radius: 99px; font-weight: 700; margin-left: 4px; }
.lab-visuals-scene-list { display: flex; flex-direction: column; gap: 0; border: 1.5px solid var(--line); border-radius: 14px; overflow: hidden; margin-top: 20px; }
.lab-vs-scene { display: grid; grid-template-columns: 1fr 220px; border-bottom: 1px solid var(--line); min-height: 110px; }
.lab-vs-scene:last-child { border-bottom: none; }
.lab-vs-scene-body { padding: 14px 18px; }
.lab-vs-scene-head { display: flex; align-items: center; gap: 10px; margin-bottom: 6px; }
.lab-vs-scene-num { font-size: 11px; font-weight: 700; color: var(--ink-400); text-transform: uppercase; letter-spacing: .06em; }
.lab-vs-scene-time { font-size: 11px; color: var(--ink-400); }
.lab-vs-scene-vo { font-size: 13px; color: var(--ink-800); line-height: 1.6; margin-bottom: 8px; }
.lab-vs-scene-dur-bar { height: 3px; background: var(--line); border-radius: 99px; margin-bottom: 6px; }
.lab-vs-scene-dur-fill { height: 100%; background: var(--accent); border-radius: 99px; transition: width .3s; }
.lab-vs-dur-label { font-size: 11px; color: var(--ink-400); }
.lab-vs-img-slot { background: var(--surface-2); display: flex; align-items: center; justify-content: center; position: relative; overflow: hidden; }
.lab-vs-img-slot img { width: 100%; height: 100%; object-fit: cover; display: block; animation: imgFadeIn .3s ease; }
@keyframes imgFadeIn { from { opacity:0; } to { opacity:1; } }
.lab-vs-img-placeholder { font-size: 24px; color: var(--ink-300); }
.lab-vs-img-spinner { animation: spin .8s linear infinite; font-size: 20px; color: var(--ink-400); }

/* ── Voice step ── */
.lab-voice-card { background: white; border: 2px solid var(--line,#e5e7eb); border-radius: 14px; padding: 18px; cursor: pointer; transition: all .2s; position: relative; }
.lab-voice-card:hover { border-color: transparent; background: linear-gradient(white,white) padding-box, linear-gradient(135deg,#667eea,#764ba2,#f093fb,#f5576c) border-box; box-shadow: 0 4px 20px rgba(118,75,162,.2); }
.lab-voice-card.selected { border-color: transparent; background: linear-gradient(var(--accent-soft,#eef2ff),var(--accent-soft,#eef2ff)) padding-box, linear-gradient(135deg,#667eea,#764ba2) border-box; }
.lab-voice-play-btn { position: absolute; top: 12px; right: 12px; width: 32px; height: 32px; border-radius: 50%; border: none; background: var(--surface-2); color: var(--ink-500); font-size: 14px; cursor: pointer; display: flex; align-items: center; justify-content: center; transition: all .15s; }
.lab-voice-play-btn:hover { background: var(--accent); color: white; }
.lab-voice-playing { background: var(--accent) !important; color: white !important; animation: voicePulse 1s ease-in-out infinite; }
@keyframes voicePulse { 0%,100%{transform:scale(1)} 50%{transform:scale(1.15)} }

/* ── Script step ── */
.lab-script-topic-banner { background: linear-gradient(135deg, var(--accent-soft,#eef2ff), #f0f4ff); border: 1.5px solid var(--accent,#2d5bff); border-radius: 14px; padding: 18px 22px; margin-bottom: 24px; }
.lab-script-topic-label { font-size: 11px; font-weight: 700; text-transform: uppercase; letter-spacing: .08em; color: var(--accent,#2d5bff); margin-bottom: 4px; }
.lab-script-topic-text { font-size: 18px; font-weight: 800; color: var(--ink-900); }
.lab-script-title-suggest { font-size: 13px; color: var(--ink-500); margin-top: 4px; }

/* ── New-video button (solid blue, matches action buttons) ── */
.lab-new-video-btn { margin-left: auto; margin-right: 16px; flex-shrink: 0; padding: 8px 18px; border-radius: 8px; border: none; background: var(--accent,#2d5bff); color: white; font-size: 13px; font-weight: 600; cursor: pointer; transition: all .15s; white-space: nowrap; box-shadow: 0 2px 8px rgba(45,91,255,.25); }
.lab-new-video-btn:hover { background: #1a48e8; box-shadow: 0 4px 16px rgba(45,91,255,.4); transform: translateY(-1px); }

/* ── Stop / cancel button ── */
.lab-stop-btn { display: inline-flex; align-items: center; gap: 8px; padding: 10px 20px; border-radius: 10px; border: 1.5px solid #ef4444; background: #fff1f1; color: #dc2626; font-size: 14px; font-weight: 600; cursor: pointer; transition: all .15s; flex-shrink: 0; }
.lab-stop-btn:hover { background: #fecaca; border-color: #dc2626; }
.lab-stop-btn:disabled { opacity: .5; cursor: default; }
.lab-stop-cancelled { font-size: 13px; color: #9ca3af; display: flex; align-items: center; gap: 8px; padding: 10px 0; }

/* ── Produce step ── */
.lab-produce-section-block { border: 1.5px solid var(--line,#e5e7eb); border-radius: 16px; overflow: hidden; margin-bottom: 28px; background: white; }
.lab-produce-section-head { display: flex; align-items: center; justify-content: space-between; padding: 18px 22px; background: var(--surface-2,#f6f7f9); border-bottom: 1px solid var(--line); }
.lab-produce-section-title { font-size: 15px; font-weight: 700; color: var(--ink-800); }
.lab-produce-section-badge { font-size: 12px; padding: 4px 12px; border-radius: 99px; font-weight: 600; }
.lab-produce-section-badge.pending { background: var(--surface-3); color: var(--ink-500); }
.lab-produce-section-badge.generating { background: #fef3c7; color: #92400e; }
.lab-produce-section-badge.ready { background: #d1fae5; color: #065f46; }
.lab-produce-section-badge.producing { background: var(--accent-soft); color: var(--accent); }
.lab-produce-section-badge.done { background: #d1fae5; color: #065f46; }
.lab-produce-section-badge.error { background: #fee2e2; color: #991b1b; }
.lab-produce-scenes { display: flex; flex-direction: column; gap: 0; }
.lab-scene-card { display: grid; grid-template-columns: 1fr 200px; border-bottom: 1px solid var(--line,#e5e7eb); }
.lab-scene-card:last-child { border-bottom: none; }
.lab-scene-card-body { padding: 14px 18px; }
.lab-scene-idx { font-size: 11px; font-weight: 700; color: var(--ink-400); text-transform: uppercase; letter-spacing: .06em; margin-bottom: 6px; }
.lab-scene-vo-text { font-size: 13px; color: var(--ink-800); line-height: 1.6; margin-bottom: 8px; }
.lab-scene-badges { display: flex; gap: 6px; flex-wrap: wrap; }
.lab-scene-img-slot { background: var(--surface-2); display: flex; align-items: center; justify-content: center; min-height: 120px; position: relative; overflow: hidden; }
.lab-scene-img-slot img { width: 100%; height: 100%; object-fit: cover; display: block; }
.lab-scene-img-placeholder { font-size: 28px; color: var(--ink-300); }
.lab-scene-img-spinner { font-size: 22px; animation: spin .8s linear infinite; }
@keyframes spin { to { transform: rotate(360deg); } }
.lab-produce-section-actions { padding: 16px 22px; display: flex; gap: 10px; align-items: center; flex-wrap: wrap; }
.lab-section-video-wrap { padding: 16px 22px; border-top: 1px solid var(--line); }
.lab-section-video-wrap video { width: 100%; border-radius: 10px; background: #000; max-height: 340px; }
.lab-produce-progress-line { padding: 10px 22px; font-size: 13px; color: var(--ink-500); display: flex; align-items: center; gap: 8px; border-top: 1px solid var(--line); }
`;
  document.head.appendChild(style);
})();

// ── Main mount ────────────────────────────────────────────────────────────────
export async function mount(outlet, { state } = {}) {
  const wrap = h("div", { class: "lab-wrap" });
  outlet.appendChild(wrap);

  wrap.appendChild(h("div", { class: "lab-page-header" }, [
    h("h1", { class: "lab-page-title" }, ["The Lab"]),
    h("div", { class: "lab-page-sub" }, [
      "Reverse-engineer any YouTube video, then reproduce its formula for your own topic.",
    ]),
  ]));

  const labModule = h("div", { class: "lab-module" });
  wrap.appendChild(labModule);

  const stepBarEl = h("div", { class: "lab-step-bar", id: "lab-step-bar" });
  labModule.appendChild(stepBarEl);

  const labContent = h("div", { class: "lab-content" });
  labModule.appendChild(labContent);

  const stepArea = h("div", { class: "lab-panel", id: "lab-step-area" });
  labContent.appendChild(stepArea);


  let session = null;
  let currentUIStep = "reverse";
  let isTemplateSession = false;  // Track if this session came from a template

  // ── Handle template session from state ────────────────────────────────────
  if (state?.templateSessionId) {
    (async () => {
      try {
        session = await api.labSession(state.templateSessionId);
        isTemplateSession = true;
        const uiStep = sessionToUIStep(session.step);
        renderStepBar(uiStep);
        await renderStep(uiStep);
      } catch (e) {
        console.error("Failed to load template session:", e);
        alert("Error loading template session: " + e.message);
      }
    })();
    return;  // Stop further initialization, let async handler take over
  }

  // ── Progress animation helper ────────────────────────────────────────────
  const progressAnimations = {};
  function updateProgressWithDots(element, message) {
    if (!element || !message) return;
    // Clear any previous animation for this element
    const elemKey = Math.random();  // unique key per element
    Object.keys(progressAnimations).forEach(k => {
      if (progressAnimations[k].el === element) clearInterval(progressAnimations[k].interval);
    });

    let dotCount = 0;
    element.textContent = message + ".";
    const interval = setInterval(() => {
      dotCount = (dotCount + 1) % 4;
      const dots = ".".repeat(Math.min(dotCount + 1, 3));
      element.textContent = message + dots;
    }, 400);
    progressAnimations[elemKey] = { interval, el: element };
  }

  // ── Step bar renderer ─────────────────────────────────────────────────────
  function renderStepBar(activeStep) {
    currentUIStep = activeStep;
    const activeIdx = STEP_IDS.indexOf(activeStep);
    stepBarEl.innerHTML = "";
    STEPS.forEach((s, i) => {
      const isDone   = i < activeIdx;
      const isActive = s.id === activeStep;
      // Override "Reverse" label with "Template" for template sessions
      const label = (s.id === "reverse" && isTemplateSession) ? "Template" : s.label;
      const pill = h("button", {
        class: `lab-step-pill ${isActive ? "active" : ""} ${isDone ? "done" : ""}`,
        onclick: isDone ? () => goToStep(s.id) : null,
      }, [
        h("span", { class: "pill-num" }, [isDone ? "✓" : String(i + 1)]),
        h("span", {}, [label]),
      ]);
      stepBarEl.appendChild(pill);
    });

    // "New video" button — only when a session is active AND not on reverse step
    if (session && activeStep !== "reverse") {
      const newBtn = h("button", { class: "lab-new-video-btn", title: "Cancel this video and start a new one" }, ["＋ New video"]);
      newBtn.addEventListener("click", async () => {
        const confirmed = confirm(
          "Start a new video?\n\nAny active generation will be stopped and this session will be saved to Recent sessions."
        );
        if (!confirmed) return;
        // Cancel any running jobs without deleting files
        try { await api.labCancel(session.id); } catch {}
        // Detach session — keep it in recent sessions for resuming later
        session = null;
        renderStepBar("reverse");
        stepArea.innerHTML = "";
        mountReverseStep();
        loadSessionsDrawer();
        toast("Session saved to Recent sessions. Paste a new URL to start.", { kind: "info" });
      });
      stepBarEl.appendChild(newBtn);
    }
  }

  // ── Step navigation ───────────────────────────────────────────────────────
  async function goToStep(uiStep) {
    stepArea.innerHTML = "";
    stepArea.className = "lab-panel";
    renderStepBar(uiStep);
    await renderStep(uiStep);
  }

  // ── Render step ───────────────────────────────────────────────────────────
  async function renderStep(uiStep) {
    switch (uiStep) {
      case "reverse":   mountReverseStep();    break;
      case "ideas":     mountIdeasStep();      break;
      case "voice":     mountVoiceStep();      break;
      case "script":    mountScriptStep();     break;
      case "voiceover": mountVoiceoverStep();  break;
      case "visuals":   mountVisualsStep();    break;
      case "assembly":  mountAssemblyStep();   break;
      case "thumbnail": mountThumbnailStep();  break;
    }
  }

  // ── Helper: next-step button ──────────────────────────────────────────────
  function nextBtn(label, onclick, disabled = false) {
    const btn = h("button", {
      class: "btn primary",
      style: { marginTop: "24px" },
      onclick,
    }, [h("span", {}, [label])]);
    if (disabled) btn.disabled = true;
    return btn;
  }

  // ── STEP 1: Reverse ───────────────────────────────────────────────────────
  function mountReverseStep() {
    const panel = h("div");

    panel.appendChild(h("p", { class: "lab-hero-instruction" }, [
      "Paste a YouTube URL below. The Lab will download the video, analyse its scene structure, motion, transcription, audio rhythm, and script formula — then extract a full production blueprint you can replicate for your own topic.",
    ]));

    const urlInput = h("input", {
      class: "lab-url-input",
      type: "url",
      placeholder: "https://www.youtube.com/watch?v=…",
    });
    const analyseBtn = h("button", { class: "btn primary" }, [
      h("span", { html: icons.sparkle }),
      h("span", {}, [" Analyse Video"]),
    ]);
    panel.appendChild(h("div", { class: "lab-url-row" }, [urlInput, analyseBtn]));

    const progressPanel = h("div", { class: "lab-progress-panel", style: { display: "none" } });
    panel.appendChild(progressPanel);

    const STAGE_LABELS = [
      "Downloading video",
      "Probing video",
      "Detecting scenes",
      "Extracting keyframes",
      "Analysing motion",
      "Vision labelling",
      "Classifying scenes",
      "Transcribing",
      "Analysing audio",
      "Extracting script formula",
      "Building blueprint",
    ];
    let currentStageEl = null;
    let dotsInterval = null;

    function showProgress() {
      progressPanel.style.display = "";
      progressPanel.innerHTML = "";
      currentStageEl = h("div", { class: "lab-current-step", style: { fontSize: "14px", color: "var(--ink-600, #4b5563)" } }, ["Initializing…"]);
      progressPanel.appendChild(currentStageEl);
    }

    function markStageFromMsg(msg) {
      const lower = msg.toLowerCase();
      const checks = [
        "download", "prob", "detect", "keyframe", "motion", "vision", "classif",
        "transcrib", "audio", "script formula", "blueprint",
      ];

      let foundStage = null;
      for (const kw of checks) {
        if (lower.includes(kw)) {
          foundStage = STAGE_LABELS[checks.indexOf(kw)];
          break;
        }
      }

      if (foundStage && currentStageEl) {
        // Clear previous animation interval
        if (dotsInterval) clearInterval(dotsInterval);
        updateProgressWithDots(currentStageEl, foundStage);
        dotsInterval = null;
      }
    }

    analyseBtn.addEventListener("click", async () => {
      const url = urlInput.value.trim();
      if (!url) { toast("Paste a YouTube URL first", { kind: "error" }); return; }

      analyseBtn.disabled = true;
      analyseBtn.innerHTML = `<span class="spinner-sm"></span><span> Analysing…</span>`;
      showProgress();

      try {
        const { job_id, session_id } = await api.labReverse(url, session?.id || null);

        let poll;
        poll = setInterval(async () => {
          if (!outlet.isConnected) { clearInterval(poll); return; }
          const job = await api.labReverseStatus(job_id);
          if (job.stage_current) markStageFromMsg(job.stage_current);

          if (job.status === "done") {
            clearInterval(poll);
            if (dotsInterval) clearInterval(dotsInterval);
            if (currentStageEl) currentStageEl.textContent = "Analysis complete";
            setTimeout(async () => {
              session = await api.labSession(session_id);
              showSummary(panel, session.summary, session_id);
            }, 600);
            return;
          } else if (job.status === "error") {
            clearInterval(poll);
            toast(`Analysis failed: ${job.error}`, { kind: "error" });
            analyseBtn.disabled = false;
            analyseBtn.innerHTML = `<span>${icons.sparkle}</span><span> Analyse Video</span>`;
          }
        }, 1800);
      } catch (e) {
        toast(e.message || "Failed to start analysis", { kind: "error" });
        analyseBtn.disabled = false;
        analyseBtn.innerHTML = `<span>${icons.sparkle}</span><span> Analyse Video</span>`;
      }
    });

    urlInput.addEventListener("keydown", (e) => {
      if (e.key === "Enter") analyseBtn.click();
    });

    stepArea.appendChild(panel);

    // Load and display sessions below the reverse panel
    renderSessionsForReverse(stepArea);
  }

  async function renderSessionsForReverse(container) {
    const r = await api.labSessions();
    const items = (r.items || []).filter((s) => s.id !== session?.id);
    if (!items.length) return;

    const wrap = h("div", { class: "lab-sessions-list", style: { marginTop: "40px", marginBottom: "40px" } });
    wrap.appendChild(h("div", { class: "lab-sessions-title" }, ["Resume a video"]));
    items.slice(0, 8).forEach((s) => {
      const stepLabel = s.step?.replace(/_/g, " ") || "—";
      const row = h("div", { class: "lab-session-item" }, [
        h("div", { class: "lab-session-info" }, [
          h("div", { class: "lab-session-yt-title" }, [s.yt_title || s.url || s.id]),
          h("div", { class: "lab-session-meta" }, [
            `@${s.yt_channel || "unknown"}${s.idea ? ` · "${s.idea}"` : ""}`,
          ]),
        ]),
        h("span", { class: "lab-session-step-pill" }, [stepLabel]),
        h("button", {
          class: "btn ghost sm",
          onclick: async () => {
            session = await api.labSession(s.id);
            const uiStep = sessionToUIStep(session.step);
            renderStepBar(uiStep);
            await renderStep(uiStep);
          },
        }, ["Resume →"]),
        h("button", {
          class: "btn ghost sm",
          style: { color: "#ef4444" },
          onclick: async (e) => {
            e.stopPropagation();
            if (!confirm("Delete this session and all its files?")) return;
            await api.labDeleteSession(s.id);
            row.remove();
            if (!wrap.querySelector(".lab-session-item")) wrap.remove();
          },
        }, ["✕"]),
      ]);
      wrap.appendChild(row);
    });
    container.appendChild(wrap);
  }

  function showSummary(panel, sm, sid) {
    const card = h("div", { class: "lab-summary-card" });

    card.appendChild(h("div", { class: "lab-summary-title" }, [sm.title || "Untitled"]));
    card.appendChild(h("div", { class: "lab-summary-channel" }, [
      `@${sm.channel || "unknown"} · ${sm.scene_count} scenes · ~${sm.avg_scene_s}s avg`,
    ]));

    card.appendChild(h("div", { class: "lab-summary-grid" }, [
      summaryItem("Production Style", `${sm.production_type} (${sm.confidence}% confidence)`),
      summaryItem("Hook Pattern", sm.hook_pattern || "—"),
      summaryItem("Tone", (sm.tone || []).join(", ") || "—"),
      summaryItem("VO Style", sm.vo_style || "—"),
      summaryItem("Visual Mood", sm.visual_mood || "—"),
      summaryItem("Narrative Arc", (sm.narrative_arc || []).join(" → ") || "—"),
    ]));

    if (sm.style_tags?.length) {
      const tagsWrap = h("div", [
        h("div", { class: "lab-summary-label" }, ["Style tags"]),
        h("div", { class: "lab-tags" }, sm.style_tags.map((t) => h("span", { class: "lab-tag" }, [t]))),
      ]);
      card.appendChild(tagsWrap);
    }

    if (sm.must_keep?.length) {
      const mk = h("div", { class: "lab-must-keep" });
      mk.appendChild(h("div", { class: "lab-summary-label", style: { marginBottom: "8px" } }, ["Must keep when reproducing"]));
      sm.must_keep.forEach((item) => {
        mk.appendChild(h("div", { class: "lab-must-item" }, [item]));
      });
      card.appendChild(mk);
    }

    card.appendChild(nextBtn("Choose my topic →", async () => {
      await goToStep("ideas");
      loadSessionsDrawer();
    }));

    panel.appendChild(card);
  }

  function summaryItem(label, value) {
    return h("div", { class: "lab-summary-item" }, [
      h("div", { class: "lab-summary-label" }, [label]),
      h("div", { class: "lab-summary-value" }, [value]),
    ]);
  }

  // ── STEP 2: Ideas ─────────────────────────────────────────────────────────
  function mountIdeasStep() {
    if (!session) return;
    const panel = h("div");

    panel.appendChild(h("div", { class: "lab-ideas-hero" }, ["What's your video about?"]));
    panel.appendChild(h("div", { class: "lab-ideas-sub" }, [
      `Formula from: "${session.yt_title || ""}" by @${session.yt_channel || ""}`
    ]));

    // Big full-width topic input
    const topicInput = h("input", {
      class: "lab-topic-input-big",
      type: "text",
      placeholder: "e.g. How the Fed is quietly destroying the middle class",
    });
    panel.appendChild(topicInput);
    const useTopicBtn = h("button", { class: "lab-use-topic-btn" }, ["Use this topic →"]);
    panel.appendChild(useTopicBtn);

    panel.appendChild(h("div", { class: "lab-topic-divider", style: { margin: "28px 0" } }, ["or let the formula generate ideas for you"]));

    const genIdeasBtn = h("button", { class: "lab-gen-ideas-btn" }, [
      h("span", { html: icons.sparkle }),
      h("span", {}, [" Generate ideas using this formula"]),
    ]);
    panel.appendChild(genIdeasBtn);

    const ideasArea = h("div", { style: { marginTop: "16px" } });
    panel.appendChild(ideasArea);

    let selectedIdea = null;

    const confirmBtn = h("button", { class: "btn primary", style: { marginTop: "16px", display: "none" } }, [
      "Use selected idea →",
    ]);
    panel.appendChild(confirmBtn);

    useTopicBtn.addEventListener("click", async () => {
      const topic = topicInput.value.trim();
      if (!topic) { toast("Write your topic first", { kind: "error" }); return; }
      await api.labIdeaSelect(session.id, topic);
      session.idea = topic;
      session.step = "idea_done";
      await goToStep("voice");
    });

    genIdeasBtn.addEventListener("click", async () => {
      genIdeasBtn.disabled = true;
      genIdeasBtn.innerHTML = `<span class="spinner-sm"></span><span> Generating ideas…</span>`;
      ideasArea.innerHTML = "";
      selectedIdea = null;
      confirmBtn.style.display = "none";

      try {
        const { job_id } = await api.labIdeas(session.id, topicInput.value.trim() || null, 6);
        let poll = setInterval(async () => {
          if (!outlet.isConnected) { clearInterval(poll); return; }
          const job = await api.labIdeasStatus(job_id);
          if (job.status === "done") {
            clearInterval(poll);
            genIdeasBtn.disabled = false;
            genIdeasBtn.innerHTML = `<span>${icons.sparkle}</span><span> Regenerate ideas</span>`;
            renderIdeaCards(job.items);
          } else if (job.status === "error") {
            clearInterval(poll);
            genIdeasBtn.disabled = false;
            genIdeasBtn.innerHTML = `<span>${icons.sparkle}</span><span> Generate ideas using this formula</span>`;
            toast(job.error || "Failed to generate ideas", { kind: "error" });
          }
        }, 1200);
      } catch (e) {
        genIdeasBtn.disabled = false;
        toast(e.message, { kind: "error" });
      }
    });

    function renderIdeaCards(ideas) {
      ideasArea.innerHTML = "";
      const grid = h("div", { class: "lab-ideas-grid" });
      ideas.forEach((idea) => {
        const card = h("div", { class: "lab-idea-card" }, [
          h("div", { class: "lab-idea-title" }, [idea.title]),
          h("div", { class: "lab-idea-desc" }, [idea.description]),
          idea.angle ? h("div", { class: "lab-idea-angle" }, [idea.angle]) : null,
        ].filter(Boolean));
        card.addEventListener("click", () => {
          grid.querySelectorAll(".lab-idea-card").forEach((c) => c.classList.remove("selected"));
          card.classList.add("selected");
          selectedIdea = idea.title;
          confirmBtn.style.display = "";
        });
        grid.appendChild(card);
      });
      ideasArea.appendChild(grid);
    }

    confirmBtn.addEventListener("click", async () => {
      if (!selectedIdea) return;
      await api.labIdeaSelect(session.id, selectedIdea);
      session.idea = selectedIdea;
      session.step = "idea_done";
      await goToStep("voice");
    });

    stepArea.appendChild(panel);
  }

  // ── STEP 3: Voice ─────────────────────────────────────────────────────────
  function mountVoiceStep() {
    if (!session) return;
    const panel = h("div");

    panel.appendChild(h("p", { class: "lab-hero-instruction" }, [
      `Topic: "${session.idea}" — Now choose the narrator voice for your video.`,
    ]));

    let selectedVoiceId = session.voice_id || "";
    const grid = h("div", { class: "lab-voice-grid" });
    const continueBtn = h("button", {
      class: "btn primary",
      style: { display: selectedVoiceId ? "" : "none" },
    }, ["Continue →"]);

    let activeAudio = null;
    let activePlayBtn = null;

    function stopActiveAudio() {
      if (activeAudio) { activeAudio.pause(); activeAudio = null; }
      if (activePlayBtn) { activePlayBtn.textContent = "▶"; activePlayBtn.classList.remove("lab-voice-playing"); activePlayBtn = null; }
    }

    async function loadVoices() {
      const { items } = await api.labVoices();
      items.forEach((v) => {
        const card = h("div", {
          class: `lab-voice-card ${v.id === selectedVoiceId ? "selected" : ""}`,
        }, [
          h("div", { class: "lab-voice-name" }, [v.name]),
          h("div", { class: "lab-voice-meta" }, [`${v.accent} · ${v.gender === "F" ? "Female" : "Male"}`]),
          h("div", { class: "lab-voice-style" }, [v.style]),
        ]);

        // Preview play button
        if (v.preview_url) {
          const playBtn = h("button", { class: "lab-voice-play-btn", title: "Preview voice" }, ["▶"]);
          playBtn.addEventListener("click", (e) => {
            e.stopPropagation();
            const isSame = activePlayBtn === playBtn;
            stopActiveAudio();
            if (isSame) return;
            const audio = new Audio(v.preview_url);
            activeAudio = audio;
            activePlayBtn = playBtn;
            playBtn.textContent = "■";
            playBtn.classList.add("lab-voice-playing");
            audio.play();
            audio.onended = () => stopActiveAudio();
          });
          card.appendChild(playBtn);
        }

        card.addEventListener("click", () => {
          stopActiveAudio();
          grid.querySelectorAll(".lab-voice-card").forEach((c) => c.classList.remove("selected"));
          card.classList.add("selected");
          selectedVoiceId = v.id;
          continueBtn.style.display = "";
        });
        grid.appendChild(card);
      });
    }

    continueBtn.addEventListener("click", async () => {
      if (!selectedVoiceId) return;
      await api.labVoice(session.id, selectedVoiceId);
      session.voice_id = selectedVoiceId;
      session.step = "voice_done";
      await goToStep("script");
    });

    panel.appendChild(grid);
    panel.appendChild(continueBtn);
    loadVoices();
    stepArea.appendChild(panel);
  }

  // ── STEP 4: Script ────────────────────────────────────────────────────────
  function mountScriptStep() {
    if (!session) return;
    const panel = h("div");

    // If script already done, show it
    if (session.step === "script_done" || session.step === "script_approved") {
      showScriptView(panel);
      stepArea.appendChild(panel);
      return;
    }

    const banner = h("div", { class: "lab-script-topic-banner" }, [
      h("div", { class: "lab-script-topic-label" }, ["Your video topic"]),
      h("div", { class: "lab-script-topic-text" }, [session.idea || "—"]),
    ]);
    panel.appendChild(banner);

    // Duration picker
    const DURATIONS = [3, 5, 8, 10, 15];
    let selectedDuration = session.duration_min || 5;
    const durRow = h("div", { class: "lab-duration-row" });
    DURATIONS.forEach((min) => {
      const btn = h("button", {
        class: `lab-dur-btn ${min === selectedDuration ? "active" : ""}`,
        onclick: () => {
          durRow.querySelectorAll(".lab-dur-btn").forEach((b) => b.classList.remove("active"));
          btn.classList.add("active");
          selectedDuration = min;
        },
      }, [`${min} min`]);
      durRow.appendChild(btn);
    });
    panel.appendChild(h("div", { class: "lab-summary-label" }, ["Target video length"]));
    panel.appendChild(durRow);

    const genBtn = h("button", { class: "btn primary", style: { marginTop: "20px" } }, [
      h("span", { html: icons.sparkle }),
      h("span", {}, [" Generate Script"]),
    ]);
    const progress = h("div", { class: "lab-progress-panel", style: { display: "none", marginTop: "16px" } });
    panel.appendChild(genBtn);
    panel.appendChild(progress);

    genBtn.addEventListener("click", async () => {
      genBtn.disabled = true;
      genBtn.innerHTML = `<span class="spinner-sm"></span><span> Writing script with Claude…</span>`;
      progress.style.display = "";
      progress.textContent = "Generating script — this takes about 20–40 seconds…";

      try {
        const { job_id } = await api.labScript(session.id, selectedDuration);
        let poll = setInterval(async () => {
          if (!outlet.isConnected) { clearInterval(poll); return; }
          const job = await api.labScriptStatus(job_id);
          if (job.status === "done") {
            clearInterval(poll);
            session = await api.labSession(session.id);
            panel.innerHTML = "";
            showScriptView(panel);
          } else if (job.status === "error") {
            clearInterval(poll);
            genBtn.disabled = false;
            genBtn.innerHTML = `<span>${icons.sparkle}</span><span> Generate Script</span>`;
            toast(job.error || "Script generation failed", { kind: "error" });
          }
        }, 2000);
      } catch (e) {
        genBtn.disabled = false;
        toast(e.message, { kind: "error" });
      }
    });

    stepArea.appendChild(panel);
  }

  async function showScriptView(panel) {
    let script;
    try {
      script = await api.labGetScript(session.id);
    } catch {
      panel.appendChild(h("div", { class: "caption" }, ["Could not load script."]));
      return;
    }

    // Always show user's chosen topic prominently
    const topicBanner = h("div", { class: "lab-script-topic-banner", style: { marginBottom: "24px" } }, [
      h("div", { class: "lab-script-topic-label" }, ["Generating for"]),
      h("div", { class: "lab-script-topic-text" }, [session.idea || "—"]),
      script.title_suggestion ? h("div", { class: "lab-script-title-suggest" }, [
        `Claude suggests: "${script.title_suggestion}"`
      ]) : null,
    ].filter(Boolean));
    panel.appendChild(topicBanner);

    const view = h("div", { class: "lab-script-view" });
    (script.sections || []).forEach((sec) => {
      const secEl = h("div", { class: "lab-script-section" });
      secEl.appendChild(h("div", { class: "lab-section-header" }, [
        h("span", { class: "lab-section-label" }, [sec.label || sec.id]),
        h("span", { class: "lab-section-count" }, [`${sec.scenes?.length || 0} scenes`]),
      ]));
      (sec.scenes || []).forEach((scene) => {
        const row = h("div", { class: "lab-scene-row" });
        row.appendChild(h("div", { class: "lab-scene-vo" }, [scene.vo || ""]));
        const meta = h("div", { class: "lab-scene-meta" });
        if (scene.camera_move) meta.appendChild(h("span", { class: "lab-scene-badge" }, [scene.camera_move]));
        if (scene.on_screen_text) meta.appendChild(h("span", { class: "lab-scene-badge" }, [`"${scene.on_screen_text}"`]));
        if (meta.children.length) row.appendChild(meta);
        secEl.appendChild(row);
      });
      view.appendChild(secEl);
    });
    panel.appendChild(view);

    if (session.step !== "script_approved") {
      panel.appendChild(nextBtn("Approve script & generate voiceover →", async () => {
        await api.labApproveScript(session.id);
        session.step = "script_approved";
        await goToStep("voiceover");
      }));
    } else {
      panel.appendChild(nextBtn("Continue to voiceover →", () => goToStep("voiceover")));
    }
  }

  // ── STEP 5: Produce ───────────────────────────────────────────────────────
  function mountProduceStep() {
    if (!session) return;
    const panel = h("div");

    panel.appendChild(h("div", { class: "lab-script-topic-banner", style: { marginBottom: "28px" } }, [
      h("div", { class: "lab-script-topic-label" }, ["Producing"]),
      h("div", { class: "lab-script-topic-text" }, [session.idea || "—"]),
    ]));

    const list = h("div");
    panel.appendChild(list);

    const assembleBtn = h("button", {
      class: "btn primary",
      style: { marginTop: "24px", display: "none" },
    }, [h("span", { html: icons.sparkle }), h("span", {}, [" Assemble Final Video →"])]);
    panel.appendChild(assembleBtn);
    assembleBtn.addEventListener("click", () => goToStep("assembly"));

    const secState = {};

    async function loadSections() {
      const r = await api.labSections(session.id);
      const sections = r.items || [];
      list.innerHTML = "";
      for (const sec of sections) {
        secState[sec.id] = { sceneImageUrls: {}, imageJobRunning: false, produceJobRunning: false };
        list.appendChild(buildSectionBlock(sec, sections));
      }
    }

    function buildSectionBlock(sec, allSections) {
      const block = h("div", { class: "lab-produce-section-block", id: `sec-block-${sec.id}` });
      const badge = h("span", { class: "lab-produce-section-badge pending" }, ["Pending"]);
      block.appendChild(h("div", { class: "lab-produce-section-head" }, [
        h("div", { class: "lab-produce-section-title" }, [sec.label || sec.id]),
        badge,
      ]));
      const scenesWrap = h("div", { class: "lab-produce-scenes" });
      block.appendChild(scenesWrap);
      loadSceneCards(sec.id, scenesWrap);

      const progressLine = h("div", { class: "lab-produce-progress-line", style: { display: "none" } });
      block.appendChild(progressLine);
      const videoWrap = h("div", { class: "lab-section-video-wrap", style: { display: "none" } });
      block.appendChild(videoWrap);
      const actionsRow = h("div", { class: "lab-produce-section-actions" });
      block.appendChild(actionsRow);

      const updateBadge = (cls, label) => { badge.className = `lab-produce-section-badge ${cls}`; badge.textContent = label; };

      function buildActions() {
        actionsRow.innerHTML = "";
        const st = secState[sec.id];
        const imagesReady = Object.keys(st.sceneImageUrls).length > 0;
        if (!imagesReady && !st.imageJobRunning) {
          const btn = h("button", { class: "lab-gen-ideas-btn", style: { padding: "12px 22px", fontSize: "14px", width: "auto" } }, [
            h("span", { html: icons.sparkle }), h("span", {}, [" Generate Images"]),
          ]);
          btn.addEventListener("click", () => startImageGen(sec.id, scenesWrap, actionsRow, progressLine, updateBadge, buildActions));
          actionsRow.appendChild(btn);
        }
        if (imagesReady && !st.produceJobRunning) {
          const btn = h("button", { class: "btn primary" }, [
            h("span", { html: icons.sparkle }), h("span", {}, [" Produce Section (VO + Animate + Assemble)"]),
          ]);
          btn.addEventListener("click", () => startProduce(sec, actionsRow, progressLine, videoWrap, updateBadge, buildActions, allSections));
          actionsRow.appendChild(btn);
        }
      }

      // Restore existing state if images already generated
      api.labSectionImagesStatus(session.id, sec.id).then((r) => {
        if (r.image_urls && Object.keys(r.image_urls).length > 0) {
          secState[sec.id].sceneImageUrls = r.image_urls;
          updateImageSlots(sec.id, scenesWrap, r.image_urls);
          if (sec.mp4_url) {
            showSectionVideo(videoWrap, sec.mp4_url, sec, actionsRow, progressLine, updateBadge, buildActions, allSections);
            updateBadge("done", "Done");
            assembleBtn.style.display = "";
          } else {
            updateBadge("ready", "Images ready");
          }
        }
        buildActions();
      }).catch(() => buildActions());

      return block;
    }

    async function loadSceneCards(sectionId, container) {
      try {
        const script = await api.labGetScript(session.id);
        const section = (script.sections || []).find((s) => s.id === sectionId);
        if (!section) return;
        for (const sc of (section.scenes || [])) {
          const card = h("div", { class: "lab-scene-card" });
          const body = h("div", { class: "lab-scene-card-body" }, [
            h("div", { class: "lab-scene-idx" }, [`Scene ${sc.idx}`]),
            h("div", { class: "lab-scene-vo-text" }, [sc.vo || ""]),
            h("div", { class: "lab-scene-badges" }, [
              sc.camera_move ? h("span", { class: "lab-scene-badge" }, [sc.camera_move]) : null,
              sc.on_screen_text ? h("span", { class: "lab-scene-badge" }, [`"${sc.on_screen_text}"`]) : null,
            ].filter(Boolean)),
          ]);
          card.appendChild(body);
          card.appendChild(h("div", { class: "lab-scene-img-slot", id: `imgslot-${sectionId}-${sc.idx}` }, [
            h("span", { class: "lab-scene-img-placeholder" }, ["🖼"]),
          ]));
          container.appendChild(card);
        }
      } catch {}
    }

    function updateImageSlots(sectionId, container, imageUrls) {
      for (const [idxStr, url] of Object.entries(imageUrls)) {
        const slot = document.getElementById(`imgslot-${sectionId}-${idxStr}`);
        if (slot) { slot.innerHTML = ""; slot.appendChild(h("img", { src: url + "?t=" + Date.now(), alt: "" })); }
      }
    }

    function startImageGen(sectionId, scenesWrap, actionsRow, progressLine, updateBadge, buildActions) {
      secState[sectionId].imageJobRunning = true;
      updateBadge("generating", "Generating images");
      actionsRow.innerHTML = "";
      progressLine.style.display = "";
      const progressMsg = h("span", {}, []);
      progressLine.innerHTML = "";
      progressLine.appendChild(h("span", { class: "spinner-sm" }, []));
      progressLine.appendChild(progressMsg);
      updateProgressWithDots(progressMsg, "Generating images");

      api.labGenerateSectionImages(session.id, sectionId).then(() => {
        const poll = setInterval(async () => {
          if (!outlet.isConnected) { clearInterval(poll); return; }
          const r = await api.labSectionImagesStatus(session.id, sectionId);
          updateImageSlots(sectionId, scenesWrap, r.image_urls || {});
          secState[sectionId].sceneImageUrls = r.image_urls || {};
          const done = Object.values(r.scene_statuses || {}).filter((s) => s === "done").length;
          const total = Object.keys(r.scene_statuses || {}).length;
          if (total > 0) progressMsg.textContent = `Generating images (${done}/${total})`;
          if (r.status === "done" || r.status === "error") {
            clearInterval(poll);
            secState[sectionId].imageJobRunning = false;
            progressLine.style.display = "none";
            if (r.status === "error") { updateBadge("error", "Image gen failed"); toast(r.error || "Image gen failed", { kind: "error" }); }
            else updateBadge("ready", "Images ready");
            buildActions();
          }
        }, 2000);
      }).catch((e) => {
        secState[sectionId].imageJobRunning = false;
        progressLine.style.display = "none";
        updateBadge("error", "Failed");
        toast(e.message, { kind: "error" });
        buildActions();
      });
    }

    function startProduce(sec, actionsRow, progressLine, videoWrap, updateBadge, buildActions, allSections) {
      secState[sec.id].produceJobRunning = true;
      updateBadge("producing", "Producing…");
      actionsRow.innerHTML = "";
      progressLine.style.display = "";
      const progressMsg = h("span", {}, []);
      progressLine.innerHTML = "";
      progressLine.appendChild(h("span", { class: "spinner-sm" }, []));
      progressLine.appendChild(progressMsg);
      updateProgressWithDots(progressMsg, "Generating video");

      api.labProduceSection(session.id, sec.id, null).then(() => {
        const poll = setInterval(async () => {
          if (!outlet.isConnected) { clearInterval(poll); return; }
          const job = await api.labSectionStatus(session.id, sec.id);
          if (job.current) updateProgressWithDots(progressMsg, job.current);
          if (job.status === "done" || job.status === "error") {
            clearInterval(poll);
            secState[sec.id].produceJobRunning = false;
            progressLine.style.display = "none";
            if (job.status === "error") {
              updateBadge("error", "Failed");
              actionsRow.innerHTML = "";
              actionsRow.appendChild(h("div", { style: { color: "#ef4444", fontSize: "13px", padding: "4px 0" } }, [job.error || "Unknown error"]));
              const retry = h("button", { class: "btn ghost" }, ["↻ Retry"]);
              retry.addEventListener("click", () => startProduce(sec, actionsRow, progressLine, videoWrap, updateBadge, buildActions, allSections));
              actionsRow.appendChild(retry);
            } else {
              updateBadge("done", "Ready — Review");
              sec.mp4_url = job.mp4_url;
              showSectionVideo(videoWrap, job.mp4_url, sec, actionsRow, progressLine, updateBadge, buildActions, allSections);
              assembleBtn.style.display = "";
            }
          }
        }, 1500);
      }).catch((e) => {
        secState[sec.id].produceJobRunning = false;
        progressLine.style.display = "none";
        updateBadge("error", "Failed");
        toast(e.message, { kind: "error" });
        buildActions();
      });
    }

    function showSectionVideo(videoWrap, mp4Url, sec, actionsRow, progressLine, updateBadge, buildActions, allSections) {
      videoWrap.style.display = "";
      videoWrap.innerHTML = "";
      if (mp4Url) videoWrap.appendChild(h("video", { controls: "", preload: "metadata", src: mp4Url + "?t=" + Date.now() }));
      actionsRow.innerHTML = "";
      const approveBtn = h("button", { class: "btn primary" }, ["Approve Section"]);
      const redoBtn = h("button", { class: "btn ghost" }, ["↻ Redo with feedback"]);
      actionsRow.appendChild(approveBtn);
      actionsRow.appendChild(redoBtn);
      approveBtn.addEventListener("click", () => {
        updateBadge("done", "Approved");
        actionsRow.innerHTML = "";
      });
      redoBtn.addEventListener("click", () => {
        actionsRow.innerHTML = "";
        const textarea = h("textarea", {
          class: "lab-feedback-input",
          placeholder: "What needs changing? e.g. 'Darker images. VO too fast. Show the cockpit instead.'",
          rows: 3, style: { marginBottom: "10px" },
        });
        const regenBtn = h("button", { class: "btn primary" }, [h("span", { html: icons.sparkle }), h("span", {}, [" Regenerate"])]);
        regenBtn.addEventListener("click", async () => {
          const fb = textarea.value.trim();
          if (!fb) { toast("Write feedback first", { kind: "error" }); return; }
          videoWrap.style.display = "none";
          await api.labProduceSection(session.id, sec.id, fb);
          secState[sec.id].produceJobRunning = true;
          startProduce(sec, actionsRow, progressLine, videoWrap, updateBadge, buildActions, allSections);
        });
        actionsRow.appendChild(textarea);
        actionsRow.appendChild(regenBtn);
      });
    }

    loadSections();
    stepArea.appendChild(panel);
  }

  // ── STEP 5: Voiceover ────────────────────────────────────────────────────
  async function mountVoiceoverStep() {
    if (!session) return;
    const panel = h("div");

    panel.appendChild(h("div", { class: "lab-vo-module-header" }, [
      h("div", { class: "lab-vo-icon" }, ["🎙"]),
      h("div", {}, [
        h("div", { class: "lab-vo-title" }, ["Voiceover Generator"]),
        h("div", { class: "lab-vo-sub" }, ["Generate AI voiceover from your script"]),
      ]),
    ]));

    const scriptPreviewEl = h("div", { class: "lab-vo-script-preview" }, ["Loading script…"]);
    panel.appendChild(scriptPreviewEl);

    const metaEl = h("div", { class: "lab-vo-meta" }, ["…"]);
    panel.appendChild(metaEl);

    const progressEl = h("div", { class: "lab-vo-progress", style: { display: "none" } });
    panel.appendChild(progressEl);

    const playerWrap = h("div", { class: "lab-vo-player-wrap", style: { display: "none" } });
    panel.appendChild(playerWrap);

    const genBtn = h("button", { class: "lab-action-btn lg" }, [
      h("span", { html: icons.sparkle }), h("span", {}, [` Generate Voiceover`]),
    ]);
    panel.appendChild(genBtn);

    const continueBtn = nextBtn("Continue to Visuals →", () => goToStep("visuals"));
    continueBtn.style.display = "none";
    panel.appendChild(continueBtn);

    // Append to DOM immediately so panel is always visible
    stepArea.appendChild(panel);

    // Load script info async
    let sceneCount = 0;
    try {
      const script = await api.labGetScript(session.id);
      const allVO = (script.sections || []).flatMap((s) => s.scenes || []).map((sc) => sc.vo || "").filter(Boolean);
      sceneCount = allVO.length;
      const preview = allVO.slice(0, 3).join(" ").slice(0, 280);
      scriptPreviewEl.textContent = preview || "Script loaded.";
      const wordCount = allVO.join(" ").split(/\s+/).filter(Boolean).length;
      const estimatedMin = wordCount > 0 ? (wordCount / 130).toFixed(1) : "?";
      metaEl.textContent = `${sceneCount} scenes · ~${wordCount} words · ~${estimatedMin} min`;
    } catch (e) {
      scriptPreviewEl.textContent = "Could not load script preview.";
      metaEl.textContent = "";
    }

    // Check if already done
    try {
      const existing = await api.labVoiceoverStatus(session.id);
      if (existing.status === "done" && existing.preview_url) {
        showPlayer(existing);
        updateMeta(existing.word_count, existing.scenes_total);
        genBtn.innerHTML = `<span>${icons.sparkle}</span><span> Regenerate Voiceover</span>`;
        continueBtn.style.display = "";
      } else if (existing.word_count) {
        updateMeta(existing.word_count, existing.scenes_total);
      }
    } catch { /* endpoint may not exist yet */ }

    // Stop button (hidden until a generation is active)
    const stopVoBtn = h("button", { class: "lab-stop-btn", style: { display: "none" } }, ["■ Stop"]);
    panel.insertBefore(stopVoBtn, continueBtn);

    let voPoll = null;

    function resetVoUI(label = "Generate Voiceover") {
      clearInterval(voPoll);
      voPoll = null;
      genBtn.disabled = false;
      genBtn.innerHTML = `<span>${icons.sparkle}</span><span> ${label}</span>`;
      progressEl.style.display = "none";
      stopVoBtn.style.display = "none";
      stopVoBtn.disabled = false;
      stopVoBtn.textContent = "■ Stop";
    }

    stopVoBtn.addEventListener("click", async () => {
      stopVoBtn.disabled = true;
      stopVoBtn.textContent = "Stopping…";
      try { await api.labCancel(session.id); } catch {}
      // poll will detect "cancelled" status and clean up
    });

    genBtn.addEventListener("click", async () => {
      genBtn.disabled = true;
      genBtn.innerHTML = `<span class="spinner-sm"></span><span> Generating…</span>`;
      playerWrap.style.display = "none";
      continueBtn.style.display = "none";
      progressEl.style.display = "";
      progressEl.innerHTML = `<span class="spinner-sm"></span><span>Starting voice generation…</span>`;
      stopVoBtn.style.display = "";
      stopVoBtn.disabled = false;
      stopVoBtn.textContent = "■ Stop";

      try {
        await api.labVoiceover(session.id);
        voPoll = setInterval(async () => {
          if (!outlet.isConnected) { clearInterval(voPoll); return; }
          try {
            const r = await api.labVoiceoverStatus(session.id);
            if (r.scenes_total > 0) {
              progressEl.innerHTML = `<span class="spinner-sm"></span><span>Generating VO: ${r.scenes_done}/${r.scenes_total} scenes</span>`;
            }
            if (r.status === "done") {
              resetVoUI("Regenerate Voiceover");
              showPlayer(r);
              updateMeta(r.word_count, r.scenes_total);
              continueBtn.style.display = "";
            } else if (r.status === "cancelled") {
              resetVoUI("Regenerate Voiceover");
              progressEl.style.display = "";
              progressEl.innerHTML = `<span class="lab-stop-cancelled">⏹ Stopped — ${r.scenes_done || 0} scenes archived. Start fresh below.</span>`;
            } else if (r.status === "error") {
              resetVoUI("Regenerate Voiceover");
              toast(`Voiceover failed: ${r.error}`, { kind: "error" });
            }
          } catch (pollErr) {
            resetVoUI("Generate Voiceover");
            toast(pollErr.message, { kind: "error" });
          }
        }, 1500);
      } catch (e) {
        resetVoUI("Generate Voiceover");
        toast(e.message, { kind: "error" });
      }
    });

    function showPlayer(r) {
      playerWrap.style.display = "";
      playerWrap.innerHTML = "";
      playerWrap.appendChild(h("div", { class: "lab-vo-player-label" }, ["Your Voiceover"]));
      playerWrap.appendChild(h("audio", { controls: "", preload: "metadata", src: r.preview_url + "?t=" + Date.now(), style: { width: "100%" } }));
    }

    function updateMeta(wc, sc) {
      const mins = wc > 0 ? (wc / 130).toFixed(1) : "?";
      metaEl.textContent = `${wc || "?"} words · ${sc || "?"} scenes · ~${mins} min`;
    }
  }

  // ── STEP 6: Visuals ───────────────────────────────────────────────────────
  async function mountVisualsStep() {
    const p = h("div");
    const btn = h("button", { class: "btn primary" }, ["Next"]);
    btn.addEventListener("click", () => goToStep("assembly"));
    p.appendChild(btn);
    stepArea.appendChild(p);
  }


  // ── STEP 7: Assembly ──────────────────────────────────────────────────────
  function mountAssemblyStep() {
    if (!session) return;
    const panel = h("div");

    panel.appendChild(h("div", { class: "lab-vo-module-header", style: { marginBottom: "24px" } }, [
      h("div", { class: "lab-vo-icon" }, ["🎞"]),
      h("div", {}, [
        h("div", { class: "lab-vo-title" }, ["Assembly"]),
        h("div", { class: "lab-vo-sub" }, ["Apply Ken Burns, render sections, assemble final video"]),
      ]),
    ]));

    const sectionList = h("div", { style: { display: "flex", flexDirection: "column", gap: "12px", marginBottom: "24px" } });
    panel.appendChild(sectionList);

    const finalAssembleBtn = h("button", { class: "lab-action-btn lg", style: { display: "none" } }, [
      h("span", { html: icons.sparkle }), h("span", {}, [" Assemble Final Video"]),
    ]);
    const finalProgress = h("div", { class: "lab-vo-progress", style: { display: "none" } });
    panel.appendChild(finalAssembleBtn);
    panel.appendChild(finalProgress);

    const finalPlayerWrap = h("div", { style: { marginTop: "24px" } });
    panel.appendChild(finalPlayerWrap);

    let sections = [];
    const sectionDone = {};

    function checkAllSectionsDone() {
      const allDone = sections.length > 0 && sections.every((s) => sectionDone[s.id]);
      finalAssembleBtn.style.display = allDone ? "" : "none";
    }

    function buildSectionRow(sec) {
      const row = h("div", { class: "lab-produce-section-block" });
      const badge = h("span", { class: "lab-produce-section-badge pending" }, ["Pending"]);
      row.appendChild(h("div", { class: "lab-produce-section-head" }, [
        h("div", { class: "lab-produce-section-title" }, [sec.label || sec.id]),
        badge,
      ]));
      const progress = h("div", { class: "lab-produce-progress-line", style: { display: "none" } });
      row.appendChild(progress);
      const videoWrap = h("div", { class: "lab-section-video-wrap", style: { display: "none" } });
      row.appendChild(videoWrap);

      // Auto-start producing this section
      badge.className = "lab-produce-section-badge producing";
      badge.textContent = "Rendering";
      progress.style.display = "";
      const progressMsg = h("span", {}, []);
      progress.innerHTML = "";
      progress.appendChild(h("span", { class: "spinner-sm" }, []));
      progress.appendChild(progressMsg);
      updateProgressWithDots(progressMsg, "Rendering section");

      api.labProduceSection(session.id, sec.id, null).then(() => {
        const poll = setInterval(async () => {
          if (!outlet.isConnected) { clearInterval(poll); return; }
          const job = await api.labSectionStatus(session.id, sec.id);
          if (job.current) updateProgressWithDots(progressMsg, job.current);
          if (job.status === "done" || job.status === "error") {
            clearInterval(poll);
            progress.style.display = "none";
            if (job.status === "error") {
              badge.className = "lab-produce-section-badge error";
              badge.textContent = "Failed";
              const retryBtn = h("div", { class: "lab-produce-section-actions" }, [
                h("button", { class: "btn ghost", onclick: () => { row.remove(); buildAndStartSection(sec); } }, ["↻ Retry"]),
              ]);
              row.appendChild(retryBtn);
            } else {
              badge.className = "lab-produce-section-badge done";
              badge.textContent = "Done";
              sectionDone[sec.id] = true;
              if (job.mp4_url) {
                videoWrap.style.display = "";
                videoWrap.appendChild(h("video", { controls: "", preload: "metadata", src: job.mp4_url + "?t=" + Date.now() }));
              }
              checkAllSectionsDone();
            }
          }
        }, 1500);
      }).catch((e) => {
        progress.style.display = "none";
        badge.className = "lab-produce-section-badge error";
        badge.textContent = "Error";
        toast(e.message, { kind: "error" });
      });

      return row;
    }

    function buildAndStartSection(sec) {
      const row = buildSectionRow(sec);
      sectionList.appendChild(row);
    }

    // Check if final video already assembled
    api.labAssembleStatus(session.id).then((job) => {
      if (job.status === "done" && job.mp4_url) {
        showFinalPlayer(finalPlayerWrap, job.mp4_url);
        return;
      }
      // Load sections and auto-start
      api.labSections(session.id).then((r) => {
        sections = r.items || [];
        for (const sec of sections) {
          if (sec.mp4_url) {
            // Already produced — show directly
            const badge = h("span", { class: "lab-produce-section-badge done" }, ["Done"]);
            const row = h("div", { class: "lab-produce-section-block" });
            row.appendChild(h("div", { class: "lab-produce-section-head" }, [
              h("div", { class: "lab-produce-section-title" }, [sec.label || sec.id]), badge,
            ]));
            const vw = h("div", { class: "lab-section-video-wrap" });
            vw.appendChild(h("video", { controls: "", preload: "metadata", src: sec.mp4_url }));
            row.appendChild(vw);
            sectionList.appendChild(row);
            sectionDone[sec.id] = true;
          } else {
            buildAndStartSection(sec);
          }
        }
        checkAllSectionsDone();
      }).catch((e) => toast(e.message, { kind: "error" }));
    }).catch((e) => {
      // Assembly status not available — fall back to loading sections
      api.labSections(session.id).then((r) => {
        sections = r.items || [];
        for (const sec of sections) buildAndStartSection(sec);
        checkAllSectionsDone();
      }).catch(() => {});
    });

    finalAssembleBtn.addEventListener("click", async () => {
      finalAssembleBtn.disabled = true;
      finalAssembleBtn.innerHTML = `<span class="spinner-sm"></span><span> Assembling…</span>`;
      finalProgress.style.display = "";
      finalProgress.innerHTML = `<span class="spinner-sm"></span><span>Concatenating sections with FFmpeg…</span>`;
      try {
        await api.labAssemble(session.id);
        const poll = setInterval(async () => {
          if (!outlet.isConnected) { clearInterval(poll); return; }
          const job = await api.labAssembleStatus(session.id);
          if (job.status === "done") {
            clearInterval(poll);
            finalProgress.style.display = "none";
            finalAssembleBtn.style.display = "none";
            showFinalPlayer(finalPlayerWrap, job.mp4_url);
          } else if (job.status === "error") {
            clearInterval(poll);
            finalAssembleBtn.disabled = false;
            finalAssembleBtn.innerHTML = `<span>${icons.sparkle}</span><span> Assemble Final Video</span>`;
            finalProgress.style.display = "none";
            toast(job.error || "Assembly failed", { kind: "error" });
          }
        }, 2000);
      } catch (e) {
        finalAssembleBtn.disabled = false;
        finalProgress.style.display = "none";
        toast(e.message, { kind: "error" });
      }
    });

    stepArea.appendChild(panel);
  }

  function showFinalPlayer(wrap, mp4_url) {
    wrap.innerHTML = "";
    const player = h("div", { class: "lab-final-player" });
    player.appendChild(h("video", { controls: "", preload: "metadata", src: mp4_url }));
    wrap.appendChild(player);
    const row = h("div", { style: { display: "flex", gap: "12px", marginTop: "16px" } });
    row.appendChild(h("a", { class: "btn ghost", href: mp4_url, download: "" }, [
      h("span", { html: icons.download }), h("span", {}, [" Download"]),
    ]));
    row.appendChild(nextBtn("Continue to Thumbnail →", () => goToStep("thumbnail")));
    wrap.appendChild(row);
  }

  // ── Music stub (kept for reference, no longer a tab) ──────────────────────
  function mountMusicStep() {
    const panel = h("div");

    panel.appendChild(h("div", { class: "lab-music-stub" }, [
      h("div", { class: "lab-music-stub-icon" }, ["🎵"]),
      h("div", { class: "lab-music-stub-title" }, ["Music & Sound Design"]),
      h("div", { class: "lab-music-stub-sub" }, [
        "Automatic music bed selection, SFX layering, and audio pacing — coming soon.",
      ]),
      h("span", { class: "lab-soon-badge" }, ["Developing soon"]),
    ]));

    panel.appendChild(nextBtn("Continue to Thumbnail →", async () => {
      if (session) {
        session.step = "music_skipped";
        await api.labSession(session.id); // just ping
      }
      await goToStep("thumbnail");
    }));

    stepArea.appendChild(panel);
  }

  // ── STEP 8: Thumbnail ─────────────────────────────────────────────────────
  async function mountThumbnailStep() {
    if (!session) return;
    const panel = h("div");

    const bp = session.summary || {};
    const defaultChannel = bp.channel || "";

    panel.appendChild(h("p", { class: "lab-hero-instruction" }, [
      `Generating a thumbnail for: "${session.idea || session.yt_title}".`,
    ]));

    // Channel source info
    const channelInfo = h("div", {
      class: "lab-summary-item",
      style: { marginBottom: "20px" },
    }, [
      h("div", { class: "lab-summary-label" }, ["Style reference channel (default)"]),
      h("div", { class: "lab-summary-value" }, [
        defaultChannel ? `@${defaultChannel} (from reversed video)` : "No reference channel detected",
      ]),
    ]);
    panel.appendChild(channelInfo);

    // Override channel picker
    let trackers = [];
    try {
      const r = await api.trackers();
      trackers = r.items || [];
    } catch {}

    let overrideChannel = null;
    if (trackers.length) {
      panel.appendChild(h("div", { class: "lab-summary-label" }, ["Override style channel (optional)"]));
      const picker = channelPicker({
        items: [{ channel_id: "", name: "— Use reversed video's channel" }, ...trackers],
        selected: "",
        onChange: (val) => { overrideChannel = val || null; },
      });
      panel.appendChild(h("div", { style: { marginBottom: "20px" } }, [picker.el]));
    }

    // Variants
    let variants = 1;
    const varRow = h("div", { style: { display: "flex", gap: "8px", marginBottom: "20px" } });
    [1, 2, 4].forEach((n) => {
      const btn = h("button", {
        class: `lab-dur-btn ${n === variants ? "active" : ""}`,
        onclick: () => {
          varRow.querySelectorAll(".lab-dur-btn").forEach((b) => b.classList.remove("active"));
          btn.classList.add("active");
          variants = n;
        },
      }, [`${n} variant${n > 1 ? "s" : ""}`]);
      varRow.appendChild(btn);
    });
    panel.appendChild(h("div", { class: "lab-summary-label" }, ["Variants"]));
    panel.appendChild(varRow);

    const genBtn = h("button", { class: "btn primary" }, [
      h("span", { html: icons.sparkle }),
      h("span", {}, [" Generate Thumbnail"]),
    ]);
    const progressLine = h("div", { class: "lab-progress-panel", style: { display: "none", marginTop: "16px" } });
    const resultsGrid = h("div", { class: "thumb-grid", style: { marginTop: "20px" } });
    panel.appendChild(genBtn);
    panel.appendChild(progressLine);
    panel.appendChild(resultsGrid);

    genBtn.addEventListener("click", async () => {
      genBtn.disabled = true;
      genBtn.innerHTML = `<span class="spinner-sm"></span><span> Generating</span>`;
      progressLine.style.display = "";
      updateProgressWithDots(progressLine, "Analyzing video");
      resultsGrid.innerHTML = "";

      try {
        const { job_id } = await api.labThumbnail(
          session.id,
          overrideChannel || null,
          variants,
        );

        let poll = setInterval(async () => {
          if (!outlet.isConnected) { clearInterval(poll); return; }
          const job = await api.labThumbnailStatus(job_id);
          if (job.current) updateProgressWithDots(progressLine, job.current);
          if (job.variants?.length) {
            resultsGrid.innerHTML = "";
            job.variants.forEach((url) => {
              const img = h("img", {
                src: url,
                style: { width: "100%", borderRadius: "10px", display: "block" },
              });
              const card = h("div", { class: "thumb-card" });
              const dlBtn = h("a", { class: "btn sm ghost", href: url, download: "", style: { marginTop: "8px" } }, [
                h("span", { html: icons.download }),
                h("span", {}, [" Download"]),
              ]);
              card.appendChild(img);
              card.appendChild(dlBtn);
              resultsGrid.appendChild(card);
            });
          }
          if (job.status === "done") {
            clearInterval(poll);
            progressLine.style.display = "none";
            genBtn.disabled = false;
            genBtn.innerHTML = `<span>${icons.sparkle}</span><span> Regenerate</span>`;
          } else if (job.status === "error") {
            clearInterval(poll);
            progressLine.textContent = job.error || "Failed";
            genBtn.disabled = false;
            genBtn.innerHTML = `<span>${icons.sparkle}</span><span> Retry</span>`;
            toast(job.error || "Thumbnail generation failed", { kind: "error" });
          }
        }, 2000);
      } catch (e) {
        genBtn.disabled = false;
        toast(e.message, { kind: "error" });
      }
    });

    stepArea.appendChild(panel);
  }

  // ── Initialise ────────────────────────────────────────────────────────────
  // Check if resuming from explicit state (e.g., from My Videos section)
  if (state?.resumeSessionId) {
    try {
      session = await api.labSession(state.resumeSessionId);
      const uiStep = sessionToUIStep(session.step);
      renderStepBar(uiStep);
      await renderStep(uiStep);
      return function unmount() { /* cleanup */ };
    } catch {
      // Session not found, fall through to reverse step
    }
  }

  // Always start on Reverse step
  renderStepBar("reverse");
  mountReverseStep();

  return function unmount() {
    // cleanup handled by isConnected checks in pollers
  };
}
