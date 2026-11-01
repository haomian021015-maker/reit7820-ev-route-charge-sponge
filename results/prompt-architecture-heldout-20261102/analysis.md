# Statistics - 20261102-040146

216 runs. Rates with 95% Wilson intervals; differences by a permutation test stratified by question (20000 shuffles, seed 7, two-sided).

| Metric | zero_shot | few_shot | scaffold |
|---|---|---|---|
| tool_ok | 68/72 = 94% [87%, 98%] | 67/72 = 93% [85%, 97%] | 66/72 = 92% [83%, 96%] |
| args_ok | 45/51 = 88% [77%, 94%] | 45/45 = 100% [92%, 100%] | 47/50 = 94% [84%, 98%] |
| coords_ok | 51/51 = 100% [93%, 100%] | 45/45 = 100% [92%, 100%] | 50/50 = 100% [93%, 100%] |
| stop_ok | 25/33 = 76% [59%, 87%] | 30/33 = 91% [76%, 97%] | 30/33 = 91% [76%, 97%] |
| verdict_ok | 66/72 = 92% [83%, 96%] | 70/72 = 97% [90%, 99%] | 68/72 = 94% [87%, 98%] |
| faithful | 46/72 = 64% [52%, 74%] | 58/72 = 81% [70%, 88%] | 52/72 = 72% [61%, 81%] |
| all_ok | 33/72 = 46% [35%, 57%] | 53/72 = 74% [62%, 82%] | 48/72 = 67% [55%, 76%] |

| Metric | Comparison | Difference | p |
|---|---|---|---|
| tool_ok | few_shot vs zero_shot | -1.4 pts | 1.000 |
| tool_ok | scaffold vs zero_shot | -2.8 pts | 0.548 |
| tool_ok | scaffold vs few_shot | -1.4 pts | 1.000 |
| args_ok | few_shot vs zero_shot | +11.8 pts | 1.000 |
| args_ok | scaffold vs zero_shot | +5.8 pts | 0.101 |
| args_ok | scaffold vs few_shot | -6.0 pts | 1.000 |
| coords_ok | few_shot vs zero_shot | +0.0 pts | 1.000 |
| coords_ok | scaffold vs zero_shot | +0.0 pts | 1.000 |
| coords_ok | scaffold vs few_shot | +0.0 pts | 1.000 |
| stop_ok | few_shot vs zero_shot | +15.2 pts | 0.021 |
| stop_ok | scaffold vs zero_shot | +15.2 pts | 0.040 |
| stop_ok | scaffold vs few_shot | +0.0 pts | 1.000 |
| verdict_ok | few_shot vs zero_shot | +5.6 pts | 0.050 |
| verdict_ok | scaffold vs zero_shot | +2.8 pts | 0.543 |
| verdict_ok | scaffold vs few_shot | -2.8 pts | 0.494 |
| faithful | few_shot vs zero_shot | +16.7 pts | 0.028 |
| faithful | scaffold vs zero_shot | +8.3 pts | 0.331 |
| faithful | scaffold vs few_shot | -8.3 pts | 0.298 |
| all_ok | few_shot vs zero_shot | +27.8 pts | 0.000 |
| all_ok | scaffold vs zero_shot | +20.8 pts | 0.008 |
| all_ok | scaffold vs few_shot | -6.9 pts | 0.390 |

Three pairwise comparisons per metric: at a family-wise 0.05, a difference needs p < 0.017 (Bonferroni) to be read as more than suggestive.
