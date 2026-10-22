"""
run_prompt_experiment.py - Purpose 2: how does the calling model's prompt
architecture change how reliably it uses this agent?

    docker compose exec charging pip install anthropic==1.15.0   # the judge's SDK, once per container
    docker compose exec charging python eval/run_prompt_experiment.py --repeats 3

Independent variable - the router's system prompt, in eval/prompts/:
  zero_shot   the console's ROUTER_SYSTEM, verbatim: the baseline
  few_shot    the baseline plus four worked examples, on trips not in the task set
  scaffold    the baseline plus a five-step working procedure
Each treatment is the baseline plus an addition, so the addition is the only
thing that differs.

Held constant: the router model, this agent and its tool descriptions, the
pinned OCM snapshot, the questions in tasks.charging.json, and the console's
own router loop (ui.run_with_model), including its four-decision budget and
its 2,500-character view of each tool result.

The router is the caller's side of the interface, so nothing here touches the
agent or the zone: the prompt is swapped by replacing ui.ROUTER_SYSTEM for the
length of each run.

Each run is scored against the hand-labelled expectations in SPEC:
  tool_ok     called the tool the question needs; for an out-of-coverage
              question, got the refusal from a tool rather than its own knowledge
  args_ok     passed every value the question states, and none it does not
  coords_ok   every coordinate given to the trip tool came from a place lookup
              in the same run - the kit's rule: never guess a coordinate
  stop_ok     when a tool recommended a stop, the answer names the first one
  verdict_ok  the answer's verdict is the expected one        } read by a
  faithful    no claim or figure that the tool results don't back } judge model
plus wall-clock latency and the router's own tokens and cost. Runs are
interleaved in a seeded random order, so drift in API latency over a session
does not line up with one condition.

Results go to logs/experiments/<stamp>/ (runs.jsonl, summary.json, summary.md)
and to W&B, one run per condition in a shared group.
"""
from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import os
import random
import re
import statistics
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))                          # src/: llm
sys.path.insert(0, str(HERE.parent.parent / "application"))   # ui: the console's router

import llm  # noqa: E402
import ui  # noqa: E402

PROMPTS = HERE / "prompts"
TASKS = HERE / "tasks.charging.json"
OUT = Path(os.environ.get("USAGE_LOG") or HERE.parent / "usage.jsonl").parent / "experiments"
CONDITIONS = ("zero_shot", "few_shot", "scaffold")
TRIP, NEAREST = "assess_ev_trip_feasibility", "find_nearest_charger"
BRISBANE = timezone(timedelta(hours=10))

# USD per million tokens. llm.py's logger drops prompt-cache counts, which the
# longer few-shot prompt can incur, so router usage is read from each response.
ROUTER_PRICES = {"claude-haiku-4-5": {"input_tokens": 1.00, "output_tokens": 5.00,
                                      "cache_creation_input_tokens": 1.25,
                                      "cache_read_input_tokens": 0.10}}
JUDGE_MODEL = "claude-opus-5-5"
JUDGE_PRICE = {"input_tokens": 4.00, "output_tokens": 20.00}

