"""Safe zone validation (masterplan §17). Stops text from landing in
YouTube's timestamp overlay or progress bar."""
from __future__ import annotations

from dataclasses import dataclass

# Coordinates assume canonical 1280x720
SAFE_ZONE = {
    "text_area": {"left": 128, "top": 72, "right": 1088, "bottom": 576},
    "danger_zones": {
        "timestamp": {"x_start": 1088, "y_start": 612,
                      "x_end": 1276, "y_end": 716,
                      "label": "YouTube duration overlay"},
        "progress_bar": {"x_start": 0, "y_start": 710,
                         "x_end": 1280, "y_end": 720,
                         "label": "Red watch progress bar"},
    },
}


@dataclass
class SafeZoneCheck:
    safe: bool
    warnings: list[str]
    suggested_bbox: tuple[int, int, int, int] | None


def _overlaps(bbox: tuple[int, int, int, int], zone: dict) -> bool:
    x1, y1, x2, y2 = bbox
    return not (x2 < zone["x_start"] or x1 > zone["x_end"]
                or y2 < zone["y_start"] or y1 > zone["y_end"])


def validate_text_placement(bbox: tuple[int, int, int, int],
                             image_size: tuple[int, int]) -> SafeZoneCheck:
    iw, ih = image_size
    # Scale danger zones if image differs from canonical 1280x720
    sx, sy = iw / 1280, ih / 720
    warnings = []
    for name, z in SAFE_ZONE["danger_zones"].items():
        scaled = {
            "x_start": z["x_start"] * sx, "x_end": z["x_end"] * sx,
            "y_start": z["y_start"] * sy, "y_end": z["y_end"] * sy,
        }
        if _overlaps(bbox, scaled):
            warnings.append(f"Text overlaps {name} ({z['label']})")
    return SafeZoneCheck(safe=not warnings, warnings=warnings, suggested_bbox=None)
