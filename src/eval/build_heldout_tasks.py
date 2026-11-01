"""
build_heldout_tasks.py - a second, held-out question set for the replication.

    python src/eval/build_heldout_tasks.py

The first prompt experiment used the 12 questions in tasks.charging.json, which
were written while the agent was built and seen while the few-shot examples
were written. A replication needs questions that played no part in either.
This script writes 24 new ones to tasks.heldout.json, in the same schema, with
the same mix of question types: places outside the coverage, malformed values,
nearest-charger lookups, and trips that are feasible, need a stop, or cannot
be made. None reuses a trip from the task set or from the few-shot examples
(Brisbane-Surfers Paradise, Brisbane-Noosa, Boonah-Brisbane, Cairns).

Expected values come from the data, never from the agent: places are located
with the kit's own cached Nominatim lookup, trips are derived by
derive_ground_truth.py, and nearest chargers by great-circle distance on the
TMR list, as find_nearest_charger documents. Each case also carries a "label"
- the verdict, the tool the question needs and the values it states - which
run_prompt_experiment.py scores against; run_eval.py ignores it.

Trip ranges are chosen well clear of the feasibility boundary (at least 10% of
the trip either way), so a router that looks a place up under a slightly
different name still has one right verdict. The script refuses to write a set
that breaks that rule.
"""
from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))
import data  # noqa: E402

spec = importlib.util.spec_from_file_location("dg", ROOT / "src" / "eval" / "derive_ground_truth.py")
dg = importlib.util.module_from_spec(spec)
spec.loader.exec_module(dg)

OUT = ROOT / "src" / "eval" / "tasks.heldout.json"
TRIP, NEAREST = "assess_ev_trip_feasibility", "find_nearest_charger"
BOTH = ["Open Charge Map", "Queensland Government"]
MIN_MARGIN = 0.10

# (prompt, kind, places, values the question states)
QUESTIONS = [
    ("Is there a public charger I can use in Darwin city centre?", "place_out", ["Darwin"], {}),
    ("Where can I charge my EV near Adelaide Airport?", "place_out", ["Adelaide Airport"], {}),
    ("Can I get from Ipswich to Sydney on the 300 km of range I have left?", "dest_out",
     ["Ipswich", "Sydney"], {"remaining_range_km": 300}),
    ("I'm in Caboolture with 250 km of range. Can I drive to Canberra?", "dest_out",
     ["Caboolture", "Canberra"], {"remaining_range_km": 250}),
    ("My dashboard shows 0 km of range left. Can I drive from Cleveland to Gatton?", "invalid_range",
     ["Cleveland, Queensland", "Gatton"], {"remaining_range_km": 0}),
    ("My car reports -12 kWh per 100 km thanks to regenerative braking. I have 100 km of range and want to "
     "go from Nambour to Ipswich.", "invalid_consumption",
     ["Nambour", "Ipswich"], {"remaining_range_km": 100, "consumption_kwh_per_100km": -12}),
    ("Where is the closest public EV charger to Ipswich?", "nearest", ["Ipswich"], {}),
    ("I'm in Caloundra. Where's the nearest place to charge my electric car?", "nearest", ["Caloundra"], {}),
    ("Find me the nearest EV charging station to Cleveland, Queensland.", "nearest", ["Cleveland, Queensland"], {}),
    ("I'm in Strathpine with 150 km of range left. Can I reach Coomera without charging?", "trip",
     ["Strathpine", "Coomera"], {"remaining_range_km": 150}),
    ("Redcliffe to Beaudesert with 180 km of range showing. Do I need to stop?", "trip",
     ["Redcliffe, Queensland", "Beaudesert"], {"remaining_range_km": 180}),
    ("I have 200 km left in a car that does 450 km on a full charge. Logan Central to Kilcoy - any need to "
     "charge?", "trip", ["Logan Central", "Kilcoy, Queensland"], {"remaining_range_km": 200, "full_range_km": 450}),
    ("Gatton to Cleveland on 170 km of range: will I make it?", "trip",
     ["Gatton", "Cleveland, Queensland"], {"remaining_range_km": 170}),
    ("I'm leaving Caloundra for Toowoomba with 100 km of range in a car that does 350 km when full. Where "
     "should I charge?", "trip", ["Caloundra", "Toowoomba"], {"remaining_range_km": 100, "full_range_km": 350}),
    ("Nambour to Ipswich with 90 km of range; my car does 400 km on a full battery. Where should I stop?",
     "trip", ["Nambour", "Ipswich"], {"remaining_range_km": 90, "full_range_km": 400}),
    ("Driving from Coolangatta to Caboolture with 110 km of range. Where should I charge?", "trip",
     ["Coolangatta", "Caboolture"], {"remaining_range_km": 110}),
    ("My car has a CCS2 plug and 300 km of full range. I'm in Esk with 120 km left, heading to Coolangatta. "
     "Where should I charge?", "trip", ["Esk, Queensland", "Coolangatta"],
     {"remaining_range_km": 120, "full_range_km": 300, "connector_type": "CCS2"}),
    ("Laidley to Maroochydore with 100 km left. The car charges at 50 kW at most and does 250 km on a full "
     "battery. Where do I stop?", "trip", ["Laidley", "Maroochydore"],
     {"remaining_range_km": 100, "full_range_km": 250, "vehicle_max_charge_kw": 50}),
    ("I drive a CHAdeMO car that charges at up to 50 kW and does 200 km on a full charge. Springfield Central "
     "to Noosa Heads with 90 km left - where should I charge?", "trip", ["Springfield Central", "Noosa Heads"],
     {"remaining_range_km": 90, "full_range_km": 200, "connector_type": "CHAdeMO", "vehicle_max_charge_kw": 50}),
    ("My large SUV uses about 22 kWh per 100 km and does 450 km when full. Maroochydore to Beaudesert with "
     "140 km of range - where should I charge?", "trip", ["Maroochydore", "Beaudesert"],
     {"remaining_range_km": 140, "full_range_km": 450, "consumption_kwh_per_100km": 22}),
    ("Mount Tamborine to Caboolture with only 60 km of range in a car that does 300 km on a full charge. "
     "Can I make it?", "trip", ["Mount Tamborine", "Caboolture"], {"remaining_range_km": 60, "full_range_km": 300}),
    ("I'm in Kilcoy with 15 km of range left and need to get to Logan Central.", "trip",
     ["Kilcoy, Queensland", "Logan Central"], {"remaining_range_km": 15}),
    ("I'm in Kenilworth with 25 km of range left and need to get to Caboolture.", "trip",
     ["Kenilworth, Queensland", "Caboolture"], {"remaining_range_km": 25}),
    ("Crows Nest to Ipswich, but the car only has 20 km of range left.", "trip",
     ["Crows Nest, Queensland", "Ipswich"], {"remaining_range_km": 20}),
]


