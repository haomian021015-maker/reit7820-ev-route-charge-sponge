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

The specification asks for a v1 and a v2. This tool has been refined twice -
once against the Queensland Government data, and again when Open Charge Map was
added - so all three are recorded. **v3 is the version served live.**

### v1 - initial draft
> Check whether an EV can complete a trip on its remaining range, and recommend
> charging stations near the route if it cannot. Takes an origin, a destination,
> the current remaining range and the full battery range, and returns a
> feasibility flag, a ranked list of recommended charging stops with connector
> type, availability and estimated charging time, and a short explanation.

This is the capability contract as written in the project proposal, before any of
it was checked against the dataset. Three of the fields it promises do not exist.

### v2 - refined against the TMR data (superseded by v3)
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

#### What changed from v1 to v2, and why

| # | Change | Evidence that prompted it |
|---|---|---|
| 1 | Dropped "connector type, availability and estimated charging time" from the promised output, and added them to an explicit NOT list | Dataset inspection: the CKAN resource publishes a `Charging plugs available` column that is **empty on every one of the 17 rows**, and no power or connector column at all. Charging time cannot be computed from any published field, so v1 advertised three outputs the agent can never produce |
| 2 | Replaced "charging stations near the route" with "Queensland Electric Super Highway stations ... intercity highway corridors and not kerbside chargers in a suburb" | Dataset inspection: 17 stations statewide, only 6 inside SEQ (Brisbane, Springfield, Gatton, Toowoomba, Cooroy, Coolangatta). "Near the route" implies the density of a commercial charging map, which would attract "where can I charge in West End" queries this agent answers badly |
| 3 | Named the three verdicts in the description (`feasible` / `requires_charging` / `infeasible`) instead of saying "a feasibility flag" | Local testing: `infeasible` is a computed answer ("no station is reachable"), not a failure, and it is returned through `respond()` while an out-of-coverage query is returned through `out_of_scope()`. A caller that cannot tell them apart will treat a real answer as an error |
| 4 | Added "Takes coordinates, not place names: call `geocode_place` first" | Local testing: the tool signature takes four floats. Without this line a caller has no instruction to run the geocoding step, and the kit's rule is that a recalled coordinate has no source. Case 3 of the evaluation set exercises the two-step chain |
| 5 | Stated the x 1.3 road-distance approximation in the description rather than only in the response body | Local testing: the UQ St Lucia to Toowoomba estimate comes out at 135,899 m from a 104,538 m straight line. It is a flat correction, not a routed distance, and a caller told only "estimated road distance" could quote it as a driving distance |
| 6 | Added "Plans a single stop, not a multi-stop itinerary" | Design limit, stated so it is not discovered at the Showcase: the ranking picks one station, and `completes_trip_after_stop` reports whether that one stop is enough rather than planning a second |

### v3 - Open Charge Map added (this is what's served live)
> Decide whether an electric vehicle can finish a trip on the range it has left, and where to charge if it cannot.
>
> Takes an origin, a destination and the range remaining in the battery. Estimates
> the road distance, holds back a safety reserve, and returns one of three verdicts:
> `feasible` (drive straight there), `requires_charging` (a stop is needed) or
> `infeasible` (no public charger is reachable on the range left). When a stop is
> needed, public chargers that are reachable and close to the direct line are ranked
> by the time they add to the trip - the detour plus the charging needed to finish -
> and each reports its rated power, connector types, the range and energy to add,
> and whether a full charge there completes the trip. An optional connector type
> limits the stops to chargers the vehicle can use.
>
> The origin must be in South East Queensland; the destination may be anywhere in
> Queensland. Stations come from a pinned Open Charge Map snapshot of Queensland,
> dated in every response, cross-checked against the Queensland Government's
> Electric Super Highway list, which flags the state's designated corridor sites.
>
> Takes coordinates, not place names: call `geocode_place` first. Road distance is
> straight-line distance x 1.3, not a routed path. Charging time is a minimum: it
> assumes the charger's rated power, capped at the vehicle's limit if one is given,
> and charging slows past about 80%. Does NOT report live availability or
> occupancy - no open source publishes it, and most station records were last
> verified years ago - nor pricing. Plans a single stop, not a multi-stop itinerary.

#### What changed from v2 to v3, and why

