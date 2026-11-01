"""
pool_experiments.py - analyse two runs of the same experiment as one.

    python src/eval/pool_experiments.py OUT_DIR RESULTS_DIR [RESULTS_DIR ...]

The first prompt experiment (12 questions) and its replication on the held-out
set (24 questions) share the router, the prompts, the agent and the scoring
rules; only the questions differ. Pooled, they give 36 questions per condition.
Each question keeps its own stratum (case numbers are prefixed with the source
folder's position: A1..A12, B1..B24), so the stratified permutation test in
analyse_prompt_experiment.py still only compares conditions within a question.

Writes OUT_DIR/runs.jsonl and summary.json (just the meta the analysis needs),
then runs the analysis, which writes OUT_DIR/analysis.md.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import analyse_prompt_experiment as analysis  # noqa: E402


def main(out: Path, sources: list[Path]) -> int:
    rows, metas = [], []
    for prefix, folder in zip("ABCDEFGH", sources):
        meta = json.loads((folder / "summary.json").read_text(encoding="utf-8"))["meta"]
        metas.append({"folder": folder.name, "router_model": meta["router_model"], "tasks": meta.get("tasks"),
                      "runs": 0})
        for line in (folder / "runs.jsonl").read_text(encoding="utf-8").splitlines():
            if line.strip():
                r = json.loads(line)
                r["case"] = f"{prefix}{r['case']}"
                rows.append(r)
                metas[-1]["runs"] += 1
    if len({m["router_model"] for m in metas}) > 1:
        raise SystemExit("These experiments used different router models; pooling would mix the variable in.")
    out.mkdir(parents=True, exist_ok=True)
    (out / "runs.jsonl").write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows), encoding="utf-8")
    meta = {"stamp": f"pooled ({', '.join(m['folder'] for m in metas)})", "sources": metas}
    (out / "summary.json").write_text(json.dumps({"meta": meta}, indent=2), encoding="utf-8")
    print(analysis.main(out))
    return 0


if __name__ == "__main__":
    if len(sys.argv) < 4:
        raise SystemExit(__doc__)
    raise SystemExit(main(Path(sys.argv[1]), [Path(p) for p in sys.argv[2:]]))
