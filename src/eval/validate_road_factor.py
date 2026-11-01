"""
validate_road_factor.py - how good is "road distance = straight line x 1.3"?

    python src/eval/validate_road_factor.py

The agent never routes on a road network: it multiplies the great-circle
distance by a fixed road factor of 1.3. This script measures that assumption
against real driving distances. It geocodes a fixed list of South East
Queensland places with the kit's own cached Nominatim lookup (never a recalled
coordinate), asks the public OSRM demo router for the driving distance between
every pair, and reports the observed road-to-straight-line ratio and the error
the fixed factor makes.

Both services are rate-limited and shared, so requests are spaced (Nominatim
through data.geocode's own 1.1 s lock; OSRM at one request per 1.1 s) and
results are cached in the output folder: a re-run only fetches what is missing.

Writes results/road-factor/: pairs.csv (one row per place pair) and summary.md.
Standard library only, apart from the kit's data module.
"""
from __future__ import annotations

import csv
import json
import math
import statistics
import sys
import time
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))
import data  # noqa: E402 - the kit's cached, rate-limited Nominatim lookup

OUT = ROOT / "results" / "road-factor"
OSRM = "https://router.project-osrm.org/route/v1/driving/{a_lon},{a_lat};{b_lon},{b_lat}?overview=false"
ROAD_FACTOR = 1.3                      # the agent's constant, restated
BRISBANE = timezone(timedelta(hours=10))

# Origins and destinations spread across South East Queensland: the city, the
# coasts, the hinterland and the western Darling Downs edge. Every pair is
# measured, so short urban trips and long highway trips are both represented.
PLACES = [
    "University of Queensland St Lucia", "Brisbane City", "Toowoomba", "Ipswich", "Gatton",
    "Surfers Paradise", "Coolangatta", "Beenleigh", "Cleveland, Queensland", "Redcliffe, Queensland",
    "Caboolture", "Caloundra", "Maroochydore", "Noosa Heads", "Nambour", "Kilcoy, Queensland",
    "Esk, Queensland", "Boonah", "Beaudesert", "Springfield Central",
]


def great_circle_m(a: tuple, b: tuple) -> float:
    lat1, lon1, lat2, lon2 = map(math.radians, (*a, *b))
    h = math.sin((lat2 - lat1) / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin((lon2 - lon1) / 2) ** 2
    return 2 * 6_371_008.8 * math.asin(math.sqrt(h))


def osrm_m(a: tuple, b: tuple, cache: dict) -> float | None:
    key = f"{a[0]:.6f},{a[1]:.6f};{b[0]:.6f},{b[1]:.6f}"
    if key not in cache:
        url = OSRM.format(a_lat=a[0], a_lon=a[1], b_lat=b[0], b_lon=b[1])
        req = urllib.request.Request(url, headers={"User-Agent": data.USER_AGENT})
        with urllib.request.urlopen(req, timeout=30) as r:
            body = json.load(r)
        cache[key] = body["routes"][0]["distance"] if body.get("code") == "Ok" else None
        time.sleep(1.1)
    return cache[key]


def pct(values: list[float], q: float) -> float:
    s = sorted(values)
    k = (len(s) - 1) * q
    return s[int(k)] + (s[min(int(k) + 1, len(s) - 1)] - s[int(k)]) * (k - int(k))


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    cache_file = OUT / "osrm_cache.json"
    cache = json.loads(cache_file.read_text(encoding="utf-8")) if cache_file.exists() else {}

    points = {}
    for p in PLACES:
        hit = data.geocode(p)
        if hit is None:
            raise SystemExit(f"no geocode for {p!r}")
        points[p] = (hit["lat"], hit["lon"], hit["matched_name"])

    rows = []
    names = list(points)
    try:
        for i, a in enumerate(names):
            for b in names[i + 1:]:
                pa, pb = points[a][:2], points[b][:2]
                road = osrm_m(pa, pb, cache)
                if road is None:
                    continue
                straight = great_circle_m(pa, pb)
                est = straight * ROAD_FACTOR
                rows.append({"from": a, "to": b, "straight_m": round(straight), "osrm_road_m": round(road),
                             "estimate_m": round(est), "ratio": round(road / straight, 3),
                             "error_pct": round((est - road) / road * 100, 1)})
    finally:
        cache_file.write_text(json.dumps(cache, indent=1), encoding="utf-8")

    with (OUT / "pairs.csv").open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)

    ratios = [r["ratio"] for r in rows]
    errors = [r["error_pct"] for r in rows]
    bands = [("under 30 km", 0, 30_000), ("30-100 km", 30_000, 100_000), ("100 km and over", 100_000, 1e12)]
    lines = [
        "# Road factor validation",
        "",
        f"{len(rows)} place pairs among {len(points)} South East Queensland places, measured "
        f"{datetime.now(BRISBANE):%Y-%m-%d}. Driving distance from the public OSRM demo router "
        "(OpenStreetMap data); straight line is the great-circle distance; the agent's estimate is "
        f"straight line x {ROAD_FACTOR}. Positive error = the agent overestimates the drive.",
        "",
        "| | Observed ratio road / straight | Agent's error |",
        "|---|---|---|",
        f"| Median | {statistics.median(ratios):.3f} | {statistics.median(errors):+.1f}% |",
        f"| Interquartile range | {pct(ratios, .25):.3f} - {pct(ratios, .75):.3f} | "
        f"{pct(errors, .25):+.1f}% to {pct(errors, .75):+.1f}% |",
        f"| Min - max | {min(ratios):.3f} - {max(ratios):.3f} | {min(errors):+.1f}% to {max(errors):+.1f}% |",
        f"| Overestimates (safe side) | | {sum(e > 0 for e in errors)}/{len(errors)} pairs |",
        f"| Within +/-10% | | {sum(abs(e) <= 10 for e in errors)}/{len(errors)} pairs |",
        "",
        "## By straight-line distance",
        "",
        "| Band | Pairs | Median ratio | Median error | Underestimates |",
        "|---|---|---|---|---|",
    ]
    for label, lo, hi in bands:
        sel = [r for r in rows if lo <= r["straight_m"] < hi]
        if sel:
            lines.append(f"| {label} | {len(sel)} | {statistics.median(r['ratio'] for r in sel):.3f} | "
                         f"{statistics.median(r['error_pct'] for r in sel):+.1f}% | "
                         f"{sum(r['error_pct'] < 0 for r in sel)} |")
    worst = sorted(rows, key=lambda r: r["error_pct"])[:5]
    lines += ["", "## Largest underestimates (the unsafe direction)", "",
              "| From | To | Straight km | OSRM road km | Agent km | Error |", "|---|---|---|---|---|---|"]
    lines += [f"| {r['from']} | {r['to']} | {r['straight_m'] / 1000:.1f} | {r['osrm_road_m'] / 1000:.1f} | "
              f"{r['estimate_m'] / 1000:.1f} | {r['error_pct']:+.1f}% |" for r in worst]
    lines += ["", "## Places as geocoded", "", "| Query | Matched | lat | lon |", "|---|---|---|---|"]
    lines += [f"| {p} | {v[2]} | {v[0]:.5f} | {v[1]:.5f} |" for p, v in points.items()]
    text = "\n".join(lines) + "\n"
    (OUT / "summary.md").write_text(text, encoding="utf-8")
    print(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
