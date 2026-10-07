# Tool descriptions - v1 and v2

**The specification requires two versions of every domain tool description.**
Only **v2** is served live, in your docstring. **v1** lives here, and is submitted
with your final report.

Fill this in as you go. If you skip it and only write v1 here at the end, you will
be reconstructing it from memory - and it shows.

---

## Why this file exists

The Orchestrator never reads your code. Choosing whether to call you, it sees
**only your tool name, your description, and your parameter descriptions**. That
text is the whole interface, and it is graded.

Writing a better description is the cheapest, highest-leverage improvement
available to anyone in this theme regardless of programming background - and the
v1/v2 pair is the built-in before/after dataset for **ablation option 3 (tool
schema & description design)**.

---

## What makes v2 better than v1

A useful description covers four things:

1. **What it does**, concretely - not "handles charging queries".
2. **Coverage** - where your answers are valid.
3. **Freshness** - how live the data is.
4. **What it does *not* do.** The most-skipped and most valuable: it stops the
   Orchestrator calling you for questions you would answer badly.

Describe every parameter too - those are the instructions for filling in your
tool:

```python
lat: Annotated[float, Field(description="WGS84 latitude of the trip origin.")]
```

A revision is only worth recording if you can say **what evidence prompted it**.
"Sounded better" is not evidence. Real evidence looks like: it was selected for a
query it shouldn't have been; it wasn't selected for one it should have; a
parameter came back wrong; a peer's agent was chosen over yours.

---

## Tool 1 - `assess_ev_trip_feasibility`

My own tool, and the capability this agent is built around: given an origin, a
destination and the range left in the battery, decide whether the trip can be
completed and, if not, which real charging station to stop at.

### v1 - initial draft
> Check whether an EV can complete a trip on its remaining range, and recommend
> charging stations near the route if it cannot. Takes an origin, a destination,
> the current remaining range and the full battery range, and returns a
> feasibility flag, a ranked list of recommended charging stops with connector
> type, availability and estimated charging time, and a short explanation.

This is the capability contract as written in the project proposal, before any of
it was checked against the dataset. Three of the fields it promises do not exist.

### v2 - refined (this is what's served live)
> Decide whether an electric vehicle can finish a trip on the range it has left, and where to charge if it cannot.
>
> Takes an origin, a destination and the range remaining in the battery. Estimates
> the road distance, subtracts a safety reserve, and returns one of three verdicts:
> `feasible` (drive straight there), `requires_charging` (a stop is needed, with
> Queensland Electric Super Highway stations ranked by how little they add to the
> direct line) or `infeasible` (no station is reachable on the range left). Each
> recommended stop reports how far it is, the detour it adds, and whether a full
> charge there would complete the trip.
>
> The origin must be in South East Queensland; the destination may be anywhere in
> Queensland, because the trips worth asking about leave SEQ. Stations come from the
> Queensland Government's published list, re-fetched at most every six hours, so this
> covers intercity highway corridors and not kerbside chargers in a suburb.
>
> Takes coordinates, not place names: call `geocode_place` first. Road distance is
> estimated as straight-line distance x 1.3, not routed over a road network, so it is
> an approximation rather than a driving route. Does NOT report plug or connector
> types, charging speed, charging time, live availability or pricing - the source
> publishes none of them. Plans a single stop, not a multi-stop itinerary.

### What changed and why

| # | Change | Evidence that prompted it |
|---|---|---|
| 1 | Dropped "connector type, availability and estimated charging time" from the promised output, and added them to an explicit NOT list | Dataset inspection: the CKAN resource publishes a `Charging plugs available` column that is **empty on every one of the 17 rows**, and no power or connector column at all. Charging time cannot be computed from any published field, so v1 advertised three outputs the agent can never produce |
| 2 | Replaced "charging stations near the route" with "Queensland Electric Super Highway stations ... intercity highway corridors and not kerbside chargers in a suburb" | Dataset inspection: 17 stations statewide, only 6 inside SEQ (Brisbane, Springfield, Gatton, Toowoomba, Cooroy, Coolangatta). "Near the route" implies the density of a commercial charging map, which would attract "where can I charge in West End" queries this agent answers badly |
| 3 | Named the three verdicts in the description (`feasible` / `requires_charging` / `infeasible`) instead of saying "a feasibility flag" | Local testing: `infeasible` is a computed answer ("no station is reachable"), not a failure, and it is returned through `respond()` while an out-of-coverage query is returned through `out_of_scope()`. A caller that cannot tell them apart will treat a real answer as an error |
| 4 | Added "Takes coordinates, not place names: call `geocode_place` first" | Local testing: the tool signature takes four floats. Without this line a caller has no instruction to run the geocoding step, and the kit's rule is that a recalled coordinate has no source. Case 3 of the evaluation set exercises the two-step chain |
| 5 | Stated the x 1.3 road-distance approximation in the description rather than only in the response body | Local testing: the UQ St Lucia to Toowoomba estimate comes out at 135,899 m from a 104,538 m straight line. It is a flat correction, not a routed distance, and a caller told only "estimated road distance" could quote it as a driving distance |
| 6 | Added "Plans a single stop, not a multi-stop itinerary" | Design limit, stated so it is not discovered at the Showcase: the ranking picks one station, and `completes_trip_after_stop` reports whether that one stop is enough rather than planning a second |

