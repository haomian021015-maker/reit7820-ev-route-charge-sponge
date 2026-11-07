"""
check_explanations.py - does the agent's written explanation keep to its own figures?

    python src/eval/check_explanations.py OUT_DIR RESULTS_DIR [RESULTS_DIR ...]

The tool computes estimated_road_m as straight line x 1.3, then a model writes a
short explanation from those figures. The judge's flags pointed to a pattern: the
explanation sometimes applies the 1.3 a second time, so a road distance of 100 km
appears as 130 km. This script measures that over every saved trip call.

An explanation counts as affected when it states a distance within 1 km of
estimated_road_m x 1.3 that matches none of the true figures in the same result
(road, straight line, range, usable range, shortfall, or a stop's distances). It
is a pattern match, so it is a close estimate rather than an exact count. The check
itself is in explanation_check.py, which the agent now also applies to its own
explanations; the runs saved here predate that.

Writes OUT_DIR/summary.md.
"""
from __future__ import annotations

import json
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from explanation_check import distances, doubled  # noqa: E402

TRIP = "assess_ev_trip_feasibility"


def main(out: Path, folders: list[Path]) -> int:
    calls, hits = Counter(), Counter()
    lines = ["# Agent explanations against the agent's own figures", "",
             "Every trip call with an explanation in the saved runs. Affected = the explanation states "
             "estimated_road_m x road_factor as a distance (the factor applied twice).", "",
             "| Folder | Calls | Affected | Answers repeating it | ...of those judged unfaithful |", "|---|---|---|---|---|"]
    for folder in folders:
        n = bad = repeated = caught = 0
        for line in (folder / "runs.jsonl").read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            run = json.loads(line)
            for call in run["calls"]:
                if call["tool"] != TRIP or not call["result"].get("explanation") or not call["result"].get("trip"):
                    continue
                n += 1
                verdict = call["result"]["feasibility"]
                calls[verdict] += 1
                wrong = doubled(call["result"]["explanation"], call["result"])
                if wrong is None:
                    continue
                bad += 1
                hits[verdict] += 1
                if any(abs(v - wrong) <= 1 for v in distances(run["answer"] or "")):
                    repeated += 1
                    caught += run["faithful"] is False
        lines.append(f"| {folder.name} | {n} | {bad} | {repeated} | {caught} |")
    lines += ["", "| Verdict | Calls | Affected |", "|---|---|---|"]
    lines += [f"| {v} | {calls[v]} | {hits[v]} ({hits[v] / calls[v]:.0%}) |" for v in sorted(calls)]
    lines += [f"| All | {sum(calls.values())} | {sum(hits.values())} ({sum(hits.values()) / sum(calls.values()):.0%}) |", ""]
    text = "\n".join(lines)
    out.mkdir(parents=True, exist_ok=True)
    (out / "summary.md").write_text(text, encoding="utf-8")
    print(text)
    return 0


if __name__ == "__main__":
    if len(sys.argv) < 3:
        raise SystemExit(__doc__)
    raise SystemExit(main(Path(sys.argv[1]), [Path(p) for p in sys.argv[2:]]))
