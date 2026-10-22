"""
derive_ground_truth.py - re-derive the trip cases' expected values from the data.

    python src/eval/derive_ground_truth.py

The specification asks that every expected value be traceable to the dataset,
never taken from the agent under test. This script is that trace. It does not
import the agent: it re-implements the documented rules on the two sources -
the pinned Open Charge Map snapshot (src/snapshots/ocm_qld.json) and the TMR
Electric Super Highway list - then checks each assess_ev_trip_feasibility case
in tasks.charging.json against what it derives, with the runner's own matching
rules (numbers exact, text by substring).

Refusals and malformed-input cases are rules, not data, so they are skipped.
A disagreement here means either the eval file or this derivation is wrong;
the agent is not consulted to settle it.
"""
from __future__ import annotations

import json
import math
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))
import data  # noqa: E402 - only to read the cached TMR rows

SNAPSHOT = json.loads((ROOT / "src" / "snapshots" / "ocm_qld.json").read_text(encoding="utf-8"))
TMR = [s for s in data.charging_stations() if (s.get("status") or "").strip().lower() == "active"]

# The documented constants, restated rather than imported from the agent.
ROAD_FACTOR, DETOUR_KMH, SAME_SITE_M = 1.3, 60, 300
CONNECTORS = {"CCS2": {"CCS (Type 2)"}, "CHAdeMO": {"CHAdeMO"},
              "Type2": {"Type 2 (Socket Only)", "Type 2 (Tethered Connector)"},
              "Type1": {"Type 1 (J1772)"}}


def great_circle_m(a: tuple, b: tuple) -> int:
    p1, p2 = math.radians(a[0]), math.radians(b[0])
    dp, dl = math.radians(b[0] - a[0]), math.radians(b[1] - a[1])
    x = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return int(round(2 * 6_371_000.0 * math.asin(math.sqrt(x))))


def road_m(a: tuple, b: tuple) -> int:
    return int(round(great_circle_m(a, b) * ROAD_FACTOR))


def candidate_stations() -> list[dict]:
    """Public, in-service OCM sites, flagged where they match a TMR site, plus
    any TMR site OCM does not hold."""
    out, matched = [], set()
    for o in SNAPSHOT["stations"]:
        if not (o["usage"] or "").startswith("Public"):
            continue
        if o["is_operational"] is False or o["status"] == "Temporarily Unavailable":
            continue
        twin = next((i for i, t in enumerate(TMR)
                     if great_circle_m((o["lat"], o["lon"]), (t["lat"], t["lon"])) <= SAME_SITE_M), None)
        if twin is not None:
            matched.add(twin)
        out.append({**o, "is_qesh": twin is not None,
                    "onward_stations": TMR[twin]["onward_stations"] if twin is not None else None})
    for i, t in enumerate(TMR):
        if i not in matched:
            out.append({"name": t["name"], "lat": t["lat"], "lon": t["lon"], "power_kw": None,
                        "connector_types": [], "is_qesh": True, "onward_stations": t["onward_stations"]})
    return out


def derive(a: dict) -> dict:
    """The expected response for one call's arguments, from the data alone."""
    keep = 1 - a.get("safety_margin_pct", 10) / 100
    origin, dest = (a["origin_lat"], a["origin_lon"]), (a["dest_lat"], a["dest_lon"])
    full_km, conn = a.get("full_range_km"), a.get("connector_type")
    cons, vmax = a.get("consumption_kwh_per_100km", 18.0), a.get("vehicle_max_charge_kw")

    trip = road_m(origin, dest)
    rem = int(round(a["remaining_range_km"] * 1000))
    usable = int(round(rem * keep))
    full = int(round(max(full_km or 0.0, a["remaining_range_km"]) * 1000))
    cap = max(30_000, int(round(trip * 0.25)))
    pool = candidate_stations()
    stations = [s for s in pool if conn is None or CONNECTORS[conn] & set(s["connector_types"])]

    stops = []
    if usable < trip:
        for s in stations:
            p = (s["lat"], s["lon"])
            to_s, to_d = road_m(origin, p), road_m(p, dest)
            detour = to_s + to_d - trip
            if to_s > usable or detour > cap:
                continue
            target = to_d / keep if not full_km else min(to_d / keep, full)
            add = int(round(max(0.0, target - (rem - to_s))))
            kwh = add / 1000 * cons / 100
            rate = min(s["power_kw"], vmax) if s["power_kw"] and vmax else s["power_kw"]
            charge = int(round(kwh / rate * 3600)) if rate else None
            stops.append({
                "name": s["name"], "power_kw": s["power_kw"], "charge_rate_kw": rate,
                "is_qesh": s["is_qesh"], "onward_stations": s["onward_stations"],
                "distance_from_origin_m": to_s, "drive_after_stop_m": to_d, "detour_m": detour,
                "range_to_add_m": add, "energy_to_add_kwh": round(kwh, 1), "charging_time_s": charge,
                "added_time_s": int(round(detour / (DETOUR_KMH / 3.6))) + charge if charge is not None else None,
                "completes_trip_after_stop": (to_d <= int(round(full * keep))) if full_km else None,
            })
        stops.sort(key=lambda s: (s["added_time_s"] is None,
                                  s["detour_m"] if s["added_time_s"] is None else s["added_time_s"]))
    verdict = "feasible" if usable >= trip else ("requires_charging" if stops else "infeasible")
    return {
        "feasibility": verdict,
        "trip": {"straight_line_m": great_circle_m(origin, dest), "estimated_road_m": trip,
                 "usable_range_m": usable, "shortfall_m": max(0, trip - usable)},
        "recommended_stops": stops[:max(1, min(a.get("max_results", 3), 5))],
        "stations": {"considered": len(stations), "excluded_by_connector": len(pool) - len(stations)},
    }


def mismatches(expected, derived, path=""):
    """Leaves of `expected` that the derivation contradicts. Keys the derivation
    does not model (sources, reason, data_gaps, the exclusion counts) are skipped."""
    if isinstance(expected, dict):
        return [m for k, v in expected.items() if isinstance(derived, dict) and k in derived
                for m in mismatches(v, derived[k], f"{path}.{k}" if path else k)]
    if isinstance(expected, list):
        if not isinstance(derived, list) or len(derived) < len(expected):
            return [f"{path}: expected {len(expected)} item(s), derived {len(derived or [])}"]
        return [m for i, v in enumerate(expected) for m in mismatches(v, derived[i], f"{path}[{i}]")]
    if isinstance(expected, str):
        return [] if isinstance(derived, str) and expected.lower() in derived.lower() \
            else [f"{path}: expected text {expected!r}, derived {derived!r}"]
    return [] if expected == derived else [f"{path}: expected {expected!r}, derived {derived!r}"]


if __name__ == "__main__":
    cases = json.loads((ROOT / "src" / "eval" / "tasks.charging.json").read_text(encoding="utf-8"))
    print(f"OCM snapshot taken {SNAPSHOT['fetched_at']}, {SNAPSHOT['station_count']} stations; "
          f"TMR list {len(TMR)} active stations\n")
    checked = bad = 0
    for case in cases:
        last = case["tools"][-1]
        if last["name"] != "assess_ev_trip_feasibility" or "status" in case["output"]:
            continue
        checked += 1
        problems = mismatches(case["output"], derive(last["input"]))
        bad += bool(problems)
        print(("OK    " if not problems else "DIFF  ") + case["prompt"][:72])
        for p in problems:
            print("        " + p)
    print(f"\n{checked - bad}/{checked} trip cases agree with the data")
    sys.exit(1 if bad else 0)
