"""
The demo query catalogue.

Each query is a question a person might actually ask, paired with a scripted
plan of tool calls that answers it. The plan is a fallback: when a model is
configured the router chooses the tools itself, and the scripted plan is only
used when no API key is set, or when someone ticks "scripted" to guarantee a
demo runs the same way twice.

An argument written as "$0.location.lat" means "take it from step 0's result",
which is how a query gets geocoded before it is answered.

Every domain includes at least one question the agents should refuse. Watching
an agent decline to answer is the most useful thing an observer can see: it is
the difference between a system that knows its coverage and one that invents.
"""

DOMAINS = [
    {
        "id": "charging",
        "name": "EV Charging",
        "blurb": "Trip feasibility and charging stops across Queensland: Open Charge Map stations, cross-checked against the state's Electric Super Highway list.",
    },
]

QUERIES = [
    {
        "id": "chg-trip-stop",
        "domain": "charging",
        "text": "I'm at the University of Queensland in St Lucia with 80 km of range left and want to drive to Toowoomba. Can I make it, and if not, where should I charge?",
        "why": "Three calls the model plans for itself: look up both places, then check the trip. The verdict, the shortfall and each stop's added time are arithmetic on the station data; the model only puts them into words.",
        "plan": [
            {"agent": "charging", "tool": "geocode_place", "arguments": {"place": "University of Queensland St Lucia"}},
            {"agent": "charging", "tool": "geocode_place", "arguments": {"place": "Toowoomba"}},
            {"agent": "charging", "tool": "assess_ev_trip_feasibility",
             "arguments": {"origin_lat": "$0.lat", "origin_lon": "$0.lon", "dest_lat": "$1.lat", "dest_lon": "$1.lon", "remaining_range_km": 80}},
        ],
    },
    {
        "id": "chg-trip-direct",
        "domain": "charging",
        "text": "I'm at the University of Queensland with 250 km of range. Can I drive to Toowoomba without stopping to charge?",
        "why": "Enough range, so the answer is a plain yes, with the road distance and the safety reserve behind it.",
        "plan": [
            {"agent": "charging", "tool": "geocode_place", "arguments": {"place": "University of Queensland St Lucia"}},
            {"agent": "charging", "tool": "geocode_place", "arguments": {"place": "Toowoomba"}},
            {"agent": "charging", "tool": "assess_ev_trip_feasibility",
             "arguments": {"origin_lat": "$0.lat", "origin_lon": "$0.lon", "dest_lat": "$1.lat", "dest_lon": "$1.lon", "remaining_range_km": 250}},
        ],
    },
    {
        "id": "chg-trip-stranded",
        "domain": "charging",
        "text": "I'm in Kilcoy with only 20 km of range left and need to get to the University of Queensland. What should I do?",
        "why": "The nearest public charger is over 45 km away, so no stop is reachable. 'Infeasible' is a computed answer, not a failure: the tool reports how many stations were out of reach.",
        "plan": [
            {"agent": "charging", "tool": "geocode_place", "arguments": {"place": "Kilcoy, Queensland"}},
            {"agent": "charging", "tool": "geocode_place", "arguments": {"place": "University of Queensland St Lucia"}},
            {"agent": "charging", "tool": "assess_ev_trip_feasibility",
             "arguments": {"origin_lat": "$0.lat", "origin_lon": "$0.lon", "dest_lat": "$1.lat", "dest_lon": "$1.lon", "remaining_range_km": 20}},
        ],
    },
    {
        "id": "chg-trip-chademo",
        "domain": "charging",
        "text": "I drive an older Nissan Leaf: CHAdeMO plug, 50 kW charging at most, 150 km on a full battery. I'm at the University of Queensland with 80 km left, heading to Toowoomba. Where should I charge?",
        "why": "The first trip again, for a car that can only use CHAdeMO chargers and draw 50 kW. Capped at 50 kW, the 350 kW charger loses its edge and the stop with almost no detour comes first.",
        "plan": [
            {"agent": "charging", "tool": "geocode_place", "arguments": {"place": "University of Queensland St Lucia"}},
            {"agent": "charging", "tool": "geocode_place", "arguments": {"place": "Toowoomba"}},
            {"agent": "charging", "tool": "assess_ev_trip_feasibility",
             "arguments": {"origin_lat": "$0.lat", "origin_lon": "$0.lon", "dest_lat": "$1.lat", "dest_lon": "$1.lon", "remaining_range_km": 80, "full_range_km": 150, "connector_type": "CHAdeMO", "vehicle_max_charge_kw": 50}},
        ],
    },
    {
        "id": "chg-trip-unpublished",
        "domain": "charging",
        "text": "I'm at the University of Queensland with 80 km of range, driving to Toowoomba. Is the charger you'd recommend free right now, and what will it cost me?",
        "why": "No open dataset publishes live availability or prices. The tool lists both as data gaps, and a faithful answer says so instead of guessing.",
        "plan": [
            {"agent": "charging", "tool": "geocode_place", "arguments": {"place": "University of Queensland St Lucia"}},
            {"agent": "charging", "tool": "geocode_place", "arguments": {"place": "Toowoomba"}},
            {"agent": "charging", "tool": "assess_ev_trip_feasibility",
             "arguments": {"origin_lat": "$0.lat", "origin_lon": "$0.lon", "dest_lat": "$1.lat", "dest_lon": "$1.lon", "remaining_range_km": 80}},
        ],
    },
    {
        "id": "chg-trip-interstate",
        "domain": "charging",
        "text": "Can I drive from the University of Queensland to the Sydney Opera House on 200 km of range?",
        "why": "The destination is in New South Wales. The trip tool covers destinations in Queensland only, so it declines and says why, rather than estimating a route its data does not cover.",
        "plan": [
            {"agent": "charging", "tool": "geocode_place", "arguments": {"place": "University of Queensland St Lucia"}},
            {"agent": "charging", "tool": "assess_ev_trip_feasibility",
             "arguments": {"origin_lat": "$0.lat", "origin_lon": "$0.lon", "dest_lat": -33.8568, "dest_lon": 151.2153, "remaining_range_km": 200}},
        ],
    },
    {
        "id": "chg-nearest-named-place",
        "domain": "charging",
        "text": "Where is the nearest EV charger to Toowong Village in Brisbane?",
        "why": "No coordinates in the question. The agent has to look the place up before it can measure anything, so this takes two tool calls.",
        "plan": [
            {"agent": "charging", "tool": "geocode_place",
             "arguments": {"place": "Toowong Village, Brisbane"}},
            {"agent": "charging", "tool": "find_nearest_charger",
             "arguments": {"lat": "$0.lat", "lon": "$0.lon", "max_results": 3}},
        ],
    },
    {
        "id": "chg-onward",
        "domain": "charging",
        "text": "I am at latitude -27.4975, longitude 153.0137. Which three highway charging stations are closest, and how far is each?",
        "why": "Coordinates are given, so no lookup is needed: one call, three stations, each distance computed from the dataset rather than recalled.",
        "plan": [
            {"agent": "charging", "tool": "find_nearest_charger",
             "arguments": {"lat": -27.4975, "lon": 153.0137, "max_results": 3}},
        ],
    },
    {
        "id": "chg-plug-types",
        "domain": "charging",
        "text": "What plug types does the charger nearest to Brisbane Airport have?",
        "why": "The source has a connector column, but it is empty on every row. The right answer says that is not published, rather than guessing CCS2 or Type 2.",
        "plan": [
            {"agent": "charging", "tool": "geocode_place",
             "arguments": {"place": "Brisbane Airport"}},
            {"agent": "charging", "tool": "find_nearest_charger",
             "arguments": {"lat": "$0.lat", "lon": "$0.lon", "max_results": 1}},
        ],
    },
    {
        "id": "chg-out-of-scope",
        "domain": "charging",
        "text": "Where is the nearest charger to the Sydney Opera House?",
        "why": "Outside Queensland. A refusal that still cites its source is the correct answer here, and it is what the specification requires.",
        "plan": [
            {"agent": "charging", "tool": "find_nearest_charger",
             "arguments": {"lat": -33.8568, "lon": 151.2153, "max_results": 3}},
        ],
    },
]


def by_id(query_id: str) -> dict | None:
    return next((q for q in QUERIES if q["id"] == query_id), None)