# What a correct caller does with each question, labelled by hand from the
# question's wording and from the tool results in tasks.charging.json:
#   start of the question, the verdict the answer should give, the tool the
#   question needs (None where declining is the right outcome), and every value
#   the question states - which the trip tool should receive, and nothing else.
SPEC = [
    ("Can I charge my EV at the Sydney Opera House", "declined_out_of_scope", None, {}),
    ("Where can I charge my EV near the University of Queensland", "nearest_listed", NEAREST, {}),
    ("I'm at UQ St Lucia with 80 km of range left in a car that does 400 km", "requires_charging", TRIP,
     {"remaining_range_km": 80, "full_range_km": 400}),
    ("Same trip from UQ St Lucia to Toowoomba, but the battery shows 250 km", "feasible", TRIP,
     {"remaining_range_km": 250}),
    ("I'm in Kilcoy with 20 km of range left", "infeasible", TRIP, {"remaining_range_km": 20}),
    ("Can I drive from UQ St Lucia to Melbourne", "declined_out_of_scope", None, {"remaining_range_km": 200}),
    ("Malformed call: the vehicle reports a negative remaining range", "declined_invalid_input", None,
     {"remaining_range_km": -50}),
    ("UQ St Lucia to Toowoomba with 80 km of range, but I never said", "requires_charging", TRIP,
     {"remaining_range_km": 80}),
    ("I drive an older Nissan Leaf", "requires_charging", TRIP,
     {"remaining_range_km": 80, "full_range_km": 150, "connector_type": "CHAdeMO", "vehicle_max_charge_kw": 50}),
    ("UQ St Lucia to Toowoomba with 120 km of range in a car that takes 50 kW", "requires_charging", TRIP,
     {"remaining_range_km": 120, "full_range_km": 400, "vehicle_max_charge_kw": 50}),
    ("Malformed call: a vehicle consumption of 0 kWh", "declined_invalid_input", None,
     {"consumption_kwh_per_100km": 0}),
    ("I'm at UQ St Lucia with only 5 km of range left", "requires_charging", TRIP, {"remaining_range_km": 5}),
]
# Optional trip arguments and their defaults. Passing one the question never
# stated, at anything but its default, is an invented value.
OPTIONAL = {"full_range_km": None, "connector_type": None, "vehicle_max_charge_kw": None,
            "consumption_kwh_per_100km": 18.0, "safety_margin_pct": 10}
# Words too generic to identify a station by.
STOPWORDS = {"qesh", "station", "charging", "charger", "public", "carpark", "centre", "center",
             "shopping", "street", "road", "highway", "electric", "super", "pulse", "fast"}

VERDICTS = ["feasible", "requires_charging", "infeasible", "declined_out_of_scope",
            "declined_invalid_input", "nearest_listed", "no_clear_verdict"]
JUDGE_SCHEMA = {
    "type": "object",
    "properties": {
        "stated_verdict": {"type": "string", "enum": VERDICTS},
        "unsupported_claims": {"type": "array", "items": {"type": "string"}},
        "misattributed_figures": {"type": "array", "items": {"type": "string"}},
    },
    "required": ["stated_verdict", "unsupported_claims", "misattributed_figures"],
    "additionalProperties": False,
}
JUDGE_SYSTEM = """You grade one answer written by an assistant that used tools to answer a driver's \
question about an electric-vehicle trip in Queensland. You are given the tool descriptions the \
assistant could read, the question, every tool call the assistant made with the tool's full JSON \
result, and the assistant's final answer. Grade only against the tool descriptions and the tool \
results; do not use outside knowledge of places, chargers or vehicles. A statement that restates a \
tool description is supported.

stated_verdict - the conclusion the answer gives the driver:
  feasible: the trip can be made without charging
  requires_charging: the trip needs a charging stop
  infeasible: the trip cannot be made because no charger is reachable
  declined_out_of_scope: the answer declines because the place or trip is outside what the tools cover
  declined_invalid_input: the answer declines because a value in the question is invalid or missing
  nearest_listed: the answer lists nearby charging stations without a trip verdict
  no_clear_verdict: none of these clearly applies, or there is no answer

unsupported_claims - each specific factual statement in the answer that neither a tool result nor \
a tool description supports, \
such as a price, live availability, a plug type, a distance or a time that appears in no result. \
Saying something is not published or not available is not an unsupported claim. Rounding a figure \
to a sensible precision is not one. General advice, such as checking with an operator, is not one.

misattributed_figures - each figure that does appear in a result but is attached in the answer to \
the wrong quantity or the wrong station."""


class UsageTap:
    """Stands in for the httpx module inside llm, so every Claude call the router
    makes in this process is counted in full - cache reads and writes included -
    without editing llm.py. The agent's own calls run in its server process and
    are not counted: this measures the caller."""

    def __init__(self, real):
        self.real, self.calls = real, []

    def post(self, *args, **kwargs):
        response = self.real.post(*args, **kwargs)
        try:
            self.calls.append(response.json().get("usage", {}))
        except Exception:  # noqa: BLE001 - a failed call still raises inside llm.ask
            self.calls.append({})
        return response

    def __getattr__(self, name):
        return getattr(self.real, name)


