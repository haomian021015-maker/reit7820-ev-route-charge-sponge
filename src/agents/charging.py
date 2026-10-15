"""
agents/charging.py - your EV Charging Infrastructure agent.

    python agents/charging.py     # serves on :8000

The server wiring is done, and find_nearest_charger is written out as a
worked example. Read it, then build tools of your own.

Import note: use `from mcp.server import MCPServer`. Most tutorials show
`FastMCP`, which is not in the SDK version this course requires.
"""
import math
import os
import sys
from pathlib import Path
from typing import Annotated, Literal

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from mcp.server import MCPServer
from pydantic import Field

import common
import data
import llm                                 # llm.ask() writes prose about your results
from smac import check_identity, guard, haversine_m, in_seq, metres, out_of_scope, respond, seconds

AGENT_NAME = "smac-charging-tripfeasibility"
VERSION = "0.2.0"

check_identity(AGENT_NAME, VERSION)
mcp = MCPServer(name=AGENT_NAME, version=VERSION)

# health and geocode_place come from common.py. geocode_place is optional
# and counts towards your five tools - drop it if your tools take no lat/lon.
common.register(mcp, agent_name=AGENT_NAME, version=VERSION,
                data_sources=[data.OCM_LICENCE, data.QLD_LICENCE])


# Assumptions behind assess_ev_trip_feasibility. They are constants rather than
# parameters on purpose: the Orchestrator should not be choosing them, and they
# are reported back in every response so any number here can be recomputed by
# hand from the dataset.

# Real roads are longer than the great-circle line between two points. v1 applies
# a flat correction instead of consulting a road network; a routing API can
# replace this later without changing the tool's contract.
ROAD_FACTOR = 1.3

# Drivers do not plan to arrive at 0%. This much of the stated range is held back.
DEFAULT_SAFETY_MARGIN_PCT = 10

# A station is only "on the way" if it adds little to the direct line. The cap is
# relative, because 30 km off a 130 km run to Toowoomba is a detour while 30 km
# off a 1,700 km run to Cairns is not, with a floor for short trips.
CORRIDOR_DETOUR_FLOOR_M = 30_000
CORRIDOR_DETOUR_FRACTION = 0.25

# Queensland, generously bounded: Torres Strait in the north, the NSW border in
# the south, the NT border in the west. smac.SEQ_BBOX covers the origin; this
# covers the destination, because the interesting trips leave SEQ.
QLD_BBOX = {"lat_min": -29.20, "lat_max": -9.00, "lon_min": 137.90, "lon_max": 153.60}

# Energy use of a typical mid-size EV. It only turns the range a stop must add
# into kWh, and so into charging time; a caller who knows their car passes theirs.
DEFAULT_CONSUMPTION_KWH_PER_100KM = 18.0

# Speed for the extra distance a detour adds, so detour and charging can be
# compared in one unit (seconds). Detours leave the highway for arterial roads.
DETOUR_SPEED_KMH = 60

# OCM and the TMR list describe the same Super Highway sites from different
# surveys. Within this distance they are one site: the 16 matches statewide lie
# within 150 m, and the nearest non-match is over 4 km away.
SAME_SITE_M = 300

# What a caller can ask for, and the OCM connector titles each matches. OCM's
# "Type I (AS 3112)" is the Australian household socket, not the Type 1 EV plug,
# so it is deliberately absent.
CONNECTORS = {
    "CCS2": ("CCS (Type 2)",),
    "CHAdeMO": ("CHAdeMO",),
    "Type2": ("Type 2 (Socket Only)", "Type 2 (Tethered Connector)"),
    "Type1": ("Type 1 (J1772)",),
}


def in_qld(lat: float, lon: float) -> bool:
    """True if a WGS84 point is inside Queensland."""
    return (
        QLD_BBOX["lat_min"] <= lat <= QLD_BBOX["lat_max"]
        and QLD_BBOX["lon_min"] <= lon <= QLD_BBOX["lon_max"]
    )


def road_m(lat1: float, lon1: float, lat2: float, lon2: float) -> int:
    """Estimated road distance in metres: great-circle distance x ROAD_FACTOR."""
    return metres(haversine_m(lat1, lon1, lat2, lon2) * ROAD_FACTOR)