| # | Change | Evidence that prompted it |
|---|---|---|
| 1 | Stations now come from Open Charge Map, cross-checked against the TMR list, which flags the state's designated corridor sites (`is_qesh`) | Measured on 2026-10-15 with the proposal's primary source: 148 stations in the Queensland box against TMR's 17; `PowerKW` on 143 of 148; one data provider, CC BY 4.0, so the `opendata=true` filter removed nothing. 16 of the 17 TMR sites sit within 150 m of an OCM record, the nearest non-match is 4.2 km away (Marlborough), so the proposal's cross-check step is directly implementable |
| 2 | Removed connector types, charging speed and charging time from the NOT list; each stop now reports `power_kw`, `connector_types`, `range_to_add_m`, `energy_to_add_kwh` and `charging_time_s` | The v2 reason for the NOT list - the source publishes none of them - no longer holds: 98.9% of SEQ records carry a rated power and a connector type |
| 3 | Ranking changed from least detour to least **added time**: the detour at 60 km/h plus the charging needed to finish | Replaying evaluation case 3 on OCM data with the v2 ranking: the five least-detour stations lay within 1.6 km of detour of each other yet ranged from 22 to 75 kW, while a 350 kW charger 3 km off the line did not make the top five. Across the candidates rated power spans 22 to 350 kW, a sixteen-fold difference that detour alone ignores |
| 4 | Added the optional `vehicle_max_charge_kw` parameter, and "charging time is a minimum" to the description | Local testing: for a CHAdeMO car, ranking by each charger's rated power put a 350 kW site first with 132 s of charging - power a ~50 kW car cannot draw. Capped at 50 kW, the 11 m-detour Indooroopilly charger correctly ranks first (evaluation case 9) |
| 5 | `full_range_km` now says "Optional: the verdict and the recommended stops do not need it" | **Observed from a model calling the tool.** In the 2026-10-07 evaluation run, the router's answer to case 8 was "I cannot assess whether this trip is feasible. The assess_ev_trip_feasibility tool requires the full battery range in kilometres to determine whether one charging stop is sufficient" - it read an optional parameter as required and refused a question the tool can answer |
| 6 | Response field `distance_to_destination_m` renamed `drive_after_stop_m`, and `range_to_add_m` added beside it | **Observed from a model calling the tool.** In the same run, the router's answer to case 3 said a stop "will get you to Toowoomba with 122 km remaining" - 122 km was the distance still to drive, read as charge left on arrival. After the change the agent's own explanation reads "102 km to drive after charging" |
| 7 | Added the optional `connector_type` parameter (CCS2, CHAdeMO, Type2, Type1) | The proposal's input contract promised a connector preference, and OCM now makes it answerable. OCM's "Type I (AS 3112)" is the Australian household socket, not the Type 1 EV plug, so it is deliberately not mapped to `Type1` |
| 8 | Coverage line changed from "intercity highway corridors, not kerbside chargers" to the OCM snapshot of Queensland | OCM holds inner-city sites the TMR list does not (Hamilton, Kelvin Grove, Brisbane City), including one on the UQ St Lucia campus. Keeping the v2 line would now turn away suburban questions the tool can answer |
| 9 | Freshness changed from "re-fetched every six hours" to a pinned, dated snapshot, and "live availability" kept on the NOT list with the reason stated | OCM's own schema defines its status as "generally operational", and 65 of the 92 SEQ records were last verified or updated in 2023, so querying live would buy no freshness. A pinned snapshot keeps the dataset constant across the prompt-architecture conditions, which the proposal's method requires |

Rows 5 and 6 are the first evidence of the kind the brief values most: a
behaviour observed when a model, seeing only the tool's description and schema,
called it and misread it. Both came from the `final_response` column the
evaluation runner records for every case. The rest come from dataset
measurement and local testing.

### Parameter descriptions

| Parameter | v1 | v3 (served live; v2 where unchanged) |
|---|---|---|
| `origin_lat` | Origin latitude | WGS84 latitude of where the trip starts. Must be in South East Queensland. |
| `origin_lon` | Origin longitude | WGS84 longitude of where the trip starts. Must be in South East Queensland. |
| `dest_lat` | Destination latitude | WGS84 latitude of the destination. May be anywhere in Queensland. |
| `dest_lon` | Destination longitude | WGS84 longitude of the destination. May be anywhere in Queensland. |
| `remaining_range_km` | Current remaining range in km | Range left in the battery right now, in kilometres, as the vehicle reports it. Must be greater than zero. |
| `full_range_km` | Full battery range in km | Range in kilometres on a full battery. Optional: the verdict and the recommended stops do not need it. Supply it to learn whether one stop is enough to finish the trip (completes_trip_after_stop), and to cap the charge a stop asks for at a full battery. |
| `connector_type` | Optional connector-type preference | Only recommend chargers that have this connector. Optional; omit it to consider every connector. CCS2 and CHAdeMO are DC fast-charging plugs; Type2 is the AC plug most Australian EVs use. |
| `consumption_kwh_per_100km` | *(not in v1)* | The vehicle's energy use in kWh per 100 km, which turns the range a stop must add into energy and so into charging time. Defaults to 18, typical of a mid-size EV. |
| `vehicle_max_charge_kw` | *(not in v1)* | The most power the vehicle can accept while charging, in kW. Optional; without it each charger's full rated power is assumed, so charging times are minimums and the most powerful chargers rank first even for a car that cannot use that power. |
| `safety_margin_pct` | *(not in v1)* | Percentage of range held back as a reserve rather than planned for, 0 to 50. Defaults to 10. |
| `max_results` | *(not in v1)* | How many charging stops to return when the trip needs one, 1 to 5. |
| `explain` | *(not in v1)* | Include a short written explanation of the verdict alongside the computed figures. |

The v1 column is what the proposal's capability contract implies. `connector_type`
was in that contract, dropped in v2 because the TMR list publishes no connectors,
and restored in v3 once OCM made it answerable. `consumption_kwh_per_100km` and
`vehicle_max_charge_kw` are new in v3: they are what turning a distance into a
charging time needs.

---

## Tool 2 - `find_nearest_charger`

Shipped with the starter kit, kept and served unchanged. Its description is the
kit's, reproduced in the worked example below, and it is not offered as my own
work. It is retained because it answers a genuinely different question -
"where is the nearest charger to this point" with no trip and no range - and
because evaluation case 2 depends on it. It deliberately stays on the TMR list:
its description promises Electric Super Highway stations, and switching its data
would make that promise false.

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