TAP = UsageTap(llm.httpx)
llm.httpx = TAP


def load_prompts() -> dict[str, str]:
    prompts = {c: (PROMPTS / f"{c}.txt").read_text(encoding="utf-8").rstrip("\n") for c in CONDITIONS}
    if prompts["zero_shot"] != ui.ROUTER_SYSTEM:
        raise SystemExit("prompts/zero_shot.txt no longer matches ui.ROUTER_SYSTEM; the baseline must be verbatim.")
    for c in CONDITIONS[1:]:
        if not prompts[c].startswith(prompts["zero_shot"]):
            raise SystemExit(f"prompts/{c}.txt must begin with the baseline, so the addition is the only difference.")
    return prompts


def calls_of(trace: list[dict]) -> list[dict]:
    out = []
    for step in trace:
        if step.get("kind") == "call":
            out.append({"tool": step["tool"], "arguments": step.get("arguments") or {},
                        "status": step.get("status"), "result": step.get("result") or {}})
        elif step.get("kind") == "error":
            out.append({"tool": step.get("tool"), "arguments": {}, "status": "error",
                        "result": {"error": step.get("text")}})
    return out


def same(a, b) -> bool:
    if a is None or b is None:
        return a is b
    if isinstance(b, str) or isinstance(a, str):
        return str(a).lower() == str(b).lower()
    try:
        return abs(float(a) - float(b)) < 1e-6
    except (TypeError, ValueError):
        return False


def tool_ok(spec_tool, verdict, calls) -> bool:
    if spec_tool:
        return any(c["tool"] == spec_tool for c in calls)
    if verdict == "declined_out_of_scope":
        return any(c["status"] == "out_of_scope" for c in calls)
    return True  # invalid input: declining outright and declining via the tool are both right


def args_ok(stated: dict, calls: list[dict]):
    trips = [c for c in calls if c["tool"] == TRIP]
    if not trips:
        return None
    given = trips[-1]["arguments"]
    if any(not same(given.get(k), v) for k, v in stated.items()):
        return False
    if any(k in given and not same(given[k], d) for k, d in OPTIONAL.items() if k not in stated):
        return False
    return not ("remaining_range_km" not in stated and "remaining_range_km" in given)


def coords_ok(calls: list[dict]):
    """Every point handed to the trip tool must be one a place lookup returned in
    this run. 5e-4 degrees (about 50 m) forgives rounding, not a recalled value."""
    trips = [c for c in calls if c["tool"] == TRIP]
    if not trips:
        return None
    looked_up = [(c["result"]["lat"], c["result"]["lon"]) for c in calls
                 if c["tool"] == "geocode_place" and "lat" in c["result"]]
    def sourced(lat, lon):
        try:
            return any(abs(float(lat) - a) < 5e-4 and abs(float(lon) - b) < 5e-4 for a, b in looked_up)
        except (TypeError, ValueError):
            return False
    return all(sourced(t["arguments"].get(f"{end}_lat"), t["arguments"].get(f"{end}_lon"))
               for t in trips for end in ("origin", "dest"))


def first_item(calls: list[dict]) -> str | None:
    for c in reversed(calls):
        r = c["result"]
        if c["tool"] == TRIP and r.get("recommended_stops"):
            return r["recommended_stops"][0]["name"]
        if c["tool"] == NEAREST and r.get("nearest"):
            return r["nearest"][0]["name"]
    return None


def names(answer: str, station: str) -> bool:
    # Whole words only: "east" (East Brisbane) is inside "at least".
    words = [w for w in re.findall(r"[a-z]+", station.lower()) if len(w) >= 4 and w not in STOPWORDS]
    text = answer.lower()
    if not words:
        return station.lower() in text
    return any(re.search(rf"\b{re.escape(w)}\b", text) for w in words)


def router_usage(usages: list[dict], model: str) -> dict:
    prices = ROUTER_PRICES[model]
    totals = {k: sum(u.get(k) or 0 for u in usages) for k in prices}
    return {**totals, "calls": len(usages),
            "usd": round(sum(totals[k] / 1e6 * prices[k] for k in prices), 6)}


