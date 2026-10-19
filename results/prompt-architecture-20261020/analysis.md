# Statistics - 20261020-053044-rescored

108 runs. Rates with 95% Wilson intervals; differences by a permutation test stratified by question (20000 shuffles, seed 7, two-sided).

| Metric | zero_shot | few_shot | scaffold |
|---|---|---|---|
| tool_ok | 32/36 = 89% [75%, 96%] | 30/36 = 83% [68%, 92%] | 33/36 = 92% [78%, 97%] |
| args_ok | 20/21 = 95% [77%, 99%] | 15/18 = 83% [61%, 94%] | 20/20 = 100% [84%, 100%] |
| coords_ok | 12/21 = 57% [37%, 76%] | 18/18 = 100% [82%, 100%] | 20/20 = 100% [84%, 100%] |
| stop_ok | 12/15 = 80% [55%, 93%] | 13/15 = 87% [62%, 96%] | 15/17 = 88% [66%, 97%] |
| verdict_ok | 33/36 = 92% [78%, 97%] | 33/36 = 92% [78%, 97%] | 35/36 = 97% [86%, 100%] |
| faithful | 18/36 = 50% [34%, 66%] | 21/36 = 58% [42%, 73%] | 25/36 = 69% [53%, 82%] |
| all_ok | 15/36 = 42% [27%, 58%] | 18/36 = 50% [34%, 66%] | 24/36 = 67% [50%, 80%] |

| Metric | Comparison | Difference | p |
|---|---|---|---|
| tool_ok | few_shot vs zero_shot | -5.6 pts | 0.396 |
| tool_ok | scaffold vs zero_shot | +2.8 pts | 1.000 |
| tool_ok | scaffold vs few_shot | +8.3 pts | 0.208 |
| args_ok | few_shot vs zero_shot | -11.9 pts | 0.302 |
| args_ok | scaffold vs zero_shot | +4.8 pts | 1.000 |
| args_ok | scaffold vs few_shot | +16.7 pts | 0.049 |
| coords_ok | few_shot vs zero_shot | +42.9 pts | 0.008 |
| coords_ok | scaffold vs zero_shot | +42.9 pts | 0.009 |
| coords_ok | scaffold vs few_shot | +0.0 pts | 1.000 |
| stop_ok | few_shot vs zero_shot | +6.7 pts | 1.000 |
| stop_ok | scaffold vs zero_shot | +8.2 pts | 0.604 |
| stop_ok | scaffold vs few_shot | +1.6 pts | 1.000 |
| verdict_ok | few_shot vs zero_shot | +0.0 pts | 1.000 |
| verdict_ok | scaffold vs zero_shot | +5.6 pts | 0.400 |
| verdict_ok | scaffold vs few_shot | +5.6 pts | 0.405 |
| faithful | few_shot vs zero_shot | +8.3 pts | 0.569 |
| faithful | scaffold vs zero_shot | +19.4 pts | 0.122 |
| faithful | scaffold vs few_shot | +11.1 pts | 0.356 |
| all_ok | few_shot vs zero_shot | +8.3 pts | 0.570 |
| all_ok | scaffold vs zero_shot | +25.0 pts | 0.046 |
| all_ok | scaffold vs few_shot | +16.7 pts | 0.148 |

Three pairwise comparisons per metric: at a family-wise 0.05, a difference needs p < 0.017 (Bonferroni) to be read as more than suggestive.
