"""Stage 7: fuse motion + vision signals into final production_type per
scene, then roll up to a video-level production_formula."""
from __future__ import annotations

from collections import Counter

# Canonical formula labels used in blueprint.json
FORMULAS = ("ai_animated", "ken_burns", "talking_head", "stock_montage",
            "motion_graphic", "screen_recording", "hybrid")


def _map_vision_to_formula(vision_production: str | None) -> str | None:
    m = {
        "ai_image_animated": "ai_animated",
        "ai_image_static": "ken_burns",
        "live_action": "talking_head",   # refined by face check below
        "stock_footage": "stock_montage",
        "motion_graphic": "motion_graphic",
        "screen_recording": "screen_recording",
    }
    return m.get(vision_production or "")


def fuse_scene(motion: dict, vision: dict | None) -> dict:
    """Produce {production_type, confidence, evidence[]} for one scene."""
    evidence: list[str] = []
    vision = vision or {}
    motion_label = motion.get("label", "unknown")
    vis_formula = _map_vision_to_formula(vision.get("production_type"))
    has_face = bool(vision.get("has_face"))

    # Strong signals
    if motion_label == "ai_animated_warp":
        evidence.append(f"motion residual {motion.get('residual_ratio')} (non-rigid warp)")
        pt = "ai_animated"
        conf = 0.8 if vis_formula == "ai_animated" else 0.65
        if vis_formula == "ai_animated":
            evidence.append("vision agrees: ai_image_animated")
    elif motion_label == "ken_burns":
        evidence.append(f"affine-only motion (residual {motion.get('residual_ratio')})")
        pt = "ai_animated" if vis_formula == "ai_animated" else "ken_burns"
        conf = 0.75
    elif motion_label == "static":
        evidence.append("near-zero motion between frames")
        pt = vis_formula or "ken_burns"
        conf = 0.6
    elif motion_label == "localized_center_motion" and has_face:
        evidence.append("localized motion with face present")
        pt = "talking_head"
        conf = 0.85
    elif motion_label == "real_camera":
        evidence.append("globally consistent flow (real camera)")
        if has_face:
            pt = "talking_head"; conf = 0.75
            evidence.append("face detected")
        else:
            pt = vis_formula or "stock_montage"
            conf = 0.6
    else:
        pt = vis_formula or "hybrid"
        conf = 0.4

    if vision.get("production_evidence"):
        evidence.append(f"vision: {vision['production_evidence']}")

    return {"production_type": pt, "confidence": round(conf, 2),
            "evidence": evidence}


def video_formula(scenes_fused: list[dict]) -> dict:
    """Weighted rollup: dominant formula + mix + evidence."""
    if not scenes_fused:
        return {"primary": "unknown", "confidence": 0.0, "mix": {}, "evidence": []}

    # Weight each scene's vote by confidence × duration
    totals: Counter = Counter()
    weight_sum = 0.0
    for sc in scenes_fused:
        w = float(sc.get("confidence") or 0.5) * max(float(sc.get("duration") or 1.0), 0.1)
        totals[sc["production_type"]] += w
        weight_sum += w

    mix = {k: round(v / weight_sum, 3) for k, v in totals.items()} if weight_sum else {}
    primary = max(mix, key=mix.get) if mix else "unknown"
    primary_share = mix.get(primary, 0.0)
    # Hybrid if no clear winner
    if primary_share < 0.55 and len([v for v in mix.values() if v >= 0.2]) >= 2:
        primary = "hybrid"
        confidence = 0.6
    else:
        confidence = round(min(0.98, primary_share + 0.1), 2)

    # Pick top-3 evidence strings across scenes
    evidence: list[str] = []
    for sc in scenes_fused[:10]:
        for e in sc.get("evidence", [])[:1]:
            if e not in evidence:
                evidence.append(e)
        if len(evidence) >= 6:
            break

    return {"primary": primary, "confidence": confidence, "mix": mix,
            "evidence": evidence}