# YOUR TOOLS: one to five, verb-first snake_case.
#
# The docstring and parameter descriptions are the only things the Orchestrator
# sees when deciding whether to call you, and their quality is graded.
#
# Compute your numbers in code. When you cannot answer, say so in a structured
# response rather than inventing one - how you express that is your design.
# Every response needs sources.
#
# The tool below is written out as a worked example. Read it, then replace it
# with tools of your own - an agent that only serves this one is a copy of the
# starter kit.

@mcp.tool()
@guard
def find_nearest_charger(
    lat: Annotated[float, Field(description="WGS84 latitude of the trip origin, in South East Queensland.")],
    lon: Annotated[float, Field(description="WGS84 longitude of the trip origin, in South East Queensland.")],
    max_results: Annotated[int, Field(description="How many of the closest stations to return, 1 to 5.")] = 3,
) -> dict:
    """Find the closest Queensland Electric Super Highway charging stations to a point.

    Answers range-planning questions for electric vehicle trips starting in South
    East Queensland - where the next public charging site is, how far away, and
    which sites lie onward along the highway network. Uses the Queensland
    Government's published station list, so it covers intercity corridors rather
    than every kerbside charger in a suburb.

    Origin must be in South East Queensland; returned stations may be anywhere in
    Queensland, since onward stations matter on long trips. Plug and connector
    types are NOT available - the source publishes that column empty. Does not
    report live availability or pricing, and does not plan a route.
    """
    # Outside the coverage this agent claims, so it declines rather than
    # answering from data that does not apply.
    if not in_seq(lat, lon):
        return out_of_scope(
            f"This agent covers trips starting in South East Queensland; {lat}, {lon} is outside it.",
            sources=[data.QLD_LICENCE],
        )

    # Every number here is arithmetic on the dataset. Nothing is asked of a model.
    stations = data.charging_stations()
    max_results = max(1, min(int(max_results), 5))
    nearest = sorted(
        ({**s, "distance_m": haversine_m(lat, lon, s["lat"], s["lon"])} for s in stations),
        key=lambda s: s["distance_m"],
    )[:max_results]

    payload = {
        "origin": {"lat": lat, "lon": lon},
        "nearest": nearest,
        "stations_in_dataset": len(stations),
        # What this dataset cannot tell you. The plug column exists but is empty
        # on every row, so reporting it would look like real detail.
        "data_gaps": ["plug_and_connector_types", "live_availability", "pricing"],
    }

    return respond(payload, sources=[data.QLD_LICENCE])


def station_pool() -> tuple[list[dict], dict]:
    """Every station a trip could use, and a count of what was left out and why.

    Open Charge Map supplies the stations, with their power and connectors. The
    TMR list is the cross-check the proposal describes: an OCM record within
    SAME_SITE_M of a TMR site is flagged as part of the state's designated
    corridor and inherits its onward-station note, and a TMR site that OCM does
    not hold is kept, with its power and connectors left unknown rather than
    guessed. Without an OCM snapshot this degrades to the TMR list alone.
    """
    tmr = [s for s in data.charging_stations() if (s.get("status") or "").strip().lower() == "active"]
    snapshot = data.ocm_snapshot()
    info = {"snapshot_taken": snapshot["fetched_at"] if snapshot else None,
            "private": 0, "not_operational": 0}
    pool: list[dict] = []
    matched: set[int] = set()
    for o in (snapshot or {}).get("stations", []):
        # A recommendation the driver cannot use is worse than none.
        if not (o.get("usage") or "").startswith("Public"):
            info["private"] += 1
            continue
        if o.get("is_operational") is False or o.get("status") == "Temporarily Unavailable":
            info["not_operational"] += 1
            continue
        twin = next((i for i, t in enumerate(tmr)
                     if haversine_m(o["lat"], o["lon"], t["lat"], t["lon"]) <= SAME_SITE_M), None)
        if twin is not None:
            matched.add(twin)
        pool.append({**o, "source": "ocm", "is_qesh": twin is not None,
                     "onward_stations": tmr[twin]["onward_stations"] if twin is not None else None})
    for i, t in enumerate(tmr):
        if i not in matched:
            pool.append({"name": t["name"], "lat": t["lat"], "lon": t["lon"], "address": t["address"],
                         "operator": t["host"], "usage": None, "status": t["status"],
                         "power_kw": None, "connector_types": [], "last_updated": None,
                         "source": "tmr", "is_qesh": True, "onward_stations": t["onward_stations"]})
    return pool, info


