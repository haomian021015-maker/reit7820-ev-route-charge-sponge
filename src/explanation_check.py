"""
explanation_check.py - does a written explanation apply the road factor twice?

The tool's estimated_road_m already includes road_factor. A model writing about that
figure sometimes multiplies it again, so a road distance of 100 km appears as 130 km.

The agent uses doubled() to refuse such an explanation; eval/check_explanations.py
uses it to count them in saved runs. It is a pattern match, so a wrong figure stated
in some other way (rounded to "about 160 km", say) passes it.
"""
from __future__ import annotations

import re

KM = re.compile(r"(\d[\d,]*(?:\.\d+)?)\s*(?:km|kilomet)")


def distances(text: str) -> list[float]:
    """Every distance stated in the text, in kilometres."""
    return [float(value.replace(",", "")) for value in KM.findall(text)]


def doubled(text: str, result: dict) -> float | None:
    """The twice-factored distance, if the text states it and no true figure explains it."""
    trip = result["trip"]
    wrong = trip["estimated_road_m"] / 1000 * trip["road_factor"]
    true = [trip[k] / 1000 for k in ("estimated_road_m", "straight_line_m", "remaining_range_m", "usable_range_m",
                                     "shortfall_m")]
    for stop in result.get("recommended_stops") or []:
        true += [stop[k] / 1000 for k in ("distance_from_origin_m", "drive_after_stop_m", "detour_m", "range_to_add_m")]
    for value in distances(text):
        if abs(value - wrong) <= 1 and not any(abs(value - t) <= 0.6 for t in true):
            return wrong
    return None