def score_rules(row: dict) -> None:
    """The checks that need no model: from the calls made and the answer given."""
    _, verdict, spec_tool, stated = SPEC[row["case"] - 1]
    calls, answer = row["calls"], row["answer"]
    top = first_item(calls) if verdict in ("requires_charging", "nearest_listed") else None
    row.update(tool_ok=tool_ok(spec_tool, verdict, calls), args_ok=args_ok(stated, calls),
               coords_ok=coords_ok(calls), first_item=top,
               stop_ok=(names(answer, top) if answer else False) if top else None)


async def route(job, tasks, prompts, agents, model) -> dict:
    repeat, index, condition = job
    case = tasks[index]
    ui.ROUTER_SYSTEM = prompts[condition]
    TAP.calls = []
    started, error, trace = time.perf_counter(), None, []
    try:
        trace = await ui.run_with_model({"text": case["prompt"]}, agents)
    except Exception as exc:  # noqa: BLE001 - recorded as a failed run, not a crash
        error = f"{type(exc).__name__}: {exc}"[:300]
    latency = round(time.perf_counter() - started, 2)
    calls = calls_of(trace)
    answer = next((s["text"] for s in reversed(trace) if s.get("kind") == "answer"), None)
    hit_limit = bool(answer and answer.startswith("Stopped after"))
    row = {
        "condition": condition, "repeat": repeat, "case": index + 1, "prompt": case["prompt"],
        "expected_verdict": SPEC[index][1], "calls": calls, "tools_called": [c["tool"] for c in calls],
        "answer": None if hit_limit else answer, "hit_step_limit": hit_limit, "error": error,
        "latency_s": latency, "router": router_usage(TAP.calls, model),
    }
    score_rules(row)
    return row


async def judge(client, row: dict, menu: str, gate: asyncio.Semaphore) -> None:
    if not row["answer"]:
        row.update(stated_verdict="no_clear_verdict", unsupported_claims=[], misattributed_figures=[],
                   judge_model=None, judge_usd=0.0)
        return
    shown = [{k: c[k] for k in ("tool", "arguments", "result")} for c in row["calls"]]
    user = (f"TOOL DESCRIPTIONS THE ASSISTANT COULD READ:{menu}\n\nQUESTION:\n{row['prompt']}\n\n"
            f"TOOL CALLS, IN ORDER, WITH FULL RESULTS:\n{json.dumps(shown, ensure_ascii=False)}\n\n"
            f"ANSWER:\n{row['answer']}")
    async with gate:
        response = await client.beta.messages.create(
            model=JUDGE_MODEL,
            max_tokens=16000,
            betas=["server-side-fallback-2026-07-01"],
            fallbacks="default",
            output_config={"effort": "medium",
                           "format": {"type": "json_schema", "schema": JUDGE_SCHEMA}},
            system=JUDGE_SYSTEM,
            messages=[{"role": "user", "content": user}],
        )
    if response.stop_reason == "refusal":
        raise RuntimeError("the judge declined to grade this answer")
    graded = json.loads(next(b.text for b in response.content if b.type == "text"))
    usage = response.usage
    row.update(graded, judge_model=response.model,
               judge_usd=round(usage.input_tokens / 1e6 * JUDGE_PRICE["input_tokens"]
                               + usage.output_tokens / 1e6 * JUDGE_PRICE["output_tokens"], 6))


def finish(row: dict) -> None:
    graded = "stated_verdict" in row
    row["verdict_ok"] = row["stated_verdict"] == row["expected_verdict"] if graded else None
    row["faithful"] = (not row["unsupported_claims"] and not row["misattributed_figures"]) if graded else None
    checks = [row[k] for k in ("tool_ok", "args_ok", "coords_ok", "stop_ok", "verdict_ok", "faithful")]
    row["all_ok"] = bool(row["answer"]) and not row["error"] and all(c is not False for c in checks) \
        and None not in (row["verdict_ok"], row["faithful"])


METRICS = ("tool_ok", "args_ok", "coords_ok", "stop_ok", "verdict_ok", "faithful", "all_ok")


