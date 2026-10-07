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
from typing import Annotated

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from mcp.server import MCPServer
from pydantic import Field

import common
import data
import llm                                 # llm.ask() writes prose about your results
from smac import check_identity, guard, haversine_m, in_seq, metres, out_of_scope, respond

AGENT_NAME = "smac-charging-tripfeasibility"
VERSION = "0.1.0"

check_identity(AGENT_NAME, VERSION)
mcp = MCPServer(name=AGENT_NAME, version=VERSION)

# health and geocode_place come from common.py. geocode_place is optional
# and counts towards your five tools - drop it if your tools take no lat/lon.
common.register(mcp, agent_name=AGENT_NAME, version=VERSION,
                data_sources=[data.QLD_LICENCE])


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
    explain: Annotated[bool, Field(description="Include short written range-planning advice.")] = True,
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

    # The model only writes prose about numbers already computed above, and is
    # told plainly which fields do not exist so it cannot fill them in.
    if explain and nearest:
        closest = nearest[0]
        payload["advice"] = llm.ask(
            system=(
                "You advise electric vehicle drivers on range planning in Queensland. "
                "Use only the facts you are given. Never invent plug types, prices or "
                "availability; if something is missing, say it is not published. "
                "At most three sentences."
            ),
            user=(
                f"Closest station: {closest['name']}, {closest['distance_m'] / 1000:.1f} km away, "
                f"at {closest['address']}. Host: {closest['host']}. Status: {closest['status']}. "
                f"Onward from there: {closest['onward_stations'] or 'not published'}. "
                "Plug types, live availability and pricing are not published."
            ),
        )

    return respond(payload, sources=[data.QLD_LICENCE])


