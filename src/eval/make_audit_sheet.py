"""
make_audit_sheet.py - a sample of judged runs for a person to check by hand.

    python src/eval/make_audit_sheet.py results/<experiment> [--n 4] [--seed 11]
    python src/eval/make_audit_sheet.py results/<experiment> --score

Two of the six checks (verdict_ok, faithful) are read by a judge model. Its
grades are only as good as an audit says they are, and the audit has to be a
person's, so this script does not grade anything itself.

Without --score it samples --n runs per condition (seeded), and writes
audit.md - for each run, the question, the figures the tools returned, the
answer, and the judge's grades - plus audit.csv with one empty row per run for
the person's own verdict. With --score it reads the filled-in audit.csv and
reports how often the person agreed with the judge: on the verdict, on whether
the answer was faithful, and on each claim the judge flagged.
"""
from __future__ import annotations

import argparse
import csv
import json
import random
from pathlib import Path

KEEP = ("matched_name", "lat", "lon", "feasibility", "status", "reason", "trip", "recommended_stops", "nearest",
        "data_gaps", "explanation")
STOP_FIELDS = ("name", "power_kw", "charge_rate_kw", "distance_from_origin_m", "detour_m", "range_to_add_m",
               "energy_to_add_kwh", "charging_time_s", "added_time_s", "completes_trip_after_stop")


def brief(result: dict) -> dict:
    """The fields a person needs to check an answer, without the bulk."""
    out = {k: result[k] for k in KEEP if k in result}
    if "recommended_stops" in out:
        out["recommended_stops"] = [{k: s.get(k) for k in STOP_FIELDS} for s in out["recommended_stops"][:3]]
    if "nearest" in out:
        out["nearest"] = [{k: s.get(k) for k in ("name", "distance_m")} for s in out["nearest"][:3]]
    return out


def sample(folder: Path, n: int, seed: int) -> None:
    rows = [json.loads(line) for line in (folder / "runs.jsonl").read_text(encoding="utf-8").splitlines() if line.strip()]
    rng = random.Random(seed)
    picked = []
    for c in sorted({r["condition"] for r in rows}):
        mine = [r for r in rows if r["condition"] == c and r.get("answer")]
        picked += rng.sample(mine, min(n, len(mine)))
    lines = [f"# Judge audit - {folder.name}", "",
             f"{len(picked)} runs, {n} per condition, seed {seed}. For each run, read the tool results and the "
             "answer, then fill in your own judgement in audit.csv **before** looking at the judge's grades "
             "(they are at the end of each run, below the line).", "",
             "- `my_verdict`: feasible, requires_charging, infeasible, declined_out_of_scope, "
             "declined_invalid_input, nearest_listed, or no_clear_verdict",
             "- `my_faithful`: yes if every specific claim in the answer is backed by a tool result or a tool "
             "description; no otherwise",
             "- `my_flags_agree`: for each claim the judge flagged, is it really unsupported? e.g. 2/2", ""]
    for i, r in enumerate(picked, 1):
        lines += [f"## {i}. {r['condition']} - question {r['case']}, repeat {r['repeat']}", "",
                  f"**Question:** {r['prompt']}", "", "**Tool calls and results:**", ""]
        for c in r["calls"]:
            lines += [f"- `{c['tool']}({json.dumps(c['arguments'], ensure_ascii=False)})`", "",
                      "  ```json", "  " + json.dumps(brief(c["result"]), ensure_ascii=False), "  ```"]
        lines += ["", "**Answer:**", "", *(f"> {x}" for x in (r["answer"] or "").splitlines()), "", "---", "",
                  f"Judge: verdict `{r.get('stated_verdict')}` (expected `{r['expected_verdict']}`); "
                  f"flagged unsupported: {r.get('unsupported_claims') or 'none'}; "
                  f"flagged misattributed: {r.get('misattributed_figures') or 'none'}", ""]
    (folder / "audit.md").write_text("\n".join(lines), encoding="utf-8")
    with (folder / "audit.csv").open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["n", "condition", "case", "repeat", "judge_verdict", "judge_faithful", "judge_flags",
                    "my_verdict", "my_faithful", "my_flags_agree", "notes"])
        for i, r in enumerate(picked, 1):
            flags = len(r.get("unsupported_claims") or []) + len(r.get("misattributed_figures") or [])
            w.writerow([i, r["condition"], r["case"], r["repeat"], r.get("stated_verdict"),
                        "yes" if r.get("faithful") else "no", flags, "", "", "", ""])
    print(f"wrote {folder / 'audit.md'} and {folder / 'audit.csv'} ({len(picked)} runs)")


def score(folder: Path) -> None:
    rows = list(csv.DictReader((folder / "audit.csv").open(encoding="utf-8")))
    done = [r for r in rows if r["my_verdict"].strip() and r["my_faithful"].strip()]
    if not done:
        raise SystemExit("audit.csv has no filled-in rows yet.")
    verdict = sum(r["my_verdict"].strip() == r["judge_verdict"] for r in done)
    faithful = sum(r["my_faithful"].strip().lower() == r["judge_faithful"] for r in done)
    agreed = flagged = 0
    for r in done:
        if r["my_flags_agree"].strip():
            a, b = r["my_flags_agree"].split("/")
            agreed, flagged = agreed + int(a), flagged + int(b)
    missed = sum(r["judge_faithful"] == "yes" and r["my_faithful"].strip().lower() == "no" for r in done)
    text = "\n".join([
        f"# Judge audit result - {folder.name}", "",
        f"{len(done)} runs checked by hand.", "",
        "| | Agreement |", "|---|---|",
        f"| Verdict | {verdict}/{len(done)} |",
        f"| Faithful or not | {faithful}/{len(done)} |",
        f"| Flags confirmed (judge flagged, person agrees) | {agreed}/{flagged} |",
        f"| Missed problems (judge said faithful, person did not) | {missed}/{len(done)} |", ""])
    (folder / "audit_result.md").write_text(text, encoding="utf-8")
    print(text)


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("folder", type=Path)
    ap.add_argument("--n", type=int, default=4, help="runs per condition (default 4)")
    ap.add_argument("--seed", type=int, default=11)
    ap.add_argument("--score", action="store_true", help="score a filled-in audit.csv")
    a = ap.parse_args()
    score(a.folder) if a.score else sample(a.folder, a.n, a.seed)
