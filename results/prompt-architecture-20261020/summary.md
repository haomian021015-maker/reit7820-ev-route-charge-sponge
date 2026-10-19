# Prompt architecture experiment - 20261020-053044-rescored

Router `claude-haiku-4-5`, judge `claude-opus-5-5`, 3 repeat(s) of 12 question(s) per condition, seed 20261020, OCM snapshot 2026-10-15T18:30:22+10:00.

| Metric | zero_shot | few_shot | scaffold |
|---|---|---|---|
| tool_ok | 89% (n=36) | 83% (n=36) | 92% (n=36) |
| args_ok | 95% (n=21) | 83% (n=18) | 100% (n=20) |
| coords_ok | 57% (n=21) | 100% (n=18) | 100% (n=20) |
| stop_ok | 80% (n=15) | 87% (n=15) | 88% (n=17) |
| verdict_ok | 92% (n=36) | 92% (n=36) | 97% (n=36) |
| faithful | 50% (n=36) | 58% (n=36) | 69% (n=36) |
| all_ok | 42% (n=36) | 50% (n=36) | 67% (n=36) |
| step-limit hits | 0 | 0 | 0 |
| errors | 0 | 0 | 0 |
| median latency (s) | 8.03 | 7.9750000000000005 | 9.965 |
| router USD per run | 0.007063 | 0.011082 | 0.009241 |
| router input tokens per run | 5072 | 9477 | 6638 |
| router output tokens per run | 398 | 321 | 520 |

## all_ok by question

| Q | zero_shot | few_shot | scaffold |
|---|---|---|---|
| 1 | 67% | 0% | 33% |
| 2 | 33% | 67% | 67% |
| 3 | 33% | 100% | 33% |
| 4 | 33% | 100% | 100% |
| 5 | 100% | 100% | 100% |
| 6 | 0% | 100% | 100% |
| 7 | 100% | 100% | 67% |
| 8 | 0% | 0% | 33% |
| 9 | 33% | 0% | 67% |
| 10 | 33% | 33% | 67% |
| 11 | 67% | 0% | 100% |
| 12 | 0% | 0% | 33% |
