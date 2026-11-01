"""
analyse_prompt_experiment.py - the statistics behind the prompt-architecture results.

    python src/eval/analyse_prompt_experiment.py results/prompt-architecture-20261020

Reads a results folder written by run_prompt_experiment.py and writes
analysis.md beside it: each metric with a 95% Wilson interval, and each pair of
conditions compared by a permutation test stratified by question - condition
labels are shuffled only within a question, so a hard question cannot pass for
a condition effect. Standard library only, so it runs anywhere.
"""
from __future__ import annotations

import json
import math
import random
import sys
from collections import defaultdict
from pathlib import Path

CONDITIONS = ("zero_shot", "few_shot", "scaffold")
METRICS = ("tool_ok", "args_ok", "coords_ok", "stop_ok", "verdict_ok", "faithful", "all_ok")
PAIRS = (("zero_shot", "few_shot"), ("zero_shot", "scaffold"), ("few_shot", "scaffold"))
ITERATIONS, SEED = 20000, 7


def wilson(k: int, n: int, z: float = 1.96) -> tuple[float, float]:
    p, d = k / n, 1 + z * z / n
    centre, half = (p + z * z / (2 * n)) / d, z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return centre - half, centre + half


def permutation(rows: list[dict], metric: str, a: str, b: str) -> tuple[float, float]:
    """Difference b - a in the metric's rate, and its two-sided p-value."""
    by_q = defaultdict(list)
    for r in rows:
        if r["condition"] in (a, b) and r[metric] is not None:
            by_q[r["case"]].append((r["condition"], int(r[metric])))

    def diff(groups) -> float:
        xb = [v for g in groups.values() for c, v in g if c == b]
        xa = [v for g in groups.values() for c, v in g if c == a]
        return sum(xb) / len(xb) - sum(xa) / len(xa)

    observed, rng, extreme = diff(by_q), random.Random(SEED), 0
    for _ in range(ITERATIONS):
        shuffled = {}
        for q, g in by_q.items():
            labels = [c for c, _ in g]
            rng.shuffle(labels)
            shuffled[q] = [(labels[i], v) for i, (_, v) in enumerate(g)]
        extreme += abs(diff(shuffled)) >= abs(observed) - 1e-12
    return observed, (extreme + 1) / (ITERATIONS + 1)


def main(folder: Path) -> str:
    rows = [json.loads(line) for line in (folder / "runs.jsonl").read_text(encoding="utf-8").splitlines() if line.strip()]
    meta = json.loads((folder / "summary.json").read_text(encoding="utf-8"))["meta"]
    # Only the conditions this experiment ran, and only the pairs among them.
    conditions = [c for c in CONDITIONS if any(r["condition"] == c for r in rows)]
    pairs = [(a, b) for a, b in PAIRS if a in conditions and b in conditions]
    lines = [f"# Statistics - {meta['stamp']}", "",
             f"{len(rows)} runs. Rates with 95% Wilson intervals; differences by a permutation test "
             f"stratified by question ({ITERATIONS} shuffles, seed {SEED}, two-sided).", "",
             "| Metric | " + " | ".join(conditions) + " |", "|---|" + "---|" * len(conditions)]
    for m in METRICS:
        cells = []
        for c in conditions:
            values = [r[m] for r in rows if r["condition"] == c and r[m] is not None]
            k, n = sum(values), len(values)
            lo, hi = wilson(k, n)
            cells.append(f"{k}/{n} = {k / n:.0%} [{lo:.0%}, {hi:.0%}]")
        lines.append(f"| {m} | " + " | ".join(cells) + " |")
    lines += ["", "| Metric | Comparison | Difference | p |", "|---|---|---|---|"]
    for m in METRICS:
        for a, b in pairs:
            d, p = permutation(rows, m, a, b)
            lines.append(f"| {m} | {b} vs {a} | {d * 100:+.1f} pts | {p:.3f} |")
    if len(pairs) > 1:
        lines += ["", f"{len(pairs)} pairwise comparisons per metric: at a family-wise 0.05, a difference needs "
                  f"p < {0.05 / len(pairs):.3f} (Bonferroni) to be read as more than suggestive."]
    else:
        lines += ["", "One comparison per metric: a difference needs p < 0.05."]
    text = "\n".join(lines) + "\n"
    (folder / "analysis.md").write_text(text, encoding="utf-8")
    return text


if __name__ == "__main__":
    print(main(Path(sys.argv[1])))