@mcp.tool()
@guard
def assess_ev_trip_feasibility(
    origin_lat: Annotated[float, Field(description="WGS84 latitude of where the trip starts. Must be in South East Queensland.")],
    origin_lon: Annotated[float, Field(description="WGS84 longitude of where the trip starts. Must be in South East Queensland.")],
    dest_lat: Annotated[float, Field(description="WGS84 latitude of the destination. May be anywhere in Queensland.")],
    dest_lon: Annotated[float, Field(description="WGS84 longitude of the destination. May be anywhere in Queensland.")],
    remaining_range_km: Annotated[float, Field(description="Range left in the battery right now, in kilometres, as the vehicle reports it. Must be greater than zero.")],
    full_range_km: Annotated[float | None, Field(description="Range in kilometres on a full battery. Optional; supply it to learn whether one charging stop is enough to finish the trip.")] = None,
    safety_margin_pct: Annotated[int, Field(description="Percentage of range held back as a reserve rather than planned for, 0 to 50. Defaults to 10.")] = DEFAULT_SAFETY_MARGIN_PCT,
    max_results: Annotated[int, Field(description="How many charging stops to return when the trip needs one, 1 to 5.")] = 3,
    explain: Annotated[bool, Field(description="Include a short written explanation of the verdict alongside the computed figures.")] = True,
) -> dict:
    """Decide whether an electric vehicle can finish a trip on the range it has left, and where to charge if it cannot.

    Takes an origin, a destination and the range remaining in the battery. Estimates
    the road distance, subtracts a safety reserve, and returns one of three verdicts:
    `feasible` (drive straight there), `requires_charging` (a stop is needed, with
    Queensland Electric Super Highway stations ranked by how little they add to the
    direct line) or `infeasible` (no station is reachable on the range left). Each
    recommended stop reports how far it is, the detour it adds, and whether a full
    charge there would complete the trip.

    The origin must be in South East Queensland; the destination may be anywhere in
    Queensland, because the trips worth asking about leave SEQ. Stations come from the
    Queensland Government's published list, re-fetched at most every six hours, so this
    covers intercity highway corridors and not kerbside chargers in a suburb.

    Takes coordinates, not place names: call `geocode_place` first. Road distance is
    estimated as straight-line distance x 1.3, not routed over a road network, so it is
    an approximation rather than a driving route. Does NOT report plug or connector
    types, charging speed, charging time, live availability or pricing - the source
    publishes none of them. Plans a single stop, not a multi-stop itinerary.
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

    # Decommissioned sites are excluded rather than recommended. Every row is Active
    # today; `stations_considered` in the response makes it visible if that changes.
    stations = [s for s in data.charging_stations()
                if (s.get("status") or "").strip().lower() == "active"]

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
            stops.append({
                "name": station["name"],
                "lat": station["lat"],
                "lon": station["lon"],
                "address": station["address"],
                "host": station["host"],
                "status": station["status"],
                "distance_from_origin_m": to_station_m,
                "distance_to_destination_m": to_dest_m,
                "detour_m": detour_m,
                # None, not a guess, when the caller did not say how big the battery is.
                "completes_trip_after_stop": (to_dest_m <= usable_full_m) if full_range_km else None,
                "onward_stations": station["onward_stations"],
            })
        # Least detour first: the station that costs the driver the least to use.
        stops = sorted(stops, key=lambda s: s["detour_m"])[:max_results]
        if not stops:
            feasibility = "infeasible"

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
        "stations_considered": len(stations),
        # Stated, not hidden: every figure above can be recomputed from these.
        "assumptions": [
            f"Road distance is estimated as straight-line distance x {ROAD_FACTOR}; no road network is consulted.",
            f"{margin_pct}% of the stated range is held back as a reserve and not planned for.",
            f"A station is recommended only if it can be reached on the range remaining and adds at most "
            f"{detour_cap_m / 1000:.0f} km to the direct line.",
            "Only stations published as Active are considered; live availability is not published.",
        ],
        # What this dataset cannot tell you. Charging time in particular: the source
        # publishes no connector or power column, so any duration would be invented.
        "data_gaps": [
            "plug_and_connector_types",
            "charging_speed_kw",
            "estimated_charging_time",
            "live_availability",
            "pricing",
            "road_network_routing",
        ],
    }

    if feasibility == "infeasible":
        payload["reason"] = (
            f"No charging station is reachable within the {usable_m / 1000:.1f} km of usable range: "
            f"{unreachable} station(s) are too far to reach"
            + (f", and {off_corridor} reachable one(s) are more than "
               f"{detour_cap_m / 1000:.0f} km off the direct line." if off_corridor else ".")
        )

    # The model only writes prose about numbers already computed above, and is told
    # plainly which fields do not exist so it cannot fill them in.
    if explain:
        first = stops[0] if stops else None
        try:
            payload["explanation"] = llm.ask(
                system=(
                    "You explain electric vehicle range results to drivers in Queensland. "
                    "Use only the facts you are given; every distance has already been "
                    "calculated for you. Never invent plug types, charging speeds, charging "
                    "times, prices or live availability - none of those are published, and "
                    "say so if they matter. At most four sentences."
                ),
                user=(
                    f"Verdict: {feasibility}. Estimated road distance {trip_road_m / 1000:.0f} km "
                    f"(straight line {straight_line_m / 1000:.0f} km x {ROAD_FACTOR}). "
                    f"Usable range {usable_m / 1000:.0f} km after holding back {margin_pct}%. "
                    + (f"Short by {shortfall_m / 1000:.0f} km. " if shortfall_m else "")
                    + (
                        f"Best stop: {first['name']} at {first['address']}, "
                        f"{first['distance_from_origin_m'] / 1000:.0f} km from the origin, adding "
                        f"{first['detour_m'] / 1000:.0f} km of detour, leaving "
                        f"{first['distance_to_destination_m'] / 1000:.0f} km to the destination. "
                        f"Host: {first['host']}. Onward from there: {first['onward_stations'] or 'not published'}. "
                        if first else ""
                    )
                    + (payload.get("reason", "") + " " if feasibility == "infeasible" else "")
                    + "Plug types, charging speed, charging time, live availability and pricing are not published."
                ),
            )
        except Exception as exc:  # noqa: BLE001
            # llm.ask() raises when a key is present but rejected. Every figure above
            # is already computed, so only the commentary is lost - report the fault
            # in the response rather than failing the whole call.
            payload["explanation"] = None
            payload["explanation_error"] = f"{type(exc).__name__}: {exc}"

    return respond(payload, sources=[data.QLD_LICENCE])

# TODO: add your remaining tools here, up to five including geocode_place.


if __name__ == "__main__":
    mcp.run(transport="streamable-http", host="0.0.0.0",
            port=int(os.environ.get("PORT", "8000")))
