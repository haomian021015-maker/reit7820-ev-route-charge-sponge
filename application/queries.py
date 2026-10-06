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
        "blurb": "Queensland Electric Super Highway stations, from the Department of Transport and Main Roads.",
    },
]

QUERIES = [
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
