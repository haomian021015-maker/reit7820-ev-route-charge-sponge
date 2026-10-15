"""
data.py - fetching open data, with a cache.

Two sources, both open, both keyless:

  * Queensland Government charging stations, via the data.qld.gov.au CKAN
    datastore API. Returns clean JSON - use this rather than the published CSV,
    which contains embedded newlines inside quoted fields.
  * OpenStreetMap place lookup, via Nominatim (ODbL). The specification requires openly
    licensed sources, which rules out Google Maps geocoding.

Everything is cached on disk. That is not an optimisation: a tool call must
return within 45 seconds, and Nominatim's public endpoint allows only one
request per second. Fifty-five agents calling it live would get the cohort
blocked.
"""

from __future__ import annotations

import hashlib
import json
import os
import threading
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import httpx

CACHE_DIR = Path(__file__).with_name(".cache")
CACHE_DIR.mkdir(exist_ok=True)

# data.qld.gov.au - "Find a charging station - Electric vehicle", CC BY 4.0
QLD_API = "https://www.data.qld.gov.au/api/3/action/datastore_search"
QLD_RESOURCE_ID = "a34d4b5f-8e3c-4995-8950-2e84fd7bb4d5"
QLD_LICENCE = "Queensland Government (TMR) via data.qld.gov.au, CC BY 4.0"

NOMINATIM = "https://nominatim.openstreetmap.org/search"
OSM_LICENCE = "© OpenStreetMap contributors, ODbL 1.0"
USER_AGENT = "REIT7820-SMAC-agent/0.1 (UQ teaching project)"

_nominatim_lock = threading.Lock()
_nominatim_last = 0.0


def _cached(key: str, ttl_seconds: int, fetch) -> Any:
    """Return cached JSON if fresh, else fetch and store. Falls back to a stale
    copy if the fetch fails - a publisher outage must not fail your tool call."""
    path = CACHE_DIR / (hashlib.sha256(key.encode()).hexdigest()[:16] + ".json")
    if path.exists() and time.time() - path.stat().st_mtime < ttl_seconds:
        return json.loads(path.read_text(encoding="utf-8"))
    try:
        payload = fetch()
        path.write_text(json.dumps(payload), encoding="utf-8")
        return payload
    except Exception:
        if path.exists():
            return json.loads(path.read_text(encoding="utf-8"))
        raise


def charging_stations(ttl_seconds: int = 6 * 3600) -> list[dict]:
    """All Queensland Electric Super Highway stations, as clean records.

    Fields kept: name, lat, lon, address, host, status, onward_stations.
    The source publishes a `Charging plugs available` column that is empty for
    every row, so it is left out rather than reported as unknown
    detail your caller might mistake for real.
    """
    def fetch():
        response = httpx.get(
            QLD_API,
            params={"resource_id": QLD_RESOURCE_ID, "limit": 1000},
            timeout=20.0,
        )
        response.raise_for_status()
        return response.json()["result"]["records"]

    stations = []
    for row in _cached(f"qld:{QLD_RESOURCE_ID}", ttl_seconds, fetch):
        try:
            lat, lon = float(row["Latitude"]), float(row["Longitude"])
        except (KeyError, TypeError, ValueError):
            continue  # skip malformed rows rather than crashing
        stations.append(
            {
                "name": str(row.get("Location Name", "")).strip(),
                "lat": lat,
                "lon": lon,
                "address": " ".join(str(row.get("Address", "")).split()),
                "host": str(row.get("Host", "")).strip() or None,
                "status": str(row.get("Status", "")).strip() or None,
                "onward_stations": " ".join(str(row.get("Nearest QESH charging station", "")).split()) or None,
            }
        )
    return stations


def geocode(place: str, ttl_seconds: int = 30 * 24 * 3600) -> dict | None:
    """Look up a place name on OpenStreetMap. Returns None if there is no match.

    Cached for a month and rate-limited to Nominatim's published 1 req/sec.
    """
    query = (place or "").strip()
    if not query:
        return None

    def fetch():
        global _nominatim_last
        with _nominatim_lock:
            wait = 1.1 - (time.time() - _nominatim_last)
            if wait > 0:
                time.sleep(wait)
            _nominatim_last = time.time()
        response = httpx.get(
            NOMINATIM,
            params={"q": query, "format": "json", "limit": 1, "countrycodes": "au"},
            headers={"User-Agent": USER_AGENT},
            timeout=20.0,
        )
        response.raise_for_status()
        return response.json()

    results = _cached(f"osm:{query.lower()}", ttl_seconds, fetch)
    if not results:
        return None
    hit = results[0]
    return {
        "lat": float(hit["lat"]),
        "lon": float(hit["lon"]),
        "matched_name": hit.get("display_name"),
        # building vs suburb vs administrative area - precision varies hugely,
        # and the caller deserves to know which it got.
        "match_kind": f"{hit.get('class', '?')}/{hit.get('type', '?')}",
    }


# Open Charge Map - the proposal's primary station source. Unlike the TMR list it
# publishes each connector's type and rated power, which is what makes a charging
# time computable at all.
#
# The agent reads a pinned snapshot rather than calling the API per request:
#   * the prompt-architecture experiment holds the dataset constant, and OCM is
#     crowd-sourced, so a live feed could change between experimental runs;
#   * most SEQ records were last verified in 2023, so querying live buys no
#     freshness worth having;
#   * the API needs a key and bans heavy callers, and neither belongs on the
#     Showcase's critical path.
# CC BY 4.0 permits redistributing the snapshot with attribution. Refresh it from
# the repository root with:
#
#     python src/data.py refresh-ocm        # reads OCM_API_KEY from .env
OCM_API = "https://api.openchargemap.io/v3/poi/"
OCM_LICENCE = "Open Charge Map contributors via api.openchargemap.io, CC BY 4.0"
OCM_SNAPSHOT = Path(__file__).with_name("snapshots") / "ocm_qld.json"
# Queensland as a bounding box. It clips a strip of northern NSW, whose chargers
# are kept: Tweed Heads is minutes from Coolangatta.
OCM_BBOX = "(-29.20,137.90),(-9.00,153.60)"
_BRISBANE = timezone(timedelta(hours=10))


