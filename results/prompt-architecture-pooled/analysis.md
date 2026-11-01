# Statistics - pooled (prompt-architecture-20261020, prompt-architecture-heldout-20261102)

324 runs. Rates with 95% Wilson intervals; differences by a permutation test stratified by question (20000 shuffles, seed 7, two-sided).

| Metric | zero_shot | few_shot | scaffold |
|---|---|---|---|
| tool_ok | 100/108 = 93% [86%, 96%] | 97/108 = 90% [83%, 94%] | 99/108 = 92% [85%, 96%] |
| args_ok | 65/72 = 90% [81%, 95%] | 60/63 = 95% [87%, 98%] | 67/70 = 96% [88%, 99%] |
| coords_ok | 63/72 = 88% [78%, 93%] | 63/63 = 100% [94%, 100%] | 70/70 = 100% [95%, 100%] |
| stop_ok | 37/48 = 77% [63%, 87%] | 43/48 = 90% [78%, 95%] | 45/50 = 90% [79%, 96%] |
| verdict_ok | 99/108 = 92% [85%, 96%] | 103/108 = 95% [90%, 98%] | 103/108 = 95% [90%, 98%] |
| faithful | 64/108 = 59% [50%, 68%] | 79/108 = 73% [64%, 81%] | 77/108 = 71% [62%, 79%] |
| all_ok | 48/108 = 44% [35%, 54%] | 71/108 = 66% [56%, 74%] | 72/108 = 67% [57%, 75%] |

| Metric | Comparison | Difference | p |
|---|---|---|---|
| tool_ok | few_shot vs zero_shot | -2.8 pts | 0.318 |
| tool_ok | scaffold vs zero_shot | -0.9 pts | 1.000 |
| tool_ok | scaffold vs few_shot | +1.9 pts | 0.674 |
| args_ok | few_shot vs zero_shot | +5.0 pts | 0.975 |
| args_ok | scaffold vs zero_shot | +5.4 pts | 0.049 |
| args_ok | scaffold vs few_shot | +0.5 pts | 1.000 |
| coords_ok | few_shot vs zero_shot | +12.5 pts | 0.009 |
| coords_ok | scaffold vs zero_shot | +12.5 pts | 0.008 |
| coords_ok | scaffold vs few_shot | +0.0 pts | 1.000 |
| stop_ok | few_shot vs zero_shot | +12.5 pts | 0.033 |
| stop_ok | scaffold vs zero_shot | +12.9 pts | 0.026 |
| stop_ok | scaffold vs few_shot | +0.4 pts | 1.000 |
| verdict_ok | few_shot vs zero_shot | +3.7 pts | 0.050 |
| verdict_ok | scaffold vs zero_shot | +3.7 pts | 0.141 |
| verdict_ok | scaffold vs few_shot | +0.0 pts | 1.000 |
| faithful | few_shot vs zero_shot | +13.9 pts | 0.023 |
| faithful | scaffold vs zero_shot | +12.0 pts | 0.062 |
| faithful | scaffold vs few_shot | -1.9 pts | 0.869 |
| all_ok | few_shot vs zero_shot | +21.3 pts | 0.000 |
| all_ok | scaffold vs zero_shot | +22.2 pts | 0.000 |
| all_ok | scaffold vs few_shot | +0.9 pts | 1.000 |

Three pairwise comparisons per metric: at a family-wise 0.05, a difference needs p < 0.017 (Bonferroni) to be read as more than suggestive.