Rows 1-6 come from dataset inspection and local testing against the evaluation
set. Evidence of the other kind the brief asks for - the Orchestrator selecting
this tool for a query it should not have, or passing it a bad parameter - can
only be gathered once peer agents are calling it, and is added after the Week 9
handshake.

### Parameter descriptions

| Parameter | v1 | v2 |
|---|---|---|
| `origin_lat` | Origin latitude | WGS84 latitude of where the trip starts. Must be in South East Queensland. |
| `origin_lon` | Origin longitude | WGS84 longitude of where the trip starts. Must be in South East Queensland. |
| `dest_lat` | Destination latitude | WGS84 latitude of the destination. May be anywhere in Queensland. |
| `dest_lon` | Destination longitude | WGS84 longitude of the destination. May be anywhere in Queensland. |
| `remaining_range_km` | Current remaining range in km | Range left in the battery right now, in kilometres, as the vehicle reports it. Must be greater than zero. |
| `full_range_km` | Full battery range in km | Range in kilometres on a full battery. Optional; supply it to learn whether one charging stop is enough to finish the trip. |
| `safety_margin_pct` | *(not in v1)* | Percentage of range held back as a reserve rather than planned for, 0 to 50. Defaults to 10. |
| `max_results` | *(not in v1)* | How many charging stops to return when the trip needs one, 1 to 5. |
| `explain` | *(not in v1)* | Include a short written explanation of the verdict alongside the computed figures. |

The v1 column is what the proposal's capability contract implies; the units and
bounds in v2 exist because they are the instructions a caller actually needs -
`remaining_range_km` without "must be greater than zero" invites the malformed
call that evaluation case 7 sends deliberately.

---

## Tool 2 - `find_nearest_charger`

Shipped with the starter kit, kept and served unchanged. Its description is the
kit's, reproduced in the worked example below, and it is not offered as my own
work. It is retained because it answers a genuinely different question -
"where is the nearest charger to this point" with no trip and no range - and
because two of the evaluation cases depend on it.

---

## Worked example

Taken from the starter kit's charging tool, so you can see the shape.

### v1 - initial draft
> Find EV charging stations near a location in Queensland.

### v2 - refined
> Find the closest Queensland Electric Super Highway charging stations to a point.
>
> Answers range-planning questions for electric vehicle trips starting in South
> East Queensland - where the next public charging site is, how far away, and
> which sites lie onward along the highway network. Uses the Queensland
> Government's published station list, so it covers intercity corridors rather
> than every kerbside charger in a suburb.
>
> Origin must be in South East Queensland; returned stations may be anywhere in
> Queensland, since onward stations matter on long trips. Plug and connector
> types are NOT available - the source publishes that column empty. Does not
> report live availability or pricing, and does not plan a route.

### What changed and why

| # | Change | Evidence |
|---|---|---|
| 1 | Named the actual dataset ("Electric Super Highway") instead of "in Queensland" | 17 stations statewide - "near a location" implied dense urban coverage the data doesn't have |
| 2 | Stated origin must be in SEQ, results may be statewide | Ambiguity: the agent refuses Cairns *origins* but returns Cairns *stations* |
| 3 | Added "Plug and connector types are NOT available" | Source publishes that column empty; without this the Orchestrator routes connector questions here |
| 4 | Added "does not report live availability or pricing, does not plan a route" | Competing agents exist for cost and routing - this stops mis-selection |

Each row cites something observed rather than a preference. That table is what
you analyse in your report.
