"""
sensitivity_analysis.py - how much do the agent's answers depend on its assumptions?

    python src/eval/sensitivity_analysis.py      (after validate_road_factor.py)

The agent answers from four fixed assumptions: road distance = straight line x
1.3, a 10% range reserve, 18 kWh per 100 km when the driver gives no figure,
and stops ranked by the time they add. This script asks three questions of a
grid of trips between the South East Queensland places measured by
validate_road_factor.py, with remaining ranges from 30% to 120% of each trip:

1. Assumptions - if a constant were different, would the verdict or the first
   recommended stop change?
2. Real roads - judged against the OSRM driving distance, how often would the
   agent call a trip feasible that is not (the unsafe error), and how often the
   reverse (the cautious one)?
3. Ranking rule - against simple alternatives (nearest station, least detour,
   most powerful charger), how much time does ranking by time added save?

The derivation is src/eval/derive_ground_truth.py - the independent
re-implementation of the agent's rules - so the agent itself is not called.
Writes results/sensitivity/summary.md and trips.csv. Standard library only.
"""
from __future__ import annotations

import csv
import importlib.util
import statistics
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))
import data  # noqa: E402

spec = importlib.util.spec_from_file_location("dg", ROOT / "src" / "eval" / "derive_ground_truth.py")
dg = importlib.util.module_from_spec(spec)
spec.loader.exec_module(dg)

OUT = ROOT / "results" / "sensitivity"
PAIRS = ROOT / "results" / "road-factor" / "pairs.csv"
FRACTIONS = (0.3, 0.5, 0.7, 0.9, 1.2)    # remaining range as a share of the estimated road distance
FULL_KM = 400
MIN_STRAIGHT_M = 30_000                 # shorter trips rarely need a stop


def run(args: dict, factor: float) -> dict:
    dg.ROAD_FACTOR = factor
    try:
        return dg.derive(args, every_stop=True)
    finally:
        dg.ROAD_FACTOR = 1.3


def first(result: dict) -> str | None:
    stops = result["recommended_stops"]
    return stops[0]["name"] if stops else None


