# Prompt architecture experiment - 20261102-051327

Router `claude-haiku-4-5`, judge `claude-opus-5-5`, 3 repeat(s) of 24 question(s) from `tasks.heldout.json` per condition, seed 20261102, OCM snapshot 2026-10-15T18:30:22+10:00.

| Metric | zero_shot |
|---|---|
| tool_ok | 94% (n=72) |
| args_ok | 93% (n=56) |
| coords_ok | 84% (n=56) |
| stop_ok | 97% (n=33) |
| verdict_ok | 93% (n=72) |
| faithful | 46% (n=72) |
| all_ok | 38% (n=72) |
| step-limit hits | 0 |
| errors | 0 |
| median latency (s) | 9.075 |
| router USD per run | 0.009749 |
| router input tokens per run | 6772 |
| router output tokens per run | 595 |

## all_ok by question

| Q | zero_shot |
|---|---|
| 1 | 33% |
| 2 | 33% |
| 3 | 0% |
| 4 | 0% |
| 5 | 33% |
| 6 | 0% |
| 7 | 67% |
| 8 | 33% |
| 9 | 100% |
| 10 | 33% |
| 11 | 100% |
| 12 | 67% |
| 13 | 0% |
| 14 | 67% |
| 15 | 33% |
| 16 | 100% |
| 17 | 33% |
| 18 | 33% |
| 19 | 0% |
| 20 | 33% |
| 21 | 0% |
| 22 | 33% |
| 23 | 0% |
| 24 | 67% |