@mcp.tool()
@guard
def assess_ev_trip_feasibility(
    origin_lat: Annotated[float, Field(description="WGS84 latitude of where the trip starts. Must be in South East Queensland.", examples=[-27.4981423])],
    origin_lon: Annotated[float, Field(description="WGS84 longitude of where the trip starts. Must be in South East Queensland.", examples=[153.0111536])],
    dest_lat: Annotated[float, Field(description="WGS84 latitude of the destination. May be anywhere in Queensland.", examples=[-27.5610193])],
    dest_lon: Annotated[float, Field(description="WGS84 longitude of the destination. May be anywhere in Queensland.", examples=[151.953351])],
    remaining_range_km: Annotated[float, Field(description="Range left in the battery right now, in kilometres, as the vehicle reports it. Must be greater than zero.", examples=[80.0])],
    full_range_km: Annotated[float | None, Field(description="Range in kilometres on a full battery. Optional: the verdict and the recommended stops do not need it. Supply it to learn whether one stop is enough to finish the trip (completes_trip_after_stop), and to cap the charge a stop asks for at a full battery.", examples=[400.0])] = None,
    connector_type: Annotated[Literal["CCS2", "CHAdeMO", "Type2", "Type1"] | None, Field(description="Only recommend chargers that have this connector. Optional; omit it to consider every connector. CCS2 and CHAdeMO are DC fast-charging plugs; Type2 is the AC plug most Australian EVs use.")] = None,
    consumption_kwh_per_100km: Annotated[float, Field(description="The vehicle's energy use in kWh per 100 km, which turns the range a stop must add into energy and so into charging time. Defaults to 18, typical of a mid-size EV.")] = DEFAULT_CONSUMPTION_KWH_PER_100KM,
    vehicle_max_charge_kw: Annotated[float | None, Field(description="The most power the vehicle can accept while charging, in kW. Optional; without it each charger's full rated power is assumed, so charging times are minimums and the most powerful chargers rank first even for a car that cannot use that power.")] = None,
    safety_margin_pct: Annotated[int, Field(description="Percentage of range held back as a reserve rather than planned for, 0 to 50. Defaults to 10.")] = DEFAULT_SAFETY_MARGIN_PCT,
    max_results: Annotated[int, Field(description="How many charging stops to return when the trip needs one, 1 to 5.")] = 3,
    explain: Annotated[bool, Field(description="Include a short written explanation of the verdict alongside the computed figures.")] = True,
) -> dict:
    """Decide whether an electric vehicle can finish a trip on the range it has left, and where to charge if it cannot.

    Takes an origin, a destination and the range remaining in the battery. Estimates
    the road distance, holds back a safety reserve, and returns one of three verdicts:
    `feasible` (drive straight there), `requires_charging` (a stop is needed) or
    `infeasible` (no public charger is reachable on the range left). When a stop is
    needed, public chargers that are reachable and close to the direct line are ranked
    by the time they add to the trip - the detour plus the charging needed to finish -
    and each reports its rated power, connector types, the range and energy to add,
    and whether a full charge there completes the trip. An optional connector type
    limits the stops to chargers the vehicle can use.

    The origin must be in South East Queensland; the destination may be anywhere in
    Queensland. Stations come from a pinned Open Charge Map snapshot of Queensland,
    dated in every response, cross-checked against the Queensland Government's
    Electric Super Highway list, which flags the state's designated corridor sites.

    Takes coordinates, not place names: call `geocode_place` first. Road distance is
    straight-line distance x 1.3, not a routed path. Charging time is a minimum: it
    assumes the charger's rated power, capped at the vehicle's limit if one is given,
    and charging slows past about 80%. Does NOT report live availability or
    occupancy - no open source publishes it, and most station records were last
    verified years ago - nor pricing. Plans a single stop, not a multi-stop itinerary.
    """
    # Malformed input is answered, not crashed on: the handshake test sends some
    # deliberately, and a structured refusal is more useful to the Orchestrator
    # than an exception. Nothing the caller sent is echoed back.
    if not math.isfinite(remaining_range_km) or remaining_range_km <= 0:
        return respond(
            {
                "status": "invalid_input",
                "feasibility": None,
                "reason": "remaining_range_km must be a positive number of kilometres.",
            },
            sources=[data.QLD_LICENCE],
        )
    #SEQ bounding box is checked in smac.in_seq(), so the origin is guaranteed to be in SEQ if that passes.
    if not all(math.isfinite(v) for v in (origin_lat, origin_lon, dest_lat, dest_lon)):
        return respond(
            {
                "status": "invalid_input",
                "feasibility": None,
                "reason": "Origin and destination must be finite WGS84 decimal degrees.",
            },
            sources=[data.QLD_LICENCE],
        )
    if not math.isfinite(consumption_kwh_per_100km) or consumption_kwh_per_100km <= 0:
        return respond(
            {
                "status": "invalid_input",
                "feasibility": None,
                "reason": "consumption_kwh_per_100km must be a positive number.",
            },
            sources=[data.QLD_LICENCE],
        )
    if vehicle_max_charge_kw is not None and (not math.isfinite(vehicle_max_charge_kw) or vehicle_max_charge_kw <= 0):
        return respond(
            {
                "status": "invalid_input",
                "feasibility": None,
                "reason": "vehicle_max_charge_kw must be a positive number of kilowatts when given.",
            },
            sources=[data.QLD_LICENCE],
        )

    # Coverage. The origin bound is what this agent claims to know; the destination
    # bound is how far the station dataset can still support an answer.
    if not in_seq(origin_lat, origin_lon):
        return out_of_scope(
            f"This agent covers trips starting in South East Queensland; {origin_lat}, {origin_lon} is outside it.",
            sources=[data.QLD_LICENCE],
        )
    if not in_qld(dest_lat, dest_lon):
        return out_of_scope(
            f"This agent covers destinations in Queensland; {dest_lat}, {dest_lon} is outside it. "
            "The charging dataset stops at the border, so a trip beyond it cannot be checked.",
            sources=[data.QLD_LICENCE],
        )

    # From here down every number is arithmetic on the dataset and the caller's own
    # figures. Nothing below is asked of a model.
    margin_pct = max(0, min(int(safety_margin_pct), 50))
    keep = 1 - margin_pct / 100
    max_results = max(1, min(int(max_results), 5))

    straight_line_m = haversine_m(origin_lat, origin_lon, dest_lat, dest_lon)
    trip_road_m = metres(straight_line_m * ROAD_FACTOR)
    remaining_m = metres(remaining_range_km * 1000)
    usable_m = metres(remaining_m * keep)

    # A battery cannot be charged past full, so a full range below the range reported
    # as remaining is a contradiction; take the larger of the two rather than refuse.
    full_m = metres(max(full_range_km or 0.0, remaining_range_km) * 1000)
    usable_full_m = metres(full_m * keep)

    detour_cap_m = max(CORRIDOR_DETOUR_FLOOR_M, metres(trip_road_m * CORRIDOR_DETOUR_FRACTION))

    pool, pool_info = station_pool()
    # A site whose connectors are unpublished cannot be shown to fit, so a
    # connector preference excludes it rather than assuming it does.
    wanted = set(CONNECTORS[connector_type]) if connector_type else None
    stations = [s for s in pool if wanted is None or wanted & set(s["connector_types"])]

    feasibility = "feasible" if usable_m >= trip_road_m else "requires_charging"
    shortfall_m = max(0, trip_road_m - usable_m)

    stops: list[dict] = []
    unreachable = off_corridor = 0
    if feasibility == "requires_charging":
        for station in stations:
            to_station_m = road_m(origin_lat, origin_lon, station["lat"], station["lon"])
            to_dest_m = road_m(station["lat"], station["lon"], dest_lat, dest_lon)
            detour_m = to_station_m + to_dest_m - trip_road_m
            # Two independent reasons to drop a station, counted separately so the
            # refusal below can say which constraint actually bit.
            if to_station_m > usable_m:
                unreachable += 1
                continue
            if detour_m > detour_cap_m:
                off_corridor += 1
                continue

            # How much charge this stop must add. The battery arrives holding its
            # actual range less the leg just driven, and must leave with enough to
            # finish with the reserve still held back - never more than a full battery.
            arrival_m = remaining_m - to_station_m
            target_m = to_dest_m / keep
            if full_range_km:
                target_m = min(target_m, full_m)
            range_to_add_m = metres(max(0.0, target_m - arrival_m))
            energy_kwh = range_to_add_m / 1000 * consumption_kwh_per_100km / 100
            power = station["power_kw"]
            # The car charges no faster than the slower of charger and vehicle.
            rate = min(power, vehicle_max_charge_kw) if power and vehicle_max_charge_kw else power
            # No published rating, no charging time: a guessed one would rank it.
            charging_s = seconds(energy_kwh / rate * 3600) if rate else None
            detour_s = seconds(detour_m / (DETOUR_SPEED_KMH / 3.6))
            stops.append({
                "name": station["name"],
                "lat": station["lat"],
                "lon": station["lon"],
                "address": station["address"],
                "operator": station["operator"],
                "access": station["usage"],
                "power_kw": power,
                "charge_rate_kw": rate,
                "connector_types": station["connector_types"],
                "is_qesh": station["is_qesh"],
                "last_updated": station["last_updated"],
                "distance_from_origin_m": to_station_m,
                # Distance still to drive after the stop - not charge left on arrival.
                "drive_after_stop_m": to_dest_m,
                "detour_m": detour_m,
                "range_to_add_m": range_to_add_m,
                "energy_to_add_kwh": round(energy_kwh, 1),
                "charging_time_s": charging_s,
                "added_time_s": detour_s + charging_s if charging_s is not None else None,
                # None, not a guess, when the caller did not say how big the battery is.
                "completes_trip_after_stop": (to_dest_m <= usable_full_m) if full_range_km else None,
                "onward_stations": station["onward_stations"],
                "source": station["source"],
            })
        # Least added time first: the stop that costs the driver the least. A site
        # without a published rating cannot be timed, so it follows those that can,
        # in order of detour, rather than being given a guessed rating.
        stops.sort(key=lambda s: (s["added_time_s"] is None,
                                  s["detour_m"] if s["added_time_s"] is None else s["added_time_s"]))
        stops = stops[:max_results]
        if not stops:
            feasibility = "infeasible"

    have_ocm = pool_info["snapshot_taken"] is not None
    assumptions = [
        f"Road distance is estimated as straight-line distance x {ROAD_FACTOR}; no road network is consulted.",
        f"{margin_pct}% of the stated range is held back as a reserve and not planned for.",
        "A station is recommended only if it is public, not marked out of service, reachable on the "
        f"range remaining, and adds at most {detour_cap_m / 1000:.0f} km to the direct line.",
        f"Stops are ranked by the time they add: the detour at {DETOUR_SPEED_KMH} km/h plus the time "
        "to charge enough to finish with the reserve intact.",
        f"Charging time uses {consumption_kwh_per_100km:g} kWh per 100 km and "
        + (f"the lower of each charger's rated power and the vehicle's {vehicle_max_charge_kw:g} kW. "
           if vehicle_max_charge_kw else "each charger's full rated power. ")
        + "It is a minimum: charging slows past about 80%, and real sessions rarely hold peak power.",
    ]
    if have_ocm:
        assumptions.append(
            f"Stations come from an Open Charge Map snapshot taken {pool_info['snapshot_taken'][:10]}; "
            "each stop's last_updated shows how old its record is.")
    if connector_type:
        assumptions.append(f"Only chargers listing a {connector_type} connector are considered; "
                           "sites whose connectors are unpublished are left out.")

    # What no source here can tell you. Without the OCM snapshot, connectors, power
    # and charging time join the list, since the TMR list publishes none of them.
    data_gaps = ["live_availability", "pricing", "road_network_routing"]
    if not vehicle_max_charge_kw:
        data_gaps.append("vehicle_charge_rate_limit")
    if not have_ocm:
        data_gaps = ["plug_and_connector_types", "charging_speed_kw", "estimated_charging_time"] + data_gaps

    payload = {
        "origin": {"lat": origin_lat, "lon": origin_lon},
        "destination": {"lat": dest_lat, "lon": dest_lon},
        "feasibility": feasibility,
        "trip": {
            "straight_line_m": straight_line_m,
            "estimated_road_m": trip_road_m,
            "road_factor": ROAD_FACTOR,
            "remaining_range_m": remaining_m,
            "usable_range_m": usable_m,
            "safety_margin_pct": margin_pct,
            "shortfall_m": shortfall_m,
            "corridor_detour_cap_m": detour_cap_m,
        },
        "recommended_stops": stops,
        "stations": {
            "considered": len(stations),
            "excluded_private": pool_info["private"],
            "excluded_not_operational": pool_info["not_operational"],
            "excluded_by_connector": len(pool) - len(stations),
            "ocm_snapshot_taken": pool_info["snapshot_taken"],
        },
        # Stated, not hidden: every figure above can be recomputed from these.
        "assumptions": assumptions,
        "data_gaps": data_gaps,
    }

    if feasibility == "infeasible":
        payload["reason"] = (
            f"No charging station is reachable within the {usable_m / 1000:.1f} km of usable range: "
            f"{unreachable} station(s) are too far to reach"
            + (f", and {off_corridor} reachable one(s) are more than "
               f"{detour_cap_m / 1000:.0f} km off the direct line" if off_corridor else "")
            + (f", among the {len(stations)} with a {connector_type} connector." if connector_type else ".")
        )

    # The model only writes prose about numbers already computed above, and is told
    # plainly which fields do not exist so it cannot fill them in.
    if explain:
        first = stops[0] if stops else None
        facts = [
            f"Verdict: {feasibility}.",
            f"Estimated road distance {trip_road_m / 1000:.0f} km (straight line x {ROAD_FACTOR}); "
            f"usable range {usable_m / 1000:.0f} km after holding back {margin_pct}%.",
        ]
        if shortfall_m:
            facts.append(f"Short by {shortfall_m / 1000:.0f} km.")
        if first:
            minutes = (f"at least {round(first['charging_time_s'] / 60)} minutes of charging"
                       if first["charging_time_s"] is not None else "charging time unknown (power unpublished)")
            facts.append(
                f"Best stop: {first['name']}, {first['address']}, {first['distance_from_origin_m'] / 1000:.0f} km "
                f"from the start, adding a {first['detour_m'] / 1000:.0f} km detour. "
                f"Charger rated {first['power_kw'] or 'unpublished'} kW"
                + (f", charging at {first['charge_rate_kw']:g} kW for this vehicle"
                   if first["charge_rate_kw"] and first["charge_rate_kw"] != first["power_kw"] else "")
                + ", connectors "
                f"{', '.join(first['connector_types']) or 'unpublished'}, access {first['access'] or 'unpublished'}. "
                f"Add {first['range_to_add_m'] / 1000:.0f} km of range ({first['energy_to_add_kwh']} kWh), {minutes}. "
                f"After the stop, {first['drive_after_stop_m'] / 1000:.0f} km remain to drive."
            )
        if feasibility == "infeasible":
            facts.append(payload["reason"])
        facts.append("Live availability and pricing are not published.")
        try:
            payload["explanation"] = llm.ask(
                system=(
                    "You explain electric vehicle range results to drivers in Queensland. "
                    "Use only the facts you are given; every figure has already been calculated. "
                    "'km remain to drive' is distance still to travel, not charge left in the battery. "
                    "Charging times are minimums. Never invent live availability, prices or any detail "
                    "you were not given; say so if it matters. At most four sentences."
                ),
                user=" ".join(facts),
            )
        except Exception as exc:  # noqa: BLE001
            # llm.ask() raises when a key is present but rejected. Every figure above
            # is already computed, so only the commentary is lost - report the fault
            # in the response rather than failing the whole call.
            payload["explanation"] = None
            payload["explanation_error"] = f"{type(exc).__name__}: {exc}"

    sources = [data.OCM_LICENCE, data.QLD_LICENCE] if have_ocm else [data.QLD_LICENCE]
    return respond(payload, sources=sources)

# TODO: add your remaining tools here, up to five including geocode_place.


if __name__ == "__main__":
    # 127.0.0.1 on your UQCloud zone. Docker sets HOST=0.0.0.0 so the port reaches your laptop.
    mcp.run(transport="streamable-http", host=os.environ.get("HOST", "127.0.0.1"),
            port=int(os.environ.get("PORT", "8000")))
