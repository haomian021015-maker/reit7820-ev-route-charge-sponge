# Prompt architecture experiment - 20261102-043628

Router `claude-sonnet-5-5`, judge `claude-opus-5-5`, 3 repeat(s) of 24 question(s) from `tasks.heldout.json` per condition, seed 20261102, OCM snapshot 2026-10-15T18:30:22+10:00.

| Metric | zero_shot | few_shot |
|---|---|---|
| tool_ok | 88% (n=72) | 100% (n=72) |
| args_ok | 94% (n=48) | 94% (n=48) |
| coords_ok | 100% (n=48) | 100% (n=48) |
| stop_ok | 97% (n=33) | 97% (n=33) |
| verdict_ok | 96% (n=72) | 94% (n=72) |
| faithful | 89% (n=72) | 99% (n=72) |
| all_ok | 82% (n=72) | 93% (n=72) |
| step-limit hits | 0 | 1 |
| errors | 0 | 0 |
| median latency (s) | 10.885 | 9.33 |
| router USD per run | 0.022938 | 0.021689 |
| router input tokens per run | 8415 | 15015 |
| router output tokens per run | 611 | 556 |

## all_ok by question

| Q | zero_shot | few_shot |
|---|---|---|
| 1 | 0% | 100% |
| 2 | 0% | 100% |
| 3 | 67% | 100% |
| 4 | 33% | 67% |
| 5 | 100% | 100% |
| 6 | 0% | 0% |
| 7 | 100% | 100% |
| 8 | 100% | 100% |
| 9 | 100% | 100% |
| 10 | 100% | 100% |
| 11 | 100% | 100% |
| 12 | 100% | 100% |
| 13 | 100% | 100% |
| 14 | 100% | 100% |
| 15 | 100% | 100% |
| 16 | 100% | 100% |
| 17 | 100% | 100% |
| 18 | 67% | 100% |
| 19 | 100% | 100% |
| 20 | 100% | 100% |
| 21 | 100% | 67% |
| 22 | 100% | 100% |
| 23 | 100% | 100% |
| 24 | 100% | 100% |
