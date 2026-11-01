"""
audit_stations.py - what the agent's station data does and does not hold.

    python src/eval/audit_stations.py

Describes the two station sources exactly as the agent uses them: the pinned
Open Charge Map snapshot (src/snapshots/ocm_qld.json) and the TMR Queensland
Electric Super Highway list. Reports how many sites survive the agent's
filters, what share of each field is filled, how old the records are, how the
power ratings and plug types are spread, and how closely the two sources agree
on the highway sites they share.

Writes results/station-audit/summary.md. Standard library only, apart from the
kit's data module (to read the cached TMR rows).
"""
from __future__ import annotations

import collections
import json
import math
import statistics
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))
import data  # noqa: E402

OUT = ROOT / "results" / "station-audit"
SNAPSHOT = json.loads((ROOT / "src" / "snapshots" / "ocm_qld.json").read_text(encoding="utf-8"))
SAME_SITE_M = 300                       # the agent's twin-matching radius, restated
POWER_BANDS = [("AC slow, under 7.4 kW", 0, 7.4), ("AC, 7.4-22 kW", 7.4, 22.01), ("DC, 22-50 kW", 22.01, 50.01),
               ("DC fast, 50-150 kW", 50.01, 150.01), ("DC ultra-fast, over 150 kW", 150.01, 1e9)]


def great_circle_m(a: tuple, b: tuple) -> float:
    lat1, lon1, lat2, lon2 = map(math.radians, (*a, *b))
    h = math.sin((lat2 - lat1) / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin((lon2 - lon1) / 2) ** 2
    return 2 * 6_371_008.8 * math.asin(math.sqrt(h))


def share(n: int, total: int) -> str:
    return f"{n}/{total} ({n / total:.0%})" if total else "0/0"


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    stations = SNAPSHOT["stations"]
    taken = date.fromisoformat(SNAPSHOT["fetched_at"][:10])
    tmr_all = data.charging_stations()
    tmr = [s for s in tmr_all if (s.get("status") or "").strip().lower() == "active"]

    public = [s for s in stations if (s["usage"] or "").startswith("Public")]
    in_service = [s for s in public if s["is_operational"] is not False and s["status"] != "Temporarily Unavailable"]
    lines = [
        "# Station data audit",
        "",
        f"Open Charge Map snapshot taken {SNAPSHOT['fetched_at']} ({SNAPSHOT['station_count']} sites, open-data "
        f"records only, licence: {SNAPSHOT['licence']}); TMR Electric Super Highway list: {len(tmr_all)} rows, "
        f"{len(tmr)} active.",
        "",
        "## What survives the agent's filters",
        "",
        "| Step | Sites |",
        "|---|---|",
        f"| OCM snapshot | {len(stations)} |",
        f"| Public access (private sites dropped) | {len(public)} |",
        f"| Public and in service (not operational / temporarily unavailable dropped) | {len(in_service)} |",
    ]
    tmr_only = sum(1 for t in tmr if all(great_circle_m((t["lat"], t["lon"]), (o["lat"], o["lon"])) > SAME_SITE_M
                                         for o in in_service))
    lines.append(f"| Plus TMR highway sites with no OCM twin (no power or plug data) | {tmr_only} |")
    lines.append(f"| **Candidate pool for a trip with no plug preference** | **{len(in_service) + tmr_only}** |")

    usage = collections.Counter(s["usage"] or "(blank)" for s in stations)
    status = collections.Counter(s["status"] or "(blank)" for s in stations)
    lines += ["", "## Access and status, all OCM sites", "", "| Usage | Sites |", "|---|---|"]
    lines += [f"| {k} | {v} |" for k, v in usage.most_common()]
    lines += ["", "| Status | Sites |", "|---|---|"]
    lines += [f"| {k} | {v} |" for k, v in status.most_common()]

    fields = ["name", "address", "operator", "power_kw", "connector_types", "last_updated", "status"]
    lines += ["", f"## Fields filled, public in-service sites (n = {len(in_service)})", "",
              "| Field | Filled |", "|---|---|"]
    for f in fields:
        filled = sum(1 for s in in_service if s.get(f) not in (None, "", [], "(Unknown Operator)"))
        lines.append(f"| {f} | {share(filled, len(in_service))} |")

    powers = [s["power_kw"] for s in in_service if s["power_kw"]]
    lines += ["", "## Rated power, public in-service sites", "", "| Band | Sites |", "|---|---|"]
    for label, lo, hi in POWER_BANDS:
        lines.append(f"| {label} | {sum(lo <= p < hi for p in powers)} |")
    lines.append(f"| Not published | {len(in_service) - len(powers)} |")
    if powers:
        lines.append(f"\nMedian rated power {statistics.median(powers):g} kW; maximum {max(powers):g} kW.")

    plugs = collections.Counter(c for s in in_service for c in set(s["connector_types"]))
    lines += ["", "## Plug types offered, public in-service sites", "", "| Plug | Sites offering it |", "|---|---|"]
    lines += [f"| {k} | {share(v, len(in_service))} |" for k, v in plugs.most_common()]

    ages = []
    for s in in_service:
        try:
            ages.append((taken - date.fromisoformat(s["last_updated"][:10])).days / 365.25)
        except (TypeError, ValueError):
            pass
    if ages:
        lines += ["", "## How recently each record was updated (public in-service sites)", "",
                  "| Last updated | Sites |", "|---|---|",
                  f"| Within 1 year | {sum(a <= 1 for a in ages)} |",
                  f"| 1-3 years | {sum(1 < a <= 3 for a in ages)} |",
                  f"| 3-5 years | {sum(3 < a <= 5 for a in ages)} |",
                  f"| Over 5 years | {sum(a > 5 for a in ages)} |",
                  f"\nMedian record age {statistics.median(ages):.1f} years at snapshot time."]

    operators = collections.Counter(s["operator"] or "(blank)" for s in in_service)
    lines += ["", "## Largest operators, public in-service sites", "", "| Operator | Sites |", "|---|---|"]
    lines += [f"| {k} | {v} |" for k, v in operators.most_common(8)]

    # How the two sources agree on the official highway sites.
    nearest = []
    for t in tmr:
        d, o = min(((great_circle_m((t["lat"], t["lon"]), (o["lat"], o["lon"])), o) for o in stations),
                   key=lambda x: x[0])
        nearest.append((t["name"], d, o))
    matched = [n for n in nearest if n[1] <= SAME_SITE_M]
    lines += ["", "## Agreement with the TMR Electric Super Highway list", "",
              f"{len(matched)}/{len(tmr)} active TMR sites have an OCM site within {SAME_SITE_M} m "
              f"(the agent's matching radius); {sum(n[1] <= 150 for n in nearest)}/{len(tmr)} within 150 m. "
              "TMR publishes no plug or power data (its plug column is empty), so OCM supplies both for "
              "matched sites.", "",
              "| TMR site | Nearest OCM site | Distance m | OCM power kW |", "|---|---|---|---|"]
    lines += [f"| {n} | {o['name']} | {d:.0f} | {o['power_kw'] if o['power_kw'] is not None else '-'} |"
              for n, d, o in sorted(nearest, key=lambda x: x[1])]
    lines += ["", "## What no source provides", "",
              "- Live availability (whether a plug is free now): OCM status means 'generally operational'.",
              "- Pricing.",
              "- Per-plug power: OCM gives one rating per site, used for every plug there.",
              "- The vehicle's charging curve: charging is modelled at a constant rate."]
    text = "\n".join(lines) + "\n"
    (OUT / "summary.md").write_text(text, encoding="utf-8")
    print(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