def locate(place: str) -> tuple[float, float]:
    hit = data.geocode(place)
    if hit is None:
        raise SystemExit(f"no geocode for {place!r}")
    return hit["lat"], hit["lon"]


def trip_args(places, stated) -> dict:
    (olat, olon), (dlat, dlon) = locate(places[0]), locate(places[1])
    return {"origin_lat": olat, "origin_lon": olon, "dest_lat": dlat, "dest_lon": dlon, **stated, "explain": False}


def build(prompt, kind, places, stated) -> dict:
    geo = [{"name": "geocode_place", "input": {"place": p}} for p in places]
    if kind == "place_out":
        return {"prompt": prompt, "tools": geo[:1],
                "output": {"status": "out_of_scope", "reason": "outside South East Queensland"},
                "label": {"verdict": "declined_out_of_scope", "tool": None, "stated": stated}}
    if kind == "dest_out":
        return {"prompt": prompt, "tools": [{"name": TRIP, "input": trip_args(places, stated)}],
                "output": {"status": "out_of_scope", "reason": "destinations in Queensland"},
                "label": {"verdict": "declined_out_of_scope", "tool": None, "stated": stated}}
    if kind in ("invalid_range", "invalid_consumption"):
        reason = "must be a positive number of kilometres" if kind == "invalid_range" else "consumption_kwh_per_100km"
        return {"prompt": prompt, "tools": [{"name": TRIP, "input": trip_args(places, stated)}],
                "output": {"status": "invalid_input", "feasibility": None, "reason": reason},
                "label": {"verdict": "declined_invalid_input", "tool": None, "stated": stated}}
    if kind == "nearest":
        lat, lon = locate(places[0])
        best = min(data.charging_stations(), key=lambda s: dg.great_circle_m((lat, lon), (s["lat"], s["lon"])))
        return {"prompt": prompt,
                "tools": geo + [{"name": NEAREST, "input": {"lat": lat, "lon": lon, "max_results": 1}}],
                "output": {"nearest": [{"name": best["name"],
                                        "distance_m": dg.great_circle_m((lat, lon), (best["lat"], best["lon"]))}],
                           "sources": ["Queensland Government"]},
                "label": {"verdict": "nearest_listed", "tool": NEAREST, "stated": stated}}

    args = trip_args(places, stated)
    d = dg.derive(args)
    road, usable = d["trip"]["estimated_road_m"], d["trip"]["usable_range_m"]
    if abs(usable - road) < MIN_MARGIN * road:
        raise SystemExit(f"too close to the feasibility boundary: {prompt[:60]} (usable {usable}, road {road})")
    out = {"feasibility": d["feasibility"],
           "trip": {k: d["trip"][k] for k in ("estimated_road_m", "usable_range_m", "shortfall_m")},
           "sources": BOTH}
    if d["feasibility"] == "requires_charging":
        top = d["recommended_stops"][0]
        out["recommended_stops"] = [{k: top[k] for k in ("name", "power_kw", "detour_m", "charging_time_s",
                                                         "added_time_s", "completes_trip_after_stop")}]
    elif d["feasibility"] == "infeasible":
        out["reason"] = "No charging station is reachable"
        out["recommended_stops"] = []
    else:
        out["recommended_stops"] = []
    return {"prompt": prompt, "tools": geo + [{"name": TRIP, "input": args}], "output": out,
            "label": {"verdict": d["feasibility"], "tool": TRIP, "stated": stated}}


def main() -> int:
    cases = [build(*q) for q in QUESTIONS]
    OUT.write_text(json.dumps(cases, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    counts = {}
    for c in cases:
        counts[c["label"]["verdict"]] = counts.get(c["label"]["verdict"], 0) + 1
    print(f"wrote {len(cases)} cases to {OUT.relative_to(ROOT)}: {counts}")
    for i, c in enumerate(cases, 1):
        o = c["output"]
        top = (o.get("recommended_stops") or [{}])[0].get("name") or (o.get("nearest") or [{}])[0].get("name") or ""
        print(f"  H{i:<2} {c['label']['verdict']:<24} {top:<36} {c['prompt'][:60]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
