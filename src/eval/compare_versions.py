"""
compare_versions.py - did the v4 tool descriptions change how the router used the tool?

    python src/eval/compare_versions.py OUT_DIR --v3 DIR [DIR ...] --v4 DIR [DIR ...]

The prompt experiment found four places where a router misread the v3 tool
descriptions. v4 rewrites those descriptions and reorders the response; the
figures the tool computes are unchanged. This script compares the zero-shot
runs against v3 with the zero-shot runs against v4 on the same questions, the
same router and the same scoring, with the stratified permutation test from
analyse_prompt_experiment.py (labels shuffled only within a question).

Questions are keyed by their task file, so the original and held-out sets can
be combined. The questions each fix was aimed at are also reported on their own.

Writes OUT_DIR/comparison.md.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import analyse_prompt_experiment as analysis  # noqa: E402

METRICS = analysis.METRICS
# The questions each v4 fix was aimed at, by task file and case number.
TARGETS = {
    "Consumption must be > 0 (fix 1)": [("tasks.charging.json", 11), ("tasks.heldout.json", 6)],
    "null means unknown, not no (fix 2)": [("tasks.charging.json", 8), ("tasks.heldout.json", 16)],
    "Call even without optional values (fix 3)": [("tasks.charging.json", 8)],
}


def load(folders: list[Path], label: str) -> list[dict]:
    rows = []
    for folder in folders:
        tasks = json.loads((folder / "summary.json").read_text(encoding="utf-8"))["meta"].get("tasks",
                                                                                            "tasks.charging.json")
        for line in (folder / "runs.jsonl").read_text(encoding="utf-8").splitlines():
            if line.strip():
                r = json.loads(line)
                if r["condition"] == "zero_shot":
                    rows.append({**r, "condition": label, "case": (tasks, r["case"])})
    return rows


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("out", type=Path)
    ap.add_argument("--v3", type=Path, nargs="+", required=True)
    ap.add_argument("--v4", type=Path, nargs="+", required=True)
    a = ap.parse_args()
    rows = load(a.v3, "v3") + load(a.v4, "v4")
    lines = ["# Tool descriptions v3 against v4 - zero-shot router", "",
             f"v3 runs: {', '.join(p.name for p in a.v3)}; v4 runs: {', '.join(p.name for p in a.v4)}. "
             "Same router, questions, seeds and scoring; only the agent's descriptions and response order differ. "
             "Differences by a permutation test stratified by question (20000 shuffles, two-sided).", "",
             "| Metric | v3 | v4 | Difference | p |", "|---|---|---|---|---|"]
    for m in METRICS:
        cells = []
        for label in ("v3", "v4"):
            values = [r[m] for r in rows if r["condition"] == label and r[m] is not None]
            cells.append(f"{sum(values)}/{len(values)} = {sum(values) / len(values):.0%}" if values else "-")
        d, p = analysis.permutation(rows, m, "v3", "v4")
        lines.append(f"| {m} | {cells[0]} | {cells[1]} | {d * 100:+.1f} pts | {p:.3f} |")

    lines += ["", "## The questions each fix was aimed at", "",
              "| Fix | Question | v3 all_ok | v4 all_ok | v3 verdict_ok | v4 verdict_ok | v3 faithful | v4 faithful |",
              "|---|---|---|---|---|---|---|---|"]
    for fix, cases in TARGETS.items():
        for case in cases:
            cell = []
            for m in ("all_ok", "verdict_ok", "faithful"):
                for label in ("v3", "v4"):
                    v = [r[m] for r in rows if r["condition"] == label and r["case"] == case and r[m] is not None]
                    cell.append(f"{sum(v)}/{len(v)}" if v else "-")
            lines.append(f"| {fix} | {case[0].split('.')[1]} Q{case[1]} | " + " | ".join(cell) + " |")
    text = "\n".join(lines) + "\n"
    a.out.mkdir(parents=True, exist_ok=True)
    (a.out / "comparison.md").write_text(text, encoding="utf-8")
    print(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
