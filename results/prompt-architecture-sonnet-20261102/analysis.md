# Statistics - 20261102-043628

144 runs. Rates with 95% Wilson intervals; differences by a permutation test stratified by question (20000 shuffles, seed 7, two-sided).

| Metric | zero_shot | few_shot |
|---|---|---|
| tool_ok | 63/72 = 88% [78%, 93%] | 72/72 = 100% [95%, 100%] |
| args_ok | 45/48 = 94% [83%, 98%] | 45/48 = 94% [83%, 98%] |
| coords_ok | 48/48 = 100% [93%, 100%] | 48/48 = 100% [93%, 100%] |
| stop_ok | 32/33 = 97% [85%, 99%] | 32/33 = 97% [85%, 99%] |
| verdict_ok | 69/72 = 96% [88%, 99%] | 68/72 = 94% [87%, 98%] |
| faithful | 64/72 = 89% [80%, 94%] | 71/72 = 99% [93%, 100%] |
| all_ok | 59/72 = 82% [72%, 89%] | 67/72 = 93% [85%, 97%] |

| Metric | Comparison | Difference | p |
|---|---|---|---|
| tool_ok | few_shot vs zero_shot | +12.5 pts | 0.001 |
| args_ok | few_shot vs zero_shot | +0.0 pts | 1.000 |
| coords_ok | few_shot vs zero_shot | +0.0 pts | 1.000 |
| stop_ok | few_shot vs zero_shot | +0.0 pts | 1.000 |
| verdict_ok | few_shot vs zero_shot | -1.4 pts | 1.000 |
| faithful | few_shot vs zero_shot | +9.7 pts | 0.010 |
| all_ok | few_shot vs zero_shot | +11.1 pts | 0.011 |

One comparison per metric: a difference needs p < 0.05.