def main() -> int:
    if not PAIRS.exists():
        raise SystemExit("Run src/eval/validate_road_factor.py first: this analysis uses its place pairs.")
    OUT.mkdir(parents=True, exist_ok=True)
    pairs = list(csv.DictReader(PAIRS.open(encoding="utf-8")))
    ratios = sorted(float(p["ratio"]) for p in pairs)
    observed = round(statistics.median(ratios), 2)
    q1, q3 = ratios[len(ratios) // 4], ratios[(3 * len(ratios)) // 4]
    coords = {}
    for p in pairs:
        for name in (p["from"], p["to"]):
            if name not in coords:
                hit = data.geocode(name)
                coords[name] = (hit["lat"], hit["lon"])

    trips = []
    for p in pairs:
        if int(p["straight_m"]) < MIN_STRAIGHT_M:
            continue
        est_km = int(p["estimate_m"]) / 1000
        for f in FRACTIONS:
            o, d = coords[p["from"]], coords[p["to"]]
            trips.append({"from": p["from"], "to": p["to"], "osrm_road_m": int(p["osrm_road_m"]),
                          "args": {"origin_lat": o[0], "origin_lon": o[1], "dest_lat": d[0], "dest_lon": d[1],
                                   "remaining_range_km": round(est_km * f, 1), "full_range_km": FULL_KM}})

    base = [run(t["args"], 1.3) for t in trips]
    verdicts = [b["feasibility"] for b in base]
    lines = ["# Sensitivity of the agent's answers to its assumptions", "",
             f"{len(trips)} trips: {len(trips) // len(FRACTIONS)} place pairs at least "
             f"{MIN_STRAIGHT_M // 1000} km apart (straight line), each with a remaining range of "
             f"{', '.join(f'{int(f * 100)}%' for f in FRACTIONS)} of the agent's road estimate; "
             f"full range {FULL_KM} km. Baseline verdicts: "
             + ", ".join(f"{v} {verdicts.count(v)}" for v in ("feasible", "requires_charging", "infeasible")) + ".",
             "", "## 1. If an assumption were different", "",
             "| Change from the baseline | Same verdict | Same first stop (trips needing one in both) |",
             "|---|---|---|"]
    scenarios = [
        (f"Road factor {observed} (observed median, OSRM)", observed, {}),
        (f"Road factor {q1} (observed lower quartile)", q1, {}),
        (f"Road factor {q3} (observed upper quartile)", q3, {}),
        ("Consumption 15 kWh/100 km (efficient car)", 1.3, {"consumption_kwh_per_100km": 15}),
        ("Consumption 22 kWh/100 km (large SUV)", 1.3, {"consumption_kwh_per_100km": 22}),
        ("No range reserve (0%)", 1.3, {"safety_margin_pct": 0}),
        ("Range reserve 20%", 1.3, {"safety_margin_pct": 20}),
        ("Car limited to 50 kW charging", 1.3, {"vehicle_max_charge_kw": 50}),
    ]
    for label, factor, extra in scenarios:
        alt = [run({**t["args"], **extra}, factor) for t in trips]
        same_v = sum(a["feasibility"] == b["feasibility"] for a, b in zip(alt, base))
        both = [(a, b) for a, b in zip(alt, base) if first(a) and first(b)]
        same_s = sum(first(a) == first(b) for a, b in both)
        lines.append(f"| {label} | {same_v}/{len(trips)} ({same_v / len(trips):.0%}) | "
                     f"{same_s}/{len(both)} ({same_s / len(both):.0%}) |" if both else f"| {label} | "
                     f"{same_v}/{len(trips)} | - |")

    # 2. Verdicts against real driving distances: only the trip itself is re-measured, so this
    # tests the 'can I make it without charging' decision.
    unsafe = cautious = agree = 0
    examples = []
    for t, b in zip(trips, base):
        usable = b["trip"]["usable_range_m"]
        says_ok, really_ok = b["feasibility"] == "feasible", usable >= t["osrm_road_m"]
        if says_ok and not really_ok:
            unsafe += 1
            examples.append(t)
        elif really_ok and not says_ok:
            cautious += 1
        else:
            agree += 1
    lines += ["", "## 2. 'Can I make it without charging?' against real driving distance", "",
              "Each trip's verdict compared with the same reserve applied to the OSRM driving distance.", "",
              "| Outcome | Trips |", "|---|---|",
              f"| Agrees with the real-road verdict | {agree} |",
              f"| Says a stop is needed, real road says not (cautious) | {cautious} |",
              f"| Says feasible, real road says not (unsafe) | {unsafe} |"]
    said_ok = sum(b["feasibility"] == "feasible" for b in base)
    lines += ["", f"Of the {said_ok} trips the agent calls feasible, {unsafe} ({unsafe / said_ok:.0%}) are not "
              "feasible by the real road with the same reserve. In this grid a feasible verdict always has "
              f"{(max(FRACTIONS) * 0.9 - 1) * 100:.0f}% to spare on the agent's own estimate, so the share depends "
              "on that margin; the routes involved are the ones the road factor underestimates (see "
              "results/road-factor)."]
    if examples:
        lines += ["", "Unsafe cases: " + "; ".join(f"{e['from']} to {e['to']} at "
                                                   f"{e['args']['remaining_range_km']} km" for e in examples)]

    # 3. Ranking rule against simple alternatives, on the baseline trips that need a stop.
    rules = {
        "Nearest to the origin": lambda s: (s["distance_from_origin_m"],),
        "Least detour": lambda s: (s["detour_m"],),
        "Most powerful charger": lambda s: (-(s["power_kw"] or 0), s["detour_m"]),
    }
    need = [b for b in base if b["feasibility"] == "requires_charging"
            and all(s["added_time_s"] is not None for s in b["recommended_stops"][:1])]
    lines += ["", "## 3. Ranking by time added against simple alternatives", "",
              f"{len(need)} trips that need a stop. Extra time = time the alternative's pick adds minus the "
              "time the agent's pick adds, both under the agent's own time model (detour at 60 km/h plus "
              "charging at the charger's rated power).", "",
              "| Alternative rule | Picks the same stop | Median extra minutes | 90th percentile | Maximum |",
              "|---|---|---|---|---|"]
    for label, key in rules.items():
        extra, same = [], 0
        for b in need:
            stops = [s for s in b["recommended_stops"] if s["added_time_s"] is not None]
            best, alt = stops[0], min(stops, key=key)
            same += alt["name"] == best["name"]
            extra.append((alt["added_time_s"] - best["added_time_s"]) / 60)
        extra.sort()
        lines.append(f"| {label} | {same}/{len(need)} ({same / len(need):.0%}) | {statistics.median(extra):.1f} | "
                     f"{extra[int(0.9 * (len(extra) - 1))]:.1f} | {max(extra):.1f} |")

    with (OUT / "trips.csv").open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["from", "to", "remaining_range_km", "estimated_road_m", "osrm_road_m", "verdict", "first_stop"])
        for t, b in zip(trips, base):
            w.writerow([t["from"], t["to"], t["args"]["remaining_range_km"], b["trip"]["estimated_road_m"],
                        t["osrm_road_m"], b["feasibility"], first(b) or ""])
    text = "\n".join(lines) + "\n"
    (OUT / "summary.md").write_text(text, encoding="utf-8")
    print(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