def rate(rows, key):
    values = [r[key] for r in rows if r.get(key) is not None]
    return (round(sum(values) / len(values), 3), len(values)) if values else (None, 0)


def summarise(rows: list[dict], conditions) -> dict:
    out = {}
    for c in conditions:
        mine = [r for r in rows if r["condition"] == c]
        out[c] = {
            "runs": len(mine),
            **{m: dict(zip(("rate", "n"), rate(mine, m))) for m in METRICS},
            "step_limit_hits": sum(r["hit_step_limit"] for r in mine),
            "errors": sum(bool(r["error"]) for r in mine),
            "latency_s_median": statistics.median(r["latency_s"] for r in mine),
            "router_usd_per_run": round(statistics.mean(r["router"]["usd"] for r in mine), 6),
            "router_input_tokens_per_run": round(statistics.mean(
                r["router"]["input_tokens"] + r["router"]["cache_creation_input_tokens"]
                + r["router"]["cache_read_input_tokens"] for r in mine)),
            "router_output_tokens_per_run": round(statistics.mean(r["router"]["output_tokens"] for r in mine)),
            "per_case_all_ok": {r["case"]: rate([x for x in mine if x["case"] == r["case"]], "all_ok")[0]
                                for r in mine},
        }
    return out


def markdown(summary: dict, meta: dict) -> str:
    conds = list(summary)
    pct = lambda v: "-" if v is None else f"{v * 100:.0f}%"  # noqa: E731
    lines = [f"# Prompt architecture experiment - {meta['stamp']}", "",
             f"Router `{meta['router_model']}`, judge `{meta['judge_model']}`, {meta['repeats']} repeat(s) "
             f"of {meta['cases']} question(s) per condition, seed {meta['seed']}, OCM snapshot {meta['snapshot']}.", "",
             "| Metric | " + " | ".join(conds) + " |", "|---|" + "---|" * len(conds)]
    for m in METRICS:
        lines.append(f"| {m} | " + " | ".join(
            f"{pct(summary[c][m]['rate'])} (n={summary[c][m]['n']})" for c in conds) + " |")
    for key, label in (("step_limit_hits", "step-limit hits"), ("errors", "errors"),
                       ("latency_s_median", "median latency (s)"), ("router_usd_per_run", "router USD per run"),
                       ("router_input_tokens_per_run", "router input tokens per run"),
                       ("router_output_tokens_per_run", "router output tokens per run")):
        lines.append(f"| {label} | " + " | ".join(str(summary[c][key]) for c in conds) + " |")
    lines += ["", "## all_ok by question", "", "| Q | " + " | ".join(conds) + " |", "|---|" + "---|" * len(conds)]
    for q in sorted({q for c in conds for q in summary[c]["per_case_all_ok"]}):
        lines.append(f"| {q} | " + " | ".join(pct(summary[c]["per_case_all_ok"].get(q)) for c in conds) + " |")
    return "\n".join(lines) + "\n"


def log_wandb(rows, summary, meta, prompts) -> str | None:
    try:
        import wandb
    except ImportError:
        print("wandb is not installed; skipping W&B logging")
        return None
    project = os.environ.get("WANDB_PROJECT", "reit7820-eval")
    entity = os.environ.get("WANDB_ENTITY") or None
    if "/" in project:
        entity, project = project.split("/", 1)
    columns = ["case", "repeat", "prompt", "tools_called", "answer", "expected_verdict", "stated_verdict",
               *METRICS, "unsupported_claims", "misattributed_figures", "latency_s", "router_usd"]
    url = None
    for c in summary:
        run = wandb.init(entity=entity, project=project, group=f"prompt-architecture-{meta['stamp']}",
                         name=f"{c}-{meta['stamp']}", job_type="prompt-architecture",
                         config={**meta, "condition": c,
                                 "prompt_sha256": hashlib.sha256(prompts[c].encode()).hexdigest()[:16]})
        data = [[r["case"], r["repeat"], r["prompt"], ", ".join(r["tools_called"]), r["answer"],
                 r["expected_verdict"], r.get("stated_verdict"), *[r.get(m) for m in METRICS],
                 "; ".join(r.get("unsupported_claims") or []), "; ".join(r.get("misattributed_figures") or []),
                 r["latency_s"], r["router"]["usd"]] for r in rows if r["condition"] == c]
        s = summary[c]
        run.log({"runs": wandb.Table(columns=columns, data=data),
                 **{f"rate/{m}": s[m]["rate"] for m in METRICS},
                 "latency_s_median": s["latency_s_median"], "router_usd_per_run": s["router_usd_per_run"],
                 "step_limit_hits": s["step_limit_hits"]})
        url = getattr(run, "project_url", None)
        url = url() if callable(url) else url
        run.finish()
    return url