def ocm_snapshot() -> dict | None:
    """The pinned OCM snapshot: when it was taken, its licence, and its stations.

    None if no snapshot exists, so the agent can fall back to the TMR list
    rather than fail. Every record is returned, private and non-operational
    sites included, so a caller can say how many it excluded and why.
    """
    if not OCM_SNAPSHOT.exists():
        return None
    return json.loads(OCM_SNAPSHOT.read_text(encoding="utf-8"))


def _normalise_ocm(poi: dict) -> dict:
    """One OCM point of interest, reduced to the fields the agent uses."""
    a = poi["AddressInfo"]
    connections = poi.get("Connections") or []
    rated = [c["PowerKW"] for c in connections if c.get("PowerKW")]
    types = {((c.get("ConnectionType") or {}).get("Title") or "").strip() for c in connections}
    status = poi.get("StatusType") or {}
    address = ", ".join(str(x).strip() for x in (a.get("AddressLine1"), a.get("Town"),
                        a.get("StateOrProvince"), a.get("Postcode")) if x and str(x).strip())
    # The latest date OCM records for the site, verification or status update.
    # Kept as a date: it is evidence of staleness, not a timestamp to act on.
    dates = [d for d in (poi.get("DateLastVerified"), poi.get("DateLastStatusUpdate")) if d]
    return {
        "ocm_id": poi["ID"],
        "name": " ".join(str(a.get("Title") or "").split()),
        "lat": float(a["Latitude"]),
        "lon": float(a["Longitude"]),
        "address": " ".join(address.split()),
        "operator": ((poi.get("OperatorInfo") or {}).get("Title") or "").strip() or None,
        "usage": ((poi.get("UsageType") or {}).get("Title") or "").strip() or None,
        "status": (status.get("Title") or "").strip() or None,
        "is_operational": status.get("IsOperational"),
        # The fastest connector's rating. A vehicle may accept less.
        "power_kw": max(rated) if rated else None,
        "connector_types": sorted(types - {"", "Unknown"}),
        "last_updated": max(dates)[:10] if dates else None,
    }


def refresh_ocm_snapshot(api_key: str) -> dict:
    """Fetch every open-licensed OCM station in the Queensland box and pin it.

    Refuses to write anything not marked as open data: the specification
    requires openly licensed sources, and OCM's API mixes licences by provider.
    """
    response = httpx.get(
        OCM_API,
        params={"output": "json", "countrycode": "AU", "boundingbox": OCM_BBOX,
                "opendata": "true", "maxresults": 10000, "compact": "false", "verbose": "false"},
        headers={"X-API-Key": api_key, "User-Agent": USER_AGENT},
        timeout=120.0,
    )
    response.raise_for_status()
    raw = response.json()

    closed = [p.get("ID") for p in raw if not (p.get("DataProvider") or {}).get("IsOpenDataLicensed")]
    if closed:
        raise RuntimeError(f"{len(closed)} records are not marked open data, e.g. OCM IDs {closed[:5]}")

    stations = []
    for poi in raw:
        try:
            stations.append(_normalise_ocm(poi))
        except (KeyError, TypeError, ValueError):
            continue  # skip malformed rows rather than pin them
    stations.sort(key=lambda s: s["ocm_id"])

    head = {
        "source": OCM_API,
        "licence": OCM_LICENCE,
        "provider_licences": sorted({(p.get("DataProvider") or {}).get("License") for p in raw} - {None}),
        "fetched_at": datetime.now(_BRISBANE).isoformat(timespec="seconds"),
        "query": {"countrycode": "AU", "boundingbox": OCM_BBOX, "opendata": True},
        "station_count": len(stations),
    }
    # One station per line, so a refresh shows up in git as a readable diff.
    text = json.dumps(head, indent=2, ensure_ascii=False)[:-2]
    text += ',\n  "stations": [\n'
    text += ",\n".join("    " + json.dumps(s, ensure_ascii=False) for s in stations)
    text += "\n  ]\n}\n"
    snapshot = json.loads(text)  # prove it parses before replacing the old one
    OCM_SNAPSHOT.parent.mkdir(exist_ok=True)
    OCM_SNAPSHOT.write_text(text, encoding="utf-8")
    return snapshot


def _ocm_key() -> str | None:
    """OCM_API_KEY from the environment, else from .env at the repository root."""
    key = os.environ.get("OCM_API_KEY")
    if key:
        return key.strip()
    env = Path(__file__).resolve().parent.parent / ".env"
    if env.exists():
        for line in env.read_text(encoding="utf-8-sig").splitlines():
            name, sep, value = line.partition("=")
            if sep and name.strip() == "OCM_API_KEY":
                return value.split(" #")[0].strip().strip("\"'") or None
    return None


if __name__ == "__main__":
    import sys

    if sys.argv[1:] != ["refresh-ocm"]:
        sys.exit("usage: python src/data.py refresh-ocm")
    key = _ocm_key()
    if not key:
        sys.exit("OCM_API_KEY is not set. Add it to .env - see .env.example.")
    snap = refresh_ocm_snapshot(key)
    print(f"Wrote {snap['station_count']} stations to {OCM_SNAPSHOT} at {snap['fetched_at']}")
