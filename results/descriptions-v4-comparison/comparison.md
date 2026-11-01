# Tool descriptions v3 against v4 - zero-shot router

v3 runs: prompt-architecture-20261020, prompt-architecture-heldout-20261102; v4 runs: descriptions-v4-original, descriptions-v4-heldout. Same router, questions, seeds and scoring; only the agent's descriptions and response order differ. Differences by a permutation test stratified by question (20000 shuffles, two-sided).

| Metric | v3 | v4 | Difference | p |
|---|---|---|---|---|
| tool_ok | 100/108 = 93% | 103/108 = 95% | +2.8 pts | 0.411 |
| args_ok | 65/72 = 90% | 76/80 = 95% | +4.7 pts | 0.205 |
| coords_ok | 63/72 = 88% | 61/80 = 76% | -11.3 pts | 0.192 |
| stop_ok | 37/48 = 77% | 47/51 = 92% | +15.1 pts | 0.016 |
| verdict_ok | 99/108 = 92% | 103/108 = 95% | +3.7 pts | 0.049 |
| faithful | 64/108 = 59% | 52/108 = 48% | -11.1 pts | 0.112 |
| all_ok | 48/108 = 44% | 41/108 = 38% | -6.5 pts | 0.367 |

## The questions each fix was aimed at

| Fix | Question | v3 all_ok | v4 all_ok | v3 verdict_ok | v4 verdict_ok | v3 faithful | v4 faithful |
|---|---|---|---|---|---|---|---|
| Consumption must be > 0 (fix 1) | charging Q11 | 2/3 | 2/3 | 3/3 | 3/3 | 2/3 | 2/3 |
| Consumption must be > 0 (fix 1) | heldout Q6 | 0/3 | 0/3 | 0/3 | 0/3 | 3/3 | 2/3 |
| null means unknown, not no (fix 2) | charging Q8 | 0/3 | 1/3 | 0/3 | 3/3 | 0/3 | 1/3 |
| null means unknown, not no (fix 2) | heldout Q16 | 3/3 | 3/3 | 3/3 | 3/3 | 3/3 | 3/3 |
| Call even without optional values (fix 3) | charging Q8 | 0/3 | 1/3 | 0/3 | 3/3 | 0/3 | 1/3 |