async def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--repeats", type=int, default=3)
    ap.add_argument("--cases", help="comma-separated 1-based question numbers (default: all)")
    ap.add_argument("--conditions", default=",".join(CONDITIONS))
    ap.add_argument("--seed", type=int, default=20261020)
    ap.add_argument("--no-judge", action="store_true", help="route and score only; skip the judge model")
    ap.add_argument("--no-wandb", action="store_true")
    ap.add_argument("--rejudge", metavar="RUNS_JSONL",
                    help="re-score a saved runs.jsonl with the current rules and judge, without routing again")
    ap.add_argument("--relog", metavar="RESULTS_DIR",
                    help="upload a finished experiment's saved results to W&B; no model is called")
    ap.add_argument("--rescore", metavar="RESULTS_DIR",
                    help="recompute the rule-based scores of saved results, keeping the judge's grades; "
                         "no model is called")
    a = ap.parse_args()

    if a.rescore:
        source = Path(a.rescore)
        rows = [json.loads(line) for line in (source / "runs.jsonl").read_text(encoding="utf-8").splitlines() if line.strip()]
        saved = json.loads((source / "summary.json").read_text(encoding="utf-8"))
        for r in rows:
            score_rules(r)
            finish(r)
        meta = {**saved["meta"], "stamp": f"{saved['meta']['stamp']}-rescored", "rescored_from": str(source)}
        summary = summarise(rows, meta["conditions"])
        folder = OUT / meta["stamp"]
        folder.mkdir(parents=True, exist_ok=True)
        (folder / "runs.jsonl").write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows), encoding="utf-8")
        (folder / "summary.json").write_text(json.dumps({"meta": meta, "summary": summary}, indent=2), encoding="utf-8")
        (folder / "summary.md").write_text(markdown(summary, meta), encoding="utf-8")
        print(markdown(summary, meta) + f"\nresults in {folder}")
        return 0

    if a.relog:
        folder = Path(a.relog)
        rows = [json.loads(line) for line in (folder / "runs.jsonl").read_text(encoding="utf-8").splitlines() if line.strip()]
        saved = json.loads((folder / "summary.json").read_text(encoding="utf-8"))
        url = log_wandb(rows, saved["summary"], saved["meta"], load_prompts())
        print(f"W&B: {url}")
        return 0

    if not llm.configured():
        raise SystemExit("ANTHROPIC_API_KEY is not set.")
    model = llm.model_name()
    if model not in ROUTER_PRICES:
        raise SystemExit(f"No prices recorded for router model {model}; add them to ROUTER_PRICES.")
    tasks = json.loads(TASKS.read_text(encoding="utf-8"))
    if len(tasks) != len(SPEC) or any(not t["prompt"].startswith(s[0]) for t, s in zip(tasks, SPEC)):
        raise SystemExit("SPEC no longer lines up with tasks.charging.json; relabel it.")
    prompts = load_prompts()
    conditions = [c for c in a.conditions.split(",") if c]
    cases = [int(x) - 1 for x in a.cases.split(",")] if a.cases else list(range(len(tasks)))

    client = None
    if not a.no_judge:
        try:
            import anthropic
        except ImportError:
            raise SystemExit("The judge needs the Anthropic SDK: pip install anthropic==1.15.0") from None
        client = anthropic.AsyncAnthropic()

    agents = await ui.discover()
    if not all(x["online"] for x in agents):
        raise SystemExit(f"agent offline: {[x.get('error') for x in agents]}")
    # What the router read when choosing tools, and so what the judge may treat as known.
    menu = ui.tool_menu(agents)
    stamp = datetime.now(BRISBANE).strftime("%Y%m%d-%H%M%S")

    if a.rejudge:
        rows = [json.loads(line) for line in Path(a.rejudge).read_text(encoding="utf-8").splitlines() if line.strip()]
        for r in rows:
            for key in ("stated_verdict", "unsupported_claims", "misattributed_figures", "judge_model",
                        "judge_usd", "judge_error", "verdict_ok", "faithful", "all_ok"):
                r.pop(key, None)
            score_rules(r)
        conditions = [c for c in CONDITIONS if any(r["condition"] == c for r in rows)]
        cases = sorted({r["case"] - 1 for r in rows})
        a.repeats = max(r["repeat"] for r in rows)
        print(f"re-scoring {len(rows)} saved runs from {a.rejudge}")
    else:
        rows = []
    jobs = [] if a.rejudge else [(r + 1, i, c) for r in range(a.repeats) for i in cases for c in conditions]
    random.Random(a.seed).shuffle(jobs)
    if jobs:
        print(f"{len(jobs)} runs: {len(conditions)} condition(s) x {len(cases)} question(s) x {a.repeats} "
              f"repeat(s); router {model}; judge {JUDGE_MODEL if client else 'off'}")

    original = ui.ROUTER_SYSTEM
    try:
        for n, job in enumerate(jobs, 1):
            row = await route(job, tasks, prompts, agents, model)
            rows.append(row)
            print(f"  [{n:>3}/{len(jobs)}] {row['condition']:<9} Q{row['case']:<2} r{row['repeat']}  "
                  f"tools={','.join(t.split('_')[0] for t in row['tools_called']) or '-':<22} "
                  f"tool={row['tool_ok']!s:<5} args={row['args_ok']!s:<5} coords={row['coords_ok']!s:<5} "
                  f"stop={row['stop_ok']!s:<5} "
                  f"{row['latency_s']:>5.1f}s ${row['router']['usd']:.4f}"
                  + ("  STEP LIMIT" if row["hit_step_limit"] else "") + (f"  ERROR {row['error']}" if row["error"] else ""))
    finally:
        ui.ROUTER_SYSTEM = original

    if client:
        print("judging...")
        gate = asyncio.Semaphore(4)
        outcomes = await asyncio.gather(*(judge(client, r, menu, gate) for r in rows), return_exceptions=True)
        for r, outcome in zip(rows, outcomes):
            if isinstance(outcome, Exception):
                r["judge_error"] = f"{type(outcome).__name__}: {outcome}"[:300]
    for r in rows:
        finish(r)

    snapshot = json.loads((HERE.parent / "snapshots" / "ocm_qld.json").read_text(encoding="utf-8"))["fetched_at"]
    meta = {"stamp": stamp, "router_model": model, "judge_model": JUDGE_MODEL if client else None,
            "repeats": a.repeats, "cases": len(cases), "seed": a.seed, "snapshot": snapshot,
            "conditions": conditions, "max_steps": ui.MAX_STEPS, "rejudged_from": a.rejudge}
    summary = summarise(rows, conditions)
    folder = OUT / stamp
    folder.mkdir(parents=True, exist_ok=True)
    (folder / "tool_menu.txt").write_text(menu.strip() + "\n", encoding="utf-8")
    (folder / "runs.jsonl").write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows), encoding="utf-8")
    (folder / "summary.json").write_text(json.dumps({"meta": meta, "summary": summary}, indent=2), encoding="utf-8")
    (folder / "summary.md").write_text(markdown(summary, meta), encoding="utf-8")
    print("\n" + markdown(summary, meta))
    judge_usd = sum(r.get("judge_usd") or 0 for r in rows)
    router_usd = sum(r["router"]["usd"] for r in rows)
    print(f"cost: router ${router_usd:.4f}, judge ${judge_usd:.4f}; judge errors: "
          f"{sum('judge_error' in r for r in rows)}; results in {folder}")
    if not a.no_wandb:
        url = log_wandb(rows, summary, meta, prompts)
        if url:
            print(f"W&B: {url}")
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
