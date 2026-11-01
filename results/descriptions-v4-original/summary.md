# Prompt architecture experiment - 20261102-050819

Router `claude-haiku-4-5`, judge `claude-opus-5-5`, 3 repeat(s) of 12 question(s) from `tasks.charging.json` per condition, seed 20261020, OCM snapshot 2026-10-15T18:30:22+10:00.

| Metric | zero_shot |
|---|---|
| tool_ok | 97% (n=36) |
| args_ok | 100% (n=24) |
| coords_ok | 58% (n=24) |
| stop_ok | 83% (n=18) |
| verdict_ok | 100% (n=36) |
| faithful | 53% (n=36) |
| all_ok | 39% (n=36) |
| step-limit hits | 0 |
| errors | 0 |
| median latency (s) | 8.26 |
| router USD per run | 0.008103 |
| router input tokens per run | 5803 |
| router output tokens per run | 460 |

## all_ok by question

| Q | zero_shot |
|---|---|
| 1 | 67% |
| 2 | 33% |
| 3 | 100% |
| 4 | 0% |
| 5 | 0% |
| 6 | 0% |
| 7 | 33% |
| 8 | 33% |
| 9 | 0% |
| 10 | 100% |
| 11 | 67% |
| 12 | 33% |
