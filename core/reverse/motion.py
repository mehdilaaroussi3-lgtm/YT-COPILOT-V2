"""Stage 5: motion signature per scene.

We classify how a scene *moves* — this is the key signal for distinguishing
AI-animated vs Ken Burns vs real camera vs static. Implementation uses
OpenCV optical flow + affine-warp fit between the two keyframes:

  - STATIC           : near-zero flow everywhere
  - KEN_BURNS        : flow fits a global affine transform almost perfectly
                       (scale + translation), no residual internal motion
  - AI_ANIMATED_WARP : significant internal motion with non-rigid residuals
                       after removing any global transform (morphing edges,
                       parallax inconsistent with a real camera)
  - REAL_CAMERA      : consistent flow with a physically plausible global
                       motion (pan/zoom/rotation) AND parallax cues across
                       depth regions
  - TALKING_HEAD     : localized motion centered on a face region
                       (detected separately in vision stage; here we just
                       flag "localized_center_motion" as hint)

These are heuristics — the fusion classifier combines them with Gemini's
vision judgement. Perfect separation isn't required.
"""
from __future__ import annotations

from pathlib import Path

import numpy as np


def _load_gray(path: Path):
    import cv2
    img = cv2.imread(str(path), cv2.IMREAD_COLOR)
    if img is None:
        return None
    return cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)


def signature(frame_a: Path, frame_b: Path) -> dict:
    """Return motion signature stats for one scene."""
    import cv2

    g1 = _load_gray(frame_a)
    g2 = _load_gray(frame_b)
    if g1 is None or g2 is None or g1.shape != g2.shape:
        return {"label": "unknown", "flow_mean": 0.0, "residual_ratio": 0.0,
                "localized": False}

    # Downscale for speed
    h, w = g1.shape
    if max(h, w) > 480:
        scale = 480.0 / max(h, w)
        g1 = cv2.resize(g1, (int(w * scale), int(h * scale)))
        g2 = cv2.resize(g2, (int(w * scale), int(h * scale)))
        h, w = g1.shape

    flow = cv2.calcOpticalFlowFarneback(
        g1, g2, None,
        pyr_scale=0.5, levels=3, winsize=21, iterations=3,
        poly_n=5, poly_sigma=1.2, flags=0,
    )
    fx, fy = flow[..., 0], flow[..., 1]
    mag = np.sqrt(fx * fx + fy * fy)
    flow_mean = float(mag.mean())
    flow_max = float(mag.max())

    # Near-static
    if flow_mean < 0.3 and flow_max < 2.0:
        return {"label": "static", "flow_mean": flow_mean, "residual_ratio": 0.0,
                "localized": False}

    # Fit global affine and compute residual
    ys, xs = np.mgrid[0:h, 0:w]
    pts1 = np.stack([xs.ravel(), ys.ravel()], axis=1).astype(np.float32)
    pts2 = np.stack([(xs + fx).ravel(), (ys + fy).ravel()], axis=1).astype(np.float32)
    # Sample for speed
    if pts1.shape[0] > 4000:
        idx = np.random.default_rng(0).choice(pts1.shape[0], 4000, replace=False)
        pts1_s, pts2_s = pts1[idx], pts2[idx]
    else:
        pts1_s, pts2_s = pts1, pts2

    M, _inliers = cv2.estimateAffinePartial2D(pts1_s, pts2_s, method=cv2.RANSAC,
                                              ransacReprojThreshold=1.5)
    residual_ratio = 1.0
    if M is not None:
        pts1_h = np.hstack([pts1, np.ones((pts1.shape[0], 1), dtype=np.float32)])
        pred = pts1_h @ M.T
        resid = np.linalg.norm(pred - pts2, axis=1)
        # residual energy vs total flow energy
        flow_norm = np.linalg.norm(pts2 - pts1, axis=1).mean() + 1e-6
        residual_ratio = float(resid.mean() / flow_norm)

    # Localized motion check (center vs periphery)
    cy, cx = h // 2, w // 2
    r = min(h, w) // 4
    center_mean = float(mag[cy - r:cy + r, cx - r:cx + r].mean())
    periphery = mag.copy()
    periphery[cy - r:cy + r, cx - r:cx + r] = 0
    periphery_mean = float(periphery.mean())
    localized = center_mean > 1.5 and center_mean > 2.5 * max(periphery_mean, 0.1)

    if residual_ratio < 0.12 and flow_mean > 0.5:
        label = "ken_burns"
    elif residual_ratio > 0.45:
        label = "ai_animated_warp"
    elif localized:
        label = "localized_center_motion"
    else:
        label = "real_camera"

    return {
        "label": label,
        "flow_mean": round(flow_mean, 3),
        "flow_max": round(flow_max, 3),
        "residual_ratio": round(residual_ratio, 3),
        "localized": localized,
    }
