# Project Context — REIT7820 Project 2: Smart Mobility Agent Collective

This file briefs Claude Code on everything already established for this project in a prior
planning conversation (with Claude in Cowork), so it can continue without re-deriving context.
Read this fully before making changes.

## Course / assessment context

- Course: REIT7820, UQ. Project 2 is "Smart Mobility Agent Collective" — each student builds an
  individual AI agent that speaks the **Model Context Protocol (MCP)** and occupies one capability
  slot within a shared multi-agent ecosystem. The semester culminates in a **Week 12 Interoperability
  Showcase**: an orchestrator and peer agents call every student's agent live, unscripted.
- My domain: **EV Charging Infrastructure**.
- Data sources (already wired into the starter kit): OpenChargeMap-style / Queensland Electric
  Super Highway station data (data.qld.gov.au, CC BY 4.0), OpenStreetMap via a shared Nominatim
  geocoding service (`geocode_place`, rate-limited to 1 req/sec, must cache).
- Independent variable chosen for the course-required controlled evaluation: **prompt architecture**
  (zero-shot vs few-shot vs structured reasoning scaffold) — NOT model tier, NOT tool-schema
  ablation, NOT robustness. This is the "thesis contribution" the report needs empirical results for.
- **Progress Review** happens in-person during the regular workshop slot. Format: 3 minutes live
  show-and-tell from the laptop (must be a working setup/demo, not slides) + state the single
  biggest current blocker + 2 minutes rapid Q&A. Generative AI / MT tools are not permitted
  *during the review itself* (that's about the live presentation, not a restriction on tools built
  beforehand). Marking: Background/literature 20%, build/demo progress 40%, presentation 20%, Q&A 20%.
- **Known, course-wide, non-personal blocker**: official Anthropic Claude Console access / API key
  creation is only being walked through live in the Week 7 Friday lecture — after this week's
  Progress Review. So going into the review, an invalid/placeholder Claude API key (401
  `invalid x-api-key`) is expected and should be stated plainly as the blocker, not treated as a
  personal setup failure. The starter kit is designed so that tools still return real computed facts
  without a working key — only the natural-language commentary and true LLM-based tool routing are
  lost. So a fully working tool can still be demoed live even without the key.

## The proposal (already written, submitted)

Project: **EV-RouteCharge** — an MCP-compliant agent that answers one narrow, well-defined question:
given an origin, a destination, and the vehicle's current range, is the trip feasible without
charging, and if not, which real, currently-available charging station should the driver stop at.

Capability contract (from the proposal):
- **Input**: origin (address or coordinates), destination (address or coordinates), current state of
  charge / remaining range (km), full battery range (km), optional connector-type preference.
- **Output**: feasibility flag (`feasible` / `requires_charging` / `infeasible`), an ordered list of
  recommended charging stops (each with distance from route, connector type, availability, estimated
  charging time), and a short natural-language explanation.

Deliberately scoped narrow (not the whole EV Charging domain) so the tool schema stays small enough
to describe clearly, test exhaustively, and defend live at the Showcase — tool-description quality is
explicitly graded.

## Starter kit structure (as provided by the course)

```
src/
  agents/charging.py         <- MY file. `find_nearest_charger` ships fully implemented as a
                                 reference tool with 2 passing eval cases. Read it, then extend it —
                                 don't just keep serving the shipped reference tool.
  agents/public_transport.py, policy.py   <- other students' domains, not mine
  eval/tasks.charging.json   <- MY evaluation cases: prompt + expected tool calls + expected output.
  eval/run_eval.py           <- runner, don't edit
  common.py                  <- shared `health` and `geocode_place` (geocoding is opt-in per agent,
                                 counts toward the 5-tool cap; `health` doesn't)
  smac.py                    <- identity checks, respond(), @guard — read once, don't edit
  data.py                    <- open-data fetching/caching (EV charging stations etc.)
  llm.py                     <- one ask() wrapper for the Claude API
  preflight.py                <- environment/dependency/key/dataset checker
  descriptions.md             <- REQUIRED submission: v1 and refined v2 of every tool description
docker/compose.yml, docker/.env (git-ignored; ANTHROPIC_API_KEY, WANDB_API_KEY, etc.)
```

Two non-negotiable rules from the kit's README:
1. **Compute the facts; let the model write the prose.** Distances/ranking/feasibility must be
   arithmetic in code, never asked of the model — a number that can't be traced to code can't be
   checked against ground truth, and can't be defended live.
2. **Never guess a coordinate.** Always use `geocode_place`; a model-recalled coordinate has no
   source and can be wrong by hundreds of metres.

`AGENT_NAME` must be `smac-charging-{approved-slot}`, lowercase, hyphenated — checked at startup.

## Environment status (as of last session)

- Docker Desktop + WSL2 were broken (virtualization/TxF/CBS transaction errors on Windows) and have
  been fixed. `docker compose -f docker/compose.yml up --build` runs cleanly; all agent containers
  report Healthy; `preflight.py` passes (Python 3.12.14, deps ok, EV charging stations loaded from
  data.qld.gov.au, GTFS cached, patronage cached).
- Console at `http://localhost:8080` works. A test query against the shipped reference tool
  (`find_nearest_charger`, via `geocode_place` first) returned correct real data, but **model
  routing failed with a 401 `invalid x-api-key`** — expected per the blocker above, not a setup bug.
  The system fell back to a scripted plan from the query catalogue in that case, which is the
  designed degrade-gracefully behavior, not a crash.
- `WANDB_API_KEY` has been set up (account created under UQ entity `haomian021015-uq`).
- **Not yet started**: the actual custom tool for trip-feasibility + charging-stop recommendation.
  Only the shipped `find_nearest_charger` reference tool currently works. This is today's priority.

## Immediate task (what Claude Code should help with now)

Build a **minimal but real, live-demoable v1** of the EV-RouteCharge capability inside
`src/agents/charging.py`, reusing what's already proven to work:

1. Geocode origin and destination via the shared `geocode_place`.
2. Estimate route distance — for v1, a straight-line (haversine) distance × a road-distance
   correction factor (e.g. ×1.3) is an acceptable simplification; a real routing API can replace this
   later. Don't block on building full route-corridor search for tonight's demo.
3. Compare estimated distance to the user-supplied range to produce the feasibility flag.
4. If not feasible, reuse the same charging-station dataset/lookup logic `find_nearest_charger`
   already uses to recommend a real, available station (e.g. nearest to the destination or route
   midpoint) — don't reinvent the data access layer.
5. Return the structured output shape defined in the proposal (feasibility flag + ranked
   recommendation(s) + a plain-language explanation when an LLM key is available, degrading
   gracefully to just the computed facts when it isn't, per the kit's design).
6. Add at least one hand-verified evaluation case to `eval/tasks.charging.json` (prompt, expected
   tool call, expected output) and confirm `run_eval.py` passes it.
7. Write the v1 tool description into `descriptions.md` per the kit's four-part guidance (what it
   does concretely, coverage, freshness, what it does *not* do) — this is graded.

Ask the user to paste the current contents of `src/agents/charging.py` (and the charging-station
loading portion of `src/data.py`) before writing code, so the new tool matches the existing style,
imports, and data shapes exactly rather than guessing.
